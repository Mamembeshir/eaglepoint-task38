from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.bookmarks import router as bookmarks_router
from app.api.v1.content_submission import router as content_submission_router
from app.api.v1.engagement import router as engagement_router
from app.api.v1.employer_jobs import router as employer_jobs_router
from app.api.v1.integration import router as integration_router
from app.api.v1.operations import router as operations_router
from app.api.v1.publishing import router as publishing_router
from app.api.v1.review_workflow import router as review_workflow_router
from app.api.v1.topic_subscriptions import router as topic_subscriptions_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.user_management import router as user_management_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(audit_logs_router)
api_router.include_router(bookmarks_router)
api_router.include_router(user_management_router)
api_router.include_router(content_submission_router)
api_router.include_router(review_workflow_router)
api_router.include_router(publishing_router)
api_router.include_router(engagement_router)
api_router.include_router(integration_router)
api_router.include_router(topic_subscriptions_router)
api_router.include_router(employer_jobs_router)
api_router.include_router(operations_router)
api_router.include_router(webhooks_router)
