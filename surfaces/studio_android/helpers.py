"""Studio-app test helpers.

Carries over the member repo's find_and_tap_vod_class pattern. Element
IDs assumed same as member repo for now — confirm via tools/dump_screen.py
once we run the first class-listing test on Studio.
"""
import logging
from appium.webdriver.common.appiumby import AppiumBy
from surfaces.studio_android.config import APP_PACKAGE

log = logging.getLogger(__name__)


def find_and_tap_vod_class(page, max_scrolls=10, include_completed=False):
    """Scroll through Studio class cards and tap the first VOD class.

    A VOD class is identified by an individual trainer name (not 'Team
    FORME', not empty) OR by the class title including 'FITBENCH' (which
    uses Team FORME as the trainer but is still a VOD).

    By default skips completed classes. Pass include_completed=True when
    the test just needs to start a class briefly (e.g. to check whether
    the HRM dialog appears on class entry, regardless of completion state).

    Returns the class title if found and tapped, or None if nothing
    eligible was found after max_scrolls.
    """
    seen_titles = set()

    for scroll in range(max_scrolls + 1):
        cards = page.find_all_by_id("card")

        for card in cards:
            try:
                detail = card.find_element(
                    AppiumBy.ID, f"{APP_PACKAGE}:id/text_detail"
                )
                d_text = detail.get_attribute("text")

                if "MIN" not in d_text:
                    continue

                title = card.find_element(
                    AppiumBy.ID, f"{APP_PACKAGE}:id/text_title"
                )
                t_title = title.get_attribute("text")

                try:
                    trainer = card.find_element(
                        AppiumBy.ID, f"{APP_PACKAGE}:id/text_trainer"
                    )
                    t_text = trainer.get_attribute("text")
                except Exception:
                    t_text = ""

                is_fitbench = "FITBENCH" in t_title.upper()
                has_individual_trainer = (
                    len(t_text) > 0 and "Team FORME" not in t_text
                )
                if not (has_individual_trainer or is_fitbench):
                    continue

                if t_title in seen_titles:
                    continue
                seen_titles.add(t_title)

                if not include_completed:
                    try:
                        card.find_element(
                            AppiumBy.ID, f"{APP_PACKAGE}:id/text_complete"
                        )
                        log.info(f"Skipping completed class: {t_title}")
                        continue
                    except Exception:
                        pass

                card.click()
                log.info(
                    f"Tapped VOD class: {t_title} - {d_text} - "
                    f"{t_text or 'Team FORME (fitbench)'}"
                )
                return t_title

            except Exception as e:
                log.debug(f"Could not read card: {e}")
                continue

        if scroll < max_scrolls:
            page.scroll_down()
            page.wait_seconds(1)

    completion_note = "" if include_completed else " non-completed"
    log.warning(
        f"No{completion_note} VOD class found after {max_scrolls} scrolls"
    )
    return None
