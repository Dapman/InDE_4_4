"""
InDE MVP v3.8 - FastAPI Application Entry Point
Innovation Development Environment - "Commercial Launch Infrastructure"

This is the main entry point for the InDE v3.8 API server.

v3.8 Features (NEW):
- License Validation Service: Startup and periodic license checks
- First-Run Setup Wizard: Guided deployment configuration
- Read-Only Mode: Grace period enforcement for expired licenses
- BYOK API Keys: Bring-Your-Own-Key Anthropic API configuration

v3.4 Features (inherited):
- Org-Level Portfolio Dashboard: 7-panel enterprise intelligence view
- Coaching Convergence Protocol: Signal detection, criteria evaluation, outcome capture
- IDTFS: Six-pillar expertise assessment for intelligent team formation
- Advanced RBAC: Custom role definitions, policy-based access control
- Methodology Archetypes: Design Thinking + Stage-Gate with coaching configs
- SOC 2 Audit Pipeline: Immutable audit events via Redis Streams

Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
import logging
import os

from core.config import VERSION, VERSION_NAME, INDE_ADMIN_EMAIL
from core.database import Database
from api import auth, pursuits, coaching, artifacts, analytics, reports
from api import timeline, health, ikf, crisis, maturity, system
# v3.12: Account management router
from api import account
# v3.3: Team innovation routers
from api import organizations, teams
# v3.4: Enterprise intelligence & governance routers
from api import convergence, governance, audit, discovery, formation, portfolio_dashboard, odicm
# v3.15: User discovery (guided first-use experience) and client error logging
from api import user_discovery, client_errors
# v4.3: Depth dimension API
from api import depth

# v3.2: Import event bus components
from events.redis_publisher import publisher
from events.consumer_registry import create_app_consumers, register_fallback_handlers
from events.dispatcher import get_dispatcher

# v3.14: Diagnostics error buffer
from modules.diagnostics.error_buffer import error_buffer

# v3.8: Import license middleware
from middleware.license import LicenseMiddleware, validate_license_on_startup

# v3.15: Import rate limiting middleware
from middleware.rate_limiting import RateLimitMiddleware

# v3.11: Import database index management and migration
from database.indexes import create_all_indexes_sync
from migrations.v311_milestone_permissions import run as run_v311_migration
# v3.12: Account trust migration
from migrations.v312_account_trust import run as run_v312_migration
# v3.13: Experience polish migration
from migrations.v313_experience_polish import run_sync as run_v313_migration
# v3.14: Operational readiness migration (onboarding metrics)
from migrations.v314_operational import run_sync as run_v314_migration

# Configure logging
log_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("inde")

# Database instance (initialized on startup)
db: Database = None

# v3.2: Track consumer tasks for cleanup
consumer_tasks = []

# v3.12: Track background tasks
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    global db, consumer_tasks

    # Startup
    logger.info(f"Starting InDE v{VERSION} - {VERSION_NAME}")

    # Initialize database
    db = Database()
    app.state.db = db

    # v3.11: Create/verify MongoDB indexes for performance
    try:
        create_all_indexes_sync(db)
        logger.info("MongoDB indexes created/verified")
    except Exception as e:
        logger.warning(f"Index creation skipped: {e}")

    # v3.11: Run milestone permissions migration (backfill created_by_user_id)
    try:
        migration_result = run_v311_migration(db)
        if migration_result.get("migrated", 0) > 0:
            logger.info(f"v3.11 migration completed: {migration_result}")
    except Exception as e:
        logger.warning(f"v3.11 migration skipped: {e}")

    # v3.12: Run account trust migration (add status and deletion fields)
    try:
        migration_result = run_v312_migration(db)
        if migration_result.get("migrated_users", 0) > 0:
            logger.info(f"v3.12 migration completed: {migration_result}")
    except Exception as e:
        logger.warning(f"v3.12 migration skipped: {e}")

    # v3.13: Run experience polish migration (add archive fields to pursuits)
    try:
        migration_result = run_v313_migration(db)
        if migration_result.get("pursuits_updated", 0) > 0:
            logger.info(f"v3.13 migration completed: {migration_result}")
    except Exception as e:
        logger.warning(f"v3.13 migration skipped: {e}")

    # v3.14: Run operational readiness migration (onboarding metrics indexes)
    try:
        migration_result = run_v314_migration(db)
        if migration_result.get("indexes_created", 0) > 0:
            logger.info(f"v3.14 migration completed: {migration_result}")
    except Exception as e:
        logger.warning(f"v3.14 migration skipped: {e}")

    # v3.14: Auto-assign admin role from INDE_ADMIN_EMAIL
    if INDE_ADMIN_EMAIL:
        try:
            result = db.db.users.update_one(
                {"email": INDE_ADMIN_EMAIL.lower()},
                {"$set": {"role": "admin"}}
            )
            if result.modified_count > 0:
                logger.info(f"Admin role assigned to {INDE_ADMIN_EMAIL}")
            elif result.matched_count > 0:
                logger.debug(f"Admin role already set for {INDE_ADMIN_EMAIL}")
            # If no match, user hasn't registered yet - will be assigned on registration
        except Exception as e:
            logger.warning(f"Admin role assignment skipped: {e}")

    # v3.2: Connect Redis publisher
    try:
        await publisher.connect(db)
        logger.info("Redis publisher connected")
    except Exception as e:
        logger.warning(f"Redis publisher failed to connect: {e}")
        logger.info("Running in fallback mode (in-memory events)")

    # v3.2: Start Redis consumers as background tasks
    try:
        consumers = create_app_consumers(db)
        for consumer in consumers:
            await consumer.connect(db=db)
            task = asyncio.create_task(consumer.start())
            consumer_tasks.append((consumer, task))
        logger.info(f"Started {len(consumers)} event consumer groups")
    except Exception as e:
        logger.warning(f"Failed to start Redis consumers: {e}")
        logger.info("Events will use fallback dispatch only")

    # v3.2: Register fallback handlers for graceful degradation
    dispatcher = get_dispatcher(db)
    register_fallback_handlers(dispatcher, db)

    # v3.8: Validate license on startup
    try:
        license_status = await validate_license_on_startup(db)
        if license_status.get("setup_required"):
            logger.info("First-run setup required - setup wizard will be shown")
        elif license_status.get("valid"):
            logger.info(f"License validated: {license_status.get('tier', 'unknown')} tier")
        elif license_status.get("read_only"):
            logger.warning("Operating in read-only mode (grace period expired)")
        else:
            logger.warning(f"License status: {license_status}")
    except Exception as e:
        logger.warning(f"License validation skipped: {e}")

    # v3.12: Start background deletion job
    async def deletion_job_loop():
        """Hourly background loop for scheduled account deletions."""
        from modules.account.deletion import AccountDeletionService
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                deletion_service = AccountDeletionService(db)
                result = await deletion_service.run_scheduled_deletions()
                if result.get("processed", 0) > 0:
                    logger.info(f"Deletion job completed: {result}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Deletion job loop error: {e}")

    deletion_task = asyncio.create_task(deletion_job_loop())
    background_tasks.append(deletion_task)
    logger.info("Account deletion background job started")

    # v4.2: Start re-engagement scheduler
    async def reengagement_job_loop():
        """6-hour background loop for async re-engagement."""
        from modules.reengagement import ReengagementScheduler, ReengagementGenerator
        from modules.reengagement.reengagement_delivery import ReengagementDeliveryService
        while True:
            try:
                await asyncio.sleep(6 * 3600)  # 6 hours
                generator = ReengagementGenerator()
                delivery = ReengagementDeliveryService()
                scheduler = ReengagementScheduler(db, delivery, generator)
                result = scheduler.run_check()
                if result.get("messages_sent", 0) > 0:
                    logger.info(f"Re-engagement job completed: {result}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Re-engagement job loop error: {e}")

    reengagement_task = asyncio.create_task(reengagement_job_loop())
    background_tasks.append(reengagement_task)
    logger.info("Re-engagement background job started (6h interval)")

    logger.info("InDE API ready to accept requests")

    yield

    # Shutdown
    logger.info("Shutting down InDE API...")

    # v3.12: Stop background tasks
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Background tasks stopped")

    # v3.2: Stop consumers gracefully
    for consumer, task in consumer_tasks:
        try:
            await consumer.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")

    logger.info("InDE API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="InDE API",
    description="Innovation Development Environment - API Server",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v3.15: Rate limiting middleware (runs before auth)
app.add_middleware(RateLimitMiddleware)

# v3.8: License validation middleware
# Only add if not in disabled mode (for development)
if os.getenv("INDE_LICENSE_MODE", "simulation").lower() != "disabled":
    app.add_middleware(LicenseMiddleware)


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    v3.15: Enhanced with user-friendly error messages.
    """
    logger.error(f"Unhandled error: {exc}", exc_info=True)

    # v3.14: Record error in diagnostics buffer
    error_buffer.record(
        level="ERROR",
        module="app",
        message=str(exc)[:300],
        request_path=str(request.url.path),
        exception_type=type(exc).__name__
    )

    # v3.15: Provide user-friendly error messages
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()

    if "timeout" in exc_str or "timed out" in exc_str:
        detail = "The request took too long. Please try again."
    elif "connection" in exc_str or "connect" in exc_str:
        detail = "Unable to connect to a required service. Please try again in a moment."
    elif "database" in exc_str or "mongo" in exc_str:
        detail = "There was a database issue. Please try again."
    elif "validation" in exc_type.lower() or "value" in exc_type.lower():
        detail = "Invalid data provided. Please check your input and try again."
    else:
        detail = "Something unexpected happened. Please try again."

    return JSONResponse(
        status_code=500,
        content={"detail": detail}
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - serve frontend or API info."""
    # Serve frontend if available
    index_path = react_build_path / "index.html"
    if react_build_path.is_dir() and index_path.is_file():
        return FileResponse(str(index_path))
    # Otherwise return API info
    return {
        "name": "InDE API",
        "version": VERSION,
        "version_name": VERSION_NAME,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Health check endpoint (for Docker health checks)
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    # v3.2: Include Redis status
    redis_status = await publisher.health_check()
    return {
        "status": "healthy",
        "version": VERSION,
        "redis": redis_status
    }


# Register API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pursuits.router, prefix="/api/pursuits", tags=["Pursuits"])
app.include_router(coaching.router, prefix="/api/coaching", tags=["Coaching"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["Artifacts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline"])
app.include_router(health.router, prefix="/api/health", tags=["Health Monitor"])
app.include_router(ikf.router, prefix="/api/ikf", tags=["IKF"])
app.include_router(crisis.router, prefix="/api/crisis", tags=["Crisis Mode"])
app.include_router(maturity.router, prefix="/api/maturity", tags=["Maturity"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
# v3.3: Team innovation routes
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
# v3.4: Enterprise intelligence routes
app.include_router(convergence.router, prefix="/api", tags=["Convergence"])
app.include_router(governance.router, prefix="/api", tags=["Governance"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(discovery.router, prefix="/api", tags=["Discovery"])
app.include_router(formation.router, prefix="/api", tags=["Formation"])
app.include_router(portfolio_dashboard.router, prefix="/api", tags=["Portfolio Dashboard"])
app.include_router(odicm.router, prefix="/api", tags=["ODICM"])
# v3.12: Account management routes
app.include_router(account.router, prefix="/api/account", tags=["Account"])
# v3.15: User discovery (Getting Started) and client error logging
app.include_router(user_discovery.router, tags=["User Discovery"])
app.include_router(client_errors.router, tags=["Client Errors"])
# v4.3: Depth dimension API
app.include_router(depth.router, prefix="/api/v1", tags=["Depth"])


# WebSocket for real-time coaching
@app.websocket("/ws/coaching/{pursuit_id}")
async def coaching_websocket(websocket: WebSocket, pursuit_id: str):
    """
    WebSocket endpoint for real-time coaching sessions.

    Protocol:
    - Client sends: {"type": "message", "content": "user message", "mode": "coaching"}
    - Server sends: {"type": "chunk", "content": "partial response"} (streaming)
    - Server sends: {"type": "complete"} (end of response)
    - Server may send: {"type": "intervention", ...}
    """
    from core.llm_interface import LLMInterface
    from scaffolding.engine import ScaffoldingEngine
    from auth.jwt_handler import decode_token

    await websocket.accept()

    # Get token from query params
    token = websocket.query_params.get("token")
    user_id = None

    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")

    # Get database and engine
    db = app.state.db
    llm = LLMInterface()
    engine = ScaffoldingEngine(db, llm)
    if user_id:
        engine.set_user_id(user_id)

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("content", "")
            mode = data.get("mode", "coaching")

            if not message.strip():
                continue

            try:
                # Process through scaffolding engine
                result = engine.process_message(
                    message=message,
                    current_pursuit_id=pursuit_id,
                    user_id=user_id
                )

                response = result.get("response", "I'm here to help. Tell me more.")

                # Send response (matches frontend expected types)
                await websocket.send_json({
                    "type": "coach_response",
                    "content": response
                })

                # Send completion signal
                await websocket.send_json({
                    "type": "coach_response_complete",
                    "pursuit_id": pursuit_id,
                    "health_zone": result.get("health_zone"),
                    "intervention": result.get("intervention_made"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

                # Send health update if available
                if result.get("health_zone"):
                    await websocket.send_json({
                        "type": "health_update",
                        "zone": result.get("health_zone"),
                        "score": result.get("health_score", 50)
                    })

            except Exception as e:
                logger.error(f"Coaching engine error: {e}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "type": "coach_response",
                    "content": "I encountered an issue. Could you try rephrasing that?"
                })
                await websocket.send_json({"type": "coach_response_complete"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for pursuit {pursuit_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


# =============================================================================
# STATIC FILE SERVING FOR REACT FRONTEND (Production)
# =============================================================================

# Serve React build in production
react_build_path = Path(__file__).parent / "frontend" / "dist"

if react_build_path.is_dir():
    # Serve static assets (JS, CSS, images)
    assets_path = react_build_path / "assets"
    if assets_path.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="static-assets")

    # Catch-all for client-side routing - serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        """
        Serve React frontend for client-side routing.

        This catch-all route serves index.html for any path that isn't:
        - An API route (/api/*)
        - A WebSocket route (/ws/*)
        - The docs/openapi routes

        React Router handles the rest.
        """
        # Don't intercept API routes, WebSocket routes, or docs
        if full_path.startswith(("api/", "ws/", "docs", "redoc", "openapi.json", "health")):
            raise HTTPException(status_code=404)

        # Serve index.html for React Router
        index_path = react_build_path / "index.html"
        if index_path.is_file():
            return FileResponse(str(index_path))

        raise HTTPException(status_code=404, detail="Frontend not built")

    logger.info(f"React frontend mounted from {react_build_path}")
else:
    logger.info("React build not found - frontend will be served by Vite dev server")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
