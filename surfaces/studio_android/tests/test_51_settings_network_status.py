"""test_51_settings_network_status — Settings › Network Status MAC address tests.

Covers the MAC address display additions introduced in commit 24ff5a2:

  - test_NEW_ethernet_mac_address_displayed
      Verify a MAC Address row is present in the Ethernet section of
      the Network Status screen and contains a value in the expected
      XX:XX:XX:XX:XX:XX format.

  - test_NEW_wifi_mac_address_displayed
      Verify a MAC Address row is present in the Wi-Fi section of the
      Network Status screen.

  - test_NEW_mac_addresses_are_uppercase
      Verify that all MAC address values displayed are uppercase
      (matching the .uppercase() call in SettingsNetworkStatusFragment).

Pre-conditions:
  - Ethernet cable must be connected to the Studio device.
  - Wi-Fi must be enabled on the Studio device.
  - OWNER_PROFILE_INDEX from config_local.py is valid.

Run all:
    pytest -m studio surfaces/studio_android/tests/test_51_settings_network_status.py -v -s
"""
import re
import pytest
import logging

from surfaces.studio_android.pages.settings_network_status_page import SettingsNetworkStatusPage
from surfaces.studio_android.pages.home_page import HomePage

try:
    from surfaces.studio_android.config_local import OWNER_PROFILE_INDEX
except ImportError:
    OWNER_PROFILE_INDEX = 0

log = logging.getLogger(__name__)

# Regex for a standard MAC address (uppercase enforced in assertions)
MAC_PATTERN = re.compile(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$')


# ---------------------------------------------------------------------------
# Module-scoped fixture — login once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def network_status_driver(request):
    """Login as owner and yield a driver already on the Home screen."""
    from surfaces.studio_android.conftest import (
        _create_studio_driver,
        login_at_profile_index,
    )

    driver = _create_studio_driver(request)
    login_at_profile_index(driver, OWNER_PROFILE_INDEX)
    yield driver
    try:
        driver.quit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def _navigate_to_network_status(driver) -> SettingsNetworkStatusPage:
    """From Home, navigate: Settings → Network → Network Status."""
    home = HomePage(driver)
    home.tap_settings()

    page = SettingsNetworkStatusPage(driver)
    # Tap Network in SettingsMainFragment
    page.tap_by_text("Network")
    # Tap Network Status in the network submenu
    page.tap_by_text("Network Status")

    assert page.is_loaded(timeout=10), "Network Status screen did not load"
    log.info("Navigated to Network Status screen")
    return page


def _return_to_home(driver):
    """Pop back to Home."""
    home = HomePage(driver)
    for _ in range(4):
        try:
            if home.is_loaded(timeout=2):
                return
            driver.back()
        except Exception:
            break


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.studio
def test_NEW_ethernet_mac_address_displayed(network_status_driver):
    """A MAC Address row must be present in the Ethernet section and its
    value must be a non-empty string (getEthernetMAC() returned a value)."""
    driver = network_status_driver
    page = _navigate_to_network_status(driver)

    try:
        assert page.is_ethernet_mac_visible(), (
            "Ethernet MAC Address row not found in Network Status screen"
        )
        macs = page.get_all_mac_addresses()
        log.info("MAC addresses found: %s", macs)
        assert len(macs) >= 1, "No MAC address values rendered on Network Status screen"
        assert macs[0], "Ethernet MAC address value is empty"
    finally:
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_wifi_mac_address_displayed(network_status_driver):
    """Both Ethernet AND Wi-Fi MAC Address rows must be present (two MAC
    rows total — one per interface)."""
    driver = network_status_driver
    page = _navigate_to_network_status(driver)

    try:
        assert page.is_wifi_mac_visible(), (
            "Expected at least two MAC Address rows (Ethernet + Wi-Fi) "
            "but found fewer on the Network Status screen"
        )
        macs = page.get_all_mac_addresses()
        log.info("All MAC addresses: %s", macs)
        assert len(macs) >= 2, (
            f"Expected >= 2 MAC rows, found {len(macs)}: {macs}"
        )
    finally:
        _return_to_home(driver)


@pytest.mark.studio
def test_NEW_mac_addresses_are_uppercase(network_status_driver):
    """All displayed MAC addresses must be uppercase (matching the
    .uppercase() call added in SettingsNetworkStatusFragment)."""
    driver = network_status_driver
    page = _navigate_to_network_status(driver)

    try:
        macs = page.get_all_mac_addresses()
        log.info("MAC addresses for uppercase check: %s", macs)
        assert macs, "No MAC address values found — cannot verify case"
        for mac in macs:
            assert mac == mac.upper(), (
                f"MAC address {mac!r} is not fully uppercase"
            )
            assert MAC_PATTERN.match(mac), (
                f"MAC address {mac!r} does not match expected XX:XX:XX:XX:XX:XX format"
            )
    finally:
        _return_to_home(driver)
