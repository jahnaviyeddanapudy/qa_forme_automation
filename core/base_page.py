"""Generic cross-surface base page. Surface-specific subclasses set APP_PACKAGE."""
import time
import logging
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


class BasePage:
    APP_PACKAGE = None
    WAIT_DEFAULT = 15

    def __init__(self, driver):
        if self.APP_PACKAGE is None:
            raise RuntimeError(f"{self.__class__.__name__} must set APP_PACKAGE.")
        self.driver = driver
        self.wait = WebDriverWait(driver, self.WAIT_DEFAULT)

    def by_id(self, resource_id):
        return (AppiumBy.ID, f"{self.APP_PACKAGE}:id/{resource_id}")

    def _id(self, resource_id):
        return f"{self.APP_PACKAGE}:id/{resource_id}"

    def find_by_id(self, resource_id, timeout=None):
        w = WebDriverWait(self.driver, timeout or self.WAIT_DEFAULT)
        return w.until(EC.presence_of_element_located(self.by_id(resource_id)))

    def find_all_by_id(self, resource_id):
        return self.driver.find_elements(AppiumBy.ID, f"{self.APP_PACKAGE}:id/{resource_id}")

    def tap_by_id(self, resource_id, timeout=None):
        w = WebDriverWait(self.driver, timeout or self.WAIT_DEFAULT)
        el = w.until(EC.element_to_be_clickable(self.by_id(resource_id)))
        el.click()

    def tap_by_text(self, text, timeout=None):
        w = WebDriverWait(self.driver, timeout or self.WAIT_DEFAULT)
        el = w.until(EC.element_to_be_clickable((AppiumBy.XPATH, f"//*[@text='{text}']")))
        el.click()

    def is_visible(self, resource_id, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.by_id(resource_id))
            )
            return True
        except Exception:
            return False

    def is_text_visible(self, text, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((AppiumBy.XPATH, f"//*[@text='{text}']"))
            )
            return True
        except Exception:
            return False

    def input_text(self, resource_id, text, timeout=None):
        el = self.find_by_id(resource_id, timeout)
        el.click()
        el.clear()
        el.send_keys(text)

    def scroll_down(self):
        size = self.driver.get_window_size()
        x = size["width"] // 2
        self.driver.swipe(x, int(size["height"] * 0.7), x, int(size["height"] * 0.3), 800)

    def scroll_up(self):
        size = self.driver.get_window_size()
        x = size["width"] // 2
        self.driver.swipe(x, int(size["height"] * 0.3), x, int(size["height"] * 0.7), 800)

    def wait_seconds(self, seconds):
        time.sleep(seconds)

    def go_back(self):
        self.driver.back()
