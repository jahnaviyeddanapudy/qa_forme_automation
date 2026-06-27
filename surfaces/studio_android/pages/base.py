"""Studio Android base page."""
from core.base_page import BasePage
from surfaces.studio_android.config import APP_PACKAGE


class StudioAndroidBasePage(BasePage):
    APP_PACKAGE = APP_PACKAGE
