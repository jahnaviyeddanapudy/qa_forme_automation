"""PlayerPage — Studio's in-class video player (all variants).

A single PlayerPage handles two top-level player variants:

  VOD VARIANT
    Plain video playback. Header shows time/calories/HR. Tapping the
    screen wakes basic controls (play/pause, +/-15s, end session,
    settings). No move tracker, no block preview.

  GUIDED-WORKOUT VARIANT (any non-VOD: CPS, Planned Session/Workout,
                          potentially Programs)
    Same header. PLUS a move-by-move workout-tracker UI. The class is
    organized into BLOCKS (e.g. Warm Up, Conditioning, Cooldown), each
    containing one or more MOVES. The player cycles through these
    states per move:

      - BLOCK PREVIEW: between blocks. Shows the upcoming block name,
        multiplier, and list of moves with their reps/durations.
        (fragment_block_preview)

      - GET READY: brief countdown before each move starts.
        (fragment_movement_tracker with text_get_ready)

      - REP-BASED MOVE: actively performing a rep-counted move. Shows
        rep counter and a MARK COMPLETE button. User taps MARK COMPLETE
        to advance.
        (fragment_movement_tracker with label_reps_performed,
         button_complete_movement)
        Strength moves additionally show layout_weight (e.g. "5 LBS").

      - TIMED MOVE: actively performing a duration-based move (e.g.
        hold this stretch for 45 seconds). Shows movement_progress_bar
        and text_time countdown. NO button — auto-advances when timer
        expires.
        (fragment_movement_tracker with movement_progress_bar +
         text_time)

      - MOVE COMPLETE: brief checkmark state when a timed move's timer
        expires. Lasts ~1s before transitioning to next GET READY.
        (fragment_movement_tracker with image_check)

CRITICAL — Rep-based and timed moves can BOTH appear within a single
class. The move type is determined per-MOVE, not per-CLASS. A single
30-minute class might have:
  - Warm Up block with timed moves (:30, :45 each)
  - Strength block with rep-based moves (5 reps, 10 reps each)
  - Cooldown block with timed moves again

The player switches its UI between rep-based and timed presentation
mid-class. Tests should detect the CURRENT move's state (via
get_workout_state()) rather than assume one type for the whole class.

Class-type does NOT determine move-type:
  - CPS classes can have either or both
  - Planned Session / Workout classes can have either or both
  - Programs likely the same

Layout of all elements observed across variants:

  player_class                        ← root container
    exo_ad_overlay
    exo_overlay
    exo_content_frame                 ← actual video
    exo_subtitles

  fragment_header                     ← always present, top stats bar
    text_time | "11:21 AM"            ← wall-clock time (NB: id conflict
                                         with text_time inside movement
                                         tracker — scope queries to parent)
    text_class_time | "00:13"         ← REMAINING class time, counts down
    text_calories | "0"
    text_heart_rate | "---"
    apple_music_button (×2)
    button_settings

  fragment_controls                   ← VOD: appears on tap, auto-hides
    button_play_pause
    button_forward_15
    button_rewind_15
    button_end_class | "END SESSION"

  fragment_control_center             ← opens when button_settings tapped
    layout_volume_controls
      seek_bar_volume + seek_bar (0-100)
    layout_outputs
      switch_layout + textLeft="STUDIO" + textRight="BLUETOOTH"

  ----- guided-workout additions below (any non-VOD) -----

  fragment_block_preview              ← BLOCK PREVIEW state
    progress | "94550.0"
    label_coming_up | "COMING UP"
    [SKIP button — text "SKIP", NO resource-id]
    label_block | "Warm Up"
    label_multiplier | "1x"
    divider
    layout_moves_scroll_content
      text_move + text_reps × N
        (reps may be numeric '5' for rep-based, or duration ':30' for
         timed — VARIES PER MOVE within the same block)

  fragment_movement_tracker           ← GET READY / MOVE / COMPLETE states
    [GET READY:]
      get_ready_progress_bar | "12116.0"
      text_get_ready | "GET READY"
      text_name | "<next move name>"
      toggle_demo | "DEMO"

    [REP-BASED MOVE — user controls advancement:]
      label_reps_performed | "5"
      toggle_demo | "DEMO"
      label_reps_divider
      label_reps_title | "REPS"
      text_name | "<current move name>"
      (button_complete_movement appears outside fragment_movement_tracker
       but visible during this state)

    [TIMED MOVE — auto-advances:]
      movement_progress_bar | "1562.0"
      text_time | "44"                  ← seconds REMAINING (id conflict
                                           with header's wall-clock!)
      text_name | "<current move name>"
      toggle_demo | "DEMO"

    [MOVE COMPLETE — brief, ~1s:]
      movement_progress_bar | "98131.0"
      image_check                       ← green checkmark
      text_name | "<just-completed move>"
      toggle_demo | "DEMO"

  button_complete_movement | "MARK COMPLETE"   ← REP-BASED MOVE state only

  layout_weight                       ← rep-based STRENGTH moves only
    text_weight_value | "5"            (when current move uses weights —
    label_lbs | "LBS"                   per-move, not per-class)

  fragment_blocks                     ← block timeline / position dots
    container (many unlabeled children)

NOTE on text_time ID conflict:
  Both the wall-clock time in fragment_header AND the move countdown
  in fragment_movement_tracker use resource-id 'text_time'. To get the
  right value, scope queries to the right parent. We provide:
    get_wall_clock_time()         → header's text_time
    get_move_time_remaining()     → tracker's text_time

NOTE on text_class_time:
  REMAINING class time, counts down. For elapsed-time tests, subtract
  from original class duration.

NOTE on missing resource-ids:
  - SKIP button on block preview has NO resource-id. Addressed by text
    via XPath. Worth flagging to dev.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class PlayerPage(StudioBasePage):
    # =========================================================
    # ELEMENT IDS
    # =========================================================

    # --- Player root + ExoPlayer internals ---
    PLAYER_CLASS_ID = "player_class"
    EXO_CONTENT_FRAME_ID = "exo_content_frame"
    EXO_OVERLAY_ID = "exo_overlay"
    EXO_AD_OVERLAY_ID = "exo_ad_overlay"
    EXO_SUBTITLES_ID = "exo_subtitles"

    # --- Header (always visible) ---
    FRAGMENT_HEADER_ID = "fragment_header"
    TEXT_TIME_ID = "text_time"               # both wall-clock AND move countdown
    TEXT_CLASS_TIME_ID = "text_class_time"
    TEXT_CALORIES_ID = "text_calories"
    TEXT_HEART_RATE_ID = "text_heart_rate"
    APPLE_MUSIC_BUTTON_ID = "apple_music_button"
    BUTTON_SETTINGS_ID = "button_settings"

    # --- VOD playback controls (auto-hide; tap player to wake) ---
    FRAGMENT_CONTROLS_ID = "fragment_controls"
    BUTTON_PLAY_PAUSE_ID = "button_play_pause"
    BUTTON_FORWARD_15_ID = "button_forward_15"
    BUTTON_REWIND_15_ID = "button_rewind_15"
    BUTTON_END_CLASS_ID = "button_end_class"

    # --- Settings / Audio panel ---
    FRAGMENT_CONTROL_CENTER_ID = "fragment_control_center"
    LAYOUT_VOLUME_CONTROLS_ID = "layout_volume_controls"
    SEEK_BAR_VOLUME_ID = "seek_bar_volume"
    SEEK_BAR_ID = "seek_bar"
    LAYOUT_OUTPUTS_ID = "layout_outputs"
    SWITCH_OUTPUTS_ID = "switch_outputs"

    # --- Guided-workout: Block preview state ---
    FRAGMENT_BLOCK_PREVIEW_ID = "fragment_block_preview"
    PROGRESS_ID = "progress"
    LABEL_COMING_UP_ID = "label_coming_up"
    LABEL_BLOCK_ID = "label_block"
    LABEL_MULTIPLIER_ID = "label_multiplier"
    LAYOUT_MOVES_SCROLL_CONTENT_ID = "layout_moves_scroll_content"
    TEXT_MOVE_ID = "text_move"
    TEXT_REPS_ID = "text_reps"

    # --- Guided-workout: Movement tracker (GET READY + MOVE + COMPLETE) ---
    FRAGMENT_MOVEMENT_TRACKER_ID = "fragment_movement_tracker"
    LABEL_REPS_PERFORMED_ID = "label_reps_performed"
    LABEL_REPS_TITLE_ID = "label_reps_title"
    TOGGLE_DEMO_ID = "toggle_demo"
    TEXT_NAME_ID = "text_name"
    GET_READY_PROGRESS_BAR_ID = "get_ready_progress_bar"
    TEXT_GET_READY_ID = "text_get_ready"
    BUTTON_COMPLETE_MOVEMENT_ID = "button_complete_movement"

    # --- Guided-workout: timed-move tracker ---
    MOVEMENT_PROGRESS_BAR_ID = "movement_progress_bar"
    IMAGE_CHECK_ID = "image_check"

    # --- Guided-workout: Weight tracker (rep-based strength moves only) ---
    LAYOUT_WEIGHT_ID = "layout_weight"
    TEXT_WEIGHT_VALUE_ID = "text_weight_value"
    LABEL_LBS_ID = "label_lbs"

    # --- Guided-workout: Block timeline ---
    FRAGMENT_BLOCKS_ID = "fragment_blocks"

    # =========================================================
    # SCREEN DETECTION
    # =========================================================

    def is_loaded(self, timeout=10):
        """Non-blocking check: is the player visible?"""
        return self.is_visible(self.PLAYER_CLASS_ID, timeout=timeout)

    def wait_for_player(self, timeout=20):
        """Block until player loads. Long timeout because video loading
        can take a while."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.PLAYER_CLASS_ID)
        ))
        log.info("Player loaded")

    def get_player_variant(self):
        """Identify which top-level player variant is currently
        rendering, based on whether any guided-workout UI is present.

        Returns one of:
          - 'vod'             — basic video player only
          - 'guided_workout'  — guided-workout UI present (block preview
                                or movement tracker visible). Covers all
                                non-VOD class types (CPS, Workout/
                                Planned Session, Programs).

        For per-move state within a guided-workout class, use
        get_workout_state() — the move type changes throughout a class."""
        if (self.is_visible(self.FRAGMENT_BLOCK_PREVIEW_ID, timeout=1)
                or self.is_visible(self.FRAGMENT_MOVEMENT_TRACKER_ID,
                                   timeout=1)):
            return "guided_workout"
        return "vod"

    def is_current_move_weighted(self):
        """True if the CURRENT move shows the weight tracker (e.g.
        '5 LBS'). This means the current move is a weighted strength
        move. Other moves in the same class may or may not be weighted —
        this changes per-move.

        Was previously named is_strength_workout() — renamed because
        the original name implied per-class behavior, but layout_weight
        is per-move."""
        return self.is_visible(self.LAYOUT_WEIGHT_ID, timeout=1)

    # Back-compat alias — keep working but behavior is per-move
    def is_strength_workout(self):
        """DEPRECATED — use is_current_move_weighted(). Kept as alias
        because the original method name implied per-class semantics
        but the underlying check (layout_weight visibility) is
        per-move. Both rep-based and timed moves can appear in any
        guided-workout class."""
        return self.is_current_move_weighted()

    # =========================================================
    # HEADER READINGS (all variants)
    # =========================================================

    def get_wall_clock_time(self):
        """Wall-clock time displayed in the player HEADER (e.g. '10:42 AM').
        Scoped to fragment_header to disambiguate from movement tracker's
        text_time (which shows move countdown seconds)."""
        try:
            header = self.find_by_id(self.FRAGMENT_HEADER_ID)
            time_el = header.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_TIME_ID}"
            )
            return time_el.get_attribute("text") or ""
        except Exception:
            # Fallback to first match if scoping fails
            return self.get_text(self.TEXT_TIME_ID)

    def get_class_time(self):
        """Class time string (e.g. '32:38'). REMAINING time, counts
        down. Returns the raw string."""
        return self.get_text(self.TEXT_CLASS_TIME_ID)

    def get_class_time_seconds(self):
        """Parse text_class_time into total seconds (MM:SS or H:MM:SS).
        Returns int or None if can't parse."""
        raw = (self.get_class_time() or "").strip()
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

    def get_calories(self):
        """Current calories burned (string)."""
        return self.get_text(self.TEXT_CALORIES_ID)

    def get_calories_visible(self):
        """True if the calories element is visible. Per member behavior,
        calories may not be in the DOM until first value arrives."""
        return self.is_visible(self.TEXT_CALORIES_ID, timeout=2)

    def get_heart_rate(self):
        """Heart rate display: numeric (e.g. '82') if HRM connected,
        '---' if not."""
        return self.get_text(self.TEXT_HEART_RATE_ID)

    def is_hrm_connected(self):
        """True if a heart-rate value is being reported (numeric).
        False if no HRM ('---' shown)."""
        hr = (self.get_heart_rate() or "").strip()
        if not hr or hr == "---":
            return False
        try:
            int(hr)
            return True
        except ValueError:
            return False

    # =========================================================
    # VOD CONTROLS (require controls overlay to be visible)
    # =========================================================

    def tap_screen(self):
        """Tap the player surface to wake up the playback controls.
        Controls auto-hide after ~10s of inactivity."""
        try:
            el = self.find_by_id(self.PLAYER_CLASS_ID)
            el.click()
            self.wait_seconds(1)
            log.info("Tapped player to show controls")
        except Exception as e:
            log.info(f"Could not tap player to show controls: {e}")

    def tap_to_show_controls(self):
        """Alias for tap_screen() — back-compat with member conventions."""
        self.tap_screen()

    def are_controls_visible(self, timeout=1):
        """True if the controls overlay is currently visible."""
        return self.is_visible(self.FRAGMENT_CONTROLS_ID, timeout=timeout)

    def tap_play_pause(self):
        """Toggle play/pause. Auto-wakes controls first."""
        if not self.are_controls_visible():
            self.tap_screen()
        self.tap_by_id(self.BUTTON_PLAY_PAUSE_ID)
        self.wait_seconds(1)
        log.info("Tapped play/pause")

    def tap_pause(self):
        """Alias for tap_play_pause when class is currently playing."""
        self.tap_play_pause()

    def tap_play(self):
        """Alias for tap_play_pause when class is currently paused."""
        self.tap_play_pause()

    def tap_fast_forward(self):
        """Skip forward 15s. Auto-wakes controls first."""
        if not self.are_controls_visible():
            self.tap_screen()
        self.tap_by_id(self.BUTTON_FORWARD_15_ID)
        self.wait_seconds(1)
        log.info("Tapped forward 15s")

    def tap_rewind(self):
        """Skip backward 15s. Auto-wakes controls first."""
        if not self.are_controls_visible():
            self.tap_screen()
        self.tap_by_id(self.BUTTON_REWIND_15_ID)
        self.wait_seconds(1)
        log.info("Tapped rewind 15s")

    def tap_end_session(self):
        """End the class. Advances to RatingPage if class progressed
        far enough, or directly to SummaryPage if ended very early.
        Auto-wakes controls first."""
        if not self.are_controls_visible():
            self.tap_screen()
        self.tap_by_id(self.BUTTON_END_CLASS_ID)
        self.wait_seconds(2)
        log.info("Tapped END SESSION")

    # =========================================================
    # SETTINGS / AUDIO PANEL
    # =========================================================

    def tap_settings(self):
        """Tap the gear icon. Opens fragment_control_center with
        volume + Studio/Bluetooth output toggle."""
        if not self.are_controls_visible():
            self.tap_screen()
        self.tap_by_id(self.BUTTON_SETTINGS_ID)
        self.wait_seconds(1)
        log.info("Tapped settings (opened control center)")

    def is_control_center_open(self, timeout=2):
        """True if the settings/audio panel is currently visible."""
        return self.is_visible(self.FRAGMENT_CONTROL_CENTER_ID,
                               timeout=timeout)

    def get_volume(self):
        """Read the volume seek bar value (e.g. 100.0). Returns float
        or None if control center isn't open."""
        if not self.is_control_center_open():
            return None
        try:
            el = self.find_by_id(self.SEEK_BAR_ID)
            raw = (el.get_attribute("text") or "").strip()
            return float(raw)
        except (ValueError, TypeError):
            return None
        except Exception as e:
            log.info(f"Could not read volume: {e}")
            return None

    def tap_apple_music(self):
        """Tap Apple Music control."""
        self.tap_by_id(self.APPLE_MUSIC_BUTTON_ID)

    # =========================================================
    # GUIDED-WORKOUT — PER-MOVE STATE DETECTION
    # =========================================================

    def is_in_block_preview(self, timeout=1):
        """True if currently showing a 'COMING UP' block preview between
        blocks of a guided-workout class."""
        return self.is_visible(self.FRAGMENT_BLOCK_PREVIEW_ID,
                               timeout=timeout)

    def is_in_get_ready(self, timeout=1):
        """True if currently in 'GET READY' state — countdown to next
        move starts."""
        return self.is_visible(self.TEXT_GET_READY_ID, timeout=timeout)

    def is_in_rep_based_move(self, timeout=1):
        """True if the CURRENT move is rep-based — MARK COMPLETE button
        is visible. Note: a rep-based move can appear in ANY non-VOD
        class type. Don't assume per-class."""
        return self.is_visible(self.BUTTON_COMPLETE_MOVEMENT_ID,
                               timeout=timeout)

    def is_in_timed_move(self, timeout=1):
        """True if the CURRENT move is duration-based —
        movement_progress_bar inside fragment_movement_tracker with
        text_time present (countdown). Excludes the brief move-complete
        state where image_check replaces text_time.

        Note: a timed move can appear in ANY non-VOD class type. Don't
        assume per-class."""
        if not self.is_visible(self.FRAGMENT_MOVEMENT_TRACKER_ID,
                               timeout=timeout):
            return False
        if not self.is_visible(self.MOVEMENT_PROGRESS_BAR_ID, timeout=1):
            return False
        try:
            tracker = self.find_by_id(self.FRAGMENT_MOVEMENT_TRACKER_ID)
            tracker.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_TIME_ID}"
            )
            return True
        except Exception:
            return False

    def is_in_movement(self, timeout=1):
        """True if currently performing ANY move — covers both rep-based
        and timed."""
        return (self.is_in_rep_based_move(timeout=timeout)
                or self.is_in_timed_move(timeout=timeout))

    def is_in_move_complete(self, timeout=1):
        """True if currently in the brief MOVE COMPLETE state — image_check
        is shown when a timed move's timer expires. Transient — usually
        only visible for ~1 second before advancing to next GET READY
        or block preview."""
        if not self.is_visible(self.FRAGMENT_MOVEMENT_TRACKER_ID,
                               timeout=timeout):
            return False
        return self.is_visible(self.IMAGE_CHECK_ID, timeout=1)

    def get_workout_state(self):
        """Return the current per-move player state as a string:
        'block_preview', 'get_ready', 'rep_based_move', 'timed_move',
        'move_complete', or 'unknown'.

        State is per-MOVE, not per-class. The player switches between
        rep_based_move and timed_move states throughout a single class
        based on each move's type."""
        if self.is_in_block_preview():
            return "block_preview"
        if self.is_in_get_ready():
            return "get_ready"
        if self.is_in_rep_based_move():
            return "rep_based_move"
        if self.is_in_move_complete():
            return "move_complete"
        if self.is_in_timed_move():
            return "timed_move"
        return "unknown"

    # =========================================================
    # GUIDED-WORKOUT — BLOCK PREVIEW
    # =========================================================

    def get_upcoming_block_name(self):
        """In block_preview state, the name of the upcoming block
        (e.g. 'Warm Up', 'Conditioning', 'Foam Roll'). Returns None
        if not in block preview."""
        if not self.is_in_block_preview():
            return None
        try:
            return self.get_text(self.LABEL_BLOCK_ID)
        except Exception:
            return None

    def get_upcoming_block_multiplier(self):
        """How many times the upcoming block repeats (e.g. '1x', '2x').
        Returns None if not in block preview."""
        if not self.is_in_block_preview():
            return None
        try:
            return self.get_text(self.LABEL_MULTIPLIER_ID)
        except Exception:
            return None

    def get_upcoming_moves(self):
        """List of moves in the upcoming block. Returns list of dicts:
        [{'name': '90/90 Hip Drill', 'reps': '5'}, ...].

        Reps may be numeric ('5') for rep-based or duration (':30',
        ':45') for time-based — moves can mix within a single block.
        Returns empty list if not in block preview."""
        if not self.is_in_block_preview():
            return []
        moves = []
        move_els = self.find_all_by_id(self.TEXT_MOVE_ID)
        rep_els = self.find_all_by_id(self.TEXT_REPS_ID)
        for i, m in enumerate(move_els):
            name = (m.get_attribute("text") or "").strip()
            reps = ""
            if i < len(rep_els):
                reps = (rep_els[i].get_attribute("text") or "").strip()
            moves.append({"name": name, "reps": reps})
        return moves

    def tap_skip_preview(self):
        """Tap the SKIP button on the block preview to advance immediately
        to the workout. SKIP has NO resource-id — addressed by text via
        XPath. Worth flagging to dev to add an id (e.g. button_skip_preview).

        Raises if not in block preview state."""
        if not self.is_in_block_preview():
            raise RuntimeError(
                "tap_skip_preview() called but not in block preview state"
            )
        try:
            el = self.driver.find_element(
                AppiumBy.XPATH,
                "//*[@text='SKIP' and @clickable='true']"
            )
            el.click()
            self.wait_seconds(1)
            log.info("Tapped SKIP on block preview")
        except Exception as e:
            log.info(f"Could not tap SKIP: {e}")
            raise

    # =========================================================
    # GUIDED-WORKOUT — MOVEMENT TRACKER
    # =========================================================

    def get_current_move_name(self):
        """Name of the current/next move from the movement tracker
        (text_name in fragment_movement_tracker). Works in get_ready,
        rep_based_move, timed_move, and move_complete states. Returns
        None if not in any of these."""
        if not self.is_visible(self.FRAGMENT_MOVEMENT_TRACKER_ID,
                               timeout=1):
            return None
        try:
            tracker = self.find_by_id(self.FRAGMENT_MOVEMENT_TRACKER_ID)
            name_el = tracker.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_NAME_ID}"
            )
            return name_el.get_attribute("text") or ""
        except Exception:
            return None

    def get_reps_performed(self):
        """In rep_based_move state, the number of reps performed for the
        current move (e.g. '5'). Returns None if current move isn't
        rep-based.

        Returns string since field is text — caller can parse to int
        if needed."""
        if not self.is_in_rep_based_move():
            return None
        try:
            return self.get_text(self.LABEL_REPS_PERFORMED_ID)
        except Exception:
            return None

    def get_move_time_remaining(self):
        """In timed_move state, the seconds remaining for the current
        move (e.g. '44'). Scoped to fragment_movement_tracker to avoid
        the wall-clock text_time in fragment_header.

        Returns string since field is text. Returns None if current
        move isn't timed."""
        if not self.is_in_timed_move():
            return None
        try:
            tracker = self.find_by_id(self.FRAGMENT_MOVEMENT_TRACKER_ID)
            time_el = tracker.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_TIME_ID}"
            )
            return time_el.get_attribute("text") or ""
        except Exception:
            return None

    def get_move_time_remaining_seconds(self):
        """Parse get_move_time_remaining() into int seconds. Returns
        None if not in timed-move state or can't parse."""
        raw = self.get_move_time_remaining()
        if raw is None:
            return None
        try:
            return int(raw.strip())
        except (ValueError, AttributeError):
            return None

    def tap_demo_toggle(self):
        """Toggle the DEMO video for the current move (shows/hides
        instructional clip). Available in get_ready, rep_based_move,
        timed_move, and move_complete states."""
        if not self.is_visible(self.TOGGLE_DEMO_ID, timeout=2):
            raise RuntimeError(
                "tap_demo_toggle() called but DEMO toggle not visible"
            )
        self.tap_by_id(self.TOGGLE_DEMO_ID)
        self.wait_seconds(1)
        log.info("Tapped DEMO toggle")

    def tap_mark_complete(self):
        """Tap MARK COMPLETE to finish current move and advance to next.
        Only available when the current move is rep-based. Timed moves
        auto-advance — there's no MARK COMPLETE button to tap.

        Raises if current move isn't rep-based."""
        if not self.is_in_rep_based_move():
            raise RuntimeError(
                "tap_mark_complete() called but current move isn't "
                "rep-based. Note: timed moves auto-advance — no MARK "
                "COMPLETE button to tap."
            )
        self.tap_by_id(self.BUTTON_COMPLETE_MOVEMENT_ID)
        self.wait_seconds(1)
        log.info("Tapped MARK COMPLETE")

    # =========================================================
    # GUIDED-WORKOUT — WEIGHT TRACKER (rep-based strength moves only)
    # =========================================================

    def get_weight_value(self):
        """For the CURRENT move, the weight value if it's a weighted
        strength move (e.g. '5'). Returns None if current move doesn't
        show layout_weight.

        Note: Weight visibility is per-MOVE. A class can have weighted
        and non-weighted moves — this checks the current move only."""
        if not self.is_current_move_weighted():
            return None
        try:
            return self.get_text(self.TEXT_WEIGHT_VALUE_ID)
        except Exception:
            return None

    def get_weight_unit(self):
        """For the CURRENT move, the weight unit label (e.g. 'LBS').
        Returns None if current move doesn't show layout_weight."""
        if not self.is_current_move_weighted():
            return None
        try:
            return self.get_text(self.LABEL_LBS_ID)
        except Exception:
            return None

    def get_weight(self):
        """Convenience: combined weight + unit string (e.g. '5 LBS') for
        the current move. Returns None if current move isn't weighted."""
        val = self.get_weight_value()
        unit = self.get_weight_unit()
        if val and unit:
            return f"{val} {unit}"
        return None