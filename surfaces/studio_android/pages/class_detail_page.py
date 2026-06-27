"""ClassDetailPage — Studio's class preview screen.

Reached by tapping a class card on the Studio tab. Shows class metadata
and a START SESSION button. Tapping START SESSION advances to
MusicSelectionPage (separate dump needed). Tapping button_close returns
to the Studio tab.

Three observed variants of this page based on class type:

  REGULAR VOD CLASS
    text_title, text_info ('30 Min • Intermediate • Yoga • Johanna Q')
    text_description (multi-line description)
    text_equipment ('WHAT YOU'LL NEED') + layout_equipment + equipment_name × N
    button_start_class + label_start_class ('START SESSION')

  CPS (CUSTOM PLANNED SESSION) CLASS
    text_title, text_info ('30 Min • All Levels • Fitness')
    profile_button (×2) + profile_image + profile_button_text (trainer ST)
    text_personal_message (the trainer's note for this CPS — may be empty)
    NO text_description, NO equipment list
    layout_moves + layout_moves_scroll_content with sections + moves:
      text_move ('Warm Up')      + text_reps ('1x')        ← section header
      divider
      text_move ('Cat Cow')      + text_reps (':30')       ← move
      text_move ('Chest Opener') + text_reps (':30')       ← move
      ...
    button_start_class + label_start_class ('START SESSION')

  PLANNED SESSION / WORKOUT (from WORKOUTS sub-tab)
    text_title, text_info ('15 Min • All Levels • Strength • Team FORME')
    text_description (multi-line description)
    NO equipment list (typically)
    layout_moves with sections + moves (same structure as CPS)
    button_start_class + label_start_class ('START SESSION')

Header elements (always present across all variants):
  button_close, apple_music_button (×2), button_apple_watch,
  button_bookmark, utility_button

NOTE on text_info parsing:
  Single bullet-separated string. Order: '<duration> • <level> • <category>
  • <trainer>'. CPS classes have only 3 parts (no trainer field), so
  get_trainer() returns None for those.

NOTE on bookmark state:
  button_bookmark is icon-only — no text indicates current state. The
  `selected` attribute is our best guess; confirm with a follow-up dump
  after tapping.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class ClassDetailPage(StudioBasePage):
    # --- Element IDs (confirmed from dumps on 2026-04-27) ---
    CONTENT_ID = "content"
    BUTTON_CLOSE_ID = "button_close"
    BUTTON_BOOKMARK_ID = "button_bookmark"
    BUTTON_APPLE_WATCH_ID = "button_apple_watch"
    APPLE_MUSIC_BUTTON_ID = "apple_music_button"
    UTILITY_BUTTON_ID = "utility_button"

    TOP_LAYER_ID = "top_layer"
    TEXT_TITLE_ID = "text_title"
    TEXT_INFO_ID = "text_info"
    TEXT_DESCRIPTION_ID = "text_description"
    TEXT_PERSONAL_MESSAGE_ID = "text_personal_message"  # CPS only

    # CPS variant — trainer avatar shown on detail page
    PROFILE_BUTTON_ID = "profile_button"
    PROFILE_BUTTON_TEXT_ID = "profile_button_text"
    PROFILE_IMAGE_ID = "profile_image"

    # Equipment list (regular VOD only)
    TEXT_EQUIPMENT_ID = "text_equipment"        # 'WHAT YOU'LL NEED' header
    LAYOUT_EQUIPMENT_ID = "layout_equipment"
    EQUIPMENT_NAME_ID = "equipment_name"
    EQUIPMENT_IMAGE_ID = "equipment_image"

    # Move list (CPS + Planned Session variants)
    LAYOUT_MOVES_ID = "layout_moves"
    LAYOUT_MOVES_SCROLL_CONTENT_ID = "layout_moves_scroll_content"
    TEXT_MOVE_ID = "text_move"
    TEXT_REPS_ID = "text_reps"
    DIVIDER_ID = "divider"

    # Primary CTA
    BUTTON_START_CLASS_ID = "button_start_class"
    LABEL_START_CLASS_ID = "label_start_class"  # 'START SESSION'

    # --- Variant identification ---

    VARIANT_VOD = "vod"           # regular VOD with description + equipment
    VARIANT_CPS = "cps"           # custom planned session with trainer + moves
    VARIANT_WORKOUT = "workout"   # planned session / workout with description + moves

    # --- Screen detection ---

    def is_loaded(self, timeout=3):
        """Non-blocking check: are we on a class detail screen?
        Anchored on button_start_class, the primary CTA present in
        all three variants."""
        return self.is_visible(self.BUTTON_START_CLASS_ID, timeout=timeout)

    def wait_for_class_detail(self):
        """Block until class detail renders."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.BUTTON_START_CLASS_ID)
        ))
        log.info("Class detail loaded")

    def get_variant(self):
        """Identify which variant of the class detail page is currently
        showing, based on which optional elements are present.

        Heuristic:
          - personal_message present  → CPS
          - layout_moves present (no personal_message) → WORKOUT
          - layout_equipment present (no moves) → VOD
          - fallback: VOD (most common)
        """
        if self.is_visible(self.TEXT_PERSONAL_MESSAGE_ID, timeout=1):
            return self.VARIANT_CPS
        if self.is_visible(self.LAYOUT_MOVES_ID, timeout=1):
            return self.VARIANT_WORKOUT
        if self.is_visible(self.LAYOUT_EQUIPMENT_ID, timeout=1):
            return self.VARIANT_VOD
        # Default — assume VOD
        return self.VARIANT_VOD

    # --- Reading core class metadata (all variants) ---

    def get_title(self):
        """Class title (e.g. 'Yoga Sculpt: Full Body')."""
        return self.get_text(self.TEXT_TITLE_ID)

    def get_info_string(self):
        """Raw info line — bullet-separated metadata.
        E.g. '30 Min • Intermediate • Yoga • Johanna Q'"""
        return self.get_text(self.TEXT_INFO_ID)

    def _info_parts(self):
        """Split the info string on bullets, trimming whitespace.
        Returns parts in document order. Order is typically:
        [duration, level, category, trainer]. CPS classes lack trainer."""
        info = self.get_info_string() or ""
        return [p.strip() for p in info.split("•") if p.strip()]

    def get_duration(self):
        """Duration string (e.g. '30 Min'). Returns None if not present."""
        parts = self._info_parts()
        return parts[0] if len(parts) >= 1 else None

    def get_level(self):
        """Difficulty level (e.g. 'Intermediate'). Returns None if not present."""
        parts = self._info_parts()
        return parts[1] if len(parts) >= 2 else None

    def get_category(self):
        """Class category (e.g. 'Yoga'). Returns None if not present."""
        parts = self._info_parts()
        return parts[2] if len(parts) >= 3 else None

    def get_trainer(self):
        """Trainer name from text_info (e.g. 'Johanna Q'). Returns None
        for classes without an attributed trainer in text_info (e.g. CPS
        classes — for those, use get_trainer_initials_from_avatar())."""
        parts = self._info_parts()
        return parts[3] if len(parts) >= 4 else None

    def get_description(self):
        """Class description text. Returns None if not present (CPS
        classes don't have a description — they have a personal message
        instead via get_personal_message())."""
        try:
            return self.get_text(self.TEXT_DESCRIPTION_ID)
        except Exception:
            return None

    # --- CPS-specific elements ---

    def get_personal_message(self):
        """Trainer's personal message for a CPS class. Returns None if
        not present (non-CPS variants)."""
        try:
            return self.get_text(self.TEXT_PERSONAL_MESSAGE_ID)
        except Exception:
            return None

    def has_personal_message(self):
        """True if the personal message field is present (CPS class)."""
        return self.is_visible(self.TEXT_PERSONAL_MESSAGE_ID, timeout=2)

    def get_trainer_initials_from_avatar(self):
        """For CPS classes, the trainer's avatar is shown with initials
        (e.g. 'ST'). Returns the first profile_button_text on the
        screen, which is the trainer's avatar in CPS variants."""
        try:
            els = self.find_all_by_id(self.PROFILE_BUTTON_TEXT_ID)
            if els:
                return els[0].get_attribute("text") or ""
        except Exception:
            pass
        return None

    # --- Equipment list (VOD variant) ---

    def get_required_equipment(self):
        """Return a list of equipment names required (e.g. ['DUMBBELLS',
        'MAT']). Returns empty list if no equipment section (CPS,
        Workout variants typically have none)."""
        equipment_els = self.find_all_by_id(self.EQUIPMENT_NAME_ID)
        return [e.get_attribute("text") or "" for e in equipment_els]

    def has_equipment(self):
        """True if the WHAT YOU'LL NEED section is present."""
        return self.is_visible(self.TEXT_EQUIPMENT_ID, timeout=2)

    # --- Move list (CPS + Workout variants) ---

    def has_move_list(self):
        """True if the move list (layout_moves) is present on screen."""
        return self.is_visible(self.LAYOUT_MOVES_ID, timeout=2)

    def get_all_moves(self):
        """Return all moves and section labels as a list of dicts:
          [
            {'name': 'Warm Up', 'reps': '1x', 'is_section': True},
            {'name': 'Alternating Hip Cradles', 'reps': '5'},
            {'name': 'Lateral Lunge with Overhead Reach', 'reps': '5'},
            {'name': 'Conditioning', 'reps': '1x', 'is_section': True},
            ...
          ]

        Section headers are identified by reps ending in 'x' (e.g. '1x',
        '2x', '3x') — these are repeat-count markers for the section.
        Individual moves have either rep counts ('5', '10') or duration
        strings (':30', ':45')."""
        move_els = self.find_all_by_id(self.TEXT_MOVE_ID)
        rep_els = self.find_all_by_id(self.TEXT_REPS_ID)

        # Pair them by ordinal position. Both lists should be the same
        # length since each move has a corresponding reps value.
        moves = []
        for i, move_el in enumerate(move_els):
            name = (move_el.get_attribute("text") or "").strip()
            reps = ""
            if i < len(rep_els):
                reps = (rep_els[i].get_attribute("text") or "").strip()

            # Section headers have reps like '1x', '2x' (multiplier suffix)
            is_section = bool(reps) and reps[-1].lower() == "x" and reps[:-1].isdigit()

            entry = {"name": name, "reps": reps}
            if is_section:
                entry["is_section"] = True
            moves.append(entry)
        return moves

    def get_move_count(self):
        """Total number of items in the move list (sections + moves)."""
        return len(self.find_all_by_id(self.TEXT_MOVE_ID))

    def get_section_names(self):
        """Just the section labels from the move list (e.g. ['Warm Up',
        'Conditioning', 'Mobility'])."""
        return [m["name"] for m in self.get_all_moves()
                if m.get("is_section")]

    # --- Actions ---

    def tap_start_session(self):
        """Tap the START SESSION button. Advances to MusicSelectionPage."""
        self.tap_by_id(self.BUTTON_START_CLASS_ID)
        self.wait_seconds(2)
        log.info("Tapped START SESSION")

    def tap_close(self):
        """Tap the close (X) button — returns to the Studio tab."""
        self.tap_by_id(self.BUTTON_CLOSE_ID)
        self.wait_seconds(1)
        log.info("Closed class detail (returned to Studio tab)")

    # --- Bookmark ---

    def tap_bookmark(self):
        """Toggle bookmark on/off for this class. Caller should know or
        check current state via is_bookmarked()."""
        self.tap_by_id(self.BUTTON_BOOKMARK_ID)
        self.wait_seconds(1)
        log.info("Tapped bookmark toggle")

    def is_bookmarked(self):
        """Check bookmark state via the element's `selected` attribute.
        TODO: confirm this attribute actually changes on toggle — may
        need a different signal (content-desc, drawable resource)."""
        try:
            el = self.find_by_id(self.BUTTON_BOOKMARK_ID)
            return el.get_attribute("selected") == "true"
        except Exception as e:
            log.info(f"Could not determine bookmark state: {e}")
            return False

    # --- Apple Watch / Apple Music ---

    def tap_apple_watch(self):
        """Tap the Apple Watch button (FORME-6541)."""
        self.tap_by_id(self.BUTTON_APPLE_WATCH_ID)

    def tap_apple_music(self):
        """Tap the Apple Music button. Note: id appears twice (outer +
        inner) — find_element returns the first match."""
        self.tap_by_id(self.APPLE_MUSIC_BUTTON_ID)