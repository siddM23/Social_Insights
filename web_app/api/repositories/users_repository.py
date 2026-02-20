from boto3.dynamodb.conditions import Key
from .base_repository import DynamoRepository

class UsersRepository(DynamoRepository):
    def __init__(self, session=None):
        super().__init__("Social_Insights_Users", session)

    async def create_user(self, email, password_hash):
        user_id = self.uuid()

        item = {
            "PK": f"USER#{user_id}",
            "SK": "PROFILE",
            "email": email,
            "password_hash": password_hash,
            "created_at": self.now_iso(),
        }

        await self.put(item)
        return user_id

    async def add_integration(self, user_id, platform, account_id,
                              encrypted_access_token, encrypted_refresh_token, **kwargs):

        item = {
            "PK": f"USER#{user_id}",
            "SK": f"INTEGRATION#{platform}#{account_id}",
            "platform": platform,
            "account_id": account_id,
            "encrypted_access_token": encrypted_access_token,
            "encrypted_refresh_token": encrypted_refresh_token,
            "created_at": self.now_iso(),
            **kwargs 
        }

        await self.put(item)

    async def list_integrations(self, user_id):
        async with self._table() as table:
            res = await table.query(
                KeyConditionExpression=Key("PK").eq(f"USER#{user_id}")
            )

            return [
                item for item in res.get("Items", [])
                if item["SK"].startswith("INTEGRATION#")
            ]

    async def scan_all_integrations(self):
        async with self._table() as table:
            # Efficient implementation depends on access patterns. 
            # With Single Table and PK=USER#..., scanning implies scanning the whole table
            # and filtering by SK, or using a GSI if available. 
            # Assuming no GSI effectively covers "all integrations across all users" yet.
            # We will Scan and filter.
            res = await table.scan()
            items = res.get("Items", [])
            # Handle pagination if needed? For MVP/Revamp scan is okay for small scale.
            
            integrations = []
            for item in items:
                if item.get("SK", "").startswith("INTEGRATION#"):
                    integrations.append(item)
            return integrations

    async def log_activity(self, user_id, activity_type, details=None):
        timestamp = self.now_iso()
        item = {
            "PK": f"USER#{user_id}",
            "SK": f"ACTIVITY#{timestamp}",
            "user_id": user_id,
            "timestamp": timestamp,
            "activity_type": activity_type,
            "details": details or {}
        }
        await self.put(item)

    async def get_sync_status(self, user_id):
        return await self.get(f"USER#{user_id}", "SYNC_STATUS")

    async def update_sync_status(self, user_id, status_data):
        item = {
            "PK": f"USER#{user_id}",
            "SK": "SYNC_STATUS",
            **status_data
        }
        await self.put(item)
