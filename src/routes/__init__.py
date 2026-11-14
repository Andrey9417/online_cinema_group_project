from fastapi import APIRouter

from routes.movies import router as movies_router
from routes.reference import router as reference_router
from routes.accounts import router as accounts_router
from routes.payments import router as payments_router
from routes.comments import router as comments_router

api_v1_router = APIRouter()

api_v1_router.include_router(movies_router)
api_v1_router.include_router(reference_router)
api_v1_router.include_router(comments_router)

# api_v1_router includes baby-routers
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(payments_router)
