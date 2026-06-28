"""test_40_overlay_service — OverlayService auto-return and inactivity tests.

Covers the new OverlayService behaviour introduced in commit f016719:

  - test_NEW_overlay_shown_when_app_backgrounds
      Verify the overlay back button appears when Studio goes to background.

  - test_NEW_overlay_back_button_returns_to_app
      Verify tapping the overlay back button brings the Studio app back to
      the foreground and the overlay disappears.

  - test_NEW_overlay_hidden_when_app_foregrounds
      Verify the overlay is automatically hidden (via OverlayService.hide())
      when Studio comes back to the foreground (e.g. after tapping the back
      button or after auto-return).

  - test_NEW_overlay_not_shown_when_app_is_foreground
      Verify the overlay back button is NOT visible while Studio is the
      foreground app (normal browsing state).

How overlay backgrounding works on a kiosk device:
  The Studio app uses App.onAppBackgrounded() (LifecycleEvent.ON_STOP) to
  call OverlayService.show(). In a real scenario this happens when the user
  opens Apple Music. In Appium tests we simulate backgrounding by pressing
  the Android HOME key via driver.press_keycode(3) and check that the
  overlay appears in the system window layer. We then bring the app back
  via the overlay back button or via driver.activate_app().

Pre-conditions:
  - Studio must already be running and the user must be logged in on the
    Home screen (use the first_profile_driver fixture which handles login).
  - The device must have "Draw over other apps" permission granted
    (Settings.canDrawOverlays returns true — standard kiosk setup).

Limitations:
  - The overlay is drawn in a TYPE_APPLICATION_OVERLAY window. UiAutomator2
    can see system-window elements but ONLY when the Studio package granted
    the SYSTEM_ALERT_WINDOW permission (standard for kiosk).
  - These tests are tagged @pytest.mark.studio and will be skipped on
    non-kiosk emulators that lack the overlay permission.

Run:
    pytest -m studio surfaces/studio_android/tests/test_40_overlay_service.py -v -s
"""
import time
import pytest

from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.overlay_page import OverlayPage

# Android key-codes
KEYCODE_HOME = 3


@pytest.mark.studio
def test_NEW_overlay_shown_when_app_backgrounds(first_profile_driver):
    """Verify the overlay back button appears when Studio goes to background.

    Steps:
      1. Confirm we are on the Home screen (Studio is foreground).
      2. Press HOME to send Studio to the background.
      3. Wait up to 10 s for the overlay back button to appear in the
         system window layer.
      4. Restore Studio to the foreground for teardown.
    """
    driver = first_profile_driver
    home = HomePage(driver)
    overlay = OverlayPage(driver)

    # 1. Confirm Home loaded
    assert home.is_loaded(), "Expected to start on Home screen"

    # 2. Send Studio to background
    driver.press_keycode(KEYCODE_HOME)
    time.sleep(1)  # allow App.onAppBackgrounded() to fire

    try:
        # 3. Overlay should appear
        overlay.wait_for_overlay(timeout=10)
        assert overlay.is_overlay_visible(timeout=3), (
            "Overlay back button not visible after Studio backgrounded"
        )
    finally:
        # 4. Always restore Studio so subsequent tests start clean
        driver.activate_app("com.formelife.studio")
        time.sleep(2)


@pytest.mark.studio
def test_NEW_overlay_back_button_returns_to_app(first_profile_driver):
    """Verify tapping the overlay back button brings Studio to the foreground.

    Steps:
      1. Confirm Home loaded.
      2. Background Studio (HOME key).
      3. Wait for overlay to appear.
      4. Tap the overlay back button.
      5. Verify the overlay disappears.
      6. Verify Studio Home is visible again.
    """
    driver = first_profile_driver
    home = HomePage(driver)
    overlay = OverlayPage(driver)

    # 1. Confirm start state
    assert home.is_loaded(), "Expected to start on Home screen"

    # 2. Background the app
    driver.press_keycode(KEYCODE_HOME)
    time.sleep(1)

    # 3. Wait for overlay
    overlay.wait_for_overlay(timeout=10)
    assert overlay.is_overlay_visible(timeout=3), (
        "Overlay back button not visible — cannot test tap behaviour"
    )

    # 4. Tap the back button
    overlay.tap_back_button()

    # 5. Overlay should disappear
    overlay.wait_for_overlay_gone(timeout=8)
    assert not overlay.is_overlay_visible(timeout=2), (
        "Overlay still visible after tapping back button"
    )

    # 6. Studio Home should be back
    time.sleep(2)  # allow foreground transition to complete
    assert home.is_loaded(), (
        "Studio Home not visible after tapping overlay back button"
    )


@pytest.mark.studio
def test_NEW_overlay_hidden_when_app_foregrounds(first_profile_driver):
    """Verify overlay is hidden when Studio comes back to the foreground.

    This specifically validates App.onAppForegrounded() → OverlayService.hide().

    Steps:
      1. Confirm Home.
      2. Background Studio.
      3. Wait for overlay.
      4. Activate Studio via driver.activate_app() (simulates user returning
         via task-switcher, not via the overlay button).
      5. Verify overlay is gone.
    """
    driver = first_profile_driver
    home = HomePage(driver)
    overlay = OverlayPage(driver)

    assert home.is_loaded(), "Expected to start on Home screen"

    driver.press_keycode(KEYCODE_HOME)
    time.sleep(1)

    overlay.wait_for_overlay(timeout=10)

    # Return to Studio without tapping the overlay button
    driver.activate_app("com.formelife.studio")
    time.sleep(2)  # allow onAppForegrounded() lifecycle to fire

    # Overlay should be hidden by OverlayService.hide()
    assert not overlay.is_overlay_visible(timeout=3), (
        "Overlay back button still visible after Studio came to foreground"
    )

    assert home.is_loaded(), "Studio Home not visible after re-foregrounding"


@pytest.mark.studio
def test_NEW_overlay_not_shown_when_app_is_foreground(first_profile_driver):
    """Verify the overlay back button is NOT shown while Studio is foreground.

    Regression guard: overlay must only appear when Studio is backgrounded,
    never during normal in-app navigation.

    Steps:
      1. Confirm Home.
      2. Check that the overlay back button is not visible.
      3. Navigate to STUDIO tab and back — overlay must stay hidden.
    """
    driver = first_profile_driver
    home = HomePage(driver)
    overlay = OverlayPage(driver)

    assert home.is_loaded(), "Expected Home screen"

    # Overlay must not be visible while Studio is foreground
    assert not overlay.is_overlay_visible(timeout=3), (
        "Overlay back button is visible while Studio is in the foreground"
    )

    # Navigate to STUDIO tab
    home.tap_studio_tab()
    time.sleep(1)

    # Still must not be visible
    assert not overlay.is_overlay_visible(timeout=3), (
        "Overlay back button appeared after navigating to STUDIO tab"
    )

    # Return to YOUR PLAN
    home.tap_your_plan_tab()
    time.sleep(1)

    assert not overlay.is_overlay_visible(timeout=3), (
        "Overlay back button appeared after navigating back to YOUR PLAN tab"
    )
