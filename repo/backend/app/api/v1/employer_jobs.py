from fastapi import APIRouter

from app.api.v1.employer_jobs_applications import router as employer_jobs_applications_router
from app.api.v1.employer_jobs_milestones import router as employer_jobs_milestones_router
from app.api.v1.employer_jobs_posts import router as employer_jobs_posts_router

router = APIRouter(tags=["Employer Jobs"])
router.include_router(employer_jobs_posts_router)
router.include_router(employer_jobs_applications_router)
router.include_router(employer_jobs_milestones_router)
