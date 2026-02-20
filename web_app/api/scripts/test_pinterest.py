import asyncio
import os
import sys
import json
import datetime
from pathlib import Path
import boto3
from dotenv import load_dotenv

# Add parent and api dirs to path for imports
api_dir = Path(__file__).parent.parent
sys.path.append(str(api_dir))

# The root is 3 levels up from scripts/
root_dir = Path(__file__).parent.parent.parent.parent
load_dotenv(root_dir / '.env')

from services.pinterest import PinterestClient

async def test_pinterest_account(account_name):
    print(f"--- testing pinterest account: {account_name} ---")
    
    # 1. find integration in dynamodb
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    table = dynamodb.Table('Social_Insights_Users')
    
    # scan for the integration
    # in an real app we'd use a GSI, but for a debug script scan is fine
    response = table.scan()
    items = response.get('Items', [])
    
    found_acc = None
    for item in items:
        if item.get('SK', '').startswith('INTEGRATION#pinterest'):
            if item.get('account_name', '').lower() == account_name.lower():
                found_acc = item
                break
    
    if not found_acc:
        print(f"❌ error: could not find integration for '{account_name}' in database.")
        # list what we found to help debug
        print("\navailable pinterest accounts:")
        for item in items:
             if item.get('SK', '').startswith('INTEGRATION#pinterest'):
                 print(f"  - {item.get('account_name')} (ID: {item.get('account_id')})")
        return

    print(f"✅ found account: {found_acc.get('account_name')} ({found_acc.get('account_id')})")
    
    token = found_acc.get('encrypted_access_token') # naming from your schema
    client = PinterestClient(token)
    
    # 2. raw api test
    now = datetime.datetime.utcnow().date()
    start_date = now - datetime.timedelta(days=30)
    
    print(f"\n--- raw api call (30 days: {start_date} to {now}) ---")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # User account analytics
        user_url = "https://api.pinterest.com/v5/user_account/analytics"
        
        # Use a range that is definitely READY (e.g., 7-14 days ago)
        test_start = (now - datetime.timedelta(days=14)).strftime('%Y-%m-%d')
        test_end = (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"\n--- testing user_account/analytics ({test_start} to {test_end}) ---")
        
        # Request a kitchen sink of possible columns
        cols = "IMPRESSION,PIN_CLICK,SAVE,ENGAGEMENT,OUTBOUND_CLICK,AUDIENCE,TOTAL_AUDIENCE,UNIQUE_USERS,MONTHLY_ACTIVE_USERS"
        params = {
            "start_date": test_start,
            "end_date": test_end,
            "columns": cols,
            "from_at_times": "ALL"
        }
        user_res = requests_get_with_log(user_url, headers, params)
        
        if user_res.get('all'):
            all_data = user_res['all']
            print("\n✅ SUMMARY_METRICS KEYS:")
            print(list(all_data.get('summary_metrics', {}).keys()))
            print("Summary Values:", all_data.get('summary_metrics'))
            
            daily = all_data.get('daily_metrics', [])
            if daily:
                ready_day = next((d for d in daily if d.get('data_status') == 'READY'), None)
                if ready_day:
                    print(f"\n✅ DAILY_METRICS KEYS (for {ready_day['date']}):")
                    print(list(ready_day.get('metrics', {}).keys()))
                else:
                    print("\nℹ️ No READY days found in daily_metrics.")
            
    except Exception as e:
        print(f"❌ error during raw fetch: {e}")

    # 3. test the existing service logic
    print("\n--- testing existing service logic output ---")
    try:
        res = client.get_analytics(days=30)
        print("MAPPED STATS:")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"❌ error in get_analytics: {e}")

def requests_get_with_log(url, headers, params=None):
    import requests
    print(f"GET {url}")
    if params: print(f"  params: {params}")
    r = requests.get(url, headers=headers, params=params)
    print(f"  status: {r.status_code}")
    try:
        return r.json()
    except:
        return {"text": r.text}

if __name__ == "__main__":
    acc = "BLACKBROOK_CASE"
    asyncio.run(test_pinterest_account(acc))
