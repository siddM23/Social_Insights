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

    def get_channel_insights(self, channel_id: str):
        """
        Get YouTube Channel insights using YouTube Analytics API.
        Metrics mapped to our standard format.
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

        # 2. Get daily metrics via Analytics API
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d") # Use last 2 days to ensure data exists
        
        analytics_params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,subscribersGained,likes,comments,shares,estimatedMinutesWatched",
            "dimensions": "day",
            "sort": "-day",
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
                latest_row = data["rows"][0]
                # Map based on standard column headers index
                # views, subscribersGained, likes, comments, shares, estimatedMinutesWatched
                result["views_organic"] = int(latest_row[1])
                result["followers_new"] = int(latest_row[2])
                result["interactions"] = int(latest_row[3]) + int(latest_row[4]) + int(latest_row[5])
                result["accounts_reached"] = int(latest_row[1]) # YouTube Views ~ Reach
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics: {e}")
            if "error" in locals() and "data" in locals():
                logger.error(f"YouTube API raw error: {data}")

        return result
