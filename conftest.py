import subprocess
import time
import pytest
from appium import webdriver
from appium.options.common import AppiumOptions
from pages.base_page import BasePage
from pages.api_client import get_id_token


def pytest_addoption(parser):
    parser.addoption("--device-name", default="emulator-5554", help="Android device/emulator name")
    parser.addoption("--platform-version", default="12.0", help="Android platform version")
    parser.addoption("--app-path", default=None, help="Path to APK file (triggers fresh install)")
    parser.addoption("--appium-url", default="http://localhost:4723", help="Appium server URL")
    parser.addoption("--env", default="beta", choices=["beta", "prod"], help="Test environment")
    parser.addoption("--email", default=None, help="Login email (overrides built-in default)")
    parser.addoption("--password", default=None, help="Login password (overrides built-in default)")


@pytest.fixture(scope="session", autouse=True)
def configure_credentials(request):
    """Override BasePage default credentials if supplied via CLI."""
    email = request.config.getoption("--email")
    password = request.config.getoption("--password")
    if email:
        BasePage.DEFAULT_EMAIL = email
    if password:
        BasePage.DEFAULT_PASSWORD = password


@pytest.fixture(scope="session")
def appium_url(request):
    return request.config.getoption("--appium-url")


@pytest.fixture(scope="session")
def api_token():
    """Auth0 id_token fetched once per session for direct API verification.

    Uses the same ROPC grant the Android app's UserRepository uses.
    Returns None if authentication fails so individual tests can skip or
    fall back gracefully rather than aborting the entire session.
    """
    try:
        return get_id_token(BasePage.DEFAULT_EMAIL, BasePage.DEFAULT_PASSWORD)
    except Exception:
        return None


@pytest.fixture(scope="session", autouse=True)
def install_app(request):
    """Uninstall existing app and install the provided APK once per session.

    Only runs when --app-path is supplied. Subsequent test functions reuse
    the installed build without reinstalling.
    """
    app_path = request.config.getoption("--app-path")
    if app_path:
        device_name = request.config.getoption("--device-name")
        subprocess.run(
            ["adb", "-s", device_name, "uninstall", "com.formelife.member"],
            capture_output=True,
        )
        subprocess.run(
            ["adb", "-s", device_name, "install", "-r", app_path],
            capture_output=True,
            check=True,
        )
        time.sleep(5)  # allow fresh-installed app to fully initialize


@pytest.fixture(scope="session")
def driver(request, appium_url):
    options = AppiumOptions()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.app_package = "com.formelife.member"
    options.app_activity = "com.formelife.member.activity.StartActivity"
    options.device_name = request.config.getoption("--device-name")
    options.platform_version = request.config.getoption("--platform-version")
    options.new_command_timeout = 120
    options.auto_grant_permissions = True
    options.no_reset = True
    options.full_reset = False

    drv = webdriver.Remote(appium_url, options=options)
    drv.implicitly_wait(10)
    if drv.current_package != "com.formelife.member":
        drv.activate_app("com.formelife.member")

    yield drv

    drv.quit()
