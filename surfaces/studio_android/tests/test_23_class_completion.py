"""test_23_class_completion — Studio class completion suite (File B).

File B of the player-tests split. Heavy: plays a class to 60% of its
duration (~6 min for a 10-min class), then exercises:

  - FORME-6605 — Progress block + countdown timer reset on RR/FF
                 (verified mid-playback, NOT post-completion)
  - FORME-6603 — Program marked complete after >= 50% executed
                 (verified by navigating back to Program detail and
                  confirming the class card now has text_complete
                  badge)
  - FORME-6658 — Workout Summary screen renders with expected elements
  - FORME-6729 — Post-Session Survey after Program class (same rating
                 screen as 6739)
  - FORME-6739 — Post-Session Survey after VOD class

Scope decisions (per QA call):
  - FF skips do NOT count toward 50% completion — must play real time.
  - Play to 60% (not exact 50%) for safety buffer.
  - Rating screen verified for both structure (sections appear, submit
    button visible) AND submission. After STUDIO-4289 shipped
    (2026-05-15), the rating stars have content-desc accessibility IDs,
    so we tap a middle rating in each visible section and submit. The
    submit transitions to SummaryPage cleanly — no tap-outside trick
    needed.

Architecture:
  - Module-scoped fixture handles the long-running class playback.
  - Single test function covers the full flow (mid-class + post-class
    verifications are tightly coupled in time; splitting would require
    re-playing the class for each test).

Poll interval reasoning:
  Originally tried 60s polls to minimize chatter, but Appium's
  UiAutomator2 instrumentation kills itself after ~60s of inactivity.
  A 60s wait between Appium calls causes the session to die mid-test.
  Use 15s polls — keeps the session alive and still gives meaningful
  progress signals (a 15s decrease over 15s wall-clock proves playback
  is alive).

Runtime: ~7-8 min for a 10-min class.

Run:
    pytest -m studio surfaces/studio/tests/test_23_class_completion.py -v -s --timeout=900
"""
import time

import pytest

from appium.webdriver.common.appiumby import AppiumBy

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.program_detail_page import ProgramDetailPage
from surfaces.studio_android.pages.class_detail_page import ClassDetailPage
from surfaces.studio_android.pages.apple_watch_prompt_page import AppleWatchPromptPage
from surfaces.studio_android.pages.player_page import PlayerPage
from surfaces.studio_android.pages.rating_page import RatingPage
from surfaces.studio_android.pages.summary_page import SummaryPage
from surfaces.studio_android.pages.profile_page import ProfilePage


# Class playback target: 60% of class duration (50% threshold + buffer)
COMPLETION_TARGET_PCT = 0.60

# Sanity-poll interval during long playback. Set to 15s (not 60s)
# because UiAutomator2 instrumentation on Studio kills the Appium
# session if there's no driver activity for ~60s. Frequent polls
# keep the session alive AND give faster failure detection.
PLAYBACK_POLL_INTERVAL_SEC = 15

# Tolerance for FF/RW time jump verification (single tap).
TIME_TOLERANCE_SEC = 3
TIME_JUMP_PER_TAP = 15


# =========================================================
# MODULE-SCOPED FIXTURE — one class-completion session
# =========================================================

@pytest.fixture(scope="module")
def completed_class_session(request):
    """Set up a full class-completion session and yield state for the
    test to use. Teardown: best-effort driver.quit()."""
    driver = _create_studio_driver()
    state = {"driver": driver, "class_title": None, "duration_sec": None}

    try:
        login_at_profile_index(driver, profile_index=0)

        home = HomePage(driver)
        studio = StudioTabPage(driver)
        home.wait_for_home()
        home.tap_studio_tab()
        studio.wait_for_studio_tab()

        # Force scroll-to-top reset
        studio.tap_subtab("FEATURED")
        studio.wait_seconds(1)
        studio.tap_subtab("PROGRAMS")
        studio.wait_seconds(2)

        # Tap VIEW CLASSES on first Program with the button
        program_cards = studio.find_program_cards()
        target_program = None
        for card in program_cards:
            try:
                card.find_element(
                    "id",
                    f"{studio.APP_PACKAGE}:id/{studio.BUTTON_VIEW_CLASSES_ID}",
                )
                target_program = card
                break
            except Exception:
                continue
        if target_program is None:
            raise RuntimeError(
                "No Program card with button_view_classes found"
            )
        studio.tap_view_classes_on_card(target_program)

        program_detail = ProgramDetailPage(driver)
        program_detail.wait_for_loaded()

        # Find first non-completed class
        raw_cards = program_detail.find_all_by_id(program_detail.CARD_ID)
        target_class_index = None
        target_class_title = None
        for i, card in enumerate(raw_cards):
            try:
                title_el = card.find_element(
                    AppiumBy.ID,
                    f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_TITLE_ID}",
                )
                title = (title_el.get_attribute("text") or "").strip()
                card.find_element(
                    AppiumBy.ID,
                    f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_DETAIL_ID}",
                )
            except Exception:
                continue

            completed = card.find_elements(
                AppiumBy.ID,
                f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_COMPLETE_ID}",
            )
            if completed:
                continue

            target_class_index = i
            target_class_title = title
            break

        if target_class_index is None:
            raise RuntimeError(
                "All visible classes are completed — need a fresh class "
                "to play. Either use a different Program or reset "
                "completion state."
            )

        state["class_title"] = target_class_title
        print(f"\n[setup] Target class: '{target_class_title}' "
              f"(index {target_class_index})")

        raw_cards[target_class_index].click()
        time.sleep(2)

        class_detail = ClassDetailPage(driver)
        class_detail.wait_for_class_detail()
        print(f"[setup] Class detail loaded: '{class_detail.get_title()}' "
              f"({class_detail.get_info_string()})")

        class_detail.tap_start_session()

        prompt = AppleWatchPromptPage(driver)
        if prompt.is_showing(timeout=5):
            prompt.dismiss()
            print(f"[setup] Apple Watch prompt dismissed")

        player = PlayerPage(driver)
        player.wait_for_player(timeout=20)
        print(f"[setup] Player loaded — variant: "
              f"{player.get_player_variant()}, "
              f"class_time: {player.get_class_time()}")

        if player.is_in_block_preview(timeout=2):
            try:
                player.tap_skip_preview()
                print(f"[setup] Skipped block preview")
                time.sleep(2)
            except Exception as e:
                print(f"[setup] Could not skip block preview: {e}")

        player.tap_screen()

        duration_sec = player.get_class_time_seconds()
        if duration_sec is None or duration_sec < 30:
            raise RuntimeError(
                f"Could not parse initial class_time, or class is "
                f"shorter than 30s. Got: {player.get_class_time()}"
            )
        state["duration_sec"] = duration_sec
        print(f"[setup] Initial duration_sec: {duration_sec} "
              f"(~{duration_sec//60} min {duration_sec%60} sec)")
        print(f"[setup] Target play time: "
              f"{int(duration_sec * COMPLETION_TARGET_PCT)}s "
              f"({COMPLETION_TARGET_PCT*100:.0f}% of duration)")

        yield state

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"[teardown] driver.quit failed: {e}")


# =========================================================
# Helpers
# =========================================================

def _wake_controls_if_hidden(player):
    """Ensure player controls are visible before a read+tap sequence."""
    if not player.are_controls_visible(timeout=1):
        player.tap_screen()


def _play_until_60_percent(player, total_duration_sec):
    """Wait for elapsed playback to reach 60% of total duration. Polls
    every PLAYBACK_POLL_INTERVAL_SEC (15s) to keep the Appium session
    alive — UiAutomator2 kills the session after ~60s of inactivity.

    Verifies class_time is decreasing between polls (class is actually
    playing). If countdown stalls, tries a single recovery attempt
    (tap screen + tap play).
    """
    target_remaining_sec = int(total_duration_sec * (1 - COMPLETION_TARGET_PCT))
    expected_decrease_per_poll = PLAYBACK_POLL_INTERVAL_SEC
    min_decrease_per_poll = int(PLAYBACK_POLL_INTERVAL_SEC * 0.5)  # 7-8s = stalled

    print(f"\n[play-loop] Polling every {PLAYBACK_POLL_INTERVAL_SEC}s "
          f"until class_time <= {target_remaining_sec}s remaining "
          f"({COMPLETION_TARGET_PCT*100:.0f}% played)")

    last_remaining = player.get_class_time_seconds()
    if last_remaining is None:
        raise RuntimeError("Could not parse class_time at start of poll loop")
    print(f"[play-loop] Starting at {last_remaining}s remaining")

    poll_count = 0
    # Safety cap: total duration / poll interval * 2 = comfortable upper
    # bound. For 10 min class at 15s polls: 80 polls = 20 min real time.
    max_polls = int(total_duration_sec / PLAYBACK_POLL_INTERVAL_SEC) * 2

    while last_remaining > target_remaining_sec:
        if poll_count >= max_polls:
            raise RuntimeError(
                f"Exceeded max poll count ({max_polls}) without reaching "
                f"60% completion. Currently at {last_remaining}s remaining, "
                f"target was {target_remaining_sec}s."
            )

        time.sleep(PLAYBACK_POLL_INTERVAL_SEC)
        poll_count += 1

        current_remaining = player.get_class_time_seconds()
        if current_remaining is None:
            print(f"[play-loop] poll {poll_count}: could not parse "
                  f"class_time — assuming still playing")
            continue

        decrease = last_remaining - current_remaining
        # Log every 4th poll to keep output readable (~1 line per minute)
        if poll_count % 4 == 1 or current_remaining <= target_remaining_sec:
            print(f"[play-loop] poll {poll_count}: {current_remaining}s "
                  f"remaining (decreased {decrease}s in last "
                  f"{PLAYBACK_POLL_INTERVAL_SEC}s)")

        # Verify class is actually playing — decrease should be close
        # to the poll interval. Less than half = stalled.
        if decrease < min_decrease_per_poll:
            print(f"[play-loop] WARNING: countdown stalled "
                  f"(decrease={decrease}s, expected ~"
                  f"{expected_decrease_per_poll}s). Attempting recovery.")
            try:
                player.tap_screen()
                time.sleep(0.5)
                # tap_play_pause is idempotent in effect from our POV:
                # if playing → pauses → next poll detects stall again
                #            → we won't escape this branch
                # if paused → resumes → next poll shows progress
                # We rely on the second case being typical when stalled.
                player.tap_play()
                time.sleep(2)
            except Exception as e:
                print(f"[play-loop] Recovery attempt failed: {e}")

            current_remaining = player.get_class_time_seconds()
            if current_remaining is None or current_remaining >= last_remaining:
                raise RuntimeError(
                    f"Class playback appears stalled. Last remaining "
                    f"{last_remaining}s, after recovery attempt "
                    f"{current_remaining}s. Test cannot continue."
                )

        last_remaining = current_remaining

    print(f"[play-loop] ✓ Reached target: {last_remaining}s remaining "
          f"(<= {target_remaining_sec}s) after {poll_count} polls")


# =========================================================
# Main test — full class completion flow
# =========================================================

@pytest.mark.studio
def test_class_completion_full_flow(completed_class_session):
    """End-to-end class completion: play to 60%, end, verify rating
    screen, submit a default rating, verify summary, navigate back to
    Program detail, verify class marked completed.

    Covers FORME-6605, 6729, 6739, 6658, 6603 in one flow because
    they're tightly coupled in time."""
    driver = completed_class_session["driver"]
    class_title = completed_class_session["class_title"]
    duration_sec = completed_class_session["duration_sec"]

    player = PlayerPage(driver)
    rating = RatingPage(driver)
    summary = SummaryPage(driver)
    studio = StudioTabPage(driver)
    program_detail = ProgramDetailPage(driver)

    # =====================================================
    # FORME-6605 — Mid-playback FF/RW updates countdown timer
    # =====================================================
    print(f"\n{'='*60}\n[6605] Mid-playback FF/RW progress check\n{'='*60}")
    _wake_controls_if_hidden(player)

    t0 = player.get_class_time_seconds()
    assert t0 is not None, "Could not parse class_time at T0 (pre-FF)"
    print(f"[6605] T0 (pre-FF): {t0}s remaining")

    player.tap_fast_forward()
    time.sleep(0.3)
    t1 = player.get_class_time_seconds()
    assert t1 is not None, "Could not parse class_time at T1 (post-FF)"
    print(f"[6605] T1 (post-FF): {t1}s remaining (delta: {t0 - t1}s)")

    ff_delta = t0 - t1
    assert abs(ff_delta - TIME_JUMP_PER_TAP) <= TIME_TOLERANCE_SEC, (
        f"FF tap should decrease class_time by ~{TIME_JUMP_PER_TAP}s "
        f"(±{TIME_TOLERANCE_SEC}s). Actual: {ff_delta}s. "
        f"T0={t0}, T1={t1}. Progress block/timer may not be updating "
        f"on FF."
    )
    print(f"[6605] ✓ Timer correctly updated on FF")

    player.tap_rewind()
    time.sleep(0.3)
    t2 = player.get_class_time_seconds()
    assert t2 is not None, "Could not parse class_time at T2 (post-RW)"
    print(f"[6605] T2 (post-RW): {t2}s remaining (delta: {t2 - t1}s)")

    rw_delta = t2 - t1
    assert abs(rw_delta - TIME_JUMP_PER_TAP) <= TIME_TOLERANCE_SEC, (
        f"RW tap should increase class_time by ~{TIME_JUMP_PER_TAP}s "
        f"(±{TIME_TOLERANCE_SEC}s). Actual: {rw_delta}s. "
        f"T1={t1}, T2={t2}. Progress block/timer may not be updating "
        f"on RW."
    )
    print(f"[6605] ✓ Timer correctly updated on RW")

    # =====================================================
    # PLAY TO 60%
    # =====================================================
    _play_until_60_percent(player, duration_sec)

    # =====================================================
    # END SESSION
    # =====================================================
    print(f"\n{'='*60}\n[end] Tapping END SESSION\n{'='*60}")
    _wake_controls_if_hidden(player)
    player.tap_end_session()
    time.sleep(3)

    # =====================================================
    # FORME-6729 + 6739 — Rating screen appears + submission
    # =====================================================
    print(f"\n{'='*60}\n[6729/6739] Verify rating screen\n{'='*60}")
    assert rating.is_loaded(timeout=10), (
        "Rating screen did not appear within 10s of tapping END SESSION. "
        "Expected button_submit element to be visible."
    )
    print(f"[6729/6739] ✓ Rating screen loaded")

    sections = rating.get_section_titles()
    print(f"[6729/6739] Visible sections: {sections}")
    assert len(sections) >= 2, (
        f"Expected at least 2 rating sections (Session + Difficulty), "
        f"found {len(sections)}: {sections}"
    )
    assert "Session" in sections, (
        f"Session rating section should be visible. Got: {sections}"
    )
    assert "Difficulty For You" in sections, (
        f"Difficulty For You rating section should be visible. Got: {sections}"
    )
    print(f"[6729/6739] ✓ Session + Difficulty sections present")

    variant = rating.get_variant()
    print(f"[6729/6739] Rating variant: {variant}")

    # =====================================================
    # Submit a default rating (3rd star in each visible section).
    # Requires STUDIO-4289 fix shipped (content-desc IDs on stars).
    # Transitions cleanly to SummaryPage — no tap-outside trick needed.
    # =====================================================
    print(f"[6729/6739] Submitting ratings: session=4, instructor=5, "
          f"difficulty=2 (distinctive pattern for visual ID of "
          f"automation runs)")
    rating.submit_ratings(session=4, instructor=5, difficulty=2)
    print(f"[6729/6739] ✓ Rating submitted")
    time.sleep(2)

    # =====================================================
    # FORME-6658 — Summary screen
    # =====================================================
    print(f"\n{'='*60}\n[6658] Verify summary screen\n{'='*60}")
    assert summary.is_loaded(timeout=10), (
        "Summary screen did not become visible within 10s of submitting "
        "rating. Expected text_header ('YOUR FORME WEEK') to be visible."
    )
    print(f"[6658] ✓ Summary screen loaded")

    summary_title = summary.get_class_title()
    print(f"[6658] Class title on summary: '{summary_title}'")
    assert summary_title, "Summary screen has empty class title"

    assert class_title.upper() in summary_title.upper(), (
        f"Summary title '{summary_title}' does not match the class we "
        f"played: '{class_title}'"
    )
    print(f"[6658] ✓ Summary title matches played class")

    active_time = summary.get_active_time()
    active_time_sec = summary.get_active_time_seconds()
    print(f"[6658] Active time: '{active_time}' ({active_time_sec}s)")
    assert active_time and active_time_sec is not None, (
        f"Summary should show active time in MM:SS format. "
        f"Got raw: '{active_time}'"
    )
    assert 0 < active_time_sec < duration_sec * 2, (
        f"Active time ({active_time_sec}s) seems implausible vs class "
        f"duration ({duration_sec}s)"
    )
    print(f"[6658] ✓ Active time looks plausible")

    # =====================================================
    # Close summary. Studio's observed behavior: returns to the SAME
    # ProgramDetailPage the class was launched from. No navigation
    # needed — just verify we landed there.
    #
    # Fallbacks for other landing states (Studio tab / Home /
    # ProfileActivity) preserved as best-effort — would require
    # re-navigating to PROGRAMS and tapping into the program.
    # =====================================================
    print(f"\n{'='*60}\n[nav] Closing summary, returning to Program detail\n{'='*60}")
    summary.tap_close()
    time.sleep(5)  # Let Studio settle on the post-summary screen

    home = HomePage(driver)
    profile = ProfilePage(driver)

    if program_detail.is_loaded(timeout=5):
        print(f"[nav] ✓ Landed back on Program detail (Studio's "
              f"post-summary behavior)")
    else:
        # Studio dropped us somewhere else — try to recover.
        print(f"[nav] Not on Program detail after summary close — "
              f"attempting fallback navigation")

        landed = None
        for attempt in range(3):
            if studio.is_loaded(timeout=2):
                landed = "studio"
                break
            if home.is_loaded(timeout=2):
                landed = "home"
                break
            if profile.is_loaded(timeout=2):
                landed = "profile"
                break
            time.sleep(2)
            print(f"[nav] attempt {attempt + 1}: still in transition")

        if landed is None:
            try:
                current_activity = driver.current_activity
                current_package = driver.current_package
            except Exception as e:
                current_activity = f"<unavailable: {e}>"
                current_package = f"<unavailable: {e}>"
            raise RuntimeError(
                f"After summary close, did not land on Program detail, "
                f"Studio tab, Home, or ProfileActivity. Foreground: "
                f"package={current_package}, activity={current_activity}."
            )

        print(f"[nav] Landed on: {landed} — navigating to Program detail")
        if landed == "profile":
            login_at_profile_index(driver, profile_index=0)
            home.wait_for_home()
            home.tap_studio_tab()
            studio.wait_for_studio_tab()
        elif landed == "home":
            home.tap_studio_tab()
            studio.wait_for_studio_tab()

        # Now on Studio tab — navigate to PROGRAMS and re-enter the program
        studio.tap_subtab("FEATURED")
        studio.wait_seconds(1)
        studio.tap_subtab("PROGRAMS")
        studio.wait_seconds(2)

        program_cards = studio.find_program_cards()
        target_program = None
        for card in program_cards:
            try:
                card.find_element(
                    "id",
                    f"{studio.APP_PACKAGE}:id/{studio.BUTTON_VIEW_CLASSES_ID}",
                )
                target_program = card
                break
            except Exception:
                continue
        assert target_program is not None, (
            "After class completion + fallback nav, could not find "
            "Program card to re-enter"
        )
        studio.tap_view_classes_on_card(target_program)
        program_detail.wait_for_loaded()
        print(f"[nav] ✓ Back on Program detail via fallback nav")

    # =====================================================
    # FORME-6603 — Verify class is marked completed
    # =====================================================
    print(f"\n{'='*60}\n[6603] Verify class is marked completed\n{'='*60}")
    print(f"[6603] Looking for class titled: '{class_title}'")

    raw_cards = program_detail.find_all_by_id(program_detail.CARD_ID)
    matched_card = None
    for card in raw_cards:
        try:
            title_el = card.find_element(
                AppiumBy.ID,
                f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_TITLE_ID}",
            )
            card_title = (title_el.get_attribute("text") or "").strip()
            if card_title == class_title:
                matched_card = card
                break
        except Exception:
            continue

    assert matched_card is not None, (
        f"After class completion, could not find class '{class_title}' "
        f"in Program detail recycler. May be off-screen — would need "
        f"scrolling to find."
    )
    print(f"[6603] ✓ Found class card '{class_title}'")

    completed_els = matched_card.find_elements(
        AppiumBy.ID,
        f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_COMPLETE_ID}",
    )
    assert len(completed_els) > 0, (
        f"Class '{class_title}' does not have text_complete badge after "
        f"playing to {COMPLETION_TARGET_PCT*100:.0f}% completion. "
        f"FORME-6603 says program should mark complete at >= 50%."
    )
    print(f"[6603] ✓ Class shows text_complete badge (marked COMPLETED)")

    total, completed = program_detail.get_class_counts()
    print(f"[6603] Program counts now: {completed}/{total} completed")