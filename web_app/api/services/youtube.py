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
        """
        Get YouTube channels connected to the user.
        Includes regular channels (mine=true) AND channels managed via Content Owner (CMS) if applicable.
        """
        channels = []
        
        # 1. Fetch channels where the user is the primary owner or selected identity
        url = f"{self.base_url}/channels"
        params = {
            "part": "snippet,statistics",
            "mine": "true",
            "access_token": self.access_token
        }
        
        try:
            logger.info("Fetching primary YouTube channels (mine=true)")
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if "items" in data:
                for item in data["items"]:
                    channels.append({
                        "account_id": item["id"],
                        "name": item["snippet"]["title"],
                        "access_token": self.access_token,
                        "snippet": item["snippet"],
                        "statistics": item["statistics"]
                    })
        except Exception as e:
            logger.error(f"Error fetching primary YouTube Channels: {e}")

        # 2. Fetch channels managed via Content Owner (CMS)
        # This is what a "Manager Account" (CMS) would use to see child channels.
        # Requires 'https://www.googleapis.com/auth/youtubepartner.readonly' scope.
        try:
            logger.info("Checking for YouTube Content Owner associations")
            co_url = "https://www.googleapis.com/youtube/v3/contentOwners"
            co_params = {"mine": "true", "access_token": self.access_token}
            co_res = requests.get(co_url, params=co_params, timeout=10)
            co_data = co_res.json()
            
            if "items" in co_data:
                for co in co_data["items"]:
                    co_id = co["id"]
                    logger.info(f"Found Content Owner: {co_id}. Fetching managed channels...")
                    
                    # Fetch channels for this content owner
                    m_url = f"{self.base_url}/channels"
                    m_params = {
                        "part": "snippet,statistics",
                        "managedByMe": "true",
                        "onBehalfOfContentOwner": co_id,
                        "access_token": self.access_token
                    }
                    m_res = requests.get(m_url, params=m_params, timeout=10)
                    m_data = m_res.json()
                    
                    if "items" in m_data:
                        for item in m_data["items"]:
                            # Prevent duplicates if a channel is also in 'mine=true'
                            if not any(c["account_id"] == item["id"] for c in channels):
                                channels.append({
                                    "account_id": item["id"],
                                    "name": item["snippet"]["title"],
                                    "access_token": self.access_token,
                                    "content_owner_id": co_id,
                                    "snippet": item["snippet"],
                                    "statistics": item["statistics"]
                                })
            elif "error" in co_data and co_data["error"].get("code") != 403:
                # 403 usually means the user is just not a Content Owner, which is normal
                logger.debug(f"Content Owners API returned non-403 error: {co_data['error'].get('message')}")
        except Exception as e:
            logger.error(f"Error fetching managed YouTube Channels: {e}")

        return channels

    def get_channel_insights(self, channel_id: str, days: int = 30, start_date: str = None, end_date: str = None, content_owner_id: str = None):
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
        if content_owner_id:
            params["onBehalfOfContentOwner"] = content_owner_id
        
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
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        analytics_params = {
            "ids": f"contentOwner=={content_owner_id}" if content_owner_id else f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,subscribersGained,likes,comments,shares,estimatedMinutesWatched",
            "access_token": self.access_token
        }
        
        # Filter by channel if using a content owner
        if content_owner_id:
            analytics_params["filters"] = f"channel=={channel_id}"
        
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
                
                # Helper to safely convert potentially None values from API
                def safe_int(val):
                    try:
                        return int(float(val)) if val is not None else 0
                    except (ValueError, TypeError):
                        return 0

                # Map based on standard column headers index
                # views, subscribersGained, likes, comments, shares, estimatedMinutesWatched
                result["views_organic"] = safe_int(row[0])
                result["followers_new"] = safe_int(row[1])
                result["interactions"] = safe_int(row[2]) + safe_int(row[3]) + safe_int(row[4])
                result["accounts_reached"] = safe_int(row[0]) # YouTube Views ~ Reach
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics: {e}")
            if "data" in locals():
                logger.error(f"YouTube API raw data was: {data}")

        return result
