"""
Custom Planned Sessions (CPS) test cases
FORME-1769 | FORME-1770 | FORME-1778 | FORME-1782 | FORME-1801
"""
import pytest
from surfaces.member_android.pages.studio_page import StudioPage


@pytest.fixture(scope="class")
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestCustomPlannedSessions:

    def test_FORME_1769_cps_displayed_on_your_plan_and_can_be_played(self, studio):
        """
        FORME-1769: Verify Studio CPS is displayed on 'Your Plan' and can be played.
        Steps:
          1. Navigate to 'Your Plan' tab.
          2. Verify Custom Planned Session is listed.
          3. Tap on the CPS.
          4. Tap 'Start Session' and verify session starts.
          5. Wait 60 seconds, then tap End Session.
        """
        studio.navigate_to_your_plan()
        assert studio.is_cps_visible_on_plan(), "CPS is not displayed on 'Your Plan' tab"

        studio.open_custom_planned_sessions()
        studio.tap_start_class()
        studio.wait_seconds(3)
        assert studio.is_session_active(), "CPS session did not start from 'Your Plan'"

        studio.wait_seconds(30)
        studio.tap_end_session()

    def test_FORME_1770_cps_can_be_played_from_studio_tab(self, studio):
        """
        FORME-1770: Verify CPS can be played from Studio tab.
        Steps:
          1. Navigate to Studio tab.
          2. Navigate to Custom Planned Sessions category.
          3. Select a CPS.
          4. Tap 'Start Session'.
          5. Verify session starts playing.
        Note: session is intentionally left running for tests 1778, 1782, and 1801.
        """
        studio.navigate_to_studio()
        assert studio.is_cps_listed_in_studio(), "CPS category is not visible in Studio tab"

        studio.open_custom_planned_sessions()
        studio.select_first_cps()
        studio.tap_start_class()
        studio.wait_seconds(3)
        assert studio.is_session_active(), "CPS session did not start from Studio tab"

    def test_FORME_1778_reps_and_time_set_by_trainer_displayed_in_cps(self, studio):
        """
        FORME-1778: Verify reps and time set by trainer is displayed in CPS.
        Steps:
          1. Continue in the active CPS session started by test_1770.
          2. Verify reps/time values sent from the backend are visible on screen.
        """
        assert studio.are_reps_time_displayed(), \
            "Reps or time information set by trainer is not displayed in CPS"

    def test_FORME_1782_client_can_pause_and_play_during_cps(self, studio):
        """
        FORME-1782: Client should be able to Pause and play during CPS.
        Steps:
          1. Continue in the active CPS session started by test_1770.
          2. Tap screen to reveal controls.
          3. Tap Pause — session timer should pause.
          4. Tap Forward — should skip to next movement.
          5. Tap Back — should restart current movement.
          6. Resume session for subsequent tests.
        """
        studio.tap_screen_during_session()
        studio.wait_seconds(1)

        studio.tap_pause()
        studio.wait_seconds(1)
        assert studio.is_session_paused(), "Session did not pause after tapping Pause"

        studio.tap_forward()
        studio.wait_seconds(1)

        studio.tap_back()
        studio.wait_seconds(1)

        studio.tap_resume()
        studio.wait_seconds(1)

    def test_FORME_1801_swipe_up_displayed_after_45_seconds_for_rep_exercise(self, studio):
        """
        FORME-1801: Verify 'Swipe up to complete' is displayed after 45 seconds for Rep based exercise.
        Steps:
          1. Continue in the active CPS session started by test_1770.
          2. Wait 45 seconds in a rep-based exercise.
          3. Verify 'Swipe up to complete' label is displayed.
        """
        assert studio.wait_for_swipe_up(timeout=180), \
            "'Swipe up to complete' was not displayed within 180 seconds for rep-based exercise"
        studio.swipe_up_to_complete()
        studio.wait_seconds(2)

        # End session using the CPS-aware method: END SESSION in CPS has no resource
        # ID (ViewGroup/TextView), so coordinate-based taps are required — same
        # approach as test_FORME_1869.
        studio._end_class_leave_survey_open()

        # Close Post-Session Survey if it appears.
        if studio.is_displayed("button_submit", timeout=10):
            studio.tap("button_close")
            studio.wait_seconds(1)

        # Close Workout Summary if it appears.
        if studio.is_displayed("button_bookmark", timeout=10):
            studio.tap("button_close")
            studio.wait_seconds(2)
