import asyncio
import datetime
import os
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
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
    async def _refresh_pinterest_token(self, account: Dict[str, Any]) -> Optional[str]:
        """Refresh Pinterest token and update repository"""
        from services.auth import PinterestAuth
        refresh_token = account.get('encrypted_refresh_token')
        if not refresh_token:
            logger.warning(f"No refresh token for Pinterest account {account.get('account_id')}")
            return None

        auth = PinterestAuth()
        try:
            new_tokens = await auth.refresh_token(refresh_token)
            if not new_tokens or 'access_token' not in new_tokens:
                raise Exception("Invalid refresh response")
        except Exception as e:
            logger.error(f"TERMINAL FAILURE: Refresh failed for Pinterest {account.get('account_id')}: {e}")
            # Mark as broken to stop future RCU burn
            await self.users_repo.update_integration_status(
                user_id=account.get('PK').replace('USER#', ''),
                platform='pinterest',
                account_id=account.get('account_id'),
                status='DISCONNECTED',
                error_message="Refresh token expired or revoked. Please reconnect."
            )
            return None

        new_access_token = new_tokens['access_token']
        # Update repository
        await self.users_repo.add_integration(
            user_id=account.get('PK').replace('USER#', ''),
            platform='pinterest',
            account_id=account.get('account_id'),
            encrypted_access_token=new_access_token,
            encrypted_refresh_token=new_tokens.get('refresh_token') or refresh_token, # Keep old if new not provided
            account_name=account.get('account_name'),
            additional_info=account.get('additional_info', {})
        )
        return new_access_token

    async def sync_pinterest_account(self, account_id: str, access_token: str, account_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if account_data and account_data.get('status') == 'DISCONNECTED':
            logger.info(f"Skipping sync for disconnected Pinterest account: {account_id}")
            return None

        from services.pinterest import PinterestClient
        
        def fetch_with_refresh(token):
            client = PinterestClient(token)
            now = datetime.datetime.utcnow().date()
            days = [0, 7, 14, 30, 60]
            dates = {d: (now - datetime.timedelta(days=d)).isoformat() for d in days}
            
            wins = [('7d', 7, 0), ('7_14', 14, 7), ('30d', 30, 0), ('30_60', 60, 30)]
            try:
                # First attempt
                res = {f"period_{n}": client.get_analytics(start_date_str=dates[s], end_date_str=dates[e]) for n, s, e in wins}
                profile = client.get_account_info()
                
                # Check for failure (could be 401)
                # Note: get_account_info returns None on error
                if not profile and account_data:
                    return "REFRESH_NEEDED"
                    
                return {**res, "profile": profile}
            except Exception as e:
                logger.warning(f"Pinterest fetch error: {e}")
                return "REFRESH_NEEDED"

        data = await asyncio.to_thread(fetch_with_refresh, access_token)
        
        if data == "REFRESH_NEEDED" and account_data:
            logger.info(f"Pinterest token likely expired for {account_id}, attempting refresh...")
            new_token = await self._refresh_pinterest_token(account_data)
            if new_token:
                data = await asyncio.to_thread(fetch_with_refresh, new_token)
        
        if not data or data == "REFRESH_NEEDED" or not data.get('period_30d'): 
            return None

        def fmt(s):
            return {
                'followers_new': 0, 
                'views_organic': s.get('views', 0), 
                'views_ads': 0, 
                'interactions': s.get('engagements', 0),
                'profile_visits': s.get('clicks', 0), 
                'accounts_reached': s.get('views', 0), 
                'saves': s.get('saves', 0),
                'audience': s.get('audience', 0),
                'outbound_clicks': s.get('audience', 0)
            }

        profile = data.get('profile') or {}
        followers = profile.get('follower_count', 0) or profile.get('followerCount', 0)
        
        m30 = data['period_30d']
        raw = {k: fmt(v) for k, v in data.items() if k.startswith('period_')}
        payload = {
            "followers_total": followers,
            "followers_new": 0, 
            "impressions_total": m30.get('views', 0), 
            "interactions": raw['period_30d']['interactions'],
            "views": raw['period_30d']['views_organic'], 
            "saves": raw['period_30d']['saves'],
            "outbound_clicks": raw['period_30d']['outbound_clicks'],
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

    async def sync_youtube_account(self, account_id: str, access_token: str, content_owner_id: str = None) -> Optional[Dict[str, Any]]:
        from services.youtube import YouTubeClient
        logger.info(f"Syncing YouTube account: {account_id} (CO: {content_owner_id})")
        def fetch_data(token, co_id):
            client = YouTubeClient(token)
            now = datetime.datetime.utcnow()
            # YouTube analytics have a 2-3 day lag. Shift windows back to ensure data availability.
            # We use a 3-day lag (end=3 days ago).
            days = [3, 10, 17, 33, 63]
            dates = {d: (now - datetime.timedelta(days=d)).strftime("%Y-%m-%d") for d in days}
            wins = [('7d', 10, 3), ('7_14', 17, 10), ('30d', 33, 3), ('30_60', 63, 33)]

            try:
                res = {f"period_{n}": client.get_channel_insights(account_id, start_date=dates[s], end_date=dates[e], content_owner_id=co_id) for n, s, e in wins}
                logger.debug(f"Fetched raw YouTube data for {account_id}")
                return res
            except Exception as e:
                logger.error(f"Error fetching YouTube data in client thread for {account_id}: {e}")
                return None

        metrics = await asyncio.to_thread(fetch_data, access_token, content_owner_id)
        if not metrics:
            logger.error(f"YouTube sync failed for {account_id}: fetch_data returned None")
            return None
            
        if not metrics.get('period_30d'):
            logger.warning(f"No 30-day metrics data found for YouTube account {account_id}")
            return None

        m30 = metrics['period_30d']
        payload = {
            "followers_total": m30.get("followers_total", 0), "followers_new": m30.get("followers_new", 0),
            "impressions_total": m30.get("views_total", 0), "interactions": m30.get("interactions", 0),
            "views": m30.get("views_organic", 0) + m30.get("views_ads", 0), "watch_time_hours": m30.get("watch_time_hours", Decimal("0.0")),
            "raw_metrics": metrics
        }
        
        logger.info(f"Successfully Prepared payload for YouTube/ {account_id}. Upserting to repo...")
        await self.metrics_repo.upsert_daily_metrics('youtube', account_id, datetime.datetime.utcnow().strftime("%Y-%m-%d"), payload)
        return payload

    async def run_full_sync(self, user_id: str = None):
        if user_id:
            logger.info(f"Starting targeted sync for user: {user_id}")
            integrations = await self.users_repo.list_integrations(user_id)
        else:
            logger.info("Starting full background sync...")
            integrations = await self.users_repo.scan_all_integrations()

        success_count = 0
        fail_count = 0
        
        try:
            total = len(integrations)
            logger.info(f"Found {total} integrations to synchronize.")
            
            for i, account in enumerate(integrations, 1):
                platform = account.get('platform')
                acc_id = account.get('account_id')
                token = account.get('encrypted_access_token')
                
                if not platform or not acc_id or not token:
                    logger.warning(f"[{i}/{total}] Skipping invalid integration: Platform={platform}, ID={acc_id}")
                    continue

                logger.info(f"[{i}/{total}] Syncing {platform.upper()} account: {acc_id}")
                try:
                    res = None
                    if platform == 'instagram':
                        res = await self.sync_instagram_account(acc_id, token)
                    elif platform in ['meta', 'facebook']:
                        res = await self.sync_meta_account(acc_id, token)
                    elif platform == 'pinterest':
                        res = await self.sync_pinterest_account(acc_id, token, account_data=account)
                    elif platform == 'youtube':
                        co_id = account.get('additional_info', {}).get('content_owner_id')
                        res = await self.sync_youtube_account(acc_id, token, content_owner_id=co_id)
                    
                    if res:
                        success_count += 1
                        logger.info(f"[{i}/{total}] Successfully synced {platform.upper()} account: {acc_id}")
                    else:
                        fail_count += 1
                        logger.warning(f"[{i}/{total}] Sync returned no data for {platform.upper()} account: {acc_id}")
                        
                except Exception as e:
                    fail_count += 1
                    logger.error(f"[{i}/{total}] Background sync failed for {acc_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Full background sync critical error: {e}")
            
        logger.info(f"Full background sync complete. Summary: {success_count} succeeded, {fail_count} failed, {success_count + fail_count} total processed.")
