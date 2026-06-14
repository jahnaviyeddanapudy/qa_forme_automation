import time
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from pages.base_page import BasePage


class StudioPage(BasePage):

    # In-class controls (fragment_inclass_controls.xml)
    START_BTN = "button_start"
    PLAY_PAUSE_BTN = "button_play_pause"
    SKIP_FWD_BTN = "button_skip_forward_movement"
    SKIP_BACK_BTN = "button_skip_back_movement"
    END_CLASS_BTN = "button_end_class"
    MUSIC_BTN = "button_music"
    SWIPE_UP_LABEL = "label_swipe_up"

    # HRM dialog (dialog_heart_rate_monitor.xml)
    # button_close calls proceed() → proceedToClassPreview() on dismiss
    HRM_CONNECT_BTN = "button_connect"
    HRM_CLOSE_BTN = "button_close"
    HRM_DONT_SHOW_CHECKBOX = "checkbox_dont_show"

    # CPS onboarding dialog (dialog_cps_onboarding.xml)
    CPS_ONBOARDING_SKIP_BTN = "button_skip"

    # Bookmarks (item_vod_card.xml / dialog_class_preview.xml)
    VOD_BOOKMARK_ICON = "image_bookmark"
    PREVIEW_BOOKMARK_ICON = "button_bookmark"

    # Workouts list (fragment_browse_workouts.xml)
    FILTER_BTN = "button_filter"

    # Music dialog (dialog_select_music.xml)
    MUSIC_YOUTUBE_BTN = "button_youtube_music"
    MUSIC_APPLE_BTN = "button_apple_music"
    MUSIC_CLOSE_BTN = "button_close"
    MUSIC_LABEL = "label_title"

    # VOD / item list
    ITEM_TITLE_ID = f"com.formelife.member:id/text_title"
    # item_vod_card.xml CardView — unique to actual session tiles, not section headers
    SESSION_CARD_ID = f"com.formelife.member:id/card"

    def _dismiss_post_session_screens_if_present(self):
        # PostClassSurveyDialog: button_submit is unique to this screen.
        # button_close calls dismiss() → returns to ClassSummaryDialog.
        if self.is_displayed("button_submit", timeout=2):
            self.tap("button_close")
            self.wait_seconds(1)
        # ClassSummaryDialog: text_active_time is unique to this screen.
        # button_close calls requireActivity().finish() → returns to main nav.
        if self.is_displayed("text_active_time", timeout=2):
            self.tap("button_close")
            self.wait_seconds(2)

    def navigate_to_studio(self):
        self._dismiss_post_session_screens_if_present()
        self.ensure_logged_in()
        self.go_to_studio_tab()

    def _scroll_content_to_top(self):
        """Swipe down until the nav bar reappears at the top of the screen."""
        for _ in range(8):
            if self.is_displayed("fragment_vod_nav", timeout=1):
                return
            self.swipe_down()
            self.wait_seconds(0.3)

    def _check_bookmark_icon_scrolling_to_bottom(self):
        """Scroll from current position to the bottom, returning True if any
        bookmark icon is found on any VOD card along the way."""
        # If _tap_nav_tab_by_text accidentally matched a class title and opened a
        # preview dialog, close it so we are back on the card list.
        if self.is_displayed(self.START_BTN, timeout=2):
            self.go_back()
            self.wait_seconds(1)
        for _ in range(15):
            try:
                self._find_bookmark_icon_on_vod_card()
                return True
            except AssertionError:
                pass
            self.swipe_up()
            self.wait_seconds(0.5)
        return False

    def _tap_nav_tab_by_text(self, text):
        """Tap a nav tab whose label contains *text*, constraining the search to
        fragment_vod_nav so a class title in the content area is never matched.
        Tries both UiSelector (accessibility tree) and XPath (full view hierarchy)
        because importantForAccessibility=noHideDescendants hides the TextViews on
        some Android versions.  Returns True on success."""
        nav_id = f"{self.APP_PACKAGE}:id/fragment_vod_nav"
        # Attempt 1 — UiSelector scrollIntoView scoped to the nav RecyclerView.
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                f'.setAsHorizontalList()'
                f'.scrollIntoView(new UiSelector().textContains("{text}"))',
            )
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().resourceId("{nav_id}").childSelector('
                f'new UiSelector().textContains("{text}"))',
            ).click()
            self.wait_seconds(1)
            return True
        except Exception:
            pass
        # Attempt 2 — XPath searches the full view hierarchy (bypasses
        # importantForAccessibility restrictions), constrained to the nav element.
        for xpath_text in (text, text.upper(), text.capitalize()):
            try:
                el = self.driver.find_element(
                    AppiumBy.XPATH,
                    f'//*[@resource-id="{nav_id}"]//*[@text="{xpath_text}"]',
                )
                loc = el.location
                sz = el.size
                self.driver.execute_script("mobile: clickGesture", {
                    "x": loc["x"] + sz["width"] // 2,
                    "y": loc["y"] + sz["height"] // 2,
                })
                self.wait_seconds(1)
                return True
            except Exception:
                continue
        return False

    def select_vod_category(self):
        nav_id = f"{self.APP_PACKAGE}:id/fragment_vod_nav"
        WebDriverWait(self.driver, self.DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((AppiumBy.ID, nav_id))
        )

        # APPROACH 1 — mirror the Programs-style nav used in tap_bookmark_icon_on_program_class:
        # reset the nav bar to the beginning first, then tap Barre by text with a
        # getChildByInstance(index=2) fallback (Featured=0, Bookmarked=1, Barre=2).
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                f'.setAsHorizontalList().scrollToBeginning(10)',
            )
        except Exception:
            pass
        self.wait_seconds(0.5)
        navigated = self._tap_nav_tab_by_text("Barre") or self._tap_nav_tab_by_text("BARRE")
        if not navigated:
            try:
                item = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                    f'.setAsHorizontalList()'
                    f'.getChildByInstance(new UiSelector().clickable(true), 2)',
                )
                item.click()
                navigated = True
            except Exception:
                pass
        if navigated:
            self.wait_seconds(1)
            self._scroll_content_to_top()
            if self._check_bookmark_icon_scrolling_to_bottom():
                return

        # APPROACH 2 — text-based fallback for other categories if Barre was not found.
        for cat in ("Mind", "MIND", "Pilates", "PILATES",
                    "Strength", "STRENGTH", "Yoga", "YOGA", "Recovery", "RECOVERY",
                    "Specialty", "SPECIALTY", "Workouts", "WORKOUTS"):
            if self._tap_nav_tab_by_text(cat):
                self._scroll_content_to_top()
                if self._check_bookmark_icon_scrolling_to_bottom():
                    return

        # APPROACH 2 — position-based fallback.
        # Re-query elements fresh before EACH individual click to avoid
        # StaleElementReferenceException (elements go stale after swipe_up calls).
        # Swipe the nav bar using driver.swipe() on its own bounds (same approach
        # used in base_page for content; avoids ViewPager interception by keeping
        # the gesture within the nav's y-bounds).
        nav = self.driver.find_element(AppiumBy.ID, nav_id)
        nav_rect = nav.rect
        nav_mid_y = nav_rect["y"] + nav_rect["height"] // 2
        tapped_xs = set()

        for _ in range(30):
            self._scroll_content_to_top()

            # Fresh query every outer loop — avoids stale refs from prior swipe_up calls.
            def _fresh_nav_items():
                items = []
                for el in self.driver.find_elements(
                    AppiumBy.XPATH,
                    '//*[contains(@resource-id, "fragment_vod_nav")]//*[@clickable="true"]',
                ):
                    try:
                        x = el.location.get("x", -1)
                        if x >= 0:
                            items.append((x, el))
                    except Exception:
                        continue
                return sorted(items, key=lambda t: t[0])

            items = _fresh_nav_items()
            untapped = [(x, el) for x, el in items
                        if not any(abs(x - tx) < 40 for tx in tapped_xs)]

            if not untapped:
                # All visible tabs already tried — scroll nav left to reveal more.
                try:
                    nav = self.driver.find_element(AppiumBy.ID, nav_id)
                    nav_rect = nav.rect
                    nav_mid_y = nav_rect["y"] + nav_rect["height"] // 2
                    self.driver.swipe(
                        nav_rect["x"] + int(nav_rect["width"] * 0.8),
                        nav_mid_y,
                        nav_rect["x"] + int(nav_rect["width"] * 0.2),
                        nav_mid_y,
                        600,
                    )
                except Exception:
                    break
                self.wait_seconds(0.5)
                continue

            for target_x, _ in untapped:
                tapped_xs.add(target_x)
                self._scroll_content_to_top()

                # Re-find element at target_x with a fresh query (not the stale ref).
                fresh = [(x, el) for x, el in _fresh_nav_items()
                         if abs(x - target_x) < 40]
                if not fresh:
                    continue
                try:
                    fresh[0][1].click()
                except Exception:
                    continue
                self.wait_seconds(1)

                self._scroll_content_to_top()
                if self._check_bookmark_icon_scrolling_to_bottom():
                    return

        raise AssertionError("No VOD category with bookmark icons found in Studio navigation")

    def navigate_to_your_plan(self):
        self._dismiss_post_session_screens_if_present()
        self.ensure_logged_in()
        self.go_to_plan_tab()

    # --- Custom Sessions ---

    def open_custom_planned_sessions(self):
        # fragment_vod_nav (StudioNavigationFragment) is only present in fragment_browse_workouts.xml
        # (Studio tab). Your Plan tab does not have it. Use it to pick the correct path.
        if self.is_displayed("fragment_vod_nav", timeout=2):
            # Studio context: tap the "Custom" category pill to filter the workout list.
            try:
                self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiScrollable(new UiSelector().scrollable(true))'
                    '.scrollIntoView(new UiSelector().textContains("Custom"))',
                )
                self.tap_text_contains("Custom", timeout=5)
                return
            except Exception:
                raise AssertionError(
                    "No 'Custom' category found in Studio — "
                    "ensure a CPS is scheduled for the test account"
                )
        # Your Plan context: CPS cards expose personal_message_icon (visible() only for
        # SCHEDULED_WORKOUT CPS entries in WeeklyScheduleAdapter). The icon has no onClick,
        # so the touch propagates to root ConstraintLayout which holds the card click handler.
        full_icon_id = f"{self.APP_PACKAGE}:id/personal_message_icon"
        try:
            icon = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().scrollable(true))'
                f'.scrollIntoView(new UiSelector().resourceId("{full_icon_id}"))',
            )
            loc = icon.location
            sz = icon.size
            self.driver.execute_script("mobile: clickGesture", {
                "x": loc["x"] + sz["width"] // 2,
                "y": loc["y"] + sz["height"] // 2,
            })
            return
        except Exception:
            raise AssertionError(
                "No CPS card found in Your Plan — "
                "ensure a CPS is scheduled for the test account"
            )

    def select_first_cps(self):
        # text_title also matches section headers (which call showDetails, not navigateClassPreview).
        # card (CardView in item_vod_card.xml) is unique to actual session tiles — click it
        # to bubble the touch up to root.setOnClickListener → setVODCardClicked → ClassPreview.
        WebDriverWait(self.driver, self.DEFAULT_TIMEOUT).until(
            lambda d: d.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
        )
        cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
        if not cards:
            raise AssertionError("No CPS session tiles found in the list")
        cards[0].click()

    def _dismiss_hrm_dialog_if_present(self):
        """Close the HRM dialog so it proceeds to ClassPreviewDialog.

        HeartRateMonitorDialog.buttonClose calls proceed() → proceedToClassPreview().
        button_connect is HRM-specific (5s covers the 2s loading delay in the dialog).
        Checking checkbox_dont_show skips this prompt on future test runs.
        """
        if not self.is_displayed(self.HRM_CONNECT_BTN, timeout=5):
            return
        if self.is_displayed(self.HRM_DONT_SHOW_CHECKBOX, timeout=2):
            self.tap(self.HRM_DONT_SHOW_CHECKBOX)
        self.tap(self.HRM_CLOSE_BTN)

    def tap_start_class(self):
        self._dismiss_hrm_dialog_if_present()
        # Tap button_start on ClassPreviewDialog
        if self.is_displayed(self.START_BTN, timeout=10):
            self.tap(self.START_BTN)
        # SelectMusicDialog appears next (shown from BrowseActivity, so button_start IS visible).
        # Tap button_start again to skip music selection and start the class.
        if self.is_displayed(self.MUSIC_YOUTUBE_BTN, timeout=10):
            self.tap(self.START_BTN)
        # CPS onboarding tutorial (dialog_cps_onboarding.xml) — skip it so the session begins.
        if self.is_displayed(self.CPS_ONBOARDING_SKIP_BTN, timeout=10):
            self.tap(self.CPS_ONBOARDING_SKIP_BTN)

    def tap_screen_during_session(self):
        # fragment_block_preview (BlockPreviewFragment) shows for 12 s when entering a new
        # CPS block. While visible it blocks InClassActivity.tap() via the guard condition
        # !binding.fragmentBlockPreview.isVisible. Wait up to 15 s for it to auto-dismiss.
        block_id = f"{self.APP_PACKAGE}:id/fragment_block_preview"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            els = self.driver.find_elements(AppiumBy.ID, block_id)
            if not els:
                break
            try:
                if not els[0].is_displayed():
                    break
            except StaleElementReferenceException:
                break  # fragment removed from hierarchy — no longer blocking
            self.wait_seconds(1)
        # mobile: clickGesture uses UiAutomator2's UiDevice.click() which injects
        # real MotionEvents, ensuring GestureDetector.onSingleTapUp fires on binding.root.
        # Try y=20%, 40%, 60% — one position should land in the transparent area
        # above the CPS bottom sheet and not be consumed by a child view.
        size = self.driver.get_window_size()
        cx = size["width"] // 2
        # button_end_class is a Button with text — reliably reported by UiAutomator2.
        # Use it (not button_play_pause ImageButton) to detect controls visibility.
        end_btn_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        for y_frac in (0.2, 0.4, 0.6):
            self.driver.execute_script("mobile: clickGesture", {
                "x": cx,
                "y": int(size["height"] * y_frac)
            })
            # Poll with fresh queries to handle StaleElementReferenceException.
            # A stale pass leads to a second tap that hits the controls overlay
            # (now visible) and calls setControlsVisibilityChanged(false), hiding them.
            for _ in range(3):
                self.wait_seconds(0.5)
                els = self.driver.find_elements(AppiumBy.ID, end_btn_id)
                try:
                    if els and els[0].size.get("width", 0) > 0:
                        return  # controls confirmed visible (VOD)
                    if not els:
                        # CPS: button_end_class has no resource ID so the list is
                        # always empty. Return after the FIRST tap (y=20%) to avoid
                        # y=40% which lands on the pause button (bounds y≈894–990)
                        # and would accidentally toggle the session.
                        return
                    break  # size=0; try next tap position (VOD)
                except StaleElementReferenceException:
                    pass  # element transitioning — re-query on next poll

    # Horizontal screen-fraction fallback for ImageButtons that are not accessible via ID.
    # skip_back/skip_forward are constrained to the left/right edges of the controls overlay.
    # Fractions are approximate (valid for screens 320dp–430dp wide).
    _CONTROL_BTN_X_FRACTION = {
        "button_skip_back_movement": 0.12,
        "button_skip_forward_movement": 0.88,
    }

    def _dismiss_controls_if_visible(self):
        """Tap transparent area of the controls overlay to hide it (triggers root onClick)."""
        end_btn_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        try:
            end_els = self.driver.find_elements(AppiumBy.ID, end_btn_id)
            if not (end_els and end_els[0].size.get("width", 0) > 0):
                return  # controls already gone
        except StaleElementReferenceException:
            return
        size = self.driver.get_window_size()
        # y=30%: below button_end_class (top), above center-row buttons — transparent area
        self.driver.execute_script("mobile: clickGesture", {
            "x": size["width"] // 2,
            "y": int(size["height"] * 0.3),
        })
        self.wait_seconds(1)

    def _tap_control_btn(self, resource_id):
        # Detect controls visibility via button_end_class (has a resource ID in VOD).
        # In CPS the END SESSION button is a ViewGroup/TextView with no resource ID,
        # so controls_up stays False — fall back to button_play_pause as a secondary
        # signal (it is an ImageButton but its resource ID IS present in the CPS layout).
        full_id = f"{self.APP_PACKAGE}:id/{resource_id}"
        end_btn_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        pp_id = f"{self.APP_PACKAGE}:id/button_play_pause"
        for _ in range(3):
            controls_up = False
            try:
                end_els = self.driver.find_elements(AppiumBy.ID, end_btn_id)
                controls_up = bool(end_els and end_els[0].size.get("width", 0) > 0)
            except StaleElementReferenceException:
                pass
            # CPS fallback: check Pause/Resume button visibility when END SESSION
            # cannot be detected by resource ID.
            if not controls_up:
                try:
                    pp_els = self.driver.find_elements(AppiumBy.ID, pp_id)
                    controls_up = bool(pp_els and pp_els[0].size.get("width", 0) > 0)
                except Exception:
                    pass
            if not controls_up:
                self.tap_screen_during_session()
            # Always attempt the tap after the reveal — mirrors _tap_play_pause_btn.
            # In CPS, controls_up may still be False after tap_screen_during_session()
            # because button_end_class has no ID, but the controls ARE revealed.
            els = self.driver.find_elements(AppiumBy.ID, full_id)
            for el in els:
                try:
                    el.click()
                    return
                except StaleElementReferenceException:
                    pass
            # Coordinate fallback for buttons excluded from the accessibility tree.
            if resource_id in self._CONTROL_BTN_X_FRACTION:
                size = self.driver.get_window_size()
                self.driver.execute_script("mobile: clickGesture", {
                    "x": int(size["width"] * self._CONTROL_BTN_X_FRACTION[resource_id]),
                    "y": size["height"] // 2,
                })
                return
        raise AssertionError(f"Control button not tappable after 3 attempts: {resource_id}")

    def _tap_play_pause_btn(self):
        # button_play_pause is an ImageButton excluded from the UiAutomator2
        # accessibility tree — find_elements(AppiumBy.ID) always returns empty.
        # Use confirmed bounds from Appium Inspector instead of ID or center-guess.
        end_btn_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        l, t, r, b = self.CPS_PLAY_PAUSE_BOUNDS
        pp_cx, pp_cy = (l + r) // 2, (t + b) // 2  # 600, 942

        end_els = []
        try:
            end_els = self.driver.find_elements(AppiumBy.ID, end_btn_id)
        except StaleElementReferenceException:
            pass

        is_cps = not end_els  # empty → CPS (no resource ID); non-empty → VOD
        if not is_cps:
            # VOD: use end_btn size to determine controls visibility.
            if end_els[0].size.get("width", 0) == 0:
                self.tap_screen_during_session()
            self.driver.execute_script("mobile: clickGesture", {"x": pp_cx, "y": pp_cy})
            return

        # CPS: button_end_class has no resource ID so end_els is always empty.
        # Use the movement tracker as a controls-state probe instead:
        #   • tracker elements found + is_displayed() True  → controls are HIDDEN → reveal first
        #   • tracker elements not found (GONE = absent from accessibility tree) → controls VISIBLE
        # Do NOT use tap_screen_during_session() here — its y=40% tap lands directly
        # on the pause button (bounds y≈894–990) and would accidentally toggle the session.
        size = self.driver.get_window_size()
        tracker_visible = False
        for rid in ("text_time", "text_reps", "layout_time", "layout_reps"):
            try:
                els = self._find_elements_fast(AppiumBy.ID, f"{self.APP_PACKAGE}:id/{rid}")
                if els and els[0].is_displayed():
                    tracker_visible = True
                    break
            except Exception:
                pass
        if tracker_visible:
            # Controls are hidden — reveal with a safe tap at y=15% (transparent
            # area between END SESSION at y≤144 and Pause button at y≥894).
            self.driver.execute_script("mobile: clickGesture", {
                "x": size["width"] // 2,
                "y": int(size["height"] * 0.15),
            })
            self.wait_seconds(0.5)
        self.driver.execute_script("mobile: clickGesture", {"x": pp_cx, "y": pp_cy})

    def tap_pause(self):
        self._tap_play_pause_btn()

    def tap_resume(self):
        self._tap_play_pause_btn()

    def tap_forward(self):
        self._tap_control_btn(self.SKIP_FWD_BTN)

    def tap_back(self):
        self._tap_control_btn(self.SKIP_BACK_BTN)

    def tap_end_session(self):
        full_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        tapped = False
        for _ in range(3):
            controls_up = False
            try:
                els = self.driver.find_elements(AppiumBy.ID, full_id)
                controls_up = bool(els and els[0].size.get("width", 0) > 0)
            except StaleElementReferenceException:
                pass
            if not controls_up:
                self.tap_screen_during_session()
            els = self.driver.find_elements(AppiumBy.ID, full_id)
            try:
                if els and els[0].is_displayed():
                    els[0].click()
                    tapped = True
                    break
            except StaleElementReferenceException:
                pass
        if not tapped:
            self.driver.back()

        # PostClassSurveyDialog appears after ClassSummaryDialog loads the workout data.
        # button_submit is unique to PostClassSurveyDialog; button_close calls dismiss().
        if self.is_displayed("button_submit", timeout=10):
            self.tap("button_close")
            self.wait_seconds(1)

        # ClassSummaryDialog: button_bookmark is unique to this screen (gone for live 1:1,
        # visible for CPS). button_close calls requireActivity().finish() → main nav.
        if self.is_displayed("button_bookmark", timeout=10):
            self.tap("button_close")
            self.wait_seconds(2)

    def is_cps_visible_on_plan(self):
        # personal_message_icon (ProfileButtonView) is set to visible() only for CPS
        # entries in WeeklyScheduleAdapter (item_vod_card.xml). GONE for all other cards.
        full_icon_id = f"{self.APP_PACKAGE}:id/personal_message_icon"
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().scrollable(true))'
                f'.scrollIntoView(new UiSelector().resourceId("{full_icon_id}"))',
            )
            return True
        except Exception:
            return False

    def is_cps_listed_in_studio(self):
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiScrollable(new UiSelector().scrollable(true))'
                '.scrollIntoView(new UiSelector().textContains("Custom"))',
            )
            return True
        except Exception:
            return False

    def are_reps_time_displayed(self):
        # fragment_inclass_cps_movement_tracker is GONE while controls are visible.
        # Dismiss controls first so the tracker becomes visible, then check for
        # layout_time/text_time (TIME exercises) or layout_reps/text_reps (REPS exercises).
        self._dismiss_controls_if_visible()
        self.wait_seconds(1)
        return (
            self.is_displayed("layout_time") or
            self.is_displayed("text_time") or
            self.is_displayed("layout_reps") or
            self.is_displayed("text_reps")
        )

    def is_swipe_up_displayed(self):
        return self.is_displayed(self.SWIPE_UP_LABEL)

    def wait_for_swipe_up(self, timeout=180):
        """Poll until 'Swipe up to complete' appears.

        label_swipe_up is in fragment_cps_movement_tracker (GONE while controls are
        visible). Controls auto-hide after 10 s, so polling over 180 s is sufficient
        to catch the label once the session reaches a rep-based exercise.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_displayed(self.SWIPE_UP_LABEL, timeout=2):
                return True
            self.wait_seconds(3)
        return False

    def swipe_up_to_complete(self):
        self.swipe_up()

    def is_session_paused(self):
        # Detect CPS vs VOD: button_end_class has no resource ID in CPS so
        # find_elements returns empty; in VOD it returns the button element.
        end_btn_id = f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}"
        try:
            end_els = self.driver.find_elements(AppiumBy.ID, end_btn_id)
            is_cps = not end_els
        except Exception:
            is_cps = False

        if is_cps:
            # CPS: text_class_time is always accessible during a session regardless
            # of controls overlay state. Compare two readings 2 s apart — if frozen
            # the session is paused; if advancing it is still running.
            self.wait_seconds(0.5)
            try:
                t1 = self.get_text("text_class_time")
                self.wait_seconds(2)
                t2 = self.get_text("text_class_time")
                return t1 == t2
            except Exception:
                return False

        # VOD: dismiss controls overlay so fragment_cps_movement_tracker is visible,
        # then compare text_time.
        self._dismiss_controls_if_visible()
        self.wait_seconds(0.5)
        try:
            t1 = self.get_text("text_time")
            self.wait_seconds(2)
            t2 = self.get_text("text_time")
            return t1 == t2
        except Exception:
            # Rep-based VOD: text_time absent — reveal controls and fall back to
            # text_class_time (visible inside the controls overlay).
            size = self.driver.get_window_size()
            self.driver.execute_script("mobile: clickGesture", {
                "x": size["width"] // 2,
                "y": int(size["height"] * 0.15),
            })
            self.wait_seconds(1)
            try:
                t1 = self.get_text("text_class_time")
                self.wait_seconds(2)
                t2 = self.get_text("text_class_time")
                return t1 == t2
            except Exception:
                return False

    def is_session_active(self):
        return (
            self.is_displayed("player_view") or
            self.is_displayed("button_end_class") or
            self.is_displayed("text_class_time") or
            self.is_displayed("text_movement")
        )

    # --- Bookmarks ---

    def _find_bookmark_icon_on_vod_card(self):
        # Search the whole screen for image_bookmark — the icon may sit as an
        # overlay sibling to the CardView rather than nested inside it.
        bookmark_id = f"{self.APP_PACKAGE}:id/{self.VOD_BOOKMARK_ICON}"
        icons = self.driver.find_elements(AppiumBy.ID, bookmark_id)
        for icon in icons:
            try:
                if icon.is_displayed():
                    return icon
            except Exception:
                continue
        raise AssertionError("No visible bookmark icon found on any VOD tile")

    def _find_unbookmarked_icon_on_vod_card(self):
        """Return the first visible bookmark icon that is NOT already active.

        A selected/checked ImageView has already been bookmarked —
        tapping it would remove the bookmark instead of adding one.
        """
        bookmark_id = f"{self.APP_PACKAGE}:id/{self.VOD_BOOKMARK_ICON}"
        icons = self.driver.find_elements(AppiumBy.ID, bookmark_id)
        for icon in icons:
            try:
                if not icon.is_displayed():
                    continue
                if (icon.get_attribute("selected") == "true" or
                        icon.get_attribute("checked") == "true"):
                    continue
                return icon
            except Exception:
                continue
        raise AssertionError("No un-bookmarked class found on current screen")

    def tap_bookmark_icon_on_vod(self):
        for _ in range(8):
            try:
                self._find_bookmark_icon_on_vod_card().click()
                return
            except AssertionError:
                pass
            self.swipe_up()
            self.wait_seconds(0.5)
        raise AssertionError("No visible bookmark icon found on any VOD tile after scrolling")

    def tap_active_bookmark_in_recommended(self):
        """Swipe right through the Recommended carousel and tap the first VOD
        whose bookmark icon is already active (selected/checked), removing it.

        Falls back to tapping any visible bookmark icon if the app does not expose
        bookmark state through accessibility attributes (drawable-only state change).
        In fallback mode the test's own assertion verifies correctness.
        """
        bookmark_id = f"{self.APP_PACKAGE}:id/{self.VOD_BOOKMARK_ICON}"
        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]

        # Locate the "Recommended" section header to anchor carousel swipes.
        carousel_y = int(sh * 0.5)
        rec_header_bottom = None
        try:
            rec_el = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("Recommended")',
            )
            rec_header_bottom = rec_el.location["y"] + rec_el.size["height"]
            carousel_y = rec_header_bottom + int(sh * 0.1)
        except Exception:
            pass

        def _icons_in_recommended_section():
            """Return visible bookmark icons that are positioned below the Recommended header."""
            result = []
            for el in self.driver.find_elements(AppiumBy.ID, bookmark_id):
                try:
                    if not el.is_displayed():
                        continue
                    if rec_header_bottom is not None:
                        icon_y = el.location.get("y", 0)
                        if icon_y < rec_header_bottom:
                            continue  # skip icons above the Recommended section
                    result.append(el)
                except Exception:
                    continue
            return result

        def _is_bookmarked(icon):
            for attr in ("selected", "checked"):
                try:
                    if icon.get_attribute(attr) == "true":
                        return True
                except Exception:
                    pass
            try:
                desc = (icon.get_attribute("content-desc") or "").lower()
                if any(kw in desc for kw in ("bookmarked", "saved", "remove")):
                    return True
            except Exception:
                pass
            return False

        # Pass 1 — attribute-based detection: swipe through all carousel positions
        # and tap the first icon whose accessibility attributes indicate it is bookmarked.
        fallback_icon = None
        for _ in range(10):
            icons = _icons_in_recommended_section()
            for icon in icons:
                if fallback_icon is None:
                    fallback_icon = icon  # remember first visible icon for Pass 2
                try:
                    if _is_bookmarked(icon):
                        icon.click()
                        return
                except Exception:
                    continue
            self.driver.swipe(int(sw * 0.8), carousel_y, int(sw * 0.2), carousel_y, 400)
            self.wait_seconds(0.5)

        # Pass 2 — fallback: the app likely only changes the drawable (image resource)
        # when a bookmark is toggled, leaving all accessibility attributes unchanged.
        # Scroll the carousel back to the beginning, then tap the first visible icon.
        # The test's own assertion will verify whether a bookmark was actually removed.
        for _ in range(10):
            self.driver.swipe(int(sw * 0.2), carousel_y, int(sw * 0.8), carousel_y, 400)
            self.wait_seconds(0.3)

        icons = _icons_in_recommended_section()
        if icons:
            icons[0].click()
            return

        # Fallback icon captured during Pass 1.
        if fallback_icon is not None:
            try:
                fallback_icon.click()
                return
            except Exception:
                pass

        raise AssertionError(
            "No bookmark icon found in the Recommended section on Your Plan tab. "
            "Ensure Recommended classes are visible before running this test."
        )

    def tap_bookmark_icon_on_program_class(self):
        # Step 1 — navigate to Programs tab, scoped to fragment_vod_nav.
        # Reset the nav bar to the beginning first: the previous test may have
        # left it scrolled right to workout categories, which causes both
        # _tap_nav_tab_by_text (XPath misses off-screen elements) and
        # getChildByInstance (counts from current scroll position, not index 0)
        # to tap a workout category instead of Programs.
        nav_id = f"{self.APP_PACKAGE}:id/fragment_vod_nav"
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                f'.setAsHorizontalList().scrollToBeginning(10)',
            )
        except Exception:
            pass
        self.wait_seconds(0.5)
        navigated = self._tap_nav_tab_by_text("Programs")
        if not navigated:
            # Programs is the 3rd clickable child in the nav bar (index 2, 0-based).
            try:
                item = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                    f'.setAsHorizontalList()'
                    f'.getChildByInstance(new UiSelector().clickable(true), 2)',
                )
                item.click()
                navigated = True
            except Exception:
                pass
        if not navigated:
            raise AssertionError("Could not navigate to Programs tab")
        self.wait_seconds(1)

        # Capture nav bar bottom edge so content scrolls never touch the nav bar.
        screen = self.driver.get_window_size()
        nav_bottom = int(screen["height"] * 0.15)  # safe default
        try:
            nav_el = self.driver.find_element(AppiumBy.ID, nav_id)
            nav_bottom = nav_el.location["y"] + nav_el.size["height"]
        except Exception:
            pass

        # Step 2 — scroll program tiles to find one with a trailer link and open it.
        # Use .instance(1) for scrollIntoView: fragment_vod_nav is the first scrollable
        # (instance 0); scrolling IT causes tab switches. instance(1) targets the
        # content RecyclerView directly.
        TRAILER_TEXTS = (
            "Trailer", "Watch Trailer", "trailer",
            "Preview", "View Trailer", "Play Trailer", "TRAILER", "PREVIEW",
        )
        program_opened = False
        for _ in range(10):
            # Strategy A — text label in content RecyclerView.
            for keyword in TRAILER_TEXTS:
                try:
                    trailer_el = self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiScrollable(new UiSelector().scrollable(true).instance(1))'
                        f'.scrollIntoView(new UiSelector().textContains("{keyword}"))',
                    )
                    trailer_y = trailer_el.location["y"]
                    cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
                    for card in cards:
                        c_y = card.location["y"]
                        c_h = card.size["height"]
                        if c_y <= trailer_y <= c_y + c_h:
                            card.click()
                            program_opened = True
                            break
                    if not program_opened:
                        trailer_el.click()
                        program_opened = True
                    break
                except Exception:
                    continue
            if program_opened:
                break

            # Strategy B — content description (icon-only trailer button).
            for desc in ("trailer", "Trailer", "preview", "Preview"):
                try:
                    trailer_el = self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiScrollable(new UiSelector().scrollable(true).instance(1))'
                        f'.scrollIntoView(new UiSelector().descriptionContains("{desc}"))',
                    )
                    trailer_el.click()
                    program_opened = True
                    break
                except Exception:
                    continue
            if program_opened:
                break

            # Swipe within the content area only — start at 80% screen height,
            # end just below the nav bar so the gesture never crosses into the nav.
            sw, sh = screen["width"], screen["height"]
            scroll_end_y = nav_bottom + int((int(sh * 0.8) - nav_bottom) * 0.25)
            self.driver.swipe(sw // 2, int(sh * 0.8), sw // 2, scroll_end_y, 600)
            self.wait_seconds(0.5)

        # Fallback — no trailer element found after scrolling; tap the first
        # visible program card so the test can still reach the class list.
        if not program_opened:
            for _ in range(5):
                cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
                for card in cards:
                    try:
                        if card.is_displayed():
                            card.click()
                            program_opened = True
                            break
                    except Exception:
                        continue
                if program_opened:
                    break
                self.swipe_up()
                self.wait_seconds(0.5)

        if not program_opened:
            raise AssertionError("No program tile found in Programs tab")
        self.wait_seconds(2)

        # Step 3 — inside the program detail view, tap the first bookmark icon
        # that is NOT already active so we add a bookmark rather than remove one.
        for _ in range(10):
            try:
                self._find_unbookmarked_icon_on_vod_card().click()
                return
            except AssertionError:
                pass
            self.swipe_up()
            self.wait_seconds(0.5)

        # All classes are already bookmarked — remove one then re-add so the
        # add-bookmark path is still exercised.
        bookmark_id = f"{self.APP_PACKAGE}:id/{self.VOD_BOOKMARK_ICON}"
        for _ in range(10):
            icons = self.driver.find_elements(AppiumBy.ID, bookmark_id)
            for icon in icons:
                try:
                    if not icon.is_displayed():
                        continue
                    icon.click()  # remove bookmark
                    self.wait_seconds(1)
                    fresh = self.driver.find_elements(AppiumBy.ID, bookmark_id)
                    for fi in fresh:
                        try:
                            if fi.is_displayed():
                                fi.click()  # re-add bookmark
                                return
                        except Exception:
                            continue
                    return
                except Exception:
                    continue
            self.swipe_up()
            self.wait_seconds(0.5)
        raise AssertionError("No bookmark icon found in program class list")

    def is_bookmark_icon_visible_on_vod(self):
        try:
            self._find_bookmark_icon_on_vod_card()
            return True
        except AssertionError:
            return False

    def filter_bookmarked(self):
        # Close class preview dialog if it opened after bookmarking.
        if self.is_displayed(self.START_BTN, timeout=2):
            self.go_back()
            self.wait_seconds(1)
        # Press back until fragment_vod_nav is visible — the program detail view
        # hides the bottom nav bar so go_to_studio_tab() would time out there.
        for _ in range(5):
            if self.is_displayed("fragment_vod_nav", timeout=2):
                break
            self.go_back()
            self.wait_seconds(1)
        # If still not on the Studio browse screen, tap the Studio bottom tab.
        if not self.is_displayed("fragment_vod_nav", timeout=2):
            self.go_to_studio_tab()
            self.wait_seconds(2)
        nav_id = f"{self.APP_PACKAGE}:id/fragment_vod_nav"
        # Scroll the nav back to the beginning so index 0 (Featured) and index 1
        # (Bookmarked) are visible, then tap the Bookmarked tab by index.
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().resourceId("{nav_id}")).setAsHorizontalList().scrollToBeginning(10)',
            )
        except Exception:
            pass
        self.wait_seconds(0.5)
        try:
            item = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().resourceId("{nav_id}")).setAsHorizontalList()'
                f'.getChildByInstance(new UiSelector().clickable(true), 1)',
            )
            item.click()
            self.wait_seconds(1)
        except Exception as e:
            raise AssertionError(f"Could not find Bookmarked tab in Studio navigation: {e}")

    def is_class_in_bookmarked_list(self):
        self.wait_seconds(2)  # allow Bookmarked filter content to load
        for _ in range(3):
            # A visible class card means at least one class is bookmarked.
            cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
            for card in cards:
                try:
                    if card.is_displayed():
                        return True
                except Exception:
                    continue
            # Also accept a visible bookmark icon as confirmation.
            try:
                self._find_bookmark_icon_on_vod_card()
                return True
            except AssertionError:
                pass
            self.swipe_up()
            self.wait_seconds(0.5)
        return False

    # --- VOD Playback ---

    def _handle_end_class_confirmation(self):
        """Tap any 'Leave/End session?' confirmation button using zero-wait lookups."""
        self.driver.implicitly_wait(0)
        try:
            for label in ("End Class", "End", "Yes", "OK", "Leave", "Finish", "Stop"):
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().text("{label}")',
                )
                for el in els:
                    try:
                        if el.is_displayed():
                            el.click()
                            return
                    except Exception:
                        continue
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

    # CPS END SESSION button bounds from Appium Inspector: [24,60][247,144].
    # The button is a ViewGroup/TextView with no resource ID at the top of the
    # controls overlay that appears when the screen is tapped during a CPS session.
    CPS_END_SESSION_BOUNDS = (24, 60, 247, 144)    # left, top, right, bottom
    CPS_PLAY_PAUSE_BOUNDS  = (552, 894, 648, 990)  # left, top, right, bottom

    def _end_class_leave_survey_open(self):
        """Tap END SESSION to trigger PostClassSurveyDialog.

        Uses ONLY resource-ID lookups and mobile:clickGesture — no UiSelector
        text or XPath, which block for 2–5 min under active CPS load.

        CPS layout (confirmed via Appium Inspector):
          • END SESSION bounds: [24,60][247,144], center (135, 102).
            The button is a ViewGroup/TextView with no resource ID.
          • Reveal tap at y≈30 % (transparent overlay area above CPS bottom sheet).
          • Confirmation dialog positive button: android:id/button1 (fast ID).
        VOD: button_end_class has a resource ID — found by _tap_end_by_id().
        """
        end_btn_ids = [
            f"{self.APP_PACKAGE}:id/{self.END_CLASS_BTN}",   # VOD: button_end_class
            f"{self.APP_PACKAGE}:id/button_end_session",      # CPS alternative
        ]
        left, top, right, bottom = self.CPS_END_SESSION_BOUNDS
        cps_cx = (left + right) // 2    # 135
        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]

        # Wait for the CPS block-preview overlay to clear (fast ID lookup).
        block_id = f"{self.APP_PACKAGE}:id/fragment_block_preview"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                els = self._find_elements_fast(AppiumBy.ID, block_id)
            except WebDriverException:
                self.wait_seconds(3)
                break
            if not els:
                break
            try:
                if not els[0].is_displayed():
                    break
            except Exception:
                break
            self.wait_seconds(1)

        def _survey_visible():
            try:
                els = self._find_elements_fast(
                    AppiumBy.ID, f"{self.APP_PACKAGE}:id/button_submit"
                )
                return bool(els and els[0].is_displayed())
            except Exception:
                return False

        def _confirm_fast():
            """android:id/button1 = AlertDialog positive button (fast resource-ID)."""
            try:
                els = self._find_elements_fast(AppiumBy.ID, "android:id/button1")
                for el in els:
                    try:
                        if el.is_displayed():
                            el.click()
                            return
                    except Exception:
                        continue
            except Exception:
                pass

        def _click(x, y):
            try:
                self.driver.execute_script("mobile: clickGesture", {"x": x, "y": y})
            except WebDriverException:
                self.wait_seconds(3)

        # ── 1. VOD: button_end_class has a resource ID ────────────────────────
        try:
            for btn_id in end_btn_ids:
                for el in self._find_elements_fast(AppiumBy.ID, btn_id):
                    try:
                        if el.is_displayed():
                            el.click()
                            self.wait_seconds(2)
                            _confirm_fast()
                            self.wait_seconds(2)
                    except Exception:
                        continue
        except WebDriverException:
            self.wait_seconds(3)
        if _survey_visible():
            return

        # ── 2. CPS — Reveal controls → tap END SESSION at known coordinate ───
        # Reveal positions at y=25–55 % (transparent overlay area above bottom sheet).
        # After the reveal tap controls appear; END SESSION bounds [24,60][247,144],
        # center (135, 102).  A screenshot is saved before each tap to help diagnose
        # coordinate issues — remove the screenshot calls once the button is confirmed.
        for ry in (int(sh * 0.30), int(sh * 0.45), int(sh * 0.25)):
            if _survey_visible():
                return
            _click(sw // 2, ry)        # reveal controls
            self.wait_seconds(2)

            for cy in ((top + bottom) // 2, top + 20, bottom - 20):
                _click(cps_cx, cy)
                self.wait_seconds(2)
                _confirm_fast()
                self.wait_seconds(3)
                if _survey_visible():
                    return

    def start_vod_class(self, skip_music=True):
        """Navigate to Barre VOD, open the first class card, and start it playing.

        When skip_music=True (default) the music selection dialog is dismissed
        automatically and the class begins immediately.  When skip_music=False the
        method returns with the music dialog open so the caller can interact with it.
        Leaves the class running — does NOT end the session.
        """
        nav_id = f"{self.APP_PACKAGE}:id/fragment_vod_nav"

        if self.is_displayed("fragment_vod_nav", timeout=5):
            try:
                self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiScrollable(new UiSelector().resourceId("{nav_id}"))'
                    f'.setAsHorizontalList().scrollToBeginning(10)',
                )
            except Exception:
                pass
            self.wait_seconds(0.5)
            navigated = (self._tap_nav_tab_by_text("Barre") or
                         self._tap_nav_tab_by_text("BARRE"))
            if not navigated:
                for cat in ("Strength", "Mind", "Pilates", "Yoga", "Cardio", "Recovery"):
                    if self._tap_nav_tab_by_text(cat):
                        break
            self.wait_seconds(1)
            self._scroll_content_to_top()

        # SESSION_CARD_ID = CardView in item_vod_card.xml — unique to actual session
        # tiles (text_title is NOT used because it also matches section headers).
        cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
        if not cards:
            for _ in range(5):
                self.swipe_up()
                self.wait_seconds(0.5)
                cards = self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
                if cards:
                    break
        if not cards:
            raise AssertionError("No VOD session tiles found in Barre / Studio category")

        cards[0].click()
        self.wait_seconds(2)

        self._dismiss_hrm_dialog_if_present()

        if not self.is_displayed(self.START_BTN, timeout=10):
            raise AssertionError(
                "Class preview (button_start) did not appear after tapping a VOD card"
            )
        self.tap(self.START_BTN)

        if self.is_displayed(self.MUSIC_YOUTUBE_BTN, timeout=5):
            if skip_music:
                self.tap(self.START_BTN)
            else:
                return  # leave music dialog open for caller

        if self.is_displayed(self.CPS_ONBOARDING_SKIP_BTN, timeout=5):
            self.tap(self.CPS_ONBOARDING_SKIP_BTN)

    def play_vod_class(self):
        """Navigate to a Barre VOD class, tap Start, and leave the music selection
        dialog open for the caller to interact with.
        """
        self.start_vod_class(skip_music=False)

    def wait_for_class_completion(self, timeout=3600):
        """Poll until PostClassSurveyDialog appears after the class ends naturally.

        Uses a 1-second button_submit check every 10 s to minimise overhead
        during a potentially hour-long class.  A full text check runs every
        30 s as a fallback.  Returns True if the survey appeared within
        *timeout* seconds, False if the timeout expired first.
        """
        end_time = time.monotonic() + timeout
        next_text_check = time.monotonic() + 30
        while time.monotonic() < end_time:
            if self.is_displayed("button_submit", timeout=1):
                return True
            if time.monotonic() >= next_text_check:
                if self.is_post_session_survey_displayed():
                    return True
                next_text_check = time.monotonic() + 30
            self.wait_seconds(10)
        return False

    def enter_survey_comment(self, text):
        """Type *text* into the 'Enter Message here' field on the Post-Session Survey.

        Uses UiScrollable.scrollIntoView with the field's placeholder text so the
        method both scrolls to the field AND gets a direct reference to it.  Falls
        back to resource-ID and EditText lookups if the placeholder text differs.
        """
        def _type_into(el):
            """Click, clear, and type — handles FormeEditText wrappers."""
            el.click()
            try:
                inner = el.find_element(AppiumBy.ID, f"{self.APP_PACKAGE}:id/edit")
                inner.clear()
                inner.send_keys(text)
            except Exception:
                el.clear()
                el.send_keys(text)

        # Strategy 1 — scroll to field by its known placeholder text and type.
        # UiScrollable.scrollIntoView returns the element itself, so no second lookup.
        for hint in ("Enter Message here", "Enter Message", "Enter message",
                     "Add a comment", "Write a message", "Comments"):
            try:
                el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiScrollable(new UiSelector().scrollable(true))'
                    f'.scrollIntoView(new UiSelector().textContains("{hint}"))',
                )
                _type_into(el)
                return
            except Exception:
                continue

        # Strategy 2 — resource-ID lookup (swipe down first in case field is off-screen).
        self.swipe_up()
        self.wait_seconds(0.5)
        for field_id in ("edit_message", "edit_comment", "edit_notes", "edit_feedback"):
            if self.is_displayed(field_id, timeout=2):
                try:
                    self.type_text(field_id, text)
                    return
                except Exception:
                    continue

        # Strategy 3 — first visible EditText on screen.
        try:
            el = self.driver.find_element(
                AppiumBy.CLASS_NAME, "android.widget.EditText"
            )
            _type_into(el)
        except Exception:
            raise AssertionError(
                "Could not find 'Enter Message here' Comments field in Post-Session Survey"
            )

    def is_vod_playing(self):
        return self.is_displayed("player_view") or self.is_displayed("video_view")

    # --- Post-Session Survey ---

    def is_post_session_survey_displayed(self):
        """Return True if PostClassSurveyDialog or ClassSummaryDialog is visible.

        Checks button_submit first (2 s timeout) — it is the definitive resource-ID
        indicator of PostClassSurveyDialog and returns instantly when present.
        Text checks use find_elements + implicitly_wait(0) (~30 ms per miss) so
        the full method costs < 3 s when the survey is absent, versus 15 s before.
        """
        if self.is_displayed("button_submit", timeout=2):
            return True
        self.driver.implicitly_wait(0)
        try:
            for text in ("Session Feedback", "How was your workout", "Rate your session",
                         "How did you feel", "How was your class", "Rate your workout",
                         "Nice Work", "Workout Summary", "Class Summary", "Post Session"):
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{text}")',
                )
                if els:
                    try:
                        if els[0].is_displayed():
                            return True
                    except Exception:
                        pass
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)
        return False

    def tap_rating_star(self, n=1):
        """Tap the nth star in the Post-Session Survey using its content-desc.

        PostClassSurveyAdapter sets:
          binding.root.contentDescription = "rating_<title_snake>_star_<n>"
        where title is derived from step.title (lowercased, underscored).
        Matches any category (overall, effort, etc.) at position n.
        Falls back to tapping by text if the content-desc is not yet available.
        """
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionMatches("rating_.*_star_{n}")',
            ).click()
        except Exception:
            self.tap_text_contains(str(n))

    def tap_all_rating_stars(self, n):
        """Tap the nth star for every rating category in the Post-Session Survey.

        PostClassSurveyAdapter sets content-desc = rating_<title_snake>_star_<n>
        for each category (Session, Instructor, Difficulty for you, etc.).
        Collects all matching content-descs first via a full UiAutomator2 tree
        traversal (includes off-screen elements in RecyclerView), then uses
        UiScrollable.scrollIntoView to reach and tap each one in turn.
        Falls back to a single tap_rating_star(n) if content-descs are absent.
        """
        self.driver.implicitly_wait(0)
        try:
            els = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionMatches("rating_.*_star_{n}")',
            )
            descs = []
            for el in els:
                try:
                    desc = el.get_attribute("content-desc")
                    if desc:
                        descs.append(desc)
                except Exception:
                    continue
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

        if not descs:
            self.tap_rating_star(n)
            return

        for desc in descs:
            try:
                el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiScrollable(new UiSelector().scrollable(true))'
                    f'.scrollIntoView(new UiSelector().description("{desc}"))',
                )
                el.click()
                self.wait_seconds(0.3)
            except Exception:
                try:
                    self.driver.find_element(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().description("{desc}")',
                    ).click()
                    self.wait_seconds(0.3)
                except Exception:
                    continue

    def is_rating_star_content_desc_visible(self):
        """Return True if at least one star element has content-desc matching rating_*_star_*.

        PostClassSurveyAdapter (MW-3233) sets:
          binding.root.contentDescription = "rating_<title_snake>_star_<n>"
        Falls back to checking for any element whose content-desc starts with "rating_".
        """
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionMatches("rating_.*_star_.*")',
            )
            return True
        except Exception:
            pass
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionContains("rating_")',
            )
            return True
        except Exception:
            return False

    def submit_survey(self):
        """Tap the Submit button on the Post-Session Survey.

        Does NOT call hide_keyboard(): on Android 14 that API sends KEYCODE_BACK
        via UiAutomator2, and if the soft keyboard was already dismissed after
        send_keys() completed, the BACK event reaches the activity and closes
        the survey dialog — making button_submit vanish from the tree.
        UiAutomator2 find + click works on elements behind the keyboard anyway.
        """
        self.tap("button_submit")

    def close_workout_summary(self):
        """Close the Workout Summary dialog that appears after survey submission.

        ClassSummaryDialog is uniquely identified by button_bookmark.
        button_close on that dialog calls requireActivity().finish() → main nav.
        Falls back to text-based close buttons and driver.back() if needed.
        """
        if self.is_displayed("button_bookmark", timeout=10):
            self.tap("button_close")
            self.wait_seconds(2)
            return
        # Fallback: close/done button by text (in case layout differs by class type).
        for label in ("Close", "Done", "Finish"):
            try:
                self.tap_text(label, timeout=3)
                self.wait_seconds(1)
                return
            except Exception:
                continue
        # Last resort: back gesture to dismiss the dialog.
        self.go_back()
        self.wait_seconds(1)

    def is_submit_active(self):
        el = self.find_by_id("button_submit")
        return el.is_enabled()

    # --- Workout History ---

    def go_to_workout_history(self):
        self.ensure_logged_in()
        self.tap(self.PROFILE_BUTTON)
        self.wait_seconds(1)

    def is_vod_session_in_history(self, session_type: str = None, api_token: str = None) -> bool:
        """Check profile Progress section for completed workouts.

        When session_type and api_token are supplied, also verifies via the
        Formelife REST API that at least one completed workout of that specific
        session_type exists (e.g. "Video on Demand" vs "Lift VOD").
        This is the only way to distinguish Android from Lift sessions since
        the app UI does not expose platform information.
        """
        # UI check: profile → Progress → Completed Workouts
        ui_pass = False
        try:
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiScrollable(new UiSelector().scrollable(true))'
                '.scrollIntoView(new UiSelector().textContains("Completed Workouts"))',
            )
            ui_pass = True
        except Exception:
            ui_pass = (
                self.is_text_contains_displayed("Completed Workouts") or
                self.is_text_contains_displayed("Progress")
            )

        if not ui_pass:
            return False

        if session_type is None or api_token is None:
            return True

        # API check: confirm a completed workout of the specific session type exists.
        from pages.api_client import get_history_workouts
        try:
            workouts = get_history_workouts(api_token, session_type=session_type)
            return len(workouts) > 0
        except Exception:
            return False

    # --- Programs ---

    def go_to_programs(self):
        self.navigate_to_studio()
        self.tap_text_contains("Programs")

    def is_completed_state_shown(self):
        return self.is_text_contains_displayed("Completed")

    # --- MW-3234: Session card content description ---

    def get_session_card_content_desc(self):
        """Return the content-desc of the first visible session CardView.

        VODClassViewHolder (MW-3234) sets:
          card.contentDescription = workout.sessionType.toString()
        so each card carries its session type, e.g. CUSTOM_PLANNED_SESSION.
        """
        WebDriverWait(self.driver, self.DEFAULT_TIMEOUT).until(
            lambda d: d.find_elements(AppiumBy.ID, self.SESSION_CARD_ID)
        )
        for card in self.driver.find_elements(AppiumBy.ID, self.SESSION_CARD_ID):
            try:
                if card.is_displayed():
                    return card.get_attribute("content-desc") or ""
            except Exception:
                continue
        raise AssertionError("No visible session card found in the current view")

    # --- MW-3233: Streak checkmark image content description ---

    def is_streak_checkmark_image_content_desc_visible(self):
        """Return True if at least one day-checkmark image has content-desc
        'completed' or 'incomplete'.

        ViewDayCheckmark.bind() (MW-3233) sets:
          binding.image.contentDescription = if (checked) "completed" else "incomplete"
        The content-desc is on the ImageView inside the checkmark, not the root.
        """
        for desc in ("completed", "incomplete"):
            try:
                el = self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().className("android.widget.ImageView")'
                    f'.descriptionContains("{desc}")',
                )
                if el.is_displayed():
                    return True
            except Exception:
                continue
        return False

    # --- Music during session ---

    YOUTUBE_MUSIC_PACKAGE = "com.google.android.apps.youtube.music"
    APPLE_MUSIC_PACKAGE = "com.apple.android.music"

    def _play_song_in_music_app(self, package, timeout=30):
        """Wait for a third-party music app to open then navigate to Library → Songs
        and tap the first song.  Falls back to media keys and coordinate taps.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self.driver.current_package == package:
                    break
            except Exception:
                pass
            self.wait_seconds(1)

        self.wait_seconds(3)  # let the app finish its launch animation

        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]
        top_y = int(sh * 0.06)   # exclude status bar only (~24-48 dp)
        nav_y = int(sh * 0.85)
        bottom_nav_y = int(sh * 0.93)

        # ── helpers ──────────────────────────────────────────────────────────

        def _find_by_text(*texts):
            """Return first displayed element whose text matches any of *texts*."""
            self.driver.implicitly_wait(0)
            try:
                for text in texts:
                    els = self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().text("{text}")',
                    )
                    for el in els:
                        try:
                            if el.is_displayed():
                                return el
                        except Exception:
                            continue
                    els = self.driver.find_elements(
                        AppiumBy.ANDROID_UIAUTOMATOR,
                        f'new UiSelector().descriptionContains("{text}")',
                    )
                    for el in els:
                        try:
                            if el.is_displayed():
                                return el
                        except Exception:
                            continue
            finally:
                self.driver.implicitly_wait(self.IMPLICIT_WAIT)
            return None

        def _tap_if_found(*texts):
            el = _find_by_text(*texts)
            if el:
                try:
                    el.click()
                    return True
                except Exception:
                    pass
            return False

        def _tap_first_song_row():
            """Tap the first clickable element in the content area.

            Accepts any element wider than 15 % of the screen so small play/
            shuffle buttons (not just full-width song rows) are also matched.
            """
            self.driver.implicitly_wait(0)
            try:
                els = self.driver.find_elements(AppiumBy.XPATH, '//*[@clickable="true"]')
                for el in els:
                    try:
                        loc = el.location
                        sz = el.size
                        y = loc.get("y", nav_y + 1)
                        if y < top_y or y >= nav_y:
                            continue
                        if sz.get("width", 0) > sw * 0.15 and sz.get("height", 0) > 20:
                            if el.is_displayed():
                                el.click()
                                return True
                    except Exception:
                        continue
            finally:
                self.driver.implicitly_wait(self.IMPLICIT_WAIT)
            return False

        # ── Step 1: media keys (work when app has a recent track) ─────────────
        for kc in (126, 85):  # KEYCODE_MEDIA_PLAY, KEYCODE_MEDIA_PLAY_PAUSE
            try:
                self.driver.press_keycode(kc)
                self.wait_seconds(0.5)
            except Exception:
                pass

        # ── Step 2: navigate to Library tab ──────────────────────────────────
        if not _tap_if_found("Library", "library"):
            # Library tab not found by text — try bottom-nav coordinate positions.
            # YouTube Music: 3rd of 4 tabs; Apple Music: 4th of 5 tabs.
            for x_frac in (0.50, 0.60, 0.65, 0.70, 0.75):
                self.driver.execute_script("mobile: clickGesture", {
                    "x": int(sw * x_frac), "y": bottom_nav_y,
                })
                self.wait_seconds(0.5)
                if _find_by_text("Songs", "All Songs"):
                    break
        self.wait_seconds(0.5)

        # ── Step 3: tap "Songs" section inside Library ────────────────────────
        if _tap_if_found("Songs", "All Songs"):
            self.wait_seconds(2)  # wait for Songs list to fully load

        # ── Step 4: tap the Play / Shuffle button in the Songs list header ────
        # Apple Music uses an ImageButton whose content-desc is "Shuffle" or
        # "Shuffle songs"; YouTube Music uses "Shuffle All" / "Play All".
        for play_label in ("Play", "Play All", "Shuffle", "Shuffle All",
                           "Play all", "Shuffle all", "Shuffle songs",
                           "Play songs", "Shuffle all songs"):
            if _tap_if_found(play_label):
                return

        # ── Step 5: tap the first visible song row ────────────────────────────
        if _tap_first_song_row():
            return

        # ── Step 6: coordinate sweep — try several y positions for first song ──
        for y_frac in (0.20, 0.25, 0.30, 0.35, 0.42):
            self.driver.execute_script("mobile: clickGesture", {
                "x": sw // 2, "y": int(sh * y_frac),
            })
            self.wait_seconds(0.4)

    def play_song_in_youtube_music(self, timeout=30):
        """Wait for YouTube Music to open and play a song."""
        self._play_song_in_music_app(self.YOUTUBE_MUSIC_PACKAGE, timeout)

    def play_song_in_apple_music(self, timeout=30):
        """Wait for Apple Music to open and play a song."""
        self._play_song_in_music_app(self.APPLE_MUSIC_PACKAGE, timeout)

    def tap_music_icon(self):
        self.tap(self.MUSIC_BTN)

    def select_youtube_music(self):
        self.tap(self.MUSIC_YOUTUBE_BTN)

    def select_apple_music(self):
        self.tap(self.MUSIC_APPLE_BTN)

    def skip_music_selection(self):
        self.tap(self.MUSIC_CLOSE_BTN)

    def is_music_selection_screen_displayed(self):
        return self.is_text_displayed("Select Music") or self.is_displayed(self.MUSIC_LABEL)
