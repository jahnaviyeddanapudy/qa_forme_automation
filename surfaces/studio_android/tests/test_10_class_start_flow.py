"""test_10_class_start_flow — smoke test for full class start flow.

Validates the chain:
    Home → Studio tab → WORKOUTS sub-tab → ClassDetail
         → AppleWatchPrompt (optional) → Player → end early

Why we switch to WORKOUTS sub-tab first instead of using FEATURED:
  - FEATURED contains a mix of card types: CPS classes, Programs,
    Recovery, etc. Some of these (Programs) navigate to Program detail
    screens, not class detail screens.
  - WORKOUTS sub-tab contains only standard class cards — predictable.
  - This makes the smoke deterministic regardless of what's currently
    in FEATURED for this profile.

This is a SMOKE test — it doesn't assert specific class metadata,
just that each screen in the chain loads when expected. If any page
object's element IDs are wrong, this test fails fast and points at
which page object needs a follow-up dump.

Why end early instead of completing the class:
  - Completing a 30 MIN class to trigger Rating + Summary takes 15+
    minutes minimum. Too slow for smoke.
  - Ending early bypasses Rating screen entirely (per observed
    behavior — Rating only appears if class progressed far enough)
    and goes straight to Summary or back to home.

Run just this test:
    pytest -m studio surfaces/studio/tests/test_10_class_start_flow.py -v -s
"""
import pytest

from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.class_detail_page import ClassDetailPage
from surfaces.studio_android.pages.apple_watch_prompt_page import AppleWatchPromptPage
from surfaces.studio_android.pages.player_page import PlayerPage


@pytest.mark.studio
def test_class_start_flow_smoke(first_profile_driver):
    """Smoke: start a class, reach the player, end early.

    Steps:
      1. Verify Home loaded
      2. Tap STUDIO tab
      3. Switch to WORKOUTS sub-tab (predictable card content)
      4. Tap first non-completed card
      5. Verify ClassDetail loaded; capture title for log
      6. Tap START SESSION
      7. Dismiss Apple Watch prompt if it appears
      8. Wait for Player to load
      9. Verify header reads (class_time, calories, heart_rate)
     10. End the class (tap_end_session)
     11. Verify we're back somewhere reasonable (no longer on Player)
    """
    driver = first_profile_driver

    # 1. Home loaded
    home = HomePage(driver)
    assert home.is_loaded(), "HomePage should be loaded after login"

    # 2. Studio tab
    home.tap_studio_tab()
    studio = StudioTabPage(driver)
    studio.wait_for_studio_tab()

    print(f"\n[smoke] Studio tab loaded — initial sub-tab: "
          f"{studio.get_active_subtab()}")
    print(f"[smoke] Visible sub-tabs: {studio.all_visible_subtabs()}")

    # 3. Switch to WORKOUTS sub-tab — these are predictable class cards,
    # not Programs (which would navigate to a different screen)
    studio.tap_subtab_with_scroll("WORKOUTS")

    # Verify we're now on WORKOUTS
    active = studio.get_active_subtab()
    print(f"[smoke] Active sub-tab after tapping WORKOUTS: {active}")
    assert active == "WORKOUTS", (
        f"Expected to be on WORKOUTS sub-tab, got '{active}'. "
        f"The sub-tab tap may not have applied a filter chip."
    )

    card_count = studio.get_card_count()
    print(f"[smoke] {card_count} cards visible on WORKOUTS")
    assert card_count > 0, "Should have at least one workout card visible"

    # Diagnostic: log the first few class titles
    titles = studio.find_all_class_titles()
    print(f"[smoke] First 5 workout titles: {titles[:5]}")

    # 4. Tap first non-completed card
    studio.tap_first_non_completed_card()

    # 5. ClassDetail loaded
    detail = ClassDetailPage(driver)
    detail.wait_for_class_detail()
    assert detail.is_loaded(), "ClassDetailPage should be loaded after card tap"

    title = detail.get_title()
    info = detail.get_info_string()
    variant = detail.get_variant()
    print(f"[smoke] Class: {title}")
    print(f"[smoke] Info:  {info}")
    print(f"[smoke] Variant: {variant}")

    # 6. Start session
    detail.tap_start_session()

    # 7. Apple Watch prompt — dismiss if shown (conditional)
    prompt = AppleWatchPromptPage(driver)
    if prompt.is_showing(timeout=3):
        print("[smoke] Apple Watch prompt shown — dismissing")
        prompt.tap_continue_to_session()
    else:
        print("[smoke] Apple Watch prompt skipped (already dismissed or "
              "Apple Watch configured)")

    # 8. Player loaded
    player = PlayerPage(driver)
    player.wait_for_player(timeout=30)
    assert player.is_loaded(), "PlayerPage should be loaded after start"

    # 9. Header reads
    class_time = player.get_class_time()
    calories = player.get_calories()
    heart_rate = player.get_heart_rate()
    print(f"[smoke] Player class_time: {class_time}")
    print(f"[smoke] Player calories:   {calories}")
    print(f"[smoke] Player heart_rate: {heart_rate}")

    assert class_time, "class_time should be readable from player header"
    assert heart_rate is not None, "heart_rate should be readable (may be '---')"

    player_variant = player.get_player_variant()
    print(f"[smoke] Player variant: {player_variant}")

    workout_state = player.get_workout_state()
    print(f"[smoke] Player workout_state: {workout_state}")

    # 10. End class
    player.tap_end_session()

    # 11. Verify we left the player
    assert not player.is_loaded(timeout=5), (
        "After tap_end_session, should no longer be on Player. "
        "If we are, the end-session flow may have changed (e.g. "
        "now goes through a confirm dialog?)."
    )
    print("[smoke] Class flow complete — exited player successfully")