"""Central router aggregating all API v1 narrative endpoints."""

from fastapi import APIRouter

from spindle.api.v1.documents import router as documents_router
from spindle.api.v1.entities import router as entities_router
from spindle.api.v1.generate import router as generate_router
from spindle.api.v1.story import router as story_router
from spindle.api.v1.suggestions import router as suggestions_router
from spindle.api.v1.vault import router as vault_router

api_v1_router = APIRouter()

api_v1_router.include_router(vault_router)
api_v1_router.include_router(entities_router)
api_v1_router.include_router(story_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(generate_router)
api_v1_router.include_router(suggestions_router)
