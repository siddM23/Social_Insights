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
metrics_db = DynamoDB('instagram_metrics')
status_db = DynamoDB('app_status')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    logger.info("Initializing DynamoDB tables...")
    integrations_db.create_table(pk='platform', sk='account_id', sk_type='S')
    metrics_db.create_table(pk='account_id', sk='timestamp', sk_type='S')
    status_db.create_table(pk='id') # Simple PK for status singleton
    logger.info("Tables initialized.")
    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan,root_path="/api")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
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

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Social Insights Backend"}

# --- Auth Endpoints ---

@app.get("/auth/instagram/login")
async def auth_instagram_login():
    start_time = datetime.datetime.now()
    logger.info("Instagram login URL requested")
    auth_client = InstagramAuth()
    url = auth_client.get_auth_url()
    return RedirectResponse(url=url)

@app.get("/auth/instagram/callback")
async def auth_instagram_callback(code: str):
    auth_client = InstagramAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Instagram code for token")
    
    access_token = token_data.get("access_token")
    
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
            "additional_info": {"status": "Active", "page_name": acc.get("page_name")}
        })
        # Inline sync (Vercel compatible)
        sync_account(normalized_id, access_token)
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=instagram&count={len(accounts)}")

@app.get("/auth/pinterest/login")
async def auth_pinterest_login():
    start_time = datetime.datetime.now()
    logger.info("Pinterest login URL requested")
    auth_client = PinterestAuth()
    url = auth_client.get_auth_url()
    return RedirectResponse(url=url)

@app.get("/auth/pinterest/callback") # Matches user's recent change
async def auth_pinterest_callback(code: str):
    auth_client = PinterestAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange Pinterest code for token")
    
    access_token = token_data.get("access_token")
    
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
        "additional_info": {"status": "Active"}
    })
    
    # Inline sync (Vercel compatible)
    sync_pinterest_account(normalized_id, access_token)

    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=pinterest")

@app.get("/auth/meta/login")
async def auth_meta_login():
    start_time = datetime.datetime.now()
    logger.info("Meta login URL requested")
    auth_client = MetaAuth()
    url = auth_client.get_auth_url()
    return RedirectResponse(url=url)

@app.get("/auth/meta/callback")
async def auth_meta_callback(code: str):
    logger.info("Meta callback received. Exchanging code for token...")
    auth_client = MetaAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        logger.error("Failed to exchange Meta code for token")
        raise HTTPException(status_code=400, detail="Failed to exchange Meta code for token")
    
    access_token = token_data.get("access_token")
    logger.info("Token exchange successful. Fetching Meta pages...")
    
    # FETCH ACCOUNT DETAILS AUTOMATICALLY
    from Sources.meta import MetaClient
    client = MetaClient(access_token)
    pages = client.get_pages()
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not pages:
        logger.warning("No Facebook Pages found for this account")
        return RedirectResponse(url=f"{frontend_url}/integrations?status=error&message=no_facebook_pages")

    logger.info(f"Found {len(pages)} Meta pages. Saving...")
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
            "additional_info": {"status": "Active", "category": page.get("category")}
        })
        # Inline sync (Vercel compatible)
        sync_meta_account(normalized_id, token_to_save)
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=meta&count={len(pages)}")

@app.get("/auth/youtube/login")
async def auth_youtube_login():
    logger.info("YouTube login URL requested")
    auth_client = YouTubeAuth()
    url = auth_client.get_auth_url()
    return RedirectResponse(url=url)

@app.get("/auth/youtube/callback")
async def auth_youtube_callback(code: str):
    logger.info("YouTube callback received. Exchanging code for token...")
    auth_client = YouTubeAuth()
    token_data = auth_client.exchange_code_for_token(code)
    if not token_data:
        logger.error("Failed to exchange YouTube code for token")
        raise HTTPException(status_code=400, detail="Failed to exchange YouTube code for token")
    
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token") # Google usually gives refresh token in first auth
    
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
            "additional_info": {
                "status": "Active", 
                "refresh_token": refresh_token,
                "snippet": channel.get("snippet")
            }
        })
        # Inline sync (Vercel compatible)
        sync_youtube_account(normalized_id, access_token)
    
    return RedirectResponse(url=f"{frontend_url}/integrations?status=success&platform=youtube&count={len(channels)}")

# --- Integrations Endpoints ---

@app.post("/integrations")
async def add_integration(req: IntegrationRequest):
    if not req.access_token or not req.access_token.strip():
        raise HTTPException(status_code=400, detail="Access token is required and cannot be empty")
        
    item = req.dict()
    success = integrations_db.save_item(item)
    
    if req.platform == "instagram":
        # Inline sync (Vercel compatible)
        sync_account(req.account_id, req.access_token)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save integration")
    return {"message": "Integration saved", "data": item}

@app.get("/integrations/{platform}/{account_id}")
def get_integration(platform: str, account_id: str):
    item = integrations_db.get_item({'platform': platform, 'account_id': account_id})
    if not item:
        raise HTTPException(status_code=404, detail="Integration not found")
    return item

@app.get("/integrations")
def list_integrations():
    items = integrations_db.scan_items()
    normalized = []
    for item in items:
        if 'account_name' not in item:
             item['account_name'] = item.get('account_id', 'Unknown')
        normalized.append(item)
    return normalized

@app.delete("/integrations/{platform}/{account_id}")
def delete_integration(platform: str, account_id: str):
    success = integrations_db.delete_item({'platform': platform, 'account_id': account_id})
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete integration")
    logger.info(f"Deleted {platform} integration: {account_id}")
    return {"message": "Integration deleted"}

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
async def trigger_sync():
    max_limit = int(os.getenv("SYNC_MAX_LIMIT", 3))
    now = datetime.datetime.utcnow()
    
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

    # 3. Perform sync INLINE (Vercel compatible)
    run_full_sync()
    
    # 4. Update status immediately
    sync_count += 1
    status['sync_count'] = sync_count
    status['last_sync_time'] = now.isoformat()
    if sync_count >= max_limit:
        status['status_sync_limit_stat'] = True
    status_db.save_item(status)
    
    return {
        "message": "Sync complete",
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

    metrics = {}
    try:
        fetched_metrics = client.get_user_insights(account_id)
        interactions = client.get_media_interactions(account_id)
        
        # Merge
        metrics = fetched_metrics
        metrics['interactions'] = interactions
        
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
            'followers_total': metrics.get('followers_total', 0),
            'followers_new': metrics.get('followers_new', 0), 
            'views_organic': metrics.get('views_organic', 0),
            'views_ads': metrics.get('views_ads', 0),
            'interactions': metrics.get('interactions', 0),
            'profile_visits': metrics.get('profile_visits', 0),
            'accounts_reached': metrics.get('accounts_reached', 0)
        }
        
        metrics_db.save_item(item)
        logger.info(f"Synced metrics for {account_id}")
        return item # Return the item so it can be used immediately

    except Exception as e:
        logger.error(f"Error saving synced data for {account_id}: {e}")
        return None

def sync_pinterest_account(account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    from Sources.pinterest import PinterestClient
    
    client = PinterestClient(access_token)
    try:
        # Get basics
        stats = client.get_analytics()
        if not stats:
            return None
            
        timestamp = datetime.datetime.utcnow().isoformat()
        
        # Use composite ID for storage
        storage_id = f"pinterest#{account_id.lower()}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'pinterest',
            'followers_total': stats.get('audience', 0), 
            'followers_new': 0,
            'views_organic': stats.get('views', 0),
            'views_ads': 0,
            'interactions': stats.get('engagements', 0),
            'profile_visits': stats.get('clicks', 0),
            'accounts_reached': stats.get('views', 0),
            'saves': stats.get('saves', 0)
        }
        
        # Optionally get profile for followers
        profile = client.get_account_info()
        if profile:
            # Pinterest Audience maps to followers_total for our generic schema
            item['followers_total'] = profile.get('follower_count', 0)
            item['account_name'] = profile.get('username', account_id)
        elif stats.get('audience'):
             item['followers_total'] = stats.get('audience', 0)

        metrics_db.save_item(item)
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
        # For Facebook, we might need the Page Access Token if the User token isn't enough
        # But for now we try with user token
        metrics = client.get_page_insights(account_id)
        
        timestamp = datetime.datetime.utcnow().isoformat()
        storage_id = f"facebook#{account_id.lower()}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'facebook',
            'followers_total': metrics.get('followers_total', 0),
            'followers_new': metrics.get('followers_new', 0), 
            'views_organic': metrics.get('views_organic', 0),
            'views_ads': metrics.get('views_ads', 0),
            'interactions': metrics.get('interactions', 0),
            'profile_visits': metrics.get('profile_visits', 0),
            'accounts_reached': metrics.get('accounts_reached', 0)
        }
        
        metrics_db.save_item(item)
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
        insights = client.get_channel_insights(account_id)
        
        timestamp = datetime.datetime.utcnow().isoformat()
        storage_id = f"youtube#{account_id}"
        
        item = {
            'account_id': storage_id,
            'timestamp': timestamp,
            'platform': 'youtube',
            'followers_total': insights.get("followers_total", 0),
            'followers_new': insights.get("followers_new", 0),
            'views_organic': insights.get("views_organic", 0),
            'views_ads': 0,
            'interactions': insights.get("interactions", 0),
            'profile_visits': 0,
            'accounts_reached': insights.get("accounts_reached", 0)
        }
        
        metrics_db.save_item(item)
        logger.info(f"YouTube Sync complete for {account_id}")
        return item

    except Exception as e:
        logger.error(f"YouTube sync error for {account_id}: {e}")
        return None
