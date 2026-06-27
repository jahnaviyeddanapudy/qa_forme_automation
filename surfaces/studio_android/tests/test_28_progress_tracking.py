"""test_28_progress_tracking — Studio Progress Tracking 2.0 tests.

Covers five Zebrunner tickets, mirroring the mobile (Android) tests
for the same feature so Studio + mobile have parallel coverage:

  - FORME-6918 — Verify streaks updated when member completes first
                 workout (mirrors mobile test_09_streaks /
                 FORME-1994)
  - FORME-6940 — Verify Week + Month views display Sessions, Minutes
                 Active, Calories for members without Lift
  - FORME-6941 — Verify Life view displays Total Sessions, Total
                 Minutes Active, Total Calories for members without
                 Lift
  - FORME-6944 — Verify member can swipe between Week, Month, Life
                 view (mirrors mobile test_03_progress /
                 FORME-1987 + FORME-2020)
  - FORME-6947 — Verify "Rest up and Recover" card displayed on
                 Rest days and is not tappable (mirrors mobile
                 test_02_weekly_plan / FORME-1975)

Why owner account for all 4 tests:
  - Streak test needs days_checkmarks row which renders only on
    Weekly Plan view (owner with trainer assigned).
  - Rest day card appears only on Weekly Plan view too.
  - Progress section (Week/Month/Life) renders on both views, but
    keeping all 4 tests on owner is simpler than mixing fixtures.

Confirmed element IDs from owner-account dumps (2026-05-20):
  Week view: fragment_progress_week, label_current_streak,
             label_sessions, label_minutes_active, label_calories,
             linear_weight_moved (Lift), days_checkmarks (d1..d7)
  Month view: fragment_progress_month, label_consistency,
              profile_calendar, label_sessions, label_minutes_active,
              label_calories
  Life view: fragment_progress_life, label_total_sessions,
             label_total_minutes_active, label_total_calories_burned

  label_description text distinguishes views:
    Week  → 'VS LAST WEEK'
    Month → 'VS APRIL' (or previous month name)
    Life  → 'MEMBER SINCE <MONTH> <YEAR>'

  Rest day card: text_title='REST UP & RECOVER', text_detail='ALL DAY',
                 no text_trainer.

Run:
    pytest -m studio surfaces/studio/tests/test_28_progress_tracking.py -v -s

Single test:
    pytest -m studio surfaces/studio/tests/test_28_progress_tracking.py \\
        -v -s -k 'rest_day'
"""
import datetime
import re
import time

import pytest

from appium.webdriver.common.appiumby import AppiumBy

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.config import OWNER_PROFILE_INDEX, APP_PACKAGE
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.class_detail_page import ClassDetailPage
from surfaces.studio_android.pages.apple_watch_prompt_page import AppleWatchPromptPage
from surfaces.studio_android.pages.player_page import PlayerPage
from surfaces.studio_android.pages.rating_page import RatingPage
from surfaces.studio_android.pages.summary_page import SummaryPage


# Streak test playback parameters
STREAK_PLAY_PCT = 0.55          # Need ≥55% playback for class to count
STREAK_PLAY_CAP_MINUTES = 20    # Cap to avoid 30-min full runs
POLL_INTERVAL_SEC = 15          # Keep UiAutomator2 session alive


# =========================================================
# Driver fixture (function-scoped — clean state per test)
# =========================================================

@pytest.fixture(scope="function")
def driver():
    if OWNER_PROFILE_INDEX is None:
        pytest.skip(
            "OWNER_PROFILE_INDEX not configured in config_local.py — "
            "Progress Tracking tests require the owner profile with "
            "a Weekly Plan assigned."
        )
    d = _create_studio_driver()
    try:
        login_at_profile_index(
            d, profile_index=OWNER_PROFILE_INDEX, role_label="OWNER"
        )
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass


# =========================================================
# FORME-6944 (+ 6940 + 6941) — Tap between Week, Month, Life
# =========================================================

@pytest.mark.studio
def test_swipe_between_week_month_life(driver):
    """Tap each of Week / Month / Life and verify the right fragment
    + content elements render. Covers FORME-6940 (Week+Month metrics),
    FORME-6941 (Life metrics), FORME-6944 (navigation between views).

    Title says 'swipe' but the actual mechanic is tapping the radio
    button tabs — same as mobile (mobile's test_03_progress uses
    tap_week_tab/tap_month_tab/tap_life_tab too)."""
    home = HomePage(driver)

    home.tap_your_plan_tab()
    home.scroll_to_progress()

    # =====================================================
    # Tabs visible
    # =====================================================
    assert home.is_visible(home.RADIO_WEEK_ID), "Week tab not visible"
    assert home.is_visible(home.RADIO_MONTH_ID), "Month tab not visible"
    assert home.is_visible(home.RADIO_LIFE_ID), "Life tab not visible"
    assert home.is_text_visible("Progress"), (
        "Progress header not visible"
    )
    print(f"[6944] ✓ All three view tabs visible")

    # =====================================================
    # Week view (FORME-6940)
    # =====================================================
    home.tap_week_tab()
    home.wait_seconds(1)
    assert home.is_visible("fragment_progress_week"), (
        "Week fragment not loaded"
    )
    description = home.get_description_label()
    assert "VS LAST WEEK" in description, (
        f"Week view should show 'VS LAST WEEK', got: '{description}'"
    )
    home.scroll_to_id("header_consistency")
    assert home.is_visible("label_current_streak"), (
        "Current streak not visible in Week view"
    )
    assert home.is_visible("days_checkmarks"), (
        "Day checkmarks row not visible in Week view"
    )
    assert home.is_visible("label_sessions"), (
        "Sessions not visible in Week view"
    )
    assert home.is_visible("label_minutes_active"), (
        "Minutes active not visible in Week view"
    )
    assert home.is_visible("label_calories"), (
        "Calories not visible in Week view"
    )
    print(f"[6940] ✓ Week view shows streak + sessions + minutes + "
          f"calories")

    # =====================================================
    # Month view (FORME-6940 cont'd)
    # =====================================================
    home.scroll_up()
    home.tap_month_tab()
    home.wait_seconds(1)
    assert home.is_visible("fragment_progress_month"), (
        "Month fragment not loaded"
    )
    description = home.get_description_label()
    # Mobile checks for 'VS' and not 'WEEK' to ensure we left Week
    # view. Same heuristic works here — Month shows 'VS <MONTH>'.
    assert "VS" in description and "LAST WEEK" not in description, (
        f"Month view should show 'VS <MONTH>', got: '{description}'"
    )
    home.scroll_to_id("label_consistency")
    assert home.is_visible("label_consistency"), (
        "Consistency percentage not visible in Month view"
    )
    assert home.is_visible("profile_calendar"), (
        "Month calendar not visible"
    )
    # Sessions/minutes/calories also present in Month view per dump
    assert home.is_visible("label_sessions"), (
        "Sessions not visible in Month view"
    )
    assert home.is_visible("label_minutes_active"), (
        "Minutes active not visible in Month view"
    )
    assert home.is_visible("label_calories"), (
        "Calories not visible in Month view"
    )
    print(f"[6940] ✓ Month view shows consistency + calendar + metrics")

    # =====================================================
    # Life view (FORME-6941)
    # =====================================================
    home.scroll_up()
    home.tap_life_tab()
    home.wait_seconds(1)
    assert home.is_visible("fragment_progress_life"), (
        "Life fragment not loaded"
    )
    description = home.get_description_label()
    assert "MEMBER SINCE" in description, (
        f"Life view should show 'MEMBER SINCE <MONTH> <YEAR>', "
        f"got: '{description}'"
    )
    home.scroll_to_id("label_total_sessions")
    assert home.is_visible("label_total_sessions"), (
        "Total sessions not visible in Life view"
    )
    assert home.is_visible("label_total_minutes_active"), (
        "Total minutes not visible in Life view"
    )
    assert home.is_visible("label_total_calories_burned"), (
        "Total calories not visible in Life view"
    )
    print(f"[6941] ✓ Life view shows total sessions + minutes + "
          f"calories")

    # =====================================================
    # Switch back to Week (round-trip nav)
    # =====================================================
    home.scroll_up()
    home.tap_week_tab()
    home.wait_seconds(1)
    description = home.get_description_label()
    assert "VS LAST WEEK" in description, (
        f"Did not switch back to Week view, got: '{description}'"
    )
    print(f"[6944] ✓ Navigation Week→Month→Life→Week works")


# =========================================================
# FORME-6918 — Streak updates after workout
# =========================================================

@pytest.mark.studio
def test_streak_updates_after_workout(driver):
    """Verify streak updates when member completes first workout of
    the day. If today's class is already completed, skip the workout
    portion (streak only advances on the FIRST class of a day, so
    completing a second class today wouldn't change the count anyway).

    Mirrors mobile test_09_streaks (FORME-1994) — same branching
    logic, translated to Studio's class-flow page objects.
    """
    home = HomePage(driver)
    studio = StudioTabPage(driver)
    class_detail = ClassDetailPage(driver)
    player = PlayerPage(driver)
    rating = RatingPage(driver)
    summary = SummaryPage(driver)

    # Navigate to Your Plan → Progress → Week view
    home.tap_your_plan_tab()
    home.scroll_to_progress()
    home.tap_week_tab()
    home.wait_seconds(1)
    home.scroll_to_id("days_checkmarks")

    today_id = f"d{datetime.date.today().weekday() + 1}"
    today_state_before = home.get_today_day_state()
    streak_before = home.get_current_streak()
    print(f"\n[6918] Today ({today_id}) state: '{today_state_before}', "
          f"streak: {streak_before}")

    assert today_state_before is not None, (
        f"Could not read today's ({today_id}) day state. Either we're "
        f"not on Week view (scroll/tap issue) or d{{N}} has neither "
        f"image_check nor image_fire child (unexpected — file JIRA)."
    )

    # =====================================================
    # Branch A — today already completed, can't test increment
    # =====================================================
    # Streak only updates on the FIRST class of a day, so running
    # another class today wouldn't change the count. Assert state
    # is internally consistent (today completed → streak ≥ 1) and
    # exit early.
    if today_state_before == "completed":
        print(f"[6918] Today already completed — streak won't change "
              f"on another class today. Asserting streak ≥ 1 and "
              f"exiting.")
        assert streak_before >= 1, (
            f"Today is marked completed (d{{N}} has image_fire) but "
            f"streak shows {streak_before}. Inconsistent state — "
            f"file dev ticket."
        )
        print(f"[6918] ✓ Today completed + streak = {streak_before} "
              f"(consistent)")
        return

    # =====================================================
    # Branch B — today incomplete, complete a class to verify
    # streak increments. Note: streak_before may be 0 (no streak)
    # OR ≥ 1 (consecutive days ending yesterday). Either way,
    # completing today's class should advance the count.
    # =====================================================
    print(f"[6918] Today incomplete — running a class to verify "
          f"streak update (will check {streak_before} → "
          f"{streak_before + 1}+)")

    # Navigate to Studio → FEATURED
    home.tap_studio_tab()
    studio.wait_for_studio_tab()
    studio.tap_subtab("FEATURED")
    home.wait_seconds(2)
    studio.wait_for_card_grid_to_settle()

    # Find the SHORTEST non-CPS class with valid VOD fields. Use the
    # same VOD-filter logic as test_27 (text_title + text_trainer +
    # text_detail + no personal_message_icon). Shortest minimizes
    # the playback portion of the test (5 MIN × 55% = 3 min play vs
    # 20 MIN × 55% = 11 min play).
    chosen_record = None
    app_package = APP_PACKAGE
    for scroll_num in range(5):
        cards = driver.find_elements(
            AppiumBy.ID, f"{app_package}:id/card"
        )
        candidates = []
        for card in cards:
            try:
                title = card.find_element(
                    AppiumBy.ID, f"{app_package}:id/text_title"
                ).get_attribute("text") or ""
                detail = card.find_element(
                    AppiumBy.ID, f"{app_package}:id/text_detail"
                ).get_attribute("text") or ""
                trainer = card.find_element(
                    AppiumBy.ID, f"{app_package}:id/text_trainer"
                ).get_attribute("text") or ""
            except Exception:
                continue
            if not (title.strip() and detail.strip() and trainer.strip()):
                continue
            # Skip CPS cards
            try:
                card.find_element(
                    AppiumBy.ID,
                    f"{app_package}:id/personal_message_icon"
                )
                continue  # CPS
            except Exception:
                pass
            # Match "X MIN" in detail
            match = re.search(r"(\d+)\s*MIN", detail.upper())
            if not match:
                continue
            mins = int(match.group(1))
            candidates.append({
                "title": title.strip(),
                "detail": detail.strip(),
                "trainer": trainer.strip(),
                "mins": mins,
                "element": card,
            })

        if candidates:
            # Pick the shortest class. If multiple have the same
            # min duration, the first encountered wins (stable sort).
            candidates.sort(key=lambda c: c["mins"])
            chosen_record = candidates[0]
            shortest_mins = chosen_record["mins"]
            other_durations = sorted(set(c["mins"] for c in candidates))
            print(f"[6918] scroll {scroll_num}: {len(candidates)} "
                  f"valid VOD cards, durations seen: {other_durations} "
                  f"min — picking shortest: {shortest_mins} min")
            break

        home.scroll_down()
        home.wait_seconds(1)
        studio.wait_for_card_grid_to_settle()

    assert chosen_record is not None, (
        "Could not find a regular VOD class on FEATURED to play"
    )

    print(f"[6918] Picked: '{chosen_record['title']}' "
          f"({chosen_record['mins']} min, {chosen_record['trainer']})")
    chosen_record["element"].click()
    home.wait_seconds(3)
    assert class_detail.is_loaded(timeout=10), (
        "ClassDetailPage did not load after tapping class card"
    )

    # =====================================================
    # Start session → handle Apple Watch prompt → play
    # =====================================================
    class_detail.tap_start_session()
    prompt = AppleWatchPromptPage(driver)
    if prompt.is_showing(timeout=5):
        prompt.dismiss()
        print(f"[6918] Apple Watch prompt dismissed")

    player.wait_for_player(timeout=20)
    print(f"[6918] ✓ Player loaded")

    if player.is_in_block_preview(timeout=2):
        try:
            player.tap_skip_preview()
            print(f"[6918] Block preview skipped")
            time.sleep(2)
        except Exception:
            pass

    # Need to play ≥55% to count as complete, capped at 20 min
    play_minutes = min(
        int(chosen_record["mins"] * STREAK_PLAY_PCT) + 1,
        STREAK_PLAY_CAP_MINUTES,
    )
    play_seconds = play_minutes * 60
    print(f"[6918] Playing for {play_minutes} min "
          f"({STREAK_PLAY_PCT*100:.0f}% of {chosen_record['mins']} min, "
          f"capped at {STREAK_PLAY_CAP_MINUTES})")

    # Wake controls + read initial time (sanity check player is alive)
    player.tap_screen()
    time.sleep(1)
    t_start = player.get_class_time_seconds()
    print(f"[6918] T_start: {t_start}s remaining")

    # Poll-sleep to keep UiAutomator2 alive (memory #18)
    elapsed = 0
    while elapsed < play_seconds:
        chunk = min(POLL_INTERVAL_SEC, play_seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk
        _ = driver.get_window_size()  # cheap no-op call
        print(f"[6918] elapsed={elapsed}s / {play_seconds}s")

    # =====================================================
    # End session → submit rating → close summary
    # =====================================================
    player.tap_screen()
    time.sleep(2)
    if not player.is_visible("button_end_class", timeout=2):
        player.tap_screen()
        time.sleep(2)
    player.tap_end_session()

    if rating.is_loaded(timeout=10):
        rating.submit_ratings(session=4, instructor=5, difficulty=2)
        print(f"[6918] Rating submitted")
        time.sleep(2)

    if summary.is_loaded(timeout=10):
        summary.tap_close()
        print(f"[6918] Summary closed")
        time.sleep(3)

    # =====================================================
    # Verify streak incremented + today flipped to completed
    # =====================================================
    home.tap_your_plan_tab()
    home.scroll_to_progress()
    home.tap_week_tab()
    home.wait_seconds(1)
    home.scroll_to_id("days_checkmarks")

    today_state_after = home.get_today_day_state()
    streak_after = home.get_current_streak()
    print(f"[6918] After: today='{today_state_after}', "
          f"streak={streak_after}")

    assert today_state_after == "completed", (
        f"Today's icon did not flip to 'completed' (image_fire) after "
        f"workout — got '{today_state_after}'. State was "
        f"'{today_state_before}' before. The class playback may not "
        f"have crossed the 55% completion threshold."
    )
    assert streak_after > streak_before, (
        f"Streak did not increase after completing a class: "
        f"before={streak_before}, after={streak_after}"
    )
    print(f"[6918] ✓ Streak {streak_before} → {streak_after} + "
          f"today flipped to completed (image_fire)")


# =========================================================
# FORME-6947 — Rest day card visible and not tappable
# =========================================================

@pytest.mark.studio
def test_rest_day_visible_and_not_tappable(driver):
    """Verify 'REST UP & RECOVER' card appears in the weekly schedule
    and tapping it does NOT navigate away from home.

    Mirrors mobile test_02_weekly_plan / FORME-1975. Precondition
    (per memory #2): owner's weekly plan includes a rest day.
    """
    home = HomePage(driver)

    home.tap_your_plan_tab()
    home.wait_seconds(2)

    # =====================================================
    # Find REST UP & RECOVER card (may need to swipe horizontally)
    # =====================================================
    print(f"\n[6947] Looking for 'REST UP & RECOVER' card")
    found = home.is_text_visible("REST UP & RECOVER", timeout=3)
    if not found:
        print(f"[6947] Not visible on initial view — swiping the "
              f"weekly schedule to find it")
        found = home.swipe_to_find_text(
            "REST UP & RECOVER", direction="left", max_swipes=7
        )
    assert found, (
        "Rest day card not found in weekly schedule. Owner's weekly "
        "plan may not have a rest day assigned this week. Check "
        "trainer assignments."
    )
    assert home.is_text_visible("ALL DAY"), (
        "Rest day 'ALL DAY' detail label not visible alongside "
        "REST UP & RECOVER"
    )
    print(f"[6947] ✓ Rest day card visible with 'ALL DAY' label")

    # =====================================================
    # Tap the rest day card — should be a no-op (stays on home)
    # =====================================================
    print(f"[6947] Tapping rest day card to verify it's not tappable")
    home.tap_class_by_name("REST UP & RECOVER")
    home.wait_seconds(2)

    assert home.is_loaded(), (
        "Tapping rest day card navigated away from home — it should "
        "be a no-op (rest days are not tappable per FORME-6947)"
    )
    assert home.is_text_visible("REST UP & RECOVER"), (
        "Rest day card disappeared after tapping — should remain "
        "visible since the tap is a no-op"
    )
    print(f"[6947] ✓ Tap was a no-op — still on home with card visible")