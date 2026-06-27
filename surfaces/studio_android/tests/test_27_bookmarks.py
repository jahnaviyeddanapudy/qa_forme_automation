"""test_27_bookmarks — Studio VOD class bookmark flow.

Single comprehensive test covering three Zebrunner tickets:

  - FORME-6697 — Bookmark VOD classes (Phase A + B)
  - FORME-6698 — Remove bookmark (Phase C + D)
  - FORME-6707 — Profile-specific bookmarks (Phase E)

Lenient baseline policy:
  BOOKMARKED is allowed to have pre-existing bookmarks. The test:
   1) Reads baseline before Phase A
   2) Excludes pre-existing entries from target list (otherwise
      tapping image_bookmark on them would REMOVE them — toggle
      behavior)
   3) Asserts pre-existing bookmarks stay untouched throughout

No cleanup:
  Remaining bookmarks persist on guest profile after test completes.
  Tap_image_bookmark is idempotent because Phase A's exclusion logic
  skips already-bookmarked targets on re-runs.

Phases:
  Baseline-guest. Read guest's BOOKMARKED before any modifications.
  Baseline-owner. Switch to owner, read owner's BOOKMARKED, switch
                  back. Needed for Phase E to distinguish a real
                  leak from a coincidence (owner happens to have
                  the same class bookmarked independently).
  A. Scroll FEATURED top-to-bottom. As we encounter each section
     header (Recovery, Yoga Sculpt, Barre, ...), bookmark the first
     valid VOD card in that section. Stop when 5 sections covered.
     "Valid" = fully-bound + non-CPS + has image_bookmark + not in
     baseline.
  B. Verify all 5 targets appear in BOOKMARKED + baseline still
     present.
  C. Remove REMOVE_COUNT (2) bookmarks from BOOKMARKED sub-tab.
  D. Verify the 2 are gone, remaining 3 still there, baseline
     still untouched.
  E. Switch to owner, compute owner_new = owner_current -
     owner_baseline. Assert none of guest's 5 targets appear in
     owner_new (those would be real leaks). Pre-existing
     overlap = coincidence, not a leak.

Design choice — bookmark as we scroll (not collect-then-bookmark):
  Earlier version collected records across scrolls, then went back
  to bookmark each. That failed because Studio's sub-tab tap doesn't
  reset scroll position, so the "go back up to find Recovery" step
  was stuck at the bottom of FEATURED.
  New approach: when we see a section's first valid card during
  the scroll-down walk, bookmark it RIGHT THERE while it's still
  visible. No need to scroll back up.

VOD card identification (skip CPS and Program cards):
  - CPS cards have personal_message_icon as a descendant
  - Program cards have no text_title on the card itself
  - Regular VOD cards have text_title + text_trainer + text_detail

Section identification:
  A text_title element whose ancestor chain does NOT contain a card
  element is a section header (e.g. "Recovery", "Yoga Sculpt").
  text_title elements INSIDE a card are class titles, attributed to
  the most-recent section header in document order.

Empty-state marker:
  fragment_no_bookmarks appears when BOOKMARKED has zero cards.

Run:
    pytest -m studio surfaces/studio/tests/test_27_bookmarks.py -v -s
"""
import time
import xml.etree.ElementTree as ET

import pytest

from appium.webdriver.common.appiumby import AppiumBy

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.config import (
    GUEST1_PROFILE_INDEX,
    OWNER_PROFILE_INDEX,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage


SOURCE_SUBTAB = "FEATURED"
BOOKMARKS_SUBTAB = "BOOKMARKED"

TARGET_BOOKMARK_COUNT = 5
REMOVE_COUNT = 2
MAX_FEATURED_SCROLLS = 8

FRAGMENT_NO_BOOKMARKS_ID = "fragment_no_bookmarks"


# =========================================================
# Driver fixture
# =========================================================

@pytest.fixture(scope="function")
def driver():
    if GUEST1_PROFILE_INDEX is None:
        pytest.skip(
            "GUEST1_PROFILE_INDEX not configured in config_local.py."
        )
    d = _create_studio_driver()
    try:
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass


# =========================================================
# Navigation helpers
# =========================================================

def _ensure_studio_subtab(driver, subtab_name):
    """Navigate to Studio tab → given sub-tab."""
    home = HomePage(driver)
    studio = StudioTabPage(driver)

    if not studio.is_loaded(timeout=2):
        if home.is_loaded(timeout=2):
            home.tap_studio_tab()
            studio.wait_for_studio_tab()
        else:
            home.wait_for_home()
            home.tap_studio_tab()
            studio.wait_for_studio_tab()

    studio.tap_subtab(subtab_name)
    studio.wait_seconds(2)
    studio.wait_for_card_grid_to_settle()
    return studio


# =========================================================
# Card-record helpers (XML parsing of driver.page_source)
# =========================================================

def _read_xml_card_record(card_elem, app_package):
    """Read (title, trainer, detail) from a card XML element."""
    record = {"title": "", "trainer": "", "detail": ""}
    suffix_to_field = {
        "text_title": "title",
        "text_trainer": "trainer",
        "text_detail": "detail",
    }
    for child in card_elem.iter():
        rid = child.attrib.get("resource-id", "") or ""
        if ":id/" not in rid:
            continue
        short = rid.split(":id/")[-1]
        if short in suffix_to_field:
            text = (child.attrib.get("text", "") or "").strip()
            field = suffix_to_field[short]
            if not record[field]:
                record[field] = text
    return record


def _is_valid_vod_card_record(record):
    """All three fields populated = fully-bound bookmarkable card."""
    return bool(record["title"] and record["trainer"]
                and record["detail"])


def _xml_card_is_cps(card_elem, app_package):
    """Card has personal_message_icon → it's a CPS card."""
    pmi_rid = f"{app_package}:id/personal_message_icon"
    for child in card_elem.iter():
        if child.attrib.get("resource-id", "") == pmi_rid:
            return True
    return False


def _xml_card_has_image_bookmark(card_elem, app_package):
    """Card must have image_bookmark to be bookmarkable."""
    ib_rid = f"{app_package}:id/image_bookmark"
    for child in card_elem.iter():
        if child.attrib.get("resource-id", "") == ib_rid:
            return True
    return False


def _elem_has_card_ancestor(root, target_elem, app_package):
    """Walk root, build parent map, check if target has card ancestor."""
    parent_map = {c: p for p in root.iter() for c in p}
    cur = parent_map.get(target_elem)
    card_rid = f"{app_package}:id/card"
    while cur is not None:
        if cur.attrib.get("resource-id", "") == card_rid:
            return True
        cur = parent_map.get(cur)
    return False


def _find_card_ancestor(root, target_elem, app_package):
    """Return the card ancestor element of target_elem, or None."""
    parent_map = {c: p for p in root.iter() for c in p}
    cur = parent_map.get(target_elem)
    card_rid = f"{app_package}:id/card"
    while cur is not None:
        if cur.attrib.get("resource-id", "") == card_rid:
            return cur
        cur = parent_map.get(cur)
    return None


# =========================================================
# Tap helpers (live Appium elements)
# =========================================================

def _tap_image_bookmark_on_card(driver, studio, target):
    """Find the card matching target's triple on the CURRENT screen,
    tap its image_bookmark child. Returns True if found + tapped."""
    app_package = studio.APP_PACKAGE
    cards = driver.find_elements(
        AppiumBy.ID,
        f"{app_package}:id/{studio.CARD_ID}",
    )
    for card in cards:
        try:
            title_el = card.find_element(
                AppiumBy.ID, f"{app_package}:id/text_title"
            )
            title = (title_el.get_attribute("text") or "").strip()
            if title != target["title"]:
                continue
            try:
                trainer = (card.find_element(
                    AppiumBy.ID, f"{app_package}:id/text_trainer"
                ).get_attribute("text") or "").strip()
            except Exception:
                trainer = ""
            try:
                detail = (card.find_element(
                    AppiumBy.ID, f"{app_package}:id/text_detail"
                ).get_attribute("text") or "").strip()
            except Exception:
                detail = ""
            if (trainer == target["trainer"] and
                    detail == target["detail"]):
                try:
                    icon = card.find_element(
                        AppiumBy.ID,
                        f"{app_package}:id/image_bookmark"
                    )
                    icon.click()
                    time.sleep(1.5)
                    return True
                except Exception as e:
                    print(f"[tap-bookmark] Found card but "
                          f"image_bookmark not tappable: {e}")
                    return False
        except Exception:
            continue
    return False


# =========================================================
# BOOKMARKED sub-tab queries
# =========================================================

def _is_bookmarked_subtab_empty(driver, studio):
    """True if BOOKMARKED shows fragment_no_bookmarks."""
    try:
        driver.find_element(
            AppiumBy.ID,
            f"{studio.APP_PACKAGE}:id/{FRAGMENT_NO_BOOKMARKS_ID}",
        )
        return True
    except Exception:
        return False


def _get_bookmarked_records(driver, studio):
    """Navigate to BOOKMARKED, return card records currently
    bookmarked. Empty list if empty state shown."""
    _ensure_studio_subtab(driver, BOOKMARKS_SUBTAB)
    if _is_bookmarked_subtab_empty(driver, studio):
        return []

    # Read all card elements via XML for consistency with FEATURED
    app_package = studio.APP_PACKAGE
    try:
        root = ET.fromstring(driver.page_source)
    except ET.ParseError:
        return []

    records = []
    seen = set()
    card_rid = f"{app_package}:id/card"
    for elem in root.iter():
        if elem.attrib.get("resource-id", "") != card_rid:
            continue
        if _xml_card_is_cps(elem, app_package):
            continue
        rec = _read_xml_card_record(elem, app_package)
        if not _is_valid_vod_card_record(rec):
            continue
        key = (rec["title"], rec["trainer"], rec["detail"])
        if key in seen:
            continue
        seen.add(key)
        records.append(rec)
    return records


# =========================================================
# Core: scroll FEATURED + bookmark as we go
# =========================================================

def _scroll_and_bookmark_per_section(driver, studio, target_count,
                                     baseline_keys,
                                     max_scrolls=MAX_FEATURED_SCROLLS):
    """Scroll FEATURED top-to-bottom. For each NEW section encountered,
    bookmark the first valid VOD card visible in that section. Stop
    when target_count sections bookmarked or max_scrolls exhausted.

    "Valid" = fully-bound + non-CPS + has image_bookmark + not
    already bookmarked (key not in baseline_keys).
    "New section" = section header text we haven't bookmarked from.

    Returns list of records bookmarked. Each record has an added
    "section" key with the section name it came from.

    Bookmarking happens immediately when each card is discovered —
    no separate collect-then-bookmark phase, so we don't need to
    scroll back up.
    """
    size = driver.get_window_size()
    swipe_y_start = int(size["height"] * 0.75)
    swipe_y_end = int(size["height"] * 0.25)
    swipe_x = size["width"] // 2
    app_package = studio.APP_PACKAGE

    bookmarked = {}  # section_name -> record

    for scroll_num in range(max_scrolls + 1):
        try:
            root = ET.fromstring(driver.page_source)
        except ET.ParseError as e:
            print(f"[scroll-bookmark] XML parse failed: {e}")
            continue

        # Walk in document order: track current section, find first
        # valid bookmarkable card in each new section.
        current_section = None
        actions = []  # (section, record) to bookmark this iteration

        for elem in root.iter():
            rid = elem.attrib.get("resource-id", "") or ""
            short_id = rid.split(":id/")[-1] if ":id/" in rid else rid
            if short_id != "text_title":
                continue
            text = (elem.attrib.get("text", "") or "").strip()
            if not text:
                continue

            if _elem_has_card_ancestor(root, elem, app_package):
                # Card title
                if current_section is None:
                    continue
                if current_section in bookmarked:
                    continue
                # Don't queue more than one action per section per
                # scroll (we'll bookmark the first one and move on)
                already_queued = any(
                    s == current_section for s, _ in actions
                )
                if already_queued:
                    continue
                card_elem = _find_card_ancestor(root, elem, app_package)
                if card_elem is None:
                    continue
                record = _read_xml_card_record(card_elem, app_package)
                if not _is_valid_vod_card_record(record):
                    continue
                if _xml_card_is_cps(card_elem, app_package):
                    continue
                if not _xml_card_has_image_bookmark(
                        card_elem, app_package):
                    continue
                key = (record["title"], record["trainer"],
                       record["detail"])
                if key in baseline_keys:
                    print(f"[scroll-bookmark] Skip pre-existing "
                          f"bookmark in section '{current_section}': "
                          f"'{record['title']}'")
                    continue
                actions.append((current_section, record))
            else:
                # Section header
                current_section = text

        # Execute bookmark taps for queued actions
        for section_name, record in actions:
            if section_name in bookmarked:
                continue  # Race: another action already covered it
            print(f"[scroll-bookmark] Bookmarking from "
                  f"'{section_name}': '{record['title']}' "
                  f"({record['detail']}, {record['trainer']})")
            success = _tap_image_bookmark_on_card(
                driver, studio, record
            )
            if not success:
                # Retry once after settle
                time.sleep(1)
                success = _tap_image_bookmark_on_card(
                    driver, studio, record
                )
            if not success:
                print(f"[scroll-bookmark] Failed to tap "
                      f"image_bookmark for '{record['title']}' — "
                      f"skipping this section, will try next "
                      f"valid card in same section on next iteration")
                continue
            record["section"] = section_name
            bookmarked[section_name] = record
            if len(bookmarked) >= target_count:
                break

        print(f"[scroll-bookmark] scroll {scroll_num}: "
              f"{len(bookmarked)} sections bookmarked "
              f"so far: {list(bookmarked.keys())}")

        if len(bookmarked) >= target_count:
            break
        if scroll_num == max_scrolls:
            break

        driver.swipe(swipe_x, swipe_y_start, swipe_x, swipe_y_end, 600)
        time.sleep(1.5)
        studio.wait_for_card_grid_to_settle()

    return list(bookmarked.values())


# =========================================================
# Main test
# =========================================================

@pytest.mark.studio
def test_bookmark_flow_end_to_end(driver):
    """End-to-end bookmark flow covering FORME-6697 + 6698 + 6707."""
    if OWNER_PROFILE_INDEX is None:
        pytest.skip(
            "OWNER_PROFILE_INDEX not configured in config_local.py — "
            "Phase E requires both guest and owner profiles."
        )

    login_at_profile_index(
        driver, profile_index=GUEST1_PROFILE_INDEX,
        role_label="GUEST 1"
    )
    home = HomePage(driver)

    # =====================================================
    # BASELINE (guest)
    # =====================================================
    print(f"\n{'='*60}\n[baseline-guest] Read guest's BOOKMARKED\n"
          f"{'='*60}")
    studio = _ensure_studio_subtab(driver, SOURCE_SUBTAB)
    baseline_records = _get_bookmarked_records(driver, studio)
    baseline_keys = {
        (r["title"], r["trainer"], r["detail"])
        for r in baseline_records
    }
    print(f"[baseline-guest] {len(baseline_records)} pre-existing "
          f"bookmarks on guest profile")
    for r in baseline_records:
        print(f"[baseline-guest]   {r['title']} | {r['detail']} | "
              f"{r['trainer']}")

    # =====================================================
    # BASELINE (owner) — switch to owner and read BEFORE guest
    # modifies anything. Needed so Phase E can distinguish a real
    # bookmark leak from a coincidence (owner happens to have the
    # same class pre-bookmarked independently).
    # =====================================================
    print(f"\n{'='*60}\n[baseline-owner] Switch to owner, read "
          f"owner's BOOKMARKED\n{'='*60}")
    home.tap_back_to_profile()
    time.sleep(3)
    login_at_profile_index(
        driver, profile_index=OWNER_PROFILE_INDEX,
        role_label="OWNER"
    )

    studio = _ensure_studio_subtab(driver, SOURCE_SUBTAB)
    owner_baseline_records = _get_bookmarked_records(driver, studio)
    owner_baseline_keys = {
        (r["title"], r["trainer"], r["detail"])
        for r in owner_baseline_records
    }
    print(f"[baseline-owner] {len(owner_baseline_records)} pre-existing "
          f"bookmarks on owner profile")
    for r in owner_baseline_records:
        print(f"[baseline-owner]   {r['title']} | {r['detail']} | "
              f"{r['trainer']}")

    # Switch back to guest for Phase A
    print(f"\n[setup] Switching back to guest for Phase A")
    home.tap_back_to_profile()
    time.sleep(3)
    login_at_profile_index(
        driver, profile_index=GUEST1_PROFILE_INDEX,
        role_label="GUEST 1"
    )

    # =====================================================
    # PHASE A — Bookmark as we scroll
    # =====================================================
    print(f"\n{'='*60}\n[Phase A] Scroll FEATURED, bookmark "
          f"{TARGET_BOOKMARK_COUNT} VODs (one per section)\n"
          f"{'='*60}")
    studio = _ensure_studio_subtab(driver, SOURCE_SUBTAB)
    targets = _scroll_and_bookmark_per_section(
        driver, studio,
        target_count=TARGET_BOOKMARK_COUNT,
        baseline_keys=baseline_keys,
    )

    assert len(targets) >= TARGET_BOOKMARK_COUNT, (
        f"Need {TARGET_BOOKMARK_COUNT} bookmarks across different "
        f"sections, but only got {len(targets)}: "
        f"{[t.get('section') for t in targets]}. Either FEATURED "
        f"has too few sections with valid VOD cards, or scroll/tap "
        f"failures left us short."
    )

    sections_used = [t.get("section", "?") for t in targets]
    print(f"[Phase A] ✓ Bookmarked {len(targets)} classes from "
          f"sections: {sections_used}")

    # =====================================================
    # PHASE B — Verify targets in BOOKMARKED + baseline preserved
    # =====================================================
    print(f"\n{'='*60}\n[Phase B] Verify all in BOOKMARKED\n"
          f"{'='*60}")
    bookmarked_records = _get_bookmarked_records(driver, studio)
    bookmarked_keys = {
        (r["title"], r["trainer"], r["detail"])
        for r in bookmarked_records
    }
    print(f"[Phase B] BOOKMARKED contains {len(bookmarked_records)} "
          f"cards (baseline was {len(baseline_records)})")

    for t in targets:
        key = (t["title"], t["trainer"], t["detail"])
        assert key in bookmarked_keys, (
            f"'{t['title']}' was bookmarked in Phase A but not in "
            f"BOOKMARKED. Visible: {bookmarked_records}"
        )
    print(f"[Phase B] ✓ All {len(targets)} new bookmarks present")

    missing_baseline = baseline_keys - bookmarked_keys
    assert not missing_baseline, (
        f"Pre-existing bookmarks disappeared after Phase A: "
        f"{sorted(missing_baseline)}"
    )
    if baseline_keys:
        print(f"[Phase B] ✓ All {len(baseline_keys)} pre-existing "
              f"bookmarks still present")

    # =====================================================
    # PHASE C — Remove REMOVE_COUNT bookmarks
    # =====================================================
    print(f"\n{'='*60}\n[Phase C] Remove {REMOVE_COUNT} bookmarks\n"
          f"{'='*60}")
    to_remove = targets[:REMOVE_COUNT]
    to_keep = targets[REMOVE_COUNT:]

    studio = _ensure_studio_subtab(driver, BOOKMARKS_SUBTAB)
    for i, t in enumerate(to_remove):
        print(f"[Phase C] [{i+1}/{REMOVE_COUNT}] Removing: "
              f"'{t['title']}'")
        success = _tap_image_bookmark_on_card(driver, studio, t)
        assert success, (
            f"Could not find/tap '{t['title']}' on BOOKMARKED."
        )
    print(f"[Phase C] ✓ Removed {REMOVE_COUNT} bookmarks")

    # =====================================================
    # PHASE D — Verify state after partial removal
    # =====================================================
    print(f"\n{'='*60}\n[Phase D] Verify state after removal\n"
          f"{'='*60}")
    bookmarked_records = _get_bookmarked_records(driver, studio)
    bookmarked_keys = {
        (r["title"], r["trainer"], r["detail"])
        for r in bookmarked_records
    }
    print(f"[Phase D] BOOKMARKED now contains "
          f"{len(bookmarked_records)} cards")

    for t in to_remove:
        key = (t["title"], t["trainer"], t["detail"])
        assert key not in bookmarked_keys, (
            f"'{t['title']}' was removed but still in BOOKMARKED."
        )
    print(f"[Phase D] ✓ Removed bookmarks no longer in BOOKMARKED")

    for t in to_keep:
        key = (t["title"], t["trainer"], t["detail"])
        assert key in bookmarked_keys, (
            f"'{t['title']}' was NOT removed but is missing from "
            f"BOOKMARKED."
        )
    print(f"[Phase D] ✓ Remaining {len(to_keep)} new bookmarks "
          f"still in BOOKMARKED")

    missing_baseline = baseline_keys - bookmarked_keys
    assert not missing_baseline, (
        f"Pre-existing bookmarks disappeared after Phase C: "
        f"{sorted(missing_baseline)}"
    )
    if baseline_keys:
        print(f"[Phase D] ✓ All {len(baseline_keys)} pre-existing "
              f"bookmarks still present")

    # =====================================================
    # PHASE E — Profile isolation check
    #
    # The honest test: did any of guest's NEW bookmarks (added during
    # this test session) appear on owner since we read owner's
    # baseline? Pure overlap is NOT a leak — owner can have the same
    # class bookmarked independently. We need additions-since-baseline.
    # =====================================================
    print(f"\n{'='*60}\n[Phase E] Switch to owner, verify isolation\n"
          f"{'='*60}")
    home.tap_back_to_profile()
    time.sleep(3)
    login_at_profile_index(
        driver, profile_index=OWNER_PROFILE_INDEX,
        role_label="OWNER"
    )

    owner_current_records = _get_bookmarked_records(driver, studio)
    owner_current_keys = {
        (r["title"], r["trainer"], r["detail"])
        for r in owner_current_records
    }
    print(f"[Phase E] Owner's BOOKMARKED contains "
          f"{len(owner_current_records)} cards "
          f"(baseline was {len(owner_baseline_records)})")

    # New on owner = present now but NOT in owner's baseline. These
    # are the only ones that could possibly be a leak from guest.
    new_on_owner = owner_current_keys - owner_baseline_keys
    if new_on_owner:
        print(f"[Phase E] WARNING: owner has {len(new_on_owner)} "
              f"bookmarks now that weren't there at baseline: "
              f"{sorted(new_on_owner)}")

    # Check whether any of guest's Phase A additions appear in
    # owner's new set
    guest_target_keys = {
        (t["title"], t["trainer"], t["detail"]) for t in to_keep
    }
    guest_leaks = guest_target_keys & new_on_owner

    assert not guest_leaks, (
        f"Guest's bookmarks LEAKED into owner profile — guest "
        f"bookmarked these in Phase A and they newly appeared on "
        f"owner: {sorted(guest_leaks)}. Bookmarks should be "
        f"profile-scoped."
    )

    # Diagnostic: count overlaps that ARE coincidences (in both
    # owner-baseline and guest's targets — owner had them already,
    # not a leak)
    coincidences = guest_target_keys & owner_baseline_keys
    if coincidences:
        print(f"[Phase E] Note: {len(coincidences)} guest target(s) "
              f"happen to be in owner's pre-existing bookmarks "
              f"(coincidence, not a leak): {sorted(coincidences)}")

    print(f"[Phase E] ✓ No guest bookmarks leaked into owner "
          f"profile (profile-scoping confirmed)")

    print(f"\n[done] Test complete. Guest profile has "
          f"{len(to_keep)} bookmarks left behind (no cleanup).")