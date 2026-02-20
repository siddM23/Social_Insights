from boto3.dynamodb.conditions import Key
from .base_repository import DynamoRepository

TTL_DAYS = 90  # configurable retention

class MetricsRepository(DynamoRepository):
    def __init__(self, session=None):
        super().__init__("Social_Insights_Metrics", session)

    async def upsert_daily_metrics(
        self,
        platform,
        account_id,
        date,
        metrics: dict
    ):
        item = {
            "PK": f"INTEGRATION#{platform}#{account_id}",
            "SK": f"DATE#{date}",
            "date": date,
            "created_at": self.now_iso(),
            "ttl": self.ttl_epoch(TTL_DAYS),
            **metrics
        }

        await self.put(item)

    async def get_metrics_range(self, platform, account_id, start_date, end_date, scan_index_forward=False):
        pk = f"INTEGRATION#{platform}#{account_id}"

        async with self._table() as table:
            res = await table.query(
                KeyConditionExpression=(
                    Key("PK").eq(pk) &
                    Key("SK").between(
                        f"DATE#{start_date}",
                        f"DATE#{end_date}"
                    )
                ),
                ScanIndexForward=scan_index_forward
            )
            return res.get("Items", [])
