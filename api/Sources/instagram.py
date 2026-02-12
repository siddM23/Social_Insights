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

    def get_user_insights(self, ig_user_id: str):
        """
        Get basic user insights (Followers, Reach, Impressions, Profile Views).
        Metric: impressions, reach, profile_views
        Period: day (or 28 days for some)
        Note: API limits might apply.
        """
        url = f"{self.base_url}/{ig_user_id}/insights"
        
        # User/Business discovery metrics
        # For simplicity, getting daily metrics. 
        # But `follower_count` is on the User object itself, not insights.
        
        # 1. Get User Profile Data (Followers, Media Count)
        user_url = f"{self.base_url}/{ig_user_id}"
        logger.info(f"Fetching user profile for {ig_user_id}...")
        user_res = requests.get(user_url, params={
            "access_token": self.access_token,
            "fields": "followers_count,follows_count,media_count,name,username"
        }, timeout=10)
        user_data = user_res.json()
        if "error" in user_data:
            logger.error(f"Discovery error for {ig_user_id}: {user_data['error'].get('message')}")
            raise Exception(f"Instagram Profile Error: {user_data['error'].get('message')}")
        
        logger.info(f"Successfully fetched profile for {user_data.get('username')}")
        
        # 2. Get Insights (Reach, Impressions, Profile Views)
        # allowed period: day, week, days_28, month, lifetime (limited support)
        # we will use 'day' for now or 'days_28' for overview?
        # User requested "Views" (Organic/Ads), "Profile Visits", "Interactions", "Accounts Reached"
        
        # 'impressions', 'reach', 'profile_views' supports: period=day
        
        params = {
            "access_token": self.access_token,
            "metric": "impressions,reach,profile_views",
            "period": "day" 
        }
        logger.info(f"Fetching insights for {ig_user_id}...")
        insights_res = requests.get(url, params=params, timeout=10)
        insights_data = insights_res.json()
        
        if "error" in insights_data:
            logger.error(f"Insights error for {ig_user_id}: {insights_data['error'].get('message')}")
            raise Exception(f"Instagram Insights Error: {insights_data['error'].get('message')}")
        
        logger.info(f"Received insights data for {ig_user_id}: {json.dumps(insights_data)}")
        
        result = {
            "followers_total": user_data.get("followers_count", 0),
            "followers_new": 0, # Not directly available via API easily without delta tracking locally
            "views_organic": 0, # Mapped to impressions?
            "views_ads": 0, # Ads not available in standard Graph API usually
            "interactions": 0, # Need to sum up media interactions?
            "profile_visits": 0,
            "accounts_reached": 0
        }
        
        if "data" in insights_data:
            for item in insights_data["data"]:
                name = item["name"]
                # Sum values for the latest available day (usually yesterday)
                # item['values'] is list of {value, end_time}
                if item["values"]:
                    # Take the most recent one
                    latest_val = item["values"][-1]["value"]
                    
                    if name == "impressions":
                        result["views_organic"] = latest_val
                    elif name == "reach":
                        result["accounts_reached"] = latest_val
                    elif name == "profile_views":
                        result["profile_visits"] = latest_val

        # 3. Interactions (Likes + Comments on recent media) could be proxies
        # Or `total_interactions` metric if available (deprecated?)
        # Let's simple sum interactions from recent media (top 10?)
        
        return result

    def get_media_interactions(self, ig_user_id: str):
        """
        Get aggregated interactions (like_count + comments_count) from recent media.
        """
        url = f"{self.base_url}/{ig_user_id}/media"
        params = {
            "access_token": self.access_token,
            "fields": "like_count,comments_count,timestamp",
            "limit": 50 
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        total_interactions = 0
        if "data" in data:
            for media in data["data"]:
                # simple sum
                total_interactions += media.get("like_count", 0)
                total_interactions += media.get("comments_count", 0)
        
        return total_interactions
