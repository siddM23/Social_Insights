import requests
import json
import logging
import os

logger = logging.getLogger("social_insights.meta")

class MetaClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v19.0"

    def get_pages(self):
        """Get Facebook Pages connected to the user."""
        url = f"{self.base_url}/me/accounts"
        params = {
            "access_token": self.access_token,
            "fields": "id,name,category,access_token,perms"
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if "error" in data:
            logger.error(f"Error fetching Meta Pages: {data['error'].get('message')}")
            return []
            
        pages = []
        if "data" in data:
            for page in data["data"]:
                pages.append({
                    "account_id": page["id"],
                    "name": page["name"],
                    "access_token": page.get("access_token"), # Page access token
                    "category": page.get("category")
                })
        return pages

    def get_page_insights(self, page_id: str, page_access_token: str = None, period: str = 'day'):
        """
        Get Facebook Page insights.
        Metrics: page_impressions, page_post_engagements, page_views_total, page_fan_adds
        Params:
            period: 'day', 'week', 'days_28'
        """
        # Use Page Access Token if provided, otherwise use User Access Token (User token usually works if user has permissions)
        token = page_access_token or self.access_token
        
        url = f"{self.base_url}/{page_id}/insights"
        
        # Metrics we want:
        # page_impressions (Reach/Views)
        # page_post_engagements (Interactions)
        # page_views_total (Profile Visits)
        # page_fan_adds (New Followers)
        # page_fans (Total Followers - this one is on the object itself)
        
        # 1. Get Page Object for Total Followers (fan_count)
        # Optimization: Only fetch if needed? For now we keep it to ensure data structure completeness.
        page_url = f"{self.base_url}/{page_id}"
        
        fan_count = 0
        try:
            page_res = requests.get(page_url, params={
                "access_token": token,
                "fields": "fan_count,name"
            }, timeout=10)
            page_data = page_res.json()
            fan_count = page_data.get("fan_count", 0)
        except Exception as e:
            logger.error(f"Error fetching Page fan_count: {e}")
        
        # 2. Get Insights
        api_period = period
        if period == '7d': api_period = 'week'
        if period == '30d': api_period = 'days_28'
        
        params = {
            "access_token": token,
            "metric": "page_impressions,page_post_engagements,page_views_total,page_fan_adds",
            "period": api_period
        }
        
        insights_res = requests.get(url, params=params, timeout=10)
        insights_data = insights_res.json()
        
        result = {
            "followers_total": fan_count,
            "followers_new": 0,
            "views_organic": 0,
            "views_ads": 0,
            "interactions": 0,
            "profile_visits": 0,
            "accounts_reached": 0
        }
        
        if "data" in insights_data:
            for item in insights_data["data"]:
                name = item["name"]
                if item["values"]:
                    # For rolling windows (week/days_28), the value is the total for that window ending on 'end_time'.
                    # We take the latest one.
                    latest_val = item["values"][-1]["value"]
                    
                    if name == "page_impressions":
                        result["accounts_reached"] = latest_val
                        result["views_organic"] = latest_val
                    elif name == "page_post_engagements":
                        result["interactions"] = latest_val
                    elif name == "page_views_total":
                        result["profile_visits"] = latest_val
                    elif name == "page_fan_adds":
                        result["followers_new"] = latest_val
                        
        return result
