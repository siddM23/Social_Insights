# Social Insights Dashboard

This is a dashboard for tracking social media metrics (Instagram, Pinterest, Meta, YouTube).

## Project Structure (Monorepo)

- `web_app/src/`: Next.js Frontend source code
- `web_app/api/`: Python Backend (FastAPI) source code
- `web_app/public/`: Static assets
- `vercel.json`: Vercel routing configuration
- `Dockerfile.backend` / `Dockerfile.frontend`: Docker configuration

## Prerequisites

- Node.js & npm
- Python 3.9+
- AWS Credentials (for DynamoDB access)

## Setup & Run Locally

### 1. Install Dependencies

**Frontend:**
```bash
cd web_app
npm install
```

**Backend:**
```bash
cd web_app/api
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
```

### 2. Run Development Servers

You need to run both frontend and backend servers.

**Backend (Port 8000):**
```bash
# Recommended way
python start.py
```
*Note: `start.py` is located in `web_app/api/`*

**Frontend (Port 3000):**
```bash
# In a new terminal
cd web_app
npm run dev
```
The dashboard is available at `http://localhost:3000`.

## Docker Development

You can also run everything using Docker Compose:
```bash
docker-compose up --build
```

## Deployment on Vercel

This project is configured for a unified Vercel deployment.

1.  **Push to GitHub**.
2.  **Import Project in Vercel**.
3.  **Vercel Settings**:
    - **Framework Preset**: Next.js.
    - **Root Directory**: `./`.
4.  **Environment Variables**: Add all keys found in `.env.example` to Vercel.

Vercel will automatically route `/api/*` to the Python backend in `web_app/api/index.py`.
