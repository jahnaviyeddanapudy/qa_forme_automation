"""FORME Studio device app (Android) — config.

Test accounts can be overridden via env vars. Useful when multiple QAs
share the repo but test against different Studio accounts. Defaults
below are the existing accounts — setting no env vars preserves current
behavior.

Env vars (all optional):
  FORME_STUDIO_MAIN_EMAIL          → STUDIO_MAIN_EMAIL
  FORME_STUDIO_GUEST_EMAIL         → STUDIO_GUEST_EMAIL
  FORME_PASSWORD                   → STUDIO_PASSWORD (shared across accounts)

Profile indices come from a LOCAL config file (config_local.py) that is
gitignored. See PROFILE INDEX MODEL below.
"""
import os


# --- App configuration ---
APP_PACKAGE = "com.formelife.studio"
APP_ACTIVITY = "com.formelife.studio.activity.ProfileActivity"


# --- Test accounts ---
# Studio auto-logs these in via avatar tap on ProfileActivity.
# Password is shared across accounts (same as member repo).
STUDIO_MAIN_EMAIL = os.environ.get(
    "FORME_STUDIO_MAIN_EMAIL",
    "silvanus.thomas+prod_member@formelife.com",
)
STUDIO_GUEST_EMAIL = os.environ.get(
    "FORME_STUDIO_GUEST_EMAIL",
    "silvanus.thomas+prod_member_guest1@formelife.com",
)
STUDIO_PASSWORD = os.environ.get("FORME_PASSWORD", "Trnr!Clmbr")


# =========================================================
# PROFILE INDEX MODEL
#
# ProfileActivity's recycler order is whatever the Studio app returns —
# it does NOT necessarily match visual on-screen order, and varies
# between Studios depending on which accounts have been added and in
# what order.
#
# Tests must not assume "index 0 = owner". Each QA configures their
# Studio's actual recycler indices in a local file:
#
#     surfaces/studio/config_local.py
#
# This file is GITIGNORED so each QA's values stay private and don't
# conflict in PRs. Copy from config_local.py.example to get started:
#
#     cp surfaces/studio/config_local.py.example \
#        surfaces/studio/config_local.py
#
# Then edit config_local.py to set OWNER_PROFILE_INDEX and
# GUEST1_PROFILE_INDEX for your Studio.
#
# Defaults (used when config_local.py doesn't exist):
#   OWNER_PROFILE_INDEX = 0     (most Studios have owner at index 0)
#   GUEST1_PROFILE_INDEX = None (no guest configured -> guest1 tests
#                                pytest.skip with a helpful message)
#
# Future expansion: add GUEST2_PROFILE_INDEX through GUEST5_PROFILE_INDEX
# to config_local.py.example and config.py defaults as needed (Studio
# supports up to 5 guests). Add only when an actual test needs them.
# =========================================================

try:
    from surfaces.studio_android.config_local import (
        OWNER_PROFILE_INDEX,
        GUEST1_PROFILE_INDEX,
    )
except ImportError:
    # config_local.py not created yet — use defaults. Owner=0 works for
    # most Studios; guest1=None makes guest tests skip cleanly with a
    # message pointing the QA at config_local.py.
    OWNER_PROFILE_INDEX = 0
    GUEST1_PROFILE_INDEX = None


# --- Wait timeouts (seconds) ---
WAIT_SHORT = 5
WAIT_DEFAULT = 15
WAIT_LONG = 60