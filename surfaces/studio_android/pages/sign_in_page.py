"""SignInPage — Studio's password prompt screen.

Appears after tapping a profile on ProfileActivity if the user did NOT
choose "Keep me logged in" previously, or if their saved session expired.

The email field is pre-filled with the account being signed in (the one
whose profile was tapped on ProfileActivity). Only the password needs
entering.

Submit: this screen has no visible submit button. Submission is triggered
by the on-screen keyboard's action key. Different fields may declare
different IME actions (NEXT, DONE, GO, SEND) — submit() tries each in
order until one advances the screen.
"""
import time
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class SignInPage(StudioBasePage):
    # Element IDs confirmed from dump on 2026-04-24
    SCREEN_HEADER_ID = "text_sign_in"            # 'Sign In' text — screen marker
    EMAIL_WRAPPER_ID = "edit_email"              # wrapper around email EditText
    PASSWORD_WRAPPER_ID = "edit_password"        # wrapper around password EditText
    INNER_EDIT_ID = "edit"                       # actual EditText inside each wrapper
    SHOW_PASSWORD_ID = "button_eye"              # toggle password visibility
    KEEP_LOGGED_IN_ID = "checkbox_keep_logged_in"
    CLOSE_ID = "button_close"                    # cancel back to ProfileActivity
    HELP_ID = "button_help"
    KEYBOARD_ID = "keyboard"

    # IME actions to try on submit, in priority order. The on-screen
    # keyboard's action key sends whatever action the focused EditText
    # declares — different builds use different values.
    SUBMIT_IME_ACTIONS = ["done", "next", "go", "send"]

    # --- Screen detection ---

    def is_visible(self, timeout=3):
        """Non-blocking check: is Sign In currently up?"""
        return self.is_text_visible("Sign In", timeout=timeout)

    def wait_for_sign_in_screen(self):
        """Block until Sign In renders."""
        self.wait.until(EC.presence_of_element_located(
            (AppiumBy.XPATH, "//*[@text='Sign In']")
        ))
        log.info("Sign In screen loaded")

    def get_prefilled_email(self):
        """Email pre-filled by Studio when the user tapped their avatar."""
        wrapper = self.find_by_id(self.EMAIL_WRAPPER_ID)
        edits = wrapper.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.INNER_EDIT_ID}"
        )
        if not edits:
            raise RuntimeError("Could not find inner email EditText")
        return edits[0].get_attribute("text") or ""

    # --- Form actions ---

    def _focus_password_field(self):
        """Focus the password EditText. Returns the element."""
        wrapper = self.find_by_id(self.PASSWORD_WRAPPER_ID)
        edits = wrapper.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.INNER_EDIT_ID}"
        )
        if not edits:
            raise RuntimeError("Could not find inner password EditText")
        edit = edits[0]
        edit.click()
        return edit

    def enter_password(self, password):
        edit = self._focus_password_field()
        edit.clear()
        edit.send_keys(password)
        log.info("Entered password")

    def set_keep_logged_in(self, checked=True):
        """Check or uncheck 'Keep me logged in'.

        Default in tests is to leave UNchecked so subsequent runs
        reliably get the Sign In prompt. Pass checked=True for tests
        that verify the saved-login flow."""
        cb = self.find_by_id(self.KEEP_LOGGED_IN_ID)
        is_checked = cb.get_attribute("checked") == "true"
        if is_checked != checked:
            cb.click()
            log.info(f"Keep me logged in: {is_checked} -> {checked}")
        else:
            log.info(f"Keep me logged in already: {checked}")

    def submit(self):
        """Submit the Sign In form. The screen has no visible submit button —
        submission is triggered by the on-screen keyboard's action key.

        We don't know which IME action this build declares (NEXT vs DONE
        vs GO vs SEND), so we try each in order. After each attempt, we
        check whether the Sign In screen is still up — if it disappeared,
        the submit succeeded.

        Strategies in order:
          1. mobile: performEditorAction with each of next/done/go/send
          2. KEYCODE_TAB (61) — fallback for builds where IME action API
             isn't responding
          3. KEYCODE_ENTER (66) — last resort

        Re-focuses the password field before each attempt — IME actions
        only fire on the focused EditText.
        """
        for action in self.SUBMIT_IME_ACTIONS:
            try:
                self._focus_password_field()
                self.driver.execute_script(
                    "mobile: performEditorAction", {"action": action}
                )
                log.info(f"Tried submit via IME action: {action}")
            except Exception as e:
                log.info(f"IME action '{action}' raised: {e}")
                continue

            # Brief wait — give the form a moment to advance
            time.sleep(1.5)

            # If Sign In is gone, we succeeded
            if not self.is_visible(timeout=1):
                log.info(f"Submit succeeded via IME action: {action}")
                return

        # Fallback 1: KEYCODE_TAB
        try:
            self._focus_password_field()
            self.driver.press_keycode(61)  # KEYCODE_TAB
            log.info("Tried submit via KEYCODE_TAB")
            time.sleep(1.5)
            if not self.is_visible(timeout=1):
                log.info("Submit succeeded via KEYCODE_TAB")
                return
        except Exception as e:
            log.info(f"KEYCODE_TAB raised: {e}")

        # Fallback 2: KEYCODE_ENTER
        try:
            self._focus_password_field()
            self.driver.press_keycode(66)  # KEYCODE_ENTER
            log.info("Tried submit via KEYCODE_ENTER")
            time.sleep(1.5)
            if not self.is_visible(timeout=1):
                log.info("Submit succeeded via KEYCODE_ENTER")
                return
        except Exception as e:
            log.info(f"KEYCODE_ENTER raised: {e}")

        raise RuntimeError(
            "SignInPage.submit(): all submit strategies failed (tried "
            f"{self.SUBMIT_IME_ACTIONS} + KEYCODE_TAB + KEYCODE_ENTER). "
            "Sign In screen still visible. Inspect the keyboard's action "
            "key behavior on this Studio firmware — there may be a "
            "different submit mechanism we haven't covered."
        )

    def cancel(self):
        """Tap close (X) — return to ProfileActivity without signing in."""
        self.tap_by_id(self.CLOSE_ID)
        log.info("Cancelled Sign In (returned to ProfileActivity)")

    # --- Convenience ---

    def sign_in(self, password, keep_logged_in=False):
        """Full sign-in flow: enter password, optionally check 'Keep me
        logged in', submit. Caller is responsible for waiting for the
        home screen afterwards."""
        self.wait_for_sign_in_screen()
        self.enter_password(password)
        if keep_logged_in:
            self.set_keep_logged_in(True)
        self.submit()
        log.info("Sign In submitted")