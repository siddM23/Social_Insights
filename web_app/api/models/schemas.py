from pydantic import BaseModel
from typing import Dict, Any, Optional

class IntegrationRequest(BaseModel):
    platform: str
    account_id: str
    account_name: str
    access_token: str
    additional_info: Optional[Dict[str, Any]] = None

class MetricRequest(BaseModel):
    account_id: str
    timestamp: str 
    followers_total: int
    followers_new: int
    views_organic: int
    views_ads: int
    interactions: int
    profile_visits: Optional[int] = 0
    accounts_reached: int

class UserAuthRequest(BaseModel):
    user_id: str
    password: str

class ActivityLogRequest(BaseModel):
    activity_type: str
    details: Optional[Dict[str, Any]] = None

class CustomMetricRequest(BaseModel):
    start_date: str # YYYY-MM-DD
    end_date: str # YYYY-MM-DD
