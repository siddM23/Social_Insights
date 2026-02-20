import boto3
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

dynamodb = boto3.client(
    'dynamodb',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

tables = [
    {
        "TableName": "Social_Insights_Users",
        "KeySchema": [
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"}
        ],
        "BillingMode": "PAY_PER_REQUEST"
    },
    {
        "TableName": "Social_Insights_Metrics",
        "KeySchema": [
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"}
        ],
        "BillingMode": "PAY_PER_REQUEST"
    }
]

for table_def in tables:
    name = table_def["TableName"]
    try:
        dynamodb.describe_table(TableName=name)
        print(f"✅ Table '{name}' already exists.")
    except dynamodb.exceptions.ResourceNotFoundException:
        dynamodb.create_table(**table_def)
        print(f"🆕 Created table '{name}'.")
    except Exception as e:
        print(f"❌ Error checking table '{name}': {e}")
