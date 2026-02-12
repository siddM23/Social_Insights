# Social Insights Dashboard

This project is a dashboard for tracking social media metrics (Instagram).

## Project Structure

- `frontend/`: Next.js application
- `backend/`: FastAPI application with DynamoDB integration

## Prerequisites

- Node.js & npm
- Python 3.9+
- AWS Credentials (for DynamoDB access)

## Setup & Run

### 1. Backend

 Navigate to the backend directory:
 ```bash
 cd backend
 ```

 Create a virtual environment and install dependencies:
 ```bash
 python -m venv venv
 source venv/bin/activate  # On Windows: venv\Scripts\activate
 pip install -r requirements.txt
 ```

 Run the server:
 ```bash
 uvicorn main:app --reload
 ```
 The backend runs on `http://localhost:8000`.

 ### 2. Frontend

 Navigate to the frontend directory:
 ```bash
 cd frontend
 ```

 Install dependencies:
 ```bash
 npm install
 ```

 Run the development server:
 ```bash
 npm run dev
 ```
 The dashboard is available at `http://localhost:3000`.

 ## Environment Variables

 Ensure `.env` files are configured.
 - Backend: `backend/.env` (AWS Credentials)
 - Frontend: `frontend/.env.local` (NEXT_PUBLIC_API_URL if not localhost)

 ## Features

 - **Integrations Page**: Connect Instagram accounts (simulated/manual entry).
 - **Dashboard Page**: View metrics like Followers, Views, Interactions, etc.
