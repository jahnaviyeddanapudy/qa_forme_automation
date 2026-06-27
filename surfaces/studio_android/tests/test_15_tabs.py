"""test_15_tabs — Studio Your Plan Tab UI 2.0 + concierge tests.

This file covers the EASY 4 of the 10 tests in this category — the ones
that don't require completing a class. Class-completion tests (6673,
6675, 6676, 6677, 6681) live in a separate file because of their
runtime cost.

Easy tests in this file:
  - FORME-6672 — Main/Landing/Up Next/On Demand tab screen (owner)
  - FORME-6678 — Recommended classes (no-schedule guest)

Skipped for now (need follow-up dumps to confirm UI):
  - FORME-6674 — Global header navigation buttons (apple music, settings)
  - FORME-6679 — Filter combinations producing zero results

================================================================
ARCHITECTURE: shared module-scoped driver
================================================================
Both tests share ONE Appium session via the `shared_driver` module
fixture. This avoids ~30s of Appium spinup per test (was ~60s total
session overhead for this file).

Per-test contract:
  - START:  test calls _start_clean(driver) which ensures we're on
            ProfileActivity (recovers from prior-test mid-flight crashes
            by force-stop + relaunch if needed)
  - LOGIN:  test calls login_at_profile_index() directly with the
            account it needs
  - WORK:   test runs assertions
  - END:    test calls home.tap_back_to_profile() so next test starts
            clean

If any test fails after login but before the back-to-profile cleanup,
the NEXT test's _start_clean() will recover via get_to_profile_screen()
(which has its own force-stop fallback). One failure won't cascade.

Account split (uses semantic config-driven indices):
  - 6672 logs in as OWNER (config OWNER_PROFILE_INDEX)
  - 6678 logs in as GUEST 1 (config GUEST1_PROFILE_INDEX)

Recycler index → account mapping is configured per-QA via
surfaces/studio/config_local.py (gitignored). For Silvanus's Studio:
  OWNER_PROFILE_INDEX = 1
  GUEST1_PROFILE_INDEX = 0

Run just this file:
    pytest -m studio surfaces/studio/tests/test_15_tabs.py -v -s

Run a single test:
    pytest -m studio surfaces/studio/tests/test_15_tabs.py \\
        -v -s -k 'tabs_visible'
    pytest -m studio surfaces/studio/tests/test_15_tabs.py \\
        -v -s -k 'recommended'
"""
import pytest

from surfaces.studio_android.config import OWNER_PROFILE_INDEX, GUEST1_PROFILE_INDEX
from surfaces.studio_android.conftest import (
    _create_studio_driver,
    get_to_profile_screen,
    login_at_profile_index,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage


# =========================================================
# Module-scoped shared driver
# =========================================================

@pytest.fixture(scope="module")
def shared_driver():
    """ONE Appium session shared by all tests in this module.

    Saves ~30s per test by avoiding session spinup. Tests handle their
    own login and back-to-profile cleanup. If a test crashes mid-flight,
    the next test's _start_clean() handles recovery.
    """
    d = _create_studio_driver()
    yield d
    d.quit()


def _start_clean(driver):
    """Ensure we're on ProfileActivity before the test begins.

    Normal case (previous test cleaned up): driver is already on
    ProfileActivity, this is a no-op.

    Recovery case (previous test crashed mid-flight): driver may be on
    home, in a class, on rating screen, etc. get_to_profile_screen()
    walks back to ProfileActivity, falling back to force-stop + relaunch
    if normal navigation can't reach it.
    """
    get_to_profile_screen(driver)


# =========================================================
# LIVE 1:1 tab element IDs (from dump on 2026-04-28)
# =========================================================

LIVE_1ON1_NO_UPCOMING_ID = "layout_no_upcoming"
LIVE_1ON1_UPCOMING_30MIN_ID = "layout_upcoming_30min"
LIVE_1ON1_NEXT_SESSION_TIME_ID = "label_next_session_time"
LIVE_1ON1_BUTTON_JOIN_ID = "button_join_session"
LIVE_1ON1_NO_SESSIONS_LABEL_ID = "label_no_sessions"
LIVE_1ON1_SESSIONS_LIST_ID = "fragment_live_sessions_list"


# =========================================================
# FORME-6672 — All 3 home tabs visible and tappable (OWNER)
# =========================================================

@pytest.mark.studio
def test_tabs_visible_and_tappable(shared_driver):
    """FORME-6672: Verify all 3 top-level Home tabs (YOUR PLAN, STUDIO,
    LIVE 1:1) are visible after login, and each tab can be tapped to
    navigate to its content.

    Test wording in JIRA uses outdated tab names:
      Main/Landing = YOUR PLAN tab
      Up Next      = LIVE 1:1 tab
      On Demand    = STUDIO tab

    Login as OWNER (account most likely to have Live 1:1 sessions
    scheduled, exercising the conditional content check).

    Test plan:
      1. Login as owner
      2. Verify all 3 tab content-descs visible
      3. Tap STUDIO -> verify Studio tab content rendered
      4. Tap LIVE 1:1 -> verify navigation + conditional content check
      5. Tap YOUR PLAN -> verify Your Plan content rendered
      6. Cleanup: tap back to profile so next test starts clean
    """
    driver = shared_driver
    _start_clean(driver)

    # Login as owner
    login_at_profile_index(
        driver, profile_index=OWNER_PROFILE_INDEX, role_label="OWNER"
    )
    home = HomePage(driver)
    home.wait_for_home()

    assert home.is_loaded(), "Home should be loaded after login as owner"

    try:
        # Step 1: All 3 tabs visible by content-desc
        print(f"\n[6672] Verifying all 3 tabs visible by content-desc")
        for tab_desc in [home.TAB_YOUR_PLAN_DESC,
                         home.TAB_STUDIO_DESC,
                         home.TAB_LIVE_1ON1_DESC]:
            assert home.is_text_visible(tab_desc, timeout=3), (
                f"Tab '{tab_desc}' not visible on Home. All 3 tabs should "
                f"be present in the top tab strip."
            )
            print(f"[6672] ✓ '{tab_desc}' tab visible")

        # Step 2: Tap STUDIO -> verify Studio tab content loaded
        print(f"\n[6672] Tapping STUDIO tab")
        home.tap_studio_tab()
        studio = StudioTabPage(driver)
        studio.wait_for_studio_tab()
        assert studio.is_loaded(), (
            "After tapping STUDIO tab, fragment_vod_nav should be visible "
            "(Studio tab's marker element)"
        )
        print(f"[6672] ✓ STUDIO tab loaded "
              f"(active sub-tab: {studio.get_active_subtab()})")

        # Step 3: Tap LIVE 1:1 -> verify navigation + conditional content check
        print(f"\n[6672] Tapping LIVE 1:1 tab")
        home.tap_live_1on1_tab()
        home.wait_seconds(2)

        assert not studio.is_loaded(timeout=2), (
            "After tapping LIVE 1:1 tab, Studio tab content "
            "(fragment_vod_nav) should no longer be visible."
        )
        print(f"[6672] ✓ Left Studio tab after tapping LIVE 1:1")

        assert home.is_visible(LIVE_1ON1_SESSIONS_LIST_ID, timeout=3), (
            f"After tapping LIVE 1:1 tab, '{LIVE_1ON1_SESSIONS_LIST_ID}' "
            f"should be visible (the sessions list fragment is the "
            f"structural container for the tab). If not visible, the tab "
            f"didn't navigate or the layout has changed."
        )
        print(f"[6672] ✓ Live 1:1 tab loaded "
              f"({LIVE_1ON1_SESSIONS_LIST_ID} visible)")

        # Conditional content check
        has_next_session = home.is_visible(
            LIVE_1ON1_UPCOMING_30MIN_ID, timeout=2
        )
        has_no_upcoming = home.is_visible(
            LIVE_1ON1_NO_UPCOMING_ID, timeout=2
        )
        no_sessions_message = home.is_visible(
            LIVE_1ON1_NO_SESSIONS_LABEL_ID, timeout=2
        )

        print(f"[6672] Live 1:1 state: "
              f"upcoming_30min={has_next_session}, "
              f"no_upcoming={has_no_upcoming}, "
              f"no_sessions_message={no_sessions_message}")

        if has_next_session:
            print(f"[6672] Session scheduled within 30 min — verifying card")
            assert home.is_visible(LIVE_1ON1_NEXT_SESSION_TIME_ID, timeout=3), (
                f"layout_upcoming_30min is visible but "
                f"label_next_session_time is missing — session card "
                f"didn't fully render"
            )
            time_text = home.get_text(LIVE_1ON1_NEXT_SESSION_TIME_ID)
            print(f"[6672] ✓ Next session time: '{time_text}'")

            assert home.is_visible(LIVE_1ON1_BUTTON_JOIN_ID, timeout=3), (
                f"layout_upcoming_30min is visible but JOIN SESSION button "
                f"({LIVE_1ON1_BUTTON_JOIN_ID}) is missing"
            )
            print(f"[6672] ✓ JOIN SESSION button visible")

        elif has_no_upcoming or no_sessions_message:
            print(f"[6672] No live session scheduled — skipping content "
                  f"check (empty state is valid for this test)")

        else:
            print(f"[6672] Live 1:1 tab is in an indeterminate state — "
                  f"neither layout_upcoming_30min, layout_no_upcoming, nor "
                  f"label_no_sessions visible. Tab navigation worked, but "
                  f"the content state doesn't match either known pattern. "
                  f"Worth investigating after this test.")

        # Step 4: Tap YOUR PLAN -> verify Your Plan content rendered
        print(f"\n[6672] Tapping YOUR PLAN tab")
        home.tap_your_plan_tab()
        assert home.is_loaded(), (
            "After tapping YOUR PLAN tab, Home should still be loaded "
            "(tab_layout visible)"
        )
        assert home.is_visible(home.SECTION_HEADER_ID, timeout=3), (
            f"After tapping YOUR PLAN, the section header "
            f"({home.SECTION_HEADER_ID}) should be visible. Either the tap "
            f"didn't navigate or Your Plan content didn't render."
        )
        section_text = home.get_text(home.SECTION_HEADER_ID)
        print(f"[6672] ✓ YOUR PLAN tab loaded "
              f"(variant: '{section_text}')")

    finally:
        # Cleanup: return to profile so next test starts clean.
        # In a `finally` so it runs even if an assertion fails — without
        # it, the next test would inherit a broken state and fail with a
        # confusing error rather than the real one.
        try:
            print(f"\n[6672] Cleanup: tap_back_to_profile()")
            home.tap_back_to_profile()
        except Exception as e:
            # Best-effort cleanup — if it fails, the next test's
            # _start_clean() will force-stop + relaunch as recovery.
            print(f"[6672] Cleanup tap_back_to_profile failed: {e}")
            print(f"[6672] Next test will recover via _start_clean()")


# =========================================================
# FORME-6678 — Recommended view when no schedule (GUEST 1)
# =========================================================

@pytest.mark.studio
def test_recommended_view_when_no_schedule(shared_driver):
    """FORME-6678: When the account has no trainer / no weekly plan,
    the YOUR PLAN tab shows the Recommended view (instead of Weekly
    Plan).

    The Recommended view displays:
      - text_recommended (section header) reads "Recommended"
      - text_concierge reads "BY YOUR FORME TEAM"
      - recommendations_fragment is visible
      - At least one class card visible

    Login as GUEST 1 (no-schedule account). The fixture pytest.skips
    cleanly if GUEST1_PROFILE_INDEX is not configured for the Studio.

    Test plan:
      1. Login as guest1
      2. Tap YOUR PLAN tab (in case we're not already on it)
      3. Verify section header reads "Recommended"
      4. Verify text_concierge reads "BY YOUR FORME TEAM"
      5. Verify recommendations_fragment is visible
      6. Verify at least one class card visible
      7. Cleanup: tap back to profile
    """
    if GUEST1_PROFILE_INDEX is None:
        pytest.skip(
            "GUEST1_PROFILE_INDEX is not configured for this Studio. "
            "Set it in surfaces/studio/config_local.py."
        )

    driver = shared_driver
    _start_clean(driver)

    login_at_profile_index(
        driver, profile_index=GUEST1_PROFILE_INDEX, role_label="GUEST 1"
    )
    home = HomePage(driver)
    home.wait_for_home()

    assert home.is_loaded(), (
        "Home should be loaded after login as guest1 (no-schedule account)"
    )

    try:
        # Step 1: Land on YOUR PLAN tab
        print(f"\n[6678] Navigating to YOUR PLAN tab")
        home.tap_your_plan_tab()
        home.wait_seconds(2)

        # Step 2: Verify Recommended view (not Weekly Plan)
        print(f"[6678] Verifying account is on Recommended view")
        section_text = home.get_text(home.SECTION_HEADER_ID)
        print(f"[6678] Section header text: '{section_text}'")

        assert home.is_on_recommended_view(), (
            f"Expected Recommended view (no-schedule guest account), but "
            f"section header reads '{section_text}'. If it reads 'Weekly "
            f"Plan', GUEST1_PROFILE_INDEX is pointing at an account "
            f"that DOES have a trainer/schedule. Update "
            f"surfaces/studio/config_local.py."
        )
        print(f"[6678] ✓ Section header reads 'Recommended'")

        # Step 3: text_concierge reads "BY YOUR FORME TEAM"
        assert home.is_visible(home.TEXT_CONCIERGE_ID, timeout=3), (
            f"text_concierge element should be visible on Recommended view"
        )
        concierge_text = home.get_text(home.TEXT_CONCIERGE_ID)
        print(f"[6678] text_concierge: '{concierge_text}'")

        assert concierge_text and "FORME TEAM" in concierge_text.upper(), (
            f"Expected text_concierge to mention 'FORME TEAM' on the "
            f"no-schedule view. Got: '{concierge_text}'"
        )
        print(f"[6678] ✓ text_concierge mentions FORME TEAM "
              f"(no trainer assigned)")

        # Step 4: recommendations_fragment visible
        assert home.is_visible(home.RECOMMENDATIONS_FRAGMENT_ID, timeout=3), (
            f"recommendations_fragment "
            f"('{home.RECOMMENDATIONS_FRAGMENT_ID}') should be visible "
            f"on the Recommended view. If not, the view variant detection "
            f"is wrong or the fragment didn't render."
        )
        print(f"[6678] ✓ recommendations_fragment visible")

        # Step 5: At least one class card visible
        titles = home.find_all_class_titles()
        print(f"[6678] Class titles visible: {titles[:5]}"
              f"{'...' if len(titles) > 5 else ''}")
        assert len(titles) >= 1, (
            f"Recommended view should show at least one class card. "
            f"find_all_class_titles() returned: {titles}"
        )
        print(f"[6678] ✓ {len(titles)} recommended class card(s) visible")

    finally:
        try:
            print(f"\n[6678] Cleanup: tap_back_to_profile()")
            home.tap_back_to_profile()
        except Exception as e:
            print(f"[6678] Cleanup tap_back_to_profile failed: {e}")
            # Last test in module, so cleanup failure is moot —
            # shared_driver fixture will quit() on teardown anyway.