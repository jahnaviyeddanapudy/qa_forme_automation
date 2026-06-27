from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time


class BasePage:
    DEFAULT_TIMEOUT = 15
    IMPLICIT_WAIT = 10  # must match drv.implicitly_wait(10) in conftest.py
    APP_PACKAGE = "com.formelife.member"

    # Login screen resource IDs (fragment_setup_signin.xml)
    LOGIN_EMAIL_FIELD = "edit_email"
    LOGIN_PASSWORD_FIELD = "edit_password"
    LOGIN_BUTTON = "sign_in_button"

    # Default credentials
    DEFAULT_EMAIL = "jahnavi.yeddanapudy+prod_client@formelife.com"
    DEFAULT_PASSWORD = "Jahnavi23!"

    # Onboarding screens
    GET_STARTED_BUTTON = "button_get_started"       # fragment_onboarding_get_started.xml
    USE_PASSWORD_BUTTON = "button_use_password"     # fragment_passwordless_signin.xml

    # Bottom nav tab resource IDs (fragment_browse_header.xml)
    TAB_YOUR_PLAN = "tab_your_plan"
    TAB_STUDIO = "tab_studio"
    TAB_LIVE = "tab_live"
    TAB_MESSAGES = "tab_messages"
    TAB_MORE = "tab_more"

    # Profile & settings navigation
    PROFILE_BUTTON = "header_profile_button"
    SETTINGS_BUTTON = "button_settings"

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, self.DEFAULT_TIMEOUT)

    # --- Finders ---

    def find_by_id(self, resource_id, timeout=DEFAULT_TIMEOUT):
        locator = f"{self.APP_PACKAGE}:id/{resource_id}"
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, locator))
        )

    def find_by_text(self, text, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().text("{text}")'))
        )

    def find_by_text_contains(self, text, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().textContains("{text}")'))
        )

    def find_by_content_desc(self, desc, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionContains("{desc}")'))
        )

    def find_by_xpath(self, xpath, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath))
        )

    # --- Interactions ---

    def tap(self, resource_id, timeout=DEFAULT_TIMEOUT):
        self.find_by_id(resource_id, timeout).click()

    def tap_text(self, text, timeout=DEFAULT_TIMEOUT):
        self.find_by_text(text, timeout).click()

    def tap_text_contains(self, text, timeout=DEFAULT_TIMEOUT):
        self.find_by_text_contains(text, timeout).click()

    def type_text(self, resource_id, text, timeout=DEFAULT_TIMEOUT):
        # edit_email / edit_password are FormeEditText FrameLayout wrappers — the actual
        # AppCompatEditText sits inside as a child with id "edit". Click the wrapper to
        # focus it, then send keys to the inner EditText.
        el = self.find_by_id(resource_id, timeout)
        el.click()
        try:
            inner = el.find_element(AppiumBy.ID, f"{self.APP_PACKAGE}:id/edit")
            inner.clear()
            inner.send_keys(text)
        except NoSuchElementException:
            el.clear()
            el.send_keys(text)

    def _find_elements_fast(self, by, value):
        """find_elements with implicit wait temporarily set to 0.

        Selenium 4 / Appium makes find_elements block for the full implicit-wait
        timeout (10 s) before returning [].  This helper disables implicit wait
        for the call so "quick" polling loops don't accumulate minutes of delay.
        """
        self.driver.implicitly_wait(0)
        try:
            return self.driver.find_elements(by, value)
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

    def is_displayed(self, resource_id, timeout=5):
        try:
            el = self.find_by_id(resource_id, timeout)
            return el.is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    def is_text_displayed(self, text, timeout=5):
        try:
            el = self.find_by_text(text, timeout)
            return el.is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    def is_text_contains_displayed(self, text, timeout=5):
        try:
            el = self.find_by_text_contains(text, timeout)
            return el.is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    def get_text(self, resource_id, timeout=DEFAULT_TIMEOUT):
        return self.find_by_id(resource_id, timeout).text

    def go_back(self):
        self.driver.back()

    def scroll_to_id(self, resource_id):
        """Scroll until the element with resource_id is visible on screen."""
        locator = (
            f'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().resourceId("{self.APP_PACKAGE}:id/{resource_id}"))'
        )
        self.driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, locator)

    # --- Gestures ---

    def swipe_up(self):
        size = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.8)
        end_y = int(size["height"] * 0.2)
        self.driver.swipe(start_x, start_y, start_x, end_y, 600)

    def swipe_down(self):
        size = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.2)
        end_y = int(size["height"] * 0.8)
        self.driver.swipe(start_x, start_y, start_x, end_y, 600)

    def wait_seconds(self, seconds):
        time.sleep(seconds)

    def keep_alive_wait(self, seconds, interval=15):
        """Sleep for *seconds* while sending a brief Appium query every *interval*
        seconds to prevent session timeout (newCommandTimeout = 120 s by default).
        Use instead of wait_seconds() for any sleep longer than ~50 seconds.
        """
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            chunk = min(interval, end - time.monotonic())
            time.sleep(max(0, chunk))
            if time.monotonic() < end:
                self._find_elements_fast(
                    AppiumBy.ID, f"{self.APP_PACKAGE}:id/text_class_time"
                )

    # --- App lifecycle ---

    def launch_app(self):
        self.driver.activate_app(self.APP_PACKAGE)

    def successful_login(self, email=None, password=None):
        self.type_text(self.LOGIN_EMAIL_FIELD, email or self.DEFAULT_EMAIL)
        self.type_text(self.LOGIN_PASSWORD_FIELD, password or self.DEFAULT_PASSWORD)
        self.tap(self.LOGIN_BUTTON)
        self.wait_for_main_nav()

    def dismiss_onboarding_if_present(self):
        """Navigate through onboarding screens to reach the email/password login form.

        Flow: Get Started → passwordless sign-in → (tap Use Password) → password sign-in.
        After a fresh install the app takes longer to render each screen, so timeouts
        and inter-step waits are generous.
        """
        # Step 1: Get Started screen (fragment_onboarding_get_started.xml)
        if self.is_displayed(self.GET_STARTED_BUTTON, timeout=10):
            self.tap(self.GET_STARTED_BUTTON)
            self.wait_seconds(3)  # allow passwordless sign-in screen to fully load
        # Step 2: Passwordless sign-in (fragment_passwordless_signin.xml) — switch to password
        if self.is_displayed(self.USE_PASSWORD_BUTTON, timeout=10):
            self.tap(self.USE_PASSWORD_BUTTON)
            self.wait_seconds(2)  # allow password sign-in screen to fully load

    def ensure_logged_in(self):
        """Advance past onboarding and log in if not already on the main nav."""
        # 20s covers cold app launch when the session is already authenticated
        try:
            self.wait_for_main_nav(timeout=20)
            return
        except TimeoutException:
            pass
        # Onboarding detected early (fresh install) — go straight to login without
        # pressing back, which would push the user off the onboarding screens or exit the app.
        if self.is_displayed(self.GET_STARTED_BUTTON, timeout=3) or \
                self.is_displayed(self.USE_PASSWORD_BUTTON, timeout=3):
            self.dismiss_onboarding_if_present()
            try:
                self.wait_for_main_nav(timeout=5)
                return
            except TimeoutException:
                pass
            self.successful_login()
            return
        # InClassActivity: tap the screen to reveal the end-session button, then tap it.
        # text_class_time is always visible during an active CPS session.
        if self.is_displayed("text_class_time", timeout=3):
            size = self.driver.get_window_size()
            self.driver.tap([(size["width"] // 2, size["height"] // 2)])
            time.sleep(1)
            if self.is_displayed("button_end_class", timeout=5):
                self.tap("button_end_class")
                time.sleep(2)
        # Press back up to 5 times to escape any remaining deep screen (dialogs, surveys).
        for _ in range(5):
            self.go_back()
            try:
                self.wait_for_main_nav(timeout=3)
                return
            except TimeoutException:
                pass
        # Not on main nav — work through onboarding/login screens
        self.dismiss_onboarding_if_present()
        try:
            self.wait_for_main_nav(timeout=5)
            return
        except TimeoutException:
            pass
        self.successful_login()

    # --- Navigation ---

    def wait_for_main_nav(self, timeout=20):
        """Poll all bottom nav tab IDs within a single shared timeout window."""
        end_time = time.monotonic() + timeout
        while time.monotonic() < end_time:
            for tab_id in (self.TAB_YOUR_PLAN, self.TAB_STUDIO, self.TAB_LIVE,
                           self.TAB_MESSAGES, self.TAB_MORE):
                try:
                    els = self.driver.find_elements(
                        AppiumBy.ID, f"{self.APP_PACKAGE}:id/{tab_id}"
                    )
                    if els and els[0].is_displayed():
                        return
                except Exception:
                    pass
            time.sleep(0.5)
        raise TimeoutException("Main navigation bar did not appear within timeout")

    def go_to_studio_tab(self):
        self.tap(self.TAB_STUDIO)

    def go_to_plan_tab(self):
        self.tap(self.TAB_YOUR_PLAN)

    def go_to_messages_tab(self):
        self.tap(self.TAB_MESSAGES)

    def go_to_live_tab(self):
        self.tap(self.TAB_LIVE)

    def go_to_settings(self):
        """Navigate to Settings via profile button → Settings button.
        For prod_client (has trainer): profile_button overlays the Messages tab.
        For accounts without trainer: tap the More tab, then Settings button.
        """
        try:
            self.tap(self.PROFILE_BUTTON)
        except (TimeoutException, NoSuchElementException, WebDriverException):
            self.tap(self.TAB_MORE)
        self.tap(self.SETTINGS_BUTTON)
