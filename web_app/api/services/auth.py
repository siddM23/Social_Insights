
import os
import requests
from urllib.parse import urlencode
import logging

logger = logging.getLogger("social_insights.auth")
yt_logger = logging.getLogger("social_insights.auth.youtube")
yt_logger.setLevel(logging.DEBUG)

class InstagramAuth:
    def __init__(self):
        self.app_id = os.getenv("Instagram_app_id")
        self.app_secret = os.getenv("Instagram_app_secret")
        self.redirect_uri = os.getenv("INSTAGRAM_REDIRECT_URI", "http://localhost:8000/auth/instagram/callback")
        self.base_url = "https://www.facebook.com/v19.0/dialog/oauth"
        self.token_url = "https://graph.facebook.com/v19.0/oauth/access_token"

    def get_auth_url(self, state: str = None):
        """Build the Meta OAuth URL"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "pages_show_list,instagram_basic,instagram_manage_insights,pages_read_engagement,public_profile",
            "response_type": "code"
        }
        if state:
            params["state"] = state
        return f"{self.base_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str):
        """Exchange the auth code for a short-lived access token, then upgrade to long-lived"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.app_secret,
            "code": code
        }
        
        # 1. Short-lived token
        try:
            res = requests.get(self.token_url, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            logger.error(f"Network error getting short-lived token: {e}")
            return None
        
        if "error" in data:
            logger.error(f"Error exchanging code: {data['error'].get('message')}")
            return None

        short_token = data.get("access_token")
        
        # 2. Upgrade to Long-lived token (60 days)
        upgrade_params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_token
        }
        
        try:
            upgrade_res = requests.get(self.token_url, params=upgrade_params, timeout=10)
            long_data = upgrade_res.json()
        except Exception as e:
            logger.error(f"Network error upgrading token: {e}")
            return data # Return short token as fallback

        if "error" in long_data:
            logger.error(f"Error upgrading token: {long_data['error'].get('message')}")
            return data # Return short token as fallback
            
        return long_data

class PinterestAuth:
    def __init__(self):
        self.client_id = os.getenv("Pinterest_app_id")
        self.client_secret = os.getenv("Pinterest_app_secret")
        # Match accurately to the Pinterest Dashboard setting: http://localhost:8000/auth/callback
        self.redirect_uri = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:8000/auth/pinterest/callback")
        self.auth_url = "https://www.pinterest.com/oauth/"
        self.token_url = "https://api.pinterest.com/v5/oauth/token"

    def get_auth_url(self, state: str = None):
        """Build the Pinterest OAuth URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "user_accounts:read,pins:read,boards:read,ads:read"
        }
        if state:
            params["state"] = state
        return f"{self.auth_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str):
        """Exchange the auth code for an access token"""
        import base64
        
        # Pinterest requires Basic Auth for the token exchange
        auth_string = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        res = requests.post(self.token_url, headers=headers, data=data)
        token_data = res.json()
        
        if "error" in token_data:
            logger.error(f"Pinterest Token Error: {token_data.get('error_description', token_data.get('error'))}")
            return None
            
        return token_data
    async def refresh_token(self, refresh_token: str):
        """Exchange a refresh token for a new access token"""
        import base64
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        logger.info("Attempting to refresh Pinterest access token")
        res = requests.post(self.token_url, headers=headers, data=data)
        token_data = res.json()
        
        if "error" in token_data:
            logger.error(f"Pinterest Token Refresh Error: {token_data.get('error_description', token_data.get('error'))}")
            return None
            
        return token_data

class MetaAuth:
    def __init__(self):
        self.app_id = os.getenv("Instagram_app_id") # Use same Meta App credentials
        self.app_secret = os.getenv("Instagram_app_secret")
        self.redirect_uri = os.getenv("META_REDIRECT_URI", "http://localhost:8000/auth/meta/callback")
        self.base_url = "https://www.facebook.com/v19.0/dialog/oauth"
        self.token_url = "https://graph.facebook.com/v19.0/oauth/access_token"

    def get_auth_url(self, state: str = None):
        """Build the Meta OAuth URL for Facebook Pages"""
        # Reduced scope to core essentials to minimize friction
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": "pages_show_list,pages_read_engagement,public_profile,read_insights",
            "response_type": "code"
        }
        if state:
            params["state"] = state
        url = f"{self.base_url}?{urlencode(params)}"
        logger.info(f"Generated Meta Auth URL: {url}")
        return url

    def exchange_code_for_token(self, code: str):
        """Exchange the auth code for a short-lived access token, then upgrade to long-lived"""
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.app_secret,
            "code": code
        }
        
        logger.info(f"Exchanging code for Meta token. Client ID: {self.app_id}")
        
        # 1. Short-lived token
        try:
            res = requests.get(self.token_url, params=params, timeout=10)
            data = res.json()
        except Exception as e:
            logger.error(f"Network error exchanging Meta code: {e}")
            return None
        
        if "error" in data:
            logger.error(f"Meta error exchanging code: {data['error'].get('message')}")
            return None

        short_token = data.get("access_token")
        logger.info("Successfully received Meta short-lived token")
        
        # 2. Upgrade to Long-lived token (60 days)
        upgrade_params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_token
        }
        
        try:
            upgrade_res = requests.get(self.token_url, params=upgrade_params, timeout=10)
            long_data = upgrade_res.json()
        except Exception as e:
            logger.error(f"Network error upgrading Meta token: {e}")
            return data
            
        if "error" in long_data:
            logger.error(f"Meta error upgrading token: {long_data['error'].get('message')}")
            return data
            
        logger.info("Successfully upgraded to Meta long-lived token")
        return long_data

class YouTubeAuth:
    def __init__(self):
        yt_logger.info("Initializing YouTubeAuth")
        self.client_id = os.getenv("youtube_client_id", os.getenv("GOOGLE_CLIENT_ID"))
        self.client_secret = os.getenv("youtube_client_secret", os.getenv("GOOGLE_CLIENT_SECRET"))
        self.redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/youtube/callback"))
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        
        if not self.client_id:
            yt_logger.warning("YouTube client_id is missing (from youtube_client_id or GOOGLE_CLIENT_ID)")
        if not self.client_secret:
            yt_logger.warning("YouTube client_secret is missing")
        yt_logger.debug(f"YouTube Redirect URI: {self.redirect_uri}")

    def get_auth_url(self, state: str = None):
        """Build the Google OAuth URL for YouTube"""
        yt_logger.info(f"Building YouTube auth URL. State: {state}")
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly openid email profile",
            "access_type": "offline",
            "prompt": "select_account consent"
        }
        if state:
            params["state"] = state
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        yt_logger.debug(f"YouTube Auth URL generated: {auth_url}")
        return auth_url

    def exchange_code_for_token(self, code: str):
        """Exchange the auth code for an access token and refresh token"""
        yt_logger.info(f"Exchanging YouTube auth code. Code prefix: {code[:10]}...")
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        yt_logger.debug(f"Token exchange request payload: client_id={self.client_id}, redirect_uri={self.redirect_uri}")
        
        try:
            yt_logger.info(f"POSTing to {self.token_url}")
            res = requests.post(self.token_url, data=data, timeout=10)
            yt_logger.info(f"YouTube token exchange response status: {res.status_code}")
            token_data = res.json()
            if res.status_code != 200:
                yt_logger.error(f"YouTube token exchange failed. Response: {token_data}")
            else:
                yt_logger.debug(f"YouTube token data keys received: {list(token_data.keys())}")
        except Exception as e:
            yt_logger.error(f"Network error exchanging YouTube code: {e}")
            return None
            
        if "error" in token_data:
            yt_logger.error(f"YouTube OAuth error: {token_data.get('error_description', token_data.get('error'))}")
            return None
            
        yt_logger.info("Successfully exchanged YouTube code for tokens")
        return token_data
