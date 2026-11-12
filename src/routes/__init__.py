from fastapi import APIRouter

from routes.accounts import router as accounts_router

api_v1_router = APIRouter()

# api_v1_router includes baby-routers
api_v1_router.include_router(accounts_router)
