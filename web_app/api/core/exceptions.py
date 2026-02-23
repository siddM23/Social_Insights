
class SocialInsightsError(Exception):
    """Base class for all app-specific errors"""
    pass

class TokenExpiredError(SocialInsightsError):
    """Access token is dead, but refresh might be possible"""
    def __init__(self, platform, account_id):
        self.platform = platform
        self.account_id = account_id
        super().__init__(f"Token expired for {platform} account {account_id}")

class TerminalTokenError(SocialInsightsError):
    """Both access AND refresh tokens are dead. User ACTION REQUIRED."""
    def __init__(self, platform, account_id, message="Re-authentication required"):
        self.platform = platform
        self.account_id = account_id
        self.message = message
        super().__init__(f"Terminal token failure for {platform}: {message}")
