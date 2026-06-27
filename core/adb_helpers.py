"""ADB helpers shared across every Android surface.

Use these instead of calling subprocess.run(['adb', ...]) directly — they
honor the FORME_DEVICE_UDID env var to target the correct device when
multiple devices are connected (phone + studio + CLMBR, etc.).
"""
import os
import subprocess


def adb_cmd(*args):
    """Build an adb command with -s <udid> prefix if FORME_DEVICE_UDID is
    set, otherwise plain 'adb ...'. Ensures the command targets the correct
    device when multiple devices are connected for parallel test runs."""
    udid = os.environ.get("FORME_DEVICE_UDID", "").strip()
    if udid:
        return ["adb", "-s", udid, *args]
    return ["adb", *args]


def detect_device_profile():
    """Detect device manufacturer + model via adb and return a normalized
    profile name. Honors FORME_DEVICE_PROFILE env var as an override.

    Known profiles:
      - 'oneplus'   — OnePlus phone (e.g. OnePlus 9 5G), member app target
      - 'samsung'   — Samsung phone/tablet, member app target
      - 'pixel'     — Google Pixel, member app target
      - 'studio'    — FORME Studio device, studio app target
      - 'other'     — anything else

    Returns (profile, manufacturer, model)."""
    override = os.environ.get("FORME_DEVICE_PROFILE", "").strip().lower()
    try:
        mfr_result = subprocess.run(
            adb_cmd("shell", "getprop", "ro.product.manufacturer"),
            capture_output=True, text=True, timeout=5,
        )
        mfr = mfr_result.stdout.strip()
        model_result = subprocess.run(
            adb_cmd("shell", "getprop", "ro.product.model"),
            capture_output=True, text=True, timeout=5,
        )
        model = model_result.stdout.strip()
    except Exception:
        mfr = ""
        model = ""

    if override:
        return override, mfr, model

    mfr_l = mfr.lower()
    model_l = model.lower()
    if "oneplus" in mfr_l:
        return "oneplus", mfr, model
    if "samsung" in mfr_l:
        return "samsung", mfr, model
    if "google" in mfr_l or "pixel" in model_l:
        return "pixel", mfr, model
    if "forme" in mfr_l and "studio" in model_l:
        return "studio", mfr, model
    return "other", mfr, model
