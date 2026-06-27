"""FilterPage — Studio's filter overlay.

Opened by tapping the FILTER button on Studio tab. Layout:

  fragment_filters
    content
      button_close             ← X to close overlay (top-left, no text)
      text_filter | FILTER     ← header text (just the label)
      [chevron_up]             ← scroll-to-top affordance (only when scrolled)
      list                     ← scrollable list of accordion sections
        Each section:
          text | <SECTION NAME>     ← LENGTH, LEVEL, FOCUS, EQUIPMENT, INSTRUCTORS
          [text_number | <N>]      ← appears IF >=1 option in this section is selected
          chevron                   ← icon (collapsed/expanded indicator)
          [if expanded:]
            text | <option 1>
            text | <option 2>
            ...
      [chevron_down]           ← scroll-to-bottom affordance (only when scrollable below)

Sections are ACCORDION-STYLE: tapping a section name toggles it open/closed.

Filter options (counts may grow with content updates):
  LENGTH:      5/10/15/20/25/30/35/40/45/50/55/60 MIN   (12)
  LEVEL:       ALL LEVELS, BEGINNER, INTERMEDIATE, ADVANCED   (4)
  FOCUS:       ~20 categories (AMPLIFIED, BOXING, CARDIO, CORE, ...)
  EQUIPMENT:   ~17 items (NO EQUIPMENT, BARRE, DUMBBELLS, FITBENCH, MAT, ...)
  INSTRUCTORS: ~30+ instructors (AMANDA M, BREEZIE J, KATE S, ...)

NOTE on selection state:
  - In the overlay, only `text_number` next to a section header indicates
    selections (shows the count of selected options in that section).
    Individual option items do NOT show a 'selected' marker in the element
    tree.
  - On the Studio tab beneath the overlay, each active filter appears as
    a CHIP in scroll_filters > layout_filters. Use StudioTabPage to read
    those chips for the canonical 'what's currently filtered' view.

NOTE on apply/dismiss:
  Filter selections are applied LIVE — results behind the overlay update
  immediately when an option is tapped. Closing the overlay (button_close)
  just dismisses it; no APPLY button is needed.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class FilterPage(StudioBasePage):
    # --- Element IDs (confirmed from dumps on 2026-04-27) ---
    FRAGMENT_ID = "fragment_filters"
    CONTENT_ID = "content"
    HEADER_TEXT_ID = "text_filter"          # value: 'FILTER'
    BUTTON_CLOSE_ID = "button_close"
    LIST_ID = "list"                        # scrollable list of sections

    # Per-section
    SECTION_TEXT_ID = "text"                # section name AND option text use this id
    SECTION_NUMBER_ID = "text_number"       # selection count badge (e.g. "1")
    CHEVRON_ID = "chevron"                  # next to each section name
    CHEVRON_UP_ID = "chevron_up"            # scroll affordance
    CHEVRON_DOWN_ID = "chevron_down"        # scroll affordance

    # Section names — use these when programmatically expanding sections
    SECTION_LENGTH = "LENGTH"
    SECTION_LEVEL = "LEVEL"
    SECTION_FOCUS = "FOCUS"
    SECTION_EQUIPMENT = "EQUIPMENT"
    SECTION_INSTRUCTORS = "INSTRUCTORS"

    KNOWN_SECTIONS = {
        SECTION_LENGTH, SECTION_LEVEL, SECTION_FOCUS,
        SECTION_EQUIPMENT, SECTION_INSTRUCTORS,
    }

    # --- Screen detection ---

    def is_open(self, timeout=3):
        """Non-blocking check: is the filter overlay currently open?"""
        return self.is_visible(self.FRAGMENT_ID, timeout=timeout)

    def wait_for_filter_overlay(self):
        """Block until the filter overlay renders."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.FRAGMENT_ID)
        ))
        log.info("Filter overlay loaded")

    # --- Open / close ---

    def close(self):
        """Tap the close (X) button. Overlay dismisses; filter selections
        remain applied to the Studio tab."""
        self.tap_by_id(self.BUTTON_CLOSE_ID)
        self.wait_seconds(1)
        log.info("Closed filter overlay")

    # --- Section accordions ---

    def _section_text_elements(self):
        """All `text` elements inside the filter list. Includes BOTH
        section headers (LENGTH, LEVEL, etc.) AND option values (5 MIN,
        BEGINNER, etc.)."""
        try:
            container = self.find_by_id(self.LIST_ID)
        except Exception:
            return []
        return container.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.SECTION_TEXT_ID}"
        )

    def _section_header_names(self):
        """Return the names of section headers currently visible.
        Filtered by KNOWN_SECTIONS to distinguish from option text."""
        visible = []
        for el in self._section_text_elements():
            text = (el.get_attribute("text") or "").strip()
            if text in self.KNOWN_SECTIONS:
                visible.append(text)
        return visible

    def is_section_visible(self, section_name):
        """Check if a section header is currently visible (without scrolling)."""
        return section_name.upper() in [
            s.upper() for s in self._section_header_names()
        ]

    def tap_section(self, section_name):
        """Tap a section header to expand or collapse it. Sections start
        collapsed; tapping expands them; tapping again collapses them.

        Auto-scrolls the list if the section isn't currently visible."""
        target = section_name.strip().upper()

        if not self.is_section_visible(target):
            self.scroll_to_section(target)

        for el in self._section_text_elements():
            text = (el.get_attribute("text") or "").strip().upper()
            if text == target:
                el.click()
                self.wait_seconds(1)
                log.info(f"Tapped section: {section_name}")
                return
        raise ValueError(
            f"Section '{section_name}' not found. Visible sections: "
            f"{self._section_header_names()}"
        )

    def expand_section(self, section_name):
        """Alias for tap_section() with semantic 'open this section' intent."""
        self.tap_section(section_name)

    # --- Selection state (via text_number badge on section headers) ---

    def get_section_selection_count(self, section_name):
        """Return the number of options selected in a given section.

        Reads the `text_number` element that appears next to the section
        header when one or more options are selected. Returns 0 if no
        text_number is found near the section (i.e. nothing selected).

        Walks the filter list in document order. After encountering the
        target section header, looks for a text_number BEFORE the next
        section header. If a text_number appears in that window, returns
        its value as int. Otherwise returns 0.

        IMPORTANT: This is the only programmatic way to verify selection
        count from within the overlay — individual option items show no
        selection marker in the element tree."""
        target = section_name.strip().upper()
        if not self.is_section_visible(target):
            self.scroll_to_section(target)

        try:
            container = self.find_by_id(self.LIST_ID)
        except Exception:
            return 0

        # Get all text + text_number elements in document order.
        # NB: UiAutomator2's XPath supports `or` predicates in practice
        # — confirmed working on Studio 2026-04-27. If it stops working
        # on a future Android/Appium version, fall back to fetching each
        # id separately and merging by document position.
        try:
            all_els = container.find_elements(
                AppiumBy.XPATH,
                f".//*[@resource-id='{self.APP_PACKAGE}:id/{self.SECTION_TEXT_ID}' or "
                f"@resource-id='{self.APP_PACKAGE}:id/{self.SECTION_NUMBER_ID}']"
            )
        except Exception as e:
            log.info(f"XPath query failed: {e}")
            return 0

        found_target = False
        for el in all_els:
            rid = el.get_attribute("resource-id") or ""
            text = (el.get_attribute("text") or "").strip()

            if rid.endswith(f":id/{self.SECTION_TEXT_ID}"):
                # This is a `text` element — could be a section header
                # OR an option value
                if text == target:
                    # Found our target section
                    found_target = True
                    continue
                if found_target and text in self.KNOWN_SECTIONS:
                    # Hit the NEXT section header before finding a
                    # text_number for the target → no badge → 0 selections
                    return 0
                # Otherwise it's either a non-target section header
                # we're walking past, or an option value within some
                # section. Either way: keep walking.
                continue

            elif rid.endswith(f":id/{self.SECTION_NUMBER_ID}"):
                # This is a text_number badge
                if found_target:
                    # The first text_number after our target section
                    # is the target's badge
                    try:
                        return int(text)
                    except (ValueError, TypeError):
                        return 0
                # Otherwise this badge belongs to a section we walked
                # past — ignore it
                continue

        # Walked off the end without hitting a next section or finding
        # a badge. If we found the target, that means it's the LAST
        # section and has no badge — return 0. If we never found the
        # target, the section isn't visible — return 0 too.
        return 0

    def is_anything_selected_in_section(self, section_name):
        """True if at least one option is selected in the named section."""
        return self.get_section_selection_count(section_name) > 0

    def get_total_selection_count(self):
        """Sum of selections across all sections."""
        return sum(
            self.get_section_selection_count(s) for s in self.KNOWN_SECTIONS
        )

    # --- Filter option selection ---

    def tap_option(self, option_text):
        """Tap a filter option by its text (e.g. '30 MIN', 'BEGINNER',
        'CARDIO', 'KATE S').

        Caller is responsible for first expanding the right section so
        the option is visible. Use tap_filter() for a one-call helper
        that expands + taps."""
        target = option_text.strip().upper()

        if not self._is_option_visible(target):
            self.scroll_to_option(target)

        for el in self._section_text_elements():
            text = (el.get_attribute("text") or "").strip().upper()
            if text == target:
                el.click()
                self.wait_seconds(1)
                log.info(f"Tapped filter option: {option_text}")
                return
        raise ValueError(
            f"Filter option '{option_text}' not found. Make sure the "
            f"section containing this option is expanded first."
        )

    def tap_filter(self, section_name, option_text):
        """Convenience: expand a section if needed, then tap an option.

        Example: filter.tap_filter('LENGTH', '30 MIN')"""
        target_option = option_text.strip().upper()
        if not self._is_option_visible(target_option):
            self.expand_section(section_name)
        self.tap_option(option_text)

    def _is_option_visible(self, option_text):
        """Internal: check if an option's text is currently visible
        (without scrolling). Filters out section header text."""
        target = option_text.strip().upper()
        for el in self._section_text_elements():
            text = (el.get_attribute("text") or "").strip().upper()
            if text == target and text not in self.KNOWN_SECTIONS:
                return True
        return False

    # --- Scrolling within the filter list ---

    def scroll_list_down(self):
        """Scroll the filter list down."""
        try:
            list_el = self.find_by_id(self.LIST_ID)
            rect = list_el.rect
            self.driver.swipe(
                start_x=rect["x"] + rect["width"] // 2,
                start_y=rect["y"] + int(rect["height"] * 0.7),
                end_x=rect["x"] + rect["width"] // 2,
                end_y=rect["y"] + int(rect["height"] * 0.3),
                duration=400,
            )
            self.wait_seconds(1)
        except Exception as e:
            log.info(f"Could not scroll filter list down: {e}")

    def scroll_list_up(self):
        """Scroll the filter list up."""
        try:
            list_el = self.find_by_id(self.LIST_ID)
            rect = list_el.rect
            self.driver.swipe(
                start_x=rect["x"] + rect["width"] // 2,
                start_y=rect["y"] + int(rect["height"] * 0.3),
                end_x=rect["x"] + rect["width"] // 2,
                end_y=rect["y"] + int(rect["height"] * 0.7),
                duration=400,
            )
            self.wait_seconds(1)
        except Exception as e:
            log.info(f"Could not scroll filter list up: {e}")

    def scroll_to_section(self, section_name, max_scrolls=5):
        """Scroll the list until the named section header is visible."""
        target = section_name.strip().upper()
        for _ in range(max_scrolls):
            if self.is_section_visible(target):
                return True
            self.scroll_list_down()
        for _ in range(max_scrolls):
            if self.is_section_visible(target):
                return True
            self.scroll_list_up()
        return self.is_section_visible(target)

    def scroll_to_option(self, option_text, max_scrolls=10):
        """Scroll the list until an option's text is visible."""
        target = option_text.strip().upper()
        for _ in range(max_scrolls):
            if self._is_option_visible(target):
                return True
            self.scroll_list_down()
        for _ in range(max_scrolls):
            if self._is_option_visible(target):
                return True
            self.scroll_list_up()
        return self._is_option_visible(target)