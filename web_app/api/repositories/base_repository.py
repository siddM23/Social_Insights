import aioboto3
from datetime import datetime
import uuid
import time
import os

import contextlib

class DynamoRepository:
    def __init__(self, table_name: str, session=None):
        self.table_name = table_name
        self.session = session or aioboto3.Session()

    @contextlib.asynccontextmanager
    async def _table(self):
        async with self.session.resource("dynamodb", 
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        ) as dynamo:
            yield await dynamo.Table(self.table_name)

    async def put(self, item: dict):
        async with self._table() as table:
            await table.put_item(Item=item)

    async def get(self, pk: str, sk: str):
        async with self._table() as table:
            res = await table.get_item(Key={"PK": pk, "SK": sk})
            return res.get("Item")

    async def delete(self, pk: str, sk: str):
        async with self._table() as table:
            await table.delete_item(Key={"PK": pk, "SK": sk})

    @staticmethod
    def now_iso():
        return datetime.utcnow().isoformat()

    @staticmethod
    def uuid():
        return str(uuid.uuid4())

    @staticmethod
    def ttl_epoch(days: int):
        return int(time.time()) + days * 86400
