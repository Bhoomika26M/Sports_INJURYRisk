"""Health endpoints.

/health        liveness  — the process is up. Static; touches nothing.
/health/ready  readiness — the process can actually reach Postgres AND Redis.

Liveness alone cannot catch a container pointed at the wrong DATABASE_URL (it would answer
{"status": "healthy"} while every real request failed), so deploy checks should use /health/ready.
"""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import from_url as redis_from_url
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CHECK_TIMEOUT_SECONDS = 3.0


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unreachable"]
    redis: Literal["ok", "unreachable"]


async def _check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), CHECK_TIMEOUT_SECONDS)
        return True
    except (SQLAlchemyError, OSError, asyncio.TimeoutError) as e:
        logger.warning("readiness: database unreachable (%s)", type(e).__name__)  # never log the URL
        return False


async def _check_redis() -> bool:
    client = redis_from_url(settings.redis_url, socket_connect_timeout=CHECK_TIMEOUT_SECONDS)
    try:
        await asyncio.wait_for(client.ping(), CHECK_TIMEOUT_SECONDS)
        return True
    except (RedisError, OSError, asyncio.TimeoutError) as e:
        logger.warning("readiness: redis unreachable (%s)", type(e).__name__)
        return False
    finally:
        await (getattr(client, "aclose", None) or client.close)()   # aclose() needs redis>=5.0.1


@router.get("/health/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}})
async def readiness_check():
    db_ok, redis_ok = await _check_database(), await _check_redis()
    body = ReadinessResponse(
        status="ready" if (db_ok and redis_ok) else "not_ready",
        database="ok" if db_ok else "unreachable",
        redis="ok" if redis_ok else "unreachable",
    )
    return JSONResponse(status_code=200 if body.status == "ready" else 503, content=body.model_dump())
