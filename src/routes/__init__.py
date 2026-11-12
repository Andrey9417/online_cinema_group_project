from fastapi import APIRouter

from routes.movies import router as movies_router
from routes.reference import router as reference_router

api_v1_router = APIRouter()

api_v1_router.include_router(movies_router)
api_v1_router.include_router(reference_router)

# api_v1_router includes baby-routers
