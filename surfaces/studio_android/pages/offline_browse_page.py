"""OfflineBrowsePage — Studio's offline browse screen.

Reached when the device has no network connectivity and the app loads
the offline cache. Backed by OfflineBrowseActivity + OfflineBrowseFragment.

Layout (confirmed from Kotlin source, 2026-04-22 / 2026-04-23):

  ActivityOfflineBrowseBinding
    profile_button          ← top-left; tapping finishes the activity
    utility_button          ← top-right; toggles control-centre panel
    fragment_control_center ← control-centre overlay (gone/visible)
    nav_host_fragment       ← hosts OfflineBrowseFragment

  FragmentOfflineBrowseBinding (inside nav_host_fragment)
    tab_layout              ← TabLayout: STUDIO tab (always) + LIFT tab
                               (only when Lift is registered)
    layout_categories       ← horizontal strip of category chips
    recycler                ← grid of downloaded class cards
    text_empty              ← shown when current tab has no downloads
    view_just_lift          ← "Just Lift" shortcut card; visible only
                               when Lift registered AND LIFT tab selected
      root                  ← view_just_lift.root (visibleOrGone target)

Tabs (from OfflineBrowseFragment.Tab enum):
  Position 0 → STUDIO  (always present)
  Position 1 → LIFT    (only when liftViewModel.isLiftRegistered())

Category chips appear below the tab strip. Tapping a chip filters the
recycler to that category. Tapping it again (or the chip for the
current tab with no filter) resets to all downloads for that tab.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class OfflineBrowsePage(StudioBasePage):
    # ---- Activity-level IDs (ActivityOfflineBrowseBinding) ----
    PROFILE_BUTTON_ID = "profile_button"
    UTILITY_BUTTON_ID = "utility_button"
    FRAGMENT_CONTROL_CENTER_ID = "fragment_control_center"
    NAV_HOST_FRAGMENT_ID = "nav_host_fragment"

    # ---- Fragment-level IDs (FragmentOfflineBrowseBinding) ----
    TAB_LAYOUT_ID = "tab_layout"
    LAYOUT_CATEGORIES_ID = "layout_categories"
    RECYCLER_ID = "recycler"
    TEXT_EMPTY_ID = "text_empty"
    VIEW_JUST_LIFT_ID = "view_just_lift"

    # Tab text labels (from strings.xml R.string.studio / R.string.lift)
    TAB_STUDIO_TEXT = "Studio"
    TAB_LIFT_TEXT = "Lift"

    # ------------------------------------------------------------------ #
    #  Screen presence                                                     #
    # ------------------------------------------------------------------ #

    def wait_for_offline_browse_screen(self, timeout: int = 10) -> None:
        """Wait until the offline browse screen is fully rendered.

        We use the tab_layout as the canonical 'page loaded' marker
        because it is always present regardless of download state.
        """
        log.info("OfflineBrowsePage: waiting for offline browse screen")
        wait = WebDriverWait(self.driver, timeout)
        wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.TAB_LAYOUT_ID}")
            )
        )
        log.info("OfflineBrowsePage: offline browse screen loaded")

    def is_loaded(self, timeout: int = 5) -> bool:
        """Return True if the offline browse screen appears to be loaded."""
        return self.is_visible(self.TAB_LAYOUT_ID, timeout=timeout)

    # ------------------------------------------------------------------ #
    #  Tab interactions                                                    #
    # ------------------------------------------------------------------ #

    def get_tab_count(self) -> int:
        """Return the number of tabs currently shown in tab_layout."""
        tabs = self.driver.find_elements(
            AppiumBy.XPATH,
            f'//android.widget.TabLayout[@resource-id="{self.APP_PACKAGE}:id/{self.TAB_LAYOUT_ID}"]/android.widget.LinearLayout',
        )
        count = len(tabs)
        log.info(f"OfflineBrowsePage: tab count = {count}")
        return count

    def is_studio_tab_visible(self) -> bool:
        """Return True if the STUDIO tab text is visible."""
        return self.is_text_visible(self.TAB_STUDIO_TEXT, timeout=5)

    def is_lift_tab_visible(self) -> bool:
        """Return True if the LIFT tab text is visible."""
        return self.is_text_visible(self.TAB_LIFT_TEXT, timeout=3)

    def tap_studio_tab(self) -> None:
        """Select the STUDIO tab."""
        log.info("OfflineBrowsePage: tapping STUDIO tab")
        self.tap_by_text(self.TAB_STUDIO_TEXT)

    def tap_lift_tab(self) -> None:
        """Select the LIFT tab (only available when Lift is registered)."""
        log.info("OfflineBrowsePage: tapping LIFT tab")
        self.tap_by_text(self.TAB_LIFT_TEXT)

    # ------------------------------------------------------------------ #
    #  Content area                                                        #
    # ------------------------------------------------------------------ #

    def is_recycler_visible(self) -> bool:
        """Return True if the class card recycler is visible (has content)."""
        return self.is_visible(self.RECYCLER_ID, timeout=5)

    def is_empty_state_visible(self) -> bool:
        """Return True if the 'no downloaded classes' empty-state text is shown."""
        return self.is_visible(self.TEXT_EMPTY_ID, timeout=5)

    def is_just_lift_visible(self) -> bool:
        """Return True if the Just Lift shortcut card is visible.

        Per OfflineBrowseFragment.updateJustLiftVisibility(), this is only
        shown when Lift is registered AND the LIFT tab is currently selected.
        """
        return self.is_visible(self.VIEW_JUST_LIFT_ID, timeout=3)

    def get_category_chips(self) -> list:
        """Return all visible category chip elements from layout_categories."""
        chips = self.driver.find_elements(
            AppiumBy.XPATH,
            f'//android.view.ViewGroup[@resource-id="{self.APP_PACKAGE}:id/{self.LAYOUT_CATEGORIES_ID}"]//android.widget.TextView',
        )
        log.info(f"OfflineBrowsePage: found {len(chips)} category chips")
        return chips

    def get_category_chip_labels(self) -> list:
        """Return the text labels of all visible category chips."""
        return [chip.text for chip in self.get_category_chips()]

    # ------------------------------------------------------------------ #
    #  Header button interactions                                          #
    # ------------------------------------------------------------------ #

    def tap_profile_button(self) -> None:
        """Tap the profile button — finishes OfflineBrowseActivity."""
        log.info("OfflineBrowsePage: tapping profile button")
        self.tap_by_id(self.PROFILE_BUTTON_ID)

    def tap_utility_button(self) -> None:
        """Tap the utility button — toggles the control-centre panel."""
        log.info("OfflineBrowsePage: tapping utility button")
        self.tap_by_id(self.UTILITY_BUTTON_ID)

    def is_control_center_visible(self) -> bool:
        """Return True if the control-centre fragment overlay is visible."""
        return self.is_visible(self.FRAGMENT_CONTROL_CENTER_ID, timeout=3)
