"""
InDE IKF Service v3.7.3 - Innovation Knowledge Fabric Local Node
Entry point for the IKF container with FastAPI, Redis consumer, and MongoDB.

v3.7.3 additions:
- EMS Innovator Review Interface for coaching-assisted methodology validation
- Archetype Publisher for versioned methodology publication
- Review & Publish API endpoints (13 new endpoints)
- Synthesized archetype activation for future pursuits

v3.7.2 additions:
- EMS Pattern Inference Engine for automatic pattern discovery
- ADL Generator for synthesized archetype creation
- Inference & ADL API endpoints

v3.7.1 additions:
- EMS Process Observation Engine for ad-hoc pursuit behavior capture
- Ad-Hoc Pursuit Mode with non-directive ODICM coaching
- Process Observation consumer group on event bus

v3.7.0 additions:
- Display Label Registry integration for human-readable identifiers
- Response transform middleware for IKF API responses
- Stripped internal IDs from all innovator-facing responses

v3.6.1 additions:
- TRIZ Archetype with 40 inventive principles and contradiction matrix
- Blue Ocean Strategy Archetype with strategy canvas artifacts
- Scenario Exploration coaching mode (conversational decision support)
- TRIZ-Biomimicry Bridge for cross-methodology coaching moments
- 15 new event types (5 TRIZ + 4 Blue Ocean + 6 Scenario)

v3.6.0 additions:
- Biomimicry Pattern Database with 44+ curated biological strategies
- LLM-assisted Challenge Analyzer for function extraction and pattern matching
- Biomimicry Detection Service for coaching trigger decisions
- Biomimicry Feedback Tracker for pattern effectiveness learning
- Biomimicry API endpoints for analysis, feedback, and pattern management
- Biomimicry event types for analytics and federation

v3.5.3 additions:
- Global Benchmarking Engine for anonymized comparative analytics
- Trust Network & Reputation management
- Cross-Organization IDTFS for federated talent discovery
- WebSocket real-time event delivery
- Benchmark coaching context integration

v3.5.2 additions:
- Contribution Outbox for guaranteed delivery
- Pattern Importer for inbound IKF patterns
- Federation pattern cache (ikf_federation_patterns)
- Incremental pattern sync service
- Publication boundary enforcement
- Cross-pollination detection

v3.5.1 additions:
- Connection Manager for federation lifecycle
- Circuit Breaker for resilience
- Federation Admin API
- API versioning with /v1/ prefix
- Hub Simulator for local testing
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("inde.ikf")


@asynccontextmanager
async def lifespan(app):
    """IKF service startup and shutdown."""
    # Connect to MongoDB
    from pymongo import MongoClient
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/inde")
    client = MongoClient(mongo_uri)
    app.state.db = client.get_database()
    logger.info(f"Connected to MongoDB: {mongo_uri}")

    # Connect Redis publisher
    from events.publisher import IKFEventPublisher
    ikf_publisher = IKFEventPublisher()
    await ikf_publisher.connect()
    app.state.publisher = ikf_publisher

    # Start Redis consumer for IKF events
    from events.consumer import IKFEventConsumer
    consumer = IKFEventConsumer(app.state.db, app.state.publisher)
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.start())
    app.state.consumer = consumer
    app.state.consumer_task = consumer_task

    # Initialize federation node (v3.2 legacy)
    from federation.local_node import LocalFederationNode
    federation_node = LocalFederationNode(app.state.db)
    await federation_node.initialize()
    app.state.federation_node = federation_node
    logger.info(f"Federation node initialized: {federation_node.node_id} ({federation_node.mode.value})")

    # v3.5.1: Initialize circuit breaker
    from federation.circuit_breaker import CircuitBreaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=int(os.environ.get("IKF_CIRCUIT_BREAKER_THRESHOLD", "5")),
        reset_timeout=int(os.environ.get("IKF_CIRCUIT_BREAKER_RESET", "300"))
    )
    app.state.circuit_breaker = circuit_breaker
    logger.info("Circuit breaker initialized")

    # v3.5.1: Initialize connection manager
    from federation.connection_manager import ConnectionManager, FederationState
    connection_manager = ConnectionManager(
        db=app.state.db,
        config=None,  # Uses defaults from environment
        event_publisher=ikf_publisher,
        circuit_breaker=circuit_breaker
    )
    app.state.connection_manager = connection_manager
    logger.info(f"Connection manager initialized (state: {connection_manager.state.value})")

    # v3.5.2: Initialize HTTP client for outbound requests
    import httpx
    http_client = httpx.AsyncClient(timeout=30.0)
    app.state.http_client = http_client

    # v3.5.2: Initialize Pattern Importer
    from federation.pattern_importer import PatternImporter
    pattern_importer = PatternImporter(app.state.db, None, ikf_publisher)
    app.state.pattern_importer = pattern_importer
    logger.info("Pattern importer initialized")

    # v3.5.2: Initialize Pattern Sync Service
    from federation.pattern_sync import PatternSyncService
    pattern_sync = PatternSyncService(
        db=app.state.db,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        pattern_importer=pattern_importer,
        http_client=http_client,
        config=None,
        event_publisher=ikf_publisher
    )
    app.state.pattern_sync = pattern_sync
    logger.info("Pattern sync service initialized")

    # v3.5.2: Initialize Contribution Outbox
    from contribution.outbox import ContributionOutbox
    contribution_outbox = ContributionOutbox(
        db=app.state.db,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        event_publisher=ikf_publisher,
        http_client=http_client,
        config=None
    )
    app.state.contribution_outbox = contribution_outbox
    logger.info("Contribution outbox initialized")

    # v3.5.2: Initialize Cross-Pollination Detector
    from federation.cross_pollination import CrossPollinationDetector
    cross_pollination = CrossPollinationDetector(app.state.db, ikf_publisher, None)
    app.state.cross_pollination = cross_pollination
    logger.info("Cross-pollination detector initialized")

    # v3.5.3: Initialize Benchmark Engine
    from federation.benchmark_engine import BenchmarkEngine
    benchmark_engine = BenchmarkEngine(
        db=app.state.db,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        http_client=http_client,
        config=None
    )
    app.state.benchmark_engine = benchmark_engine
    logger.info("Benchmark engine initialized")

    # v3.5.3: Initialize Trust Manager
    from federation.trust_manager import TrustManager
    trust_manager = TrustManager(
        db=app.state.db,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        http_client=http_client,
        event_publisher=ikf_publisher,
        config=None
    )
    app.state.trust_manager = trust_manager
    logger.info("Trust manager initialized")

    # v3.5.3: Initialize Reputation Tracker
    from federation.reputation_tracker import ReputationTracker
    reputation_tracker = ReputationTracker(
        db=app.state.db,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        http_client=http_client,
        config=None
    )
    app.state.reputation_tracker = reputation_tracker
    logger.info("Reputation tracker initialized")

    # v3.5.3: Initialize Cross-Org Discovery Service
    from federation.cross_org_discovery import CrossOrgDiscoveryService
    cross_org_discovery = CrossOrgDiscoveryService(
        db=app.state.db,
        trust_manager=trust_manager,
        connection_manager=connection_manager,
        circuit_breaker=circuit_breaker,
        http_client=http_client,
        config=None
    )
    app.state.cross_org_discovery = cross_org_discovery
    logger.info("Cross-org discovery service initialized")

    # v3.5.3: Initialize WebSocket Manager
    from realtime.websocket_manager import WebSocketManager
    websocket_manager = WebSocketManager()
    app.state.websocket_manager = websocket_manager
    logger.info("WebSocket manager initialized")

    # v3.5.3: Initialize Event Bridge
    from realtime.event_bridge import EventBridge
    event_bridge = EventBridge(websocket_manager)
    app.state.event_bridge = event_bridge
    logger.info("Event bridge initialized")

    # v3.5.3: Initialize Channel Manager
    from realtime.channels import ChannelManager
    channel_manager = ChannelManager()
    app.state.channel_manager = channel_manager
    logger.info("Channel manager initialized")

    # v3.6.0: Initialize Biomimicry Services
    try:
        from biomimicry.challenge_analyzer import BiomimicryAnalyzer
        from biomimicry.detection import BiomimicryDetector
        from biomimicry.feedback import BiomimicryFeedback

        biomimicry_analyzer = BiomimicryAnalyzer(app.state.db, http_client, None)
        biomimicry_detector = BiomimicryDetector(app.state.db, None)
        biomimicry_feedback = BiomimicryFeedback(app.state.db, ikf_publisher)

        app.state.biomimicry_analyzer = biomimicry_analyzer
        app.state.biomimicry_detector = biomimicry_detector
        app.state.biomimicry_feedback = biomimicry_feedback
        logger.info("Biomimicry services initialized (analyzer, detector, feedback)")
    except ImportError as e:
        logger.warning(f"Biomimicry services not available: {e}")
        app.state.biomimicry_analyzer = None
        app.state.biomimicry_detector = None
        app.state.biomimicry_feedback = None

    # Wire up hub simulator if configured for local testing
    federation_mode = os.environ.get("IKF_FEDERATION_MODE", "OFFLINE")
    if federation_mode == "LIVE":
        hub_url = os.environ.get("IKF_REMOTE_NODE_URL", "")
        if "localhost" in hub_url or "hub-simulator" in hub_url or "127.0.0.1" in hub_url:
            try:
                from federation.hub_simulator import create_simulator_routes
                app.include_router(create_simulator_routes(), prefix="/ikf-hub")
                logger.info("Hub simulator enabled at /ikf-hub")
            except ImportError as e:
                logger.warning(f"Could not load hub simulator: {e}")

        # Auto-connect if previously registered
        if connection_manager.state == FederationState.DISCONNECTED:
            logger.info("Previously registered - scheduling auto-connect...")
            asyncio.create_task(connection_manager.connect())

        # v3.5.2: Start background workers
        contribution_outbox.start_worker()
        pattern_sync.start_periodic_sync()

        # v3.5.3: Start new background workers
        benchmark_engine.start_sync()
        reputation_tracker.start_sync()
        websocket_manager.start()
        event_bridge.start()
        logger.info("Background workers started (including v3.5.3 components)")
    else:
        logger.info(f"Federation mode: {federation_mode} - connection manager idle")

    logger.info("InDE IKF Service v3.7.3 started")
    yield

    # Shutdown: stop v3.5.3 workers first
    event_bridge.stop()
    await websocket_manager.shutdown()
    reputation_tracker.stop_sync()
    benchmark_engine.stop_sync()
    logger.info("v3.5.3 background workers stopped")

    # Shutdown: stop v3.5.2 workers
    contribution_outbox.stop_worker()
    pattern_sync.stop_sync()
    logger.info("v3.5.2 background workers stopped")

    # Close HTTP client
    await http_client.aclose()

    # Shutdown: graceful disconnect
    if connection_manager.is_connected:
        await connection_manager.disconnect()
    await connection_manager.shutdown()
    await federation_node.shutdown()
    await consumer.stop()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await ikf_publisher.close()
    client.close()
    logger.info("InDE IKF Service shutting down")


app = FastAPI(
    title="InDE IKF Service",
    description="Innovation Knowledge Fabric - Local Node",
    version="3.7.3",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from api import health, contributions, federation, federation_admin
from api import benchmarks, trust, cross_org, websocket

app.include_router(health.router)
app.include_router(contributions.router)
app.include_router(federation.router)
app.include_router(federation_admin.router)

# v3.5.3 routers
app.include_router(benchmarks.router)
app.include_router(trust.router)
app.include_router(trust.reputation_router)  # Reputation routes
app.include_router(cross_org.router)
app.include_router(websocket.router)

# v3.6.0: Biomimicry router
try:
    from api.biomimicry import create_biomimicry_router
    # Router will be created with dependencies when app starts
    # We use a startup event to wire it with dependencies
except ImportError:
    pass  # Biomimicry API not available


@app.on_event("startup")
async def wire_biomimicry_router():
    """Wire biomimicry router after app state is initialized."""
    if hasattr(app.state, 'biomimicry_analyzer') and app.state.biomimicry_analyzer:
        from api.biomimicry import create_biomimicry_router
        biomimicry_router = create_biomimicry_router(
            app.state.biomimicry_analyzer,
            app.state.biomimicry_feedback,
            app.state.db
        )
        app.include_router(biomimicry_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "InDE IKF Service",
        "version": "3.7.3",
        "status": "running",
        "federation_mode": os.environ.get("IKF_FEDERATION_MODE", "OFFLINE"),
        "api_version": "v1",
        "features": ["biomimicry", "triz", "blue_ocean", "scenario_exploration", "ems", "review_interface"]  # v3.7.3
    }


# ==============================================================================
# LEGACY REDIRECTS (Finding 6.2 - backward compatibility)
# ==============================================================================

@app.get("/ikf/federation/{path:path}")
async def legacy_federation_redirect_get(path: str, request: Request):
    """Redirect unversioned GET /ikf/federation/* to /v1/federation/*."""
    query = str(request.query_params)
    new_url = f"/v1/federation/{path}"
    if query:
        new_url = f"{new_url}?{query}"
    return RedirectResponse(url=new_url, status_code=308)


@app.post("/ikf/federation/{path:path}")
async def legacy_federation_redirect_post(path: str):
    """Redirect unversioned POST /ikf/federation/* to /v1/federation/*."""
    return RedirectResponse(url=f"/v1/federation/{path}", status_code=308)


@app.get("/federation/{path:path}")
async def legacy_redirect_get(path: str, request: Request):
    """Redirect /federation/* to /v1/federation/*."""
    query = str(request.query_params)
    new_url = f"/v1/federation/{path}"
    if query:
        new_url = f"{new_url}?{query}"
    return RedirectResponse(url=new_url, status_code=308)


@app.post("/federation/{path:path}")
async def legacy_redirect_post(path: str):
    """Redirect /federation/* to /v1/federation/*."""
    return RedirectResponse(url=f"/v1/federation/{path}", status_code=308)
