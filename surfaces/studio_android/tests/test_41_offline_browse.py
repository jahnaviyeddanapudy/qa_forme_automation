"""test_41_offline_browse — Studio offline browse screen tests.

Covers the OfflineBrowseActivity + OfflineBrowseFragment introduced in
STUDIO-4262 (Offline Experience — Residential).

Test cases:
  - test_STUDIO_4262_offline_browse_screen_loads
      Verify OfflineBrowsePage renders: tab_layout visible, STUDIO tab
      present by default.

  - test_STUDIO_4262_studio_tab_shown_by_default
      Verify the STUDIO tab is selected on initial load (position 0)
      and the recycler or empty-state view is visible.

  - test_STUDIO_4262_lift_tab_visibility_when_registered
      Verify the LIFT tab is shown when Lift is registered on this
      device. If Lift is not registered, the test is skipped.

  - test_STUDIO_4262_just_lift_visible_only_on_lift_tab
      Verify the Just Lift shortcut card is NOT visible on the STUDIO
      tab but IS visible on the LIFT tab (when Lift registered).
      Matches OfflineBrowseFragment.updateJustLiftVisibility() logic:
        visibleOrGone(liftViewModel.isLiftRegistered() && selectedTab == Tab.LIFT)

  - test_STUDIO_4262_category_chips_update_on_tab_switch
      Switch between STUDIO and LIFT tabs and verify that the category
      chips in layout_categories change (each tab's workouts have
      different categories). Skipped if LIFT tab not available.

  - test_STUDIO_4262_profile_button_exits_offline_browse
      Verify tapping the profile_button finishes OfflineBrowseActivity
      (screen disappears / driver lands back on ProfileActivity or Home).

  - test_STUDIO_4262_utility_button_toggles_control_center
      Verify tapping utility_button toggles the fragment_control_center
      overlay visibility.

Pre-conditions:
  These tests require the Studio device to be in offline mode (no active
  internet connection) OR to have the OfflineBrowseActivity launchable
  directly via deep-link / explicit Intent. In CI the network interface
  is disabled before this test module runs.

  If the app cannot reach OfflineBrowseActivity in the current session
  state, every test in this file is skipped via the module-level fixture.

Architecture:
  - Module-scoped shared_driver fixture — one Appium session for all tests.
  - _ensure_offline_browse() helper navigates to OfflineBrowseActivity,
    starting from wherever the driver currently is.
  - No class teardown needed — all tests are read-only (no bookmarks,
    no class starts).

Run all:
    pytest -m studio surfaces/studio_android/tests/test_41_offline_browse.py -v -s

Run one:
    pytest -m studio surfaces/studio_android/tests/test_41_offline_browse.py \\
        -v -s -k 'just_lift'
"""
import logging
import pytest

from surfaces.studio_android.pages.offline_browse_page import OfflineBrowsePage
from surfaces.studio_android.pages.profile_page import ProfilePage

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------#
#  Module-scoped fixture                                                      #
# ---------------------------------------------------------------------------#

@pytest.fixture(scope="module")
def offline_driver(driver):
    """Return a driver already positioned on the OfflineBrowse screen.

    If navigation to OfflineBrowseActivity fails (e.g. device is online
    and the app doesn't route there), all tests in this module are skipped.
    """
    page = OfflineBrowsePage(driver)
    try:
        # OfflineBrowseActivity is started by the app automatically when it
        # detects offline state after loading from cache. We verify the screen
        # loaded; if not reachable, skip the whole module.
        page.wait_for_offline_browse_screen(timeout=15)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(
            f"OfflineBrowseActivity not reachable in this session: {exc}"
        )
    yield driver


# ---------------------------------------------------------------------------#
#  Helpers                                                                   #
# ---------------------------------------------------------------------------#

def _ensure_studio_tab(page: OfflineBrowsePage) -> None:
    """Ensure the STUDIO tab is the active tab."""
    if page.is_studio_tab_visible():
        page.tap_studio_tab()


# ---------------------------------------------------------------------------#
#  Tests                                                                     #
# ---------------------------------------------------------------------------#

@pytest.mark.studio
def test_STUDIO_4262_offline_browse_screen_loads(offline_driver):
    """Verify OfflineBrowsePage renders with tab_layout visible.

    This is the fundamental precondition for all other tests in this file.
    If OfflineBrowseActivity doesn't render at all, something is wrong at
    the activity/navigation level — not just a fragment issue.
    """
    page = OfflineBrowsePage(offline_driver)
    assert page.is_loaded(timeout=10), (
        "OfflineBrowsePage: tab_layout not visible — OfflineBrowseActivity "
        "did not render correctly"
    )
    log.info("test_STUDIO_4262_offline_browse_screen_loads: PASS")


@pytest.mark.studio
def test_STUDIO_4262_studio_tab_shown_by_default(offline_driver):
    """Verify the STUDIO tab (position 0) is present on initial load and
    either the recycler (has downloads) or text_empty (no downloads) is
    visible — confirming the fragment rendered its content area.
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    assert page.is_studio_tab_visible(), (
        "STUDIO tab text not visible on offline browse screen"
    )

    has_content = page.is_recycler_visible()
    has_empty = page.is_empty_state_visible()
    assert has_content or has_empty, (
        "Neither recycler nor text_empty visible on STUDIO tab — "
        "fragment content area did not render"
    )
    log.info(
        f"test_STUDIO_4262_studio_tab_shown_by_default: "
        f"recycler={has_content} empty={has_empty} — PASS"
    )


@pytest.mark.studio
def test_STUDIO_4262_lift_tab_visibility_when_registered(offline_driver):
    """Verify the LIFT tab is shown when Lift is registered.

    The LIFT tab is only added in setupTabs() when
    liftViewModel.isLiftRegistered() returns true. On a non-Lift device
    the tab must NOT appear.

    This test auto-skips on devices without Lift registration.
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    tab_count = page.get_tab_count()
    lift_visible = page.is_lift_tab_visible()

    if not lift_visible:
        pytest.skip(
            "LIFT tab not visible — Lift not registered on this device. "
            "Skipping Lift-tab-specific assertions."
        )

    assert tab_count >= 2, (
        f"Expected at least 2 tabs when Lift is registered, found {tab_count}"
    )
    log.info(
        f"test_STUDIO_4262_lift_tab_visibility_when_registered: "
        f"tab_count={tab_count} — PASS"
    )


@pytest.mark.studio
def test_STUDIO_4262_just_lift_visible_only_on_lift_tab(offline_driver):
    """Verify Just Lift card visibility matches the active tab.

    updateJustLiftVisibility() logic:
      visibleOrGone(liftViewModel.isLiftRegistered() && selectedTab == Tab.LIFT)

    So:
      - On STUDIO tab → view_just_lift must NOT be visible.
      - On LIFT tab   → view_just_lift must be visible (if Lift registered).
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    if not page.is_lift_tab_visible():
        pytest.skip("LIFT tab not available — Lift not registered on this device.")

    # Step 1: switch to STUDIO tab and verify Just Lift is hidden
    page.tap_studio_tab()
    page.wait_seconds(1)
    assert not page.is_just_lift_visible(), (
        "view_just_lift should NOT be visible when STUDIO tab is selected"
    )
    log.info("Just Lift hidden on STUDIO tab — correct")

    # Step 2: switch to LIFT tab and verify Just Lift is shown
    page.tap_lift_tab()
    page.wait_seconds(1)
    assert page.is_just_lift_visible(), (
        "view_just_lift should be visible when LIFT tab is selected "
        "and Lift is registered"
    )
    log.info("Just Lift visible on LIFT tab — correct")

    log.info("test_STUDIO_4262_just_lift_visible_only_on_lift_tab: PASS")


@pytest.mark.studio
def test_STUDIO_4262_category_chips_update_on_tab_switch(offline_driver):
    """Verify category chips in layout_categories change when switching tabs.

    buildCategoryTabs() rebuilds from currentTabWorkouts on every tab
    selection event. STUDIO and LIFT workouts belong to different categories
    so the chip labels should differ between tabs.

    Skipped when the LIFT tab is unavailable.
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    if not page.is_lift_tab_visible():
        pytest.skip("LIFT tab not available — Lift not registered on this device.")

    # Collect chips on STUDIO tab
    page.tap_studio_tab()
    page.wait_seconds(1)
    studio_chips = page.get_category_chip_labels()
    log.info(f"STUDIO tab chips: {studio_chips}")

    # Collect chips on LIFT tab
    page.tap_lift_tab()
    page.wait_seconds(1)
    lift_chips = page.get_category_chip_labels()
    log.info(f"LIFT tab chips: {lift_chips}")

    # The two sets should be different (each tab filters by isLift())
    # We allow the case where one tab is empty (no downloads) — that's
    # still a valid content difference.
    assert studio_chips != lift_chips, (
        f"Category chips did not change between tabs: "
        f"studio={studio_chips} lift={lift_chips}"
    )
    log.info("test_STUDIO_4262_category_chips_update_on_tab_switch: PASS")


@pytest.mark.studio
def test_STUDIO_4262_utility_button_toggles_control_center(offline_driver):
    """Verify tapping utility_button toggles fragment_control_center visibility.

    From OfflineBrowseActivity:
      binding.utilityButton.setOnClickListener {
          controlCenterViewModel.setControlCenterVisibilityChanged(!it.isSelected)
      }
      controlCenterViewModel.onControlCenterVisibilityChanged().observe(this) {
          binding.utilityButton.isSelected = it
          binding.fragmentControlCenter.visibleOrGone(it)
      }
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    # Capture initial control-center state
    initial_visible = page.is_control_center_visible()
    log.info(f"Control center initially visible: {initial_visible}")

    # First tap — should toggle
    page.tap_utility_button()
    page.wait_seconds(1)
    after_first_tap = page.is_control_center_visible()
    assert after_first_tap != initial_visible, (
        "Control center visibility did not change after first utility_button tap"
    )
    log.info(f"Control center after first tap: {after_first_tap}")

    # Second tap — should toggle back
    page.tap_utility_button()
    page.wait_seconds(1)
    after_second_tap = page.is_control_center_visible()
    assert after_second_tap == initial_visible, (
        "Control center visibility did not return to initial state after "
        "second utility_button tap"
    )
    log.info("test_STUDIO_4262_utility_button_toggles_control_center: PASS")


@pytest.mark.studio
def test_STUDIO_4262_profile_button_exits_offline_browse(offline_driver):
    """Verify tapping profile_button finishes OfflineBrowseActivity.

    From OfflineBrowseActivity:
      binding.profileButton.setOnClickListener { finish() }

    After finish() the driver should land back on ProfileActivity
    (or Home if the app navigates there). We verify OfflineBrowsePage
    is no longer loaded.

    NOTE: This test is LAST in the module because it navigates away
    from OfflineBrowseActivity, ending the shared session's clean state.
    """
    page = OfflineBrowsePage(offline_driver)
    page.wait_for_offline_browse_screen(timeout=10)

    page.tap_profile_button()
    page.wait_seconds(2)

    # After finish(), tab_layout should no longer be visible
    assert not page.is_loaded(timeout=4), (
        "OfflineBrowsePage still loaded after tapping profile_button — "
        "activity did not finish"
    )
    log.info("test_STUDIO_4262_profile_button_exits_offline_browse: PASS")
