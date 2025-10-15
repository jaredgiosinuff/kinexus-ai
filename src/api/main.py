"""
FastAPI main application for Kinexus AI.

This is the central API server that handles:
- Authentication and authorization
- Review queue management
- Document operations
- WebSocket connections for real-time updates
- Integration with external systems
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routers import (
    admin,
    auth,
    documentation_plans,
    documents,
    github_actions,
    reviews,
    webhooks,
    websocket,
)
from core.config import settings
from core.services.metrics_service import metrics_service
from database.connection import close_database, db_manager, init_database

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
metrics_logger = logging.getLogger("kinexus.metrics")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Kinexus AI API server...")

    try:
        # Initialize database
        init_database()
        logger.info("Database initialized")

        # Verify database health
        if not db_manager.health_check():
            raise RuntimeError("Database health check failed")

        if settings.ENABLE_METRICS:
            try:
                await metrics_service.start_metrics_server(settings.METRICS_PORT)
            except Exception as metrics_exc:
                logger.warning("Metrics server failed to start: %s", metrics_exc)

        logger.info("Kinexus AI API server started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Kinexus AI API server...")
        close_database()
        logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Kinexus AI API",
    description="Human-supervised AI documentation management system",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# Add security middleware
if settings.ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_request_metrics(request: Request, call_next):
    """Capture basic request metrics for Prometheus."""
    if not settings.ENABLE_METRICS or request.url.path == "/metrics":
        return await call_next(request)

    start_time = perf_counter()
    status_code = 500
    error_logged = False

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except HTTPException as exc:
        status_code = exc.status_code
        severity = "error" if status_code < 500 else "critical"
        try:
            await metrics_service.record_error(
                "api", exc.__class__.__name__, severity=severity
            )
            error_logged = True
        except Exception:
            metrics_logger.exception("Failed to record HTTPException metrics")
        raise
    except Exception as exc:
        status_code = 500
        try:
            await metrics_service.record_error(
                "api", exc.__class__.__name__, severity="critical"
            )
            error_logged = True
        except Exception:
            metrics_logger.exception("Failed to record exception metrics")
        raise
    finally:
        duration = perf_counter() - start_time
        endpoint = request.url.path
        try:
            await metrics_service.record_request(
                request.method, endpoint, status_code, duration
            )
            if status_code >= 500 and not error_logged:
                await metrics_service.record_error(
                    "api", f"status_{status_code}", severity="error"
                )
        except Exception:
            metrics_logger.exception("Failed to record request metrics")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    try:
        # Check database health
        db_healthy = db_manager.health_check()

        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": app.version,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Kinexus AI API",
        "version": app.version,
        "description": "Human-supervised AI documentation management system",
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else None,
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics for push-based scrapers or restricted environments."""
    if not settings.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    try:
        metrics_payload = metrics_service.get_metrics()
        return Response(
            content=metrics_payload,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as exc:
        logger.error("Failed to collect metrics: %s", exc)
        raise HTTPException(status_code=503, detail="Metrics unavailable")


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(
    documentation_plans.router,
    prefix="/api/documentation-plans",
    tags=["Documentation Plans"],
)
app.include_router(github_actions.router, tags=["GitHub Actions"])


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"],
        log_level=settings.LOG_LEVEL.lower(),
    )
