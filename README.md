# Social Insights Dashboard

This project is a dashboard for tracking social media metrics (Instagram, Pinterest, Meta, YouTube).

## Project Structure (Vercel Monorepo)

- `src/`: Next.js Frontend source code
- `api/`: Python Backend (FastAPI) source code
- `public/`: Static assets
- `vercel.json`: Vercel routing configuration

## Prerequisites

- Node.js & npm
- Python 3.9+
- AWS Credentials (for DynamoDB access)

## Setup & Run Locally

### 1. Install Dependencies

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 2. Run Development Servers

You need to run both frontend and backend servers.

**Backend (Port 8000):**
```bash
cd api
uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

**Frontend (Port 3000):**
```bash
# In a new terminal at root
npm run dev
```
The dashboard is available at `http://localhost:3000`.

**Note:** Ensure your frontend `.env.local` points API requests to `http://localhost:8000` for local development if you haven't configured a proxy.
For production (Vercel), API requests should go to `/api/...`.

## Deployment on Vercel

This project is configured for a unified Vercel deployment.

1.  **Push to GitHub/GitLab/Bitbucket**.
2.  **Import Project in Vercel**.
3.  **Vercel Settings**:
    - **Framework Preset**: Next.js (Automatic).
    - **Root Directory**: `./` (default).
    - **Environment Variables**: Add all backend and frontend env vars here (e.g., `AWS_ACCESS_KEY_ID`, `meta_gapi`, `NEXT_PUBLIC_API_URL`).
4.  **Deploy**.

Vercel will automatically detect:
- Next.js in the root.
- Python Serverless Functions in `api/`.

Routes starting with `/api/` will be directed to the backend.
All other routes will be handled by the frontend.
