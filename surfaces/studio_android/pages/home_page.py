"""HomePage — Studio's main screen after login.

Three tabs at the top: YOUR PLAN, STUDIO, LIVE 1:1. Tabs are addressed
by content-desc (no resource-id on tab elements themselves — see
TAB_BY_DESC).

Two view variants for the YOUR PLAN tab depending on account state:
  - Recommended view (account has no trainer schedule):
      text_recommended = "Recommended"
      text_concierge   = "BY YOUR FORME TEAM"
      text_description = "Classes you might enjoy..."
      flat list of class cards
  - Weekly Plan view (account has assigned trainer + schedule):
      text_recommended = "Weekly Plan"     ← misleading id name
      text_concierge   = "BY <TRAINER NAME>"
      cards grouped under text_header sections (TODAY / TOMORROW / etc.)
      Live 1:1 cards have additional profile_user + profile_trainer wrappers
      Rest day cards have no text_trainer

Schedule Drop dialog can appear on home load (post-login) and blocks
content rendering. Detected by text 'Your Weekly Schedule Drop'.
Dismissed via button_close (which has text 'VIEW MY SCHEDULE' as the
primary CTA — so dismissing also navigates to Your Plan tab).

Element IDs are largely identical to the member Android app — same
team/codebase appears to share resource-ids across both surfaces.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from surfaces.studio_android.config import APP_PACKAGE
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime


class HomePage(StudioBasePage):
    # --- Element IDs (confirmed from owner + guest dumps on 2026-04-24) ---
    HEADER_FRAGMENT_ID = "header_fragment"
    TAB_LAYOUT_ID = "tab_layout"
    UTILITY_BUTTON_ID = "utility_button"
    SETTINGS_BUTTON_ID = "button_settings"
    APPLE_MUSIC_BUTTON_ID = "apple_music_button"
    NAV_HOST_FRAGMENT_ID = "nav_host_fragment"

    # Profile button in the header (top-left of home, shows user's
    # initials). Tapping it returns to ProfileActivity directly — no
    # overlay or confirmation. This element id appears multiple times
    # on screen (header avatar + various card avatars), so we scope to
    # the header_fragment when tapping it for back-to-profile.
    PROFILE_BUTTON_ID = "profile_button"
    PROFILE_BUTTON_TEXT_ID = "profile_button_text"

    RECOMMENDATIONS_FRAGMENT_ID = "recommendations_fragment"
    WEEK_STATS_FRAGMENT_ID = "week_stats_fragment"
    PROMOTIONS_FRAGMENT_ID = "promotions_fragment"

    # Section header label — id name is misleading; shows either
    # "Recommended" or "Weekly Plan" depending on account state
    SECTION_HEADER_ID = "text_recommended"
    LAYOUT_CONCIERGE_ID = "layout_concierge"
    TEXT_CONCIERGE_ID = "text_concierge"
    TEXT_DESCRIPTION_ID = "text_description"   # only present on Recommended view

    # Class cards
    CARD_ID = "card"
    TEXT_TITLE_ID = "text_title"
    TEXT_TRAINER_ID = "text_trainer"           # absent on Rest day + Recommended sometimes
    TEXT_DETAIL_ID = "text_detail"
    TEXT_HEADER_ID = "text_header"             # day grouping label (TODAY/TOMORROW)
    IMAGE_BOOKMARK_ID = "image_bookmark"

    # Progress section
    RADIO_WEEK_ID = "radio_week"
    RADIO_MONTH_ID = "radio_four_weeks"
    RADIO_LIFE_ID = "radio_life"
    LABEL_DESCRIPTION_ID = "label_description"
    LABEL_CURRENT_STREAK_ID = "label_current_streak"
    LABEL_SESSIONS_ID = "label_sessions"
    LABEL_MINUTES_ACTIVE_ID = "label_minutes_active"
    LABEL_CALORIES_ID = "label_calories"
    DAYS_CHECKMARKS_ID = "days_checkmarks"

    # --- Tabs are addressed by content-desc ---
    TAB_YOUR_PLAN_DESC = "YOUR PLAN"
    TAB_STUDIO_DESC = "STUDIO"
    TAB_LIVE_1ON1_DESC = "LIVE 1:1"

    # --- Dialog markers ---
    SCHEDULE_DROP_TITLE = "Your Weekly Schedule Drop"
    SCHEDULE_DROP_DISMISS_ID = "button_close"  # button text is "VIEW MY SCHEDULE"
    HRM_DIALOG_TITLE = "HEART RATE MONITOR"    # if/when Studio has one

    # --- Screen detection ---

    def is_loaded(self, timeout=3):
        """Non-blocking check: is home currently up?
        Anchored on tab_layout (always present on home, not on Profile/SignIn)."""
        return self.is_visible(self.TAB_LAYOUT_ID, timeout=timeout)

    def wait_for_home(self):
        """Block until home renders. Dismisses Schedule Drop dialog if it
        appears post-login (the dialog blocks tab_layout from interaction
        but doesn't necessarily prevent it from being in the view tree —
        we still poll for it as the marker)."""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.by_id(self.TAB_LAYOUT_ID))
            )
        except Exception:
            # Could be Schedule Drop blocking — try dismissing once and retry
            self.dismiss_schedule_drop()
            self.wait.until(
                EC.presence_of_element_located(self.by_id(self.TAB_LAYOUT_ID))
            )
        # Even after tab_layout shows, schedule drop dialog may still be up
        # over the content. Dismiss opportunistically.
        self.dismiss_schedule_drop()
        log.info("Home loaded")

    def is_on_weekly_plan_view(self):
        """True if home is showing the Weekly Plan variant (account has
        a trainer assigned)."""
        if not self.is_loaded(timeout=2):
            return False
        try:
            return self.get_text(self.SECTION_HEADER_ID) == "Weekly Plan"
        except Exception:
            return False

    def is_on_recommended_view(self):
        """True if home is showing the Recommended variant (account has
        no trainer)."""
        if not self.is_loaded(timeout=2):
            return False
        try:
            return self.get_text(self.SECTION_HEADER_ID) == "Recommended"
        except Exception:
            return False

    # --- Tab navigation ---

    def _tap_tab(self, content_desc):
        """Tap a top-tab by its content-desc. Tabs are TabLayout items
        with content-desc but no resource-id."""
        try:
            el = self.driver.find_element(
                AppiumBy.XPATH, f"//*[@content-desc='{content_desc}']"
            )
            el.click()
            self.wait_seconds(2)
            log.info(f"Tapped tab: {content_desc}")
        except Exception as e:
            raise RuntimeError(f"Could not tap tab '{content_desc}': {e}")

    def tap_your_plan_tab(self):
        self._tap_tab(self.TAB_YOUR_PLAN_DESC)
        # Schedule drop can appear when navigating into Your Plan
        self.dismiss_schedule_drop()

    def tap_studio_tab(self):
        self._tap_tab(self.TAB_STUDIO_DESC)

    def tap_live_1on1_tab(self):
        self._tap_tab(self.TAB_LIVE_1ON1_DESC)

    def tap_utility_button(self):
        """Tap the utility button in the header (gear/settings icon)."""
        self.tap_by_id(self.UTILITY_BUTTON_ID)

    def tap_settings(self):
        """Open the main Settings screen: utility button → SETTINGS panel button."""
        self.tap_by_id(self.UTILITY_BUTTON_ID)
        self.tap_by_id(self.SETTINGS_BUTTON_ID)

    def tap_apple_music_button(self):
        """Tap the Apple Music integration button. Note this id appears
        twice in the dump (outer + inner) — we tap by id which Selenium
        defaults to the first match."""
        self.tap_by_id(self.APPLE_MUSIC_BUTTON_ID)

    # --- Profile / session navigation ---

    def tap_back_to_profile(self, timeout=10):
        """Tap the profile_button in the header (top-left avatar) to
        return to ProfileActivity. Waits for ProfileActivity to load,
        fails loudly if it doesn't.

        This mirrors what a real user does to switch profiles: tap the
        avatar in the top-left corner of home, which navigates directly
        back to the profile picker — no overlay or confirmation. Use
        this when you need to chain multiple profile sessions in a
        single test/driver session without a full driver restart.

        IMPORTANT: profile_button id appears multiple times on home
        (header avatar + Live 1:1 card avatars + Weekly Plan card
        trainer avatars). We scope the lookup to header_fragment to
        guarantee we tap the *header's* profile button, not a card's.

        Args:
            timeout: seconds to wait for ProfileActivity to load after tap

        Raises:
            RuntimeError if the header profile_button can't be found, or
            if ProfileActivity doesn't load within `timeout` seconds.
        """
        # Scope to header_fragment so we don't pick up card avatars.
        xpath = (
            f"//*[@resource-id='{APP_PACKAGE}:id/{self.HEADER_FRAGMENT_ID}']"
            f"//*[@resource-id='{APP_PACKAGE}:id/{self.PROFILE_BUTTON_ID}']"
        )
        try:
            el = self.driver.find_element(AppiumBy.XPATH, xpath)
        except Exception as e:
            raise RuntimeError(
                f"Could not find profile_button inside header_fragment "
                f"on home. The header layout may have changed, or home "
                f"is not currently displayed. Underlying error: {e}"
            )

        el.click()
        log.info("Tapped header profile_button — returning to ProfileActivity")

        # Wait for ProfileActivity to load. We import ProfilePage here
        # rather than at module top to avoid a circular import (ProfilePage
        # could one day reference HomePage for cross-screen flows).
        from surfaces.studio_android.pages.profile_page import ProfilePage
        profile = ProfilePage(self.driver)
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.by_id(profile.LOGO_ID))
            )
            # Logo present — also wait for at least one profile_button to
            # bind in the recycler so subsequent tap_profile_at() calls
            # don't race the recycler binding.
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    self.by_id(profile.PROFILE_BUTTON_ID)
                )
            )
            log.info("ProfileActivity loaded after tap_back_to_profile")
        except Exception as e:
            raise RuntimeError(
                f"Tapped header profile_button but ProfileActivity did "
                f"not load within {timeout}s. The tap may have opened an "
                f"overlay/menu instead of navigating directly, or the "
                f"app entered an unexpected state. Underlying error: {e}"
            )

    # --- Dialog dismissal ---

    def dismiss_schedule_drop(self, timeout=2):
        """Dismiss the Weekly Schedule Drop dialog if it appears.

        Returns True if dismissed, False if no dialog was present.

        Note: the dismiss button (button_close) has text 'VIEW MY SCHEDULE'
        and tapping it navigates to the Your Plan tab. So dismissing the
        dialog doubles as 'land on Your Plan' — usually what callers want."""
        if self.is_text_visible(self.SCHEDULE_DROP_TITLE, timeout=timeout):
            try:
                self.tap_by_id(self.SCHEDULE_DROP_DISMISS_ID)
                self.wait_seconds(1)
                log.info("Dismissed schedule drop dialog")
                return True
            except Exception as e:
                log.info(f"Failed to dismiss schedule drop: {e}")
                return False
        return False

    def dismiss_hrm_dialog(self, timeout=5):
        """Dismiss the HRM dialog if it appears. Mirrors member app behavior.

        TODO: confirmed structure once we see one on Studio. Currently
        based on member app pattern — Studio dump didn't show an HRM
        dialog (account/Studio combo had no HRM paired)."""
        dismissed_any = False

        # System permission prompt (OS-level)
        try:
            allow_btn = self.driver.find_element(
                AppiumBy.ID,
                "com.android.permissioncontroller:id/permission_allow_button",
            )
            allow_btn.click()
            self.wait_seconds(1)
            log.info("Granted system BT/location permission")
            dismissed_any = True
        except Exception:
            pass

        # App-level HRM dialog
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.XPATH, f"//*[@text='{self.HRM_DIALOG_TITLE}']")
                )
            )
            self.wait_seconds(1)
            close_buttons = self.find_all_by_id("button_close")
            if close_buttons:
                close_buttons[-1].click()
                self.wait_seconds(1)
                log.info("Dismissed HRM dialog")
                dismissed_any = True
        except Exception:
            if not dismissed_any:
                log.info("No HRM dialog")

        return dismissed_any

    # --- Class card iteration ---

    def find_all_class_titles(self):
        """Return text of all visible class titles on the current screen.
        Useful for verifying which classes are visible after navigation."""
        titles = self.find_all_by_id(self.TEXT_TITLE_ID)
        return [t.get_attribute("text") or "" for t in titles]

    def find_all_class_trainers(self):
        """Return text of all visible trainer names on cards. Note Rest
        days don't have a text_trainer, so this list may be shorter than
        find_all_class_titles()."""
        trainers = self.find_all_by_id(self.TEXT_TRAINER_ID)
        return [t.get_attribute("text") or "" for t in trainers]

    def get_card_count(self):
        """Number of visible class cards. Includes Rest day cards."""
        return len(self.find_all_by_id(self.CARD_ID))

    def tap_class_by_name(self, class_name):
        """Tap the first card whose title matches class_name (case-insensitive
        partial match)."""
        self.tap_by_text_contains(class_name)

    def tap_class_by_index(self, index):
        """Tap the Nth class card on screen."""
        cards = self.find_all_by_id(self.CARD_ID)
        if index >= len(cards):
            raise IndexError(
                f"Card index {index} out of range — only {len(cards)} "
                f"cards visible"
            )
        cards[index].click()

    # --- Day-grouping (Weekly Plan view only) ---

    def find_all_day_headers(self):
        """Return text of all visible day-group headers (TODAY, TOMORROW,
        REST UP, etc.) on the Weekly Plan view."""
        headers = self.find_all_by_id(self.TEXT_HEADER_ID)
        return [h.get_attribute("text") or "" for h in headers]

    def is_day_header_visible(self, day_name):
        """Check whether a specific day header is visible (e.g. 'TODAY')."""
        return self.is_text_visible(day_name.upper(), timeout=2)

    # --- Progress section ---

    def scroll_to_progress(self):
        """Scroll down until the 'Progress' section is in view."""
        self.scroll_to_text("Progress")

    def tap_week_tab(self):
        self.tap_by_id(self.RADIO_WEEK_ID)

    def tap_month_tab(self):
        self.tap_by_id(self.RADIO_MONTH_ID)

    def tap_life_tab(self):
        self.tap_by_id(self.RADIO_LIFE_ID)

    def get_current_streak(self):
        """Return current streak count as an integer."""
        return int(self.get_text(self.LABEL_CURRENT_STREAK_ID))

    def get_sessions_count(self):
        return self.get_text(self.LABEL_SESSIONS_ID)

    def get_minutes_active(self):
        return self.get_text(self.LABEL_MINUTES_ACTIVE_ID)

    def get_calories(self):
        return self.get_text(self.LABEL_CALORIES_ID)

    def get_description_label(self):
        """Return text from label_description in the Progress section.
        Distinguishes which view is active:
          - Week view  → 'VS LAST WEEK'
          - Month view → 'VS <MONTH NAME>' (e.g. 'VS APRIL')
          - Life view  → 'MEMBER SINCE <MONTH> <YEAR>' (e.g.
                          'MEMBER SINCE JUNE 2022')
        """
        return self.get_text(self.LABEL_DESCRIPTION_ID)

    def get_today_day_state(self):
        """Read today's completion state from the Week view's
        days_checkmarks row.

        Days are mapped Mon=d1, Tue=d2, ..., Sun=d7. Studio uses
        MUTUALLY EXCLUSIVE child elements to indicate state — each
        d{N} container has EXACTLY ONE of:
          - image_check → empty placeholder (day NOT completed,
                          visual: empty circle)
          - image_fire  → completion marker (day completed, visual:
                          fire icon)

        Verified by comparing dumps:
          Owner with 0 sessions this week → ALL 7 days have image_check
          Guest with today's class done   → today (d3) = image_fire,
                                            all other days = image_check

        find_element succeeds for whichever child the container has;
        the OTHER child is not present in the DOM at all. This is the
        signal — which icon is the child, not whether it's displayed.

        Returns:
          'completed'  if d{N} has an image_fire child (today done)
          'incomplete' if d{N} has an image_check child (today empty)
          None         if d{N} can't be found, or has neither child
                       (genuinely unexpected — file JIRA)

        Caller must be on YOUR PLAN → Progress → Week view with the
        days_checkmarks row scrolled into view.
        """
        today_id = f"d{datetime.date.today().weekday() + 1}"
        try:
            day_el = self.driver.find_element(
                AppiumBy.ID, f"{APP_PACKAGE}:id/{today_id}"
            )
        except Exception as e:
            log.info(f"Could not find today's day container "
                     f"({today_id}): {e}")
            return None

        # Check for image_fire first (completion marker). If present,
        # day is completed.
        try:
            day_el.find_element(
                AppiumBy.ID, f"{APP_PACKAGE}:id/image_fire"
            )
            return "completed"
        except Exception:
            pass

        # Otherwise check for image_check (empty placeholder).
        try:
            day_el.find_element(
                AppiumBy.ID, f"{APP_PACKAGE}:id/image_check"
            )
            return "incomplete"
        except Exception:
            pass

        # Neither child — should not happen. Log and return None so
        # caller can flag this.
        log.warning(f"Today's day container ({today_id}) has neither "
                    f"image_check nor image_fire child — unexpected "
                    f"state, file JIRA")
        return None

    # --- Header / profile ---

    def get_logged_in_initials(self):
        """Return the initials shown on the user's avatar in the header.
        Note: profile_button_text appears multiple times on screen
        (header avatar, schedule cards' trainer avatars, etc.). This
        returns the FIRST instance — which is the header's user avatar."""
        elements = self.find_all_by_id("profile_button_text")
        if not elements:
            raise RuntimeError("No profile_button_text elements found on home")
        return elements[0].get_attribute("text") or ""