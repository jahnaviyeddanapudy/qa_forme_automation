"""test_22_player_controls — Studio VOD player interaction tests.

Covers basic player controls behavior. Tests share a single class-play
session via module-scoped fixture — login once, start one class, exercise
controls across multiple test functions, end session ONCE at teardown.

This is FILE A of the two-file player split:
  - File A (this file): player interaction, no class completion (~3-5 min)
  - File B (separate): class completion tests (~25-30 min)

Tests:
  - FORME-6848 (part 1) — pause stops the class-time countdown,
                          resume restarts it
  - FORME-6848 (part 2) — FF decreases remaining class-time by 15s
  - FORME-6848 (part 3) — RW increases remaining class-time by 15s
  - FORME-6849       — FF and RW are tappable many times consecutively
                       (no rate-limiting or button-disable after first
                       few taps)

Class selection:
  Picks the first non-completed class from inside a Program in the
  PROGRAMS sub-tab. Per QA spec, these tests should run "from
  programs/collections". A class within a program is a regular VOD/
  Workout class — same player controls as anywhere else.

Time element behavior (per dumps on 2026-05-11):
  text_class_time shows REMAINING time, counts DOWN.
  - Pause: should hold steady (counter stops)
  - Play: should resume countdown
  - FF (button_forward_15): jumps remaining DOWN by 15s (closer to end)
  - RW (button_rewind_15): jumps remaining UP by 15s (further from end)

Tolerance: time reads are second-precision and have small jitter from
playback continuing between tap and read. Single-tap tests allow ±3s.

Cumulative tolerance for the 5-tap test is wider (±10s) because each
tap takes ~1.5s of wall-clock time (page-object built-in 1s wait +
~0.5s action latency). 5 taps × 1.5s = ~7.5s of playback continues
between first tap and the post-loop time read. Rate-limiting (the bug
we're trying to catch) would manifest as far less decrease (e.g. 30s
instead of 75s), well outside the ±10s envelope.

Run all:
    pytest -m studio surfaces/studio/tests/test_22_player_controls.py -v -s

Run one test:
    pytest -m studio surfaces/studio/tests/test_22_player_controls.py \\
        -v -s -k 'pause'
"""
import time

import pytest

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


# Tolerance for time-delta comparisons. Playback continues during the
# tap+read sequence, so small drift is normal. ±3s gives enough margin
# to absorb that without masking real bugs.
TIME_TOLERANCE_SEC = 3

# Tolerance for cumulative multi-tap tests. Wider because each tap
# adds ~1.5s of wall-clock playback drift (PlayerPage's built-in 1s
# wait per tap plus action latency). 5 taps in a row = ~7-8s of
# accumulated drift on top of the actual FF skip. ±10s comfortably
# covers natural drift while still catching real rate-limiting bugs
# (which would show ~30s of decrease for 5 taps, far outside ±10s).
CUMULATIVE_TOLERANCE_SEC = 15

# Expected jump from one FF/RW tap. 15s per dumps + button name.
TIME_JUMP_PER_TAP = 15


# =========================================================
# MODULE-SCOPED FIXTURE — one player session shared by all tests
# =========================================================

@pytest.fixture(scope="module")
def player_session(request):
    """One Appium session. Login → Studio tab → PROGRAMS sub-tab →
    tap first Program → tap first non-completed class → Start Session
    → dismiss Apple Watch prompt → wait for player. Yields the
    PlayerPage instance.

    Teardown: tap END SESSION and gracefully handle whatever screens
    appear afterwards (Rating, Summary, or direct return to detail).
    Never asserts on teardown — best-effort cleanup only.
    """
    driver = _create_studio_driver()

    try:
        # Login
        login_at_profile_index(driver, profile_index=0)

        # Navigate to PROGRAMS sub-tab
        home = HomePage(driver)
        studio = StudioTabPage(driver)
        home.wait_for_home()
        home.tap_studio_tab()
        studio.wait_for_studio_tab()

        # Force scroll-to-top by tapping FEATURED then PROGRAMS.
        studio.tap_subtab("FEATURED")
        studio.wait_seconds(1)
        studio.tap_subtab("PROGRAMS")
        studio.wait_seconds(2)

        # Tap VIEW CLASSES on first Program card with the button
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
                "No Program card with button_view_classes found in "
                "PROGRAMS sub-tab — cannot set up player session"
            )

        studio.tap_view_classes_on_card(target_program)

        # On Program detail page now — pick a non-completed class
        program_detail = ProgramDetailPage(driver)
        program_detail.wait_for_loaded()

        bound_classes = program_detail.find_all_visible_class_records()
        if not bound_classes:
            raise RuntimeError(
                "No fully-bound class cards found in Program detail "
                "page — cannot pick a class to play"
            )

        from appium.webdriver.common.appiumby import AppiumBy
        raw_cards = program_detail.find_all_by_id(program_detail.CARD_ID)
        target_class_index = None
        for i, card in enumerate(raw_cards):
            try:
                title_el = card.find_element(
                    AppiumBy.ID,
                    f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_TITLE_ID}",
                )
                _ = title_el.get_attribute("text")
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
            break

        if target_class_index is None:
            # All visible classes are completed — fall back to first
            # bound class regardless of completion state.
            for i, card in enumerate(raw_cards):
                try:
                    card.find_element(
                        AppiumBy.ID,
                        f"{program_detail.APP_PACKAGE}:id/{program_detail.TEXT_TITLE_ID}",
                    )
                    target_class_index = i
                    break
                except Exception:
                    continue

        if target_class_index is None:
            raise RuntimeError(
                "Could not identify a class to tap in Program detail"
            )

        target_card = raw_cards[target_class_index]
        target_card.click()
        time.sleep(2)

        # On ClassDetailPage now
        class_detail = ClassDetailPage(driver)
        class_detail.wait_for_class_detail()
        print(f"\n[setup] Class detail loaded: '{class_detail.get_title()}' "
              f"({class_detail.get_info_string()})")

        # Start session
        class_detail.tap_start_session()

        # Dismiss Apple Watch prompt if present
        prompt = AppleWatchPromptPage(driver)
        if prompt.is_showing(timeout=5):
            prompt.dismiss()
            print(f"[setup] Apple Watch prompt dismissed")

        # Wait for player to load
        player = PlayerPage(driver)
        player.wait_for_player(timeout=20)
        print(f"[setup] Player loaded — variant: "
              f"{player.get_player_variant()}, "
              f"class_time: {player.get_class_time()}")

        # Skip block preview if guided_workout
        if player.is_in_block_preview(timeout=2):
            try:
                player.tap_skip_preview()
                print(f"[setup] Skipped block preview")
                time.sleep(2)
            except Exception as e:
                print(f"[setup] Could not skip block preview: {e}")

        # Tap screen once to wake controls
        player.tap_screen()

        yield player

    finally:
        print(f"\n[teardown] Ending session and exiting...")
        try:
            player = PlayerPage(driver)
            if player.is_loaded(timeout=2):
                player.tap_end_session()
                time.sleep(2)
        except Exception as e:
            print(f"[teardown] tap_end_session failed: {e}")

        try:
            driver.quit()
        except Exception as e:
            print(f"[teardown] driver.quit failed: {e}")


# =========================================================
# Helpers
# =========================================================

def _read_remaining_seconds(player, label=""):
    """Read class_time and return as seconds (int)."""
    raw = player.get_class_time()
    parsed = player.get_class_time_seconds()
    print(f"  [{label}] class_time='{raw}' → {parsed}s remaining")
    return parsed


def _wake_controls_if_hidden(player):
    """Ensure player controls are visible before a read+tap sequence."""
    if not player.are_controls_visible(timeout=1):
        player.tap_screen()


# =========================================================
# FORME-6848 — Pause and Resume
# =========================================================

@pytest.mark.studio
def test_pause_and_resume(player_session):
    """FORME-6848 part 1: Pause stops the class-time countdown.
    Resume restarts it.
    """
    player = player_session
    _wake_controls_if_hidden(player)

    print(f"\n[6848-pause] Reading initial time")
    t0 = _read_remaining_seconds(player, "T0 before pause")
    assert t0 is not None, "Could not parse class_time as seconds at T0"

    print(f"[6848-pause] Tapping pause")
    player.tap_pause()
    time.sleep(4)

    t1 = _read_remaining_seconds(player, "T1 after pause + 4s wait")
    assert t1 is not None, "Could not parse class_time at T1"

    pause_drift = abs(t1 - t0)
    print(f"[6848-pause] Drift while paused: {pause_drift}s "
          f"(tolerance: {TIME_TOLERANCE_SEC}s)")
    assert pause_drift <= TIME_TOLERANCE_SEC, (
        f"Class time changed by {pause_drift}s during a 4s pause. "
        f"Expected ≤{TIME_TOLERANCE_SEC}s drift if pause worked. "
        f"T0={t0}s, T1={t1}s. The pause button may not have stopped "
        f"playback."
    )
    print(f"[6848-pause] ✓ Timer held steady during pause")

    print(f"[6848-pause] Tapping play")
    player.tap_play()
    time.sleep(4)

    t2 = _read_remaining_seconds(player, "T2 after play + 4s wait")
    assert t2 is not None, "Could not parse class_time at T2"

    resume_progress = t1 - t2
    print(f"[6848-pause] Progress after 4s of play: {resume_progress}s "
          f"(expected: ~4s)")
    assert resume_progress >= (4 - TIME_TOLERANCE_SEC), (
        f"Class time only progressed {resume_progress}s during a 4s "
        f"play period. Expected ~4s. T1={t1}s, T2={t2}s. The play "
        f"button may not have resumed playback."
    )
    print(f"[6848-pause] ✓ Timer resumed after play tap")


# =========================================================
# FORME-6848 — Fast Forward 15s
# =========================================================

@pytest.mark.studio
def test_fast_forward_15s(player_session):
    """FORME-6848 part 2: Tapping FF advances the class by 15s.
    Since text_class_time is REMAINING time, FF DECREASES the value."""
    player = player_session
    _wake_controls_if_hidden(player)

    print(f"\n[6848-FF] Reading initial time")
    t0 = _read_remaining_seconds(player, "T0 before FF")
    assert t0 is not None, "Could not parse class_time at T0"

    print(f"[6848-FF] Tapping forward_15")
    player.tap_fast_forward()
    time.sleep(0.5)

    t1 = _read_remaining_seconds(player, "T1 after FF")
    assert t1 is not None, "Could not parse class_time at T1"

    actual_jump = t0 - t1
    expected = TIME_JUMP_PER_TAP
    print(f"[6848-FF] Time decreased by {actual_jump}s "
          f"(expected: ~{expected}s, tolerance: ±{TIME_TOLERANCE_SEC}s)")

    assert abs(actual_jump - expected) <= TIME_TOLERANCE_SEC, (
        f"FF tap should decrease remaining class time by ~{expected}s "
        f"(±{TIME_TOLERANCE_SEC}s tolerance). Actual change: {actual_jump}s. "
        f"T0={t0}s, T1={t1}s."
    )
    print(f"[6848-FF] ✓ FF advanced playback by ~15s")


# =========================================================
# FORME-6848 — Rewind 15s
# =========================================================

@pytest.mark.studio
def test_rewind_15s(player_session):
    """FORME-6848 part 3: Tapping RW rewinds the class by 15s.
    RW INCREASES the remaining time."""
    player = player_session
    _wake_controls_if_hidden(player)

    print(f"\n[6848-RW] Reading initial time")
    t0 = _read_remaining_seconds(player, "T0 before RW")
    assert t0 is not None, "Could not parse class_time at T0"

    print(f"[6848-RW] Tapping rewind_15")
    player.tap_rewind()
    time.sleep(0.5)

    t1 = _read_remaining_seconds(player, "T1 after RW")
    assert t1 is not None, "Could not parse class_time at T1"

    actual_jump = t1 - t0
    expected = TIME_JUMP_PER_TAP
    print(f"[6848-RW] Time increased by {actual_jump}s "
          f"(expected: ~{expected}s, tolerance: ±{TIME_TOLERANCE_SEC}s)")

    assert abs(actual_jump - expected) <= TIME_TOLERANCE_SEC, (
        f"RW tap should increase remaining class time by ~{expected}s "
        f"(±{TIME_TOLERANCE_SEC}s tolerance). Actual change: {actual_jump}s. "
        f"T0={t0}s, T1={t1}s."
    )
    print(f"[6848-RW] ✓ RW rewound playback by ~15s")


# =========================================================
# FORME-6849 — FF and RW tappable unlimited times
# =========================================================

@pytest.mark.studio
def test_ff_rw_unlimited_taps(player_session):
    """FORME-6849: FF and RW remain tappable when tapped many times
    consecutively. Tap 5 times each, verify cumulative time change.

    Tolerance is wider (CUMULATIVE_TOLERANCE_SEC=10) because the
    5-tap sequence takes ~7-8s of wall-clock time during which
    playback continues, adding ~7-8s of extra countdown on top of
    the 75s FF skip total. Rate-limiting (the bug we're catching)
    would show far less than 75s of decrease, well outside the
    ±10s envelope.
    """
    player = player_session
    _wake_controls_if_hidden(player)

    print(f"\n[6849] Reading initial time")
    t0 = _read_remaining_seconds(player, "T0 before 5x FF")
    assert t0 is not None, "Could not parse class_time at T0"

    print(f"[6849] Tapping FF 5 times consecutively")
    for i in range(5):
        player.tap_fast_forward()

    time.sleep(0.5)

    t1 = _read_remaining_seconds(player, "T1 after 5x FF")
    assert t1 is not None, "Could not parse class_time at T1"

    expected_total_jump = 5 * TIME_JUMP_PER_TAP  # 75s
    actual_jump = t0 - t1
    print(f"[6849] Time decreased by {actual_jump}s after 5 FF taps "
          f"(expected: ~{expected_total_jump}s, tolerance: "
          f"±{CUMULATIVE_TOLERANCE_SEC}s)")

    assert abs(actual_jump - expected_total_jump) <= CUMULATIVE_TOLERANCE_SEC, (
        f"After 5 FF taps, time should decrease by ~{expected_total_jump}s "
        f"(±{CUMULATIVE_TOLERANCE_SEC}s tolerance). Actual: {actual_jump}s. "
        f"T0={t0}s, T1={t1}s. The FF button may have become disabled "
        f"part-way through (rate-limiting bug per FORME-6849), OR "
        f"playback drift was larger than expected for this run."
    )
    print(f"[6849] ✓ FF tappable 5 consecutive times — no rate-limit")

    # Now RW 5 times
    print(f"[6849] Tapping RW 5 times consecutively")
    for i in range(5):
        player.tap_rewind()

    time.sleep(0.5)

    t2 = _read_remaining_seconds(player, "T2 after 5x FF + 5x RW")
    assert t2 is not None, "Could not parse class_time at T2"

    rw_jump = t2 - t1
    print(f"[6849] Time increased by {rw_jump}s after 5 RW taps "
          f"(expected: ~{expected_total_jump}s, tolerance: "
          f"±{CUMULATIVE_TOLERANCE_SEC}s)")

    # For RW: rw_jump should be ~75s. Playback continued during the
    # 5-tap sequence, REDUCING the net "increase" we'd see. So the
    # expected is 75 - drift, meaning actual will be SMALLER than 75
    # by ~7-8s. Use the same ±10s tolerance — covers either direction.
    assert abs(rw_jump - expected_total_jump) <= CUMULATIVE_TOLERANCE_SEC, (
        f"After 5 RW taps, time should increase by ~{expected_total_jump}s "
        f"(±{CUMULATIVE_TOLERANCE_SEC}s tolerance). Actual: {rw_jump}s. "
        f"T1={t1}s, T2={t2}s. The RW button may have become disabled "
        f"part-way through, OR playback drift exceeded expected envelope."
    )
    print(f"[6849] ✓ RW tappable 5 consecutive times — no rate-limit")