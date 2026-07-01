"""test_52_settings_members — Settings › Members owner-logout and cache-clear tests.

Covers:
  STUDIO-4285  [Android][Offline][Simplified Commercial]
               Unable to log out the owner
               Fix: added delay(1) stabilisation + safe cast on
               LOGIN_RESPONSE bundle + removed nullable guards on
               getUsers() / getVisitors().

  STUDIO-4284  [Android][Offline]
               Clearing downloaded content should be done when the
               owner logs out or Settings → Install Setup is done.
               Fix: resourcesViewModel.clearDownloadCache(false)
               called in SettingsMainFragment after signOut().

Test cases:
  - test_STUDIO_4285_owner_remove_shows_confirmation_dialog
      Navigate to Settings › Members, tap Remove on the owner row,
      verify the ConfirmationDialog appears (regression guard: before
      the fix this flow crashed silently due to the null-safety bug,
      so the dialog never appeared).

  - test_STUDIO_4285_owner_remove_cancel_keeps_owner_in_list
      After the ConfirmationDialog appears, tap Cancel and verify
      the owner name is still present in the members list (no
      accidental removal on cancel).

  - test_STUDIO_4285_owner_remove_confirm_shows_enter_password_dialog
      Tap Remove on the owner row, confirm the ConfirmationDialog,
      verify the EnterPasswordDialog appears next (the full logout
      flow requires password validation).

  - test_STUDIO_4284_sign_out_from_settings_main_completes
      Navigate to the Settings main screen, trigger Install Setup /
      sign-out, verify the app returns to ProfileActivity (the
      clearDownloadCache call must not crash the sign-out flow).

Architecture:
  Module-scoped fixture — login once as owner, all members tests
  share one Appium session. Each test navigates to/from the members
  screen independently using _navigate_to_members() /
  _return_to_home().

Pre-conditions:
  - OWNER_PROFILE_INDEX and OWNER_PASSWORD in config_local.py.
  - The owner profile must be visible on ProfileActivity.
  - At least one profile must be present in the members list.

Run all:
    pytest -m studio surfaces/studio_android/tests/test_52_settings_members.py -v -s
"""
import logging
import pytest

from surfaces.studio_android.pages.settings_members_page import SettingsMembersPage
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.profile_page import ProfilePage

try:
    from surfaces.studio_android.config_local import OWNER_PROFILE_INDEX
except ImportError:
    OWNER_PROFILE_INDEX = 0

try:
    from surfaces.studio_android.config_local import OWNER_PASSWORD
except ImportError:
    OWNER_PASSWORD = ""

try:
    from surfaces.studio_android.config_local import OWNER_NAME
except ImportError:
    OWNER_NAME = None  # will be resolved at runtime from the members list

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-scoped fixture — login once as owner
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def members_driver(request):
    """Login as owner and yield a driver already on the Home screen."""
    from surfaces.studio_android.conftest import (
        _create_studio_driver,
        login_at_profile_index,
    )

    driver = _create_studio_driver(request)
    login_at_profile_index(driver, OWNER_PROFILE_INDEX)
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------


def _navigate_to_members(driver) -> SettingsMembersPage:
    """From Home, open Settings then tap the MEMBERS button."""
    home = HomePage(driver)
    home.wait_for_home_screen()
    home.tap_settings()
    # Settings main screen — tap Members
    # button_members is the resource-id inferred from SettingsMainFragment
    from surfaces.studio_android.pages.base import StudioBasePage
    base = StudioBasePage(driver)
    base.tap_by_id("button_members")
    members = SettingsMembersPage(driver)
    members.wait_for_screen()
    return members


def _return_to_home(driver):
    """Pop back from members (and settings) to Home."""
    # Two go_back calls: members → settings main → home
    home = HomePage(driver)
    try:
        driver.back()
        driver.back()
        home.wait_for_home_screen(timeout=10)
    except Exception:
        # If we're already on home or only one level deep, ignore
        try:
            home.wait_for_home_screen(timeout=5)
        except Exception:
            pass


def _resolve_owner_name(members: SettingsMembersPage) -> str:
    """Return the owner name to use for row targeting.

    If OWNER_NAME is configured in config_local.py, use that.
    Otherwise fall back to the first non-empty name in the list
    (owner is always first per MembersAdapter sort).
    """
    if OWNER_NAME:
        return OWNER_NAME
    names = members.get_member_names()
    assert names, "Members list is empty — cannot resolve owner name"
    return names[0]


# ---------------------------------------------------------------------------
# STUDIO-4285 tests
# ---------------------------------------------------------------------------


@pytest.mark.studio
def test_STUDIO_4285_owner_remove_shows_confirmation_dialog(members_driver):
    """Tapping Remove on the owner row must open the ConfirmationDialog.

    Before the STUDIO-4285 fix the dialog never appeared because a
    crash in the fragment result listener (ClassCastException on the
    null-unsafe cast) silently swallowed the event. After the fix the
    dialog must be present.
    """
    members = _navigate_to_members(members_driver)
    owner_name = _resolve_owner_name(members)
    log.info(f"Testing Remove flow for owner: {owner_name!r}")

    members.tap_remove_for_member(owner_name)

    assert members.is_confirmation_dialog_visible(timeout=10), (
        f"ConfirmationDialog did not appear after tapping Remove for owner '{owner_name}'. "
        "Regression: STUDIO-4285 — dialog must appear for owner remove flow."
    )
    log.info("STUDIO-4285: ConfirmationDialog appeared as expected")

    # Clean up — dismiss dialog before next test
    members.cancel_dialog()
    _return_to_home(members_driver)


@pytest.mark.studio
def test_STUDIO_4285_owner_remove_cancel_keeps_owner_in_list(members_driver):
    """Cancelling the ConfirmationDialog must leave the owner in the list."""
    members = _navigate_to_members(members_driver)
    owner_name = _resolve_owner_name(members)
    log.info(f"Testing Cancel keeps owner in list: {owner_name!r}")

    members.tap_remove_for_member(owner_name)
    assert members.is_confirmation_dialog_visible(timeout=10), (
        "ConfirmationDialog did not appear — cannot test cancel behaviour"
    )

    members.cancel_dialog()
    # Dialog must be gone
    members.wait_seconds(1)
    assert not members.is_confirmation_dialog_visible(timeout=3), (
        "ConfirmationDialog still visible after Cancel"
    )

    # Owner must still be in the list
    names_after = members.get_member_names()
    assert owner_name in names_after, (
        f"Owner '{owner_name}' disappeared from members list after Cancel. "
        "Regression: Cancel must not remove the owner."
    )
    log.info("STUDIO-4285: owner still present after Cancel — correct")

    _return_to_home(members_driver)


@pytest.mark.studio
def test_STUDIO_4285_owner_remove_confirm_shows_enter_password_dialog(members_driver):
    """Confirming the ConfirmationDialog must proceed to EnterPasswordDialog.

    This validates the full fragment-result-listener chain introduced
    in STUDIO-4285:
      1. Remove tapped → ConfirmationDialog
      2. Confirmed     → delay(1) stabilisation → showEnterPasswordRequest()
      3. EnterPasswordDialog appears
    """
    members = _navigate_to_members(members_driver)
    owner_name = _resolve_owner_name(members)
    log.info(f"Testing full logout dialog chain for owner: {owner_name!r}")

    members.tap_remove_for_member(owner_name)
    assert members.is_confirmation_dialog_visible(timeout=10), (
        "ConfirmationDialog did not appear"
    )

    members.confirm_dialog()

    # After the fix a delay(1) stabilisation happens in a coroutine before
    # showEnterPasswordRequest() is called — give it a couple of seconds.
    members.wait_seconds(2)

    assert members.is_enter_password_dialog_visible(timeout=10), (
        "EnterPasswordDialog did not appear after confirming owner removal. "
        "Regression: STUDIO-4285 — the password dialog must follow confirmation."
    )
    log.info("STUDIO-4285: EnterPasswordDialog appeared — full chain works")

    # Dismiss by going back so we don't accidentally sign out the owner
    members_driver.back()
    members.wait_seconds(1)
    _return_to_home(members_driver)


# ---------------------------------------------------------------------------
# STUDIO-4284 tests
# ---------------------------------------------------------------------------


@pytest.mark.studio
def test_STUDIO_4284_sign_out_from_settings_main_completes(members_driver):
    """Sign-out via Settings main must complete without crashing.

    STUDIO-4284 added resourcesViewModel.clearDownloadCache(false) to
    the sign-out path in SettingsMainFragment. This test verifies that
    the clearDownloadCache call does not crash the flow and the app
    returns to ProfileActivity after sign-out.

    NOTE: This test signs the owner OUT, which means subsequent tests
    in this module will start from ProfileActivity. Because this test
    is placed last in the file it does not disrupt the other tests.
    If the module fixture is re-used after this test runs, subsequent
    tests will fail because the driver is on ProfileActivity, not Home.
    The test is therefore intentionally positioned last.
    """
    # Navigate to Settings main (not members sub-screen)
    home = HomePage(members_driver)
    home.wait_for_home_screen()
    home.tap_settings()

    # Settings main screen — tap the Install Setup / sign-out button.
    # The resource-id for the install-setup / sign-out button in
    # SettingsMainFragment is `button_install_setup`.
    from surfaces.studio_android.pages.base import StudioBasePage
    base = StudioBasePage(members_driver)

    # Confirm the Settings main screen loaded by checking button_close
    assert base.is_visible("button_close", timeout=10), (
        "Settings main screen did not load (button_close not found)"
    )

    # Tap Install Setup which triggers the sign-out + clearDownloadCache
    base.tap_by_id("button_install_setup")

    # A ConfirmationDialog will appear — confirm it
    base.wait_seconds(1)
    if base.is_visible("button_confirm", timeout=5):
        base.tap_by_id("button_confirm")
        log.info("STUDIO-4284: ConfirmationDialog confirmed for sign-out")

    # After sign-out the app must arrive at ProfileActivity
    profile = ProfilePage(members_driver)
    try:
        profile.wait_for_profile_screen()
        log.info("STUDIO-4284: ProfileActivity reached after sign-out — clearDownloadCache did not crash the flow")
    except Exception as exc:
        pytest.fail(
            f"STUDIO-4284: App did not return to ProfileActivity after sign-out. "
            f"clearDownloadCache may have crashed the sign-out path. Error: {exc}"
        )
