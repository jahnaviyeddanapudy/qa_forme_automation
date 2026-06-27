"""
STUDIO-4267: Verify the Member App does not crash or ANR when a client
joins and immediately ends a Live 1:1 session in quick succession.

Root cause: AgoraViewModel.initializeAndJoinChannel() could be called twice
(duplicate onTrainerStateChanged observer), and leaveAndDestroy() left
rtcEngine non-null, allowing a second init on rejoin. Fix:
  - Removed duplicate observer in LiveStreamFragment
  - Added guard: if rtcEngine != null return early in initializeAndJoinChannel()
  - Set rtcEngine = null and cleared tracks in leaveAndDestroy()
  - Added firebaseSubscribedLiveData.postValue(false) on session end

Pre-condition: A Live 1:1 session must be active (trainer is streaming).
"""
import pytest
from surfaces.member_android.pages.live_page import LivePage


@pytest.fixture()
def live(driver):
    page = LivePage(driver)
    page.ensure_logged_in()
    return page


class TestSTUDIO4267LiveSessionJoinEndQuickly:

    def test_STUDIO_4267_join_and_end_live_session_quickly_no_crash(self, live):
        """
        STUDIO-4267: Join an active Live 1:1 session and immediately end it.
        Verify the app remains responsive with no crash or ANR.
        Pre-condition: Trainer must have an active Live 1:1 session in progress.
        Steps:
          1. Navigate to the Live 1:1 tab.
          2. Tap Join on the active session tile.
          3. Immediately tap End Session without waiting.
          4. Wait up to 15s for the app to return to a stable state.
          5. Assert the app is still responsive (main nav is visible).
        """
        live.navigate_to_live()
        live.join_live_session()
        live.wait_seconds(1)
        live.end_live_session_immediately()
        live.wait_seconds(3)

        assert live.is_app_responsive(), (
            "App became unresponsive or crashed after joining and immediately ending "
            "a Live 1:1 session — potential AgoraViewModel double-init regression (STUDIO-4267)"
        )

    def test_STUDIO_4267_join_end_quickly_returns_to_live_tab(self, live):
        """
        STUDIO-4267: After joining and immediately ending a Live 1:1 session,
        verify the app returns to the Live 1:1 tab (not stuck on a blank screen
        or showing an ANR dialog).
        Pre-condition: Trainer must have an active Live 1:1 session in progress.
        Steps:
          1. Navigate to the Live 1:1 tab.
          2. Join the active session.
          3. End the session immediately.
          4. Assert the Live tab or main nav is visible within 15s.
          5. Assert no error or crash dialog is present.
        """
        live.navigate_to_live()
        live.join_live_session()
        live.wait_seconds(1)
        live.end_live_session_immediately()
        live.wait_seconds(3)

        assert live.is_app_responsive(), (
            "App did not return to a valid state after joining and immediately ending "
            "a Live 1:1 session (STUDIO-4267)"
        )

        assert not live.is_text_contains_displayed("isn't responding", timeout=3) and \
               not live.is_text_contains_displayed("has stopped", timeout=3), (
            "App crash or ANR dialog detected after joining and ending Live 1:1 quickly"
        )
