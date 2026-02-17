import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'api'))
from main import metrics_db
print(f"Table Name: {metrics_db.table_name}")
