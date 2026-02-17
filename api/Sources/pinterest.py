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
        Params:
            days: Number of days to look back (default 30)
            start_date_str: 'YYYY-MM-DD' (Optional)
            end_date_str: 'YYYY-MM-DD' (Optional)
        """
        import datetime
        stats = {
            "views": 0,
            "clicks": 0,
            "saves": 0,
            "engagements": 0,
            "audience": 0
        }

        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = datetime.date.today()

        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = end_date - datetime.timedelta(days=days)

        # 1. Try to discover Ad Accounts (Business Account)
        # Using requests for discovery as SDK discovery method might vary
        try:
            ad_url = f"{self.base_url}/ad_accounts"
            ad_res = requests.get(ad_url, headers=self.headers)
            
            if ad_res.status_code == 200:
                ad_data = ad_res.json()
                items = ad_data.get('items', [])
                
                if items:
                    target_account_id = items[0]['id']
                    
                    try:
                        from pinterest.client import PinterestSDKClient
                        from pinterest.ads.ad_accounts import AdAccount
                        
                        client = PinterestSDKClient.create_default_client(access_token=self.access_token)
                        
                        # SDK might require specific string format
                        analytics = (
                            AdAccount(ad_account_id=target_account_id, client=client)
                            .get_analytics(
                                start_date=start_date.strftime('%Y-%m-%d'),
                                end_date=end_date.strftime('%Y-%m-%d'),
                                columns=["IMPRESSION", "ENGAGEMENT", "AUDIENCE", "SAVE", "OUTBOUND_CLICK", "PIN_CLICK"],
                                granularity="TOTAL"
                            )
                        )
                        
                        # Process SDK response
                        # SDK typically returns an object or dict. Assuming dict or object with attributes.
                        # Based on user snippet, print(analytics) -> likely a response object.
                        # We need to inspect carefully. Assuming it acts like a dict or we can getattr.
                        # If it's a list, take the first item.
                        
                        # Defensive parsing
                        result = analytics
                        if isinstance(analytics, list) and analytics:
                            result = analytics[0]
                            
                        # Map fields
                        # Note: Attributes might be lowercase key properties in SDK objects
                        def get_val(obj, key):
                            if isinstance(obj, dict):
                                return obj.get(key, 0)
                            return getattr(obj, key, 0)

                        stats["views"] = int(get_val(result, "IMPRESSION") or 0)
                        stats["engagements"] = int(get_val(result, "ENGAGEMENT") or 0)
                        stats["audience"] = int(get_val(result, "AUDIENCE") or 0)
                        stats["saves"] = int(get_val(result, "SAVE") or 0)
                        stats["clicks"] = int(get_val(result, "PIN_CLICK") or 0) + int(get_val(result, "OUTBOUND_CLICK") or 0)
                        
                        return stats
                        
                    except ImportError:
                        logger.warning("pinterest-api-sdk not installed or import failed. Falling back to requests.")
                    except Exception as e:
                        logger.error(f"SDK Analytics failed: {e}. Falling back to User Account analytics.")

        except Exception as e:
            logger.error(f"Ad Account discovery failed: {e}")

        # 2. Fallback: User account analytics (Organic)
        url = f"{self.base_url}/user_account/analytics"
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "columns": "IMPRESSION,PIN_CLICK,SAVE,ENGAGEMENT,OUTBOUND_CLICK"
        }
        
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code != 200:
            logger.error(f"Error fetching Pinterest analytics: {res.text}")
            return stats # Return empty stats
            
        data = res.json()
        
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
            
        return stats
