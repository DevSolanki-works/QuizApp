"""
limiter.py — Per-IP rate limiting for Forge.

SECURITY NOTE — X-Forwarded-For trust model
============================================
Cloud Run sits behind Google's load balancer, which appends the real client
IP as the LAST entry in the X-Forwarded-For chain. An attacker who sends
requests directly (e.g. via curl or a WebSocket client) can add arbitrary
IPs at the FRONT of that header, making the first entry untrustworthy.

We always extract the LAST (rightmost) XFF entry, which is the one inserted
by the infrastructure we control. This prevents rate-limit bypass via header
spoofing.

Usage in routers:
    from app.core.limiter import is_rate_limited, extract_real_ip

    ip = extract_real_ip(request)          # for HTTP endpoints
    ip = extract_real_ip_from_ws(websocket) # for WebSocket endpoints
"""

import time
from fastapi import Request, WebSocket

from app.core import state


# ── Per-action limits ─────────────────────────────────────────────────────────
# These are intentionally conservative. Adjust if legitimate usage hits them.
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "room":     (5,  60),   # 5 room creations per minute
    "quiz":     (3,  60),   # 3 quiz generations per minute  
    "auth":     (10, 60),   # 10 auth attempts per minute
    "ws_join":  (15, 60),   # 15 WS connections per minute
    "answer":   (60, 60),   # 60 answers per minute (10 questions × 6 reconnects)
}


def extract_real_ip(request: Request) -> str:
    """
    Extract the real client IP from an HTTP request.

    Cloud Run appends the real IP as the last entry in X-Forwarded-For.
    We trust that entry, not the (potentially spoofed) first entry.
    """
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        # Split, strip whitespace, take the LAST entry
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]

    # Fall back to direct connection IP (local dev / no proxy)
    if request.client:
        return request.client.host

    return "0.0.0.0"


def extract_real_ip_from_ws(websocket: WebSocket) -> str:
    """
    Extract the real client IP from a WebSocket connection.

    Same XFF trust model as HTTP — last entry wins.
    """
    xff = websocket.headers.get("X-Forwarded-For", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]

    if websocket.client:
        return websocket.client.host

    return "0.0.0.0"


def is_rate_limited(
    ip: str,
    action: str = "quiz",
    limit: int | None = None,
    period: int | None = None,
) -> bool:
    """
    Check if an IP has exceeded the rate limit for an action.

    If limit/period are not supplied, the defaults from RATE_LIMITS are used.
    Returns True if the request should be blocked, False if allowed.
    """
    default_limit, default_period = RATE_LIMITS.get(action, (10, 60))
    limit  = limit  if limit  is not None else default_limit
    period = period if period is not None else default_period

    now = time.time()
    key = f"{action}:{ip}"

    if key not in state.quiz_rate_limits:
        state.quiz_rate_limits[key] = []

    # Evict timestamps outside the current window
    state.quiz_rate_limits[key] = [
        ts for ts in state.quiz_rate_limits[key]
        if now - ts < period
    ]

    if len(state.quiz_rate_limits[key]) >= limit:
        return True

    state.quiz_rate_limits[key].append(now)
    return False
