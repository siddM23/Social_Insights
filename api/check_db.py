import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def list_data():
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    print("--- Integrations ---")
    table_int = dynamodb.Table('socials_integrations')
    items_int = table_int.scan()['Items']
    for item in items_int:
        print(f"Platform: {item.get('platform')}, ID: {item.get('account_id')}, Name: {item.get('account_name')}")

    print("\n--- Metrics ---")
    table_met = dynamodb.Table('social_metrics')
    items_met = table_met.scan()['Items']
    for item in items_met:
        print(f"Account: {item.get('account_id')}, TS: {item.get('timestamp')}, Followers: {item.get('followers_total')}")

if __name__ == "__main__":
    list_data()
