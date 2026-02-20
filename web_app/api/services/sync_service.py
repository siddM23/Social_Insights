import asyncio
import datetime
import os
import logging
from typing import Dict, Any, Optional
from repositories.metrics_repository import MetricsRepository
from repositories.users_repository import UsersRepository

logger = logging.getLogger("social_insights.sync")

class SyncService:
    def __init__(self, metrics_repo: MetricsRepository, users_repo: UsersRepository):
        self.metrics_repo = metrics_repo
        self.users_repo = users_repo

    async def sync_instagram_account(self, account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        from services.instagram import InstagramClient
        
        if not (access_token := access_token or os.getenv("meta_gapi")):
            logger.error(f"Sync failed for {account_id}: No access token.")
            return None

        def fetch_data(token, acc_id):
            client = InstagramClient(token)
            if not acc_id.isdigit():
                try:
                    found = next((a for a in client.get_accounts() if a['username'].lower() == acc_id.lower()), None)
                    if found: acc_id = found['account_id']
                    else: return None
                except: return None
            
            now = datetime.datetime.utcnow()
            days = [0, 7, 14, 30, 60]
            ts = {d: int((now - datetime.timedelta(days=d)).timestamp()) for d in days}
            
            windows = [
                ('7d', ts[7], ts[0]), ('7_14', ts[14], ts[7]),
                ('30d', ts[30], ts[0]), ('30_60', ts[60], ts[30])
            ]
            
            try:
                res = {}
                for name, start, end in windows:
                    m = client.get_user_insights(acc_id, since=start, until=end)
                    m['interactions'] = client.get_media_interactions(acc_id, since_ts=start, until_ts=end)
                    res[f"period_{name}"] = m
                return res
            except Exception as e:
                logger.error(f"IG fetch error: {e}")
                return None

        metrics = await asyncio.to_thread(fetch_data, access_token, account_id)
        if not metrics or not metrics.get('period_30d'): return None

        m30 = metrics['period_30d']
        payload = {
            "followers_total": m30.get('followers_total', 0),
            "followers_new": m30.get('followers_new', 0),
            "impressions_total": m30.get('impressions_total', 0),
            "interactions": m30.get('interactions', 0),
            "views": m30.get('views_organic', 0) + m30.get('views_ads', 0),
            "raw_metrics": metrics
        }
        
        await self.metrics_repo.upsert_daily_metrics('instagram', account_id, datetime.datetime.utcnow().strftime("%Y-%m-%d"), payload)
        return payload

    async def sync_pinterest_account(self, account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        from services.pinterest import PinterestClient
        
        def fetch_data(token):
            client = PinterestClient(token)
            now = datetime.datetime.utcnow().date()
            days = [0, 7, 14, 30, 60]
            dates = {d: (now - datetime.timedelta(days=d)).isoformat() for d in days}
            
            wins = [('7d', 7, 0), ('7_14', 14, 7), ('30d', 30, 0), ('30_60', 60, 30)]
            try:
                res = {f"period_{n}": client.get_analytics(start_date_str=dates[s], end_date_str=dates[e]) for n, s, e in wins}
                return {**res, "profile": client.get_account_info()}
            except: return None

        data = await asyncio.to_thread(fetch_data, access_token)
        if not data or not data.get('period_30d'): return None

        def fmt(s):
            return {'followers_new': 0, 'views_organic': s.get('views', 0), 'views_ads': 0, 'interactions': s.get('engagements', 0),
                    'profile_visits': s.get('clicks', 0), 'accounts_reached': s.get('views', 0), 'saves': s.get('saves', 0),
                    'followers_total': s.get('audience', 0)}

        profile = data.get('profile') or {}
        followers = profile.get('follower_count', 0) or profile.get('followerCount', 0) or m30.get('audience', 0)
        
        m30 = data['period_30d']
        raw = {k: fmt(v) for k, v in data.items() if k.startswith('period_')}
        payload = {
            "followers_total": followers,
            "followers_new": 0, "impressions_total": m30.get('views', 0), "interactions": raw['period_30d']['interactions'],
            "views": raw['period_30d']['views_organic'], "saves": raw['period_30d']['saves'],
            "raw_metrics": raw
        }
        await self.metrics_repo.upsert_daily_metrics('pinterest', account_id.lower(), datetime.datetime.utcnow().strftime("%Y-%m-%d"), payload)
        return payload

    async def sync_meta_account(self, account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        from services.meta import MetaClient
        if not (access_token := access_token or os.getenv("meta_gapi")): return None

        def fetch_data(token):
            client = MetaClient(token)
            now = datetime.datetime.utcnow()
            days = [0, 7, 14, 30, 60]
            ts = {d: int((now - datetime.timedelta(days=d)).timestamp()) for d in days}
            wins = [('7d', 7, 0), ('7_14', 14, 7), ('30d', 30, 0), ('30_60', 60, 30)]
            try:
                return {f"period_{n}": client.get_page_insights(account_id, period='custom', since=ts[s], until=ts[e]) for n, s, e in wins}
            except: return None

        metrics = await asyncio.to_thread(fetch_data, access_token)
        if not metrics or not metrics.get('period_30d'): return None

        m30 = metrics['period_30d']
        payload = {
            "followers_total": m30.get('followers_total', 0), "followers_new": m30.get('followers_new', 0),
            "impressions_total": m30.get('impressions_total', 0), "interactions": m30.get('interactions', 0),
            "views": m30.get('views_organic', 0) + m30.get('views_ads', 0), "raw_metrics": metrics
        }
        await self.metrics_repo.upsert_daily_metrics('facebook', account_id.lower(), datetime.datetime.utcnow().strftime("%Y-%m-%d"), payload)
        return payload

    async def sync_youtube_account(self, account_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        from services.youtube import YouTubeClient
        def fetch_data(token):
            client = YouTubeClient(token)
            now = datetime.datetime.now()
            days = [0, 7, 14, 30, 60]
            dates = {d: (now - datetime.timedelta(days=d)).strftime("%Y-%m-%d") for d in days}
            wins = [('7d', 7, 0), ('7_14', 14, 7), ('30d', 30, 0), ('30_60', 60, 30)]
            try:
                return {f"period_{n}": client.get_channel_insights(account_id, start_date=dates[s], end_date=dates[e]) for n, s, e in wins}
            except: return None

        metrics = await asyncio.to_thread(fetch_data, access_token)
        if not metrics or not metrics.get('period_30d'): return None

        m30 = metrics['period_30d']
        payload = {
            "followers_total": m30.get("followers_total", 0), "followers_new": m30.get("followers_new", 0),
            "impressions_total": 0, "interactions": m30.get("interactions", 0),
            "views": m30.get("views_organic", 0) + m30.get("views_ads", 0), "watch_time_hours": m30.get("watch_time_hours", 0.0),
            "raw_metrics": metrics
        }
        await self.metrics_repo.upsert_daily_metrics('youtube', account_id, datetime.datetime.utcnow().strftime("%Y-%m-%d"), payload)
        return payload

    async def run_full_sync(self):
        logger.info("Starting full background sync...")
        try:
            integrations = await self.users_repo.scan_all_integrations()
            for account in integrations:
                platform = account.get('platform')
                acc_id = account.get('account_id')
                token = account.get('encrypted_access_token')
                
                if not platform or not acc_id or not token:
                    continue

                try:
                    if platform == 'instagram':
                        await self.sync_instagram_account(acc_id, token)
                    elif platform in ['meta', 'facebook']:
                        await self.sync_meta_account(acc_id, token)
                    elif platform == 'pinterest':
                        await self.sync_pinterest_account(acc_id, token)
                    elif platform == 'youtube':
                        await self.sync_youtube_account(acc_id, token)
                except Exception as e:
                    logger.error(f"Background sync failed for {acc_id}: {e}")
        except Exception as e:
            logger.error(f"Full background sync critical error: {e}")
        logger.info("Full background sync complete.")
