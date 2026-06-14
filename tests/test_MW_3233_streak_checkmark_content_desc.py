"""
MW-3233: Verify streak day checkmark images have content-desc 'completed' or
'incomplete' on the ImageView element inside ViewDayCheckmark.

ViewDayCheckmark.bind() (MW-3233) sets:
  binding.image.contentDescription = if (checked) "completed" else "incomplete"
The content-desc was moved from the root view to the inner image element.
WeekStatsDayCheckmarksView no longer sets it on views[dow]?.root.
"""
import pytest
from pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestMW3233StreakCheckmarkContentDesc:

    def test_MW_3233_streak_checkmark_images_have_content_desc_on_profile_screen(self, studio):
        """
        MW-3233: Verify that day checkmark ImageView elements on the profile screen
        have content-desc set to 'completed' or 'incomplete'.
        Steps:
          1. Ensure the user is logged in and on the main nav.
          2. Tap the profile button (header_profile_button) to open the profile screen.
          3. Wait for the weekly streak / activity summary to load.
          4. Assert at least one ImageView has content-desc 'completed' or 'incomplete'.
        """
        studio.ensure_logged_in()
        studio.tap(studio.PROFILE_BUTTON)
        studio.wait_seconds(2)

        assert studio.is_streak_checkmark_image_content_desc_visible(), (
            "No streak checkmark ImageView found with content-desc 'completed' or 'incomplete'. "
            "Verify MW-3233 is deployed and ViewDayCheckmark.bind() sets binding.image.contentDescription."
        )

    def test_MW_3233_streak_checkmark_content_desc_not_on_root_view(self, studio):
        """
        MW-3233: Verify that the content-desc 'completed'/'incomplete' is on the
        ImageView (binding.image), NOT on the root container view.
        WeekStatsDayCheckmarksView removed views[dow]?.root?.contentDescription — the
        root should no longer carry these values.
        Steps:
          1. Open the profile screen.
          2. Search for a FrameLayout or ConstraintLayout (root-level container) with
             content-desc 'completed' or 'incomplete'.
          3. Assert none are found (the root no longer has this attribute).
          4. Assert at least one ImageView DOES have it (binding.image).
        """
        from appium.webdriver.common.appiumby import AppiumBy

        studio.ensure_logged_in()
        studio.tap(studio.PROFILE_BUTTON)
        studio.wait_seconds(2)

        for layout_class in ("android.widget.FrameLayout", "androidx.constraintlayout.widget.ConstraintLayout"):
            for desc in ("completed", "incomplete"):
                els = studio.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("{layout_class}").descriptionContains("{desc}")',
                )
                assert not els, (
                    f"Found a {layout_class} root with content-desc '{desc}' — "
                    "this should have been removed from the root and moved to the ImageView (MW-3233)"
                )

        assert studio.is_streak_checkmark_image_content_desc_visible(), (
            "No ImageView found with content-desc 'completed' or 'incomplete' — "
            "expected it on binding.image inside ViewDayCheckmark"
        )
