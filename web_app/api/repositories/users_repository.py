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

    async def get_user_by_email(self, email):
        async with self._table() as table:
            res = await table.query(
                IndexName="EmailIndex",
                KeyConditionExpression=Key("email").eq(email)
            )
            items = res.get("Items", [])
            return items[0] if items else None

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
    
    async def get_integration(self, user_id, platform, account_id):
        """Fetch a specific integration directly using PK and SK (O(1) cost)"""
        return await self.get(f"USER#{user_id}", f"INTEGRATION#{platform}#{account_id}")

    async def update_integration_status(self, user_id, platform, account_id, status, error_message=None):
        """Update the status of an integration (O(1) cost)"""
        # Get existing to preserve details
        item = await self.get_integration(user_id, platform, account_id)
        if not item:
            return

        item["status"] = status
        if error_message:
            item["last_error"] = error_message
            item["error_at"] = self.now_iso()
        
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
        """
        DEPRECATED: Scans are expensive and burn RCUs/Money.
        Returning empty list to prevent background sync from burning your credits.
        We will replace this with a GSI-based query later.
        """
        return []

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
