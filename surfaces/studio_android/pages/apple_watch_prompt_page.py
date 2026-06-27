"""AppleWatchPromptPage — modal prompt shown between Music selection
and the actual Player.

This dialog appears when starting a class IF:
  - The user has not paired/configured an Apple Watch, AND
  - The "Don't show me this again" checkbox has NOT been ticked

For most automation runs we want to dismiss this dialog by tapping
CONTINUE TO SESSION. If we tap the checkbox first, it won't appear in
subsequent test runs on this profile — useful for clean test runs but
worth being deliberate about.

Layout:

  layout_wearing_question
    image1                         ← Apple Watch graphic
    text1 | "Connect Your Apple Watch"
    text2 | "Launch the Forme iOS app and watchOS app to track..."
    button_continue | "CONTINUE TO SESSION"
    button_setup    | "SET UP YOUR APPLE WATCH"
    checkbox_do_not_show_again | "DON'T SHOW ME THIS AGAIN"

NOTE: This dialog is conditional. Tests should check is_visible() with
a short timeout before assuming presence — if not visible after 2-3s,
the player is loading directly (Apple Watch already configured or
checkbox previously ticked)."""
from surfaces.studio_android.pages.base import StudioBasePage, log
from selenium.webdriver.support import expected_conditions as EC


class AppleWatchPromptPage(StudioBasePage):
    # --- Element IDs (confirmed from dump on 2026-04-27) ---
    LAYOUT_ID = "layout_wearing_question"
    IMAGE_ID = "image1"
    TITLE_ID = "text1"             # "Connect Your Apple Watch"
    BODY_ID = "text2"              # body description
    BUTTON_CONTINUE_ID = "button_continue"   # "CONTINUE TO SESSION"
    BUTTON_SETUP_ID = "button_setup"         # "SET UP YOUR APPLE WATCH"
    CHECKBOX_DONT_SHOW_ID = "checkbox_do_not_show_again"

    # --- Detection ---

    def is_showing(self, timeout=3):
        """Check whether the Apple Watch prompt is currently displayed.
        Returns False if the player loaded directly (Apple Watch already
        paired or checkbox previously ticked)."""
        return self.is_visible(self.LAYOUT_ID, timeout=timeout)

    def wait_for_prompt(self, timeout=10):
        """Block until the prompt appears."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.LAYOUT_ID)
        ))

    # --- Actions ---

    def tap_continue_to_session(self):
        """Dismiss the prompt and proceed to the player. This is the
        default automation path."""
        self.tap_by_id(self.BUTTON_CONTINUE_ID)
        self.wait_seconds(2)
        log.info("Tapped CONTINUE TO SESSION (dismissed Apple Watch prompt)")

    def tap_setup_apple_watch(self):
        """Tap SET UP YOUR APPLE WATCH. Likely opens further setup flow
        — not validated; tests should generally use tap_continue_to_session()
        instead."""
        self.tap_by_id(self.BUTTON_SETUP_ID)
        self.wait_seconds(2)
        log.info("Tapped SET UP YOUR APPLE WATCH")

    def tap_dont_show_again(self):
        """Tick the 'DON'T SHOW ME THIS AGAIN' checkbox. After this is
        ticked AND CONTINUE is tapped, the prompt won't appear in
        future class starts on this profile."""
        self.tap_by_id(self.CHECKBOX_DONT_SHOW_ID)
        self.wait_seconds(1)
        log.info("Ticked 'DON'T SHOW ME THIS AGAIN'")

    # --- Convenience ---

    def dismiss(self, dont_show_again=False):
        """Dismiss the prompt — common automation flow.
        If dont_show_again=True, ticks the checkbox first so future
        test runs skip this prompt entirely."""
        if dont_show_again:
            self.tap_dont_show_again()
        self.tap_continue_to_session()