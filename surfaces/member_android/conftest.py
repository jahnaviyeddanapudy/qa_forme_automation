"""Member Android surface fixtures."""
import subprocess
import time
import pytest
from appium import webdriver
from appium.options.common import AppiumOptions
from surfaces.member_android.config import APP_PACKAGE, APP_ACTIVITY
from surfaces.member_android.pages.base import MemberAndroidBasePage
from surfaces.member_android.pages.api_client import get_id_token


def pytest_addoption(parser):
    parser.addoption("--device-name", default="emulator-5554")
    parser.addoption("--platform-version", default="12.0")
    parser.addoption("--app-path", default=None)
    parser.addoption("--appium-url", default="http://localhost:4723")
    parser.addoption("--env", default="beta", choices=["beta", "prod"])
    parser.addoption("--email", default=None)
    parser.addoption("--password", default=None)


@pytest.fixture(scope="session", autouse=True)
def configure_credentials(request):
    email = request.config.getoption("--email")
    password = request.config.getoption("--password")
    if email:
        MemberAndroidBasePage.DEFAULT_EMAIL = email
    if password:
        MemberAndroidBasePage.DEFAULT_PASSWORD = password


@pytest.fixture(scope="session")
def api_token():
    try:
        return get_id_token(MemberAndroidBasePage.DEFAULT_EMAIL, MemberAndroidBasePage.DEFAULT_PASSWORD)
    except Exception:
        return None


@pytest.fixture(scope="session", autouse=True)
def install_app(request):
    app_path = request.config.getoption("--app-path")
    if app_path:
        device_name = request.config.getoption("--device-name")
        subprocess.run(["adb", "-s", device_name, "uninstall", APP_PACKAGE], capture_output=True)
        subprocess.run(["adb", "-s", device_name, "install", "-r", app_path], capture_output=True, check=True)
        time.sleep(5)


@pytest.fixture(scope="session")
def driver(request):
    options = AppiumOptions()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.app_package = APP_PACKAGE
    options.app_activity = APP_ACTIVITY
    options.device_name = request.config.getoption("--device-name")
    options.platform_version = request.config.getoption("--platform-version")
    options.new_command_timeout = 120
    options.auto_grant_permissions = True
    options.no_reset = True
    options.full_reset = False

    appium_url = request.config.getoption("--appium-url")
    drv = webdriver.Remote(appium_url, options=options)
    drv.implicitly_wait(10)
    if drv.current_package != APP_PACKAGE:
        drv.activate_app(APP_PACKAGE)

    yield drv
    drv.quit()
