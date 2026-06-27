"""ProgramDetailPage — class list shown after tapping a Program card.

Reached from StudioTabPage by tapping the VIEW CLASSES button on a
Program card in the PROGRAMS sub-tab.

Confirmed from dump on 2026-05-11:

  nav_host_fragment
    layout_header
      image_header                    ← banner image at top
      button_close                    ← X to dismiss (no text/content-desc)
    filters_container                 ← filter still available on detail
      scroll_filters
      button_filter | "FILTER"
    layout_info                       ← program metadata block
      text_description                ← multi-sentence about-the-program text
      text_classes      | "15"        ← total class count
      text_completed    | "5"         ← user's completed count
      label_classes     | "CLASSES"
      label_completed   | "COMPLETED"
    recycler                          ← list of classes within the program
      card × N
        image (UUID)
        [text_complete | "COMPLETED"] ← only on classes the user has done
        image_bookmark
        view_gradient
        text_title       | "AMPLIFIED: HEART CHAKRA"
        text_trainer     | "Donovan M"
        text_detail      | "30 MIN • ALL LEVELS"

GAP — no program title element on this page:
  The Program detail page does NOT expose a text element containing the
  program's name. Only text_description (about the program) is present.
  Tests that need to verify which program is open must rely on
  description content or image_header content-desc (also absent in
  current build). This is flagged in STUDIO-XXXX (Program title element
  request) — file follow-up JIRA if not already done.
"""
from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class ProgramDetailPage(StudioBasePage):
    # --- Element IDs (confirmed from dump 2026-05-11) ---
    LAYOUT_HEADER_ID = "layout_header"
    IMAGE_HEADER_ID = "image_header"
    BUTTON_CLOSE_ID = "button_close"

    LAYOUT_INFO_ID = "layout_info"
    TEXT_DESCRIPTION_ID = "text_description"
    TEXT_CLASSES_ID = "text_classes"
    TEXT_COMPLETED_ID = "text_completed"
    LABEL_CLASSES_ID = "label_classes"
    LABEL_COMPLETED_ID = "label_completed"

    BUTTON_FILTER_ID = "button_filter"

    # Class card structure (same as elsewhere — reuses these ids)
    CARD_ID = "card"
    TEXT_TITLE_ID = "text_title"
    TEXT_TRAINER_ID = "text_trainer"
    TEXT_DETAIL_ID = "text_detail"
    TEXT_COMPLETE_ID = "text_complete"
    IMAGE_BOOKMARK_ID = "image_bookmark"

    # --- Screen detection ---

    def is_loaded(self, timeout=3):
        """Non-blocking check: is the Program detail page up?
        Anchored on layout_header (unique to this screen)."""
        return self.is_visible(self.LAYOUT_HEADER_ID, timeout=timeout)

    def wait_for_loaded(self, timeout=10):
        """Block until the Program detail page renders. Verified by
        presence of layout_header AND layout_info (the two structural
        markers)."""
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.LAYOUT_HEADER_ID)
        ))
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.LAYOUT_INFO_ID)
        ))
        log.info("Program detail page loaded")

    # --- Metadata ---

    def get_description(self):
        """Return the program description text. Multi-sentence
        about-the-program copy."""
        return self.get_text(self.TEXT_DESCRIPTION_ID)

    def get_class_counts(self):
        """Return (total_classes, completed_classes) as a tuple of ints.

        Both come from layout_info — total from text_classes, completed
        from text_completed. Returns (None, None) for either if the
        element is missing or unparseable."""
        try:
            total = int(self.get_text(self.TEXT_CLASSES_ID))
        except Exception:
            total = None
        try:
            done = int(self.get_text(self.TEXT_COMPLETED_ID))
        except Exception:
            done = None
        return (total, done)

    # --- Class list within the program ---

    def _raw_class_card_records(self):
        """Internal: walk every card in the recycler and read its
        child text fields. Returns ALL cards including unbound and
        partially-bound ones (similar pattern to StudioTabPage)."""
        records = []
        cards = self.find_all_by_id(self.CARD_ID)
        for card in cards:
            title = ""
            detail = ""
            trainer = ""
            completed = False
            try:
                t_el = card.find_element(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.TEXT_TITLE_ID}"
                )
                title = (t_el.get_attribute("text") or "").strip()
            except Exception:
                pass
            try:
                d_el = card.find_element(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.TEXT_DETAIL_ID}"
                )
                detail = (d_el.get_attribute("text") or "").strip()
            except Exception:
                pass
            try:
                tr_el = card.find_element(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.TEXT_TRAINER_ID}"
                )
                trainer = (tr_el.get_attribute("text") or "").strip()
            except Exception:
                pass
            try:
                card.find_element(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.TEXT_COMPLETE_ID}"
                )
                completed = True
            except Exception:
                pass
            records.append({
                "title": title,
                "detail": detail,
                "trainer": trainer,
                "completed": completed,
            })
        return records

    def find_all_visible_class_records(self):
        """Return list of dicts for FULLY-BOUND class cards (with both
        title and detail) inside the program. Each record:
          {
            'title':     str
            'detail':    str   (e.g. '30 MIN • ALL LEVELS')
            'trainer':   str
            'completed': bool
          }

        Skips partially-bound recycler cells the same way as
        StudioTabPage's find_all_visible_card_records()."""
        return [r for r in self._raw_class_card_records()
                if r["title"] and r["detail"]]

    def get_visible_class_count(self):
        """Number of fully-bound class cards currently rendered on the
        screen. NOT necessarily the total — may need to scroll to see
        the rest."""
        return len(self.find_all_visible_class_records())

    # --- Close / dismiss ---

    def close(self):
        """Tap the close button (X) at the top-left to dismiss the
        Program detail page and return to the PROGRAMS sub-tab.

        button_close has no text or content-desc — it's identified
        purely by resource-id."""
        if not self.is_loaded(timeout=2):
            raise RuntimeError(
                "close() called but Program detail page is not loaded — "
                "layout_header not visible. Nothing to close."
            )
        self.tap_by_id(self.BUTTON_CLOSE_ID)
        self.wait_seconds(2)
        log.info("Closed Program detail page")