"""Root pytest configuration — cross-surface.

Surface-specific fixtures (driver, api_token, etc.) live in each
surface's conftest.py under surfaces/<surface>/conftest.py.

Run per-surface:
    pytest surfaces/member_android/
    pytest surfaces/studio_android/
    pytest -m member_android
    pytest -m studio_android
"""
import pytest

from core.adb_helpers import detect_device_profile

DEVICE_PROFILE = None
DEVICE_MANUFACTURER = None
DEVICE_MODEL = None


@pytest.fixture(scope="session", autouse=True)
def detect_device():
    global DEVICE_PROFILE, DEVICE_MANUFACTURER, DEVICE_MODEL
    DEVICE_PROFILE, DEVICE_MANUFACTURER, DEVICE_MODEL = detect_device_profile()
    print(
        f"\n[setup] device profile: {DEVICE_PROFILE} "
        f"(manufacturer={DEVICE_MANUFACTURER or 'unknown'}, "
        f"model={DEVICE_MODEL or 'unknown'})"
    )
    yield
