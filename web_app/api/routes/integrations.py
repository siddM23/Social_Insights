import logging
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from models.schemas import IntegrationRequest, ActivityLogRequest
from core.config import SYNC_MAX_LIMIT

router = APIRouter()
logger = logging.getLogger("social_insights.routes.integrations")

# Inject dependencies from main.py
users_repo = None
sync_service = None

@router.post("/integrations")
async def add_integration(req: IntegrationRequest, user_id: str = Depends(get_current_user)):
    if not req.access_token or not req.access_token.strip():
        raise HTTPException(status_code=400, detail="Access token is required and cannot be empty")
        
    await users_repo.add_integration(
        user_id=user_id,
        platform=req.platform,
        account_id=req.account_id,
        encrypted_access_token=req.access_token,
        encrypted_refresh_token=None,
        account_name=req.account_name,
        additional_info=req.additional_info
    )
    
    if req.platform == "instagram":
        await sync_service.sync_instagram_account(req.account_id, req.access_token)
    
    await users_repo.log_activity(user_id, "add_integration", {"platform": req.platform, "account_id": req.account_id})
    return {"message": "Integration saved", "data": req.dict()}

@router.get("/integrations/{platform}/{account_id}")
async def get_integration(platform: str, account_id: str, user_id: str = Depends(get_current_user)):
    sk = f"INTEGRATION#{platform}#{account_id}"
    item = await users_repo.get(f"USER#{user_id}", sk)
    
    if not item:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    clean_item = {k: v for k, v in item.items() if k not in ["encrypted_access_token", "encrypted_refresh_token"]}
    return clean_item

@router.get("/integrations")
async def list_integrations(user_id: str = Depends(get_current_user)):
    items = await users_repo.list_integrations(user_id)
    normalized = []
    for item in items:
        clean_item = {k: v for k, v in item.items() if k not in ["encrypted_access_token", "encrypted_refresh_token"]}
        normalized.append(clean_item)
    return normalized

@router.delete("/integrations/{platform}/{account_id}")
async def delete_integration(platform: str, account_id: str, user_id: str = Depends(get_current_user)):
    sk = f"INTEGRATION#{platform}#{account_id}"
    await users_repo.delete(f"USER#{user_id}", sk)
    await users_repo.log_activity(user_id, "delete_integration", {"platform": platform, "account_id": account_id})
    return {"message": "Integration deleted"}

@router.post("/activity")
async def log_activity(req: ActivityLogRequest, user_id: str = Depends(get_current_user)):
    await users_repo.log_activity(user_id, req.activity_type, req.details)
    return {"status": "logged"}
