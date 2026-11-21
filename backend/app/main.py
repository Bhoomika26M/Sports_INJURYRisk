from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.routes import auth, users, athletes, datasets, videos, risk, invitations
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sports Injury Risk Detection API",
    description="API for sports injury risk detection from video analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
def on_startup():
    from app.db.database import SessionLocal
    from app.services.seed_service import ensure_demo_personas
    db = SessionLocal()
    try:
        ensure_demo_personas(db)
    finally:
        db.close()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Log the full error server-side
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)
            # Return generic error to client
            raise HTTPException(
                status_code=500,
                detail="An internal error occurred. Please try again later."
            )


from starlette.types import ASGIApp, Receive, Scope, Send

class StripGzipForMediaMiddleware:
    """Pure ASGI middleware that strips Accept-Encoding for video endpoints
    BEFORE GZipMiddleware processes the request, ensuring video range streams are NEVER gzipped.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.endswith(("/video", "/annotated-video")) or any(k.lower() == b"range" for k, v in scope.get("headers", [])):
                scope["headers"] = [
                    (k, v) for k, v in scope.get("headers", [])
                    if k.lower() != b"accept-encoding"
                ]
        await self.app(scope, receive, send)


# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add GZip compression for API JSON/text
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Strip GZip on video endpoints (runs BEFORE GZipMiddleware in the outer onion layer)
app.add_middleware(StripGzipForMediaMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(athletes.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1/videos")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(invitations.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Sports Injury Risk Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "Milestone 1 - Foundation Complete"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
