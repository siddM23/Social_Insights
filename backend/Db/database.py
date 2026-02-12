import boto3
import os
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

class DynamoDB:
    def __init__(self, table_name: str):
        """
        Initialize DynamoDB connection.
        """
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.table_name = table_name
        self.table = self.dynamodb.Table(table_name)

    def create_table(self, pk: str, sk: str = None, sk_type: str = 'S'):
        """
        Creates the table if it doesn't exist.
        """
        try:
            # Check if table exists
            existing_tables = [t.name for t in self.dynamodb.tables.all()]
            if self.table_name in existing_tables:
                print(f"Table {self.table_name} already exists.")
                return True

            print(f"Creating table {self.table_name}...")
            
            key_schema = [{'AttributeName': pk, 'KeyType': 'HASH'}]
            attribute_definitions = [{'AttributeName': pk, 'AttributeType': 'S'}]

            if sk:
                key_schema.append({'AttributeName': sk, 'KeyType': 'RANGE'})
                attribute_definitions.append({'AttributeName': sk, 'AttributeType': sk_type})

            table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            self.table = self.dynamodb.Table(self.table_name)
            print(f"Table {self.table_name} created successfully.")
            return True
        except ClientError as e:
            print(f"Error creating table {self.table_name}: {e}")
            return False

    def save_item(self, item: Dict[str, Any]):
        """
        Generic save item method.
        """
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error saving item to {self.table_name}: {e}")
            return False

    def get_item(self, key: Dict[str, Any]):
        """
        Generic get item method.
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting item from {self.table_name}: {e}")
            return None

    def scan_items(self):
        """
        Generic scan method.
        """
        try:
            response = self.table.scan()
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error scanning {self.table_name}: {e}")
            return []

    def query_items(self, key_condition_expression, expression_attribute_values):
         try:
            response = self.table.query(
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return response.get('Items', [])
         except ClientError as e:
            print(f"Error querying {self.table_name}: {e}")
            return []
    def delete_item(self, key: Dict[str, Any]):
        """
        Generic delete item method.
        """
        try:
            self.table.delete_item(Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting item from {self.table_name}: {e}")
            return False
