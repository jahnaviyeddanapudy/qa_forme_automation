"""Formelife REST API client for direct data verification in tests.

Authentication:
    Auth0 ROPC flow (same path the Android app uses) returns an id_token that
    the Formelife backend accepts as a Bearer token (confirmed in TokenAuthenticator.kt).

Key endpoint used here:
    GET /v1/user/me/history-workout
    Filter syntax: "field||$op||value"  (from UserViewModel.getWorkoutsHistory)
"""
from datetime import datetime, timedelta, timezone

import requests

_AUTH0_DOMAIN = "auth.formelife.com"
_AUTH0_CLIENT_ID = "qJEomVhiDxffneinQLX6W9lbAKK7UxXr"
_API_BASE = "https://api.production.formelife.net"

# WorkoutSessionType.value strings from WorkoutSessionType.kt
SESSION_TYPE_ANDROID_VOD = "Video on Demand"
SESSION_TYPE_LIFT_VOD    = "Lift VOD"


def get_id_token(email: str, password: str) -> str:
    """Obtain an Auth0 id_token via Resource Owner Password Credentials grant.

    The Android app's UserRepository calls authenticationAPIClient.login() which
    uses this same grant. The id_token is what TokenAuthenticator.kt sends as
    Authorization: Bearer.
    """
    resp = requests.post(
        f"https://{_AUTH0_DOMAIN}/oauth/token",
        json={
            "grant_type": "password",
            "username": email,
            "password": password,
            "client_id": _AUTH0_CLIENT_ID,
            "scope": "openid offline_access",
            "connection": "Username-Password-Authentication",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["id_token"]


def get_history_workouts(id_token: str, session_type: str, days_back: int = 90) -> list:
    """Return completed HistoryWorkout entries matching session_type.

    Uses the same filter syntax as UserViewModel.getWorkoutsHistory:
        "workout_status||$eq||Completed"
        "session_type||$eq||<value>"
        "start_time||$gte||<iso>"
        "start_time||$lte||<iso>"

    Returns the list from the PagedResponse {"data": [...]} envelope.
    """
    now = datetime.now(timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    from_dt = (now - timedelta(days=days_back)).strftime(fmt)
    to_dt   = (now + timedelta(days=1)).strftime(fmt)

    filters = [
        "workout_status||$eq||Completed",
        f"session_type||$eq||{session_type}",
        f"start_time||$gte||{from_dt}",
        f"start_time||$lte||{to_dt}",
    ]

    resp = requests.get(
        f"{_API_BASE}/v1/user/me/history-workout",
        params=[("filter", f) for f in filters],
        headers={"Authorization": f"Bearer {id_token}"},
        timeout=20,
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("data", payload) if isinstance(payload, dict) else payload
