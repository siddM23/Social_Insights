
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

table = dynamodb.Table('app_status')
table.delete_item(Key={'id': 'global_sync'})
print("Sync limit reset.")
