"""Smoke test — verifies the Studio surface scaffold runs end-to-end.

Confirms:
  - Appium can connect to the Studio
  - The app launches and lands on ProfileActivity
  - Device detection works
  - ProfileActivity renders with at least one profile

Run this first after setup:
    pytest -m studio surfaces/studio/tests/test_00_smoke.py -v

If this passes, every other Studio test has a working foundation.
"""
import logging
from surfaces.studio_android.pages.profile_page import ProfilePage

log = logging.getLogger(__name__)


def test_appium_can_connect(driver):
    """Verify a raw Appium driver can be created. If this fails, Appium
    isn't running, adb isn't connected, capabilities are wrong, or the
    Studio is in kiosk mode (which blocks io.appium.settings)."""
    assert driver is not None
    log.info(f"Session ID: {driver.session_id}")


def test_app_launches_to_profile_activity(driver):
    """Verify the Studio app launches and lands on ProfileActivity.

    This is the fundamental assumption the rest of the test suite relies
    on. If this passes, the page-object element IDs for ProfileActivity
    are correct and fixtures can navigate from any test entry point."""
    profile = ProfilePage(driver)
    profile.wait_for_profile_screen()


def test_profile_screen_has_profiles(driver):
    """Verify at least one profile is visible on ProfileActivity, and
    log the profile names + initials. Useful as a quick health-check
    that the recycler is rendering and the right account(s) are
    configured."""
    profile = ProfilePage(driver)
    profile.wait_for_profile_screen()
    count = profile.profile_count()
    log.info(f"Profile count: {count}")
    for i in range(count):
        log.info(
            f"  [{i}] name={profile.get_profile_name(i)} "
            f"initials={profile.get_profile_initials(i)}"
        )
    assert count >= 1, "ProfileActivity loaded but no profiles visible"


def test_device_is_studio(driver):
    """Report the detected device and confirm it's a FORME Studio."""
    from conftest import DEVICE_PROFILE, DEVICE_MANUFACTURER, DEVICE_MODEL
    log.info(
        f"Device profile: {DEVICE_PROFILE}, "
        f"manufacturer: {DEVICE_MANUFACTURER}, "
        f"model: {DEVICE_MODEL}"
    )
    assert DEVICE_PROFILE == "studio", (
        f"Expected 'studio' device profile, got '{DEVICE_PROFILE}'. "
        f"Manufacturer={DEVICE_MANUFACTURER}, model={DEVICE_MODEL}. "
        f"Override with FORME_DEVICE_PROFILE=studio if running on a test rig."
    )