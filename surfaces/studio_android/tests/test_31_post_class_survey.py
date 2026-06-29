"""test_31_post_class_survey — Post-class survey rating-star accessibility tests.

Covers STUDIO-4263 / PostClassSurveyAdapter change (2026-05-12):
  Dynamic content-description attributes are now assigned to every
  rating star in the post-class survey using the pattern:
    "rating_{step.title.toSnakeCase()}_star_{index+1}"

This file verifies:
  - test_STUDIO_4263_session_stars_have_content_descriptions
      All 5 Session stars are reachable via AccessibilityId.
  - test_STUDIO_4263_instructor_stars_have_content_descriptions
      All 5 Instructor stars are reachable via AccessibilityId
      (VOD class variant only — skipped if section absent).
  - test_STUDIO_4263_difficulty_stars_have_content_descriptions
      All 5 Difficulty For You stars are reachable via AccessibilityId.
  - test_STUDIO_4263_star_content_desc_format_matches_snake_case_title
      Spot-check: verifies that content-desc values match the expected
      snake_case pattern derived from step titles.
  - test_STUDIO_4263_tap_middle_star_each_section_and_submit
      End-to-end: tap star 3 in each visible section, tap SUBMIT,
      verify we leave the rating screen (SummaryPage or Home).

Pre-conditions:
  - A class must have been played long enough to trigger the rating
    screen (>=50% playback). This test file uses the module-scoped
    `rating_screen_driver` fixture which plays a short class to
    completion and lands on RatingPage before any test runs.
  - The build under test must include the PostClassSurveyAdapter
    commit (a51af65fe222601d0ec831cf8b8033b29c3a7d75).

Architecture:
  - Module-scoped fixture handles the expensive class-play setup.
  - Individual tests are fast (element checks + taps).
  - Tests run in declaration order (pytest default) — the submit
    test is LAST because it navigates away from the rating screen.

Run:
    pytest -m studio surfaces/studio_android/tests/test_31_post_class_survey.py -v -s
"""
import logging
import pytest

from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.pages.class_detail_page import ClassDetailPage
from surfaces.studio_android.pages.apple_watch_prompt_page import AppleWatchPromptPage
from surfaces.studio_android.pages.player_page import PlayerPage
from surfaces.studio_android.pages.rating_page import RatingPage
from surfaces.studio_android.pages.summary_page import SummaryPage

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Module-scoped fixture — play a class to trigger the rating screen once.
# All tests in this file share the resulting driver state.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def rating_screen_driver(first_profile_driver):
    """Play a short VOD class to completion (or near-completion) so that
    the post-class survey / rating screen appears.

    Strategy:
      1. Navigate to STUDIO tab → WORKOUTS sub-tab.
      2. Tap the first non-completed class card (short class preferred).
      3. Dismiss Apple Watch prompt if it appears.
      4. Play for enough time that the rating screen will appear on END.
         We end the session early via PlayerPage.end_session() once
         we've played for the minimum threshold (app triggers rating at
         ~50% completion; we wait for class_time to decrease by ~60s
         which is sufficient for a 10-min class).
      5. Wait for RatingPage to appear.

    Yields the driver after landing on RatingPage.
    Tests must NOT navigate away — the submit test is last and does so.
    """
    driver = first_profile_driver

    home = HomePage(driver)
    assert home.is_loaded(timeout=15), "Expected Home screen after login"
    log.info("rating_screen_driver: on Home")

    studio = StudioTabPage(driver)
    home.tap_studio_tab()
    studio.wait_for_studio_tab(timeout=10)
    studio.tap_sub_tab("WORKOUTS")
    log.info("rating_screen_driver: on WORKOUTS sub-tab")

    detail = ClassDetailPage(driver)
    studio.tap_first_non_completed_card()
    detail.wait_for_class_detail(timeout=10)
    log.info("rating_screen_driver: ClassDetail loaded")

    detail.tap_start_class()
    log.info("rating_screen_driver: tapped START SESSION")

    # Dismiss Apple Watch prompt if shown
    apple = AppleWatchPromptPage(driver)
    if apple.is_visible(timeout=4):
        log.info("rating_screen_driver: dismissing Apple Watch prompt")
        apple.tap_continue_to_session()

    player = PlayerPage(driver)
    player.wait_for_player(timeout=20)
    log.info("rating_screen_driver: player loaded")

    # Play for ~70 seconds to exceed the 50% threshold for a short class
    initial_time = player.get_remaining_time_seconds()
    log.info(f"rating_screen_driver: initial remaining time = {initial_time}s")

    elapsed_poll = 0
    poll_interval = 15  # keep UiAutomator2 alive
    target_decrease = 70  # seconds of real playback
    while elapsed_poll < target_decrease + 30:
        player.wait_seconds(poll_interval)
        elapsed_poll += poll_interval
        current_time = player.get_remaining_time_seconds()
        decrease = initial_time - current_time
        log.info(
            f"rating_screen_driver: played ~{elapsed_poll}s, "
            f"time decreased by {decrease}s"
        )
        if decrease >= target_decrease:
            break

    log.info("rating_screen_driver: ending session to trigger rating screen")
    player.end_session()

    rating = RatingPage(driver)
    rating.wait_for_rating_screen(timeout=20)
    log.info("rating_screen_driver: RatingPage visible — fixture ready")

    yield driver


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #

def _rating_page(driver):
    return RatingPage(driver)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

@pytest.mark.studio
def test_STUDIO_4263_session_stars_have_content_descriptions(rating_screen_driver):
    """Verify all 5 Session rating stars are accessible via content-description.

    PostClassSurveyAdapter now sets:
      contentDescription = "rating_session_star_{1..5}"
    on each star view. This test confirms all 5 are findable by
    AccessibilityId — proving the toSnakeCase() conversion produced
    the expected string for the 'Session' step title.
    """
    rating = _rating_page(rating_screen_driver)

    assert rating.is_session_section_visible(timeout=5), (
        "Session section header not visible on rating screen"
    )

    for star_num in range(1, 6):
        content_desc = f"rating_session_star_{star_num}"
        assert rating.is_star_visible(content_desc, timeout=5), (
            f"Session star '{content_desc}' not found via AccessibilityId — "
            f"PostClassSurveyAdapter may not have set contentDescription correctly"
        )
        log.info(f"test_STUDIO_4263: found '{content_desc}' ✓")


@pytest.mark.studio
def test_STUDIO_4263_instructor_stars_have_content_descriptions(rating_screen_driver):
    """Verify all 5 Instructor rating stars are accessible via content-description
    when the Instructor section is present (VOD class).

    PostClassSurveyAdapter sets:
      contentDescription = "rating_instructor_star_{1..5}"
    This test is skipped (not failed) if the Instructor section is absent
    (e.g. the fixture played a CPS/Workout class instead of a VOD).
    """
    rating = _rating_page(rating_screen_driver)

    if not rating.is_instructor_section_visible(timeout=3):
        pytest.skip(
            "Instructor section not visible — class played was not a VOD. "
            "Run fixture with a VOD class to cover this branch."
        )

    for star_num in range(1, 6):
        content_desc = f"rating_instructor_star_{star_num}"
        assert rating.is_star_visible(content_desc, timeout=5), (
            f"Instructor star '{content_desc}' not found via AccessibilityId"
        )
        log.info(f"test_STUDIO_4263: found '{content_desc}' ✓")


@pytest.mark.studio
def test_STUDIO_4263_difficulty_stars_have_content_descriptions(rating_screen_driver):
    """Verify all 5 Difficulty For You rating stars are accessible via
    content-description.

    PostClassSurveyAdapter sets:
      contentDescription = "rating_difficulty_for_you_star_{1..5}"
    'Difficulty For You' → toSnakeCase() → 'difficulty_for_you'
    This section appears in BOTH 2-section and 3-section survey variants.
    """
    rating = _rating_page(rating_screen_driver)

    assert rating.is_difficulty_section_visible(timeout=5), (
        "'Difficulty For You' section header not visible on rating screen"
    )

    for star_num in range(1, 6):
        content_desc = f"rating_difficulty_for_you_star_{star_num}"
        assert rating.is_star_visible(content_desc, timeout=5), (
            f"Difficulty star '{content_desc}' not found via AccessibilityId — "
            f"check that toSnakeCase() converts 'Difficulty For You' correctly"
        )
        log.info(f"test_STUDIO_4263: found '{content_desc}' ✓")


@pytest.mark.studio
def test_STUDIO_4263_star_content_desc_format_matches_snake_case_title(rating_screen_driver):
    """Spot-check the content-description naming convention.

    The adapter uses: f"rating_{step.title.toSnakeCase()}_star_{index+1}"

    This test verifies the concrete expected values for every known
    step title. If a step title changes on the server/CMS side, or if
    toSnakeCase() changes its output, this test will catch it.

    Known mappings (as of 2026-05-12 build):
      'Session'          → rating_session_star_1..5
      'Instructor'       → rating_instructor_star_1..5  (VOD only)
      'Difficulty For You' → rating_difficulty_for_you_star_1..5
    """
    rating = _rating_page(rating_screen_driver)

    # Session — always present
    expected_session = [f"rating_session_star_{i}" for i in range(1, 6)]
    for cd in expected_session:
        assert rating.is_star_visible(cd, timeout=5), (
            f"Expected content-desc '{cd}' missing — toSnakeCase format mismatch?"
        )

    # Instructor — present for VOD variant
    if rating.is_instructor_section_visible(timeout=3):
        expected_instructor = [f"rating_instructor_star_{i}" for i in range(1, 6)]
        for cd in expected_instructor:
            assert rating.is_star_visible(cd, timeout=5), (
                f"Expected content-desc '{cd}' missing"
            )

    # Difficulty For You — always present
    expected_difficulty = [f"rating_difficulty_for_you_star_{i}" for i in range(1, 6)]
    for cd in expected_difficulty:
        assert rating.is_star_visible(cd, timeout=5), (
            f"Expected content-desc '{cd}' missing — did step title change?"
        )

    log.info("test_STUDIO_4263: all content-desc spot-checks passed ✓")


@pytest.mark.studio
def test_STUDIO_4263_tap_middle_star_each_section_and_submit(rating_screen_driver):
    """End-to-end: tap star 3 (middle) in every visible section, then
    tap SUBMIT, and verify we leave the rating screen.

    This is the submit test and MUST be last — it navigates away from
    the rating screen, invalidating state for other tests.

    Acceptance criteria:
      - Each star 3 is tappable without error.
      - SUBMIT button is visible after rating.
      - Tapping SUBMIT transitions away from the rating screen
        (SummaryPage or Home — either indicates successful submission).
    """
    rating = _rating_page(rating_screen_driver)
    driver = rating_screen_driver

    # Tap star 3 in Session section
    assert rating.is_star_visible("rating_session_star_3", timeout=5), (
        "rating_session_star_3 not visible before tap"
    )
    rating.tap_session_star(3)
    log.info("test_STUDIO_4263: tapped rating_session_star_3")

    # Tap star 3 in Instructor section if present (VOD)
    if rating.is_instructor_section_visible(timeout=3):
        assert rating.is_star_visible("rating_instructor_star_3", timeout=5), (
            "rating_instructor_star_3 not visible before tap"
        )
        rating.tap_instructor_star(3)
        log.info("test_STUDIO_4263: tapped rating_instructor_star_3")
    else:
        log.info("test_STUDIO_4263: Instructor section absent — skipping instructor star tap")

    # Tap star 3 in Difficulty For You section
    assert rating.is_star_visible("rating_difficulty_for_you_star_3", timeout=5), (
        "rating_difficulty_for_you_star_3 not visible before tap"
    )
    rating.tap_difficulty_star(3)
    log.info("test_STUDIO_4263: tapped rating_difficulty_for_you_star_3")

    # Submit
    rating.tap_submit(timeout=10)
    log.info("test_STUDIO_4263: tapped SUBMIT")

    # Verify we left the rating screen — accept either SummaryPage or Home
    summary = SummaryPage(driver)
    home = HomePage(driver)

    on_summary = summary.is_loaded(timeout=15)
    on_home = False if on_summary else home.is_loaded(timeout=5)

    assert on_summary or on_home, (
        "After tapping SUBMIT on rating screen, neither SummaryPage nor "
        "Home was detected — submission may have failed or navigation broke"
    )
    log.info(
        f"test_STUDIO_4263: post-submit screen = "
        f"{'SummaryPage' if on_summary else 'HomePage'} ✓"
    )
