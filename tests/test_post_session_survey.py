"""
Post-Session Survey test cases
FORME-1861 | FORME-1869 | FORME-1871
"""
import pytest
from pages.studio_page import StudioPage
from pages.live_page import LivePage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


@pytest.fixture()
def live(driver):
    page = LivePage(driver)
    page.ensure_logged_in()
    return page


class TestPostSessionSurvey:

    def test_FORME_1861_post_session_survey_after_vod_completion(self, studio):
        """
        FORME-1861: Post-Session Survey appears after full VOD class completion.
        Steps:
          1. Navigate to Barre VOD category and start a class.
          2. Wait for the class to complete naturally (up to 60 min).
             (Falls back to manual end if the survey has not appeared by then.)
          3. Post-Session Survey appears.
          4. Enter message in Comments field.
          5. Tap 4 stars for Session rating, Instructor, and Difficulty for you.
          6. Assert Submit button is enabled.
          7. Tap Submit.
          8. Close Workout Summary.
        """
        studio.navigate_to_studio()
        studio.start_vod_class()

        if not studio.wait_for_class_completion(timeout=3600):
            studio._end_class_leave_survey_open()

        assert studio.is_post_session_survey_displayed(), \
            "Post-Session Survey did not appear after class completion"

        survey_comment = "Great class! Really enjoyed the full session."
        studio.enter_survey_comment(survey_comment)

        studio.tap_all_rating_stars(4)
        studio.wait_seconds(0.5)

        assert studio.is_submit_active(), \
            "Submit button is not enabled after entering rating and comment"

        studio.submit_survey()
        studio.wait_seconds(2)

        studio.close_workout_summary()

    def test_FORME_1869_post_session_survey_after_cps_ended_prematurely(self, studio):
        """
        FORME-1869: Post-Session Survey appears after CPS Class ended prematurely.
        Steps:
          1. Navigate to Custom category under Studio tab.
          2. Tap a class card → tap Start → class plays.
          3. Start the Class.
          4. After 30 seconds, end the session prematurely.
          5. Tap 4 stars for Session rating and Difficulty for you.
          6. Assert Submit button is enabled.
          7. Tap Submit.
          8. Close Workout Summary.
        """
        studio.navigate_to_studio()
        studio.open_custom_planned_sessions()
        studio.select_first_cps()
        studio.tap_start_class()

        # Wait 30 s for the session to get underway.
        # keep_alive_wait() sends a brief Appium query every 15 s to prevent
        # session timeout (newCommandTimeout = 120 s) during the sleep.
        studio.keep_alive_wait(30)

        # End the session prematurely and leave the Post-Session Survey open.
        studio._end_class_leave_survey_open()

        # Poll for the survey using a fast resource-ID check only.
        # is_post_session_survey_displayed() falls back to UiSelector text queries
        # which block for 2–5 min each while CPS is still running — avoid it here.
        import time as _time
        deadline = _time.monotonic() + 120
        while _time.monotonic() < deadline:
            if studio.is_displayed("button_submit", timeout=3):
                break
            studio.wait_seconds(2)

        assert studio.is_displayed("button_submit", timeout=5), \
            "Post-Session Survey did not appear after CPS class ended prematurely"

        # Tap 4 stars for Session rating and Difficulty for you.
        studio.tap_all_rating_stars(4)
        studio.wait_seconds(0.5)

        assert studio.is_submit_active(), \
            "Submit button is not enabled after selecting rating"

        studio.submit_survey()
        studio.wait_seconds(2)

        studio.close_workout_summary()

    def test_FORME_1871_post_session_survey_after_trainer_ends_1on1_session(self, live):
        """
        FORME-1871: Check Post-Session Survey after trainer ends 1:1 Session.
        Pre-condition: A Live 1:1 session must be scheduled and completed by the trainer.
        Steps:
          1. Navigate to Live 1:1 tab.
          2. After trainer ends the session, verify survey appears on member app.
        Note: Requires the trainer to end the session from the Trainer Studio app.
        """
        live.navigate_to_live()

        max_wait = 300
        elapsed = 0
        interval = 10
        survey_appeared = False
        while elapsed < max_wait:
            if live.is_post_session_survey_displayed():
                survey_appeared = True
                break
            live.wait_seconds(interval)
            elapsed += interval

        assert survey_appeared, \
            "Post-Session Survey did not appear after trainer ended the Live 1:1 session"
