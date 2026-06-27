"""test_26_recommended_carousel — YOUR PLAN Recommended carousel tests.

Two test functions covering three Zebrunner tickets on Home tab →
YOUR PLAN → Recommended view:

  - test_recommended_carousel_visible  → FORME-6845
  - test_play_carousel_video_with_timer_check  → FORME-6846 + 6847

Why 6846 + 6847 merged (per QA call 2026-05-15):
  Opening a class detail without playing leaves the user journey
  incomplete — verifying both navigation AND playback in one flow
  gives end-to-end coverage without redundant carousel-and-tap
  setup. Each ticket is asserted in its own section of the merged
  test, so failure attribution is still clear.

Reframe note (per QA call 2026-05-15):
  - FORME-6847 was originally scoped as manual-only "Video Quality
    and Sync" (subjective look/feel). Reframed to "play class for
    1 min + verify countdown timer decreased by ~60s" — objective
    playback-alive check.

Carousel uniqueness:
  Per product spec, each class card in the Recommended carousel
  should be unique (same instructor may appear multiple times, but
  each CLASS must be distinct). _swipe_carousel_and_collect_titles
  fails the test if it sees duplicate titles within the same
  visible set — that's a content/CMS bug worth surfacing.

Recommended view availability:
  The Recommended carousel exists on YOUR PLAN whenever the account
  has no weekly plan from a trainer. Per QA notes (2026-05-15),
  this can happen for BOTH guest accounts AND owner accounts
  during periods when no trainer is configured. Progress + streak
  blocks render for both account types regardless.

  These tests use the guest account (GUEST1_PROFILE_INDEX from
  config_local.py) for determinism — guests reliably show
  Recommended.

Carousel structure (confirmed via dump 2026-05-15):
  - recommendations_fragment       (section container)
  - text_recommended               ("Recommended" / "Weekly Plan")
  - layout_concierge with:
    - forme_icon
    - text_concierge               ("BY YOUR FORME TEAM")
    - text_description             ("Classes you might enjoy...")
  - recycler                       (horizontally scrollable carousel)
    - card (multiple, unique titles per spec)
      - image, image_bookmark, view_gradient
      - text_title                 (class name)
      - text_trainer               (trainer name)
      - text_detail                (e.g. "30 MIN • ADVANCED")

Test pattern: swipe-then-tap-last-card.
  Always tapping cards[0] doesn't exercise the swipe-then-tap path.
  These tests swipe through the carousel to inventory all classes,
  then tap the LAST one. Verifies horizontal scroll works AND that
  cards rendered after a swipe remain tappable.

Architecture:
  - Module-scoped shared_driver — login as guest once.
  - Each test does its own swipe-through-and-collect to confirm
    carousel state independently.
  - 6846+6847 merged test plays a class so it MUST run last (or
    standalone). Pytest collection order respects function
    definition order; 6845 is defined first.

Run all:
    pytest -m studio surfaces/studio/tests/test_26_recommended_carousel.py -v -s

Run a single test:
    pytest -m studio surfaces/studio/tests/test_26_recommended_carousel.py \\
        -v -s -k 'carousel_visible'
"""
import time

import pytest

from appium.webdriver.common.appiumby import AppiumBy

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.config import GUEST1_PROFILE_INDEX
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.class_detail_page import ClassDetailPage
from surfaces.studio_android.pages.apple_watch_prompt_page import AppleWatchPromptPage
from surfaces.studio_android.pages.player_page import PlayerPage


# Carousel swipe parameters
MAX_CAROUSEL_SWIPES = 6  # Cap to prevent runaway loops on unbounded recyclers

# Timer-tick verification (FORME-6847)
PLAYBACK_DURATION_SEC = 60          # Play for 1 minute
EXPECTED_DECREASE_SEC = 60          # Timer should drop ~60s
TIMER_TOLERANCE_SEC = 5             # Allow ±5s for poll/render lag


# =========================================================
# MODULE-SCOPED DRIVER — login once as guest
# =========================================================

@pytest.fixture(scope="module")
def shared_driver():
    """Module-scoped driver. Login as guest1 once; 3 tests share session.

    Skips the entire module if GUEST1_PROFILE_INDEX isn't configured
    in config_local.py."""
    if GUEST1_PROFILE_INDEX is None:
        pytest.skip(
            "GUEST1_PROFILE_INDEX not configured in config_local.py — "
            "test_26 requires a guest profile that shows Recommended "
            "view (no weekly plan). Edit surfaces/studio/config_local.py."
        )

    d = _create_studio_driver()
    try:
        login_at_profile_index(
            d, profile_index=GUEST1_PROFILE_INDEX, role_label="GUEST 1"
        )
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass


# =========================================================
# Helpers
# =========================================================

def _ensure_your_plan_loaded(driver):
    """Ensure we're on Home → YOUR PLAN tab, with Recommended carousel
    rendered.

    Best-effort cleanup if a prior test left us mid-class or
    elsewhere. Re-taps YOUR PLAN to force a fresh render at scroll
    position 0 (so the carousel is at the top of viewport).
    """
    home = HomePage(driver)

    # If we're in a class detail or player, back out and give the
    # transition enough time. ClassDetailPage → Home back-transition
    # can take 3-4s in practice; previous 2s sleep was too aggressive.
    class_detail = ClassDetailPage(driver)
    if class_detail.is_loaded(timeout=2):
        driver.back()
        time.sleep(4)
        # If we're STILL on class detail, try once more
        if class_detail.is_loaded(timeout=2):
            driver.back()
            time.sleep(4)

    # If home isn't loaded, try a couple more recovery attempts before
    # calling wait_for_home (which has its own 10s timeout)
    if not home.is_loaded(timeout=3):
        driver.back()
        time.sleep(3)

    home.wait_for_home()

    home.tap_your_plan_tab()
    home.wait_seconds(2)

    # Confirm Recommended view (not Weekly Plan) — these tests assume
    # guest account with no trainer.
    assert home.is_on_recommended_view(), (
        f"YOUR PLAN is showing Weekly Plan view, not Recommended. "
        f"GUEST1_PROFILE_INDEX may point to an account with a trainer "
        f"assigned. Section header text: "
        f"'{home.get_text(home.SECTION_HEADER_ID)}'"
    )
    return home


def _tap_card_by_record(driver, home, target_record):
    """Walk all visible cards on screen, click the one whose (title,
    trainer, detail) matches target_record exactly. Returns True if
    found and clicked, False if no card matches.

    Used when tap_class_by_name's partial-text match would be
    ambiguous — e.g. two cards share a title prefix but differ in
    duration. The composite triple uniquely identifies the card.
    """
    app_package = home.APP_PACKAGE
    cards = driver.find_elements(
        AppiumBy.ID,
        f"{app_package}:id/{home.CARD_ID}",
    )
    for card in cards:
        rec = _read_card_record(card, app_package)
        if (rec["title"] == target_record["title"] and
                rec["trainer"] == target_record["trainer"] and
                rec["detail"] == target_record["detail"]):
            card.click()
            return True
    return False


def _read_card_record(card, app_package):
    """Read (title, trainer, detail) triple from a single card element.

    Returns dict with all three fields, using empty string for any
    missing. The triple is the card's composite identity — same title
    with different duration/level is a DIFFERENT class, not a
    duplicate.
    """
    record = {"title": "", "trainer": "", "detail": ""}
    for field, id_suffix in [("title", "text_title"),
                              ("trainer", "text_trainer"),
                              ("detail", "text_detail")]:
        try:
            el = card.find_element(
                AppiumBy.ID,
                f"{app_package}:id/{id_suffix}",
            )
            record[field] = (el.get_attribute("text") or "").strip()
        except Exception:
            # Element may be absent on partially-bound cards or rest
            # days. Leave field as empty string.
            pass
    return record


def _swipe_carousel_and_collect_records(driver, home):
    """Swipe the Recommended carousel horizontally, collecting all
    unique class records seen across swipes.

    Each card's identity is the composite triple (title, trainer,
    detail). Same title with different duration/level → different
    record, not a duplicate. Real duplicate = identical triple
    within the same swipe's visible cards (that's a content bug).

    Why ordered list of records (vs set): the same recycler re-binds
    card positions as we swipe (memory #11), so the "current index"
    of a given card is unstable. The composite identity is stable.

    Returns list of dicts with keys: title, trainer, detail. The
    first occurrence of each unique triple is preserved in order.

    Stop conditions:
      - No new records after a swipe (we've hit the end)
      - MAX_CAROUSEL_SWIPES reached (safety cap)
    """
    size = driver.get_window_size()
    # Swipe within the carousel area — top third of screen (the
    # Recommended carousel is at the top of YOUR PLAN). x: right→left
    # to swipe forward through the carousel.
    swipe_y = int(size["height"] * 0.30)
    swipe_x_start = int(size["width"] * 0.85)
    swipe_x_end = int(size["width"] * 0.15)

    app_package = home.APP_PACKAGE

    ordered_records = []
    seen_keys = set()

    for swipe_num in range(MAX_CAROUSEL_SWIPES + 1):
        cards = driver.find_elements(
            AppiumBy.ID,
            f"{app_package}:id/{home.CARD_ID}",
        )

        visible_records = []
        for c in cards:
            rec = _read_card_record(c, app_package)
            # Skip cards still binding (no title yet)
            if not rec["title"]:
                continue
            visible_records.append(rec)

        # Build composite keys for duplicate detection within this swipe
        visible_keys = [
            (r["title"], r["trainer"], r["detail"])
            for r in visible_records
        ]

        # True duplicate = same (title, trainer, detail) twice in the
        # SAME visible set. Same title with different details is fine.
        if len(visible_keys) != len(set(visible_keys)):
            dupes = [k for k in visible_keys if visible_keys.count(k) > 1]
            raise AssertionError(
                f"Recommended carousel has true-duplicate cards "
                f"within the same view (swipe {swipe_num}): same "
                f"(title, trainer, detail) appears twice. "
                f"Visible: {visible_records}. "
                f"Duplicates (composite keys): {sorted(set(dupes))}. "
                f"Per spec each Recommended class should be unique "
                f"by identity (same title with different duration/"
                f"level is OK)."
            )

        new_this_swipe = []
        for r, k in zip(visible_records, visible_keys):
            if k not in seen_keys:
                ordered_records.append(r)
                seen_keys.add(k)
                new_this_swipe.append(r)

        # Compact log: show short summary per card
        short = [
            f"{r['title']} | {r['detail']}" for r in visible_records
        ]
        print(f"[carousel] swipe {swipe_num}: visible={short}, "
              f"new={len(new_this_swipe)}, total_seen={len(ordered_records)}")

        if swipe_num > 0 and not new_this_swipe:
            print(f"[carousel] No new cards after swipe {swipe_num} — "
                  f"reached end of carousel")
            break

        if swipe_num == MAX_CAROUSEL_SWIPES:
            print(f"[carousel] Hit MAX_CAROUSEL_SWIPES ({MAX_CAROUSEL_SWIPES}) "
                  f"— stopping inventory")
            break

        # Swipe horizontally within the carousel
        driver.swipe(swipe_x_start, swipe_y, swipe_x_end, swipe_y, 600)
        time.sleep(1.5)  # Let recycler rebind

    return ordered_records


# =========================================================
# FORME-6845 — Video Carousel visible
# =========================================================

@pytest.mark.studio
def test_recommended_carousel_visible(shared_driver):
    """YOUR PLAN tab → Recommended carousel is visible and populated
    with class cards.

    Verifies the structural elements (recommendations_fragment,
    text_recommended, text_concierge, layout_concierge) AND that the
    carousel contains at least one tappable class card. Also
    inventories all cards via swipe to confirm horizontal scrolling
    works.
    """
    home = _ensure_your_plan_loaded(shared_driver)

    # =====================================================
    # Step 1 — Structural elements
    # =====================================================
    print(f"\n[6845] Verifying Recommended carousel structure")

    assert home.is_visible(home.RECOMMENDATIONS_FRAGMENT_ID, timeout=3), (
        "recommendations_fragment should be visible on YOUR PLAN "
        "Recommended view"
    )
    assert home.is_visible(home.LAYOUT_CONCIERGE_ID, timeout=3), (
        "layout_concierge (header block above the carousel) should "
        "be visible"
    )
    section_text = home.get_text(home.SECTION_HEADER_ID)
    concierge_text = home.get_text(home.TEXT_CONCIERGE_ID)
    print(f"[6845] Section header: '{section_text}'")
    print(f"[6845] Concierge text: '{concierge_text}'")

    # =====================================================
    # Step 2 — Inventory carousel via swipe
    # =====================================================
    print(f"[6845] Inventorying carousel via swipe")
    records = _swipe_carousel_and_collect_records(shared_driver, home)

    assert len(records) > 0, (
        "Recommended carousel rendered but no class records found. "
        "Either the recycler is empty or text_title elements aren't "
        "binding."
    )
    print(f"[6845] ✓ Found {len(records)} unique cards in Recommended carousel")
    for i, r in enumerate(records):
        print(f"[6845]   [{i}] {r['title']} • {r['trainer']} • {r['detail']}")


# =========================================================
# FORME-6846 + 6847 — Play carousel video + verify timer counts
#
# Merged into one test (per QA call 2026-05-15): opening a class
# detail without playing leaves the user journey incomplete. Verifying
# both navigation AND playback in a single flow gives end-to-end
# coverage without redundant setup.
#
# Single test covers:
#   - 6846: tap last carousel card → ClassDetailPage loads with
#           matching title (nav verification)
#   - 6847: start session, play 1 min, verify timer decreased ~60s
#           (objective playback-alive check, reframed from Video
#           Quality and Sync)
# =========================================================

@pytest.mark.studio
def test_play_carousel_video_with_timer_check(shared_driver):
    """Tap the last card in the Recommended carousel → ClassDetailPage
    loads → start session → play 1 minute → verify countdown timer
    decreased by ~60s.

    Covers FORME-6846 (carousel video tap navigates to detail) and
    FORME-6847 (playback-is-alive verified via timer tick).

    Why last card (not first): tapping cards[0] doesn't exercise the
    swipe-then-tap path. Inventorying via swipe and tapping the last
    title seen verifies the carousel is scrollable AND that cards
    rendered after swipes remain tappable.
    """
    home = _ensure_your_plan_loaded(shared_driver)

    # =====================================================
    # 6846 — Inventory carousel + tap last card
    # =====================================================
    print(f"\n[6846] Inventorying carousel before tap")
    records = _swipe_carousel_and_collect_records(shared_driver, home)
    assert len(records) > 0, "Carousel is empty — cannot tap a card"

    last_record = records[-1]
    last_title = last_record["title"]
    print(f"[6846] Tapping last card: '{last_title}' "
          f"({last_record['detail']}, {last_record['trainer']})")
    # Precise tap by composite identity. tap_class_by_name does a
    # partial title match which is ambiguous when two cards share a
    # title prefix (e.g. STRENGTH: FULL BODY 20 MIN vs 30 MIN). We
    # walk the cards and click the one matching the full triple.
    if not _tap_card_by_record(shared_driver, home, last_record):
        # Card scrolled off-screen during swipe inventory → swipe back
        # to find it again before failing
        print(f"[6846] Card not currently visible — swiping back to "
              f"find it")
        _swipe_carousel_and_collect_records(shared_driver, home)
        assert _tap_card_by_record(shared_driver, home, last_record), (
            f"Could not find card matching {last_record} after "
            f"inventory swipe. Card may have scrolled off-screen."
        )
    time.sleep(3)

    # 6846 — Verify ClassDetailPage loaded
    class_detail = ClassDetailPage(shared_driver)
    assert class_detail.is_loaded(timeout=10), (
        f"Tapping last carousel card ('{last_title}') did not load "
        f"ClassDetailPage within 10s. Either the tap missed, the "
        f"card scrolled out of view between inventory and tap, or "
        f"navigation is broken."
    )
    title_on_detail = class_detail.get_title()
    print(f"[6846] ✓ ClassDetailPage loaded with title: '{title_on_detail}'")

    # 6846 — Sanity check title match
    assert title_on_detail and last_title.upper() in title_on_detail.upper(), (
        f"ClassDetailPage title '{title_on_detail}' does not match "
        f"the carousel card we tapped: '{last_title}'"
    )
    print(f"[6846] ✓ Detail title matches tapped card")

    # =====================================================
    # 6847 — Start session → handle prompt → wait for player
    # =====================================================
    print(f"\n[6847] Starting session for playback verification")
    class_detail.tap_start_session()

    prompt = AppleWatchPromptPage(shared_driver)
    if prompt.is_showing(timeout=5):
        prompt.dismiss()
        print(f"[6847] Apple Watch prompt dismissed")

    player = PlayerPage(shared_driver)
    player.wait_for_player(timeout=20)
    print(f"[6847] ✓ Player loaded")

    # Skip block preview if present
    if player.is_in_block_preview(timeout=2):
        try:
            player.tap_skip_preview()
            print(f"[6847] Block preview skipped")
            time.sleep(2)
        except Exception as e:
            print(f"[6847] Could not skip block preview: {e}")

    # Wake controls + read initial time
    player.tap_screen()
    time.sleep(1)

    t_start = player.get_class_time_seconds()
    assert t_start is not None, "Could not parse initial class_time"
    print(f"[6847] T_start: {t_start}s remaining")

    # =====================================================
    # 6847 — Wait 60s with 15s polls, then re-read timer
    # =====================================================
    print(f"[6847] Sleeping {PLAYBACK_DURATION_SEC}s (polling at 15s "
          f"intervals to keep Appium session alive)")

    # Poll every 15s instead of one big sleep — UiAutomator2 kills the
    # session after ~60s of inactivity (memory #18).
    POLL_INTERVAL = 15
    elapsed = 0
    while elapsed < PLAYBACK_DURATION_SEC:
        remaining = min(POLL_INTERVAL, PLAYBACK_DURATION_SEC - elapsed)
        time.sleep(remaining)
        elapsed += remaining
        # Touch the driver to keep session alive (read window size is
        # the cheapest no-op call)
        _ = shared_driver.get_window_size()
        print(f"[6847] elapsed={elapsed}s")

    # Re-read timer
    player.tap_screen()  # Wake controls in case they hid
    time.sleep(1)

    t_end = player.get_class_time_seconds()
    assert t_end is not None, "Could not parse class_time after 60s playback"
    decrease = t_start - t_end
    print(f"[6847] T_end: {t_end}s remaining (decreased {decrease}s)")

    assert abs(decrease - EXPECTED_DECREASE_SEC) <= TIMER_TOLERANCE_SEC, (
        f"Expected timer to decrease by ~{EXPECTED_DECREASE_SEC}s "
        f"(±{TIMER_TOLERANCE_SEC}s) over {PLAYBACK_DURATION_SEC}s of "
        f"playback. Actual decrease: {decrease}s. T_start={t_start}, "
        f"T_end={t_end}. Video may be stalled or playback rate is wrong."
    )
    print(f"[6847] ✓ Timer decreased {decrease}s in {PLAYBACK_DURATION_SEC}s "
          f"(playback confirmed alive)")

    # =====================================================
    # Cleanup — end class, submit rating, close summary
    # =====================================================
    print(f"\n[cleanup] Ending session")
    player.tap_end_session()
    time.sleep(3)

    # Rating screen — dismiss via rating submission (uses STUDIO-4289
    # content-desc IDs shipped 2026-05-15). Distinctive 4/5/2 pattern
    # makes automation runs visually identifiable.
    from surfaces.studio_android.pages.rating_page import RatingPage
    rating = RatingPage(shared_driver)
    if rating.is_loaded(timeout=10):
        rating.submit_ratings(session=4, instructor=5, difficulty=2)
        print(f"[cleanup] Rating submitted (session=4, instructor=5, "
              f"difficulty=2)")
        time.sleep(2)

    # Close summary if it appears
    from surfaces.studio_android.pages.summary_page import SummaryPage
    summary = SummaryPage(shared_driver)
    if summary.is_loaded(timeout=5):
        summary.tap_close()
        print(f"[cleanup] Summary closed")
        time.sleep(2)