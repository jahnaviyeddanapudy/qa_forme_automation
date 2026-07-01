"""test_50_settings_timezone — Settings › System › Timezone picker tests.

Covers the new timezone picker introduced in commits 27eb5e4 + 031c1a4:

  - test_NEW_timezone_row_visible
      Verify the Time Zone row is present in the System settings list
      and displays a non-empty timezone ID as its description.

  - test_NEW_timezone_picker_dialog_opens
      Verify tapping the PICK button on the Time Zone row opens the
      TimezonePickerDialog (recycler_timezones visible).

  - test_NEW_timezone_picker_cancel_dismisses_dialog
      Verify tapping CANCEL in the timezone picker closes the dialog
      without changing the displayed timezone.

  - test_NEW_timezone_picker_select_timezone
      Select a known timezone (America/Chicago) from the picker,
      verify the Time Zone row description updates to the selected
      timezone ID, and verify the dialog closes.

  - test_NEW_timezone_picker_contains_global_timezones
      Verify the picker contains at least one timezone from each
      major UTC-offset group (spot-checking ALL_TIMEZONES expansion
      from US-only to global).

Architecture:
  Module-scoped shared_driver — login once, all tests share one session.
  Each test calls _navigate_to_system_settings() at the start and
  _return_to_home() at the end so tests are independent in terms of
  screen state.

Pre-conditions:
  - Studio is configured with at least one profile.
  - OWNER_PROFILE_INDEX from config_local.py is valid.

Run all:
    pytest -m studio surfaces/studio_android/tests/test_50_settings_timezone.py -v -s
"""
import pytest
import logging

from surfaces.studio_android.pages.settings_system_page import SettingsSystemPage
from surfaces.studio_android.pages.home_page import HomePage

try:
    from surfaces.studio_android.config_local import OWNER_PROFILE_INDEX
except ImportError:
    OWNER_PROFILE_INDEX = 0

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timezone IDs to exercise in tests (subset of TimezonePickerDialog.ALL_TIMEZONES)
# ---------------------------------------------------------------------------
TZ_TO_SELECT = "America/Chicago"

GLOBAL_TZ_SPOT_CHECK = [
    "America/New_York",        # UTC-5
    "America/Los_Angeles",     # UTC-8
    "Europe/London",           # UTC+0
    "Europe/Paris",            # UTC+1
    "Asia/Tokyo",              # UTC+9
    "Australia/Sydney",        # UTC+10
    "Pacific/Auckland",        # UTC+12
]


# ---------------------------------------------------------------------------
# Module-scoped fixture — login once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def settings_driver():
    """Login as owner and yield a driver already on the Home screen."""
    from surfaces.studio_android.conftest import (
        _create_studio_driver,
        login_at_profile_index,
    )

    driver = _create_studio_driver()
    login_at_profile_index(driver, OWNER_PROFILE_INDEX)
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def _navigate_to_system_settings(driver) -> SettingsSystemPage:
    """From any screen, navigate back to Home then into System settings."""
    _return_to_home(driver)
    home = HomePage(driver)
    home.tap_settings()
    system_page = SettingsSystemPage(driver)
    system_page.tap_by_id("button_system")
    assert system_page.is_loaded(timeout=10), "System settings screen did not load"
    log.info("Navigated to System settings")
    return system_page


def _return_to_home(driver):
    """Close any open settings overlays then wait for Home."""
    from appium.webdriver.common.appiumby import AppiumBy
    home = HomePage(driver)
    # Tap button_close up to 3 times to dismiss system settings → main settings → overlay
    for _ in range(3):
        try:
            close_els = driver.find_elements(
                AppiumBy.ID, f"com.formelife.studio:id/button_close"
            )
            if close_els:
                close_els[0].click()
                import time as _t; _t.sleep(0.8)
            else:
                break
        except Exception:
            break
    # Fall back to back-press if still not on home
    for _ in range(3):
        try:
            if home.is_loaded(timeout=2):
                return
            driver.back()
            import time as _t; _t.sleep(0.8)
        except Exception:
            break


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.studio
def test_NEW_timezone_row_visible(settings_driver):
    """The Time Zone row must appear in the System settings list with a
    non-empty timezone ID as its description."""
    driver = settings_driver
    page = _navigate_to_system_settings(driver)

    try:
        description = page.get_timezone_description()
        log.info("Current timezone description: %s", description)
        assert description, "Time Zone description is empty"
        # Must be a valid Java TimeZone ID format (contains '/' or is 'UTC')
        assert "/" in description or description == "UTC", (
            f"Unexpected timezone description format: {description!r}"
        )
    finally:
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_timezone_picker_dialog_opens(settings_driver):
    """Tapping the PICK button on the Time Zone row must open
    TimezonePickerDialog (recycler_timezones becomes visible)."""
    driver = settings_driver
    page = _navigate_to_system_settings(driver)

    try:
        page.tap_timezone_pick_button()
        assert page.is_timezone_picker_dialog_visible(timeout=8), (
            "TimezonePickerDialog did not appear after tapping PICK"
        )
        log.info("TimezonePickerDialog opened successfully")
    finally:
        # Cancel the dialog if still open before returning
        try:
            if page.is_timezone_picker_dialog_visible(timeout=2):
                page.tap_timezone_cancel()
        except Exception:
            pass
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_timezone_picker_cancel_dismisses_dialog(settings_driver):
    """Tapping CANCEL in the timezone picker must close the dialog
    without changing the displayed timezone."""
    driver = settings_driver
    page = _navigate_to_system_settings(driver)

    try:
        original_tz = page.get_timezone_description()
        log.info("Original timezone before cancel test: %s", original_tz)

        page.tap_timezone_pick_button()
        assert page.is_timezone_picker_dialog_visible(timeout=8), (
            "TimezonePickerDialog did not open"
        )

        page.tap_timezone_cancel()
        assert page.is_timezone_picker_dismissed(timeout=5), (
            "TimezonePickerDialog did not dismiss after tapping Cancel"
        )

        tz_after_cancel = page.get_timezone_description()
        assert tz_after_cancel == original_tz, (
            f"Timezone changed after Cancel: was {original_tz!r}, "
            f"now {tz_after_cancel!r}"
        )
        log.info("Cancel dismissed dialog without changing timezone — OK")
    finally:
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_timezone_picker_select_timezone(settings_driver):
    """Select America/Chicago from the picker. Verify:
    1. The dialog closes automatically after selection.
    2. The Time Zone row description updates to 'America/Chicago'.
    """
    driver = settings_driver
    page = _navigate_to_system_settings(driver)

    original_tz = page.get_timezone_description()
    log.info("Original timezone: %s", original_tz)

    try:
        page.tap_timezone_pick_button()
        assert page.is_timezone_picker_dialog_visible(timeout=8), (
            "TimezonePickerDialog did not open"
        )

        selected = page.select_timezone_by_id(TZ_TO_SELECT)
        assert selected, f"Could not find timezone {TZ_TO_SELECT!r} in the picker"

        # Dialog should auto-dismiss after selection
        assert page.is_timezone_picker_dismissed(timeout=5), (
            "TimezonePickerDialog did not dismiss after selecting a timezone"
        )

        new_tz = page.get_timezone_description()
        log.info("New timezone after selection: %s", new_tz)
        assert new_tz == TZ_TO_SELECT, (
            f"Expected timezone {TZ_TO_SELECT!r} but got {new_tz!r}"
        )
    finally:
        # Best-effort restore to original timezone
        try:
            if page.is_timezone_picker_dialog_visible(timeout=1):
                page.tap_timezone_cancel()
            if page.get_timezone_description() != original_tz:
                page.tap_timezone_pick_button()
                if page.is_timezone_picker_dialog_visible(timeout=6):
                    page.select_timezone_by_id(original_tz)
                    page.is_timezone_picker_dismissed(timeout=5)
        except Exception as restore_exc:
            log.warning("Could not restore original timezone: %s", restore_exc)
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_timezone_picker_contains_global_timezones(settings_driver):
    """Spot-check that the timezone picker contains timezones from
    multiple UTC-offset groups (validates the expansion from US-only
    to the global ALL_TIMEZONES list)."""
    driver = settings_driver
    page = _navigate_to_system_settings(driver)

    try:
        page.tap_timezone_pick_button()
        assert page.is_timezone_picker_dialog_visible(timeout=8), (
            "TimezonePickerDialog did not open"
        )

        found = set()
        max_scrolls = 20
        for _ in range(max_scrolls):
            rows = page.get_timezone_rows()
            for row_el in rows:
                text = row_el.text
                for tz_id in GLOBAL_TZ_SPOT_CHECK:
                    if tz_id in text:
                        found.add(tz_id)
            if len(found) == len(GLOBAL_TZ_SPOT_CHECK):
                break
            # Scroll the recycler down
            try:
                recycler = driver.find_element(
                    "id",
                    f"{driver.capabilities.get('appPackage', 'com.formelife.studio')}:id/recycler_timezones",
                )
                driver.execute_script(
                    "mobile: scrollGesture",
                    {"elementId": recycler.id, "direction": "down", "percent": 0.5},
                )
            except Exception as scroll_exc:
                log.debug("Scroll error during global TZ check: %s", scroll_exc)

        missing = set(GLOBAL_TZ_SPOT_CHECK) - found
        log.info("Found timezones: %s", found)
        assert not missing, (
            f"The following global timezones were not found in the picker: {missing}"
        )
    finally:
        try:
            if page.is_timezone_picker_dialog_visible(timeout=2):
                page.tap_timezone_cancel()
        except Exception:
            pass
        _return_to_home(driver)
