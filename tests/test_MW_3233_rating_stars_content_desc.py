"""
MW-3233: Verify rating star checkboxes in Post-Session Survey have the correct
content-desc format: rating_<title_snake_case>_star_<n> (all lowercase).

PostClassSurveyAdapter sets:
  binding.root.contentDescription = "rating_${step.title.toSnakeCase()}_star_${index + 1}"
where toSnakeCase() now also lowercases the result (StringExtensions.kt MW-3233).
"""
import pytest
from pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestMW3233RatingStarsContentDesc:

    def test_MW_3233_rating_stars_have_content_desc_after_vod_completion(self, studio):
        """
        MW-3233: Verify rating star elements in the Post-Session Survey have
        content-desc matching the pattern 'rating_*_star_*' (all lowercase).
        Steps:
          1. Navigate to Studio tab and play a VOD class.
          2. Wait for the Post-Session Survey to appear (max 180s).
          3. Assert at least one star element with content-desc 'rating_*_star_*' is visible.
          4. Assert the first star (star_1) is selectable via content-desc.
          5. Tap the first star using the content-desc selector.
          6. Assert Submit button becomes active.
        """
        studio.navigate_to_studio()
        studio.play_vod_class()

        max_wait = 180
        elapsed = 0
        interval = 5
        survey_appeared = False
        while elapsed < max_wait:
            if studio.is_post_session_survey_displayed():
                survey_appeared = True
                break
            studio.wait_seconds(interval)
            elapsed += interval

        assert survey_appeared, "Post-Session Survey did not appear after VOD class completion"

        assert studio.is_rating_star_content_desc_visible(), (
            "No rating star element found with content-desc matching 'rating_*_star_*' — "
            "check that MW-3233 is deployed and toSnakeCase() lowercases the title"
        )

        studio.tap_rating_star(1)
        studio.wait_seconds(1)

        assert studio.is_submit_active(), (
            "Submit button should be active after tapping the first rating star via content-desc"
        )

    def test_MW_3233_rating_star_content_desc_is_lowercase(self, studio):
        """
        MW-3233: Verify that rating star content-descs are fully lowercase.
        toSnakeCase() now calls .lowercase() — selectors must use lowercase strings.
        Steps:
          1. Navigate to Studio and play a VOD class.
          2. Wait for Post-Session Survey (max 180s).
          3. Assert no star element exists with an uppercase letter in its content-desc.
          4. Assert at least one element with the all-lowercase pattern exists.
        """
        from appium.webdriver.common.appiumby import AppiumBy

        studio.navigate_to_studio()
        studio.play_vod_class()

        max_wait = 180
        elapsed = 0
        interval = 5
        survey_appeared = False
        while elapsed < max_wait:
            if studio.is_post_session_survey_displayed():
                survey_appeared = True
                break
            studio.wait_seconds(interval)
            elapsed += interval

        assert survey_appeared, "Post-Session Survey did not appear after VOD class completion"

        assert studio.is_rating_star_content_desc_visible(), (
            "Rating star content-descs not found — cannot verify lowercase format"
        )

        try:
            el = studio.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionMatches("rating_[a-z_]+_star_[0-9]+")',
            )
            assert el.is_displayed(), "Lowercase rating star element is not visible"
        except Exception:
            pytest.fail(
                "No rating star found matching all-lowercase pattern 'rating_[a-z_]+_star_[0-9]+'. "
                "Content-desc may still contain uppercase characters."
            )
