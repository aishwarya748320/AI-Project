from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.flights import router as flights_router
from app.api.hotels import router as hotels_router
from app.api.recommendations import (
    router as recommendations_router,
    search_router,
)
from app.api.booking import router as booking_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(flights_router)
api_router.include_router(hotels_router)
api_router.include_router(recommendations_router)
api_router.include_router(search_router)
api_router.include_router(booking_router)
