"""SettingsMembersPage — Studio's Settings › Members screen.

Reached from SettingsMainFragment by tapping the MEMBERS button.
Lists all profiles (owner + visitors) and provides sign-out /
remove-profile actions.

Key flows covered:
  - STUDIO-4285: Owner logout fix — tapping Remove on the owner
    profile must show the ConfirmationDialog, then the
    EnterPasswordDialog, and ultimately sign the owner out.
  - STUDIO-4284: After owner logs out (or Install Setup is run)
    downloaded content cache is cleared.

Element IDs inferred from MembersAdapter + FragmentSettingsMembersBinding:
  recycler             — list of member rows
  text_name            — member display name per row
  button_sign_out      — sign-out action per row
  button_remove        — remove-profile action per row

ConfirmationDialog (generic re-use):
  button_confirm       — confirm / yes
  button_cancel        — cancel / no

EnterPasswordDialog:
  edit_password        — password field (inner edit)
  button_confirm       — submit password

LoginDialog (re-login prompt when switching owners):
  edit_email           — e-mail field
  edit_password        — password field
  button_sign_in       — submit
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SettingsMembersPage(StudioBasePage):
    # ------------------------------------------------------------------ #
    # Members list
    # ------------------------------------------------------------------ #
    RECYCLER_ID = "recycler"
    TEXT_NAME_ID = "text_name"
    BUTTON_SIGN_OUT_ID = "button_sign_out"
    BUTTON_REMOVE_ID = "button_remove"

    # ------------------------------------------------------------------ #
    # ConfirmationDialog
    # ------------------------------------------------------------------ #
    CONFIRMATION_BUTTON_CONFIRM_ID = "button_confirm"
    CONFIRMATION_BUTTON_CANCEL_ID = "button_cancel"

    # ------------------------------------------------------------------ #
    # EnterPasswordDialog
    # ------------------------------------------------------------------ #
    ENTER_PASSWORD_FIELD_ID = "edit_password"
    ENTER_PASSWORD_SUBMIT_ID = "button_confirm"

    # ------------------------------------------------------------------ #
    # LoginDialog (owner re-authentication)
    # ------------------------------------------------------------------ #
    LOGIN_DIALOG_EMAIL_ID = "edit_email"
    LOGIN_DIALOG_PASSWORD_ID = "edit_password"
    LOGIN_DIALOG_SUBMIT_ID = "button_sign_in"

    # ------------------------------------------------------------------ #
    # Screen lifecycle
    # ------------------------------------------------------------------ #

    def is_loaded(self, timeout: int = 10) -> bool:
        """Return True when the members recycler is visible."""
        return self.is_visible(self.RECYCLER_ID, timeout=timeout)

    def wait_for_screen(self, timeout: int = 15):
        """Block until the members screen is fully rendered."""
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(self.by_id(self.RECYCLER_ID))
        )
        log.info("SettingsMembersPage loaded")

    # ------------------------------------------------------------------ #
    # Member row helpers
    # ------------------------------------------------------------------ #

    def get_member_names(self) -> list:
        """Return list of visible member name strings."""
        els = self.find_all_by_id(self.TEXT_NAME_ID)
        return [e.text for e in els if e.text]

    def tap_remove_for_member(self, name: str):
        """Tap the Remove button on the row whose text_name matches *name*.

        Uses an XPath container predicate to scope button_remove to the
        correct row — avoids positional index fragility.
        """
        xpath = (
            f"//*[*[@resource-id='{self._id(self.TEXT_NAME_ID)}' "
            f"and @text='{name}']]/*[@resource-id='{self._id(self.BUTTON_REMOVE_ID)}']"
        )
        el = WebDriverWait(self.driver, self.WAIT_DEFAULT).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, xpath))
        )
        el.click()
        log.info(f"Tapped Remove for member: {name}")

    def tap_sign_out_for_member(self, name: str):
        """Tap the Sign Out button on the row whose text_name matches *name*."""
        xpath = (
            f"//*[*[@resource-id='{self._id(self.TEXT_NAME_ID)}' "
            f"and @text='{name}']]/*[@resource-id='{self._id(self.BUTTON_SIGN_OUT_ID)}']"
        )
        el = WebDriverWait(self.driver, self.WAIT_DEFAULT).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, xpath))
        )
        el.click()
        log.info(f"Tapped Sign Out for member: {name}")

    def is_remove_button_visible_for_member(self, name: str, timeout: int = 5) -> bool:
        """Check whether a Remove button is visible for the named member."""
        xpath = (
            f"//*[*[@resource-id='{self._id(self.TEXT_NAME_ID)}' "
            f"and @text='{name}']]/*[@resource-id='{self._id(self.BUTTON_REMOVE_ID)}']"
        )
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.XPATH, xpath))
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # ConfirmationDialog helpers
    # ------------------------------------------------------------------ #

    def is_confirmation_dialog_visible(self, timeout: int = 10) -> bool:
        """Return True when the generic ConfirmationDialog is on screen."""
        return self.is_visible(self.CONFIRMATION_BUTTON_CONFIRM_ID, timeout=timeout)

    def confirm_dialog(self):
        """Tap the confirm / yes button on the ConfirmationDialog."""
        self.tap_by_id(self.CONFIRMATION_BUTTON_CONFIRM_ID)
        log.info("ConfirmationDialog: tapped Confirm")

    def cancel_dialog(self):
        """Tap the cancel button on the ConfirmationDialog."""
        self.tap_by_id(self.CONFIRMATION_BUTTON_CANCEL_ID)
        log.info("ConfirmationDialog: tapped Cancel")

    # ------------------------------------------------------------------ #
    # EnterPasswordDialog helpers
    # ------------------------------------------------------------------ #

    def is_enter_password_dialog_visible(self, timeout: int = 10) -> bool:
        """Return True when the EnterPasswordDialog is on screen."""
        return self.is_visible(self.ENTER_PASSWORD_FIELD_ID, timeout=timeout)

    def enter_password_and_submit(self, password: str):
        """Type *password* into the EnterPasswordDialog and submit."""
        self.input_text(self.ENTER_PASSWORD_FIELD_ID, password)
        self.tap_by_id(self.ENTER_PASSWORD_SUBMIT_ID)
        log.info("EnterPasswordDialog: password submitted")
