from pages.base_page import BasePage


class LivePage(BasePage):

    # Session list item (item_live_schedule.xml)
    CANCEL_BTN = "button_cancel"
    THREE_DOTS_BTN = "button_more"

    # Cancel dialog (dialog_cancel_session.xml)
    CONFIRM_BTN = "button_positive"
    NEVERMIND_BTN = "button_negative"

    def navigate_to_live(self):
        self.ensure_logged_in()
        self.go_to_live_tab()

    # --- Sub-tabs ---

    def go_to_upcoming_tab(self):
        self.tap_text_contains("Upcoming")

    def go_to_past_tab(self):
        self.tap_text_contains("Past")

    # --- Session actions ---

    def tap_cancel_session(self):
        self.tap(self.CANCEL_BTN)

    def tap_three_dots_on_session(self):
        self.tap(self.THREE_DOTS_BTN)

    def tap_cancel_in_menu(self):
        self.tap_text_contains("Cancel Session")

    def tap_confirm_cancel(self):
        self.tap(self.CONFIRM_BTN)

    def tap_nevermind(self):
        self.tap(self.NEVERMIND_BTN)

    # --- Assertions ---

    def is_live_tab_visible(self):
        return self.is_displayed(self.TAB_LIVE)

    def is_cancel_session_visible(self):
        return self.is_displayed(self.CANCEL_BTN) or self.is_text_contains_displayed("Cancel Session")

    def is_cancel_modal_displayed(self):
        return self.is_displayed(self.CONFIRM_BTN) and self.is_displayed(self.NEVERMIND_BTN)

    def is_cancellation_toast_displayed(self):
        return (
            self.is_text_contains_displayed("cancelled") or
            self.is_text_contains_displayed("Session cancelled")
        )

    def is_on_upcoming_tab(self):
        return (
            self.is_text_contains_displayed("No upcoming sessions") or
            self.is_text_contains_displayed("Upcoming")
        )

    def _scroll_to_text_contains(self, text, timeout=10):
        """Scroll the current list until an element containing text is visible.

        Uses UiScrollable so the list auto-scrolls rather than requiring a fixed
        pixel-offset swipe. Returns True if found, False if not present.
        """
        from appium.webdriver.common.appiumby import AppiumBy
        try:
            locator = (
                f'new UiScrollable(new UiSelector().scrollable(true))'
                f'.scrollIntoView(new UiSelector().textContains("{text}"))'
            )
            self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, locator)
            return True
        except Exception:
            return False

    def is_session_cancelled_in_past(self):
        return self._scroll_to_text_contains("Cancelled")

    def is_late_cancel_in_past(self):
        return self._scroll_to_text_contains("Late Cancel")

    def is_post_session_survey_displayed(self):
        return (
            self.is_text_contains_displayed("Session Feedback") or
            self.is_text_contains_displayed("How was your workout") or
            self.is_text_contains_displayed("Rate your session")
        )

    def is_upcoming_sessions_page(self):
        return self.is_text_contains_displayed("Upcoming")

    # --- STUDIO-4267: Join and end live session ---

    def join_live_session(self):
        """Tap the Join button on an active Live 1:1 session tile.

        Pre-condition: a session must be active (trainer is streaming).
        Tries common button texts and resource IDs used in the live session UI.
        """
        for text in ("Join", "Join Session", "JOIN", "JOIN SESSION", "Start"):
            try:
                self.find_by_text_contains(text, timeout=5).click()
                return
            except Exception:
                continue
        for res_id in ("button_join", "button_start_session", "button_join_session"):
            try:
                self.tap(res_id, timeout=3)
                return
            except Exception:
                continue
        raise AssertionError(
            "No 'Join' button found on the Live tab — "
            "ensure a Live 1:1 session is active before running this test"
        )

    def end_live_session_immediately(self):
        """Tap the End Session button as quickly as possible after joining.

        Tests the STUDIO-4267 crash scenario: joining and ending in quick succession.
        Tries both text-based and resource-id-based selectors.
        """
        for text in ("End Session", "End", "Leave", "Leave Session"):
            try:
                self.find_by_text_contains(text, timeout=5).click()
                return
            except Exception:
                continue
        for res_id in ("button_end_session", "button_end", "button_leave"):
            try:
                self.tap(res_id, timeout=3)
                return
            except Exception:
                continue

    def is_app_responsive(self):
        """Return True if the app is still alive and showing a known UI element.

        After joining and immediately ending a session the app should return to
        either the Live tab or the main nav without crashing or ANR-ing.
        """
        try:
            self.wait_for_main_nav(timeout=15)
            return True
        except Exception:
            pass
        for tab_id in (self.TAB_LIVE, self.TAB_STUDIO, self.TAB_YOUR_PLAN):
            if self.is_displayed(tab_id, timeout=5):
                return True
        return False
