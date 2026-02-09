import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.src.api.routes import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run migrations on startup."""
    if os.getenv("RUN_MIGRATIONS", "true").lower() == "true":
        from services.api.src.api.db.migrate import run_migrations
        run_migrations()

    yield


app = FastAPI(title="Agent Incident Triage API", lifespan=lifespan)

# CORS for frontend
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "https://localhost:3000",
]

if os.getenv("CORS_ORIGIN"):
    cors_origins.append(os.getenv("CORS_ORIGIN"))

cors_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"(https://.*\.vercel\.app|http://192\.168\.\d+\.\d+:\d+)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "agent-incident-triage-api", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
