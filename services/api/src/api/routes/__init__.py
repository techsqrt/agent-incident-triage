"""Router aggregation."""

from fastapi import APIRouter

from services.api.src.api.routes.triage import router as triage_router

api_router = APIRouter()
api_router.include_router(triage_router, prefix="/api/triage", tags=["triage"])
