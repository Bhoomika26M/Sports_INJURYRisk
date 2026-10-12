"""Health endpoints.

/health        liveness  — the process is up. Static; touches nothing.
/health/ready  readiness — the process can actually reach Postgres.

Liveness alone cannot catch a container pointed at the wrong DATABASE_URL (it would answer
{"status": "healthy"} while every real request failed), so deploy checks should use /health/ready.
"""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CHECK_TIMEOUT_SECONDS = 3.0


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unreachable"]


async def _check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), CHECK_TIMEOUT_SECONDS)
        return True
    except (SQLAlchemyError, OSError, asyncio.TimeoutError) as e:
        logger.warning("readiness: database unreachable (%s)", type(e).__name__)  # never log the URL
        return False


@router.get("/health/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}})
async def readiness_check():
    db_ok = await _check_database()
    body = ReadinessResponse(status="ready" if db_ok else "not_ready", database="ok" if db_ok else "unreachable")
    return JSONResponse(status_code=200 if db_ok else 503, content=body.model_dump())
