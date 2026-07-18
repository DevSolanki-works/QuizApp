"""Endpoint for registering a device's FCM token after Google sign-in."""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.routers.http import _verify_google_token  # reuse existing ownership check
from app.services.push import register_token

logger = logging.getLogger(__name__)
router = APIRouter()


class RegisterTokenRequest(BaseModel):
    user_id: str
    fcm_token: str


@router.post("/push/register-token")
async def register_token_endpoint(
    body: RegisterTokenRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Store/refresh the caller's FCM device token, ownership-verified."""

    credential = ""
    if authorization and authorization.startswith("Bearer "):
        credential = authorization[len("Bearer "):]

    verified_uid = _verify_google_token(credential)
    if verified_uid != body.user_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match the requested user account.",
        )

    try:
        await register_token(body.user_id, body.fcm_token)
        return {"ok": True}
    except Exception as e:
        logger.error("Push token registration failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not register device token")