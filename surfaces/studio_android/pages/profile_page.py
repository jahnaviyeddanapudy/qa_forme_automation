"""ProfileActivity — the Studio launcher / user-picker screen.

The Studio app boots straight to ProfileActivity on every launch. Profiles
appear as tappable buttons inside a RecyclerView. Tapping a profile may:
  - Auto-login → directly to home (if user previously chose "Keep me logged in")
  - Show a Sign In prompt → password required (handled in sign_in_page.py)

Profile identification is POSITIONAL. The recycler returns elements in
some order which may not match visual on-screen order, and which varies
between Studios. Tests must not assume "index 0 = owner" — instead each
QA configures their Studio so the desired profile is at the index their
tests target.

NOTE on element layout — ProfileActivity has a tricky tree:
  - `profile_button` id appears TWICE per profile row (outer container
    + clickable inner wrapper)
  - `text_name` id appears N+1 times — once per profile row PLUS one
    empty extra near the Add Profile button. We filter empties out.
  - `profile_button_text` (initials) appears EXACTLY once per profile
    row, only inside real profile rows — used as the canonical row count

We do NOT use XPath ancestor:: traversal — Appium UiAutomator2 doesn't
support it reliably. Instead we filter and pair flat element lists.

Setup Wizard (first-run state) is NOT this screen. See setup_wizard_page.py.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from selenium.webdriver.support import expected_conditions as EC


class ProfilePage(StudioBasePage):
    # Element IDs confirmed from dump on 2026-04-24
    RECYCLER_ID = "recycler"
    PROFILE_BUTTON_ID = "profile_button"
    PROFILE_IMAGE_ID = "profile_image"
    PROFILE_BUTTON_TEXT_ID = "profile_button_text"  # initials, e.g. "ST"
    PROFILE_NAME_ID = "text_name"                   # display name, e.g. "SILVANUS"
    BUTTON_ADD_ID = "button_add"                    # add new profile
    BUTTON_UTILITY_ID = "button_utility"            # top-corner action
    LOGO_ID = "image_logo"                          # FORME logo at top

    def wait_for_profile_screen(self):
        """Wait for ProfileActivity to render. Uses image_logo as the
        primary marker (always present here, not on Setup Wizard or
        Sign In). Then waits for at least one profile_button to bind."""
        self.wait.until(EC.presence_of_element_located(self.by_id(self.LOGO_ID)))
        self.wait.until(
            EC.presence_of_element_located(self.by_id(self.PROFILE_BUTTON_ID))
        )
        log.info("ProfileActivity loaded")

    def is_loaded(self, timeout=3):
        """Non-blocking check — useful for distinguishing ProfileActivity
        from Sign In or other in-app screens."""
        return self.is_visible(self.LOGO_ID, timeout=timeout)

    # --- Profile querying ---
    #
    # Canonical sources:
    #   - profile count → count of `profile_button_text` (initials) — exactly
    #     one per row, never present on non-profile widgets
    #   - per-row name  → text_name elements with non-empty text — filters out
    #     the empty text_name emitted near the Add Profile button
    #   - per-row tap target → outer of the two profile_button elements
    #     for the row (so even-index entries: 0, 2, 4, ...)

    def _all_initials_elements(self):
        return self.find_all_by_id(self.PROFILE_BUTTON_TEXT_ID)

    def _all_name_texts(self):
        """Return the text of every text_name element on screen, with
        empty entries filtered out. Empties come from the Add Profile
        button's label slot."""
        return [
            (el.get_attribute("text") or "").strip()
            for el in self.find_all_by_id(self.PROFILE_NAME_ID)
            if (el.get_attribute("text") or "").strip()
        ]

    def _all_profile_button_containers(self):
        """All profile_button elements — note this returns 2 per row.
        Outer container is at even indices (0, 2, 4, ...)."""
        return self.find_all_by_id(self.PROFILE_BUTTON_ID)

    def profile_count(self):
        """Number of profiles currently visible. Uses initials count
        (one per row, never polluted)."""
        return len(self._all_initials_elements())

    def get_profile_name(self, index):
        """Display name at the given profile index (uppercase, e.g.
        'SILVANUS').

        Pairs by ordinal position: the Nth non-empty text_name is the
        Nth profile's name. Assumes the Studio's recycler maintains the
        same per-row order across both `profile_button_text` and
        `text_name` element queries — true in every dump we've inspected
        and standard RecyclerView behavior."""
        names = self._all_name_texts()
        if index >= len(names):
            raise IndexError(
                f"Profile index {index} out of range — only "
                f"{len(names)} non-empty profile names visible "
                f"(profile_count() = {self.profile_count()})"
            )
        return names[index]

    def get_profile_initials(self, index):
        """Initials at the given index (e.g. 'ST' for Silvanus Thomas)."""
        initials = self._all_initials_elements()
        if index >= len(initials):
            raise IndexError(
                f"Profile index {index} out of range — only "
                f"{len(initials)} profiles visible"
            )
        return initials[index].get_attribute("text") or ""

    def all_profile_names(self):
        """List of all visible profile names. Convenient for tests that
        want to verify which profiles exist regardless of order."""
        return self._all_name_texts()

    # --- Profile tapping ---

    def tap_profile_at(self, index):
        """Tap the profile at the given recycler row index.

        Recycler order is whatever the Studio app returns — it does NOT
        necessarily match visual on-screen order, and may differ between
        Studios. Tests pick which index corresponds to the desired
        account based on their Studio's actual setup.

        Implementation: profile_button id appears twice per row (outer
        container + clickable inner wrapper). Outer is at even global
        indices, so for row N we tap index N*2."""
        count = self.profile_count()
        if index >= count:
            raise IndexError(
                f"Cannot tap profile at index {index} — only {count} "
                f"profiles visible. Use profile_count() to check first."
            )
        buttons = self._all_profile_button_containers()
        outer_index = index * 2
        if outer_index >= len(buttons):
            raise RuntimeError(
                f"Expected {(count) * 2} profile_button elements (2 per "
                f"row × {count} rows) but found {len(buttons)}. The "
                f"recycler may have rendered an unexpected layout."
            )
        target = buttons[outer_index]
        try:
            name = self.get_profile_name(index)
        except IndexError:
            name = "<no name>"
        target.click()
        log.info(f"Tapped profile [{index}]: {name}")

    def tap_first_profile(self):
        """Convenience for index 0."""
        self.tap_profile_at(0)

    def tap_profile_by_name(self, name):
        """Find the profile button whose name matches `name` and tap it.
        Match is case-insensitive and whitespace-trimmed.
        Raises ValueError if no matching profile exists."""
        target = name.strip().upper()
        names = self.all_profile_names()
        for i, n in enumerate(names):
            if n.upper() == target:
                self.tap_profile_at(i)
                return
        raise ValueError(
            f"No profile named '{name}' found. Visible profiles: {names}"
        )

    # --- Add / utility actions ---

    def tap_add_profile(self):
        """Open the 'Add new profile' flow. Used by guest-add tests."""
        self.tap_by_id(self.BUTTON_ADD_ID)

    def tap_utility(self):
        """Tap the top-corner utility button. TODO: confirm what this
        opens (likely Settings or Power menu) — capture another dump
        after tapping it to find out."""
        self.tap_by_id(self.BUTTON_UTILITY_ID)