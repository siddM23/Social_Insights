import asyncio
import os
import sys
import requests
from pathlib import Path

# Add api directory to sys.path
api_path = Path(__file__).resolve().parent.parent
sys.path.append(str(api_path))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

async def test_pinterest_fields():
    token = os.getenv("PINTEREST_ACCESS_TOKEN") # Fallback to env if available
    if not token:
         # Try to find a token in the DB for the user
         from repositories.users_repository import UsersRepository
         repo = UsersRepository()
         integrations = await repo.scan_all_integrations() # This is deprecated/empty in my repo?
         # Check list_integrations for a known user
         user = await repo.get_user_by_email("siddharth@cubehq.ai")
         if user:
             user_id = user['PK'].replace('USER#', '')
             ints = await repo.list_integrations(user_id)
             p_int = next((i for i in ints if i['platform'] == 'pinterest'), None)
             if p_int:
                 token = p_int['encrypted_access_token']

    if not token:
        print("No token found.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    print("--- User Account Info ---")
    res = requests.get("https://api.pinterest.com/v5/user_account", headers=headers)
    print(res.json())

    print("\n--- User Account Analytics (Organic) ---")
    import datetime
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    url = "https://api.pinterest.com/v5/user_account/analytics"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "columns": "IMPRESSION,PIN_CLICK,SAVE,ENGAGEMENT,OUTBOUND_CLICK",
        "from_at_times": "ALL"
    }
    res = requests.get(url, headers=headers, params=params)
    print(res.json())

if __name__ == "__main__":
    asyncio.run(test_pinterest_fields())
