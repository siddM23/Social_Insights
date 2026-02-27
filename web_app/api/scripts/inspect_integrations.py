import asyncio
import os
import sys
from pathlib import Path

# Add api directory to sys.path
api_path = Path(__file__).resolve().parent.parent
sys.path.append(str(api_path))

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from repositories.users_repository import UsersRepository

async def inspect_integrations(email: str):
    repo = UsersRepository()
    
    user = await repo.get_user_by_email(email)
    if not user:
        print(f"Error: User with email {email} not found.")
        return

    user_id = user['PK'].replace('USER#', '')
    print(f"User ID: {user_id}")
    
    integrations = await repo.list_integrations(user_id)
    print(f"\nFound {len(integrations)} integrations:")
    for i in integrations:
        print(f" - {i['platform']}: {i['account_id']} ({i.get('account_name', 'N/A')})")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else 'test3@cubehq.ai'
    asyncio.run(inspect_integrations(email))
