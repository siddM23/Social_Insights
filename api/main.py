from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from Db.database import DynamoDB
import os
import requests
import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
from auth import InstagramAuth, PinterestAuth, MetaAuth, YouTubeAuth
from fastapi.responses import RedirectResponse
import jwt
import bcrypt

# Monkeypatch bcrypt for passlib compatibility (bcrypt 4.0+ removed __about__)
# This fixes AttributeError: module 'bcrypt' has no attribute '__about__'
if not hasattr(bcrypt, "__about__"):
    try:
        from bcrypt import __version__ as bcrypt_version
        class About:
            __version__ = bcrypt_version
        bcrypt.__about__ = About()
    except ImportError:
        pass
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("social_insights")

# Load environment variables
load_dotenv()

# Initialize DB instances
integrations_db = DynamoDB('socials_integrations')
metrics_db = DynamoDB('social_metrics')
status_db = DynamoDB('app_status')
users_db = DynamoDB('social_users')
activity_db = DynamoDB('user_activity')

# --- Auth Utilities ---
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(token: Optional[str] = None, oauth_token: str = Depends(oauth2_scheme)):
    # Fallback to query param if header is missing (useful for GET redirects)
    actual_token = oauth_token if oauth_token else token
    
    if not actual_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        payload = jwt.decode(actual_token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# --- Activity Logger ---
def log_user_activity(user_id: str, activity_type: str, details: Dict[str, Any] = None):
    try:
        timestamp = datetime.datetime.utcnow().isoformat()
        activity_db.save_item({
            "user_id": user_id,
            "timestamp": timestamp,
            "activity_type": activity_type,
            "details": details or {}
        })
        logger.info(f"Logged activity: {activity_type} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip table creation in production/Vercel to avoid timeouts
    # Only use for local development if needed
    logger.info("Social Insights Backend Starting...")
    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "alive", "timestamp": datetime.datetime.utcnow().isoformat()}

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IntegrationRequest(BaseModel):
    platform: str
    account_id: str
    account_name: str
    access_token: str
    additional_info: Optional[Dict[str, Any]] = None

class MetricRequest(BaseModel):
    account_id: str
    timestamp: str 
    followers_total: int
    followers_new: int
    views_organic: int
    views_ads: int
    interactions: int
    profile_visits: int
    accounts_reached: int

class UserAuthRequest(BaseModel):
    user_id: str
    password: str

class ActivityLogRequest(BaseModel):
    activity_type: str
    details: Optional[Dict[str, Any]] = None

class CustomMetricRequest(BaseModel):
    start_date: str # YYYY-MM-DD
    end_date: str # YYYY-MM-DD

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Social Insights Backend"}

# --- Auth Endpoints ---

@app.get("/auth/instagram/login")
async def auth_instagram_login(user_id: str = Depends(get_current_user)):
    logger.info(f"Instagram login URL requested by user: {user_id}")
    auth_client = InstagramAuth()
    url = auth_client.get_auth_url(state=user_id)
    return RedirectResponse(url=url)

@app.get("/auth/instagram/callback")
async def auth_instagram_callback(code: str, state: Optional[str] = None):
    auth_client = InstagramAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Instagram code for token")
    
    access_token = token_data.get("access_token")
    user_id = state or "anonymous"
    
    # FETCH ACCOUNT DETAILS AUTOMATICALLY
    from Sources.instagram import InstagramClient
    client = InstagramClient(access_token)
    accounts = client.get_accounts()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not accounts:
        return RedirectResponse(url=f"{frontend_url}/integrations?status=error&message=no_business_accounts")

    # For now, we auto-save all discovered accounts
    for acc in accounts:
        normalized_id = acc["account_id"].lower()
        integrations_db.save_item({
            "platform": "instagram",
            "account_id": normalized_id,
            "account_name": acc.get("username", acc["account_id"]),
            "access_token": access_token,
            "owner_id": user_id,
            "additional_info": {"status": "Active", "page_name": acc.get("page_name")}
        })
        # Inline sync (Vercel compatible)
        sync_account(normalized_id, access_token)
        # Log Activity
        log_user_activity(user_id, "add_integration", {"platform": "instagram", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=instagram&count={len(accounts)}")

@app.get("/auth/pinterest/login")
async def auth_pinterest_login(user_id: str = Depends(get_current_user)):
    logger.info(f"Pinterest login URL requested by user: {user_id}")
    auth_client = PinterestAuth()
    url = auth_client.get_auth_url(state=user_id)
    return RedirectResponse(url=url)

@app.get("/auth/pinterest/callback") # Matches user's recent change
async def auth_pinterest_callback(code: str, state: Optional[str] = None):
    auth_client = PinterestAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Pinterest code for token")
    
    access_token = token_data.get("access_token")
    user_id = state or "anonymous"
    
    from Sources.pinterest import PinterestClient
    client = PinterestClient(access_token)
    profile = client.get_account_info()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not profile:
        return RedirectResponse(url=f"{frontend_url}/integrations?status=error&message=profile_fetch_failed")

    normalized_id = profile.get("username", "pinterest_user").lower()
    integrations_db.save_item({
        "platform": "pinterest",
        "account_id": normalized_id,
        "account_name": profile.get("username", normalized_id),
        "access_token": access_token,
        "owner_id": user_id,
        "additional_info": {"status": "Active"}
    })
    
    # Inline sync (Vercel compatible)
    sync_pinterest_account(normalized_id, access_token)
    
    # Log Activity
    log_user_activity(user_id, "add_integration", {"platform": "pinterest", "account_id": normalized_id})

    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=pinterest")

@app.get("/auth/meta/login")
async def auth_meta_login(user_id: str = Depends(get_current_user)):
    logger.info(f"Meta login URL requested by user: {user_id}")
    auth_client = MetaAuth()
    url = auth_client.get_auth_url(state=user_id)
    return RedirectResponse(url=url)

@app.get("/auth/meta/callback")
async def auth_meta_callback(code: str, state: Optional[str] = None):
    logger.info("Meta callback received. Exchanging code for token...")
    auth_client = MetaAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        logger.error("Failed to exchange Meta code for token")
        raise HTTPException(status_code=400, detail="Failed to exchange Meta code for token")
    
    access_token = token_data.get("access_token")
    user_id = state or "anonymous"
    
    # FETCH ACCOUNT DETAILS AUTOMATICALLY
    from Sources.meta import MetaClient
    client = MetaClient(access_token)
    pages = client.get_pages()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not pages:
        logger.warning("No Facebook Pages found for this account")
        return RedirectResponse(url=f"{frontend_url}/integrations?status=error&message=no_facebook_pages")

    # Save all discovered pages
    for page in pages:
        normalized_id = page["account_id"].lower()
        # Use Page Access Token if available, fallback to user token
        token_to_save = page.get("access_token") or access_token
        
        integrations_db.save_item({
            "platform": "facebook", 
            "account_id": normalized_id,
            "account_name": page["name"],
            "access_token": token_to_save,
            "owner_id": user_id,
            "additional_info": {"status": "Active", "category": page.get("category")}
        })
        # Inline sync (Vercel compatible)
        sync_meta_account(normalized_id, token_to_save)
        # Log Activity
        log_user_activity(user_id, "add_integration", {"platform": "facebook", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=meta&count={len(pages)}")

@app.get("/auth/youtube/login")
async def auth_youtube_login(user_id: str = Depends(get_current_user)):
    logger.info(f"YouTube login URL requested by user: {user_id}")
    auth_client = YouTubeAuth()
    url = auth_client.get_auth_url(state=user_id)
    return RedirectResponse(url=url)

@app.get("/auth/youtube/callback")
async def auth_youtube_callback(code: str, state: Optional[str] = None):
    logger.info("YouTube callback received. Exchanging code for token...")
    auth_client = YouTubeAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        logger.error("Failed to exchange YouTube code for token")
        raise HTTPException(status_code=400, detail="Failed to exchange YouTube code for token")
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token") # Google usually gives refresh token in first auth
    user_id = state or "anonymous"
    
    logger.info("Token exchange successful. Fetching YouTube channels...")
    
    # FETCH ACCOUNT DETAILS AUTOMATICALLY
    from Sources.youtube import YouTubeClient
    client = YouTubeClient(access_token)
    channels = client.get_channels()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not channels:
        logger.warning("No YouTube Channels found for this account")
        return RedirectResponse(url=f"{frontend_url}/integrations?status=error&message=no_youtube_channels")

    logger.info(f"Found {len(channels)} YouTube channels. Saving...")
    for channel in channels:
        normalized_id = channel["account_id"]
        
        integrations_db.save_item({
            "platform": "youtube", 
            "account_id": normalized_id,
            "account_name": channel["name"],
            "access_token": access_token,
            "owner_id": user_id,
            "additional_info": {
                "status": "Active", 
                "refresh_token": refresh_token,
                "snippet": channel.get("snippet")
            }
        })
        # Inline sync (Vercel compatible)
        sync_youtube_account(normalized_id, access_token)
        # Log Activity
        log_user_activity(user_id, "add_integration", {"platform": "youtube", "account_id": normalized_id})
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=youtube&count={len(channels)}")

# --- User Auth Endpoints ---

@app.post("/register")
async def register(req: UserAuthRequest):
    # Check if user exists
    existing = users_db.get_item({"user_id": req.user_id})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = get_password_hash(req.password)
    users_db.save_item({
        "user_id": req.user_id,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow().isoformat()
    })
    return {"message": "User created successfully"}

@app.post("/login")
async def login(req: UserAuthRequest):
    user = users_db.get_item({"user_id": req.user_id})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect user ID or password")
    
    access_token = create_access_token(data={"sub": req.user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/activity")
async def log_activity(req: ActivityLogRequest, user_id: str = Depends(get_current_user)):
    log_user_activity(user_id, req.activity_type, req.details)
    return {"status": "logged"}

@app.get("/auth/me")
async def check_auth(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}

# --- Integrations Endpoints ---

@app.post("/integrations")
async def add_integration(req: IntegrationRequest, user_id: str = Depends(get_current_user)):
    if not req.access_token or not req.access_token.strip():
        raise HTTPException(status_code=400, detail="Access token is required and cannot be empty")
        
    item = req.dict()
    item["owner_id"] = user_id # Track ownership
    success = integrations_db.save_item(item)
    
    if req.platform == "instagram":
        # Inline sync (Vercel compatible)
        sync_account(req.account_id, req.access_token)
    
    # LOG ACTIVITY
    log_user_activity(user_id, "add_integration", {"platform": req.platform, "account_id": req.account_id})

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save integration")
    return {"message": "Integration saved", "data": item}

@app.get("/integrations/{platform}/{account_id}")
def get_integration(platform: str, account_id: str, user_id: str = Depends(get_current_user)):
    item = integrations_db.get_item({'platform': platform, 'account_id': account_id})
    if not item:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Security: Remove sensitive token before sending to frontend
    clean_item = {k: v for k, v in item.items() if k != "access_token"}
    return clean_item

@app.get("/integrations")
def list_integrations(user_id: str = Depends(get_current_user)):
    items = integrations_db.scan_items()
    normalized = []
    for item in items:
        # Security: Remove sensitive token before sending to frontend
        clean_item = {k: v for k, v in item.items() if k != "access_token"}
        if 'account_name' not in clean_item:
             clean_item['account_name'] = clean_item.get('account_id', 'Unknown')
        normalized.append(clean_item)
    return normalized

@app.delete("/integrations/{platform}/{account_id}")
def delete_integration(platform: str, account_id: str, user_id: str = Depends(get_current_user)):
    # Verify existence before deleting
    existing = integrations_db.get_item({'platform': platform, 'account_id': account_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Integration not found")

    success = integrations_db.delete_item({'platform': platform, 'account_id': account_id})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete integration")
    
    # LOG ACTIVITY
    log_user_activity(user_id, "delete_integration", {"platform": platform, "account_id": account_id})
    
    logger.info(f"Deleted {platform} integration: {account_id}")
    logger.info(f"Deleted {platform} integration: {account_id}")
    return {"message": "Integration deleted"}

@app.post("/metrics/custom_range")
async def get_custom_range_metrics(req: CustomMetricRequest, user_id: str = Depends(get_current_user)):
    """
    Fetch metrics for all user accounts for a custom date range.
    Returns ad-hoc data structure.
    """
    logger.info(f"Fetching custom metrics for {user_id} from {req.start_date} to {req.end_date}")
    
    # 1. Get all integrations for user
    # Note: integrations_db.scan_items() gets ALL items. In real app, we should query by owner_id or filter.
    # For now, we scan and filter.
    all_items = integrations_db.scan_items()
    
    # DEBUG LOGGING START
    logger.info(f"Total items in DB: {len(all_items)}")
    for item in all_items:
        logger.info(f"Item ID: {item.get('account_id')} | Platform: {item.get('platform')} | Owner: {item.get('owner_id')}")
    # DEBUG LOGGING END

    # Include items owned by user OR items with no owner (legacy/global)
    user_integrations = [
        i for i in all_items 
        if i.get('owner_id') == user_id or i.get('owner_id') is None
    ]
    
    logger.info(f"Found {len(user_integrations)} integrations for user {user_id}")
    
    results = []
    
    import datetime
    
    # Helper to parse dates to timestamps
    try:
        start_dt = datetime.datetime.strptime(req.start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(req.end_date, "%Y-%m-%d")
        # Set end_dt to end of day? 
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    for acc in user_integrations:
        platform = acc.get('platform')
        account_id = acc.get('account_id')
        access_token = acc.get('access_token')
        
        # skip if missing key info
        if not platform or not account_id: 
            continue
            
        logger.info(f"Fetching custom metrics for {platform} account {account_id}")
        metric_data = None
        
        try:
            if platform == 'instagram':
                from Sources.instagram import InstagramClient
                client = InstagramClient(access_token)
                
                # Fetch Custom
                # Note: 'interactions' needs special handling in IG
                custom_insight = client.get_user_insights(account_id, since=start_ts, until=end_ts)
                interactions = client.get_media_interactions(account_id, since_ts=start_ts, until_ts=end_ts)
                custom_insight['interactions'] = interactions
                metric_data = custom_insight

            elif platform in ['meta', 'facebook']:
                from Sources.meta import MetaClient
                client = MetaClient(access_token)
                metric_data = client.get_page_insights(account_id, since=start_ts, until=end_ts)

            elif platform == 'pinterest':
                from Sources.pinterest import PinterestClient
                client = PinterestClient(access_token)
                metric_data = client.get_analytics(days=0, start_date_str=req.start_date, end_date_str=req.end_date)
                
                # Pinterest returns schema: views, clicks, saves, engagements
                # Map to standard
                # (function inside sync_pinterest_account does this mapping, logic duplicated for speed here)
                s = metric_data
                metric_data = {
                    'followers_new': 0,
                    'views_organic': s.get('views', 0),
                    'views_ads': 0,
                    'interactions': s.get('engagements', 0),
                    'profile_visits': s.get('clicks', 0),
                    'accounts_reached': s.get('views', 0),
                    'saves': s.get('saves', 0),
                    'followers_total': s.get('audience', 0) # Fallback
                }

            elif platform == 'youtube':
                from Sources.youtube import YouTubeClient
                client = YouTubeClient(access_token)
                metric_data = client.get_channel_insights(account_id, start_date=req.start_date, end_date=req.end_date)
            
            if metric_data:
                 logger.info(f"Successfully fetched metrics for {account_id}")
            else:
                 logger.warning(f"Fetched None metrics for {account_id}")

        except Exception as e:
            logger.error(f"Error fetching custom metrics for {platform}/{account_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # metric_data will be None
        
        if metric_data:
            # Construct result item matching dashboard expectations
            results.append({
                "accountName": acc.get('account_name', account_id),
                "platform": platform,
                "data": {
                    "custom_period": metric_data,
                    "followers_total": metric_data.get('followers_total', 0) # Might be 0 if endpoint didn't fetch profile
                }
            })

    logger.info(f"Returning {len(results)} custom metric results")
    return results

# --- Metrics Endpoints ---

@app.post("/metrics")
def add_metric(req: MetricRequest):
    item = req.dict()
    success = metrics_db.save_item(item)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save metric")
    return {"message": "Metric saved", "data": item}

@app.get("/metrics/{platform}/{account_id}")
def get_metrics_for_platform_account(platform: str, account_id: str):
    # Use composite key to prevent platform collision
    lookup_id = f"{platform.lower()}#{account_id.lower()}"
    response = metrics_db.table.query(
        KeyConditionExpression='account_id = :acc',
        ExpressionAttributeValues={':acc': lookup_id},
        ScanIndexForward=False # Newest first
    )
    items = response.get('Items', [])
    
    # FALLBACK: If no data found with prefix, try without prefix (for legacy data)
    if not items:
        response = metrics_db.table.query(
            KeyConditionExpression='account_id = :acc',
            ExpressionAttributeValues={':acc': account_id.lower()},
            ScanIndexForward=False
        )
        items = response.get('Items', [])
        
    return items

@app.get("/metrics/{account_id}") # Maintain legacy endpoint for compatibility if needed
def get_metrics_for_account(account_id: str):
    return get_metrics_for_platform_account("instagram", account_id)

@app.get("/sync/status")
def get_sync_status():
    status = status_db.get_item({'id': 'global_sync'})
    if not status:
        return {
            "sync_count": 0,
            "sync_limit_stat": False,
            "last_sync_time": None,
            "max_limit": int(os.getenv("SYNC_MAX_LIMIT", 3))
        }
    return {
        "sync_count": status.get('sync_count', 0),
        "sync_limit_stat": status.get('sync_limit_stat', False),
        "last_sync_time": status.get('last_sync_time'),
        "max_limit": int(os.getenv("SYNC_MAX_LIMIT", 3))
    }

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    max_limit = int(os.getenv("SYNC_MAX_LIMIT", 3))
    now = datetime.datetime.utcnow()
    
    # Log the activity
    log_user_activity(user_id, "trigger_sync")
    
    # 1. Check sync status
    status = status_db.get_item({'id': 'global_sync'})
    if not status:
        status = {
            'id': 'global_sync',
            'sync_count': 0,
            'sync_limit_stat': False,
            'last_sync_time': None
        }

    sync_count = status.get('sync_count', 0)
    last_sync_str = status.get('last_sync_time')
    
    # 2. Check if we are in limit mode
    if status.get('sync_limit_stat') and last_sync_str:
        last_sync = datetime.datetime.fromisoformat(last_sync_str)
        if (now - last_sync).total_seconds() < (3 * 3600):
            wait_remaining = int((3 * 3600) - (now - last_sync).total_seconds())
            raise HTTPException(
                status_code=429, 
                detail=f"Sync limit reached. Please wait {wait_remaining // 60} minutes."
            )
        else:
            sync_count = 0
            status['sync_limit_stat'] = False

    # 3. Update status IMMEDIATELY (Prevent Vercel timeout)
    sync_count += 1
    status['sync_count'] = sync_count
    status['last_sync_time'] = now.isoformat()
    if sync_count >= max_limit:
        status['sync_limit_stat'] = True
    status_db.save_item(status)

    # 4. Perform sync in BACKGROUND
    background_tasks.add_task(run_full_sync)
    
    return {
        "message": "Sync started in background",
        "sync_count": sync_count,
        "limit_reached": status.get('sync_limit_stat', False)
    }

def run_full_sync():
    """Background task to sync all accounts"""
    logger.info("Starting full background sync...")
    integrations = integrations_db.scan_items()
    for account in integrations:
        platform = account.get('platform')
        try:
            if platform == 'instagram':
                sync_account(account['account_id'], account['access_token'])
            elif platform in ['meta', 'facebook']:
                sync_meta_account(account['account_id'], account['access_token'])
            elif platform == 'pinterest':
                sync_pinterest_account(account['account_id'], account['access_token'])
            elif platform == 'youtube':
                sync_youtube_account(account['account_id'], account['access_token'])
        except Exception as e:
            logger.error(f"Background sync failed for {account.get('account_id')}: {e}")
    logger.info("Full background sync complete.")

def _update_integration_sync_time(platform: str, account_id: str):
    """Helper to update last_synced_at in integrations table"""
    try:
        timestamp = datetime.datetime.utcnow().isoformat()
        # We need to fetch the item first to preserve other fields, or use update expression
        # Since our DB wrapper is simple, allow's fetch-modify-save
        item = integrations_db.get_item({'platform': platform, 'account_id': account_id})
        if item:
            item['last_synced_at'] = timestamp
            integrations_db.save_item(item)
    except Exception as e:
        logger.error(f"Failed to update sync time for {platform}/{account_id}: {e}")

def sync_account(account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    from Sources.instagram import InstagramClient
    
    # Fallback to master token from env if provided token is missing or generic 'env'
    if not access_token or access_token == "env":
        access_token = os.getenv("meta_gapi")
        if not access_token:
            logger.error(f"Sync failed for {account_id}: No access token provided and no master token in env.")
            return None
        logger.info(f"Using master token from environment for {account_id}")

    # REAL MODE: Fetch from Instagram API
    client = InstagramClient(access_token)
    
    # SMART DISCOVERY: If account_id is not numeric (e.g. 'blackbrookcase'), try to find the numeric ID
    if not account_id.isdigit():
        logger.info(f"Account ID '{account_id}' is not numeric. Attempting to discover Numeric ID...")
        try:
            available_accounts = client.get_accounts()
            # Diagnostic: Log all usernames found for this token
            found_usernames = [a['username'] for a in available_accounts if 'username' in a]
            logger.info(f"Token has access to {len(found_usernames)} accounts: {', '.join(found_usernames)}")
            
            found_id = None
            for acc in available_accounts:
                if acc['username'].lower() == account_id.lower():
                    found_id = acc['account_id']
                    logger.info(f"Auto-discovered Numeric ID for {account_id}: {found_id}")
                    break
            
            if found_id:
                account_id = found_id
            else:
                logger.error(f"Could not find a numeric ID for username '{account_id}' among connected accounts.")
                return None
        except Exception as e:
            logger.error(f"Error during account discovery for {account_id}: {e}")
            return None

    try:
        # Fetch 7 Days
        m7 = client.get_user_insights(account_id, period='7d')
        m7['interactions'] = client.get_media_interactions(account_id, days=7)
        
        # Fetch 30 Days
        m30 = client.get_user_insights(account_id, period='30d')
        m30['interactions'] = client.get_media_interactions(account_id, days=30)
        
    except Exception as e:
        print(f"Error fetching from Instagram API for {account_id}: {e}")
        return None

    try:
        timestamp = datetime.datetime.utcnow().isoformat()
        
        # Use composite ID for storage
        storage_id = f"instagram#{account_id.lower()}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'instagram',
            'followers_total': m30.get('followers_total', 0), # Total is same for both
            'period_7d': m7,
            'period_30d': m30
        }
        
        # Backward compatibility fields (optional, but good for safety if UI breaks)
        item.update({
            'followers_new': m30.get('followers_new', 0), 
            'views_organic': m30.get('views_organic', 0),
            'views_ads': m30.get('views_ads', 0),
            'interactions': m30.get('interactions', 0),
            'profile_visits': m30.get('profile_visits', 0),
            'accounts_reached': m30.get('accounts_reached', 0)
        })
        
        metrics_db.save_item(item)
        _update_integration_sync_time('instagram', account_id.lower())
        
        logger.info(f"Synced metrics (7d & 30d) for {account_id}")
        return item 

    except Exception as e:
        logger.error(f"Error saving synced data for {account_id}: {e}")
        return None

def sync_pinterest_account(account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    from Sources.pinterest import PinterestClient
    
    client = PinterestClient(access_token)
    try:
        # Fetch 7 Days
        s7 = client.get_analytics(days=7)
        # Fetch 30 Days
        s30 = client.get_analytics(days=30)
        
        if not s30: # If 30 fails, we probably failed
            return None
            
        # Get Profile for total followers
        profile = client.get_account_info()
        followers_total = 0
        account_name = account_id
        if profile:
            followers_total = profile.get('follower_count', 0)
            account_name = profile.get('username', account_id)
        elif s30.get('audience'):
             followers_total = s30.get('audience', 0)

        # Helper to format pinterest stats to generic schema
        def fmt(s):
            return {
                'followers_new': 0,
                'views_organic': s.get('views', 0),
                'views_ads': 0,
                'interactions': s.get('engagements', 0),
                'profile_visits': s.get('clicks', 0), # Clicks as profile visits proxy
                'accounts_reached': s.get('views', 0),
                'saves': s.get('saves', 0)
            }

        timestamp = datetime.datetime.utcnow().isoformat()
        storage_id = f"pinterest#{account_id.lower()}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'pinterest',
            'followers_total': followers_total,
            'period_7d': fmt(s7),
            'period_30d': fmt(s30)
        }
        
        # Backwards compat
        item.update(fmt(s30))
        item['account_name'] = account_name

        metrics_db.save_item(item)
        _update_integration_sync_time('pinterest', account_id.lower())
        
        logger.info(f"Synced Pinterest metrics for {account_id}")
        return item

    except Exception as e:
        logger.error(f"Pinterest sync error for {account_id}: {e}")
        return None

def sync_meta_account(account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    from Sources.meta import MetaClient
    
    if not access_token or access_token == "env":
        access_token = os.getenv("meta_gapi")
        if not access_token:
            logger.error(f"Meta sync failed for {account_id}: No access token.")
            return None

    client = MetaClient(access_token)
    
    try:
        # Fetch 7 Days
        m7 = client.get_page_insights(account_id, period='7d')
        # Fetch 30 Days
        m30 = client.get_page_insights(account_id, period='30d')
        
        timestamp = datetime.datetime.utcnow().isoformat()
        storage_id = f"facebook#{account_id.lower()}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'facebook',
            'followers_total': m30.get('followers_total', 0),
            'period_7d': m7,
            'period_30d': m30
        }
        
        # Backwards compat
        item.update({
             'followers_new': m30.get('followers_new', 0), 
            'views_organic': m30.get('views_organic', 0),
            'views_ads': m30.get('views_ads', 0),
            'interactions': m30.get('interactions', 0),
            'profile_visits': m30.get('profile_visits', 0),
            'accounts_reached': m30.get('accounts_reached', 0)
        })
        
        metrics_db.save_item(item)
        _update_integration_sync_time('facebook', account_id.lower())
        
        logger.info(f"Synced Meta (Facebook) metrics for {account_id}")
        return item

    except Exception as e:
        logger.error(f"Meta sync error for {account_id}: {e}")
        return None

def sync_youtube_account(account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    from Sources.youtube import YouTubeClient
    
    logger.info(f"Syncing YouTube account {account_id}...")
    client = YouTubeClient(access_token)
    
    try:
        # Fetch 7 Days
        m7 = client.get_channel_insights(account_id, days=7)
        # Fetch 30 Days
        m30 = client.get_channel_insights(account_id, days=30)
        
        timestamp = datetime.datetime.utcnow().isoformat()
        storage_id = f"youtube#{account_id}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'youtube',
            'followers_total': m30.get("followers_total", 0),
            'period_7d': m7,
            'period_30d': m30
        }
        
        # Backwards compat
        item.update({
            'followers_new': m30.get("followers_new", 0),
            'views_organic': m30.get("views_organic", 0),
            'views_ads': 0,
            'interactions': m30.get("interactions", 0),
            'profile_visits': 0,
            'accounts_reached': m30.get("accounts_reached", 0)
        })
        
        metrics_db.save_item(item)
        _update_integration_sync_time('youtube', account_id)
        
        logger.info(f"YouTube Sync complete for {account_id}")
        return item

    except Exception as e:
        logger.error(f"YouTube sync error for {account_id}: {e}")
        return None
