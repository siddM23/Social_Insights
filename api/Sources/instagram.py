import requests
import json
import time
import logging
import os

logger = logging.getLogger("social_insights.instagram")

class InstagramClient:
    def __init__(self, access_token: str, account_id: str = None):
        self.access_token = access_token
        self.account_id = account_id
        self.base_url = "https://graph.facebook.com/v19.0"

    def get_me(self):
        """Verify token and get user basic info"""
        url = f"{self.base_url}/me"
        # Checking for direct account connections that might exist in some v19.0 configurations
        params = {
            "access_token": self.access_token,
            "fields": "id,name,instagram_business_account"
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        logger.info(f"Token 'me' info: {json.dumps(data)}")
        
        # Also check permissions
        perm_url = f"{self.base_url}/me/permissions"
        perm_res = requests.get(perm_url, params={"access_token": self.access_token}, timeout=10)
        logger.info(f"Token permissions: {json.dumps(perm_res.json())}")
        
        return data

    def get_accounts(self):
        """
        Get Instagram Business Accounts connected to the user.
        Note: This usually requires getting user's Facebook Pages -> Connected IG Accounts.
        """
        # First, check who we are and if there's a direct IG account link
        me_data = self.get_me()
        accounts = []
        
        # 1. Check if the User object itself has a linked IG account (Business Discovery Entry Point)
        if "instagram_business_account" in me_data:
            ig_info = me_data["instagram_business_account"]
            logger.info("Found direct instagram_business_account on User object!")
            accounts.append({
                "page_id": "direct",
                "page_name": "Direct Link",
                "account_id": ig_info["id"],
                "username": ig_info.get("username")
            })

        # 2. Check Facebook Pages (Standard method)
        url = f"{self.base_url}/me/accounts"
        params = {
            "access_token": self.access_token,
            "fields": "id,name,category,tasks,instagram_business_account{id,username,profile_picture_url,followers_count}"
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if "error" in data:
            logger.error(f"Error fetching connected accounts: {data['error'].get('message')}")
            return accounts
            
        logger.info(f"Raw Page discovery response: {json.dumps(data)}")
        
        # 3. Check /me/businesses (Optional Business Manager check)
        biz_res = requests.get(f"{self.base_url}/me/businesses", params={"access_token": self.access_token}, timeout=10)
        logger.info(f"Business Manager check: {json.dumps(biz_res.json())}")

        if "data" in data:
            if len(data["data"]) == 0 and not accounts:
                logger.warning("No Facebook Pages or direct IG accounts found for this token.")
                logger.info("CRITICAL: Instagram Business accounts MUST be linked to a Facebook Page to appear here.")
                logger.info("ACTION: Go to IG App > Settings > Sharing to other apps > Facebook and connect a Page.")
            
            for page in data["data"]:
                ig_info = page.get("instagram_business_account")
                if ig_info:
                    accounts.append({
                        "page_id": page["id"],
                        "page_name": page["name"],
                        "account_id": ig_info["id"],
                        "username": ig_info.get("username"),
                        "followers_count": ig_info.get("followers_count")
                    })
                else:
                    logger.info(f"Page '{page.get('name')}' (ID: {page.get('id')}) has no connected Instagram Business Account.")
        return accounts

    def get_user_insights(self, ig_user_id: str, period: str = 'day'):
        """
        Get basic user insights (Followers, Reach, Impressions, Profile Views).
        Params:
            period: 'day', 'week', 'days_28'
        """
        url = f"{self.base_url}/{ig_user_id}/insights"
        
        # 1. Get User Profile Data (Followers, Media Count) - Only if we need total followers
        # Optimization: We might not need to call this every time if we just want mismatched period stats, 
        # but for consistency we'll keep it or let the caller handle it. 
        # For now, we'll fetch it to ensure we always have followers_total.
        user_url = f"{self.base_url}/{ig_user_id}"
        user_res = requests.get(user_url, params={
            "access_token": self.access_token,
            "fields": "followers_count,follows_count,media_count,name,username"
        }, timeout=10)
        user_data = user_res.json()
        
        # 2. Get Insights
        # API Mapping:
        # 7 days -> period='week' (supported by reach, impressions)
        # 30 days -> period='days_28' (supported by reach, impressions)
        
        metric_param = "impressions,reach,profile_views"
        api_period = period
        
        if period == '7d':
             api_period = 'week' # approx
        elif period == '30d':
             api_period = 'days_28' # approx
        
        params = {
            "access_token": self.access_token,
            "metric": metric_param,
            "period": api_period 
        }
        
        # Note: 'profile_views' only supports 'day'. We might need to sum 'day' for other periods?
        # For simplicity, if period is not 'day', we might lose profile_views in single call or need separate call.
        # Let's try to fetch all. If valid period error, we might handle it.
        # Actually, `profile_views` DOES NOT support `week` or `days_28`. It only supports `day`.
        # So for 7d/30d, we must fetch `day` and sum them up.
        
        # Revision: Always fetch `day` and sum up locally for exact control?
        # `reach` and `impressions` are unique/reach, so summing `day` reach != `week` reach (uniques overlap).
        # We SHOULD use `week`/`days_28` for reach/impressions if possible.
        
        # Strategy:
        # 1. Fetch `reach,impressions` with requested period (week/days_28).
        # 2. Fetch `profile_views` with `day` and sum last N days.
        
        result = {
            "followers_total": user_data.get("followers_count", 0),
            "followers_new": 0,
            "views_organic": 0,
            "views_ads": 0,
            "interactions": 0,
            "profile_visits": 0,
            "accounts_reached": 0
        }
        
        # A. Fetch Reach/Impressions (supports day, week, days_28)
        # However, `profile_views` fails if we mix periods incompatible. 
        # So we split the calls.
        
        # Call 1: Organic Views (Impressions) & Reach
        try:
            p = 'day'
            if period == '7d': p = 'week'
            if period == '30d': p = 'days_28'
            
            res = requests.get(url, params={
                "access_token": self.access_token,
                "metric": "impressions,reach",
                "period": p
            }, timeout=10)
            data = res.json()
            
            if "data" in data:
                for item in data["data"]:
                    if item["values"]:
                        val = item["values"][-1]["value"] # Latest window value
                        if item["name"] == "impressions": result["views_organic"] = val
                        if item["name"] == "reach": result["accounts_reached"] = val
        except Exception as e:
            logger.error(f"Error fetching IG reach/impressions for {period}: {e}")

        # Call 2: Profile Views (Always 'day', we sum up)
        try:
            days_to_sum = 1
            if period == '7d': days_to_sum = 7
            if period == '30d': days_to_sum = 30
            
            # We need slightly more data to sum correctly?
            # 'period=day' usually returns last couple of days. 
            # To get 30 days history, we need 'since' and 'until' params potentially.
            # But standard `/insights` current window usually allows `since` and `until`.
            
            import datetime
            until = datetime.datetime.now()
            since = until - datetime.timedelta(days=days_to_sum)
            
            res = requests.get(url, params={
                "access_token": self.access_token,
                "metric": "profile_views",
                "period": "day",
                "since": int(since.timestamp()),
                "until": int(until.timestamp())
            }, timeout=10)
            data = res.json()
            
            total_views = 0
            if "data" in data:
                for item in data["data"]:
                    if item["name"] == "profile_views":
                        for v in item["values"]:
                            total_views += v["value"]
            
            result["profile_visits"] = total_views
            
        except Exception as e:
            logger.error(f"Error fetching IG profile_views: {e}")

        return result

    def get_media_interactions(self, ig_user_id: str, days: int = 1):
        """
        Get aggregated interactions (like_count + comments_count) from media in the last N days.
        """
        url = f"{self.base_url}/{ig_user_id}/media"
        params = {
            "access_token": self.access_token,
            "fields": "like_count,comments_count,timestamp",
            "limit": 100 # Fetch more to cover time window
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            total_interactions = 0
            
            import datetime
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            if "data" in data:
                for media in data["data"]:
                    # Check timestamp
                    # Format: "2024-10-24T12:00:00+0000"
                    if media.get("timestamp"):
                        try:
                            # Simple ISO parsing (remove timezone if tricky or use str comparison if format consistent)
                            # Timestamp usually ends with +0000
                            ts_str = media["timestamp"].replace("+0000", "") 
                            ts = datetime.datetime.fromisoformat(ts_str)
                            
                            if ts >= cutoff:
                                total_interactions += media.get("like_count", 0)
                                total_interactions += media.get("comments_count", 0)
                        except:
                            pass
                            
            return total_interactions
        except Exception as e:
            logger.error(f"Error fetching IG interactions: {e}")
            return 0
