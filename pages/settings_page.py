from pages.base_page import BasePage
from appium.webdriver.common.appiumby import AppiumBy


class SettingsPage(BasePage):

    # Resource IDs from fragment_settings.xml
    HELP_LINK = "setting_help"
    TERMS_LINK = "setting_terms"
    VIEW_ACCOUNT = "setting_view_account"
    PRIVACY_LINK = "setting_privacy"
    SIGN_OUT = "setting_sign_out"
    VERSION = "setting_version"

    def navigate_to_settings(self):
        if self.is_settings_visible():
            return
        self.ensure_logged_in()
        self.go_to_settings()

    def tap_support_help(self):
        self.tap(self.HELP_LINK)

    def tap_terms_of_service(self):
        self.scroll_to_id(self.TERMS_LINK)
        self.tap(self.TERMS_LINK)

    def tap_view_membership(self):
        self.tap(self.VIEW_ACCOUNT)

    def is_settings_visible(self):
        return self.is_text_displayed("Settings")

    def is_help_link_visible(self):
        return self.is_displayed(self.HELP_LINK)

    def is_terms_link_visible(self):
        self.scroll_to_id(self.TERMS_LINK)
        return self.is_displayed(self.TERMS_LINK)

    def is_view_account_visible(self):
        return self.is_displayed(self.VIEW_ACCOUNT)

    def return_to_settings(self):
        """Close the browser/webview and return to the Settings screen."""
        self.go_back()
        self.driver.activate_app(self.APP_PACKAGE)
        self.find_by_text("Settings")

    def is_browser_opened(self):
        """Check if an external browser / webview has been opened."""
        current_package = self.driver.current_package
        browser_packages = [
            "com.android.chrome",
            "org.mozilla.firefox",
            "com.microsoft.emmx",
            "com.android.browser",
        ]
        return any(pkg in current_package for pkg in browser_packages)

    def is_webview_displayed(self):
        """Check for an in-app WebView (fallback when browser stays in-app)."""
        return len(self.driver.find_elements(AppiumBy.CLASS_NAME, "android.webkit.WebView")) > 0
