from typing import TypedDict, Dict, Any

class MetricsPayload(TypedDict, total=False):
    followers_total: int
    followers_new: int
    impressions_total: int
    impressions_organic: int
    impressions_paid: int
    reach: int
    audience_total: int
    audience_engaged: int
    interactions: int
    saves: int
    views: int
    watch_time_hours: float
    raw_metrics: Dict[str, Any]  # Stores period_7d, period_30d, period_180d data
