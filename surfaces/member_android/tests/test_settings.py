"""
Settings test cases
FORME-1728 | FORME-1730 | FORME-1733
"""
import pytest
from surfaces.member_android.pages.settings_page import SettingsPage


@pytest.fixture(autouse=True)
def settings(driver):
    page = SettingsPage(driver)
    page.navigate_to_settings()
    return page


class TestSettings:

    def test_FORME_1728_support_link_redirects_to_support_page(self, driver, settings):
        """
        FORME-1728: Verify support link redirects user to support page.
        Steps:
          1. Navigate to Settings.
          2. Tap Help under Support section.
          3. Verify external support page or in-app WebView opens.
        """
        assert settings.is_help_link_visible(), "Help link is not visible in Settings"
        settings.tap_support_help()
        settings.wait_seconds(2)
        assert (
            settings.is_browser_opened() or settings.is_webview_displayed()
        ), "Support page was not opened after tapping Help link"
        settings.return_to_settings()

    def test_FORME_1730_terms_of_service_link_redirects_to_tos(self, driver, settings):
        """
        FORME-1730: Verify 'Terms of Service' link redirects user to latest ToS URL.
        Steps:
          1. Navigate to Settings.
          2. Tap Terms of Service under Policies section.
          3. Verify the Terms of Service page opens in browser/WebView.
        """
        assert settings.is_terms_link_visible(), "Terms of Service link is not visible in Settings"
        settings.tap_terms_of_service()
        settings.wait_seconds(2)
        assert (
            settings.is_browser_opened() or settings.is_webview_displayed()
        ), "Terms of Service page was not opened after tapping the link"
        settings.return_to_settings()

    def test_FORME_1733_view_membership_button_available_and_redirects(self, driver, settings):
        """
        FORME-1733: View Membership details button should be available and redirect to Webapp.
        Steps:
          1. Navigate to Settings.
          2. Verify 'View Account Details' is visible under Account section.
          3. Tap it and verify browser/WebView opens.
        """
        assert settings.is_view_account_visible(), "View Account Details button is not visible in Settings"
        settings.tap_view_membership()
        settings.wait_seconds(2)
        assert (
            settings.is_browser_opened() or settings.is_webview_displayed()
        ), "Membership web app was not opened after tapping View Account Details"
        settings.return_to_settings()
