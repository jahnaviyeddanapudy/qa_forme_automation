"""Studio Android smoke tests — stub, to be expanded by Claw Bot."""
import pytest
from surfaces.studio_android.pages.base import StudioAndroidBasePage


@pytest.fixture()
def app(driver):
    return StudioAndroidBasePage(driver)


class TestStudioSmoke:

    def test_app_launches(self, app):
        """Verify the studio app launches to the expected screen."""
        assert app.is_visible("tab_studio") or app.is_text_visible("Studio"), \
            "Studio app did not launch to the expected screen"
