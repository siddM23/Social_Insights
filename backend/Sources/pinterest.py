import requests
import logging
import json
import os

logger = logging.getLogger("social_insights.pinterest")

class PinterestClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.pinterest.com/v5"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_account_info(self):
        """Get the authenticated user's account information"""
        url = f"{self.base_url}/user_account"
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            logger.error(f"Error fetching Pinterest account: {res.text}")
            return None
        return res.json()

    def get_analytics(self, ad_account_id: str = None):
        """
        Get Pinterest Analytics. 
        Note: Pinterest metrics can be complex. 
        We'll try to get basic engagement metrics.
        """
        # User account analytics
        url = f"{self.base_url}/user_account/analytics"
        # We need a date range. Let's take last 30 days.
        import datetime
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "columns": "IMPRESSION,PIN_CLICK,SAVE,ENGAGEMENT,OUTBOUND_CLICK"
        }
        
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code != 200:
            logger.error(f"Error fetching Pinterest analytics: {res.text}")
            return None
            
        data = res.json()
        logger.info(f"Pinterest raw analytics response: {json.dumps(data)}")
        
        stats = {
            "views": 0,
            "clicks": 0,
            "saves": 0,
            "engagements": 0,
            "audience": 0
        }
        
        # Pinterest V5 returns daily metrics in 'all' -> 'daily_metrics'
        if "all" in data:
            all_data = data["all"]
            
            # 1. Try to get summary metrics if available
            summary = all_data.get("summary_metrics", {})
            if summary:
                stats["views"] = int(summary.get("IMPRESSION", 0))
                stats["clicks"] = int(summary.get("PIN_CLICK", 0)) + int(summary.get("OUTBOUND_CLICK", 0))
                stats["saves"] = int(summary.get("SAVE", 0))
                stats["engagements"] = int(summary.get("ENGAGEMENT", 0))
            else:
                # 2. Sum up daily metrics
                daily = all_data.get("daily_metrics", [])
                for day in daily:
                    metrics = day.get("metrics", {})
                    stats["views"] += int(metrics.get("IMPRESSION", 0))
                    stats["clicks"] += int(metrics.get("PIN_CLICK", 0)) + int(metrics.get("OUTBOUND_CLICK", 0))
                    stats["saves"] += int(metrics.get("SAVE", 0))
                    stats["engagements"] += int(metrics.get("ENGAGEMENT", 0))
            
        logger.info(f"Final aggregated Pinterest stats: {stats}")
        return stats
