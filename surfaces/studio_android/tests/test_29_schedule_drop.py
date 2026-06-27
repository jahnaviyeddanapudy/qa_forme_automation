"""test_29_schedule_drop — Studio weekly schedule drop dialog tests.

Single merged test covering two Zebrunner tickets:

  - FORME-6967 — Verify weekly schedule drop displays Trainer message
                 (dialog renders with concierge name + message body)
  - FORME-6968 — Verify '...more icon' is displayed with Weekly Plan
                 if Trainer has sent a message (image_more present
                 on YOUR PLAN view, can re-open the dialog after
                 dismissing it)

Studio dialog behavior (per QA call 2026-05-20):
  - Dialog auto-appears on LOGIN if trainer has sent a new schedule
    message AND the dialog hasn't been seen this app session yet.
  - Does NOT re-appear on subsequent YOUR PLAN tab navigations within
    the same app session (only on login / fresh app launch).
  - After dismiss, image_more remains visible on the Weekly Plan
    header so the user can re-open the dialog.

Test flow honors that behavior:
  1. Inline the login (don't use login_at_profile_index because its
     wait_for_home() auto-dismisses the dialog before we can see it).
  2. After tapping the profile + password (if needed), check whether
     the schedule drop dialog is visible.
       Branch A — dialog auto-appeared: verify 6967 elements + dismiss
       Branch B — no dialog: assert image_more visible (6968), tap
                  it to open dialog, verify 6967 elements + dismiss
  3. Both branches end with: assert we're on home, dialog gone.

Studio dialog elements (confirmed via dump 2026-05-20):
  text 'Your Weekly Schedule Drop'  (no resource-id)
  layout_concierge
    forme_icon
    text_concierge: 'By Your Forme Team'  (or trainer name)
    text_body: '<trainer message>'
  button_close: 'VIEW MY SCHEDULE'

Note: Studio does NOT have button_x (X close) like mobile. Dismiss
is only via button_close.

Run:
    pytest -m studio surfaces/studio/tests/test_29_schedule_drop.py -v -s
"""
import time

import pytest

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    get_to_profile_screen,
)
from surfaces.studio_android.config import OWNER_PROFILE_INDEX, STUDIO_PASSWORD
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.profile_page import ProfilePage
from surfaces.studio_android.pages.sign_in_page import SignInPage


# Element IDs on the Weekly Plan view header
IMAGE_MORE_ID = "image_more"

# Element IDs inside the schedule drop dialog
SCHEDULE_DROP_TITLE_TEXT = "Your Weekly Schedule Drop"
TEXT_CONCIERGE_ID = "text_concierge"
TEXT_BODY_ID = "text_body"
BUTTON_CLOSE_ID = "button_close"
BUTTON_CLOSE_EXPECTED_TEXT = "VIEW MY SCHEDULE"


# =========================================================
# Driver fixture — raw driver, no auto-login
# =========================================================
# This test does its OWN login flow inline because the standard
# login_at_profile_index() ends with wait_for_home() which
# auto-dismisses the schedule drop dialog. We need to catch the
# dialog before that dismissal happens.

@pytest.fixture(scope="function")
def driver():
    if OWNER_PROFILE_INDEX is None:
        pytest.skip(
            "OWNER_PROFILE_INDEX not configured in config_local.py — "
            "schedule drop tests require the owner profile with a "
            "Weekly Plan assigned."
        )
    d = _create_studio_driver()
    try:
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass


# =========================================================
# FORME-6967 + 6968 — Schedule drop dialog + more icon
# =========================================================

@pytest.mark.studio
def test_schedule_drop_dialog_and_more_icon(driver):
    """Verify schedule drop dialog auto-appears on owner login when
    trainer has sent a message (FORME-6967), and image_more is
    available on Weekly Plan view so the user can re-open the
    dialog after dismissing (FORME-6968).

    Inline login (no wait_for_home) so we can see the dialog before
    it gets auto-dismissed."""
    profile = ProfilePage(driver)
    sign_in = SignInPage(driver)
    home = HomePage(driver)

    # =====================================================
    # Inline login — replicates login_at_profile_index BUT stops
    # short of wait_for_home() so the schedule drop dialog (if it
    # appears on login) remains visible for us to observe.
    # =====================================================
    print(f"\n[setup] Inline login as OWNER (no wait_for_home — "
          f"need to catch dialog if it auto-appears)")

    get_to_profile_screen(driver)
    profile_name = profile.get_profile_name(OWNER_PROFILE_INDEX)
    print(f"[setup] Tapping profile [{OWNER_PROFILE_INDEX}]: "
          f"{profile_name}")
    profile.tap_profile_at(OWNER_PROFILE_INDEX)
    time.sleep(2)

    if sign_in.is_visible(timeout=3):
        print(f"[setup] Sign In prompt — entering password")
        sign_in.enter_password(STUDIO_PASSWORD)
        sign_in.submit()

    # Wait a few seconds for either the schedule drop dialog OR the
    # home tabs to appear. Do NOT call wait_for_home() — it would
    # auto-dismiss the dialog.
    print(f"[setup] Waiting for dialog or home to render "
          f"(no auto-dismiss)")
    time.sleep(5)

    # =====================================================
    # Check whether dialog auto-appeared on login
    # =====================================================
    dialog_auto_appeared = home.is_text_visible(
        SCHEDULE_DROP_TITLE_TEXT, timeout=3
    )

    if dialog_auto_appeared:
        print(f"[6967] ✓ Schedule drop dialog auto-appeared on login "
              f"(trainer message detected)")
    else:
        print(f"[6968→6967] Dialog did NOT auto-appear — likely no "
              f"new trainer message since last dismissal. Falling "
              f"back to image_more trigger.")

        # Home may not have fully rendered yet — let wait_for_home
        # complete now (no dialog to dismiss anyway)
        home.wait_for_home()

        # FORME-6968 — image_more must be visible
        assert home.is_visible(IMAGE_MORE_ID, timeout=5), (
            f"image_more icon should be visible alongside trainer "
            f"name on the Weekly Plan header when a schedule message "
            f"exists. Without it, the user has no way to re-open "
            f"the dismissed dialog."
        )
        print(f"[6968] ✓ image_more visible")

        # Sanity check we're on Weekly Plan view
        section_header = home.get_text(home.SECTION_HEADER_ID)
        assert "Weekly Plan" in section_header, (
            f"Expected Weekly Plan view but section header reads: "
            f"'{section_header}'. Owner may not have a trainer "
            f"assigned."
        )

        # Tap image_more to open dialog
        print(f"[6968→6967] Tapping image_more to open schedule "
              f"drop dialog")
        home.tap_by_id(IMAGE_MORE_ID)
        home.wait_seconds(2)

        assert home.is_text_visible(SCHEDULE_DROP_TITLE_TEXT, timeout=5), (
            f"Schedule drop dialog did not open after tapping "
            f"image_more"
        )

    # =====================================================
    # FORME-6967 — verify dialog elements (same in both branches)
    # =====================================================
    print(f"[6967] Verifying dialog elements")

    assert home.is_visible(TEXT_CONCIERGE_ID, timeout=3), (
        f"text_concierge (trainer/team name) not visible in dialog"
    )
    concierge_text = home.get_text(TEXT_CONCIERGE_ID)
    print(f"[6967] ✓ text_concierge: '{concierge_text}'")

    assert home.is_visible(TEXT_BODY_ID, timeout=3), (
        f"text_body (trainer message) not visible in dialog"
    )
    body_text = home.get_text(TEXT_BODY_ID)
    assert body_text and body_text.strip(), (
        f"text_body is present but empty — expected trainer's "
        f"schedule message text"
    )
    print(f"[6967] ✓ text_body: '{body_text}'")

    assert home.is_visible(BUTTON_CLOSE_ID, timeout=3), (
        f"button_close not visible in dialog"
    )
    close_text = home.get_text(BUTTON_CLOSE_ID)
    assert close_text == BUTTON_CLOSE_EXPECTED_TEXT, (
        f"button_close text should be '{BUTTON_CLOSE_EXPECTED_TEXT}' "
        f"but got '{close_text}'"
    )
    print(f"[6967] ✓ button_close: '{close_text}'")

    # =====================================================
    # Dismiss + verify back on home
    # =====================================================
    print(f"[6967] Tapping button_close to dismiss dialog")
    home.tap_by_id(BUTTON_CLOSE_ID)
    home.wait_seconds(2)

    assert home.is_loaded(), (
        f"Not on home screen after dismissing schedule drop dialog"
    )
    assert not home.is_text_visible(SCHEDULE_DROP_TITLE_TEXT, timeout=2), (
        f"Dialog title still visible after tapping button_close — "
        f"dialog did not dismiss"
    )
    print(f"[6967] ✓ Dialog dismissed cleanly, back on home")

    # =====================================================
    # FORME-6968 — image_more visible AFTER dismiss (so user can
    # re-open). Skip if we already verified it in Branch B above.
    # =====================================================
    if dialog_auto_appeared:
        print(f"[6968] Verifying image_more still visible for re-open")
        assert home.is_visible(IMAGE_MORE_ID, timeout=5), (
            f"image_more icon should remain visible after dialog "
            f"dismiss so user can re-open it later"
        )
        section_header = home.get_text(home.SECTION_HEADER_ID)
        assert "Weekly Plan" in section_header, (
            f"Expected Weekly Plan view but section header reads: "
            f"'{section_header}'"
        )
        print(f"[6968] ✓ image_more visible after dismiss")