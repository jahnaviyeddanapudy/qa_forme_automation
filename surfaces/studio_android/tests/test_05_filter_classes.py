"""test_05_filter_classes — Studio filter functionality, parametrized.

Covers FORME-6833 (Studio: Classes — Filters) plus FORME-6679 (no-results
state). All tests in this file share a single driver session
(module-scoped fixture) — login happens once, then tests reuse it.

Coverage philosophy:
  - Max 2 cases per filter category (boundaries: first + last, or
    representative samples).
  - Each verification test scrolls the result list 3 times and checks
    ALL UNIQUE FULLY-BOUND CARDS across initial view + 3 scrolled views.

Cases:
  - LENGTH: 30 MIN, 60 MIN
  - LEVEL: BEGINNER, ADVANCED
  - INSTRUCTORS: KATE S
  - FOCUS: CARDIO, FULL BODY
  - EQUIPMENT: DUMBBELLS, NO EQUIPMENT
  - FORME-6679: filter combo producing 0 results

Card binding state:
  Studio uses a 4-column grid recycler. Cards bind in stages
  (scaffolding → bookmark → title → detail). For verification we
  ONLY consider cards with both title AND detail — those are the
  cards actually visible to the user. Cards in earlier stages are
  recycler scaffolds for rows about to scroll into view.
  See StudioTabPage.find_all_visible_card_records() docstring for
  the full breakdown.

Cleanup model:
  Cleanup runs BEFORE every test. If the Appium session has crashed
  (UiAutomator2 instrumentation died), cleanup detects this and
  raises a fatal error. Without this, subsequent tests would all
  fail with confusing 'Should be on Home' errors when the real
  problem is the dead driver.

Runtime: ~7-8 min for 10 tests if all pass.

Run all filter tests:
    pytest -m studio surfaces/studio/tests/test_05_filter_classes.py -v -s

Run a single parametrized case:
    pytest -m studio surfaces/studio/tests/test_05_filter_classes.py \\
        -v -s -k 'length_30_min'

Run just the no-results test:
    pytest -m studio surfaces/studio/tests/test_05_filter_classes.py \\
        -v -s -k 'no_results'
"""
import pytest

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.filter_page import FilterPage


SCROLL_VERIFY_COUNT = 3


# =========================================================
# MODULE-SCOPED DRIVER
# =========================================================

@pytest.fixture(scope="module")
def shared_driver():
    """Module-scoped driver. Login as first profile once; all filter
    tests in this file share the session. Driver quits at end of
    module."""
    d = _create_studio_driver()
    try:
        login_at_profile_index(d, profile_index=0)
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            # Teardown best-effort. If quit fails, the next pytest run
            # will get a fresh driver anyway — no need to log unless
            # debugging.
            pass


def _is_session_alive(driver):
    """Quick health check: is the Appium session responsive? Returns
    True if a basic command succeeds, False if any exception (which
    typically means the UiAutomator2 instrumentation crashed)."""
    try:
        # Cheapest possible call that touches the driver
        _ = driver.session_id
        # And a real call to the device — session_id is just a Python
        # attribute, doesn't prove the session is alive
        _ = driver.current_package
        return True
    except Exception as e:
        # Real failure signal — print so the user can see WHY the
        # subsequent pytest.fail fired.
        print(f"[health] session check failed: {type(e).__name__}: {e}")
        return False


@pytest.fixture(autouse=True)
def reset_to_clean_studio_tab(shared_driver, request):
    """Run BEFORE every test:
      1. Verify the Appium session is alive — abort hard if dead
      2. Ensure the app is on the Studio tab with no active filter chips

    Always-on for reliability. The session-alive check prevents
    cascading 'Should be on Home' errors when the real problem is
    a crashed UiAutomator2 instrumentation."""
    if not _is_session_alive(shared_driver):
        pytest.fail(
            f"Appium session is dead — UiAutomator2 instrumentation "
            f"likely crashed in a previous test. All remaining tests "
            f"in this module will fail until you restart the Appium "
            f"server. Check Appium server logs for the root cause.",
            pytrace=False,
        )

    home = HomePage(shared_driver)
    studio = StudioTabPage(shared_driver)
    flt = FilterPage(shared_driver)

    if flt.is_open(timeout=1):
        try:
            flt.close()
        except Exception:
            pass

    if home.is_loaded(timeout=2) and not studio.is_loaded(timeout=1):
        try:
            home.tap_studio_tab()
            studio.wait_for_studio_tab()
        except Exception:
            pass

    if studio.is_loaded(timeout=2):
        chips_before = studio.get_all_active_filter_chips()
        if chips_before:
            # Real diagnostic — chips leaked from a prior test, worth knowing.
            print(f"[cleanup] clearing chips: {chips_before}")
        for chip in chips_before[:]:
            try:
                studio.clear_filter(chip)
            except Exception as e:
                print(f"[cleanup] failed to clear chip '{chip}': {e}")

        chips_after = studio.get_all_active_filter_chips()
        if chips_after:
            print(f"[cleanup] WARNING: chips still present after cleanup: "
                  f"{chips_after}")

    yield


# =========================================================
# Helpers
# =========================================================

def _open_filter_overlay(driver):
    """Helper: ensure we're on Studio tab, then open the filter
    overlay. Returns (studio_tab_page, filter_page)."""
    home = HomePage(driver)
    studio = StudioTabPage(driver)

    if not studio.is_loaded(timeout=2):
        assert home.is_loaded(), "Should be on Home if not Studio tab"
        home.tap_studio_tab()
        studio.wait_for_studio_tab()

    studio.tap_filter_button()
    flt = FilterPage(driver)
    flt.wait_for_filter_overlay()
    return studio, flt


def _close_filter_and_wait(studio, flt):
    """Close the filter overlay, then wait for the grid recycler to
    settle so the card tree is stable before we read it."""
    flt.close()
    bound = studio.wait_for_card_grid_to_settle()
    print(f"[grid] settled with {bound} fully-bound cards visible")


def _collect_card_records_with_scroll(studio, scrolls=SCROLL_VERIFY_COUNT):
    """Collect unique fully-bound card records (title, detail, trainer)
    across initial view + N scrolls. Dedupes by (title, detail) tuple.

    Stops scrolling early if a scroll produces no new unique cards."""
    seen = []
    seen_keys = set()  # (title, detail) tuples

    def _add_records(records):
        added = 0
        for r in records:
            key = (r["title"], r["detail"])
            if key not in seen_keys:
                seen_keys.add(key)
                seen.append(r)
                added += 1
        return added

    initial = studio.find_all_visible_card_records()
    n_added = _add_records(initial)
    print(f"[scroll-verify] Initial view: {len(initial)} bound cards, "
          f"{n_added} unique by (title, detail)")

    for i in range(scrolls):
        studio.scroll_content_down()
        # Wait for grid to settle after scroll — same async rebind issue
        studio.wait_for_card_grid_to_settle(max_wait_seconds=2)
        records = studio.find_all_visible_card_records()
        added = _add_records(records)
        print(f"[scroll-verify] After scroll {i+1}: {len(records)} bound cards, "
              f"+{added} new unique (total {len(seen)})")

        if added == 0:
            print(f"[scroll-verify] No new unique cards after scroll {i+1}, "
                  f"stopping early")
            break

    return seen


# =========================================================
# LENGTH FILTERS (2 cases)
# =========================================================

@pytest.mark.studio
@pytest.mark.parametrize("length_value", [
    "30 MIN",
    "60 MIN",
])
def test_filter_by_length(shared_driver, length_value):
    """Filter by LENGTH = <value>. Verify badge, chip on Studio tab,
    and that all unique fully-bound cards contain the length value
    in their text_detail."""
    studio, flt = _open_filter_overlay(shared_driver)

    print(f"\n[filter] Testing LENGTH = '{length_value}'")
    initial_count = flt.get_section_selection_count("LENGTH")
    print(f"[filter] Initial LENGTH selection count: {initial_count}")
    assert initial_count == 0, (
        f"Expected LENGTH count to start at 0, got {initial_count}. "
        f"Other filters may be carrying over from previous tests."
    )

    flt.tap_filter("LENGTH", length_value)
    new_count = flt.get_section_selection_count("LENGTH")
    print(f"[filter] After tap, LENGTH selection count: {new_count}")
    assert new_count == 1, (
        f"LENGTH count should be 1, got {new_count}"
    )

    _close_filter_and_wait(studio, flt)
    assert studio.is_loaded(), "Should be back on Studio tab"

    chips = studio.get_all_active_filter_chips()
    print(f"[filter] Active chips: {chips}")
    assert chips == [length_value], (
        f"Expected exactly ['{length_value}'] chip, got: {chips}"
    )

    records = _collect_card_records_with_scroll(studio)
    print(f"[filter] Verifying {len(records)} unique cards match "
          f"'{length_value}'")

    if records:
        non_matching = [r for r in records if length_value not in r["detail"]]
        if non_matching:
            sample = [(r["title"], r["detail"]) for r in non_matching[:5]]
            assert False, (
                f"Expected all unique cards to contain '{length_value}' "
                f"in detail, but {len(non_matching)} don't: {sample}"
            )

    studio.clear_filter(length_value)
    chips_after = studio.get_all_active_filter_chips()
    print(f"[filter] Chips after clearing '{length_value}': {chips_after}")
    assert length_value not in chips_after, (
        f"Expected '{length_value}' to be removed after tapping chip"
    )


# =========================================================
# LEVEL FILTERS (2 cases)
# =========================================================

@pytest.mark.studio
@pytest.mark.parametrize("level_value", [
    "BEGINNER",
    "ADVANCED",
])
def test_filter_by_level(shared_driver, level_value):
    """Filter by LEVEL = <value>. Verify badge + chip + scroll-verify
    text_detail on all unique fully-bound cards contains the level."""
    studio, flt = _open_filter_overlay(shared_driver)

    print(f"\n[filter] Testing LEVEL = '{level_value}'")
    initial_count = flt.get_section_selection_count("LEVEL")
    print(f"[filter] Initial LEVEL selection count: {initial_count}")
    assert initial_count == 0, (
        f"Expected LEVEL count to start at 0, got {initial_count}"
    )

    flt.tap_filter("LEVEL", level_value)
    new_count = flt.get_section_selection_count("LEVEL")
    print(f"[filter] After tap, LEVEL selection count: {new_count}")
    assert new_count == 1, (
        f"LEVEL count should be 1, got {new_count}"
    )

    _close_filter_and_wait(studio, flt)
    chips = studio.get_all_active_filter_chips()
    print(f"[filter] Active chips: {chips}")
    assert chips == [level_value], (
        f"Expected exactly ['{level_value}'] chip, got: {chips}"
    )

    records = _collect_card_records_with_scroll(studio)
    print(f"[filter] Verifying {len(records)} unique cards match "
          f"'{level_value}'")

    if records:
        non_matching = [r for r in records
                        if level_value not in r["detail"].upper()]
        if non_matching:
            sample = [(r["title"], r["detail"]) for r in non_matching[:5]]
            assert False, (
                f"Expected all unique cards to contain '{level_value}' "
                f"in detail, but {len(non_matching)} don't: {sample}"
            )

    studio.clear_filter(level_value)
    assert level_value not in studio.get_all_active_filter_chips()


# =========================================================
# INSTRUCTORS FILTER (1 case)
# =========================================================

@pytest.mark.studio
def test_filter_by_instructor(shared_driver):
    """Filter by KATE S. Verify badge + chip + scroll-verify
    text_trainer on all unique fully-bound cards matches."""
    studio, flt = _open_filter_overlay(shared_driver)

    target_instructor = "KATE S"
    print(f"\n[filter] Testing INSTRUCTORS = '{target_instructor}'")

    initial_count = flt.get_section_selection_count("INSTRUCTORS")
    print(f"[filter] Initial INSTRUCTORS selection count: {initial_count}")
    assert initial_count == 0, (
        f"Expected INSTRUCTORS count to start at 0, got {initial_count}"
    )

    flt.tap_filter("INSTRUCTORS", target_instructor)
    new_count = flt.get_section_selection_count("INSTRUCTORS")
    print(f"[filter] After tap, INSTRUCTORS selection count: {new_count}")
    assert new_count == 1, (
        f"INSTRUCTORS count should be 1, got {new_count}"
    )

    _close_filter_and_wait(studio, flt)
    chips = studio.get_all_active_filter_chips()
    print(f"[filter] Active chips: {chips}")
    assert chips == [target_instructor], (
        f"Expected exactly ['{target_instructor}'] chip, got: {chips}"
    )

    records = _collect_card_records_with_scroll(studio)
    print(f"[filter] Verifying {len(records)} unique cards have "
          f"trainer matching '{target_instructor}'")

    if records:
        target_lower = target_instructor.lower()
        non_matching = [r for r in records
                        if target_lower not in r["trainer"].lower()]
        if non_matching:
            sample = [(r["title"], r["trainer"]) for r in non_matching[:5]]
            assert False, (
                f"Expected all unique cards to have trainer "
                f"'{target_instructor}', but {len(non_matching)} don't: "
                f"{sample}"
            )

    studio.clear_filter(target_instructor)
    assert target_instructor not in studio.get_all_active_filter_chips()


# =========================================================
# FOCUS FILTER (chip-only verification)
# =========================================================

@pytest.mark.studio
@pytest.mark.parametrize("focus_value", [
    "CARDIO",
    "FULL BODY",
])
def test_filter_by_focus(shared_driver, focus_value):
    """Filter by FOCUS = <value>. FOCUS isn't visible on cards, so
    we verify badge + chip only."""
    studio, flt = _open_filter_overlay(shared_driver)

    print(f"\n[filter] Testing FOCUS = '{focus_value}'")
    initial_count = flt.get_section_selection_count("FOCUS")
    assert initial_count == 0, (
        f"Expected FOCUS count to start at 0, got {initial_count}"
    )

    flt.tap_filter("FOCUS", focus_value)
    new_count = flt.get_section_selection_count("FOCUS")
    print(f"[filter] After tap, FOCUS selection count: {new_count}")
    assert new_count == 1, (
        f"FOCUS count should be 1, got {new_count}"
    )

    _close_filter_and_wait(studio, flt)
    chips = studio.get_all_active_filter_chips()
    assert chips == [focus_value], (
        f"Expected exactly ['{focus_value}'] chip, got: {chips}"
    )

    bound = studio.get_bound_card_count()
    print(f"[filter] {bound} bound cards visible after FOCUS={focus_value}")

    studio.clear_filter(focus_value)
    assert focus_value not in studio.get_all_active_filter_chips()


# =========================================================
# EQUIPMENT FILTER (2 cases)
# =========================================================

@pytest.mark.studio
@pytest.mark.parametrize("equipment_value", [
    "DUMBBELLS",
    "NO EQUIPMENT",
])
def test_filter_by_equipment(shared_driver, equipment_value):
    """Filter by EQUIPMENT. Equipment isn't visible on cards, so
    verify badge + chip only."""
    studio, flt = _open_filter_overlay(shared_driver)

    print(f"\n[filter] Testing EQUIPMENT = '{equipment_value}'")
    initial_count = flt.get_section_selection_count("EQUIPMENT")
    assert initial_count == 0, (
        f"Expected EQUIPMENT count to start at 0, got {initial_count}"
    )

    flt.tap_filter("EQUIPMENT", equipment_value)
    new_count = flt.get_section_selection_count("EQUIPMENT")
    print(f"[filter] After tap, EQUIPMENT selection count: {new_count}")
    assert new_count == 1, (
        f"EQUIPMENT count should be 1, got {new_count}"
    )

    _close_filter_and_wait(studio, flt)
    chips = studio.get_all_active_filter_chips()
    assert chips == [equipment_value], (
        f"Expected exactly ['{equipment_value}'] chip, got: {chips}"
    )

    bound = studio.get_bound_card_count()
    print(f"[filter] {bound} bound cards visible after "
          f"EQUIPMENT={equipment_value}")

    studio.clear_filter(equipment_value)
    assert equipment_value not in studio.get_all_active_filter_chips()


# =========================================================
# FORME-6679 — Filter combo producing 0 results
# =========================================================

# Filter combos to try in order. Each is a list of (section, value)
# tuples — applied cumulatively (combo 1 first; if results found, ALSO
# add combo 2's filters; etc.). Selected for high likelihood of
# producing 0 matches when combined.
#
# Strategy:
#   - Combo 1 (seed): 25 MIN + SOUND BATH — observed to produce 0
#     results on Silvanus's Studio (per the dump that motivated this
#     test). Light combo so if the Studio's content library covers it,
#     we can layer more filters on top.
#   - Each subsequent combo adds an increasingly narrow filter to
#     drive results to 0. Caps at 4 cumulative filters total.
_NO_RESULTS_FILTER_LADDER = [
    [("LENGTH", "25 MIN"), ("FOCUS", "SOUND BATH")],
    [("LEVEL", "ADVANCED")],
    [("EQUIPMENT", "DUMBBELLS")],
]


def _apply_filter_combo(flt, combo):
    """Apply a list of (section, value) filter taps inside an open
    filter overlay. Logs each tap."""
    for section, value in combo:
        print(f"[6679] Applying filter: {section} = {value}")
        flt.tap_filter(section, value)


@pytest.mark.studio
def test_filter_combo_no_results(shared_driver):
    """FORME-6679: Verify the no-results UI displays correctly when an
    active filter combination produces zero matching classes, and that
    tapping RESET FILTERS returns the Studio tab to a normal populated
    state.

    Strategy:
      1. Apply seed filter combo (25 MIN + SOUND BATH FOCUS)
      2. If results still found, layer additional narrowing filters
         from _NO_RESULTS_FILTER_LADDER until count drops to 0
      3. Verify no-results UI: fragment_no_classes visible, headline
         text, subline text, RESET FILTERS button visible
      4. Tap RESET FILTERS
      5. Verify recovery: chips cleared, bound cards reappear

    Notes:
      - Cleanup fixture (reset_to_clean_studio_tab) clears any leftover
        chips before this test starts and after it finishes.
      - The "try-then-fall-back" approach handles different Studios
        having different content libraries — what produces 0 results
        on one Studio may return 1+ on another.
    """
    studio, flt = _open_filter_overlay(shared_driver)

    print(f"\n[6679] Starting filter combo test")

    # Step 1+2: Apply filters incrementally until we reach 0 results
    applied_chips = []
    bound_count = None

    for combo_index, combo in enumerate(_NO_RESULTS_FILTER_LADDER):
        print(f"\n[6679] Applying combo #{combo_index + 1}: {combo}")
        _apply_filter_combo(flt, combo)
        applied_chips.extend(value for _, value in combo)

        # Close overlay to see live result count
        _close_filter_and_wait(studio, flt)

        # Check if grid is empty
        no_results = studio.is_no_results_state(timeout=2)
        bound_count = studio.get_bound_card_count()
        print(f"[6679] After combo #{combo_index + 1}: "
              f"no_results_visible={no_results}, "
              f"bound_cards={bound_count}")

        if no_results:
            print(f"[6679] ✓ Reached 0-result state with "
                  f"{len(applied_chips)} cumulative filter(s)")
            break

        # Still have results — re-open overlay for next combo
        if combo_index < len(_NO_RESULTS_FILTER_LADDER) - 1:
            studio.tap_filter_button()
            flt.wait_for_filter_overlay()
    else:
        # We exhausted the ladder without reaching 0 results — this
        # means the Studio's content library covers everything we tried.
        # That's a real test failure (we couldn't find any combo that
        # produces 0), so we fail clearly and ask for help expanding
        # the ladder.
        pytest.fail(
            f"Could not produce a 0-results state on this Studio after "
            f"applying {len(applied_chips)} cumulative filters: "
            f"{applied_chips}. Final bound card count: {bound_count}. "
            f"Either the Studio's content library is unusually broad, "
            f"or _NO_RESULTS_FILTER_LADDER needs to be extended with "
            f"more aggressive filters."
        )

    # Step 3: Verify no-results UI elements
    print(f"\n[6679] Verifying no-results UI elements")
    assert studio.is_no_results_state(), (
        f"fragment_no_classes should be visible after applying "
        f"{applied_chips}"
    )
    print(f"[6679] ✓ fragment_no_classes visible")

    messages = studio.get_no_results_messages()
    print(f"[6679] No-results messages: {messages}")
    assert len(messages) >= 2, (
        f"Expected at least 2 text messages in fragment_no_classes "
        f"(headline + subline), got {len(messages)}: {messages}"
    )

    # Verify headline (lenient match — exact text may vary by build)
    headline_text = studio.NO_CLASSES_HEADLINE_TEXT
    headline_found = any(headline_text in m for m in messages)
    assert headline_found, (
        f"Expected a message containing '{headline_text}' on the "
        f"no-results fragment. Got messages: {messages}"
    )
    print(f"[6679] ✓ Headline message present "
          f"(contains '{headline_text}')")

    # Verify subline
    subline_fragment = studio.NO_CLASSES_SUBLINE_TEXT
    subline_found = any(subline_fragment in m for m in messages)
    assert subline_found, (
        f"Expected a message containing '{subline_fragment}' on the "
        f"no-results fragment. Got messages: {messages}"
    )
    print(f"[6679] ✓ Subline message present "
          f"(contains '{subline_fragment}')")

    # Verify RESET FILTERS button is visible
    assert studio.is_visible(studio.BUTTON_RESET_FILTERS_ID, timeout=2), (
        f"RESET FILTERS button ({studio.BUTTON_RESET_FILTERS_ID}) "
        f"should be visible on the no-results fragment"
    )
    # Also verify the label text is "RESET FILTERS"
    reset_label_text = studio.get_text(studio.LABEL_RESET_FILTERS_ID)
    print(f"[6679] Reset button label text: '{reset_label_text}'")
    assert reset_label_text == studio.RESET_FILTERS_BUTTON_TEXT, (
        f"Expected reset button label '{studio.RESET_FILTERS_BUTTON_TEXT}', "
        f"got '{reset_label_text}'"
    )
    print(f"[6679] ✓ RESET FILTERS button visible with correct label")

    # Step 4: Tap RESET FILTERS
    print(f"\n[6679] Tapping RESET FILTERS")
    studio.tap_reset_filters()
    studio.wait_for_card_grid_to_settle()

    # Step 5: Verify recovery
    print(f"\n[6679] Verifying recovery after reset")

    # No-results fragment should be gone
    assert not studio.is_no_results_state(timeout=2), (
        f"fragment_no_classes should NOT be visible after tapping "
        f"RESET FILTERS — the Studio tab should be back to a "
        f"populated state"
    )
    print(f"[6679] ✓ fragment_no_classes no longer visible")

    # Active filter chips should be cleared (or at most 1 default
    # sub-tab chip — depends on Studio behavior post-reset)
    chips_after_reset = studio.get_all_active_filter_chips()
    print(f"[6679] Active chips after reset: {chips_after_reset}")
    assert len(chips_after_reset) <= 1, (
        f"After RESET FILTERS, expected 0 or 1 chips (the default "
        f"sub-tab) but got {len(chips_after_reset)}: {chips_after_reset}"
    )

    # Bound cards should reappear
    bound_after = studio.get_bound_card_count()
    print(f"[6679] Bound cards after reset: {bound_after}")
    assert bound_after >= 1, (
        f"After RESET FILTERS, expected at least 1 fully-bound class "
        f"card to be visible, got {bound_after}. The Studio tab may "
        f"not have recovered properly."
    )
    print(f"[6679] ✓ {bound_after} bound class card(s) visible after reset")