"""
MW-3234: Verify content-desc is set on planned session cards in Studio.
VODClassViewHolder now sets card.contentDescription = workout.sessionType.toString()
enabling Appium to locate session cards by type.
"""
import pytest
from pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestMW3234SessionCardContentDesc:

    def test_MW_3234_cps_card_has_session_type_content_desc_in_studio(self, studio):
        """
        MW-3234: Verify CPS cards in Studio carry a non-empty content-desc equal
        to the session type string (e.g. CUSTOM_PLANNED_SESSION).
        Steps:
          1. Navigate to Studio tab.
          2. Open the Custom Planned Sessions category.
          3. Wait for session cards to load.
          4. Read content-desc from the first visible card.
          5. Assert it is non-empty (session type string is set).
        """
        studio.navigate_to_studio()
        studio.open_custom_planned_sessions()

        content_desc = studio.get_session_card_content_desc()

        assert content_desc, (
            "CPS card in Studio has no content-desc — "
            "expected sessionType.toString() e.g. 'CUSTOM_PLANNED_SESSION'"
        )

    def test_MW_3234_vod_card_has_session_type_content_desc_in_studio(self, studio):
        """
        MW-3234: Verify regular VOD cards in Studio also carry a non-empty
        content-desc equal to their session type (e.g. VOD).
        Steps:
          1. Navigate to Studio tab.
          2. Select any VOD category (non-Custom).
          3. Wait for session cards to load.
          4. Read content-desc from the first visible card.
          5. Assert it is non-empty (session type string is set).
        """
        studio.navigate_to_studio()
        studio.select_vod_category()

        content_desc = studio.get_session_card_content_desc()

        assert content_desc, (
            "VOD card in Studio has no content-desc — "
            "expected sessionType.toString() e.g. 'VOD'"
        )
