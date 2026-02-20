import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from core.security import get_current_user, get_password_hash, verify_password, create_access_token
from models.schemas import UserAuthRequest
from services.auth import InstagramAuth, PinterestAuth, MetaAuth, YouTubeAuth
from core.config import FRONTEND_URL

router = APIRouter()
logger = logging.getLogger("social_insights.routes.auth")

# These will be set by main.py
users_repo = None
sync_service = None

@router.post("/register")
async def register(req: UserAuthRequest):
    existing = await users_repo.get(f"USER#{req.user_id}", "PROFILE")
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = get_password_hash(req.password)
    await users_repo.create_user(email=req.user_id, password_hash=hashed_password)
    return {"message": "User created successfully"}

@router.post("/login")
async def login(req: UserAuthRequest):
    user = await users_repo.get(f"USER#{req.user_id}", "PROFILE")
    if not user or not verify_password(req.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Incorrect user ID or password")
    
    access_token = create_access_token(data={"sub": req.user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me")
async def check_auth(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}

# --- OAuth Endpoints ---

@router.get("/auth/instagram/login")
async def auth_instagram_login(user_id: str = Depends(get_current_user)):
    auth_client = InstagramAuth()
    url = auth_client.get_auth_url(state=user_id)
    return {"url": url}

@router.get("/auth/instagram/callback")
async def auth_instagram_callback(code: str, state: Optional[str] = None):
    auth_client = InstagramAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Instagram code for token")
    
    access_token = token_data.get("access_token")
    user_id = state or "anonymous"
    
    from services.instagram import InstagramClient
    client = InstagramClient(access_token)
    accounts = client.get_accounts()
    
    if not accounts:
        return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=error&message=no_business_accounts")

    for acc in accounts:
        normalized_id = acc["account_id"].lower()
        await users_repo.add_integration(
            user_id=user_id,
            platform="instagram",
            account_id=normalized_id,
            encrypted_access_token=access_token,
            encrypted_refresh_token=None,
            account_name=acc.get("username", acc["account_id"]),
            additional_info={"status": "Active", "page_name": acc.get("page_name")}
        )
        await sync_service.sync_instagram_account(normalized_id, access_token)
        await users_repo.log_activity(user_id, "add_integration", {"platform": "instagram", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=success&platform=instagram&count={len(accounts)}")

@router.get("/auth/pinterest/login")
async def auth_pinterest_login(user_id: str = Depends(get_current_user)):
    auth_client = PinterestAuth()
    url = auth_client.get_auth_url(state=user_id)
    return {"url": url}

@router.get("/auth/pinterest/callback")
async def auth_pinterest_callback(code: str, state: Optional[str] = None):
    auth_client = PinterestAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Pinterest code for token")
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    user_id = state or "anonymous"
    
    from services.pinterest import PinterestClient
    client = PinterestClient(access_token)
    profile = client.get_account_info()
    
    if not profile:
        return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=error&message=profile_fetch_failed")

    normalized_id = profile.get("username", "pinterest_user").lower()
    await users_repo.add_integration(
        user_id=user_id,
        platform="pinterest",
        account_id=normalized_id,
        encrypted_access_token=access_token,
        encrypted_refresh_token=refresh_token,
        account_name=profile.get("username", normalized_id),
        additional_info={"status": "Active"}
    )
    await sync_service.sync_pinterest_account(normalized_id, access_token)
    await users_repo.log_activity(user_id, "add_integration", {"platform": "pinterest", "account_id": normalized_id})

    return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=success&platform=pinterest")

@router.get("/auth/meta/login")
async def auth_meta_login(user_id: str = Depends(get_current_user)):
    auth_client = MetaAuth()
    url = auth_client.get_auth_url(state=user_id)
    return {"url": url}

@router.get("/auth/meta/callback")
async def auth_meta_callback(code: str, state: Optional[str] = None):
    auth_client = MetaAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Meta code for token")
    
    access_token = token_data.get("access_token")
    user_id = state or "anonymous"
    
    from services.meta import MetaClient
    client = MetaClient(access_token)
    pages = client.get_pages()
    
    if not pages:
        return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=error&message=no_facebook_pages")

    for page in pages:
        normalized_id = page["account_id"].lower()
        token_to_save = page.get("access_token") or access_token
        await users_repo.add_integration(
            user_id=user_id,
            platform="facebook",
            account_id=normalized_id,
            encrypted_access_token=token_to_save,
            encrypted_refresh_token=None,
            account_name=page["name"],
            additional_info={"status": "Active", "category": page.get("category")}
        )
        await sync_service.sync_meta_account(normalized_id, token_to_save)
        await users_repo.log_activity(user_id, "add_integration", {"platform": "facebook", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=success&platform=meta&count={len(pages)}")

@router.get("/auth/youtube/login")
async def auth_youtube_login(user_id: str = Depends(get_current_user)):
    auth_client = YouTubeAuth()
    url = auth_client.get_auth_url(state=user_id)
    return {"url": url}

@router.get("/auth/youtube/callback")
async def auth_youtube_callback(code: str, state: Optional[str] = None):
    auth_client = YouTubeAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange YouTube code for token")
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    user_id = state or "anonymous"
    
    from services.youtube import YouTubeClient
    client = YouTubeClient(access_token)
    channels = client.get_channels()
    
    if not channels:
        return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=error&message=no_youtube_channels")

    for channel in channels:
        normalized_id = channel["account_id"]
        await users_repo.add_integration(
            user_id=user_id,
            platform="youtube",
            account_id=normalized_id,
            encrypted_access_token=access_token,
            encrypted_refresh_token=refresh_token,
            account_name=channel["name"],
            additional_info={"status": "Active", "snippet": channel.get("snippet")}
        )
        await sync_service.sync_youtube_account(normalized_id, access_token)
        await users_repo.log_activity(user_id, "add_integration", {"platform": "youtube", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{FRONTEND_URL}/integrations?status=success&platform=youtube&count={len(channels)}")
