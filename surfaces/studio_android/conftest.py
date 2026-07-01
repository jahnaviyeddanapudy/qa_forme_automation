"""FORME Studio device app — surface-specific pytest configuration.

Provides:
  - create_driver wiring to com.formelife.studio / ProfileActivity
  - fixtures: driver, profile_driver,
              first_profile_driver, second_profile_driver  (positional),
              owner_driver, guest1_driver                   (semantic)
  - login_at_profile_index() helper — handles auto-login OR Sign In prompt

Tests under this folder auto-get @pytest.mark.studio so `pytest -m studio`
runs only these tests.

ProfileActivity model:
  - Studio boots to ProfileActivity every launch
  - Profiles are POSITIONAL — recycler order is whatever Studio decides
  - Tapping a profile may auto-login OR show Sign In prompt
  - Each QA configures their Studio's account → recycler-index mapping
    via OWNER_PROFILE_INDEX / GUEST1_PROFILE_INDEX in surfaces/studio_android/
    config.py (or via env vars STUDIO_OWNER_PROFILE_INDEX /
    STUDIO_GUEST1_PROFILE_INDEX)

Two fixture flavors:
  - POSITIONAL: first_profile_driver (index 0), second_profile_driver
    (index 1). Use these when the test cares about which recycler
    *position* is being tapped (e.g. ProfileActivity behavior tests,
    add/remove guest tests, smoke test).
  - SEMANTIC: owner_driver, guest1_driver. Use these when the test cares
    about which *account* is logging in (e.g. weekly-plan-only tests,
    no-schedule-only tests). The mapping from semantic name to recycler
    index is read from config so tests stay portable across Studios.
"""
import time
import subprocess
import pytest
from appium.webdriver.common.appiumby import AppiumBy

from core.driver_factory import create_driver
from core.adb_helpers import adb_cmd

from surfaces.studio_android.config import (
    APP_PACKAGE,
    APP_ACTIVITY,
    STUDIO_PASSWORD,
    OWNER_PROFILE_INDEX,
    GUEST1_PROFILE_INDEX,
)
from surfaces.studio_android.pages.profile_page import ProfilePage
from surfaces.studio_android.pages.sign_in_page import SignInPage
from surfaces.studio_android.pages.home_page import HomePage


# --- Test marker ---
def pytest_collection_modifyitems(config, items):
    for item in items:
        if "surfaces/studio_android/tests" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.studio)


def skip_if_not_studio(reason=None):
    from conftest import DEVICE_PROFILE
    if DEVICE_PROFILE != "studio":
        default_reason = (
            f"Test requires the FORME Studio device "
            f"(detected profile: {DEVICE_PROFILE}). "
            f"Override with FORME_DEVICE_PROFILE=studio if needed."
        )
        pytest.skip(reason or default_reason)


def _recover_from_class_state(driver):
    """End any mid-class state cleanly: player → end-session → close
    rating → close summary → home. Best-effort; tolerant of missing
    screens.

    Element IDs and screen markers are TODO until Studio class flow is
    confirmed."""
    home = HomePage(driver)

    player_visible = home.is_visible("player_class", timeout=2)
    rating_visible = home.is_text_visible("SESSION FEEDBACK", timeout=2)
    summary_visible = home.is_text_visible("YOUR FORME WEEK", timeout=2)

    if not (player_visible or rating_visible or summary_visible):
        return False

    print("[recovery] detected mid-class state — ending class cleanly")

    if player_visible:
        try:
            size = driver.get_window_size()
            driver.tap([(size['width'] // 2, size['height'] // 2)])
            time.sleep(2)
            driver.find_element(AppiumBy.ID,
                                f"{APP_PACKAGE}:id/button_end_class").click()
            print("[recovery] tapped end_class from player")
            time.sleep(3)
        except Exception as e:
            print(f"[recovery] could not end from player: {e}")

    if home.is_text_visible("SESSION FEEDBACK", timeout=3):
        try:
            driver.find_element(AppiumBy.ID,
                                f"{APP_PACKAGE}:id/button_close").click()
            print("[recovery] closed rating (skipped)")
            time.sleep(2)
        except Exception as e:
            print(f"[recovery] could not close rating: {e}")

    if home.is_text_visible("YOUR FORME WEEK", timeout=3):
        try:
            driver.find_element(AppiumBy.ID,
                                f"{APP_PACKAGE}:id/button_close").click()
            print("[recovery] closed summary")
            time.sleep(2)
        except Exception as e:
            print(f"[recovery] could not close summary: {e}")

    return True


def get_to_profile_screen(driver):
    """Navigate to ProfileActivity from any app state."""
    profile = ProfilePage(driver)
    sign_in = SignInPage(driver)

    # Fast path
    if profile.is_loaded(timeout=2):
        return

    # Cancel out of Sign In if we're stuck there
    if sign_in.is_visible(timeout=2):
        sign_in.cancel()
        time.sleep(1)
        if profile.is_loaded(timeout=3):
            return

    # Recover from any mid-class state
    _recover_from_class_state(driver)

    # Back-button up to 6 times to reach ProfileActivity
    for _ in range(6):
        if profile.is_loaded(timeout=2):
            return
        driver.back()
        time.sleep(1)

    # Last resort: force-stop + relaunch via LAUNCHER intent — guaranteed
    # to land on ProfileActivity.
    try:
        subprocess.run(
            adb_cmd("shell", "am", "force-stop", APP_PACKAGE),
            capture_output=True, text=True, timeout=5,
        )
        time.sleep(1)
        subprocess.run(
            adb_cmd(
                "shell", "monkey", "-p", APP_PACKAGE,
                "-c", "android.intent.category.LAUNCHER", "1",
            ),
            capture_output=True, text=True, timeout=5,
        )
        time.sleep(3)
        profile.wait_for_profile_screen()
    except Exception as e:
        raise RuntimeError(
            f"Could not reach ProfileActivity after force-stop + relaunch: {e}"
        )


def login_at_profile_index(driver, profile_index, password=None,
                           role_label=None):
    """Tap the profile at the given recycler index and handle either
    auto-login or Sign In prompt. Returns the driver after home loads.

    Args:
        profile_index: which recycler position to tap (0, 1, 2, ...)
        password: required if Sign In prompt appears. Defaults to
                  STUDIO_PASSWORD from config.
        role_label: optional semantic label for log output (e.g. "OWNER",
                    "GUEST 1"). When provided, logs read like:
                        [login] Logging in as OWNER (profile index 1) → SILVANUS
                    Without role_label, logs use the raw index:
                        [login] [1] 'SILVANUS' auto-logged in (no Sign In prompt)

    Recycler order is whatever the Studio app returns — see
    profile_page.py docstring. Tests / fixtures decide which index
    corresponds to which logical account."""
    if password is None:
        password = STUDIO_PASSWORD

    get_to_profile_screen(driver)
    profile = ProfilePage(driver)
    home = HomePage(driver)
    sign_in = SignInPage(driver)

    profile_name = profile.get_profile_name(profile_index)

    if role_label:
        print(f"[login] Logging in as {role_label} "
              f"(profile index {profile_index}) → {profile_name}")

    profile.tap_profile_at(profile_index)
    time.sleep(2)

    # Branch: auto-login or password prompt?
    if sign_in.is_visible(timeout=3):
        if role_label:
            print(f"[login] Sign In prompt appeared — entering password")
        else:
            print(f"[login] Sign In prompt for [{profile_index}] "
                  f"'{profile_name}' — entering password")
        sign_in.enter_password(password)
        sign_in.submit()
    else:
        if not role_label:
            print(f"[login] [{profile_index}] '{profile_name}' "
                  f"auto-logged in (no Sign In prompt)")
        # else: already logged the role_label header; skip a second line

    home.wait_for_home()
    return driver


def _create_studio_driver():
    return create_driver(APP_PACKAGE, APP_ACTIVITY)


# =========================================================
# Fixtures
# =========================================================

@pytest.fixture(scope="function")
def driver():
    """Raw Appium driver, no login. Use for tests interacting with
    ProfileActivity itself or for the smoke test."""
    d = _create_studio_driver()
    yield d
    d.quit()


@pytest.fixture(scope="function")
def profile_driver(driver):
    """Driver that has confirmed ProfileActivity is loaded but has NOT
    tapped a profile. Use for tests exercising ProfileActivity itself
    (profile counts, add/remove guests, post-boot state)."""
    get_to_profile_screen(driver)
    return driver


# --- Positional fixtures (use when test cares about recycler position) ---

@pytest.fixture(scope="function")
def first_profile_driver(driver):
    """Driver logged in as the first profile in the recycler (index 0).
    Tests must not assume which actual account this is — depends on the
    Studio's setup. Use this for tests that care about the *position*,
    not the *identity*, of the profile (e.g. ProfileActivity tests,
    smoke tests). For identity-based tests, prefer owner_driver /
    guest1_driver."""
    return login_at_profile_index(driver, profile_index=0)


@pytest.fixture(scope="function")
def second_profile_driver(driver):
    """Driver logged in as the second profile (index 1). Will fail with
    IndexError if the Studio only has one profile configured. See
    first_profile_driver for usage notes."""
    return login_at_profile_index(driver, profile_index=1)


# --- Semantic fixtures (use when test cares about account identity) ---

@pytest.fixture(scope="function")
def owner_driver(driver):
    """Driver logged in as the OWNER of this Studio.

    The owner is whatever account completed the Studio's first-run
    Setup Wizard. Recycler index is read from
    surfaces.studio_android.config.OWNER_PROFILE_INDEX (configurable via
    STUDIO_OWNER_PROFILE_INDEX env var).

    Owner accounts typically have:
      - A trainer assigned (Weekly Plan view on Your Plan)
      - Schedule drop notifications
      - Lift membership and full feature access

    Use this for tests that require owner-only state (weekly plan,
    schedule, etc.). For tests that don't care which account, prefer
    first_profile_driver."""
    if OWNER_PROFILE_INDEX is None:
        pytest.skip(
            "OWNER_PROFILE_INDEX is not configured for this Studio. "
            "Set STUDIO_OWNER_PROFILE_INDEX env var (e.g. "
            "`export STUDIO_OWNER_PROFILE_INDEX=1`) or edit "
            "surfaces/studio_android/config.py."
        )
    return login_at_profile_index(
        driver, profile_index=OWNER_PROFILE_INDEX, role_label="OWNER"
    )


@pytest.fixture(scope="function")
def guest1_driver(driver):
    """Driver logged in as GUEST 1 on this Studio.

    Recycler index is read from
    surfaces.studio_android.config.GUEST1_PROFILE_INDEX (configurable via
    STUDIO_GUEST1_PROFILE_INDEX env var).

    Guest accounts typically have:
      - No trainer assigned (Recommended view on Your Plan)
      - No weekly plan or schedule

    Studio supports up to 5 guests. To add guest2_driver,
    guest3_driver, etc., follow the same pattern: add
    GUEST{N}_PROFILE_INDEX to config.py and a corresponding fixture
    here. Don't pre-define unused fixtures — add when actually needed.

    Skips with a clear message if GUEST1_PROFILE_INDEX is not set on
    this Studio (rather than failing with IndexError)."""
    if GUEST1_PROFILE_INDEX is None:
        pytest.skip(
            "GUEST1_PROFILE_INDEX is not configured for this Studio. "
            "Set STUDIO_GUEST1_PROFILE_INDEX env var (e.g. "
            "`export STUDIO_GUEST1_PROFILE_INDEX=0`) or edit "
            "surfaces/studio_android/config.py. Skip is intentional: not every "
            "QA's Studio has the same number of guest accounts."
        )
    return login_at_profile_index(
        driver, profile_index=GUEST1_PROFILE_INDEX, role_label="GUEST 1"
    )