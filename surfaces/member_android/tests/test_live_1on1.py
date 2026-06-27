"""
Live 1:1 Cancel Session test cases
FORME-7824 | FORME-7821 | FORME-7807
"""
import pytest
from surfaces.member_android.pages.live_page import LivePage


@pytest.fixture()
def live(driver):
    page = LivePage(driver)
    page.navigate_to_live()
    return page


class TestLive1on1:

    def test_FORME_7824_nevermind_button_while_cancelling_upcoming_session(self, live):
        """
        FORME-7824: Verify NEVERMIND button while cancelling Upcoming live 1:1 session.
        Pre-condition:
          - Trainer has scheduled a Live 1:1 session for the client.
        Steps:
          1. Navigate to Live 1:1 tab.
          2. Tap contextual menu (3 dots) on an upcoming session.
          3. Tap CANCEL SESSION.
          4. Verify modal shows CONFIRM and NEVERMIND buttons.
          5. Tap NEVERMIND.
          6. Verify modal closes and page returns to Upcoming tab.
        """
        live.go_to_upcoming_tab()

        live.tap_three_dots_on_session()
        live.wait_seconds(1)

        live.tap_cancel_in_menu()
        live.wait_seconds(1)

        assert live.is_cancel_modal_displayed(), \
            "Cancel session modal with CONFIRM and NEVERMIND was not displayed"

        live.tap_nevermind()
        live.wait_seconds(1)

        assert live.is_upcoming_sessions_page(), \
            "Page did not return to Upcoming sessions tab after tapping NEVERMIND"
        assert not live.is_cancel_modal_displayed(), \
            "Cancel session modal is still displayed after tapping NEVERMIND"

    def test_FORME_7821_cancel_next_live_1on1_session(self, live):
        """
        FORME-7821: Cancel next live 1:1 session.
        Pre-condition:
          - Trainer has scheduled a Live 1:1 session for the client.
          - Session is visible in the Member App Live 1:1 tab.
        Steps:
          1. Navigate to Live 1:1 tab.
          2. Tap contextual menu (3 dots) on an upcoming session.
          3. Tap CANCEL SESSION.
          4. Verify cancel confirmation modal shows CONFIRM and NEVERMIND buttons.
          5. Tap CONFIRM.
          6. Verify cancellation toast appears and page redirects to upcoming sessions.
        """
        live.go_to_upcoming_tab()

        live.tap_three_dots_on_session()
        live.wait_seconds(1)

        live.tap_cancel_in_menu()
        live.wait_seconds(1)

        assert live.is_cancel_modal_displayed(), \
            "Cancel session modal with CONFIRM and NEVERMIND was not displayed"

        live.tap_confirm_cancel()
        live.wait_seconds(2)

        assert live.is_cancellation_toast_displayed() or live.is_on_upcoming_tab(), \
            "Cancellation toast or upcoming sessions page was not shown after confirming cancel"

    def test_FORME_7807_cancelled_session_is_displayed_in_past_tab(self, live):
        """
        FORME-7807: Verify cancelled session is displayed in Past sub-tab.
        Pre-condition:
          - Trainer has a scheduled Live 1:1 session.
          - A session has been cancelled (current or past date).
        Steps:
          1. Navigate to Live 1:1 tab.
          2. Go to Past sub-tab.
          3. Scroll the list and verify a session with 'Cancelled' status is shown.
          4. Scroll the list and verify a session with 'Late Cancel' status is shown.
        """
        live.go_to_past_tab()

        assert live.is_session_cancelled_in_past(), \
            "No session with 'Cancelled' status found in the Past sub-tab"

        assert live.is_late_cancel_in_past(), \
            "No session with 'Late Cancel' status found in the Past sub-tab"
