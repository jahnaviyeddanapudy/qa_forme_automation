"""
Workout History test cases
FORME-1875 | FORME-1887
"""
import pytest
from surfaces.member_android.pages.studio_page import StudioPage
from surfaces.member_android.pages.api_client import SESSION_TYPE_LIFT_VOD, SESSION_TYPE_ANDROID_VOD


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestWorkoutHistory:

    def test_FORME_1875_completed_lift_vod_session_displayed_in_workout_history(
        self, studio, api_token
    ):
        """
        FORME-1875: Verify completed Lift VOD session is displayed in workout history.
        Pre-condition: A Lift VOD session has been completed on the Lift device.
        Steps:
          1. Tap Profile button.
          2. Verify Completed Workouts is shown under Progress (UI check).
          3. Call GET /v1/user/me/history-workout filtered by session_type "Lift VOD"
             and confirm at least one completed entry exists (API check).
        """
        studio.go_to_workout_history()
        assert studio.is_vod_session_in_history(
            session_type=SESSION_TYPE_LIFT_VOD,
            api_token=api_token,
        ), "Completed Lift VOD session not found in workout history (session_type='Lift VOD')"

    def test_FORME_1887_completed_android_vod_session_displayed_in_workout_history(
        self, studio, api_token
    ):
        """
        FORME-1887: Verify completed Android VOD session is displayed in workout history.
        Pre-condition: A VOD session has been completed on the Android Member App.
        Steps:
          1. Tap Profile button.
          2. Verify Completed Workouts is shown under Progress (UI check).
          3. Call GET /v1/user/me/history-workout filtered by session_type "Video on Demand"
             and confirm at least one completed entry exists (API check).
        """
        studio.go_to_workout_history()
        assert studio.is_vod_session_in_history(
            session_type=SESSION_TYPE_ANDROID_VOD,
            api_token=api_token,
        ), "Completed Android VOD session not found in workout history (session_type='Video on Demand')"
