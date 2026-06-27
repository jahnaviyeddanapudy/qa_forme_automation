"""Studio Android surface fixtures."""
import pytest
from core.driver_factory import create_driver
from surfaces.studio_android.config import APP_PACKAGE, APP_ACTIVITY


@pytest.fixture(scope="session")
def driver():
    d = create_driver(APP_PACKAGE, APP_ACTIVITY)
    yield d
    d.quit()
