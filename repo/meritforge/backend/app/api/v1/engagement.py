from fastapi import APIRouter

from app.api.v1.engagement_annotations import router as engagement_annotations_router
from app.api.v1.engagement_milestones import router as engagement_milestones_router
from app.api.v1.engagement_telemetry import router as engagement_telemetry_router

router = APIRouter(tags=["Engagement"])
router.include_router(engagement_telemetry_router)
router.include_router(engagement_milestones_router)
router.include_router(engagement_annotations_router)
