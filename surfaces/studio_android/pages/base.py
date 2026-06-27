"""Studio device surface base page.

Binds core BasePage to the Studio app's APP_PACKAGE. Every page object
under surfaces/studio/pages/ subclasses StudioBasePage instead of the
core BasePage directly.
"""
from core.base_page import BasePage, log  # noqa: F401
from surfaces.studio_android.config import APP_PACKAGE, WAIT_DEFAULT


class StudioBasePage(BasePage):
    APP_PACKAGE = APP_PACKAGE
    WAIT_DEFAULT = WAIT_DEFAULT
