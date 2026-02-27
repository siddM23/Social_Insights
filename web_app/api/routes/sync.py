import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from core.security import get_current_user
from core.config import SYNC_MAX_LIMIT

router = APIRouter()
logger = logging.getLogger("social_insights.routes.sync")

# Inject dependencies from main.py
users_repo = None
sync_service = None

@router.get("/sync/status")
async def get_sync_status(user_id: str = Depends(get_current_user)):
    logger.info(f"Fetching sync status for user {user_id}")
    status = await users_repo.get_sync_status(user_id)
    if not status:
        return {
            "sync_count": 0,
            "sync_limit_stat": False,
            "last_sync_time": None,
            "max_limit": SYNC_MAX_LIMIT
        }
    return {
        "sync_count": int(status.get('sync_count', 0)),
        "sync_limit_stat": status.get('sync_limit_stat', False),
        "last_sync_time": status.get('last_sync_time'),
        "max_limit": SYNC_MAX_LIMIT
    }

@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    logger.info(f"Manual sync requested by user {user_id}")
    now = datetime.datetime.utcnow()
    await users_repo.log_activity(user_id, "trigger_sync")
    
    status = await users_repo.get_sync_status(user_id)
    if not status:
        status = {'sync_count': 0, 'sync_limit_stat': False, 'last_sync_time': None}

    sync_count = int(status.get('sync_count', 0))
    last_sync_str = status.get('last_sync_time')
    
    if status.get('sync_limit_stat') and last_sync_str:
        last_sync = datetime.datetime.fromisoformat(last_sync_str)
        if (now - last_sync).total_seconds() < (3 * 3600):
            wait_remaining = int((3 * 3600) - (now - last_sync).total_seconds())
            logger.warning(f"Sync rate limited for {user_id}. Remaining: {wait_remaining // 60}m")
            raise HTTPException(
                status_code=429, 
                detail=f"Sync limit reached. Please wait {wait_remaining // 60} minutes."
            )
        else:
            sync_count = 0
            status['sync_limit_stat'] = False

    sync_count += 1
    new_status = {
        'sync_count': sync_count,
        'sync_limit_stat': True if sync_count >= SYNC_MAX_LIMIT else False,
        'last_sync_time': now.isoformat()
    }
    await users_repo.update_sync_status(user_id, new_status)
    logger.info(f"Starting background sync task for {user_id}")
    background_tasks.add_task(sync_service.run_full_sync)
    
    return {
        "message": "Sync started in background",
        "sync_count": sync_count,
        "limit_reached": new_status['sync_limit_stat']
    }
