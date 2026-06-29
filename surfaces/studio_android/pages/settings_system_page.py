"""SettingsSystemPage — Studio's System Settings screen.

Reached from SettingsMainFragment by tapping the SYSTEM button.
Organised as a dynamic list of SystemSetting rows grouped into
categories (Device, Content, Display, Network, Lift, System).

New in commit 27eb5e4 / 031c1a4:
  - Timezone row added under the System category.
  - Tapping the PICK action button opens TimezonePickerDialog
    (a RecyclerView-based dialog with a global list of timezones).
  - After selection the row's description updates to the chosen
    timezone ID and the midnight WiFi-restore alarm is rescheduled.

Element IDs inferred from SystemSettingsAdapter + layout files:
  The settings list is rendered by SystemSettingsAdapter inside a
  RecyclerView. Each row exposes:
    text_title       — setting name  (e.g. "Time Zone")
    text_description — current value (e.g. "America/New_York")
    button_action    — action button  (e.g. "PICK")

TimezonePickerDialog layout (dialog_timezone_picker.xml):
    recycler_timezones  — scrollable list of timezone rows
    button_cancel       — dismiss without selecting

Timezone row layout (item_timezone_row.xml):
    image_check         — checkmark icon (orange = selected)
    text_timezone       — e.g. "EST — America/New_York"
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SettingsSystemPage(StudioBasePage):
    # ------------------------------------------------------------------ #
    # Settings list row IDs (SystemSettingsAdapter item layout)
    # ------------------------------------------------------------------ #
    ROW_TITLE_ID = "text_title"
    ROW_DESCRIPTION_ID = "text_description"
    ROW_ACTION_BUTTON_ID = "button_action"

    # ------------------------------------------------------------------ #
    # TimezonePickerDialog IDs
    # ------------------------------------------------------------------ #
    TIMEZONE_RECYCLER_ID = "recycler_timezones"
    TIMEZONE_CANCEL_BUTTON_ID = "button_cancel"
    TIMEZONE_ROW_TEXT_ID = "text_timezone"
    TIMEZONE_ROW_CHECK_ID = "image_check"

    # ------------------------------------------------------------------ #
    # Screen marker (the System settings close / header area)
    # ------------------------------------------------------------------ #
    CLOSE_BUTTON_ID = "button_close"

    # Known title strings (from R.string)
    TIMEZONE_SETTING_TITLE = "Time Zone"
    PICK_ACTION_TEXT = "PICK"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def is_loaded(self, timeout: int = 10) -> bool:
        """Return True when the system settings list is on screen."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ID, self._id(self.CLOSE_BUTTON_ID))
                )
            )
            return True
        except Exception:
            return False

    def _find_row_by_title(self, title: str):
        """Return the root element for the settings row whose
        text_title matches *title*. Returns None if not found."""
        try:
            rows = self.driver.find_elements(
                AppiumBy.ID, self._id(self.ROW_TITLE_ID)
            )
            for row_title_el in rows:
                if row_title_el.text.strip() == title:
                    return row_title_el
        except Exception as exc:
            log.debug("_find_row_by_title(%s) error: %s", title, exc)
        return None

    def get_timezone_description(self) -> str:
        """Return the current timezone description text shown in the
        Time Zone row (e.g. 'America/New_York')."""
        title_el = self._find_row_by_title(self.TIMEZONE_SETTING_TITLE)
        if title_el is None:
            raise AssertionError("Time Zone setting row not found")
        # The description is a sibling element — find all description
        # elements and match positionally via index in the flat list.
        title_els = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ROW_TITLE_ID)
        )
        desc_els = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ROW_DESCRIPTION_ID)
        )
        for idx, t in enumerate(title_els):
            if t.text.strip() == self.TIMEZONE_SETTING_TITLE:
                if idx < len(desc_els):
                    return desc_els[idx].text.strip()
        raise AssertionError("Time Zone description element not found")

    def tap_timezone_pick_button(self):
        """Tap the PICK action button on the Time Zone row to open
        TimezonePickerDialog."""
        title_els = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ROW_TITLE_ID)
        )
        action_els = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ROW_ACTION_BUTTON_ID)
        )
        for idx, t in enumerate(title_els):
            if t.text.strip() == self.TIMEZONE_SETTING_TITLE:
                if idx < len(action_els):
                    action_els[idx].click()
                    log.info("Tapped PICK on Time Zone row")
                    return
        raise AssertionError("Time Zone PICK button not found")

    def is_timezone_picker_dialog_visible(self, timeout: int = 8) -> bool:
        """Return True when TimezonePickerDialog's recycler is on screen."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ID, self._id(self.TIMEZONE_RECYCLER_ID))
                )
            )
            return True
        except Exception:
            return False

    def get_timezone_rows(self) -> list:
        """Return all visible timezone text elements inside the dialog."""
        return self.driver.find_elements(
            AppiumBy.ID, self._id(self.TIMEZONE_ROW_TEXT_ID)
        )

    def select_timezone_by_id(self, timezone_id: str) -> bool:
        """Scroll the timezone picker until *timezone_id* is visible
        and tap it. Returns True on success.

        The dialog uses a RecyclerView so we may need to scroll to find
        a timezone that is not initially visible.
        """
        max_scrolls = 15
        for attempt in range(max_scrolls):
            rows = self.get_timezone_rows()
            for row_el in rows:
                if timezone_id in row_el.text:
                    row_el.click()
                    log.info("Selected timezone: %s", timezone_id)
                    return True
            # Scroll down inside the recycler
            try:
                recycler = self.driver.find_element(
                    AppiumBy.ID, self._id(self.TIMEZONE_RECYCLER_ID)
                )
                self.driver.execute_script(
                    "mobile: scrollGesture",
                    {
                        "elementId": recycler.id,
                        "direction": "down",
                        "percent": 0.5,
                    },
                )
            except Exception as exc:
                log.debug("Scroll attempt %d failed: %s", attempt, exc)
        log.warning("Timezone %s not found after %d scrolls", timezone_id, max_scrolls)
        return False

    def tap_timezone_cancel(self):
        """Dismiss the timezone picker without making a selection."""
        self.tap_by_id(self.TIMEZONE_CANCEL_BUTTON_ID)
        log.info("Tapped Cancel on TimezonePickerDialog")

    def is_timezone_picker_dismissed(self, timeout: int = 5) -> bool:
        """Return True once the timezone recycler is no longer visible."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(
                    (AppiumBy.ID, self._id(self.TIMEZONE_RECYCLER_ID))
                )
            )
            return True
        except Exception:
            return False
