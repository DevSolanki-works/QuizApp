"""
Authentication router for Google Login.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.config import settings
from app.services.profiles import get_or_create_profile

logger = logging.getLogger(__name__)
router = APIRouter()


class GoogleAuthRequest(BaseModel):
    credential: str


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    coins: float
    trophies: int


@router.post("/google", response_model=UserInfo)
async def google_auth(body: GoogleAuthRequest):
    """
    Verify a Google ID token and return user info.
    """
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(
            body.credential, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        )

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        userid = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        picture = idinfo.get('picture', '')

        logger.info("Successfully authenticated user %s (%s)", name, email)

        profile = get_or_create_profile(userid, email=email, name=name, picture=picture)

        return UserInfo(
            id=userid,
            email=email,
            name=name,
            picture=picture,
            coins=profile["coins"],
            trophies=profile["trophies"],
        )

    except ValueError as e:
        # Invalid token
        logger.warning("Invalid Google token received: %s", e)
        raise HTTPException(status_code=401, detail="Invalid authentication credential")
    except Exception as e:
        logger.error("Error during Google auth: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error during authentication")
