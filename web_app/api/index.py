import os
import datetime
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import PROJECT_NAME, VERSION, logger
from repositories.users_repository import UsersRepository
from repositories.metrics_repository import MetricsRepository
from services.sync_service import SyncService

from routes import auth, integrations, metrics, sync

# Initialize Repositories
users_repo = UsersRepository()
metrics_repo = MetricsRepository()

# Initialize Services
sync_service = SyncService(metrics_repo, users_repo)

# Inject dependencies into routers (Simple injection)
auth.users_repo = users_repo
auth.sync_service = sync_service

integrations.users_repo = users_repo
integrations.sync_service = sync_service

metrics.users_repo = users_repo
metrics.metrics_repo = metrics_repo

sync.users_repo = users_repo
sync.sync_service = sync_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{PROJECT_NAME} starting...")
    yield
    logger.info(f"{PROJECT_NAME} shutting down...")

app = FastAPI(title=PROJECT_NAME, version=VERSION, lifespan=lifespan)

# Vercel-specific: Handle the /api prefix
if os.getenv("VERCEL"):
    app.root_path = "/api"

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
@app.get("/")
def read_root():
    return {"status": "ok", "service": PROJECT_NAME, "version": VERSION}

@app.get("/health")
def health_check():
    return {"status": "alive", "timestamp": datetime.datetime.utcnow().isoformat()}

# Include Routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(integrations.router, tags=["Integrations"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(sync.router, tags=["Sync"])
