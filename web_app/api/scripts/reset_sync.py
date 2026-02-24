import asyncio
import os
import sys
from pathlib import Path

# Add api directory to sys.path
api_path = Path(__file__).resolve().parent.parent
sys.path.append(str(api_path))

from dotenv import load_dotenv

# Robustly find the .env file in the root directory
# __file__ is /Users/.../web_app/api/scripts/reset_sync.py
# .parent.parent.parent is /Users/.../web_app/
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from repositories.users_repository import UsersRepository

async def reset_sync_counter(email: str):
    repo = UsersRepository()
    
    # 1. Find the user by email
    user = await repo.get_user_by_email(email)
    if not user:
        print(f"Error: User with email {email} not found.")
        return

    user_id = user['PK'].replace('USER#', '')
    print(f"Found user: {email} (ID: {user_id})")

    # 2. Reset the sync status
    new_status = {
        'sync_count': 0,
        'sync_limit_stat': False,
        'last_sync_time': None
    }
    
    await repo.update_sync_status(user_id, new_status)
    print(f"Successfully reset sync counter for {email} to 0.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_sync.py <user_email>")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(reset_sync_counter(email))
