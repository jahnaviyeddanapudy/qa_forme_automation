"""Appium driver factory — shared across surfaces."""
import os
from appium import webdriver
from appium.options.android import UiAutomator2Options


def create_driver(app_package, app_activity):
    appium_url = os.environ.get("FORME_APPIUM_URL", "http://localhost:4723")
    device_udid = os.environ.get("FORME_DEVICE_UDID", "").strip()

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.app_package = app_package
    options.app_activity = app_activity
    options.no_reset = True
    options.set_capability("appium:disableWindowAnimation", True)
    options.set_capability("appium:ignoreHiddenApiPolicyError", True)
    if device_udid:
        options.set_capability("appium:udid", device_udid)

    d = webdriver.Remote(appium_url, options=options)
    d.update_settings({"enableToastDetection": False, "waitForIdleTimeout": 500})
    return d
