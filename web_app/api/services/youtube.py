import requests
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

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
            
            if co_res.status_code == 200:
                try:
                    co_data = co_res.json()
                except ValueError:
                    logger.error(f"Failed to decode JSON from Content Owners API. Response: {co_res.text[:100]}")
                    co_data = {}
            else:
                logger.debug(f"Content Owners API returned status {co_res.status_code}")
                co_data = {}
            
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
                    
                    if m_res.status_code == 200:
                        try:
                            m_data = m_res.json()
                        except ValueError:
                            logger.error(f"Failed to decode JSON from managed channels API for CO {co_id}")
                            continue
                        
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
        Uses Data API for real-time totals and Analytics API for historical deltas.
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. Get REAL-TIME stats via Data API (Total Followers & Total Views)
        url = f"{self.base_url}/channels"
        params = {
            "part": "statistics",
            "id": channel_id
        }
        if content_owner_id:
            params["onBehalfOfContentOwner"] = content_owner_id
        
        followers_total = 0
        views_total = 0
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            data = res.json()
            if "items" in data and len(data["items"]) > 0:
                stats = data["items"][0]["statistics"]
                followers_total = int(stats.get("subscriberCount", 0))
                views_total = int(stats.get("viewCount", 0))
                logger.info(f"Real-time stats for {channel_id}: Subs={followers_total}, Views={views_total}")
        except Exception as e:
            logger.error(f"Error fetching YouTube real-time stats: {e}")

        # 2. Get Aggregated Metrics via Analytics API
        # YouTube analytics are delayed by ~48-72 hours. 
        # Requesting 'today' or 'yesterday' often returns 0.
        # We shift the end_date back to ensure we get data.
        
        if not end_date:
            # Shift end date back by 3 days to hit stable data
            end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=days+3)).strftime("%Y-%m-%d")
        
        analytics_params = {
            "ids": f"contentOwner=={content_owner_id}" if content_owner_id else f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,subscribersGained,likes,comments,shares,estimatedMinutesWatched",
        }
        
        if content_owner_id:
            analytics_params["filters"] = f"channel=={channel_id}"
        
        result = {
            "followers_total": followers_total, # Real-time
            "followers_new": 0,
            "views_total": views_total,         # Real-time
            "views_organic": 0,                 # Historical delta
            "views_ads": 0,
            "interactions": 0,
            "accounts_reached": 0,
            "watch_time_hours": Decimal("0.0")
        }

        res = None
        try:
            # First Query: Totals for everything (Likes, subs, etc.)
            res = requests.get(self.analytics_url, params=analytics_params, headers=headers, timeout=15)
            data = res.json()
            
            if "rows" in data and len(data["rows"]) > 0:
                row = data["rows"][0]
                def safe_int(val):
                    try:
                        return int(float(val)) if val is not None else 0
                    except (ValueError, TypeError):
                        return 0

                # Temporary total views from this period
                total_views_period = safe_int(row[0])
                result["followers_new"] = safe_int(row[1])
                result["interactions"] = safe_int(row[2]) + safe_int(row[3]) + safe_int(row[4])
                result["accounts_reached"] = total_views_period
                
                # watch_time_hours = estimatedMinutesWatched / 60
                est_minutes = float(row[5]) if len(row) > 5 and row[5] is not None else 0
                result["watch_time_hours"] = Decimal(str(round(est_minutes / 60, 2)))

                # Second Query: Traffic Sources to isolate ADVERTISING views
                source_params = analytics_params.copy()
                source_params["dimensions"] = "insightTrafficSourceType"
                source_params["metrics"] = "views"
                
                source_res = requests.get(self.analytics_url, params=source_params, headers=headers, timeout=15)
                if source_res.status_code != 200:
                    logger.error(f"YouTube Traffic Source API error ({source_res.status_code}): {source_res.text}")
                    source_data = {}
                else:
                    source_data = source_res.json()
                
                ad_views = 0
                if "rows" in source_data:
                    for s_row in source_data["rows"]:
                        if s_row[0] == "ADVERTISING":
                            ad_views = safe_int(s_row[1])
                            break
                
                result["views_ads"] = ad_views
                result["views_organic"] = max(0, total_views_period - ad_views)
                
                logger.info(f"Traffic Source split for {channel_id}: Organic={result['views_organic']}, Ads={result['views_ads']}")
            else:
                if res is not None and res.status_code != 200:
                    logger.error(f"YouTube Analytics API error ({res.status_code}): {res.text}")
                else:
                    logger.warning(f"No analytics rows returned for {channel_id} in window {start_date} to {end_date}. Full response: {data}")
        except Exception as e:
            logger.error(f"Error fetching YouTube analytics for {channel_id}: {e}")
            if res is not None:
                logger.error(f"YouTube API response status: {res.status_code}")
                logger.error(f"YouTube API response text: {res.text[:500]}")



        return result
