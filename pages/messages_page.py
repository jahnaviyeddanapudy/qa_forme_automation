from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
from pages.base_page import BasePage


class MessagesPage(BasePage):

    # Resource IDs from fragment_messages.xml
    EDIT_MESSAGE = "edit_message"
    SEND_BTN = "button_send"
    IMAGE_BTN = "button_image"
    RECYCLER = "recycler"
    REACTIONS_VIEW = "view_reaction"
    TRAINER_NAME = "label_trainer_name"
    MESSAGE_TEXT_ID = f"com.formelife.member:id/text"

    def navigate_to_messages(self):
        self.ensure_logged_in()
        self.go_to_messages_tab()

    def type_message(self, text):
        self.type_text(self.EDIT_MESSAGE, text)

    def send_message(self):
        self.tap(self.SEND_BTN)

    def send_text_message(self, text):
        self.type_message(text)
        self.send_message()

    def tap_image_button(self):
        self.tap(self.IMAGE_BTN)

    def _back_in_forme(self):
        """Return True if the Forme app is the foreground package."""
        try:
            return self.driver.current_package == self.APP_PACKAGE
        except Exception:
            return False

    def _quick_tap_text(self, texts):
        """Find and tap the first visible element matching any of *texts* (substring).

        Uses find_elements + implicitly_wait(0) so a miss costs ~20 ms instead of
        the full WebDriverWait timeout.  Returns True if an element was tapped.
        """
        self.driver.implicitly_wait(0)
        try:
            for text in texts:
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{text}")',
                )
                for el in els:
                    try:
                        if el.is_displayed():
                            el.click()
                            return True
                    except Exception:
                        continue
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)
        return False

    def _tap_confirm_if_visible(self):
        """Tap any picker confirmation button that is currently on screen.

        Uses _quick_tap_text so a complete miss costs ~150 ms instead of 2+ s.
        "Add" also matches "Add 1" / "Add photos" (Android Photo Picker API 33+).
        """
        return self._quick_tap_text(["Add", "Done", "OK", "Select", "Use", "Choose", "Open"])

    def _photo_tap_succeeded(self):
        """After tapping a candidate, return True if the picker accepted the selection."""
        self.wait_seconds(0.1)
        if self._back_in_forme():
            return True
        if self._tap_confirm_if_visible():
            self.wait_seconds(0.3)
            return self._back_in_forme()
        return False

    def _tap_first_photo_in_grid(self, min_photo_y):
        """Select a photo from the open picker.

        Tries a coordinate sweep first (no element queries, fastest path), then
        falls back to a targeted ImageView search with a hard cap of 5 .rect calls.
        Strategy 3 (FrameLayout/ViewGroup) is intentionally omitted — it returns
        hundreds of elements on a real device, making each .rect round-trip
        multiply into 100+ seconds of overhead.
        """
        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]

        # Strategy 1 — coordinate sweep across common photo-grid positions.
        # No element queries or .rect calls — just tap and check current_package.
        for y_frac in (0.25, 0.35, 0.45, 0.20, 0.55):
            y_px = int(sh * y_frac)
            if y_px < min_photo_y:
                continue
            for x_frac in (0.17, 0.50, 0.83):
                self.driver.execute_script("mobile: clickGesture", {
                    "x": int(sw * x_frac), "y": y_px,
                })
                if self._photo_tap_succeeded():
                    return True

        # Strategy 2 — clickable ImageViews (capped at 5 to limit .rect round-trips).
        self.driver.implicitly_wait(0)
        try:
            imgs = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().className("android.widget.ImageView").clickable(true)',
            )
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)
        for img in imgs[:5]:
            try:
                r = img.rect
                if r.get("y", 0) >= min_photo_y and r.get("width", 0) >= 80:
                    img.click()
                    if self._photo_tap_succeeded():
                        return True
            except Exception:
                continue

        # Strategy 3 — first children of the tallest RecyclerView (photo grid).
        self.driver.implicitly_wait(0)
        try:
            rvs = self.driver.find_elements(
                AppiumBy.CLASS_NAME, "androidx.recyclerview.widget.RecyclerView"
            )
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)
        rvs = sorted(rvs, key=lambda r: r.size.get("height", 0), reverse=True)
        for rv in rvs[:1]:
            try:
                children = rv.find_elements(AppiumBy.XPATH, "./*")
                for child in children[:3]:
                    try:
                        r = child.rect
                        if r.get("y", 0) >= min_photo_y and r.get("width", 0) >= 80:
                            child.click()
                            if self._photo_tap_succeeded():
                                return True
                    except Exception:
                        continue
            except Exception:
                pass

        return False

    def select_image_from_gallery(self):
        self.tap_image_button()
        self.wait_seconds(1)

        # All optional-UI taps use _quick_tap_text (find_elements + implicitly_wait 0)
        # so a miss costs ~20 ms instead of the full WebDriverWait timeout.
        self._quick_tap_text(["Gallery", "Photos", "Google Photos", "Files"])
        self.wait_seconds(0.5)
        self._quick_tap_text(["Allow", "Allow access", "Only this time", "While using the app"])
        self._quick_tap_text(["Recents", "Camera", "All photos", "DCIM"])
        self.wait_seconds(0.5)

        size = self.driver.get_window_size()
        min_photo_y = int(size["height"] * 0.12)

        self._tap_first_photo_in_grid(min_photo_y)

        # One more confirm attempt in case the picker needs an explicit tap.
        self._tap_confirm_if_visible()
        self.wait_seconds(0.3)

        # Back-navigate to Forme if still inside the picker.
        for _ in range(3):
            if self._back_in_forme():
                break
            self.go_back()
            self.wait_seconds(0.3)
            self._tap_confirm_if_visible()

        if self.is_displayed(self.SEND_BTN, timeout=3):
            self.tap(self.SEND_BTN)

    # ------------------------------------------------------------------ #
    #  Emoji reaction helpers                                              #
    # ------------------------------------------------------------------ #

    def _is_reaction_quick(self):
        """Return True if any reaction badge is visible. Implicit wait = 0 for the whole method."""
        self.driver.implicitly_wait(0)
        try:
            for rid in ("view_reaction", "reaction_view", "emoji_reaction", "item_reaction",
                        "message_reaction", "layout_reaction"):
                if self.driver.find_elements(AppiumBy.ID, f"{self.APP_PACKAGE}:id/{rid}"):
                    return True
            return False
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

    def long_press_message(self, index=0):
        """Long-press a received (trainer) message to open the emoji reaction picker.

        Uses a single gesture attempt so the picker stays open for
        select_emoji_reaction() to handle.  Multiple back-to-back gestures
        would open and then immediately dismiss the picker.
        """
        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]
        mid_x = sw // 2

        all_msgs = []
        try:
            recycler = self.find_by_id(self.RECYCLER, timeout=5)
            all_msgs = recycler.find_elements(AppiumBy.ID, self.MESSAGE_TEXT_ID)
        except Exception:
            pass
        if not all_msgs:
            all_msgs = self.driver.find_elements(AppiumBy.ID, self.MESSAGE_TEXT_ID)
        if not all_msgs:
            raise AssertionError("No messages found in the chat thread")

        # Primary: find trainer message text elements by looking for containers
        # that include label_trainer_name (only present on received/trainer messages).
        trainer_msg_data = []
        try:
            trainer_els = self.driver.find_elements(
                AppiumBy.XPATH,
                f'//*[.//*[@resource-id="{self.APP_PACKAGE}:id/label_trainer_name"]]'
                f'//*[@resource-id="{self.MESSAGE_TEXT_ID}"]',
            )
            for e in trainer_els:
                try:
                    r = e.rect
                    if r.get("width", 0) > 0:
                        trainer_msg_data.append((r, e))
                except Exception:
                    continue
        except Exception:
            pass

        msg_data = []
        for m in all_msgs:
            try:
                r = m.rect
                if r.get("width", 0) > 0:
                    msg_data.append((r, m))
            except Exception:
                continue

        if not msg_data:
            raise AssertionError("No visible messages found in the chat thread")

        # Fallback: in the Forme app trainer (received) messages appear on the right
        # side of the screen; filter by center-x > mid_x.
        if trainer_msg_data:
            target_list = trainer_msg_data
        else:
            received = [(r, m) for r, m in msg_data
                        if r.get("x", 0) + r.get("width", 0) // 2 > mid_x]
            target_list = received if received else msg_data

        screen_mid_y = sh // 2
        target_list = sorted(
            target_list,
            key=lambda rm: abs(rm[0].get("y", 0) + rm[0].get("height", 0) // 2 - screen_mid_y),
        )
        rect, _ = target_list[min(index, len(target_list) - 1)]
        # Long-press at the centre of the message bubble to reach the
        # ViewGroup's OnLongClickListener without triggering text-selection.
        press_x = rect.get("x", 0) + rect.get("width", 0) // 2
        press_y = rect.get("y", 0) + rect.get("height", 0) // 2

        # Single coordinate-based long press.
        self.driver.execute_script("mobile: longClickGesture", {
            "x": press_x, "y": press_y, "duration": 2500,
        })
        self.wait_seconds(1)

        # If a context menu appeared (React / Reply / Copy…), tap React.
        # Implicit wait is 0 for the whole block so failed lookups are instant.
        self.driver.implicitly_wait(0)
        try:
            for react_label in ("React", "Add Reaction", "Reaction"):
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().textContains("{react_label}")',
                )
                for el in els:
                    try:
                        el.click()
                        self.wait_seconds(0.5)
                        return
                    except Exception:
                        continue
        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

    def select_emoji_reaction(self, emoji="👍"):
        """Select an emoji reaction from the picker that is currently visible on screen.

        All strategies use implicit wait = 0 so failed lookups are instant and the
        picker does not auto-dismiss while we wait for slow WebDriverWait timeouts.
        """
        size = self.driver.get_window_size()
        sw, sh = size["width"], size["height"]
        nav_bar_top = int(sh * 0.85)

        self.driver.implicitly_wait(0)
        try:
            # Strategy 1 — UiSelector text match (emoji Unicode as button label).
            for sel in (f'new UiSelector().text("{emoji}")',
                        f'new UiSelector().textContains("{emoji}")'):
                els = self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                if els:
                    try:
                        els[0].click()
                        return
                    except Exception:
                        pass

            # Strategy 2 — XPath text attribute.
            els = self.driver.find_elements(AppiumBy.XPATH, f'//*[@text="{emoji}"]')
            if els:
                try:
                    els[0].click()
                    return
                except Exception:
                    pass

            # Strategy 3 — content-description (icon-only emoji buttons).
            desc_map = {
                "👍": ("Thumbs up", "Like", "thumbs up", "like"),
                "❤️": ("Heart", "Love", "heart", "love"),
                "😂": ("Haha", "Laugh", "Joy", "laugh", "haha"),
                "😮": ("Wow", "Surprised", "surprise", "wow"),
                "😢": ("Sad", "Cry", "sad", "cry"),
                "😡": ("Angry", "anger", "angry"),
            }
            for desc in desc_map.get(emoji, (emoji,)):
                for sel in (f'new UiSelector().description("{desc}").clickable(true)',
                            f'new UiSelector().descriptionContains("{desc}").clickable(true)'):
                    els = self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                    if els:
                        try:
                            els[0].click()
                            return
                        except Exception:
                            pass

            # Strategy 4 — cluster detection: find the densest horizontal row of small
            # square-ish clickable elements above the system nav bar.
            # Uses UiAutomator2 (faster than XPath) + el.rect (1 call vs 3 per element).
            all_els = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().clickable(true)"
            )
            candidates = []
            for el in all_els:
                try:
                    r = el.rect
                    w = r.get("width", 0)
                    h = r.get("height", 0)
                    x = r.get("x", 0)
                    y = r.get("y", 0)
                    if 30 <= w <= 150 and 30 <= h <= 150 and abs(w - h) <= 40 and y < nav_bar_top and w > 0:
                        candidates.append((y, x, el))
                except Exception:
                    continue

            best_row = []
            for y_val, _, _ in candidates:
                row = [(ry, rx, re) for ry, rx, re in candidates if abs(ry - y_val) <= 25]
                if len(row) > len(best_row):
                    best_row = row

            if len(best_row) >= 3:
                best_row.sort(key=lambda t: t[1])
                try:
                    best_row[0][2].click()
                    return
                except Exception:
                    pass

            # Strategy 5 — keyword content-desc sweep.
            for kw in ("thumbs", "like", "heart", "love", "laugh", "haha",
                       "wow", "sad", "angry", "reaction", "emoji"):
                els = self.driver.find_elements(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    f'new UiSelector().descriptionContains("{kw}").clickable(true)',
                )
                if els:
                    try:
                        els[0].click()
                        return
                    except Exception:
                        continue

            # Strategy 6 — coordinate sweep (last resort).
            for y_frac in (0.25, 0.35, 0.5, 0.65, 0.8):
                for x_frac in (0.15, 0.5, 0.85):
                    self.driver.execute_script("mobile: clickGesture", {
                        "x": int(sw * x_frac),
                        "y": int(sh * y_frac),
                    })
                    self.wait_seconds(0.3)
                    if self._is_reaction_quick():
                        return

        finally:
            self.driver.implicitly_wait(self.IMPLICIT_WAIT)

    def is_message_in_list(self, text):
        return self.is_text_contains_displayed(text)

    def is_image_sent(self):
        for img_id in ("item_attachment_image", "image_message", "message_image",
                       "image_content", "chat_image", "attachment_thumbnail", "image"):
            if self.is_displayed(img_id, timeout=2):
                return True

        size = self.driver.get_window_size()
        min_img_px = int(min(size["width"], size["height"]) * 0.15)
        try:
            imgs = self._find_elements_fast(AppiumBy.CLASS_NAME, "android.widget.ImageView")
            for img in imgs:
                try:
                    r = img.rect
                    if r.get("width", 0) >= min_img_px and r.get("height", 0) >= min_img_px:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def is_emoji_reaction_visible(self):
        """Check for a reaction badge, retrying up to 5 times.

        Implicit wait is set to 0 once per retry (2 round trips) rather than per
        find_elements call, keeping each iteration fast.
        """
        for _ in range(5):
            self.driver.implicitly_wait(0)
            try:
                for rid in ("view_reaction", "reaction_view", "emoji_reaction",
                            "item_reaction", "message_reaction", "layout_reaction",
                            "text_reaction", "reaction_badge"):
                    if self.driver.find_elements(AppiumBy.ID, f"{self.APP_PACKAGE}:id/{rid}"):
                        return True

                for emoji_text in ("👍", "❤️", "😂", "😮", "😢", "😡"):
                    if self.driver.find_elements(AppiumBy.XPATH, f'//*[@text="{emoji_text}"]'):
                        return True
            finally:
                self.driver.implicitly_wait(self.IMPLICIT_WAIT)

            self.wait_seconds(1)

        return False

    def is_message_list_visible(self):
        return self.is_displayed(self.RECYCLER)

    def is_chat_screen_visible(self):
        return self.is_displayed(self.EDIT_MESSAGE)

    def get_trainer_name(self):
        return self.get_text(self.TRAINER_NAME)
