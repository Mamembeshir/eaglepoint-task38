from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import logging
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.database import engine
from app.core.config import settings
from app.core.idempotency import IdempotencyMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.rate_limit import UserRateLimitMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running database migrations...")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE IF EXISTS alembic_version "
                    "ALTER COLUMN version_num TYPE VARCHAR(128)"
                )
            )
    except Exception as e:
        logger.warning(f"Alembic version table check warning: {e}")

    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.warning(f"Migration warning: {e}")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title="MeritForge API",
    description="Career Media & Hiring Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    UserRateLimitMiddleware,
    redis_url=settings.redis_url,
    limit_per_minute=settings.user_rate_limit_per_minute,
)

app.add_middleware(
    IdempotencyMiddleware,
    redis_url=settings.redis_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "MeritForge API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
