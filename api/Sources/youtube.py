import requests
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger("social_insights.youtube")

class YouTubeClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.analytics_url = "https://youtubeanalytics.googleapis.com/v2/reports"

    def get_channels(self):
        """Get YouTube channels connected to the user."""
        url = f"{self.base_url}/channels"
        params = {
            "part": "snippet,statistics",
            "mine": "true",
            "access_token": self.access_token
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            logger.error(f"Network error fetching YouTube Channels: {e}")
            return []
        
        if "error" in data:
            logger.error(f"Error fetching YouTube Channels: {data['error'].get('message')}")
            return []
            
        channels = []
        if "items" in data:
            for item in data["items"]:
                channels.append({
                    "account_id": item["id"],
                    "name": item["snippet"]["title"],
                    "access_token": self.access_token, # Google use the same token for the user/channels
                    "snippet": item["snippet"],
                    "statistics": item["statistics"]
                })
        return channels

    def get_channel_insights(self, channel_id: str, days: int = 30):
        """
        Get YouTube Channel insights using YouTube Analytics API.
        Metrics mapped to our standard format.
        Params:
            days: Number of days to look back (e.g. 7 or 30)
        """
        # 1. Get current stats via Data API (for total followers)
        url = f"{self.base_url}/channels"
        params = {
            "part": "statistics",
            "id": channel_id,
            "access_token": self.access_token
        }
        
        followers_total = 0
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if "items" in data and len(data["items"]) > 0:
                followers_total = int(data["items"][0]["statistics"].get("subscriberCount", 0))
        except Exception as e:
            logger.error(f"Error fetching YouTube follower stats: {e}")

        # 2. Get aggregated metrics via Analytics API
        # To get totals for the period, we remove 'dimensions=day'
        
        # YouTube data is usually delayed by 2-3 days. 
        # If we ask for 'today', we might get partial or no data for recent days.
        # But for a 30-day window, requesting up to 'today' usually returns sum of available days.
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        analytics_params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,subscribersGained,likes,comments,shares,estimatedMinutesWatched",
            # "dimensions": "day", # Removed to get totals
            # "sort": "-day",      # Removed
            "access_token": self.access_token
        }
        
        result = {
            "followers_total": followers_total,
            "followers_new": 0,
            "views_organic": 0,
            "views_ads": 0,
            "interactions": 0,
            "profile_visits": 0,
            "accounts_reached": 0
        }

        try:
            res = requests.get(self.analytics_url, params=analytics_params, timeout=10)
            data = res.json()
            
            if "rows" in data and len(data["rows"]) > 0:
                # With no dimensions, we get a single row with totals
                row = data["rows"][0]
                # Map based on standard column headers index
                # views, subscribersGained, likes, comments, shares, estimatedMinutesWatched
                result["views_organic"] = int(row[0])
                result["followers_new"] = int(row[1])
                result["interactions"] = int(row[2]) + int(row[3]) + int(row[4])
                result["accounts_reached"] = int(row[0]) # YouTube Views ~ Reach
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics: {e}")
            if "error" in locals() and "data" in locals():
                logger.error(f"YouTube API raw error: {data}")

        return result
