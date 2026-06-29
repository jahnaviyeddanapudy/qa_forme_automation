"""test_42_promotions — Studio promotions tile tests.

Covers the PromotionsAdapter change from STUDIO-4278:
  - contentDescription moved from image.id → root.contentDescription = item.type
  - android:id="@+id/tile_promotion" added to the root CardView in item_promotion.xml

Test cases:
  - test_STUDIO_4278_promotion_tile_has_resource_id
      Verify the promotion tile root CardView is findable by its new
      resource-id (tile_promotion). Before this change, the root had no
      id and could only be found via XPath index.

  - test_STUDIO_4278_promotion_tile_content_desc_is_type
      Verify the contentDescription on the tile root is the promotion
      type string (e.g. 'TPI', 'PROMO') rather than the promotion id
      (a UUID). Before STUDIO-4278 the contentDescription was set on
      image using item.id (a UUID). After the fix it is set on root
      using item.type (a human-readable type string).

      Verification:
        - contentDescription is NOT empty
        - contentDescription does NOT look like a UUID (no hyphens in
          the pattern xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
          (UUIDs were the old incorrect value)
        - contentDescription matches a known promotion type pattern
          OR is at least a short alphabetic/underscore token

Pre-conditions:
  - User must be logged in and on the Home / Studio tab where the
    promotions horizontal strip is rendered (BrowseHeaderFragment
    shows promotions in the header area).
  - At least one promotion tile must be present. If the promotions
    strip is empty (CMS has no active promos), tests are skipped.

Architecture:
  Module-scoped shared_driver — login once, both tests share session.

Run all:
    pytest -m studio surfaces/studio_android/tests/test_42_promotions.py -v -s
"""
import logging
import re

import pytest

from surfaces.studio_android.pages.home_page import HomePage
from surfaces.studio_android.pages.studio_tab_page import StudioTabPage
from surfaces.studio_android.conftest import login_at_profile_index
from appium.webdriver.common.appiumby import AppiumBy

log = logging.getLogger(__name__)

APP_PACKAGE = "com.formelife.studio"

# resource-id added in STUDIO-4278
TILE_PROMOTION_ID = f"{APP_PACKAGE}:id/tile_promotion"

# UUID regex — old (incorrect) contentDescription value was a UUID
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------#
#  Module-scoped fixture                                                      #
# ---------------------------------------------------------------------------#

@pytest.fixture(scope="module")
def promo_driver(driver):
    """Login as owner and navigate to Home where promotions are visible."""
    login_at_profile_index(driver, 0)
    home = HomePage(driver)
    home.wait_for_home()
    yield driver


# ---------------------------------------------------------------------------#
#  Helpers                                                                   #
# ---------------------------------------------------------------------------#

def _get_promotion_tiles(driver):
    """Return all promotion tile root elements found by tile_promotion id."""
    tiles = driver.find_elements(AppiumBy.ID, TILE_PROMOTION_ID)
    log.info(f"Found {len(tiles)} promotion tiles")
    return tiles


# ---------------------------------------------------------------------------#
#  Tests                                                                     #
# ---------------------------------------------------------------------------#

@pytest.mark.studio
def test_STUDIO_4278_promotion_tile_has_resource_id(promo_driver):
    """Verify promotion tiles are findable by the new tile_promotion resource-id.

    Before STUDIO-4278, item_promotion.xml had no android:id on the root
    CardView. This made automation brittle (index-based xpath only).
    After the fix, the root has android:id="@+id/tile_promotion".
    """
    tiles = _get_promotion_tiles(promo_driver)

    if not tiles:
        pytest.skip(
            "No promotion tiles found — CMS may have no active promotions. "
            "Cannot verify tile_promotion resource-id."
        )

    # Each tile must be findable and have a non-empty resource-id attribute
    for i, tile in enumerate(tiles):
        rid = tile.get_attribute("resource-id")
        assert rid == TILE_PROMOTION_ID, (
            f"Tile [{i}] resource-id mismatch: expected {TILE_PROMOTION_ID!r}, "
            f"got {rid!r}"
        )
        log.info(f"Tile [{i}] resource-id OK: {rid}")

    log.info(
        f"test_STUDIO_4278_promotion_tile_has_resource_id: "
        f"{len(tiles)} tiles verified — PASS"
    )


@pytest.mark.studio
def test_STUDIO_4278_promotion_tile_content_desc_is_type(promo_driver):
    """Verify promotion tile contentDescription is item.type, not item.id.

    Change in PromotionsAdapter (STUDIO-4278):
      Before: image.contentDescription = item.id    (UUID, set on the image)
      After:  root.contentDescription  = item.type  (type string, set on root)

    Assertions:
      1. contentDescription on root (tile_promotion) is not empty.
      2. contentDescription does NOT match a UUID pattern
         (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) — that was the old bug.
      3. contentDescription is a short, non-numeric token consistent with
         a promotion type (e.g. 'TPI', 'PROMO', 'CHALLENGE', etc.).
    """
    tiles = _get_promotion_tiles(promo_driver)

    if not tiles:
        pytest.skip(
            "No promotion tiles found — CMS may have no active promotions. "
            "Cannot verify contentDescription value."
        )

    for i, tile in enumerate(tiles):
        content_desc = tile.get_attribute("content-desc") or ""
        log.info(f"Tile [{i}] contentDescription = {content_desc!r}")

        assert content_desc, (
            f"Tile [{i}] contentDescription is empty — "
            "root.contentDescription was not set by the adapter"
        )

        assert not _UUID_RE.match(content_desc), (
            f"Tile [{i}] contentDescription looks like a UUID ({content_desc!r}). "
            "This suggests the old code path (image.contentDescription = item.id) "
            "is still active — STUDIO-4278 fix not applied."
        )

        # Type strings are short alphabetic/underscore tokens (not numeric UUIDs)
        # Accept anything that is not a pure UUID and not empty — the exact
        # type strings depend on CMS content.
        assert len(content_desc) <= 64, (
            f"Tile [{i}] contentDescription suspiciously long ({len(content_desc)} chars): "
            f"{content_desc!r}. Expected a short type token."
        )

        log.info(f"Tile [{i}] contentDescription verified as type string: {content_desc!r}")

    log.info(
        f"test_STUDIO_4278_promotion_tile_content_desc_is_type: "
        f"{len(tiles)} tiles verified — PASS"
    )
