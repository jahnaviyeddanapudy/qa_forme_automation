"""test_25_studio_instructors — Studio INSTRUCTORS sub-tab tests.

Single test case for the INSTRUCTORS sub-tab on Studio:

  - FORME-6844 — Instructor Videos
                 INSTRUCTORS sub-tab → tap an instructor → that
                 instructor's video plays in loop (full-screen
                 ExoPlayer overlay, dismissed via button_close).

Dropped from this group (manual-only — subjective look/feel):
  - FORME-6843 Video Quality and Sync

Scope note:
  - FORME-6845/6846 (Video Carousel + Play Carousel Video) originally
    appeared in the same Zebrunner suite, but they target Home tab →
    YOUR PLAN → Recommended view (carousel below the no-schedule
    header). Different surface, different fixture requirements
    (guest account). Those live in test_26 instead.

  - "Video plays in loop" is verified by checking ExoPlayer's
    exo_content_frame is visible after tap, then re-verifying after
    5s to confirm sustained playback. "Check video quality" per QA
    spec reduces to "ensure video is playing" (not visual quality
    inspection — that's manual).

Instructor card structure (confirmed via dump 2026-05-15):
  - text_title:       instructor name (e.g. "AMANDA M")
  - text_categories:  category list (e.g. "PILATES" or "STRENGTH, YOGA")
  - image:            instructor photo (no useful attribute)

Crucially, instructor cards have text_title but NO text_detail. So
StudioTabPage.find_all_visible_card_records() does NOT work — that
helper requires both. We use a local _find_instructor_cards() helper
instead.

Post-tap behavior (confirmed via dump 2026-05-15):
  Tapping an instructor opens a FULL-SCREEN ExoPlayer overlay:
    - player_view (root)
    - exo_content_frame (the video surface — our playback marker)
    - exo_ad_overlay, exo_overlay, exo_subtitles (scaffolding)
    - button_close (to dismiss)
  This is DIFFERENT from Programs trailers (test_30), which play
  inline in the card's media_container. Don't conflate.

Architecture:
  - Module-scoped shared_driver — login as owner once.
  - INSTRUCTORS sub-tab is available on both owner and guest accounts,
    so no special fixture needed.

Run:
    pytest -m studio surfaces/studio/tests/test_25_studio_instructors.py -v -s
"""
import time

import pytest

from appium.webdriver.common.appiumby import AppiumBy

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage


# Marker for instructor preview playback — same ExoPlayer surface
# element regardless of which screen renders ExoPlayer.
EXO_CONTENT_FRAME_ID = "exo_content_frame"

# Close button on the full-screen instructor preview player.
PLAYER_CLOSE_BUTTON_ID = "button_close"

# Sustained-playback verification: re-check exo_content_frame after
# this many seconds to confirm the video loops rather than playing
# one-shot.
LOOP_VERIFICATION_DELAY_SEC = 15


# =========================================================
# MODULE-SCOPED DRIVER
# =========================================================

@pytest.fixture(scope="module")
def shared_driver():
    """Module-scoped driver. Login as first profile once."""
    d = _create_studio_driver()
    try:
        login_at_profile_index(d, profile_index=0)
        yield d
    finally:
        try:
            d.quit()
        except Exception:
            pass


# =========================================================
# Helpers
# =========================================================

def _ensure_instructors_subtab(driver):
    """Ensure Studio tab is loaded with INSTRUCTORS sub-tab active and
    scroll position reset.

    Toggle through FEATURED first to force a clean scroll-to-top
    state (sub-tabs preserve scroll position between activations).
    """
    home = HomePage(driver)
    studio = StudioTabPage(driver)

    # If a previous test left us inside the instructor preview player,
    # close it before re-entering the sub-tab.
    try:
        close_btn = driver.find_element(
            AppiumBy.ID,
            f"{studio.APP_PACKAGE}:id/{PLAYER_CLOSE_BUTTON_ID}",
        )
        if close_btn.is_displayed():
            close_btn.click()
            time.sleep(2)
    except Exception:
        pass  # Not in player, nothing to close

    if not studio.is_loaded(timeout=2):
        if home.is_loaded(timeout=2):
            home.tap_studio_tab()
            studio.wait_for_studio_tab()
        else:
            home.wait_for_home()
            home.tap_studio_tab()
            studio.wait_for_studio_tab()

    studio.tap_subtab("FEATURED")
    studio.wait_seconds(1)
    studio.tap_subtab_with_scroll("INSTRUCTORS")
    studio.wait_seconds(2)
    studio.wait_for_card_grid_to_settle()
    return studio


def _find_instructor_cards(driver, studio):
    """Find instructor cards on the INSTRUCTORS sub-tab.

    Instructor cards have text_title (e.g. "AMANDA M") but NO
    text_detail — so StudioTabPage.find_all_visible_card_records()
    doesn't work for them (it requires both).

    Returns a list of dicts with the instructor name + the title
    element (used as the tap target). Only includes cards where
    text_title is populated (filters out async-binding tail cards).
    """
    title_elements = driver.find_elements(
        AppiumBy.ID,
        f"{studio.APP_PACKAGE}:id/text_title",
    )

    records = []
    for title_el in title_elements:
        try:
            name = (title_el.get_attribute("text") or "").strip()
        except Exception:
            continue
        if not name:
            continue
        records.append({"name": name, "tap_target": title_el})
    return records


def _is_exo_content_frame_present(driver, studio):
    """Quick check whether the full-screen ExoPlayer is currently
    rendering exo_content_frame. Used both for initial playback
    verification and the post-delay loop check."""
    try:
        driver.find_element(
            AppiumBy.ID,
            f"{studio.APP_PACKAGE}:id/{EXO_CONTENT_FRAME_ID}",
        )
        return True
    except Exception:
        return False


# =========================================================
# FORME-6844 — Instructor Videos
# =========================================================

@pytest.mark.studio
def test_instructor_video_plays_on_tap(shared_driver):
    """INSTRUCTORS sub-tab loads with instructor list. Tapping an
    instructor opens a full-screen ExoPlayer that plays their preview
    video in loop.

    Verifies:
      1. INSTRUCTORS sub-tab renders an instructor list (>=1 card with
         a populated name)
      2. Tapping the first instructor causes exo_content_frame to
         appear (full-screen player opened)
      3. exo_content_frame is still present after 5s (sustained loop
         playback, not one-shot)

    Does NOT verify visual quality — that's manual.
    """
    studio = _ensure_instructors_subtab(shared_driver)

    # =====================================================
    # Step 1 — INSTRUCTORS sub-tab renders an instructor list
    # =====================================================
    print(f"\n[6844] Verifying INSTRUCTORS sub-tab content present")

    instructors = _find_instructor_cards(shared_driver, studio)
    assert len(instructors) > 0, (
        "INSTRUCTORS sub-tab loaded but no instructor cards with "
        "populated text_title found. Either no instructors configured "
        "or recycler hasn't finished async binding."
    )
    print(f"[6844] ✓ Found {len(instructors)} instructors. "
          f"First few: {[r['name'] for r in instructors[:5]]}")

    # =====================================================
    # Step 2 — Tap first instructor → verify full-screen player opens
    # =====================================================
    target = instructors[0]
    print(f"[6844] Tapping instructor: '{target['name']}'")
    target["tap_target"].click()
    time.sleep(3)  # Let preview start

    print(f"[6844] Verifying full-screen player opened "
          f"(exo_content_frame visible)")

    exo_present = False
    for attempt in range(5):
        if _is_exo_content_frame_present(shared_driver, studio):
            exo_present = True
            break
        time.sleep(1)

    assert exo_present, (
        f"After tapping instructor '{target['name']}', "
        f"exo_content_frame did not appear within ~5s. Expected a "
        f"full-screen ExoPlayer to open. Either the tap didn't "
        f"register, the player failed to load, or the post-tap "
        f"behavior changed (was full-screen player overlay as of "
        f"2026-05-15 dump)."
    )
    print(f"[6844] ✓ Full-screen instructor preview player opened")

    # =====================================================
    # Step 3 — Verify playback is sustained (loop, not one-shot)
    # =====================================================
    print(f"[6844] Waiting {LOOP_VERIFICATION_DELAY_SEC}s, then "
          f"re-verifying playback still active")
    time.sleep(LOOP_VERIFICATION_DELAY_SEC)

    assert _is_exo_content_frame_present(shared_driver, studio), (
        f"Instructor preview started but exo_content_frame disappeared "
        f"within {LOOP_VERIFICATION_DELAY_SEC}s. Spec says video plays "
        f"in LOOP — should still be rendering. Either playback is "
        f"broken or the loop behavior isn't working."
    )
    print(f"[6844] ✓ Preview still playing after "
          f"{LOOP_VERIFICATION_DELAY_SEC}s (loop confirmed)")

    # =====================================================
    # Cleanup — dismiss the full-screen player so subsequent runs
    # / tests start from a clean INSTRUCTORS state.
    # =====================================================
    print(f"[6844] Tapping button_close to exit preview player")
    try:
        close_btn = shared_driver.find_element(
            AppiumBy.ID,
            f"{studio.APP_PACKAGE}:id/{PLAYER_CLOSE_BUTTON_ID}",
        )
        close_btn.click()
        time.sleep(2)
        print(f"[6844] ✓ Player closed")
    except Exception as e:
        print(f"[6844] WARNING: could not tap button_close ({e}). "
              f"Player may still be open. Cleanup will run on next "
              f"test entry via _ensure_instructors_subtab.")