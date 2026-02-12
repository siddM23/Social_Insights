# 🔍 Deep Dive: Route Structure Analysis & 404 Issues

## Executive Summary

**Critical Finding**: Your application has a **fundamental architecture mismatch**. The routes are configured to proxy API requests to a Python FastAPI backend, but **the Python backend is not running**. This is causing 404 errors on all API endpoints.

---

## 📁 Current Project Structure

```
/Users/rmm/CUBE/Social_Insights/
├── app/                          # Next.js Frontend + Python API
│   ├── src/                      # Next.js source
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── dash/
│   │   │   │   └── page.tsx     # Dashboard at /dash
│   │   │   ├── integrations/
│   │   │   │   └── page.tsx     # Integrations at /integrations
│   │   │   ├── layout.tsx        # Root layout
│   │   │   ├── page.tsx          # Home page at /
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   └── Sidebar.tsx
│   │   └── lib/
│   ├── api/                      # Python FastAPI Backend
│   │   ├── index.py              # Main FastAPI app (623 lines)
│   │   ├── auth.py               # OAuth handlers
│   │   ├── Db/
│   │   │   └── database.py       # DynamoDB client
│   │   ├── Sources/
│   │   │   ├── instagram.py
│   │   │   ├── meta.py
│   │   │   ├── pinterest.py
│   │   │   └── youtube.py
│   │   └── requirements.txt
│   ├── vercel.json               # Vercel routing config
│   ├── package.json
│   └── next.config.ts
```

---

## 🚨 Critical Issues Identified

### **Issue #1: Python Backend Not Running**

**Problem**: The FastAPI backend (`/app/api/index.py`) is NOT running.

**Evidence**:
- Testing `http://localhost:3000/api` returns Next.js HTML, not FastAPI JSON
- Expected response: `{"status": "ok", "service": "Social Insights Backend"}`
- Actual response: Next.js 404 page or redirect

**Impact**: 
- ❌ All API routes return 404
- ❌ OAuth callbacks fail (`/api/auth/*/callback`)
- ❌ Data fetching fails (`/api/integrations`, `/api/metrics/*`)
- ❌ Sync operations fail (`/api/sync`)

---

### **Issue #2: Vercel.json Routing Misconfiguration**

**Current Configuration** (`/app/vercel.json`):
```json
{
    "rewrites": [
        {
            "source": "/api/(.*)",
            "destination": "/api/index.py"
        }
    ]
}
```

**Problems**:
1. **Missing `functions` configuration** - Vercel doesn't know to treat `index.py` as a serverless function
2. **No runtime specified** - Vercel doesn't know this is a Python application
3. **Incorrect for local development** - This only works on Vercel, not locally

**What This Should Be** (for Vercel deployment):
```json
{
    "functions": {
        "api/index.py": {
            "runtime": "python3.9"
        }
    },
    "rewrites": [
        {
            "source": "/api/:path*",
            "destination": "/api/index.py"
        }
    ]
}
```

---

### **Issue #3: Missing Local Development Setup**

**Problem**: No mechanism to run the Python backend locally alongside Next.js.

**What's Missing**:
- No `uvicorn` or FastAPI dev server running
- No process manager (like `concurrently` or `pm2`) to run both servers
- No proxy configuration in `next.config.ts` to forward `/api` requests to Python backend

**Required Setup for Local Development**:

1. **Run Python backend separately**:
   ```bash
   cd app/api
   uvicorn index:app --reload --port 8000
   ```

2. **Configure Next.js to proxy API requests** (`next.config.ts`):
   ```typescript
   const nextConfig: NextConfig = {
     reactCompiler: true,
     async rewrites() {
       return [
         {
           source: '/api/:path*',
           destination: 'http://localhost:8000/api/:path*',
         },
       ];
     },
   };
   ```

3. **Update package.json scripts**:
   ```json
   {
     "scripts": {
       "dev": "next dev",
       "dev:api": "cd api && uvicorn index:app --reload --port 8000",
       "dev:all": "concurrently \"npm run dev\" \"npm run dev:api\""
     }
   }
   ```

---

## 🔍 Route Mapping Analysis

### **Frontend Routes** (Next.js App Router)
| Route | File | Status |
|-------|------|--------|
| `/` | `src/app/page.tsx` | ✅ Working |
| `/dash` | `src/app/dash/page.tsx` | ✅ Working (but API calls fail) |
| `/integrations` | `src/app/integrations/page.tsx` | ✅ Working (but API calls fail) |

### **API Routes** (Python FastAPI - NOT RUNNING)
| Route | Handler | Purpose | Status |
|-------|---------|---------|--------|
| `GET /api/` | `index.py:read_root()` | Health check | ❌ 404 |
| `GET /api/auth/instagram/login` | `index.py:auth_instagram_login()` | Instagram OAuth | ❌ 404 |
| `GET /api/auth/instagram/callback` | `index.py:auth_instagram_callback()` | Instagram callback | ❌ 404 |
| `GET /api/auth/pinterest/login` | `index.py:auth_pinterest_login()` | Pinterest OAuth | ❌ 404 |
| `GET /api/auth/pinterest/callback` | `index.py:auth_pinterest_callback()` | Pinterest callback | ❌ 404 |
| `GET /api/auth/meta/login` | `index.py:auth_meta_login()` | Meta OAuth | ❌ 404 |
| `GET /api/auth/meta/callback` | `index.py:auth_meta_callback()` | Meta callback | ❌ 404 |
| `GET /api/auth/youtube/login` | `index.py:auth_youtube_login()` | YouTube OAuth | ❌ 404 |
| `GET /api/auth/youtube/callback` | `index.py:auth_youtube_callback()` | YouTube callback | ❌ 404 |
| `GET /api/integrations` | `index.py:list_integrations()` | List all accounts | ❌ 404 |
| `GET /api/integrations/{platform}/{account_id}` | `index.py:get_integration()` | Get specific account | ❌ 404 |
| `POST /api/integrations` | `index.py:add_integration()` | Add account | ❌ 404 |
| `DELETE /api/integrations/{platform}/{account_id}` | `index.py:delete_integration()` | Remove account | ❌ 404 |
| `GET /api/metrics/{platform}/{account_id}` | `index.py:get_metrics_for_platform_account()` | Get metrics | ❌ 404 |
| `POST /api/metrics` | `index.py:add_metric()` | Add metric | ❌ 404 |
| `GET /api/sync/status` | `index.py:get_sync_status()` | Sync status | ❌ 404 |
| `POST /api/sync` | `index.py:trigger_sync()` | Trigger sync | ❌ 404 |

---

## 🔧 Additional Issues Found

### **Issue #4: FastAPI Root Path Configuration**
```python
# Line 44 in index.py
app = FastAPI(lifespan=lifespan, root_path="/api")
```

**Problem**: The `root_path="/api"` means FastAPI expects to be mounted at `/api`, but the routes are defined without the `/api` prefix.

**Impact**: 
- Route definitions like `@app.get("/")` actually map to `/api/`
- Route definitions like `@app.get("/auth/instagram/login")` map to `/api/auth/instagram/login`
- This is correct for Vercel deployment but needs proxy setup for local dev

---

### **Issue #5: Environment Variables Not Configured**

The Python backend requires these environment variables (from `auth.py` and `index.py`):

**Required**:
- `Instagram_app_id`
- `Instagram_app_secret`
- `INSTAGRAM_REDIRECT_URI`
- `Pinterest_app_id`
- `Pinterest_app_secret`
- `PINTEREST_REDIRECT_URI`
- `youtube_client_id`
- `youtube_client_secret`
- `YOUTUBE_REDIRECT_URI`
- `META_REDIRECT_URI`
- `FRONTEND_URL`
- `SYNC_MAX_LIMIT`
- AWS credentials for DynamoDB (implicit in boto3)

**Missing**: No `.env` file found in `/app/api/` or `/app/`

---

### **Issue #6: CORS Configuration**

```python
# Lines 46-53 in index.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue**: `allow_origins=["*"]` with `allow_credentials=True` is not allowed by browsers.

**Fix**: Either:
1. Set specific origins: `allow_origins=["http://localhost:3000"]`
2. Remove `allow_credentials=True`

---

## ✅ Recommended Solutions

### **Solution 1: Local Development (Immediate Fix)**

1. **Create environment file** (`/app/api/.env`):
   ```bash
   # Social Media API Credentials
   Instagram_app_id=your_instagram_app_id
   Instagram_app_secret=your_instagram_app_secret
   INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/auth/instagram/callback
   
   Pinterest_app_id=your_pinterest_app_id
   Pinterest_app_secret=your_pinterest_app_secret
   PINTEREST_REDIRECT_URI=http://localhost:8000/api/auth/pinterest/callback
   
   youtube_client_id=your_youtube_client_id
   youtube_client_secret=your_youtube_client_secret
   YOUTUBE_REDIRECT_URI=http://localhost:8000/api/auth/youtube/callback
   
   META_REDIRECT_URI=http://localhost:8000/api/auth/meta/callback
   
   # Frontend URL
   FRONTEND_URL=http://localhost:3000
   
   # Sync Settings
   SYNC_MAX_LIMIT=3
   
   # AWS DynamoDB (if using local)
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   ```

2. **Install Python dependencies**:
   ```bash
   cd /Users/rmm/CUBE/Social_Insights/app/api
   pip install -r requirements.txt
   ```

3. **Start Python backend**:
   ```bash
   cd /Users/rmm/CUBE/Social_Insights/app/api
   uvicorn index:app --reload --port 8000
   ```

4. **Update Next.js config** (`/app/next.config.ts`):
   ```typescript
   import type { NextConfig } from "next";

   const nextConfig: NextConfig = {
     reactCompiler: true,
     async rewrites() {
       return [
         {
           source: '/api/:path*',
           destination: 'http://localhost:8000/api/:path*',
         },
       ];
     },
   };

   export default nextConfig;
   ```

5. **Update frontend API URL** (already correct):
   ```typescript
   // In dash/page.tsx and integrations/page.tsx
   const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";
   ```

6. **Start Next.js**:
   ```bash
   cd /Users/rmm/CUBE/Social_Insights/app
   npm run dev
   ```

---

### **Solution 2: Production Deployment (Vercel)**

1. **Update `vercel.json`**:
   ```json
   {
     "functions": {
       "api/index.py": {
         "runtime": "python3.9",
         "maxDuration": 30
       }
     },
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "/api/index.py"
       }
     ]
   }
   ```

2. **Add environment variables in Vercel dashboard**:
   - All the variables from the `.env` file above
   - Update redirect URIs to use production domain

3. **Ensure `requirements.txt` is in `/app/api/`** (already present)

---

### **Solution 3: Unified Development Script**

**Install concurrently**:
```bash
cd /Users/rmm/CUBE/Social_Insights/app
npm install --save-dev concurrently
```

**Update `package.json`**:
```json
{
  "scripts": {
    "dev": "next dev",
    "dev:api": "cd api && uvicorn index:app --reload --port 8000",
    "dev:all": "concurrently \"npm run dev\" \"npm run dev:api\" --names \"next,api\" --prefix-colors \"cyan,magenta\"",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

**Usage**:
```bash
npm run dev:all
```

---

## 📊 Testing Checklist

After implementing fixes, test these endpoints:

### **Health Check**
```bash
curl http://localhost:3000/api/
# Expected: {"status": "ok", "service": "Social Insights Backend"}
```

### **Integrations List**
```bash
curl http://localhost:3000/api/integrations
# Expected: [] or array of integrations
```

### **Sync Status**
```bash
curl http://localhost:3000/api/sync/status
# Expected: {"sync_count": 0, "sync_limit_stat": false, ...}
```

### **OAuth Flow**
```bash
# Visit in browser:
http://localhost:3000/api/auth/instagram/login
# Should redirect to Facebook OAuth
```

---

## 🎯 Root Cause Summary

| Issue | Root Cause | Impact | Priority |
|-------|------------|--------|----------|
| 404 on all API routes | Python backend not running | Complete API failure | 🔴 Critical |
| Missing proxy config | No Next.js → FastAPI forwarding | Local dev broken | 🔴 Critical |
| Missing .env file | No API credentials configured | OAuth won't work | 🔴 Critical |
| Incorrect vercel.json | Missing functions config | Vercel deploy will fail | 🟡 High |
| CORS misconfiguration | Invalid allow_origins + credentials | Browser blocks requests | 🟡 High |

---

## 📝 Next Steps

1. ✅ **Immediate**: Start Python backend (`uvicorn index:app --reload --port 8000`)
2. ✅ **Immediate**: Add Next.js proxy config to `next.config.ts`
3. ✅ **Immediate**: Create `.env` file with API credentials
4. ⚠️ **Soon**: Fix CORS configuration in `index.py`
5. ⚠️ **Soon**: Update `vercel.json` for production deployment
6. ⚠️ **Soon**: Add unified dev script with `concurrently`

---

## 🔗 Related Files

- **Frontend Routes**: `/app/src/app/*/page.tsx`
- **API Backend**: `/app/api/index.py`
- **Auth Handlers**: `/app/api/auth.py`
- **Routing Config**: `/app/vercel.json`
- **Next.js Config**: `/app/next.config.ts`
- **Database Client**: `/app/api/Db/database.py`
- **API Clients**: `/app/api/Sources/*.py`

---

**Generated**: 2026-02-12T20:18:27+05:30
