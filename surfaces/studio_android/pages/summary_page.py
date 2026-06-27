"""SummaryPage — Studio's post-class summary screen.

Reached after submitting the rating screen (or possibly directly after
ending a class — depends on app behavior). Shows:
  - Top header bar (close, bookmark, music, utility)
  - YOUR FORME WEEK section with day-of-week checkmarks
  - The class just completed (title + info line)
  - layout_stats with workout statistics (e.g. ACTIVE TIME)
  - fragment_container with conditional HRM connect prompt
    (shown when no HRM was connected during the class)

Layout:

  button_close                    ← close summary, return to Studio/Home
  button_bookmark                 ← bookmark the class just completed
  apple_music_button (×2)
  utility_button

  text_header | "YOUR FORME WEEK"
  days_checkmarks
    [image + text | M]            ← day initial (M T W T F S S)
    [image + text | T]            ← image is checked/unchecked indicator
    ...

  text_title | "YOGA SCULPT: FULL BODY"        ← class title
  text_info  | "30 Min • Intermediate • Yoga • Johanna Q"

  layout_stats                    ← workout statistics
    label_active_time | "ACTIVE TIME"
    text_active_time  | "01:57"
    [more stats may appear when HRM is connected:
     calories burned, avg heart rate, peak heart rate, etc.]

  fragment_container              ← conditional content
    [if no HRM was connected:]
      image_hrm
      text | "Connect a HR monitor to understand how level of effort..."
      button_connect | "CONNECT NOW"
      image_chart
    [if HRM was connected:]
      Probably shows HR chart / zones — needs separate dump to confirm

NOTE on stats:
  - When HRM is connected, layout_stats likely contains additional
    elements: calories total, avg HR, peak HR, time-in-zones. Need a
    follow-up dump from a class run with HRM connected to confirm
    element ids.
  - text_active_time format is "MM:SS"

NOTE on HRM connect prompt:
  - The prompt at the bottom is conditional — shown only when no HRM
    was connected during the class. Tests that depend on this should
    either (a) ensure no HRM is paired before running, OR (b) handle
    both states (is_hrm_prompt_shown())."""
from surfaces.studio_android.pages.base import StudioBasePage, log
from selenium.webdriver.support import expected_conditions as EC


class SummaryPage(StudioBasePage):
    # --- Element IDs (confirmed from dump on 2026-04-27) ---

    # Top header bar
    BUTTON_CLOSE_ID = "button_close"
    BUTTON_BOOKMARK_ID = "button_bookmark"
    APPLE_MUSIC_BUTTON_ID = "apple_music_button"
    UTILITY_BUTTON_ID = "utility_button"

    # Week tracker
    TEXT_HEADER_ID = "text_header"             # "YOUR FORME WEEK"
    DAYS_CHECKMARKS_ID = "days_checkmarks"

    # Class info
    TEXT_TITLE_ID = "text_title"               # class just completed
    TEXT_INFO_ID = "text_info"                 # "30 Min • Intermediate • ..."

    # Stats block
    LAYOUT_STATS_ID = "layout_stats"
    LABEL_ACTIVE_TIME_ID = "label_active_time"
    TEXT_ACTIVE_TIME_ID = "text_active_time"

    # Conditional content (HRM prompt when no HRM was connected)
    FRAGMENT_CONTAINER_ID = "fragment_container"
    IMAGE_HRM_ID = "image_hrm"
    BUTTON_CONNECT_ID = "button_connect"        # "CONNECT NOW"
    IMAGE_CHART_ID = "image_chart"

    # --- Screen detection ---

    def is_loaded(self, timeout=5):
        """Non-blocking check: are we on the summary screen?
        Anchored on text_header (YOUR FORME WEEK) which is always
        present on summary."""
        return self.is_visible(self.TEXT_HEADER_ID, timeout=timeout)

    def wait_for_summary(self, timeout=15):
        """Block until summary screen renders. Long timeout because
        rating submission may take a moment to advance."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.TEXT_HEADER_ID)
        ))
        log.info("Summary screen loaded")

    # --- Reading class info ---

    def get_class_title(self):
        """Title of the class just completed (e.g. 'YOGA SCULPT: FULL BODY')."""
        return self.get_text(self.TEXT_TITLE_ID)

    def get_class_info(self):
        """Class info line (e.g. '30 Min • Intermediate • Yoga • Johanna Q')."""
        return self.get_text(self.TEXT_INFO_ID)

    def _info_parts(self):
        """Split text_info on bullets."""
        info = self.get_class_info() or ""
        return [p.strip() for p in info.split("•") if p.strip()]

    def get_class_duration(self):
        """Class duration from text_info (e.g. '30 Min')."""
        parts = self._info_parts()
        return parts[0] if len(parts) >= 1 else None

    def get_class_trainer(self):
        """Trainer name from text_info (e.g. 'Johanna Q'). Returns
        None for classes without an attributed trainer."""
        parts = self._info_parts()
        return parts[3] if len(parts) >= 4 else None

    # --- Reading stats ---

    def get_active_time(self):
        """Active time spent in the class (e.g. '01:57'). Returns the
        raw string."""
        return self.get_text(self.TEXT_ACTIVE_TIME_ID)

    def get_active_time_seconds(self):
        """Parse active time into total seconds (MM:SS format).
        Returns int or None if can't parse."""
        raw = (self.get_active_time() or "").strip()
        try:
            parts = raw.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return (int(parts[0]) * 3600 + int(parts[1]) * 60
                        + int(parts[2]))
        except (ValueError, IndexError):
            pass
        return None

    # --- HRM connect prompt (conditional) ---

    def is_hrm_prompt_shown(self):
        """True if the 'Connect a HR monitor...' prompt is visible at
        the bottom of the summary. Shown only when no HRM was connected
        during the class."""
        return self.is_visible(self.BUTTON_CONNECT_ID, timeout=2)

    def tap_connect_hrm(self):
        """Tap CONNECT NOW on the HRM prompt. Likely opens HRM pairing
        flow — not yet validated."""
        self.tap_by_id(self.BUTTON_CONNECT_ID)
        self.wait_seconds(2)
        log.info("Tapped CONNECT NOW (HRM prompt on summary)")

    # --- Week tracker ---

    def has_week_tracker(self):
        """True if the YOUR FORME WEEK tracker is visible."""
        return self.is_visible(self.DAYS_CHECKMARKS_ID, timeout=2)

    # --- Actions ---

    def tap_close(self):
        """Dismiss the summary — typically returns to Studio tab or
        Home depending on app state."""
        self.tap_by_id(self.BUTTON_CLOSE_ID)
        self.wait_seconds(2)
        log.info("Closed summary screen")

    # Backwards-compat alias matching member conventions
    def dismiss(self):
        """Alias for tap_close()."""
        self.tap_close()

    def tap_bookmark(self):
        """Bookmark the class just completed from the summary screen."""
        self.tap_by_id(self.BUTTON_BOOKMARK_ID)
        self.wait_seconds(1)
        log.info("Tapped bookmark on summary")

    def tap_apple_music(self):
        """Tap Apple Music control."""
        self.tap_by_id(self.APPLE_MUSIC_BUTTON_ID)