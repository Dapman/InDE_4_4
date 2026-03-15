"""
IKF Hub Simulator — Mock IKF-side endpoints for federation protocol testing.

Runs as an internal FastAPI sub-application within the inde-ikf container.
Enabled only when IKF_FEDERATION_MODE=LIVE and IKF_REMOTE_NODE_URL points
to the local simulator (http://localhost:9100/ikf-hub).

In production, IKF_REMOTE_NODE_URL points to a real IKF regional node,
and the simulator is never loaded.

Implements IKF-side Federation APIs from IKF-IML Spec Section 3.2:
- POST /federation/connect      — Registration + auth, returns session token
- POST /federation/disconnect   — Graceful disconnection
- POST /federation/heartbeat    — Heartbeat acknowledgment
- GET  /federation/sync/status  — Sync status for this IML instance
- GET  /federation/sync/pull    — Return pending patterns (from seed data)
- POST /federation/sync/acknowledge — Acknowledge pattern receipt

v3.5.2 additions:
- POST /knowledge/contribute    — Accept contribution submissions from IML instances

v3.5.3 additions:
- GET  /v1/benchmark/industry/{naicsCode}     — Industry benchmarks
- GET  /v1/benchmark/methodology/{archetypeId} — Methodology benchmarks
- POST /v1/benchmark/compare                   — Percentile comparison
- GET  /v1/benchmark/trends                    — Historical trend data
- POST /v1/trust/relationship/request          — Trust request
- POST /v1/trust/relationship/respond          — Trust response
- DELETE /v1/trust/relationship/{id}           — Revoke trust
- GET  /v1/trust/network                       — Trust network
- GET  /v1/reputation/organization/{orgId}     — Org reputation
- POST /v1/identity/innovator/search           — Cross-org IDTFS
- POST /v1/identity/innovator/{gii}/introduction — Mediated introduction

v3.6.0 additions:
- GET  /v1/biomimicry/patterns                — Federated biomimicry patterns
- GET  /v1/biomimicry/patterns/{pattern_id}   — Specific biomimicry pattern
- POST /v1/biomimicry/contribute              — Submit biomimicry application
- GET  /v1/biomimicry/stats                   — Biomimicry federation stats
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

logger = logging.getLogger("inde.ikf.hub_simulator")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

SIMULATOR_LATENCY_MS = int(os.environ.get("SIMULATOR_LATENCY_MS", "50"))
SIMULATOR_FAILURE_RATE = float(os.environ.get("SIMULATOR_FAILURE_RATE", "0.0"))
SIMULATOR_VERIFICATION_LEVEL = os.environ.get("SIMULATOR_VERIFICATION_LEVEL", "PARTICIPANT")
SIMULATOR_JWT_SECRET = os.environ.get("SIMULATOR_JWT_SECRET", "simulator-secret-key-change-in-prod")


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class ConnectRequest(BaseModel):
    instance_id: str
    organization_id: str
    industry_codes: List[str] = []
    sharing_level: str = "MODERATE"
    version: str = "3.5.1"
    capabilities: List[str] = []


class ConnectResponse(BaseModel):
    status: str
    instance_id: str
    verification_level: str
    federation_token: str
    assigned_region: str
    sync_interval_recommended: int
    capabilities: List[str]


class HeartbeatRequest(BaseModel):
    instance_id: str
    connection_state: str
    pending_contributions: int = 0
    local_health: Dict[str, Any] = {}
    timestamp: str


class HeartbeatResponse(BaseModel):
    status: str
    pending_patterns: int
    pending_actions: List[str]
    server_time: str


class DisconnectRequest(BaseModel):
    instance_id: str
    reason: str = "manual"


class DisconnectResponse(BaseModel):
    status: str
    pending_committed: bool


class SyncPullResponse(BaseModel):
    patterns: List[Dict[str, Any]]
    count: int
    has_more: bool


class SyncAcknowledgeRequest(BaseModel):
    instance_id: str
    pattern_ids: List[str]


class SyncAcknowledgeResponse(BaseModel):
    acknowledged: int


# v3.5.2: Contribution acceptance models
class ContributeRequest(BaseModel):
    """Knowledge contribution submission from an IML instance."""
    contribution_id: str
    package_type: str
    generalized_content: Optional[Dict[str, Any]] = None
    sharing_rights: str = "ORG"
    generalization_level: int = 1
    applicability_context: Dict[str, Any] = {}
    source_metadata: Dict[str, Any] = {}
    contributor_gii: Optional[str] = None
    submitted_at: Optional[str] = None


class ContributeResponse(BaseModel):
    """Response to contribution submission."""
    status: str  # "ACCEPTED", "REJECTED", "PENDING"
    receipt_id: str
    message: str


# v3.5.3: Benchmark models
class BenchmarkCompareRequest(BaseModel):
    """Request for benchmark comparison."""
    metrics: Dict[str, float]
    industryCode: str
    organizationSize: str
    timeframe: str = "YEAR"


# v3.5.3: Trust models
class TrustRequest(BaseModel):
    """Trust relationship request."""
    targetOrganizationId: str
    relationshipType: str
    sharingLevel: str
    justification: Optional[str] = None
    expirationDate: Optional[str] = None


class TrustResponse(BaseModel):
    """Trust relationship response."""
    relationshipId: str
    response: str  # "ACCEPT" or "REJECT"
    terms: Optional[Dict[str, Any]] = None


# v3.5.3: Cross-org IDTFS models
class InnovatorSearchRequest(BaseModel):
    """Cross-org innovator search request."""
    capabilityDomains: List[str] = []
    industryExpertise: List[str] = []
    experienceLevel: str = "INTERMEDIATE"
    availabilityRequired: bool = True
    trustedOrgsOnly: bool = True
    maxResults: int = 10


class IntroductionRequest(BaseModel):
    """Mediated introduction request."""
    targetGii: str
    capabilityNeed: str
    pursuitDomain: str
    requestingOrgDisclosure: str = "ANONYMOUS"


# ==============================================================================
# HUB SIMULATOR CORE
# ==============================================================================

class HubSimulator:
    """
    Simulates IKF hub behavior for federation protocol testing.

    Configuration:
    - SIMULATOR_LATENCY_MS: Artificial latency (default 50ms, simulates network)
    - SIMULATOR_FAILURE_RATE: Probability of simulated failure (default 0.0)
    - SIMULATOR_VERIFICATION_LEVEL: Assigned to connecting orgs (default PARTICIPANT)
    """

    def __init__(self):
        self._registered_nodes: Dict[str, Dict] = {}  # instance_id -> registration data
        self._connected_nodes: Dict[str, Dict] = {}   # instance_id -> session data
        self._pending_patterns: List[Dict] = []       # Patterns to deliver on sync/pull
        self._acknowledged_patterns: Dict[str, List[str]] = {}  # instance_id -> pattern_ids
        self._received_contributions: List[Dict] = []  # v3.5.2: Received contributions
        # v3.5.3: Trust relationships and simulated cross-org data
        self._trust_relationships: List[Dict] = []
        self._introductions: List[Dict] = []
        self._biomimicry_contributions: List[Dict] = []  # v3.6.0
        self._seed_patterns()
        self._seed_trust_network()
        self._seed_cross_org_profiles()
        self._seed_biomimicry_patterns()  # v3.6.0
        logger.info("IKF Hub Simulator initialized")

    def _seed_patterns(self):
        """Seed simulator with test patterns for protocol validation."""
        # 3 universal patterns for testing pattern delivery
        self._pending_patterns = [
            {
                "pattern_id": f"sim-pattern-{i}",
                "title": f"Simulated Global Pattern {i}: {'Customer Discovery' if i == 1 else 'Rapid Prototyping' if i == 2 else 'Market Validation'}",
                "type": "success_pattern",
                "confidence": 0.85 + (i * 0.03),
                "applicability": {
                    "industries": ["ALL"],
                    "stages": ["VISION", "DE_RISK"],
                    "methodologies": ["LEAN_STARTUP", "DESIGN_THINKING"]
                },
                "content": {
                    "summary": f"Test pattern {i} for federation validation - simulates a globally-sourced innovation pattern",
                    "key_takeaways": [
                        f"Simulated insight {i}.1 for protocol testing",
                        f"Simulated insight {i}.2 demonstrating pattern delivery"
                    ],
                    "source_org_count": 10 + i * 5,
                    "success_rate": 0.72 + (i * 0.05)
                },
                "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            for i in range(1, 4)
        ]
        logger.info(f"Seeded {len(self._pending_patterns)} test patterns")

    def _seed_trust_network(self):
        """Seed simulator with test trust relationships."""
        self._trust_relationships = [
            {
                "relationshipId": "trust-rel-001",
                "partnerOrgId": "org-partner-alpha",
                "partnerOrgName": "Alpha Innovations",
                "relationshipType": "BILATERAL",
                "sharingLevel": "PARTNER",
                "status": "ACTIVE",
                "establishedAt": "2025-06-15T10:00:00Z",
                "expiresAt": "2027-06-15T10:00:00Z"
            },
            {
                "relationshipId": "trust-rel-002",
                "partnerOrgId": "org-partner-beta",
                "partnerOrgName": "Beta Technologies",
                "relationshipType": "BILATERAL",
                "sharingLevel": "INDUSTRY",
                "status": "ACTIVE",
                "establishedAt": "2025-09-01T10:00:00Z",
                "expiresAt": "2026-09-01T10:00:00Z"
            },
            {
                "relationshipId": "trust-rel-003",
                "partnerOrgId": "org-partner-gamma",
                "partnerOrgName": "Gamma Solutions",
                "relationshipType": "BILATERAL",
                "sharingLevel": "PARTNER",
                "status": "PROPOSED",
                "establishedAt": None,
                "expiresAt": None
            },
            {
                "relationshipId": "trust-rel-004",
                "partnerOrgId": "org-partner-delta",
                "partnerOrgName": "Delta Corp",
                "relationshipType": "BILATERAL",
                "sharingLevel": "INDUSTRY",
                "status": "EXPIRED",
                "establishedAt": "2024-01-01T10:00:00Z",
                "expiresAt": "2025-01-01T10:00:00Z"
            }
        ]
        logger.info(f"Seeded {len(self._trust_relationships)} trust relationships")

    def _seed_cross_org_profiles(self):
        """Seed simulator with test cross-org innovator profiles."""
        self._cross_org_profiles = [
            {
                "gii": "gii-alpha-001",
                "capabilitySummary": "Product strategy and market validation specialist",
                "domainExpertise": ["product_management", "market_research"],
                "experienceLevel": "EXPERT",
                "availability": "AVAILABLE",
                "orgAffiliation": "Alpha Innovations",
                "industryExpertise": ["TECHNOLOGY", "HEALTHCARE"]
            },
            {
                "gii": "gii-alpha-002",
                "capabilitySummary": "Technical architecture and system design",
                "domainExpertise": ["software_architecture", "cloud_infrastructure"],
                "experienceLevel": "SENIOR",
                "availability": "AVAILABLE",
                "orgAffiliation": "Alpha Innovations",
                "industryExpertise": ["TECHNOLOGY"]
            },
            {
                "gii": "gii-beta-001",
                "capabilitySummary": "Data science and machine learning",
                "domainExpertise": ["data_science", "machine_learning", "analytics"],
                "experienceLevel": "EXPERT",
                "availability": "AVAILABLE",
                "orgAffiliation": "Beta Technologies",
                "industryExpertise": ["TECHNOLOGY", "FINANCE"]
            }
        ]
        logger.info(f"Seeded {len(self._cross_org_profiles)} cross-org profiles")

    def _seed_biomimicry_patterns(self):
        """
        Seed simulator with federated biomimicry patterns.
        v3.6.0: These represent patterns contributed by other organizations.
        """
        self._federated_biomimicry = [
            {
                "pattern_id": "fed-bio-001",
                "organism": "Electric Eel (Electrophorus electricus)",
                "category": "ENERGY_EFFICIENCY",
                "strategy_name": "Distributed Power Generation",
                "description": "Electric eels generate electricity through thousands of specialized cells (electrocytes) arranged in series, creating cumulative voltage.",
                "mechanism": "Electrocytes act like batteries - sodium and potassium ion flow creates ~0.15V per cell. Stacking thousands in series produces 600-860V pulses.",
                "functions": ["generate_electricity", "store_energy", "signal_transmission"],
                "applicable_domains": ["energy", "electronics", "biomedical"],
                "innovation_principles": ["distributed generation", "series amplification", "modular power"],
                "triz_connections": ["35", "19", "28"],
                "source": "ikf_federation",
                "federation_org": "BioEnergy Research Consortium",
                "acceptance_rate": 0.78,
                "match_count": 45
            },
            {
                "pattern_id": "fed-bio-002",
                "organism": "Bombardier Beetle (Brachinus)",
                "category": "ADAPTATION",
                "strategy_name": "Chemical Propulsion System",
                "description": "Bombardier beetles spray boiling chemicals at attackers using a binary chemical reaction triggered only at the moment of ejection.",
                "mechanism": "Two chambers contain hydroquinone and hydrogen peroxide. When mixed in a reaction chamber with catalytic enzymes, they reach 100°C and explosively spray.",
                "functions": ["chemical_defense", "propulsion", "controlled_reaction"],
                "applicable_domains": ["defense", "aerospace", "firefighting", "propulsion"],
                "innovation_principles": ["binary activation", "compartmentalization", "catalytic trigger"],
                "triz_connections": ["36", "31", "15"],
                "source": "ikf_federation",
                "federation_org": "Defense Innovation Lab",
                "acceptance_rate": 0.65,
                "match_count": 28
            },
            {
                "pattern_id": "fed-bio-003",
                "organism": "Mycorrhizal Network",
                "category": "COMMUNICATION",
                "strategy_name": "Underground Resource Network",
                "description": "Mycorrhizal fungi form vast underground networks connecting tree roots, enabling nutrient sharing and chemical signaling across the forest.",
                "mechanism": "Fungal hyphae extend plant root surface area 100-1000x. Trees share sugars, nutrients, and even warning signals through these 'wood wide web' connections.",
                "functions": ["nutrient_distribution", "communication", "resource_sharing"],
                "applicable_domains": ["supply_chain", "distributed_systems", "healthcare", "agriculture"],
                "innovation_principles": ["network effects", "mutualistic exchange", "distributed intelligence"],
                "triz_connections": ["24", "22", "3"],
                "source": "ikf_federation",
                "federation_org": "AgriTech Innovations",
                "acceptance_rate": 0.82,
                "match_count": 67
            },
            {
                "pattern_id": "fed-bio-004",
                "organism": "Pistol Shrimp (Alpheidae)",
                "category": "ENERGY_EFFICIENCY",
                "strategy_name": "Cavitation Weapon",
                "description": "Pistol shrimp produce one of the loudest sounds in the ocean by rapidly closing a specialized claw, creating a cavitation bubble.",
                "mechanism": "Rapid claw closure creates a water jet at 100 km/h. The low pressure zone generates a cavitation bubble that collapses, producing temperatures of 4,700°C briefly.",
                "functions": ["generate_force", "stun_prey", "communication"],
                "applicable_domains": ["cleaning", "medical", "manufacturing", "underwater_tech"],
                "innovation_principles": ["pressure differential", "cavitation harvesting", "sonic weaponry"],
                "triz_connections": ["18", "36", "28"],
                "source": "ikf_federation",
                "federation_org": "Marine Biomimetics Institute",
                "acceptance_rate": 0.71,
                "match_count": 34
            },
            {
                "pattern_id": "fed-bio-005",
                "organism": "Diatoms",
                "category": "STRUCTURAL_STRENGTH",
                "strategy_name": "Optimized Silica Architecture",
                "description": "Diatoms build intricate silica shells (frustules) with patterns that maximize strength while minimizing material usage.",
                "mechanism": "Hierarchical pore structures distribute stress optimally. Computer analysis shows diatom frustule designs exceed human-engineered structures in strength-to-weight ratio.",
                "functions": ["structural_support", "material_efficiency", "light_manipulation"],
                "applicable_domains": ["construction", "materials", "optics", "solar"],
                "innovation_principles": ["hierarchical structure", "topology optimization", "multifunctional design"],
                "triz_connections": ["40", "14", "30"],
                "source": "ikf_federation",
                "federation_org": "Materials Science Federation",
                "acceptance_rate": 0.88,
                "match_count": 89
            }
        ]
        logger.info(f"Seeded {len(self._federated_biomimicry)} federated biomimicry patterns")

    async def _apply_latency(self):
        """Apply configurable artificial latency to simulate network conditions."""
        if SIMULATOR_LATENCY_MS > 0:
            await asyncio.sleep(SIMULATOR_LATENCY_MS / 1000)

    def _should_fail(self) -> bool:
        """Determine if this request should simulate a failure."""
        import random
        return random.random() < SIMULATOR_FAILURE_RATE

    async def handle_connect(self, request: ConnectRequest) -> ConnectResponse:
        """
        Process federation connection request.

        Validates registration, assigns verification level, issues JWT.
        """
        await self._apply_latency()

        if self._should_fail():
            raise HTTPException(status_code=503, detail="Simulated hub failure")

        instance_id = request.instance_id
        org_id = request.organization_id

        # Register if new
        self._registered_nodes[instance_id] = {
            "org_id": org_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "verification_level": SIMULATOR_VERIFICATION_LEVEL,
            "industry_codes": request.industry_codes,
            "sharing_level": request.sharing_level,
            "version": request.version
        }

        # Issue federation JWT (simulated)
        federation_jwt = self._issue_jwt(instance_id, org_id)

        # Mark as connected
        self._connected_nodes[instance_id] = {
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "jwt": federation_jwt,
            "org_id": org_id
        }

        logger.info(f"Hub simulator: CONNECTED {instance_id} (org: {org_id})")

        return ConnectResponse(
            status="CONNECTED",
            instance_id=instance_id,
            verification_level=SIMULATOR_VERIFICATION_LEVEL,
            federation_token=federation_jwt,
            assigned_region="NA",
            sync_interval_recommended=60,
            capabilities=["patterns", "contributions", "benchmarks"]
        )

    async def handle_heartbeat(self, request: HeartbeatRequest) -> HeartbeatResponse:
        """Acknowledge heartbeat and return any pending actions."""
        await self._apply_latency()

        if self._should_fail():
            raise HTTPException(status_code=503, detail="Simulated hub failure")

        instance_id = request.instance_id
        if instance_id not in self._connected_nodes:
            raise HTTPException(status_code=401, detail="Not connected")

        self._connected_nodes[instance_id]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()

        # Calculate pending patterns for this instance
        acknowledged = self._acknowledged_patterns.get(instance_id, [])
        pending_for_instance = [
            p for p in self._pending_patterns
            if p["pattern_id"] not in acknowledged
        ]

        logger.debug(f"Hub simulator: heartbeat from {instance_id}, pending: {len(pending_for_instance)}")

        return HeartbeatResponse(
            status="OK",
            pending_patterns=len(pending_for_instance),
            pending_actions=[],
            server_time=datetime.now(timezone.utc).isoformat()
        )

    async def handle_disconnect(self, request: DisconnectRequest) -> DisconnectResponse:
        """Process graceful disconnection."""
        await self._apply_latency()

        instance_id = request.instance_id
        self._connected_nodes.pop(instance_id, None)

        logger.info(f"Hub simulator: DISCONNECTED {instance_id}")

        return DisconnectResponse(
            status="DISCONNECTED",
            pending_committed=True
        )

    async def handle_sync_status(self, instance_id: str) -> Dict[str, Any]:
        """Return sync status for this instance."""
        await self._apply_latency()

        if instance_id not in self._connected_nodes:
            raise HTTPException(status_code=401, detail="Not connected")

        acknowledged = self._acknowledged_patterns.get(instance_id, [])
        pending_for_instance = [
            p for p in self._pending_patterns
            if p["pattern_id"] not in acknowledged
        ]

        return {
            "status": "OK",
            "instance_id": instance_id,
            "pending_patterns": len(pending_for_instance),
            "last_sync": self._connected_nodes[instance_id].get("last_sync"),
            "server_time": datetime.now(timezone.utc).isoformat()
        }

    async def handle_sync_pull(self, instance_id: str) -> SyncPullResponse:
        """Return pending patterns for this instance."""
        await self._apply_latency()

        if self._should_fail():
            raise HTTPException(status_code=503, detail="Simulated hub failure")

        if instance_id not in self._connected_nodes:
            raise HTTPException(status_code=401, detail="Not connected")

        acknowledged = self._acknowledged_patterns.get(instance_id, [])
        pending_for_instance = [
            p for p in self._pending_patterns
            if p["pattern_id"] not in acknowledged
        ]

        # Update last sync time
        self._connected_nodes[instance_id]["last_sync"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Hub simulator: sync/pull for {instance_id}, returning {len(pending_for_instance)} patterns")

        return SyncPullResponse(
            patterns=pending_for_instance,
            count=len(pending_for_instance),
            has_more=False
        )

    async def handle_sync_acknowledge(self, request: SyncAcknowledgeRequest) -> SyncAcknowledgeResponse:
        """Acknowledge receipt of synced patterns."""
        await self._apply_latency()

        instance_id = request.instance_id
        pattern_ids = request.pattern_ids

        if instance_id not in self._acknowledged_patterns:
            self._acknowledged_patterns[instance_id] = []

        # Record acknowledgments
        for pid in pattern_ids:
            if pid not in self._acknowledged_patterns[instance_id]:
                self._acknowledged_patterns[instance_id].append(pid)

        logger.info(f"Hub simulator: acknowledged {len(pattern_ids)} patterns for {instance_id}")

        return SyncAcknowledgeResponse(acknowledged=len(pattern_ids))

    async def handle_contribute(self, contribution_data: ContributeRequest) -> ContributeResponse:
        """
        Accept a knowledge contribution from an IML instance.
        Simulates IKF validation and acceptance.

        v3.5.2: Added for bidirectional knowledge flow.
        """
        await self._apply_latency()

        if self._should_fail():
            raise HTTPException(status_code=503, detail="Simulated hub failure")

        receipt_id = f"ikf-receipt-{uuid.uuid4().hex[:12]}"

        # Store the received contribution
        self._received_contributions.append({
            "receipt_id": receipt_id,
            "contribution_id": contribution_data.contribution_id,
            "package_type": contribution_data.package_type,
            "source_instance": contribution_data.source_metadata.get("instance_id"),
            "source_org": contribution_data.source_metadata.get("org_id"),
            "received_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(
            f"Hub simulator: received contribution {contribution_data.contribution_id} "
            f"(type: {contribution_data.package_type}, receipt: {receipt_id})"
        )

        return ContributeResponse(
            status="ACCEPTED",
            receipt_id=receipt_id,
            message="Contribution accepted for processing"
        )

    def _issue_jwt(self, instance_id: str, org_id: str) -> str:
        """
        Issue a simulated federation JWT.

        In production, this comes from the IKF Identity Service.
        The JWT structure matches IKF-IML Spec Section 9.1.2.
        """
        try:
            import jwt  # PyJWT

            now = datetime.now(timezone.utc)
            payload = {
                "sub": org_id,
                "iss": "https://auth.ikf.indeverse.io",
                "aud": "api.ikf.indeverse.io",
                "exp": (now + timedelta(minutes=30)).timestamp(),
                "iat": now.timestamp(),
                "scope": "federation:read federation:write patterns:read knowledge:contribute",
                "orgId": org_id,
                "verificationLevel": SIMULATOR_VERIFICATION_LEVEL,
                "region": "NA",
                "instanceId": instance_id
            }

            return jwt.encode(payload, SIMULATOR_JWT_SECRET, algorithm="HS256")
        except ImportError:
            # Fallback if PyJWT not installed - return a mock token
            logger.warning("PyJWT not available, returning mock token")
            return f"mock-jwt-{instance_id}-{org_id}-{uuid.uuid4().hex[:8]}"

    def get_stats(self) -> Dict[str, Any]:
        """Return simulator statistics for admin/debugging."""
        return {
            "registered_nodes": len(self._registered_nodes),
            "connected_nodes": len(self._connected_nodes),
            "pending_patterns": len(self._pending_patterns),
            "acknowledged_patterns": {
                k: len(v) for k, v in self._acknowledged_patterns.items()
            },
            "received_contributions": len(self._received_contributions),  # v3.5.2
            "config": {
                "latency_ms": SIMULATOR_LATENCY_MS,
                "failure_rate": SIMULATOR_FAILURE_RATE,
                "verification_level": SIMULATOR_VERIFICATION_LEVEL
            }
        }

    def get_contributions(self) -> List[Dict]:
        """Return list of received contributions (v3.5.2)."""
        return self._received_contributions

    # =========================================================================
    # v3.5.3: BENCHMARK HANDLERS
    # =========================================================================

    async def handle_industry_benchmark(self, naics_code: str) -> Dict[str, Any]:
        """Return simulated industry benchmark data."""
        await self._apply_latency()

        # Simulated benchmark data - realistic distributions
        return {
            "naicsCode": naics_code,
            "industryName": self._get_industry_name(naics_code),
            "metrics": {
                "pursuitSuccessRate": {"mean": 0.42, "median": 0.40, "stdDev": 0.15, "p25": 0.28, "p75": 0.55},
                "timeToValidation": {"mean": 45.0, "median": 42.0, "stdDev": 18.0, "p25": 30.0, "p75": 58.0},
                "pivotRate": {"mean": 0.35, "median": 0.32, "stdDev": 0.12, "p25": 0.22, "p75": 0.45},
                "learningVelocity": {"mean": 0.65, "median": 0.62, "stdDev": 0.18, "p25": 0.50, "p75": 0.78},
                "knowledgeUtilization": {"mean": 0.55, "median": 0.52, "stdDev": 0.20, "p25": 0.38, "p75": 0.70},
                "repeatFailureRate": {"mean": 0.18, "median": 0.15, "stdDev": 0.10, "p25": 0.08, "p75": 0.25},
                "patternRecognitionLatency": {"mean": 12.0, "median": 10.0, "stdDev": 5.0, "p25": 7.0, "p75": 15.0},
                "crossPollinationApplicationRate": {"mean": 0.25, "median": 0.22, "stdDev": 0.12, "p25": 0.15, "p75": 0.35}
            },
            "sampleSize": 127,
            "confidenceInterval": 0.95,
            "timeframe": "YEAR",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    async def handle_methodology_benchmark(self, archetype_id: str) -> Dict[str, Any]:
        """Return simulated methodology benchmark data."""
        await self._apply_latency()

        return {
            "archetypeId": archetype_id,
            "archetypeName": archetype_id.replace("_", " ").title(),
            "completionRate": 0.68,
            "avgTimePerPhase": {
                "VISION": 14.5,
                "DE_RISK": 28.0,
                "SCALE_PREP": 21.5
            },
            "successDistribution": {
                "COMPLETED.SUCCESSFUL": 0.42,
                "COMPLETED.VALIDATED_NOT_PURSUED": 0.18,
                "TERMINATED.PIVOTED": 0.22,
                "TERMINATED.FAILED": 0.12,
                "ACTIVE": 0.06
            },
            "sampleSize": 89,
            "timeframe": "YEAR",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    async def handle_benchmark_compare(self, request: BenchmarkCompareRequest) -> Dict[str, Any]:
        """Return simulated percentile ranking."""
        await self._apply_latency()

        # Calculate simulated percentiles based on input metrics
        percentiles = {}
        for metric, value in request.metrics.items():
            # Simulate percentile calculation
            percentiles[metric] = self._simulate_percentile(metric, value)

        return {
            "industryBaseline": {
                metric: {"mean": 0.45, "median": 0.42, "stdDev": 0.15}
                for metric in request.metrics.keys()
            },
            "globalBaseline": {
                metric: {"mean": 0.48, "median": 0.45, "stdDev": 0.18}
                for metric in request.metrics.keys()
            },
            "percentileRanking": percentiles,
            "sampleSize": 250,
            "confidenceInterval": 0.95,
            "calculatedAt": datetime.now(timezone.utc).isoformat()
        }

    async def handle_benchmark_trends(self, industry_code: str) -> Dict[str, Any]:
        """Return simulated historical trend data."""
        await self._apply_latency()

        # Generate simulated trend data points
        return {
            "industryCode": industry_code,
            "trends": [
                {
                    "metricName": "pursuitSuccessRate",
                    "dataPoints": [
                        {"period": "2025-Q1", "value": 0.38},
                        {"period": "2025-Q2", "value": 0.40},
                        {"period": "2025-Q3", "value": 0.42},
                        {"period": "2025-Q4", "value": 0.44}
                    ],
                    "trendDirection": "improving",
                    "changePercentage": 15.8
                },
                {
                    "metricName": "learningVelocity",
                    "dataPoints": [
                        {"period": "2025-Q1", "value": 0.58},
                        {"period": "2025-Q2", "value": 0.60},
                        {"period": "2025-Q3", "value": 0.62},
                        {"period": "2025-Q4", "value": 0.65}
                    ],
                    "trendDirection": "improving",
                    "changePercentage": 12.1
                }
            ],
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    def _get_industry_name(self, naics_code: str) -> str:
        """Get industry name from NAICS code."""
        names = {
            "541": "Professional Services",
            "541511": "Custom Software Development",
            "621": "Healthcare",
            "522": "Finance",
            "334": "Technology Manufacturing"
        }
        return names.get(naics_code, f"Industry {naics_code}")

    def _simulate_percentile(self, metric: str, value: float) -> int:
        """Simulate percentile calculation."""
        import random
        # Add some randomness but keep it reasonable
        base = int(value * 100) if value <= 1 else int(min(value, 100))
        variance = random.randint(-15, 15)
        return max(1, min(99, base + variance))

    # =========================================================================
    # v3.5.3: TRUST HANDLERS
    # =========================================================================

    async def handle_trust_request(self, request: TrustRequest) -> Dict[str, Any]:
        """Process trust relationship request."""
        await self._apply_latency()

        relationship_id = f"trust-rel-{uuid.uuid4().hex[:8]}"

        relationship = {
            "relationshipId": relationship_id,
            "partnerOrgId": request.targetOrganizationId,
            "relationshipType": request.relationshipType,
            "sharingLevel": request.sharingLevel,
            "status": "PROPOSED",
            "requestedAt": datetime.now(timezone.utc).isoformat(),
            "expirationDate": request.expirationDate
        }

        self._trust_relationships.append(relationship)
        logger.info(f"Hub simulator: trust request {relationship_id} to {request.targetOrganizationId}")

        return relationship

    async def handle_trust_respond(self, request: TrustResponse) -> Dict[str, Any]:
        """Process trust relationship response."""
        await self._apply_latency()

        # Find and update the relationship
        for rel in self._trust_relationships:
            if rel["relationshipId"] == request.relationshipId:
                if request.response == "ACCEPT":
                    rel["status"] = "ACTIVE"
                    rel["establishedAt"] = datetime.now(timezone.utc).isoformat()
                else:
                    rel["status"] = "REJECTED"
                logger.info(f"Hub simulator: trust {request.relationshipId} -> {rel['status']}")
                return rel

        raise HTTPException(status_code=404, detail="Relationship not found")

    async def handle_trust_revoke(self, relationship_id: str) -> Dict[str, Any]:
        """Revoke a trust relationship."""
        await self._apply_latency()

        for rel in self._trust_relationships:
            if rel["relationshipId"] == relationship_id:
                rel["status"] = "REVOKED"
                rel["revokedAt"] = datetime.now(timezone.utc).isoformat()
                logger.info(f"Hub simulator: trust {relationship_id} revoked")
                return {"status": "REVOKED", "relationshipId": relationship_id}

        raise HTTPException(status_code=404, detail="Relationship not found")

    async def handle_trust_network(self) -> Dict[str, Any]:
        """Return the trust network."""
        await self._apply_latency()
        return {"relationships": self._trust_relationships}

    async def handle_org_reputation(self, org_id: str) -> Dict[str, Any]:
        """Return simulated organization reputation."""
        await self._apply_latency()

        return {
            "orgId": org_id,
            "overallScore": 78,
            "components": {
                "contributionVolume": {"score": 72, "weight": 0.20},
                "contributionQuality": {"score": 85, "weight": 0.30},
                "patternValidation": {"score": 80, "weight": 0.25},
                "communityEngagement": {"score": 65, "weight": 0.15},
                "complianceRecord": {"score": 92, "weight": 0.10}
            },
            "trend": "improving",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # v3.5.3: CROSS-ORG IDTFS HANDLERS
    # =========================================================================

    async def handle_innovator_search(self, request: InnovatorSearchRequest) -> Dict[str, Any]:
        """Search for cross-org innovators."""
        await self._apply_latency()

        # Filter profiles based on request
        results = []
        for profile in self._cross_org_profiles:
            # Only return AVAILABLE (UNAVAILABLE is never exposed)
            if profile["availability"] != "AVAILABLE":
                continue

            # Match capabilities
            if request.capabilityDomains:
                overlap = set(request.capabilityDomains) & set(profile.get("domainExpertise", []))
                if not overlap:
                    continue

            results.append(profile)

            if len(results) >= request.maxResults:
                break

        logger.info(f"Hub simulator: cross-org search returned {len(results)} results")

        return {
            "results": results,
            "totalMatches": len(results),
            "trustedOrgsSearched": 2
        }

    async def handle_introduction_request(self, gii: str, request: IntroductionRequest) -> Dict[str, Any]:
        """Process mediated introduction request."""
        await self._apply_latency()

        introduction_id = f"intro-{uuid.uuid4().hex[:8]}"

        introduction = {
            "introductionId": introduction_id,
            "targetGii": gii,
            "capabilityNeed": request.capabilityNeed,
            "pursuitDomain": request.pursuitDomain,
            "status": "PENDING",
            "requestedAt": datetime.now(timezone.utc).isoformat()
        }

        self._introductions.append(introduction)
        logger.info(f"Hub simulator: introduction {introduction_id} requested for {gii}")

        return introduction

    # =========================================================================
    # v3.6.0: BIOMIMICRY HANDLERS
    # =========================================================================

    async def handle_biomimicry_patterns(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Return federated biomimicry patterns."""
        await self._apply_latency()

        patterns = self._federated_biomimicry
        if category:
            patterns = [p for p in patterns if p.get("category") == category]

        patterns = patterns[:limit]

        return {
            "patterns": patterns,
            "count": len(patterns),
            "total_available": len(self._federated_biomimicry),
            "source": "ikf_federation"
        }

    async def handle_biomimicry_pattern(self, pattern_id: str) -> Dict[str, Any]:
        """Return a specific federated biomimicry pattern."""
        await self._apply_latency()

        for pattern in self._federated_biomimicry:
            if pattern["pattern_id"] == pattern_id:
                return pattern

        raise HTTPException(status_code=404, detail="Biomimicry pattern not found")

    async def handle_biomimicry_contribute(self, contribution: Dict[str, Any]) -> Dict[str, Any]:
        """Accept a biomimicry application contribution."""
        await self._apply_latency()

        if self._should_fail():
            raise HTTPException(status_code=503, detail="Simulated hub failure")

        receipt_id = f"bio-receipt-{uuid.uuid4().hex[:12]}"

        self._biomimicry_contributions.append({
            "receipt_id": receipt_id,
            "contribution_id": contribution.get("contribution_id"),
            "pursuit_id": contribution.get("pursuit_id"),
            "patterns_applied": len(contribution.get("biomimicry_applications", [])),
            "received_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(
            f"Hub simulator: received biomimicry contribution "
            f"(receipt: {receipt_id}, patterns: {len(contribution.get('biomimicry_applications', []))})"
        )

        return {
            "status": "ACCEPTED",
            "receipt_id": receipt_id,
            "message": "Biomimicry application contribution accepted"
        }

    async def handle_biomimicry_stats(self) -> Dict[str, Any]:
        """Return biomimicry federation statistics."""
        await self._apply_latency()

        by_category = {}
        for pattern in self._federated_biomimicry:
            cat = pattern.get("category", "UNKNOWN")
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_patterns": len(self._federated_biomimicry),
            "by_category": by_category,
            "contributing_orgs": len(set(p.get("federation_org") for p in self._federated_biomimicry)),
            "total_contributions_received": len(self._biomimicry_contributions),
            "avg_acceptance_rate": sum(p.get("acceptance_rate", 0) for p in self._federated_biomimicry) / max(1, len(self._federated_biomimicry))
        }


# ==============================================================================
# ROUTER FACTORY
# ==============================================================================

def create_simulator_routes() -> APIRouter:
    """
    Create FastAPI router with hub simulator endpoints.

    Usage in ikf-service/main.py:
        if should_enable_simulator():
            from federation.hub_simulator import create_simulator_routes
            app.include_router(create_simulator_routes(), prefix="/ikf-hub")
    """
    router = APIRouter(tags=["IKF Hub Simulator"])
    simulator = HubSimulator()

    @router.post("/federation/connect", response_model=ConnectResponse)
    async def connect(request: ConnectRequest):
        """Register and connect an InDE instance to the simulated hub."""
        return await simulator.handle_connect(request)

    @router.post("/federation/heartbeat", response_model=HeartbeatResponse)
    async def heartbeat(request: HeartbeatRequest):
        """Process heartbeat from connected instance."""
        return await simulator.handle_heartbeat(request)

    @router.post("/federation/disconnect", response_model=DisconnectResponse)
    async def disconnect(request: DisconnectRequest):
        """Gracefully disconnect an instance."""
        return await simulator.handle_disconnect(request)

    @router.get("/federation/sync/status")
    async def sync_status(x_inde_instance: str = Header(alias="X-InDE-Instance")):
        """Get sync status for calling instance."""
        return await simulator.handle_sync_status(x_inde_instance)

    @router.get("/federation/sync/pull", response_model=SyncPullResponse)
    async def sync_pull(x_inde_instance: str = Header(alias="X-InDE-Instance")):
        """Pull pending patterns for calling instance."""
        return await simulator.handle_sync_pull(x_inde_instance)

    @router.post("/federation/sync/acknowledge", response_model=SyncAcknowledgeResponse)
    async def sync_acknowledge(request: SyncAcknowledgeRequest):
        """Acknowledge receipt of synced patterns."""
        return await simulator.handle_sync_acknowledge(request)

    # v3.5.2: Contribution acceptance endpoint
    @router.post("/knowledge/contribute", response_model=ContributeResponse)
    async def contribute(request: ContributeRequest):
        """Accept a knowledge contribution from an IML instance."""
        return await simulator.handle_contribute(request)

    @router.get("/admin/stats")
    async def admin_stats():
        """Get simulator statistics (admin endpoint)."""
        return simulator.get_stats()

    @router.get("/admin/contributions")
    async def admin_contributions():
        """Get received contributions (v3.5.2)."""
        return {"contributions": simulator.get_contributions()}

    @router.get("/health")
    async def health():
        """Health check for the simulator."""
        return {
            "status": "healthy",
            "simulator": True,
            "version": "3.6.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # v3.5.3: BENCHMARK ENDPOINTS
    # =========================================================================

    @router.get("/v1/benchmark/industry/{naics_code}")
    async def get_industry_benchmark(naics_code: str):
        """Get industry benchmark data."""
        return await simulator.handle_industry_benchmark(naics_code)

    @router.get("/v1/benchmark/methodology/{archetype_id}")
    async def get_methodology_benchmark(archetype_id: str):
        """Get methodology benchmark data."""
        return await simulator.handle_methodology_benchmark(archetype_id)

    @router.post("/v1/benchmark/compare")
    async def compare_benchmarks(request: BenchmarkCompareRequest):
        """Compare org metrics against benchmarks."""
        return await simulator.handle_benchmark_compare(request)

    @router.get("/v1/benchmark/trends")
    async def get_benchmark_trends(industryCode: str = None):
        """Get benchmark trend data."""
        return await simulator.handle_benchmark_trends(industryCode or "541")

    # =========================================================================
    # v3.5.3: TRUST ENDPOINTS
    # =========================================================================

    @router.post("/v1/trust/relationship/request")
    async def request_trust(request: TrustRequest):
        """Request a trust relationship."""
        return await simulator.handle_trust_request(request)

    @router.post("/v1/trust/relationship/respond")
    async def respond_to_trust(request: TrustResponse):
        """Respond to a trust relationship request."""
        return await simulator.handle_trust_respond(request)

    @router.delete("/v1/trust/relationship/{relationship_id}")
    async def revoke_trust(relationship_id: str):
        """Revoke a trust relationship."""
        return await simulator.handle_trust_revoke(relationship_id)

    @router.get("/v1/trust/network")
    async def get_trust_network():
        """Get the organization's trust network."""
        return await simulator.handle_trust_network()

    @router.get("/v1/reputation/organization/{org_id}")
    async def get_org_reputation(org_id: str):
        """Get organization reputation score."""
        return await simulator.handle_org_reputation(org_id)

    # =========================================================================
    # v3.5.3: CROSS-ORG IDTFS ENDPOINTS
    # =========================================================================

    @router.post("/v1/identity/innovator/search")
    async def search_innovators(request: InnovatorSearchRequest):
        """Search for innovators across trusted organizations."""
        return await simulator.handle_innovator_search(request)

    @router.post("/v1/identity/innovator/{gii}/introduction")
    async def request_introduction(gii: str, request: IntroductionRequest):
        """Request mediated introduction to an innovator."""
        return await simulator.handle_introduction_request(gii, request)

    # =========================================================================
    # v3.6.0: BIOMIMICRY ENDPOINTS
    # =========================================================================

    @router.get("/v1/biomimicry/patterns")
    async def get_biomimicry_patterns(category: str = None, limit: int = 20):
        """Get federated biomimicry patterns."""
        return await simulator.handle_biomimicry_patterns(category, limit)

    @router.get("/v1/biomimicry/patterns/{pattern_id}")
    async def get_biomimicry_pattern(pattern_id: str):
        """Get a specific federated biomimicry pattern."""
        return await simulator.handle_biomimicry_pattern(pattern_id)

    @router.post("/v1/biomimicry/contribute")
    async def contribute_biomimicry(request: Request):
        """Submit a biomimicry application contribution."""
        contribution = await request.json()
        return await simulator.handle_biomimicry_contribute(contribution)

    @router.get("/v1/biomimicry/stats")
    async def get_biomimicry_stats():
        """Get biomimicry federation statistics."""
        return await simulator.handle_biomimicry_stats()

    return router
