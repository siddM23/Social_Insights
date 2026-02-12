# Vercel Deployment Plan for Social Insights

This plan outlines the steps to deploy your **Next.js Frontend** and **Python Backend** (FastAPI) to Vercel in a single "monorepo" deployment under the domain `social.siddharthmedhamurthy.com`.

## Strategy: Standard Vercel Structure

To achieve a unified deployment where:
- `social.siddharthmedhamurthy.com/` serves the **Frontend**
- `social.siddharthmedhamurthy.com/api/*` serves the **Backend**

We need to align the project structure with Vercel's conventions. Vercel automatically detects Next.js at the project root and Python Serverless Functions in the `api/` directory.

### Current Structure vs. Target Structure

**Current:**
```
/
├── backend/       (FastAPI app)
└── frontend/      (Next.js app)
```

**Target:**
```
/
├── package.json   (From frontend)
├── next.config.ts (From frontend)
├── src/           (From frontend)
├── public/        (From frontend)
└── api/           (Renamed from backend)
    ├── index.py   (Entry point for Vercel)
    └── ...other backend files
```

---

## Step-by-Step Implementation Plan

### 1. Restructure Backend (`backend/` -> `api/`)
- Rename the `backend` folder to `api`.
- Create an `api/index.py` file. This is the Vercel entry point. It will import your FastAPI `app` instance.
- Ensure `requirements.txt` is present in the `api/` folder.

### 2. Restructure Frontend (`frontend/*` -> `./`)
- Move all files from `frontend/` to the root directory `.`
- Merge `.gitignore` files if necessary.

### 3. Configure `vercel.json` (Routing)
- Create a `vercel.json` file at the root to handle routing rewrites.
- This ensures all requests to `/api/*` are routed to the FastAPI app, while everything else goes to Next.js.
- **No Nginx is required.** Vercel's Edge Network handles the routing/reverse proxying.

**Example `vercel.json`:**
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index.py" }
  ]
}
```

### 4. Configure `api/index.py`
This file adapters the FastAPI app for Vercel.

```python
from api.main import app

# Vercel looks for a variable named 'app' or 'handler'
```

### 5. Update Frontend API Calls
- Ensure the frontend makes requests to `/api/...` instead of `localhost:8000` or absolute URLs.
- In `next.config.ts`, we can add a rewrite for local development to proxy `/api` to `localhost:8000`.

### 6. Environment Variables
- Add your environment variables (from `.env` and `global.env`) to the Vercel Project Settings.
- Examples: `meta_gapi`, `FRONTEND_URL`, AWS Credentials for DynamoDB.

---

## Execution
I can perform the restructuring (Steps 1, 2, 3, and 4) for you immediately.

**Shall I proceed with moving `frontend/` to root and `backend/` to `api/`?**
