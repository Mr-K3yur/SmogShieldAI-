from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.aqi import router as aqi_router
from app.api.v1.stations import router as stations_router
from app.api.v1.planner import router as planner_router
from app.api.v1.advisor import router as advisor_router
from app.api.v1.transport import router as transport_router
from app.api.v1.impact import router as impact_router
from app.api.v1.assistant import router as assistant_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(aqi_router)
api_v1_router.include_router(stations_router)
api_v1_router.include_router(planner_router)
api_v1_router.include_router(advisor_router)
api_v1_router.include_router(transport_router)
api_v1_router.include_router(impact_router)
api_v1_router.include_router(assistant_router)

__all__ = ["api_v1_router"]
