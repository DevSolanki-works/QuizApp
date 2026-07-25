"""
services/google_auth.py — Server-side Google OAuth refresh-token exchange.

WHY THIS EXISTS:
  Native Google Sign-In ID tokens expire after ~1hr. The Capacitor plugin
  has no silent-refresh method (confirmed against its own type defs) —
  its only option is signIn(), which shows a real account picker UI.
  Calling that from a background timer caused a real production incident
  (repeating popup loop, July 2026 — see CLAUDE.md Decisions Log).

  This module implements the actual standard fix: exchange a one-time
  serverAuthCode (requested via the 'scopes' option at sign-in) for a
  long-lived refresh token, ONCE, server-side. From then on, the client
  never touches the native Google plugin again to get a fresh token —
  it just calls our own /auth/refresh endpoint, which uses the stored
  refresh token to mint a new ID token from Google directly. No native
  UI is ever shown again after the very first sign-in.

WHY A SEPARATE FILE FROM profiles.py:
  Refresh tokens are long-lived, sensitive credentials — a fundamentally
  different risk category from coins/trophies. Keeping them in their own
  store means they're never touched by routine economy read/write paths,
  and can be handled with tighter care (e.g. encrypted-at-rest) later
  without restructuring the whole profile store.
"""

from __future__ import annotations

import json
import os
import time
from threading import RLock
from typing import Any, Optional

import httpx

from app.core.config import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

_lock = RLock()


def _store_path() -> str:
    """Same data directory as profiles.json, separate filename."""

    profile_path = settings.PROFILE_STORE_PATH
    directory = os.path.dirname(profile_path) or "."
    return os.path.join(directory, "refresh_tokens.json")


def _load_all() -> dict[str, dict[str, Any]]:
    path = _store_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _save_all(store: dict[str, dict[str, Any]]) -> None:
    path = _store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(store, fh, ensure_ascii=True, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


async def exchange_code_for_tokens(auth_code: str) -> dict[str, Any]:
    """
    Trade a one-time serverAuthCode for Google's token set.

    Google's response includes an access_token, id_token, and — critically,
    ONLY on this first exchange — a refresh_token. Google does not return
    a refresh_token on subsequent exchanges for the same user unless the
    prior grant was revoked, which is why this must be stored, not re-fetched.
    """

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": auth_code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                # Native/installed-app flow — no redirect actually happens,
                # but Google's token endpoint requires this exact literal
                # value for server-auth-code exchanges from mobile SDKs.
                "grant_type": "authorization_code",
                "redirect_uri": "",
            },
        )
        if resp.status_code != 200:
            raise ValueError(f"Google token exchange failed: {resp.status_code} {resp.text}")
        return resp.json()


def store_refresh_token(user_id: str, refresh_token: str) -> None:
    """Persist a user's refresh token. Overwrites any prior one on file."""

    with _lock:
        store = _load_all()
        store[user_id] = {
            "refresh_token": refresh_token,
            "stored_at": time.time(),
        }
        _save_all(store)


def has_refresh_token(user_id: str) -> bool:
    with _lock:
        store = _load_all()
        return user_id in store


async def refresh_id_token(user_id: str) -> Optional[dict[str, Any]]:
    """
    Use a stored refresh token to mint a fresh ID token from Google.

    Returns None if no refresh token is on file for this user (e.g. they
    signed in on a build before this system existed, or on a platform
    where serverAuthCode isn't available — falls back to the client's
    existing manual-reauth flow in that case).
    """

    with _lock:
        store = _load_all()
        entry = store.get(user_id)

    if not entry or not entry.get("refresh_token"):
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": entry["refresh_token"],
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            # Refresh token itself can be revoked/expired (e.g. user
            # revoked app access in their Google Account settings) — the
            # caller falls back to a manual sign-in in that case, same
            # as any other failed refresh.
            return None
        return resp.json()