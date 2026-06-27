"""SettingsPage — Studio settings screen.

Covers sanity tests:
  - FORME-3268: System Settings (High)
  - FORME-3269: Settings (High)
  - FORME-3270: Wifi + Bluetooth toggle functionality (Low)
"""
from surfaces.studio_android.pages.base import StudioBasePage


class SettingsPage(StudioBasePage):
    # TODO: All IDs need confirmation

    def is_loaded(self):
        # TODO: confirm
        return self.is_text_visible("Settings", timeout=5)

    def tap_wifi_toggle(self):
        """FORME-3270: toggle WiFi on/off."""
        raise NotImplementedError("SettingsPage.tap_wifi_toggle()")

    def tap_bluetooth_toggle(self):
        """FORME-3270: toggle BT on/off."""
        raise NotImplementedError("SettingsPage.tap_bluetooth_toggle()")

    def tap_sign_out(self):
        raise NotImplementedError("SettingsPage.tap_sign_out()")
