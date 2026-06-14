"""
Bookmarks test cases
FORME-1819 | FORME-1833 | FORME-1825
"""
import pytest
from pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestBookmarks:

    def test_FORME_1819_bookmark_icon_on_vod_classes(self, studio):
        """
        FORME-1819: Verify bookmark icon on VOD Classes.
        Pre-condition: User is logged in to Members App.
        Steps:
          1. Navigate to Studio tab and select a VOD category (e.g. Strength).
          2. Verify VOD tiles have bookmark icon in top-right corner.
          3. Tap bookmark icon on a VOD.
          4. Verify the VOD is added to the Bookmarked filter list.
        """
        studio.navigate_to_studio()
        studio.select_vod_category()
        assert studio.is_bookmark_icon_visible_on_vod(), \
            "Bookmark icon is not visible on VOD tiles in Studio tab"

        studio.tap_bookmark_icon_on_vod()
        studio.wait_seconds(1)

        studio.filter_bookmarked()
        assert studio.is_class_in_bookmarked_list(), \
            "VOD class was not added to Bookmarked list after tapping bookmark icon"

    def test_FORME_1833_bookmark_icon_on_program_classes(self, studio):
        """
        FORME-1833: Verify bookmark icon on Program classes.
        Steps:
          1. Under Programs, tap bookmark icon on a class.
          2. Verify the class is bookmarked and added to the list of Bookmarked classes.
        """
        studio.navigate_to_studio()
        studio.tap_bookmark_icon_on_program_class()
        studio.wait_seconds(1)

        studio.filter_bookmarked()
        assert studio.is_class_in_bookmarked_list(), \
            "Program class was not added to Bookmarked list after tapping bookmark icon"

    def test_FORME_1825_removing_bookmark_for_recommended_classes(self, studio):
        """
        FORME-1825: Verify removing Bookmark for Recommended Classes.
        Pre-condition: User is logged in to Members App.
        Steps:
          1. Navigate to 'Your Plan' tab.
          2. Tap on an active bookmark icon for a Recommended class.
          3. Verify bookmark changes to inactive state.
          4. Verify class is removed from the Bookmarked classes list.
        """
        studio.navigate_to_your_plan()
        assert studio.is_text_contains_displayed("Recommended"), \
            "Recommended section is not visible on Your Plan tab"

        studio.tap_active_bookmark_in_recommended()
        studio.wait_seconds(1)

        studio.navigate_to_studio()
        studio.filter_bookmarked()
        assert not studio.is_text_contains_displayed("Recommended class"), \
            "Recommended class was not removed from Bookmarked list after un-bookmarking"
