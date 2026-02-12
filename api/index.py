import os
import sys

# Add the current directory to sys.path so that imports in main.py work
# (e.g., 'from Db import ...', 'from auth import ...')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app

# Vercel-specific: Handle the /api prefix if necessary
# If Vercel doesn't strip the prefix, we might need to adjust root_path
# app.root_path = "/api"
