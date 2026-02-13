import os
from dotenv import load_dotenv
from Db.database import DynamoDB

load_dotenv()

def init_tables():
    print("Initializing social_users table...")
    users_db = DynamoDB('social_users')
    # PK: user_id (Email or Username)
    users_db.create_table(pk='user_id')

    print("\nInitializing user_activity table...")
    activity_db = DynamoDB('user_activity')
    # PK: activity_id (UUID)
    # SK: timestamp (ISO String)
    activity_db.create_table(pk='user_id', sk='timestamp')

    print("\nInitializing social_metrics table...")
    metrics_db = DynamoDB('social_metrics')
    # PK: account_id (composite: platform#id)
    # SK: timestamp
    metrics_db.create_table(pk='account_id', sk='timestamp')

    print("\nTable initialization complete.")

if __name__ == "__main__":
    init_tables()
