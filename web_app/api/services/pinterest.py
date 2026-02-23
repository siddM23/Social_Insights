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
        Tries to use SDK for Ad Account analytics first, falls back to User Account analytics.
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

        # 1. Try Ad Accounts (Advanced Analytics)
        try:
            ad_url = f"{self.base_url}/ad_accounts"
            ad_res = requests.get(ad_url, headers=self.headers)
            
            if ad_res.status_code == 200:
                items = ad_res.json().get('items', [])
                if items:
                    target_account_id = items[0]['id']
                    try:
                        from pinterest.client import PinterestSDKClient
                        from pinterest.ads.ad_accounts import AdAccount
                        client = PinterestSDKClient.create_client_with_token(access_token=self.access_token)
                        
                        analytics = (
                            AdAccount(ad_account_id=target_account_id, client=client)
                            .get_analytics(
                                start_date=start_date.strftime('%Y-%m-%d'),
                                end_date=end_date.strftime('%Y-%m-%d'),
                                columns=["TOTAL_IMPRESSION", "TOTAL_ENGAGEMENT", "TOTAL_AUDIENCE_IMPRESSIONS", "TOTAL_SAVE", "TOTAL_OUTBOUND_CLICK", "TOTAL_PIN_CLICK"],
                                granularity="TOTAL"
                            )
                        )
                        
                        # Debug: Raw call to verify fields (as requested)
                        try:
                            raw_url = f"{self.base_url}/ad_accounts/{target_account_id}/analytics"
                            params = {
                                "start_date": start_date.strftime('%Y-%m-%d'),
                                "end_date": end_date.strftime('%Y-%m-%d'),
                                "columns": "TOTAL_IMPRESSION,TOTAL_AUDIENCE_IMPRESSIONS,TOTAL_ENGAGEMENT,TOTAL_SAVE,TOTAL_OUTBOUND_CLICK,TOTAL_PIN_CLICK",
                                "granularity": "TOTAL"
                            }
                            r = requests.get(raw_url, headers=self.headers, params=params)
                            logger.info(f"DEBUG Pinterest Raw Response: {r.json()}")
                        except: pass

                        result = analytics[0] if isinstance(analytics, list) and analytics else analytics
                        
                        def get_val(obj, keys):
                            for k in keys:
                                for variant in [k, k.upper(), k.lower()]:
                                    if isinstance(obj, dict):
                                        if variant in obj: return obj[variant]
                                    else:
                                        val = getattr(obj, variant, None)
                                        if val is not None: return val
                            return 0

                        stats["views"] = int(get_val(result, ["TOTAL_IMPRESSION", "IMPRESSION"]) or 0)
                        stats["engagements"] = int(get_val(result, ["TOTAL_ENGAGEMENT", "ENGAGEMENT"]) or 0)
                        stats["audience"] = int(get_val(result, ["TOTAL_AUDIENCE_IMPRESSIONS", "TOTAL_AUDIENCE", "AUDIENCE_IMPRESSIONS", "AUDIENCE"]) or 0)
                        stats["saves"] = int(get_val(result, ["TOTAL_SAVE", "SAVE"]) or 0)
                        stats["clicks"] = int(get_val(result, ["TOTAL_PIN_CLICK", "PIN_CLICK"]) or 0) + int(get_val(result, ["TOTAL_OUTBOUND_CLICK", "OUTBOUND_CLICK"]) or 0)
                        
                        if stats["views"] > 0: return stats
                        
                    except Exception as e:
                        logger.warning(f"SDK Analytics failed: {e}. Falling back.")

        except Exception as e:
            logger.error(f"Ad Account discovery failed: {e}")

        # 2. Fallback: User account analytics (Organic)
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
            
            # Helper to get from summary or daily sum
            def extract(key):
                if key in summary: return int(summary[key])
                return sum(int(day.get("metrics", {}).get(key, 0)) for day in all_data.get("daily_metrics", []))

            stats["views"] = extract("IMPRESSION")
            stats["clicks"] = extract("PIN_CLICK") + extract("OUTBOUND_CLICK")
            stats["saves"] = extract("SAVE")
            stats["engagements"] = extract("ENGAGEMENT")
            
            # For organic, Pinterest doesn't always provide Audience in the daily breakdown.
            # We'll try to get it from the summary if it exists under common names.
            stats["audience"] = int(summary.get("AUDIENCE") or summary.get("TOTAL_AUDIENCE") or summary.get("UNIQUE_USERS") or 0)

        return stats
