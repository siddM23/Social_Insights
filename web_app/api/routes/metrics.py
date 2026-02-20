import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from models.schemas import MetricRequest, CustomMetricRequest

router = APIRouter()
logger = logging.getLogger("social_insights.routes.metrics")

# Inject dependencies from main.py
users_repo = None
metrics_repo = None

@router.post("/metrics/custom_range")
async def get_custom_range_metrics(req: CustomMetricRequest, user_id: str = Depends(get_current_user)):
    logger.info(f"Fetching custom metrics for {user_id} from {req.start_date} to {req.end_date}")
    
    user_integrations = await users_repo.list_integrations(user_id)
    results = []
    
    try:
        start_dt = datetime.datetime.strptime(req.start_date, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(req.end_date, "%Y-%m-%d")
        duration = end_dt - start_dt
        
        # Ranges
        curr = (int(start_dt.timestamp()), int(end_dt.replace(hour=23, minute=59, second=59).timestamp()))
        prev_dt = (start_dt - duration - datetime.timedelta(days=1), start_dt - datetime.timedelta(seconds=1))
        prev = (int(prev_dt[0].timestamp()), int(prev_dt[1].timestamp()))
        prev_str = (prev_dt[0].strftime("%Y-%m-%d"), prev_dt[1].strftime("%Y-%m-%d"))
    except: raise HTTPException(400, "Invalid date format")

    for acc in user_integrations:
        platform, aid, token = acc.get('platform'), acc.get('account_id'), acc.get('encrypted_access_token')
        if not platform or not aid: continue
        
        m_curr, m_prev = None, None
        try:
            if platform == 'instagram':
                from services.instagram import InstagramClient
                c = InstagramClient(token)
                m_curr = c.get_user_insights(aid, since=curr[0], until=curr[1])
                m_curr['interactions'] = c.get_media_interactions(aid, since_ts=curr[0], until_ts=curr[1])
                m_prev = c.get_user_insights(aid, since=prev[0], until=prev[1])
                m_prev['interactions'] = c.get_media_interactions(aid, since_ts=prev[0], until_ts=prev[1])

            elif platform in ['meta', 'facebook']:
                from services.meta import MetaClient
                c = MetaClient(token)
                m_curr, m_prev = c.get_page_insights(aid, since=curr[0], until=curr[1]), c.get_page_insights(aid, since=prev[0], until=prev[1])

            elif platform == 'pinterest':
                from services.pinterest import PinterestClient
                c = PinterestClient(token)
                prof = c.get_account_info() or {}
                f_total = prof.get('follower_count', 0) or prof.get('followerCount', 0)
                
                def get_p(s, e):
                    v = c.get_analytics(start_date_str=s, end_date_str=e)
                    return {'followers_new': 0, 'views_organic': v.get('views', 0), 'views_ads': 0, 'interactions': v.get('engagements', 0),
                            'profile_visits': v.get('clicks', 0), 'accounts_reached': v.get('views', 0), 'saves': v.get('saves', 0), 
                            'followers_total': f_total, 'audience': v.get('audience', 0)}
                m_curr, m_prev = get_p(req.start_date, req.end_date), get_p(prev_str[0], prev_str[1])

            elif platform == 'youtube':
                from services.youtube import YouTubeClient
                c = YouTubeClient(token)
                m_curr, m_prev = c.get_channel_insights(aid, start_date=req.start_date, end_date=req.end_date), c.get_channel_insights(aid, start_date=prev_str[0], end_date=prev_str[1])
                
        except Exception as e: logger.error(f"Error fetching {platform}/{aid}: {e}")
        
        if m_curr:
            results.append({"accountName": acc.get('account_name', aid), "platform": platform, "data": {"custom_period": m_curr, "previous_period": m_prev, "followers_total": m_curr.get('followers_total', 0)}})

    return results

@router.post("/metrics")
async def add_metric(req: MetricRequest):
    date_str = req.timestamp.split("T")[0] if "T" in req.timestamp else req.timestamp
    metrics_data = req.dict()
    await metrics_repo.upsert_daily_metrics(
        platform="generated",
        account_id=req.account_id,
        date=date_str,
        metrics=metrics_data
    )
    return {"message": "Metric saved", "data": metrics_data}

@router.get("/metrics/{platform}/{account_id}")
async def get_metrics_for_platform_account(platform: str, account_id: str):
    end_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.utcnow() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    items = await metrics_repo.get_metrics_range(platform, account_id, start_date, end_date)
    return items

@router.get("/metrics/{account_id}")
async def get_metrics_for_account(account_id: str):
    return await get_metrics_for_platform_account("instagram", account_id)
