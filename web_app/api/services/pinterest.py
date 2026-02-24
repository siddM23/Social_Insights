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

    def get_analytics(self, ad_account_id: str = None, days: int = 30, start_date_str: str = None, end_date_str: str = None):
        """
        Get Pinterest Analytics. 
        Tries to use Ad Account analytics (which includes Audience/Uniques) first.
        """
        import datetime
        stats = {"views": 0, "clicks": 0, "saves": 0, "engagements": 0, "audience": 0}

        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = datetime.date.today()

        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = end_date - datetime.timedelta(days=days)

        # 1. Try Ad Accounts (Required for 'Total Audience' / Unique Viewers)
        try:
            ad_url = f"{self.base_url}/ad_accounts"
            ad_res = requests.get(ad_url, headers=self.headers)
            
            if ad_res.status_code == 200:
                items = ad_res.json().get('items', [])
                if items:
                    target_account_id = items[0]['id']
                    logger.info(f"Found Pinterest Ad Account: {target_account_id}. Fetching advanced metrics...")
                    
                    try:
                        # Direct HTTP call for more control over columns
                        raw_url = f"{self.base_url}/ad_accounts/{target_account_id}/analytics"
                        params = {
                            "start_date": start_date.strftime('%Y-%m-%d'),
                            "end_date": end_date.strftime('%Y-%m-%d'),
                            "columns": "TOTAL_IMPRESSION,TOTAL_ENGAGEMENT,TOTAL_SAVE,TOTAL_PIN_CLICK,TOTAL_OUTBOUND_CLICK,TOTAL_AUDIENCE",
                            "granularity": "TOTAL"
                        }
                        r = requests.get(raw_url, headers=self.headers, params=params)
                        if r.status_code == 200:
                            data = r.json()
                            logger.debug(f"Pinterest Ad Analytics Data: {data}")
                            
                            # Result is often a dictionary or a list of one item
                            result = data[0] if isinstance(data, list) and data else data
                            
                            def get_val(obj, keys):
                                for k in keys:
                                    if k in obj: return obj[k]
                                return 0

                            stats["views"] = int(get_val(result, ["TOTAL_IMPRESSION"]) or 0)
                            stats["engagements"] = int(get_val(result, ["TOTAL_ENGAGEMENT"]) or 0)
                            stats["audience"] = int(get_val(result, ["TOTAL_AUDIENCE"]) or 0)
                            stats["saves"] = int(get_val(result, ["TOTAL_SAVE"]) or 0)
                            stats["clicks"] = int(get_val(result, ["TOTAL_PIN_CLICK"]) or 0) + int(get_val(result, ["TOTAL_OUTBOUND_CLICK"]) or 0)
                            
                            if stats["views"] > 0:
                                return stats
                    except Exception as e:
                        logger.warning(f"Pinterest Ad analytics call failed: {e}")
        except Exception as e:
            logger.error(f"Pinterest Ad Account discovery failed: {e}")

        # 2. Fallback: User account analytics (Organic - Audience metric is often omitted here by Pinterest)
        logger.info("Falling back to Pinterest User (Organic) analytics...")
        url = f"{self.base_url}/user_account/analytics"
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "columns": "IMPRESSION,PIN_CLICK,SAVE,ENGAGEMENT,OUTBOUND_CLICK",
            "from_at_times": "ALL"
        }
        
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code == 200:
            data = res.json()
            all_data = data.get("all", {})
            summary = all_data.get("summary_metrics", {})
            
            def extract(key):
                return int(summary.get(key, 0))

            stats["views"] = extract("IMPRESSION")
            stats["clicks"] = extract("PIN_CLICK") + extract("OUTBOUND_CLICK")
            stats["saves"] = extract("SAVE")
            stats["engagements"] = extract("ENGAGEMENT")
            
            # Note: Pinterest Organic API almost NEVER provides 'Audience' (Unique Users).
            # It only provides Impressions.
            stats["audience"] = 0 
            logger.info(f"Pinterest Organic Sync complete. Views: {stats['views']}")

        return stats
