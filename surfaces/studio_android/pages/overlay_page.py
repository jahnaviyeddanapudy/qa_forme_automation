"""OverlayPage — Studio's kiosk-mode overlay back button service.

The OverlayService is a foreground service that draws a small back-button
overlay (R.layout.overlay_back_button) whenever the Studio app goes to the
background (e.g. when Apple Music is launched). Tapping the button returns
the user to the Studio app.

New in this build (commit f016719):
  - setAutoReturnConfig(timeoutMs, enabled) — overlay now auto-returns
    after the same idle window the app would sleep on.
  - ACTION_OUTSIDE touch detection resets the auto-return countdown when
    the user interacts with the foreground app (e.g. Apple Music).
  - consumeInactivityReturn() flag — when the overlay auto-returns due to
    inactivity, BaseActivity immediately starts the sleep countdown instead
    of restarting the full inactivity timer.

Element IDs (from R.layout.overlay_back_button referenced in OverlayService):
  - backButton   — the ImageButton drawn by the overlay service

Because the overlay is drawn via WindowManager TYPE_APPLICATION_OVERLAY
(a system-level window), it appears ABOVE the foreground activity. Appium
with UiAutomator2 can find it through the accessibility hierarchy.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class OverlayPage(StudioBasePage):
    # --- Element IDs (from R.layout.overlay_back_button) ---
    BACK_BUTTON_ID = "backButton"

    # Overlay is a system window — UiAutomator2 finds it via
    # resource-id with full package prefix.
    BACK_BUTTON_RESOURCE_ID = f"{StudioBasePage.APP_PACKAGE}:id/backButton"

    def is_overlay_visible(self, timeout: int = 5) -> bool:
        """Return True if the overlay back button is currently drawn."""
        return self.is_visible(self.BACK_BUTTON_ID, timeout=timeout)

    def wait_for_overlay(self, timeout: int = 15):
        """Block until the overlay back button appears or timeout."""
        log.debug("Waiting for overlay back button to appear")
        wait = WebDriverWait(self.driver, timeout)
        wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ID, self.BACK_BUTTON_RESOURCE_ID)
            )
        )
        log.debug("Overlay back button visible")

    def tap_back_button(self):
        """Tap the overlay back button to return to the Studio app."""
        log.debug("Tapping overlay back button")
        self.tap_by_id(self.BACK_BUTTON_ID)
        log.debug("Overlay back button tapped")

    def wait_for_overlay_gone(self, timeout: int = 10):
        """Block until the overlay back button disappears (app foregrounded)."""
        log.debug("Waiting for overlay to disappear")
        wait = WebDriverWait(self.driver, timeout)
        wait.until_not(
            EC.presence_of_element_located(
                (AppiumBy.ID, self.BACK_BUTTON_RESOURCE_ID)
            )
        )
        log.debug("Overlay gone — app is in foreground")
