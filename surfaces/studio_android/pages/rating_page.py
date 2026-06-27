"""RatingPage — Studio's post-class rating / survey screen.

Reached after ending a class (when class progressed far enough to
trigger rating). Submitting advances to SummaryPage.

Two observed variants — confirmed across class types on 2026-04-27:

  3-SECTION VARIANT — VOD classes only
    Session, Instructor, Difficulty For You

  2-SECTION VARIANT — CPS AND Workout classes
    Session, Difficulty For You
    (no Instructor section — for CPS, the trainer is the user's
    assigned personal trainer with separate feedback channels; for
    Workout / Planned Session, classes are typically Team FORME
    content where individual instructor rating may not apply)

Layout (same structure, different section count):

  text_title | "How Satisfied Are You With"   ← screen header

  recycler                                     ← list of rating sections
    [section 1 — always]
      text_title | "Session"
      layout_options                           ← 5 rating buttons
        content-desc | rating_session_star_1..5
    [section 2 — VOD only]
      text_title | "Instructor"
      layout_options
        content-desc | rating_instructor_star_1..5
    [last section — always]
      text_title | "Difficulty For You"
      layout_options
        content-desc | rating_difficulty_for_you_star_1..5

  button_submit | "SUBMIT"

STUDIO-4289 (Ready for QA on 2026-05-15):
  Dev added content-desc accessibility IDs to all 15 rating stars.
  Verified via dump_screen_attach on the fix build — all 15 present,
  cleanly named:

    rating_session_star_1..5
    rating_instructor_star_1..5
    rating_difficulty_for_you_star_1..5

  Note the difficulty section uses 'difficulty_for_you' (literal of
  the title), not just 'difficulty'.

Rating button strategy:
  PRIMARY: Look up by content-desc via AppiumBy.ACCESSIBILITY_ID.
           Robust, stable across UI changes, semantically meaningful.
  FALLBACK: Positional XPath child-walk within the section's
           layout_options element. Used only if content-desc lookup
           fails (e.g. running against an old build without the fix).
           Logs a warning when the fallback fires so we know.

NOTE on dynamic section detection:
  We scan get_section_titles() at runtime instead of asserting a fixed
  list. That way a 2-section CPS/Workout rating and a 3-section VOD
  rating both work — submit_default_ratings() iterates over what's
  actually on screen.

NOTE on submit button enablement:
  button_submit only enables after at least one rating is selected.
  Tests that use submit_default_ratings() naturally satisfy this.
  Tests that want to verify "submit is disabled before any rating"
  should call wait_for_rating_screen() then check button_submit's
  enabled state directly.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class RatingPage(StudioBasePage):
    # --- Element IDs (confirmed from VOD + CPS + Workout dumps) ---
    TEXT_TITLE_ID = "text_title"          # used for header AND each section name
    RECYCLER_ID = "recycler"
    LAYOUT_OPTIONS_ID = "layout_options"
    BUTTON_SUBMIT_ID = "button_submit"    # "SUBMIT"

    # --- Section names (text content of text_title elements within recycler) ---
    SECTION_SESSION = "Session"
    SECTION_INSTRUCTOR = "Instructor"
    SECTION_DIFFICULTY = "Difficulty For You"

    # All sections we recognize. Used to filter the page header
    # ("How Satisfied Are You With") from the actual section names.
    ALL_KNOWN_SECTIONS = [
        SECTION_SESSION, SECTION_INSTRUCTOR, SECTION_DIFFICULTY,
    ]

    # Map section title -> content-desc key fragment (per STUDIO-4289).
    # 1-indexed star numbers are appended at lookup time:
    #   rating_{key}_star_{N}  where N in 1..5
    _SECTION_KEY = {
        SECTION_SESSION: "session",
        SECTION_INSTRUCTOR: "instructor",
        SECTION_DIFFICULTY: "difficulty_for_you",
    }

    # --- Variants ---
    VARIANT_VOD = "vod"          # 3 sections: Session, Instructor, Difficulty
    VARIANT_CPS_OR_WORKOUT = "cps_or_workout"  # 2 sections: Session, Difficulty
    VARIANT_UNKNOWN = "unknown"

    # --- Screen detection ---

    def is_loaded(self, timeout=5):
        """Non-blocking check: are we on the rating screen?"""
        return self.is_visible(self.BUTTON_SUBMIT_ID, timeout=timeout)

    def wait_for_rating_screen(self, timeout=10):
        """Block until rating screen renders. Anchored on button_submit."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.BUTTON_SUBMIT_ID)
        ))
        log.info("Rating screen loaded")

    # --- Variant identification ---

    def get_variant(self):
        """Identify which rating variant is currently rendering, based
        on which sections are present.

        Returns:
          - 'vod': all 3 sections (Session, Instructor, Difficulty) —
            VOD classes only
          - 'cps_or_workout': 2 sections (Session, Difficulty —
            no Instructor) — both CPS and Workout/Planned Session
            classes use this variant
          - 'unknown': different section configuration we haven't seen
        """
        sections = set(self.get_section_titles())
        if sections == {self.SECTION_SESSION, self.SECTION_INSTRUCTOR,
                        self.SECTION_DIFFICULTY}:
            return self.VARIANT_VOD
        if sections == {self.SECTION_SESSION, self.SECTION_DIFFICULTY}:
            return self.VARIANT_CPS_OR_WORKOUT
        return self.VARIANT_UNKNOWN

    # --- Reading section info ---

    def get_section_titles(self):
        """Return all visible section titles in document order.
        E.g. ['Session', 'Instructor', 'Difficulty For You'] for VOD,
        or ['Session', 'Difficulty For You'] for CPS or Workout.

        Excludes the page header ('How Satisfied Are You With') by
        filtering against ALL_KNOWN_SECTIONS."""
        titles = self.find_all_by_id(self.TEXT_TITLE_ID)
        result = []
        for t in titles:
            text = (t.get_attribute("text") or "").strip()
            if text in self.ALL_KNOWN_SECTIONS:
                result.append(text)
        return result

    def get_layout_options_count(self):
        """Number of layout_options elements visible (one per section)."""
        return len(self.find_all_by_id(self.LAYOUT_OPTIONS_ID))

    def has_section(self, section_name):
        """Check if a given section is present on the current rating screen."""
        return section_name in self.get_section_titles()

    # --- Tapping rating options ---

    def tap_rating(self, section_name, option_index):
        """Tap a rating option within a given section.

        section_name: 'Session', 'Instructor', or 'Difficulty For You'
        option_index: 0-based index of the rating option within that
                     section. Typically 0-4 for the 5 stars.

        Strategy:
          1. PRIMARY — look up by content-desc using AppiumBy.ACCESSIBILITY_ID:
             rating_{section_key}_star_{option_index + 1}
             (1-indexed per dev convention; we translate at the boundary).
          2. FALLBACK — positional XPath child-walk within the section's
             layout_options. Logs a warning when this path fires.

        Raises ValueError if the section isn't present on this rating
        screen (e.g. requesting 'Instructor' on a CPS or Workout
        rating).
        """
        target_section = section_name.strip()
        if target_section not in self.ALL_KNOWN_SECTIONS:
            raise ValueError(
                f"Unknown rating section: '{section_name}'. "
                f"Known sections: {self.ALL_KNOWN_SECTIONS}"
            )

        # Section must be visible (e.g. don't ask for Instructor on CPS)
        section_titles = self.get_section_titles()
        if target_section not in section_titles:
            raise ValueError(
                f"Section '{section_name}' not visible on this rating "
                f"screen. Visible sections: {section_titles}. "
                f"(This is a CPS or Workout rating if Instructor is "
                f"missing.)"
            )

        # PRIMARY: content-desc lookup
        section_key = self._SECTION_KEY[target_section]
        star_number = option_index + 1  # dev uses 1-indexed star_1..star_5
        content_desc = f"rating_{section_key}_star_{star_number}"

        try:
            element = self.driver.find_element(
                AppiumBy.ACCESSIBILITY_ID, content_desc
            )
            element.click()
            self.wait_seconds(1)
            log.info(
                f"Tapped rating: {section_name}, option index "
                f"{option_index} (content-desc: {content_desc})"
            )
            return
        except Exception as e:
            log.warning(
                f"Content-desc lookup failed for '{content_desc}' ({e}). "
                f"Falling back to positional XPath. This means the build "
                f"under test does NOT have the STUDIO-4289 fix — verify "
                f"and consider blocking until rebuilt."
            )

        # FALLBACK: positional XPath child-walk
        self._tap_rating_by_position(target_section, option_index,
                                     section_titles)

    def _tap_rating_by_position(self, target_section, option_index,
                                section_titles):
        """Fallback tap strategy: positional within layout_options.

        Used when content-desc lookup fails (old build without
        STUDIO-4289). Fragile — depends on layout_options children
        being in stable order with no resource-ids."""
        section_ordinal = section_titles.index(target_section)

        layout_optionses = self.find_all_by_id(self.LAYOUT_OPTIONS_ID)
        if section_ordinal >= len(layout_optionses):
            raise RuntimeError(
                f"Found section '{target_section}' at ordinal "
                f"{section_ordinal} but only {len(layout_optionses)} "
                f"layout_options elements present"
            )

        layout = layout_optionses[section_ordinal]
        children = layout.find_elements(AppiumBy.XPATH, "./*")
        clickable = [c for c in children if c.is_displayed()]

        if option_index >= len(clickable):
            raise IndexError(
                f"Option index {option_index} out of range — section "
                f"'{target_section}' has {len(clickable)} options visible"
            )

        clickable[option_index].click()
        self.wait_seconds(1)
        log.info(
            f"Tapped rating (FALLBACK / positional): {target_section}, "
            f"option index {option_index}"
        )

    def tap_session_rating(self, option_index):
        """Convenience: tap a Session rating by index (0-based)."""
        self.tap_rating(self.SECTION_SESSION, option_index)

    def tap_instructor_rating(self, option_index):
        """Convenience: tap an Instructor rating by index (0-based).
        Only available on VOD variant — raises if used on CPS/Workout."""
        self.tap_rating(self.SECTION_INSTRUCTOR, option_index)

    def tap_difficulty_rating(self, option_index):
        """Convenience: tap a Difficulty rating by index (0-based)."""
        self.tap_rating(self.SECTION_DIFFICULTY, option_index)

    # --- Submit ---

    def tap_submit(self):
        """Submit the rating. Advances to SummaryPage."""
        self.tap_by_id(self.BUTTON_SUBMIT_ID)
        self.wait_seconds(2)
        log.info("Tapped SUBMIT (rating submitted)")

    # --- Convenience for tests that just need to clear the rating screen ---

    def submit_default_ratings(self, option_index=2):
        """Tap a 'middle' rating in each VISIBLE section, then submit.
        option_index defaults to 2 (3rd of 5 stars).

        Iterates over actual visible sections at runtime, so works for
        VOD (3 sections) and CPS/Workout (2 sections) without
        modification.

        Useful for tests that need to advance past the rating screen
        without caring what gets submitted. For tests specifically
        about rating behavior, use tap_*_rating() directly. For tests
        that want different ratings per section (e.g. for visual
        differentiation between runs), use submit_ratings()."""
        sections = self.get_section_titles()
        if not sections:
            log.info(
                "submit_default_ratings called but no sections detected "
                "— submitting anyway (may fail validation)"
            )
        for section in sections:
            self.tap_rating(section, option_index)
        self.tap_submit()

    def submit_ratings(self, session=4, instructor=5, difficulty=2):
        """Tap a specific rating per section, then submit.

        Args are 1-indexed star numbers (1-5), matching dev's
        rating_*_star_N naming convention and the natural way to
        describe ratings ("5 stars for instructor"). Internally we
        translate to 0-indexed for tap_rating().

        Defaults (session=4, instructor=5, difficulty=2) are chosen
        for visual differentiation — a screen recording or live
        observer can immediately tell this came from an automation
        run because the pattern is distinctive (not the boring all-3
        from submit_default_ratings).

        Graceful variant handling:
          - On VOD (3 sections): all three args are applied.
          - On CPS/Workout (2 sections, no Instructor): the instructor
            arg is silently ignored. The same call works across
            variants without raising.

        Raises ValueError if a star number is outside 1-5."""
        for name, n in [("session", session),
                        ("instructor", instructor),
                        ("difficulty", difficulty)]:
            if not (1 <= n <= 5):
                raise ValueError(
                    f"Star number for {name} must be 1-5, got {n}"
                )

        visible_sections = self.get_section_titles()

        rating_map = {
            self.SECTION_SESSION: session,
            self.SECTION_INSTRUCTOR: instructor,
            self.SECTION_DIFFICULTY: difficulty,
        }

        for section, star_number in rating_map.items():
            if section not in visible_sections:
                # CPS/Workout variant lacks Instructor — silently skip
                log.info(
                    f"Section '{section}' not visible on this rating "
                    f"variant — skipping (variant: {self.get_variant()})"
                )
                continue
            # Translate 1-indexed star number to 0-indexed option_index
            self.tap_rating(section, star_number - 1)

        self.tap_submit()