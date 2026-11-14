from fastapi import APIRouter

from routes.movies import router as movies_router
from routes.reference import router as reference_router
from routes.accounts import router as accounts_router
from routes.carts import router as carts_router
from routes.payments import router as payments_router
from routes.orders import router as orders_router
from routes.comments import router as comments_router

api_v1_router = APIRouter()

api_v1_router.include_router(movies_router)
api_v1_router.include_router(reference_router)
api_v1_router.include_router(comments_router)

# api_v1_router includes baby-routers
api_v1_router.include_router(accounts_router, prefix="/accounts", tags=["accounts", "profiles"])
api_v1_router.include_router(carts_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(orders_router)
