"""SetupWizardPage — first-run Studio setup flow.

Runs the first time the Studio boots after factory reset or after
`adb shell pm clear com.formelife.studio`. Covers:
  - FORME-3286: Sign in to Station / Register Studio to Membership
  - FORME-3287: Wi-Fi Setup
  - FORME-3288: Headphones Pairing Test
  - FORME-3289: HRM Pairing

Tests for this flow should be marked @pytest.mark.first_run_only and
excluded from the default pytest invocation — running them trashes the
Studio's persisted auto-login state, which most other tests depend on.

Run them manually like:
    pytest -m "studio and first_run_only" surfaces/studio/tests/test_01_setup_wizard.py

This file is a placeholder — actual implementation needs a first-run
Studio to inspect element IDs and flow.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log  # noqa: F401


class SetupWizardPage(StudioBasePage):
    # TODO: All IDs in this file need confirmation via tools/dump_screen.py
    # on a Studio that's been reset to first-run state.

    def wait_for_welcome_screen(self):
        """Wait for the Setup Wizard's first screen to render."""
        raise NotImplementedError(
            "SetupWizardPage.wait_for_welcome_screen() needs real element "
            "IDs — inspect a first-run Studio and fill in."
        )

    def tap_wifi_network(self, ssid):
        """FORME-3287: select Wi-Fi network during setup."""
        raise NotImplementedError("SetupWizardPage.tap_wifi_network()")

    def enter_wifi_password(self, password):
        raise NotImplementedError("SetupWizardPage.enter_wifi_password()")

    def scan_qr_code_for_sign_in(self, qr_image_path):
        """FORME-3286: sign in via QR code.
        Studio shows a QR code that a phone scans to authorize the login."""
        raise NotImplementedError("SetupWizardPage.scan_qr_code_for_sign_in()")

    def enter_manual_credentials(self, email, password):
        """Fallback if Studio offers a text-input sign-in (not just QR)."""
        raise NotImplementedError("SetupWizardPage.enter_manual_credentials()")

    def pair_headphones(self, device_name):
        """FORME-3288: pair Bluetooth headphones during setup."""
        raise NotImplementedError("SetupWizardPage.pair_headphones()")

    def pair_hrm(self, device_name):
        """FORME-3289: pair HRM during setup."""
        raise NotImplementedError("SetupWizardPage.pair_hrm()")

    def tap_continue(self):
        """Advance to the next wizard step."""
        raise NotImplementedError("SetupWizardPage.tap_continue()")

    def is_setup_complete(self):
        """Return True when the wizard has finished."""
        raise NotImplementedError("SetupWizardPage.is_setup_complete()")
