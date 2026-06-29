"""SettingsNetworkStatusPage — Studio's Network Status screen.

Reached from SettingsNetworkFragment (or SettingsMainFragment → Network).
Renders a RecyclerView of NetworkStatusItem rows grouped by interface
(Ethernet, Wi-Fi, Performance).

New in commit 24ff5a2:
  - MAC address row added for Ethernet section.
  - MAC address row added for Wi-Fi section.
  Both use the string resource R.string.mac_address as the title.

Element IDs inferred from NetworkStatusAdapter + layout files:
  Each NetworkStatusItem row exposes:
    text_title   — label  (e.g. "MAC Address", "IP Address")
    text_value   — value  (e.g. "AA:BB:CC:DD:EE:FF")
  Section header rows:
    text_header  — section name (e.g. "ETHERNET", "WI-FI")

Top-level layout IDs (FragmentSettingsNetworkStatusBinding):
    button_close    — close / pop back
    button_refresh  — re-run speed test / refresh values
    recycler        — the status item list
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SettingsNetworkStatusPage(StudioBasePage):
    # ------------------------------------------------------------------ #
    # Layout IDs
    # ------------------------------------------------------------------ #
    RECYCLER_ID = "recycler"
    CLOSE_BUTTON_ID = "button_close"
    REFRESH_BUTTON_ID = "button_refresh"

    # NetworkStatusItem row IDs
    ITEM_TITLE_ID = "text_title"
    ITEM_VALUE_ID = "text_value"
    ITEM_HEADER_ID = "text_header"

    # Known label strings (from R.string.mac_address)
    MAC_ADDRESS_LABEL = "MAC Address"
    ETHERNET_HEADER = "ETHERNET"
    WIFI_HEADER = "WI-FI"

    # ------------------------------------------------------------------ #
    # Screen lifecycle
    # ------------------------------------------------------------------ #

    def is_loaded(self, timeout: int = 10) -> bool:
        """Return True when the network status recycler is visible."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ID, self._id(self.RECYCLER_ID))
                )
            )
            return True
        except Exception:
            return False

    def tap_close(self):
        """Close the network status screen."""
        self.tap_by_id(self.CLOSE_BUTTON_ID)

    def tap_refresh(self):
        """Tap the refresh button to re-fetch network status."""
        self.tap_by_id(self.REFRESH_BUTTON_ID)

    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #

    def _get_all_items(self) -> list:
        """Return a list of (title_text, value_text) tuples for every
        non-header row currently rendered in the recycler."""
        titles = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ITEM_TITLE_ID)
        )
        values = self.driver.find_elements(
            AppiumBy.ID, self._id(self.ITEM_VALUE_ID)
        )
        items = []
        for t, v in zip(titles, values):
            items.append((t.text.strip(), v.text.strip()))
        return items

    def get_value_for_label(self, label: str) -> str | None:
        """Return the value text for the first row whose title matches
        *label*, or None if not found."""
        for title, value in self._get_all_items():
            if title == label:
                return value
        return None

    def get_all_mac_addresses(self) -> list:
        """Return a list of all MAC address values shown on this screen
        (one per interface that exposes a MAC)."""
        macs = []
        for title, value in self._get_all_items():
            if title == self.MAC_ADDRESS_LABEL and value:
                macs.append(value)
        return macs

    def is_ethernet_mac_visible(self) -> bool:
        """Return True if a MAC Address row is present in the Ethernet
        section of the status list."""
        # We check that at least one MAC address row exists and that
        # the ETHERNET header appears before a MAC row in the flat list.
        try:
            headers = self.driver.find_elements(
                AppiumBy.ID, self._id(self.ITEM_HEADER_ID)
            )
            header_texts = [h.text.strip().upper() for h in headers]
            return self.ETHERNET_HEADER in header_texts and len(self.get_all_mac_addresses()) > 0
        except Exception as exc:
            log.debug("is_ethernet_mac_visible error: %s", exc)
            return False

    def is_wifi_mac_visible(self) -> bool:
        """Return True if at least two MAC Address rows are present,
        indicating both Ethernet and Wi-Fi MACs are shown."""
        return len(self.get_all_mac_addresses()) >= 2
