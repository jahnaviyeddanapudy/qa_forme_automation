"""test_30_programs_collections — Studio Programs & Collections tests.

Covers structural verification of the PROGRAMS sub-tab + Program detail
page. Three test cases:

  - FORME-6595 — Programs Details page UI (structural)
  - FORME-6607 — Trailer link NOT shown on Collections (negative)
  - FORME-6608 — Trailer Link Visible on Programs + trailer plays
                 inline; tapping the playing trailer surface
                 navigates to the Program detail page

Definitions (from QA spec):
  - "Program" = card in PROGRAMS sub-tab WITH button_trailer
  - "Collection" = card in PROGRAMS sub-tab WITHOUT button_trailer

Currently 2 programs have trailers ("ONE MOVE A DAY", "AMPLIFY YOUR
CHAKRAS"). The count will grow when Lift is attached. Studio has ~10
total programs/collections.

GAP — no program title element exposed in current build:
  Program cards have no text element naming the program. Tests verify
  STRUCTURAL features but cannot verify SEMANTIC correctness (which
  named programs are which).

Trailer playback behavior (verified 2026-05-11):
  - button_trailer tap starts inline ExoPlayer playback in the card's
    media_container (exo_content_frame appears)
  - Trailer LOOPS — does not naturally end
  - Tapping the player surface navigates to the Program detail page
    (this is the user-facing "preview then learn more" interaction)
  - Trailer also stops if user scrolls the card out of viewport

Architecture:
  - Module-scoped shared_driver — login once, 3 tests share session
  - _ensure_programs_subtab() handles recovery if a test left us on a
    different screen (e.g. Program detail page after 6608), and
    ALWAYS forces a fresh PROGRAMS sub-tab render at the top of the
    list by tapping FEATURED then PROGRAMS. Required because PROGRAMS
    sub-tab preserves scroll position between activations — a previous
    test scrolled to the bottom would leave the next test starting
    at the bottom, missing cards above.

Run all:
    pytest -m studio surfaces/studio/tests/test_30_programs_collections.py -v -s

Run a single test:
    pytest -m studio surfaces/studio/tests/test_30_programs_collections.py \\
        -v -s -k 'trailer_on_program'
"""
import pytest

from surfaces.studio_android.conftest import (
    _create_studio_driver,
    login_at_profile_index,
)
from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.program_detail_page import ProgramDetailPage


# =========================================================
# MODULE-SCOPED DRIVER
# =========================================================

@pytest.fixture(scope="module")
def shared_driver():
    """Module-scoped driver. Login as first profile once; 3 tests share."""
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

def _ensure_programs_subtab(driver):
    """Ensure we're on the PROGRAMS sub-tab AT THE TOP of the list.
    Recovers from common leftover states:
      - On Program detail page (e.g. left over from previous test)
      - On Home tab
      - On Studio tab but a different sub-tab
      - On PROGRAMS sub-tab but scrolled down

    Always taps FEATURED then PROGRAMS at the end to force a fresh
    render that starts at the top of the list. Without this, the
    PROGRAMS sub-tab preserves scroll position between activations
    and scroll_collect_all_program_cards() would miss cards above the
    current viewport.

    Returns StudioTabPage. Raises RuntimeError if recovery fails."""
    home = HomePage(driver)
    studio = StudioTabPage(driver)
    detail = ProgramDetailPage(driver)

    # Recovery 1: if on Program detail page, close it
    if detail.is_loaded(timeout=2):
        try:
            detail.close()
        except Exception:
            try:
                driver.back()
            except Exception:
                pass

    # Standard navigation paths
    if not studio.is_loaded(timeout=2):
        if home.is_loaded(timeout=2):
            home.tap_studio_tab()
            studio.wait_for_studio_tab()
        else:
            # Last-resort: one back press in case we're on unexpected screen
            try:
                driver.back()
            except Exception:
                pass
            if studio.is_loaded(timeout=2):
                pass
            elif home.is_loaded(timeout=2):
                home.tap_studio_tab()
                studio.wait_for_studio_tab()
            else:
                raise RuntimeError(
                    "Not on Home, Studio tab, or Program detail page — "
                    "test setup failed. Driver state unrecoverable."
                )

    # ALWAYS force a scroll-position reset by switching to FEATURED
    # then back to PROGRAMS. Tapping the already-active sub-tab does
    # NOT scroll to top on Studio — switching sub-tabs is required.
    studio.tap_subtab("FEATURED")
    studio.wait_seconds(1)
    studio.tap_subtab("PROGRAMS")
    studio.wait_seconds(2)

    return studio


# =========================================================
# FORME-6608 — Trailer plays and navigates to detail on tap
# =========================================================

@pytest.mark.studio
def test_trailer_on_program_plays_and_dismisses(shared_driver):
    """FORME-6608: Verify trailer feature on Program cards:
      1. At least one Program card with button_trailer exists (scrolling
         to find — trailer-having cards may be below initial viewport)
      2. Tapping button_trailer activates inline trailer playback
         (exo_content_frame appears inside the card)
      3. Tapping the playing trailer surface navigates to the Program
         detail page (documented behavior — trailer = "preview then
         learn more")
      4. Close detail page → return to PROGRAMS sub-tab cleanly

    Studio has ~10 programs total, ~3 visible per viewport.
    max_scrolls=5 covers the whole list with margin.
    """
    studio = _ensure_programs_subtab(shared_driver)
    detail = ProgramDetailPage(shared_driver)

    # Step 1: scroll to find a trailer-capable Program card
    print(f"\n[6608] Scrolling PROGRAMS list to find a trailer-capable card")
    target_card = studio.scroll_to_first_program_with_trailer(max_scrolls=5)

    assert target_card is not None, (
        f"No Program card with button_trailer found after scrolling. "
        f"Expected at least 1 trailer-capable program on this Studio "
        f"(currently 'ONE MOVE A DAY' and 'AMPLIFY YOUR CHAKRAS')."
    )
    print(f"[6608] ✓ Found trailer-capable Program card")

    # Step 2: tap TRAILER → verify exo surface appears
    print(f"[6608] Tapping TRAILER button")
    studio.tap_trailer_on_card(target_card)

    # Re-fetch card reference (recycler may have rebound during the tap)
    viewport_trailer_cards = studio.find_program_cards_with_trailer()
    assert len(viewport_trailer_cards) >= 1, (
        "After tapping TRAILER, no trailer-capable cards in viewport — "
        "recycler may have shifted unexpectedly"
    )
    target_card = viewport_trailer_cards[0]

    is_playing = studio.is_trailer_playing_on_card(target_card)
    print(f"[6608] Trailer playing on target card: {is_playing}")
    assert is_playing, (
        f"After tapping button_trailer, exo_content_frame should be "
        f"visible inside the card's media_container. Not found — trailer "
        f"playback may have failed to start."
    )

    try:
        # Step 3: tap player surface → verify navigation to detail page
        print(f"[6608] Tapping player surface — should navigate to detail")
        # dismiss_trailer_on_card() taps exo_content_frame. The
        # method name is a holdover from earlier hypothesis — the
        # actual behavior is navigation to detail, not dismissal.
        studio.dismiss_trailer_on_card(target_card)

        # Verify we landed on Program detail page
        assert detail.is_loaded(timeout=5), (
            f"After tapping the playing trailer, the Program detail page "
            f"should have loaded (layout_header visible). It did not — "
            f"either trailer-tap behavior changed, or the navigation "
            f"failed."
        )
        print(f"[6608] ✓ Tapping trailer navigated to Program detail page")

    finally:
        # Step 4: cleanup — close detail page back to PROGRAMS
        try:
            if detail.is_loaded(timeout=2):
                print(f"[6608] Closing Program detail page (cleanup)")
                detail.close()
        except Exception as e:
            print(f"[6608] Cleanup close failed: {e} — using back button")
            try:
                shared_driver.back()
            except Exception:
                pass


# =========================================================
# FORME-6607 — Trailer link NOT shown on Collections
# =========================================================

@pytest.mark.studio
def test_trailer_not_shown_on_collections(shared_driver):
    """FORME-6607: Verify Collections (cards WITHOUT button_trailer)
    exist in PROGRAMS sub-tab. Scrolls through entire list (~10 cards)
    for accurate counting."""
    studio = _ensure_programs_subtab(shared_driver)

    print(f"\n[6607] Scrolling PROGRAMS list to enumerate all cards")
    all_cards = studio.scroll_collect_all_program_cards(max_scrolls=5)

    with_trailer = [c for c in all_cards if c["has_trailer"]]
    without_trailer = [c for c in all_cards if not c["has_trailer"]]

    print(f"[6607] Total programs seen: {len(all_cards)}")
    print(f"[6607] Cards WITH trailer (Programs): {len(with_trailer)}")
    print(f"[6607] Cards WITHOUT trailer (Collections): {len(without_trailer)}")

    assert len(all_cards) >= 1, (
        f"Expected at least 1 Program card in PROGRAMS sub-tab, found 0."
    )

    assert len(without_trailer) >= 1, (
        f"Expected at least 1 Collection (Program card without "
        f"button_trailer). Found {len(without_trailer)} Collections out "
        f"of {len(all_cards)} total cards."
    )
    print(f"[6607] ✓ {len(without_trailer)} Collection(s) confirmed without "
          f"trailer link")


# =========================================================
# FORME-6595 — Programs Details page UI
# =========================================================

@pytest.mark.studio
def test_program_detail_page_ui(shared_driver):
    """FORME-6595: Verify Program detail page renders with expected
    structural elements after tapping VIEW CLASSES on a Program card."""
    studio = _ensure_programs_subtab(shared_driver)

    print(f"\n[6595] Opening Program detail page")
    program_cards = studio.find_program_cards()
    assert len(program_cards) >= 1, (
        f"Expected at least 1 Program card in PROGRAMS sub-tab, "
        f"found {len(program_cards)}"
    )

    target_card = None
    for card in program_cards:
        try:
            card.find_element(
                "id",
                f"{studio.APP_PACKAGE}:id/{studio.BUTTON_VIEW_CLASSES_ID}",
            )
            target_card = card
            break
        except Exception:
            continue
    assert target_card is not None, (
        "No Program card with button_view_classes found"
    )

    studio.tap_view_classes_on_card(target_card)
    detail = ProgramDetailPage(shared_driver)

    try:
        detail.wait_for_loaded(timeout=10)
        assert detail.is_loaded(), "Program detail page should be loaded"
        print(f"[6595] ✓ Program detail page loaded (layout_header present)")

        assert detail.is_visible(detail.IMAGE_HEADER_ID, timeout=2), (
            "image_header should be visible on Program detail page"
        )
        print(f"[6595] ✓ image_header visible")

        assert detail.is_visible(detail.BUTTON_CLOSE_ID, timeout=2), (
            "button_close should be visible on Program detail page"
        )
        print(f"[6595] ✓ button_close visible")

        assert detail.is_visible(detail.LAYOUT_INFO_ID, timeout=2), (
            "layout_info (program metadata block) should be visible"
        )
        print(f"[6595] ✓ layout_info visible")

        description = detail.get_description()
        assert description and len(description) > 0, (
            f"text_description should be non-empty, got: '{description}'"
        )
        print(f"[6595] ✓ Description present ({len(description)} chars): "
              f"'{description[:80]}{'...' if len(description) > 80 else ''}'")

        total, completed = detail.get_class_counts()
        assert total is not None and total >= 1, (
            f"text_classes should be a positive integer, got: {total}"
        )
        assert completed is not None and completed >= 0, (
            f"text_completed should be a non-negative integer, got: {completed}"
        )
        assert completed <= total, (
            f"Completed ({completed}) cannot exceed total ({total})"
        )
        print(f"[6595] ✓ Class counts valid: {completed}/{total} completed")

        bound_cards = detail.find_all_visible_class_records()
        print(f"[6595] {len(bound_cards)} fully-bound class card(s) visible")
        assert len(bound_cards) >= 1, (
            f"Expected ≥1 fully-bound class card, found {len(bound_cards)}"
        )
        assert len(bound_cards) <= total, (
            f"More bound cards ({len(bound_cards)}) than total ({total})"
        )

        for i, card in enumerate(bound_cards):
            assert card["title"], f"Card [{i}] has no title: {card}"
            assert card["detail"], f"Card [{i}] has no detail: {card}"
        print(f"[6595] ✓ All {len(bound_cards)} bound cards have title + detail")

    finally:
        try:
            print(f"\n[6595] Closing Program detail page")
            detail.close()
        except Exception as e:
            print(f"[6595] Close failed: {e}")
            try:
                shared_driver.back()
            except Exception:
                pass