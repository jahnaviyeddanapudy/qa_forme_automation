"""StudioTabPage — Studio app's main class browse screen (the STUDIO tab).

Reached by tapping the STUDIO tab on Home. Layout:

  header (always present, from home)
  fragment_vod_nav
    recycler                          ← horizontal sub-tab strip
      text | FEATURED, BOOKMARKED, CUSTOM, WORKOUTS, PROGRAMS, BARRE,
              FITBENCH, GOLF, MIND, PILATES, RECOVERY, SPECIALTY,
              STRENGTH, YOGA, INSTRUCTORS, ...
  filters_container
    scroll_filters
      layout_filters
        text | <chip>                  ← one chip per active filter
                                          (sub-tab + filter selections)
    button_filter | FILTER             ← opens filter overlay
  [layout_tab_description]            ← appears on some sub-tabs (e.g.
                                          WORKOUTS shows "From FORME")
  featured_scroll / content area
    [SECTION] (FEATURED only — has multiple sections)
      text_title (section header)
      text_description
      recycler                         ← class card recycler (grid layout)
        card × N
          image, [text_complete], image_bookmark, view_gradient
          [CPS extras: personal_message_icon, profile_button + ST,
                       text_personal_message]
          text_title
          [text_trainer]               ← optional (Team FORME content
                                          may not have)
          text_detail | "20 MIN • BEGINNER"

  [fragment_no_classes]               ← appears INSTEAD OF the recycler
                                          when an active filter combo
                                          produces zero results
    text "We don't have that class… yet"
    text "We're launching new classes every week..."
    button_reset
      label_start_class | "RESET FILTERS"

PROGRAMS sub-tab cards:
  recycler
    card × N                           ← each card is a Program (or Collection)
      media_container
        image (UUID content-desc)      ← only stable per-card identifier
        [exo_content_frame, exo_subtitles, exo_ad_overlay, exo_overlay]
                                       ← present INSIDE the card while
                                          trailer is playing inline
      button_view_classes | "VIEW CLASSES"
      [button_trailer | "TRAILER"]    ← optional — Programs WITH trailer
                                          vs Collections WITHOUT (per QA spec)
      text_classes      | "12"
      text_completed    | "9"
      label_classes     | "CLASSES"
      label_completed   | "COMPLETED"

PROGRAMS sub-tab scrolling:
  ~10 total programs/collections on the Studio. ~3 visible per viewport.
  Each card has a unique image UUID (content-desc on the image element).
  Use the UUID as the dedup key when scroll-collecting.

NOTE on Studio's grid recycler binding stages:
  Cards visible on the device pass through these stages in order:
    Stage 0: SCAFFOLDING — image + view_gradient only
    Stage 1: BOOKMARK    — adds image_bookmark
    Stage 2: TITLE       — adds text_title (and text_trainer where present)
    Stage 3: DETAIL      — adds text_detail "20 MIN • BEGINNER"
    Stage 4: COMPLETE    — fully visible to user

  For test verification we want ONLY stage 4 cards (fully bound).
  find_all_visible_card_records() requires BOTH title AND detail.

NOTE on grid recycler stabilization:
  After applying a filter, the grid recycler takes ~1-2s to fully
  rebind cards. wait_for_card_grid_to_settle() polls until stable.

NOTE on Programs cards (FEATURED tab):
  Cards in the FEATURED tab's Programs section have a different structure
  (media_container instead of text_title direct child). Tests that need
  a class card should AVOID FEATURED's Programs section.

NOTE on sub-tabs as filters:
  Tapping a sub-tab (FEATURED/BARRE/etc.) creates a chip in
  scroll_filters > layout_filters with that sub-tab's text. ALSO
  tapping a filter option (e.g. "30 MIN") creates a chip. So
  get_active_subtab() and get_all_active_filter_chips() both read
  from layout_filters."""
import time

from surfaces.studio_android.pages.base import StudioBasePage, log
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC


class StudioTabPage(StudioBasePage):
    # --- Element IDs (confirmed from dumps on 2026-04-27 and 2026-05-11) ---
    FRAGMENT_VOD_NAV_ID = "fragment_vod_nav"
    SUBTAB_RECYCLER_ID = "recycler"           # NB: shared with class card recyclers
    SUBTAB_TEXT_ID = "text"                   # text inside each sub-tab item

    FILTERS_CONTAINER_ID = "filters_container"
    SCROLL_FILTERS_ID = "scroll_filters"
    LAYOUT_FILTERS_ID = "layout_filters"
    BUTTON_FILTER_ID = "button_filter"        # text "FILTER"

    # Optional sub-tab description block (appears on some sub-tabs)
    LAYOUT_TAB_DESCRIPTION_ID = "layout_tab_description"
    TEXT_TAB_TITLE_ID = "text_tab_title"
    TEXT_TAB_DESCRIPTION_ID = "text_tab_description"

    # Class cards
    CARD_ID = "card"
    TEXT_TITLE_ID = "text_title"              # both section header AND class title
    TEXT_TRAINER_ID = "text_trainer"
    TEXT_DETAIL_ID = "text_detail"            # "20 MIN • BEGINNER"
    TEXT_DESCRIPTION_ID = "text_description"  # section subtitle (FEATURED only)
    TEXT_COMPLETE_ID = "text_complete"        # "COMPLETED" badge
    IMAGE_BOOKMARK_ID = "image_bookmark"
    IMAGE_ID = "image"

    # CPS-specific elements
    PERSONAL_MESSAGE_ICON_ID = "personal_message_icon"
    TEXT_PERSONAL_MESSAGE_ID = "text_personal_message"

    # No-results state (when filter combo produces zero classes)
    FRAGMENT_NO_CLASSES_ID = "fragment_no_classes"
    BUTTON_RESET_FILTERS_ID = "button_reset"
    LABEL_RESET_FILTERS_ID = "label_start_class"
    NO_CLASSES_HEADLINE_TEXT = "We don't have that class"
    NO_CLASSES_SUBLINE_TEXT = "launching new classes every week"
    RESET_FILTERS_BUTTON_TEXT = "RESET FILTERS"

    # PROGRAMS sub-tab card elements
    MEDIA_CONTAINER_ID = "media_container"
    BUTTON_VIEW_CLASSES_ID = "button_view_classes"
    BUTTON_TRAILER_ID = "button_trailer"
    TEXT_CLASSES_ID = "text_classes"
    TEXT_COMPLETED_ID = "text_completed"
    LABEL_CLASSES_ID = "label_classes"
    LABEL_COMPLETED_ID = "label_completed"

    # ExoPlayer elements (appear inside a Program card during trailer playback)
    EXO_CONTENT_FRAME_ID = "exo_content_frame"
    EXO_SUBTITLES_ID = "exo_subtitles"
    EXO_AD_OVERLAY_ID = "exo_ad_overlay"
    EXO_OVERLAY_ID = "exo_overlay"

    # --- Screen detection ---

    def is_loaded(self, timeout=3):
        return self.is_visible(self.FRAGMENT_VOD_NAV_ID, timeout=timeout)

    def wait_for_studio_tab(self):
        self.wait.until(EC.presence_of_element_located(
            self.by_id(self.FRAGMENT_VOD_NAV_ID)
        ))
        log.info("Studio tab loaded")

    # --- Sub-tab strip ---

    def all_visible_subtabs(self):
        try:
            nav = self.find_by_id(self.FRAGMENT_VOD_NAV_ID)
        except Exception:
            return []
        text_els = nav.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.SUBTAB_TEXT_ID}"
        )
        return [(t.get_attribute("text") or "").strip() for t in text_els
                if (t.get_attribute("text") or "").strip()]

    def tap_subtab(self, name):
        target = name.strip().upper()
        try:
            nav = self.find_by_id(self.FRAGMENT_VOD_NAV_ID)
        except Exception as e:
            raise RuntimeError(f"Studio tab not loaded: {e}")

        text_els = nav.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.SUBTAB_TEXT_ID}"
        )
        for el in text_els:
            text = (el.get_attribute("text") or "").strip().upper()
            if text == target:
                el.click()
                self.wait_seconds(2)
                log.info(f"Tapped sub-tab: {name}")
                return
        visible = self.all_visible_subtabs()
        raise ValueError(
            f"Sub-tab '{name}' not visible in strip. "
            f"Currently visible: {visible}. Scroll the strip and retry."
        )

    def get_active_subtab(self):
        chips = self.get_all_active_filter_chips()
        return chips[0] if chips else None

    def get_all_active_filter_chips(self):
        try:
            layout = self.find_by_id(self.LAYOUT_FILTERS_ID)
        except Exception:
            return []
        chips = layout.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.SUBTAB_TEXT_ID}"
        )
        return [(c.get_attribute("text") or "").strip() for c in chips
                if (c.get_attribute("text") or "").strip()]

    def tap_active_filter_chip(self, chip_text):
        target = chip_text.strip().upper()
        try:
            layout = self.find_by_id(self.LAYOUT_FILTERS_ID)
        except Exception:
            raise RuntimeError("layout_filters not found — no chips to tap")
        chips = layout.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.SUBTAB_TEXT_ID}"
        )
        for c in chips:
            text = (c.get_attribute("text") or "").strip().upper()
            if text == target:
                c.click()
                self.wait_seconds(1)
                log.info(f"Tapped filter chip: {chip_text}")
                return
        visible = self.get_all_active_filter_chips()
        raise ValueError(
            f"Filter chip '{chip_text}' not visible. "
            f"Currently visible chips: {visible}"
        )

    def clear_filter(self, chip_text):
        self.tap_active_filter_chip(chip_text)

    def scroll_subtabs_left(self):
        try:
            nav = self.find_by_id(self.FRAGMENT_VOD_NAV_ID)
            rect = nav.rect
            cy = rect["y"] + rect["height"] // 2
            self.driver.swipe(
                start_x=rect["x"] + rect["width"] - 50,
                start_y=cy,
                end_x=rect["x"] + 50,
                end_y=cy,
                duration=400,
            )
            self.wait_seconds(1)
        except Exception as e:
            log.info(f"Could not scroll sub-tabs left: {e}")

    def scroll_subtabs_to(self, name, max_swipes=5):
        target = name.strip().upper()
        for _ in range(max_swipes):
            visible = [s.upper() for s in self.all_visible_subtabs()]
            if target in visible:
                return True
            self.scroll_subtabs_left()
        return target in [s.upper() for s in self.all_visible_subtabs()]

    def tap_subtab_with_scroll(self, name, max_swipes=5):
        if not self.scroll_subtabs_to(name, max_swipes=max_swipes):
            visible = self.all_visible_subtabs()
            raise ValueError(
                f"Sub-tab '{name}' not found after {max_swipes} swipes. "
                f"Last visible: {visible}"
            )
        self.tap_subtab(name)

    # --- Filter button ---

    def tap_filter_button(self):
        self.tap_by_id(self.BUTTON_FILTER_ID)
        self.wait_seconds(1)
        log.info("Tapped FILTER button")

    # --- Sub-tab description block ---

    def has_tab_description(self):
        return self.is_visible(self.LAYOUT_TAB_DESCRIPTION_ID, timeout=2)

    def get_tab_title(self):
        if not self.has_tab_description():
            return None
        try:
            return self.get_text(self.TEXT_TAB_TITLE_ID)
        except Exception:
            return None

    def get_tab_description(self):
        if not self.has_tab_description():
            return None
        try:
            return self.get_text(self.TEXT_TAB_DESCRIPTION_ID)
        except Exception:
            return None

    # --- Card grid stabilization ---

    def wait_for_card_grid_to_settle(self, max_wait_seconds=4,
                                     poll_interval=0.5):
        elapsed = 0.0
        last_count = -1
        stable_iterations = 0
        REQUIRED_STABLE = 2

        while elapsed < max_wait_seconds:
            current_count = sum(
                1 for r in self._raw_card_records()
                if r["title"] and r["detail"]
            )
            if current_count == last_count:
                stable_iterations += 1
                if stable_iterations >= REQUIRED_STABLE:
                    return current_count
            else:
                stable_iterations = 0
                last_count = current_count
            time.sleep(poll_interval)
            elapsed += poll_interval

        return last_count if last_count >= 0 else 0

    # --- Class card iteration ---

    def get_card_count(self):
        return len(self.find_all_by_id(self.CARD_ID))

    def get_bound_card_count(self):
        return sum(1 for r in self._raw_card_records()
                   if r["title"] and r["detail"])

    def _raw_card_records(self):
        records = []
        cards = self.find_all_by_id(self.CARD_ID)
        for card in cards:
            title = ""
            detail = ""
            trainer = ""
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
            records.append({
                "title": title,
                "detail": detail,
                "trainer": trainer,
            })
        return records

    def find_all_visible_card_records(self):
        return [r for r in self._raw_card_records()
                if r["title"] and r["detail"]]

    def find_all_class_titles(self):
        titles = []
        for title_el in self.find_all_by_id(self.TEXT_TITLE_ID):
            try:
                title_el.find_element(
                    AppiumBy.XPATH,
                    f"./ancestor::*[@resource-id='{self.APP_PACKAGE}:id/{self.CARD_ID}'][1]",
                )
                t = title_el.get_attribute("text") or ""
                if t:
                    titles.append(t)
            except Exception:
                pass
        return titles

    def find_all_class_titles_fallback(self):
        return [r["title"] for r in self.find_all_visible_card_records()]

    def find_all_section_headers(self):
        headers = []
        for title_el in self.find_all_by_id(self.TEXT_TITLE_ID):
            try:
                title_el.find_element(
                    AppiumBy.XPATH,
                    f"./ancestor::*[@resource-id='{self.APP_PACKAGE}:id/{self.CARD_ID}'][1]",
                )
            except Exception:
                t = title_el.get_attribute("text") or ""
                if t:
                    headers.append(t)
        return headers

    def find_all_class_trainers(self):
        return [r["trainer"] for r in self.find_all_visible_card_records()
                if r["trainer"]]

    def find_all_class_details(self):
        return [r["detail"] for r in self.find_all_visible_card_records()]

    def find_completed_count(self):
        return len(self.find_all_by_id(self.TEXT_COMPLETE_ID))

    def is_card_completed(self, card_index):
        cards = self.find_all_by_id(self.CARD_ID)
        if card_index >= len(cards):
            raise IndexError(
                f"Card index {card_index} out of range — only "
                f"{len(cards)} cards visible"
            )
        card = cards[card_index]
        completed_els = card.find_elements(
            AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.TEXT_COMPLETE_ID}"
        )
        return len(completed_els) > 0

    # --- Tapping cards ---

    def tap_card_by_index(self, index):
        cards = self.find_all_by_id(self.CARD_ID)
        if index >= len(cards):
            raise IndexError(
                f"Card index {index} out of range — only {len(cards)} "
                f"cards visible"
            )
        title = ""
        try:
            title_el = cards[index].find_element(
                AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.TEXT_TITLE_ID}"
            )
            title = title_el.get_attribute("text") or ""
        except Exception:
            pass
        cards[index].click()
        log.info(f"Tapped card [{index}]: {title or '<no title>'}")

    def tap_class_by_title(self, title):
        target = title.strip().upper()
        for i, t in enumerate(self.find_all_class_titles_fallback()):
            if t.strip().upper() == target:
                self.tap_card_by_index(i)
                return
        visible = self.find_all_class_titles_fallback()
        raise ValueError(
            f"Class '{title}' not found. Visible class titles: {visible}"
        )

    def tap_first_non_completed_card(self):
        cards = self.find_all_by_id(self.CARD_ID)
        for i, card in enumerate(cards):
            completed = card.find_elements(
                AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.TEXT_COMPLETE_ID}"
            )
            if not completed:
                self.tap_card_by_index(i)
                return
        raise RuntimeError(
            f"All {len(cards)} visible cards are COMPLETED. Either "
            f"scroll further to find a non-completed card, or use a "
            f"different sub-tab."
        )

    # --- Scrolling within content area ---

    def scroll_content_down(self):
        size = self.driver.get_window_size()
        self.driver.swipe(
            start_x=size["width"] // 2,
            start_y=int(size["height"] * 0.7),
            end_x=size["width"] // 2,
            end_y=int(size["height"] * 0.3),
            duration=400,
        )
        self.wait_seconds(1)

    def scroll_to_class(self, title, max_scrolls=10):
        target = title.strip().upper()
        for _ in range(max_scrolls):
            if any(t.strip().upper() == target
                   for t in self.find_all_class_titles_fallback()):
                return True
            self.scroll_content_down()
        return any(t.strip().upper() == target
                   for t in self.find_all_class_titles_fallback())

    def scroll_to_section(self, section_name, max_scrolls=10):
        target = section_name.strip()
        for _ in range(max_scrolls):
            if any(h.strip() == target
                   for h in self.find_all_section_headers()):
                return True
            self.scroll_content_down()
        return any(h.strip() == target
                   for h in self.find_all_section_headers())

    # --- No-results state (filter combo produces zero classes) ---

    def is_no_results_state(self, timeout=2):
        return self.is_visible(self.FRAGMENT_NO_CLASSES_ID, timeout=timeout)

    def get_no_results_messages(self):
        try:
            fragment = self.find_by_id(self.FRAGMENT_NO_CLASSES_ID)
        except Exception:
            return []
        all_text_els = fragment.find_elements(AppiumBy.XPATH, ".//*[@text]")
        messages = []
        for el in all_text_els:
            text = (el.get_attribute("text") or "").strip()
            if text and text != self.RESET_FILTERS_BUTTON_TEXT:
                messages.append(text)
        return messages

    def tap_reset_filters(self):
        if not self.is_no_results_state(timeout=2):
            raise RuntimeError(
                f"tap_reset_filters() called but no-results state isn't "
                f"visible. fragment_no_classes (the empty-state container) "
                f"isn't on screen — there's no RESET FILTERS button to tap."
            )
        self.tap_by_id(self.BUTTON_RESET_FILTERS_ID)
        self.wait_seconds(1)
        log.info("Tapped RESET FILTERS button")

    # --- PROGRAMS sub-tab card iteration (no text_title — UUID-based) ---

    def find_program_cards(self):
        """Return the list of Program card WebElements currently in the
        recycler tree. Positional, no dedup. References go stale after
        scrolling."""
        return self.find_all_by_id(self.CARD_ID)

    def find_program_cards_with_trailer(self):
        """Return Program cards in the CURRENT viewport that have
        button_trailer. Does NOT scroll — see
        scroll_to_first_program_with_trailer() for the scrolling version."""
        result = []
        for card in self.find_program_cards():
            trailer_els = card.find_elements(
                AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.BUTTON_TRAILER_ID}"
            )
            if trailer_els:
                result.append(card)
        return result

    def find_program_cards_without_trailer(self):
        """Return Program cards in the CURRENT viewport that DON'T have
        button_trailer. Filters out partial recycler cells by requiring
        button_view_classes. Does NOT scroll."""
        result = []
        for card in self.find_program_cards():
            trailer_els = card.find_elements(
                AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.BUTTON_TRAILER_ID}"
            )
            view_classes_els = card.find_elements(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.BUTTON_VIEW_CLASSES_ID}"
            )
            if not trailer_els and view_classes_els:
                result.append(card)
        return result

    def tap_view_classes_on_card(self, card):
        """Tap VIEW CLASSES button on a Program card. Opens detail page."""
        try:
            btn = card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.BUTTON_VIEW_CLASSES_ID}"
            )
        except Exception as e:
            raise ValueError(
                f"Card has no button_view_classes child — likely a "
                f"partially-bound recycler cell. Underlying error: {e}"
            )
        btn.click()
        self.wait_seconds(2)
        log.info("Tapped VIEW CLASSES on Program card")

    def tap_trailer_on_card(self, card):
        """Tap TRAILER button on a Program card. Starts inline trailer
        playback. Raises ValueError if card has no button_trailer."""
        try:
            btn = card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.BUTTON_TRAILER_ID}"
            )
        except Exception as e:
            raise ValueError(
                f"Card has no button_trailer — this is a Collection, "
                f"not a Program with trailer. Underlying error: {e}"
            )
        btn.click()
        self.wait_seconds(2)  # let ExoPlayer initialize
        log.info("Tapped TRAILER on Program card")

    def is_trailer_playing_on_card(self, card):
        """True if the card has exo_content_frame visible inside it.
        Indicates inline trailer is active in the card's media_container."""
        try:
            card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.EXO_CONTENT_FRAME_ID}"
            )
            return True
        except Exception:
            return False

    def dismiss_trailer_on_card(self, card):
        """Stop a playing trailer by tapping the player surface
        (exo_content_frame) on the given card. Per QA confirmation,
        tapping the player itself stops playback."""
        try:
            exo = card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.EXO_CONTENT_FRAME_ID}"
            )
        except Exception as e:
            raise RuntimeError(
                f"No trailer playing on this card — exo_content_frame "
                f"not present. Nothing to dismiss. Underlying error: {e}"
            )
        exo.click()
        self.wait_seconds(2)
        log.info("Tapped trailer player to dismiss")

    def get_program_card_class_counts(self, card):
        """Return (total, completed) ints from a Program card."""
        try:
            total = int(card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_CLASSES_ID}"
            ).get_attribute("text") or "0")
        except Exception:
            total = None
        try:
            done = int(card.find_element(
                AppiumBy.ID,
                f"{self.APP_PACKAGE}:id/{self.TEXT_COMPLETED_ID}"
            ).get_attribute("text") or "0")
        except Exception:
            done = None
        return (total, done)

    # --- PROGRAMS sub-tab scrolling helpers (NEW) ---

    def _get_image_uuid_from_card(self, card):
        """Return the content-desc of the image element inside a Program
        card (a UUID like '409b838d-1ade-4845-b7ce-f7186206c361'). Used
        as the only stable per-card identifier on PROGRAMS sub-tab since
        cards have no title element.

        Returns empty string if image element or its content-desc is
        not present (partially-bound recycler cell)."""
        try:
            img = card.find_element(
                AppiumBy.ID, f"{self.APP_PACKAGE}:id/{self.IMAGE_ID}"
            )
            return img.get_attribute("contentDescription") or ""
        except Exception:
            return ""

    def scroll_to_first_program_with_trailer(self, max_scrolls=5):
        """Scroll the PROGRAMS sub-tab progressively downward until a
        Program card with button_trailer appears in the current viewport.

        Returns a fresh WebElement reference to that card (suitable for
        immediate interaction — no staleness), or None if no
        trailer-having card found after `max_scrolls` scrolls.

        Uses image UUID dedup to detect "end of list" — if a scroll
        produces no new card UUIDs, we've hit the bottom. Bails early
        in that case rather than wasting scrolls.

        NB: Studio has ~10 programs/collections total, so default
        max_scrolls=5 should be enough (each viewport shows ~2-3 cards).
        """
        seen_uuids = set()
        scrolls_done = 0

        while scrolls_done <= max_scrolls:
            # Check current viewport first — does any card have trailer?
            current_viewport_trailer_cards = self.find_program_cards_with_trailer()
            if current_viewport_trailer_cards:
                log.info(
                    f"Found trailer-capable card after {scrolls_done} scroll(s)"
                )
                return current_viewport_trailer_cards[0]

            # No trailer in current viewport — collect UUIDs to track progress
            new_uuids_this_pass = set()
            for card in self.find_program_cards():
                uuid = self._get_image_uuid_from_card(card)
                if uuid:
                    new_uuids_this_pass.add(uuid)

            # If we've seen all these UUIDs already, we're stuck at end of list
            if new_uuids_this_pass and new_uuids_this_pass.issubset(seen_uuids):
                log.info(
                    f"Reached end of PROGRAMS list after {scrolls_done} "
                    f"scroll(s) — {len(seen_uuids)} unique cards seen, "
                    f"none with trailer"
                )
                return None

            seen_uuids.update(new_uuids_this_pass)

            # Not at end yet, and no trailer found — scroll and retry
            if scrolls_done == max_scrolls:
                log.info(
                    f"Hit max_scrolls={max_scrolls} without finding "
                    f"trailer-capable card. Seen {len(seen_uuids)} unique "
                    f"cards."
                )
                return None

            self.scroll_content_down()
            scrolls_done += 1

        return None

    def scroll_collect_all_program_cards(self, max_scrolls=5):
        """Scroll through the PROGRAMS sub-tab and aggregate info about
        every unique Program card. Dedupes by image UUID.

        Returns list of dicts (in scroll order — first-seen first):
          [
            {
              'uuid':         str   # image content-desc UUID
              'has_trailer':  bool  # whether button_trailer exists
              'total':        int   # text_classes
              'completed':    int   # text_completed
            },
            ...
          ]

        Stops scrolling early when no new UUIDs appear (end of list).
        Hard caps at max_scrolls.

        Use this for tests that need a complete count of programs
        (e.g. 6607's '≥1 Collection exists' check, or a future
        '≥2 Programs have trailers' assertion)."""
        seen = {}  # uuid -> record
        scrolls_done = 0
        stale_scroll_count = 0  # how many consecutive scrolls produced no new uuids

        while scrolls_done <= max_scrolls:
            new_this_pass = 0
            for card in self.find_program_cards():
                uuid = self._get_image_uuid_from_card(card)
                if not uuid or uuid in seen:
                    continue

                # New card — must also have button_view_classes (filters
                # out partially-bound recycler cells)
                view_classes_els = card.find_elements(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.BUTTON_VIEW_CLASSES_ID}"
                )
                if not view_classes_els:
                    continue

                trailer_els = card.find_elements(
                    AppiumBy.ID,
                    f"{self.APP_PACKAGE}:id/{self.BUTTON_TRAILER_ID}"
                )
                total, completed = self.get_program_card_class_counts(card)

                seen[uuid] = {
                    "uuid": uuid,
                    "has_trailer": bool(trailer_els),
                    "total": total,
                    "completed": completed,
                }
                new_this_pass += 1

            if new_this_pass == 0:
                stale_scroll_count += 1
            else:
                stale_scroll_count = 0

            # Stop if no new cards seen in last 2 scrolls (end of list)
            if stale_scroll_count >= 2:
                log.info(
                    f"Reached end of PROGRAMS list after {scrolls_done} "
                    f"scrolls — {len(seen)} unique cards collected"
                )
                break

            if scrolls_done == max_scrolls:
                log.info(
                    f"Hit max_scrolls={max_scrolls} during program "
                    f"collection — {len(seen)} unique cards collected"
                )
                break

            self.scroll_content_down()
            scrolls_done += 1

        return list(seen.values())