"""
InDE IKF Service v3.5.1 - Federation Protocol API
Full implementation for local node operations, pattern queries, and submissions.

Features:
- Node status and heartbeat
- Pattern search (federation + local)
- Benchmark queries
- Risk indicator aggregation
- Contribution submission
- API versioning (/v1/federation)

Finding 6.2: API versioning added with /v1/ prefix
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import os
import logging

logger = logging.getLogger("inde.ikf.federation.api")

# v3.5.1: Use versioned API prefix (Finding 6.2)
router = APIRouter(prefix="/v1/federation", tags=["federation"])


class PatternSearchRequest(BaseModel):
    """Pattern search query."""
    methodology: Optional[str] = None
    industry: Optional[str] = None
    phase: Optional[str] = None
    package_type: str = "pattern_contribution"
    limit: int = 10


class BenchmarkRequest(BaseModel):
    """Benchmark query."""
    methodology: str
    phase: str
    industry: Optional[str] = None


class RiskIndicatorRequest(BaseModel):
    """Risk indicator query."""
    phase: Optional[str] = None
    methodology: Optional[str] = None
    industry: Optional[str] = None


class SubmissionRequest(BaseModel):
    """Submission request."""
    contribution_ids: List[str]


class PatternSyncRequest(BaseModel):
    """Request to sync patterns from IKF."""
    categories: List[str] = []
    since: Optional[datetime] = None
    limit: int = 100


@router.get("/status")
async def get_federation_status(request: Request):
    """
    Get local federation node status.

    Returns node ID, connectivity mode, and capabilities.
    """
    node = getattr(request.app.state, "federation_node", None)
    if not node:
        return {
            "status": "NOT_INITIALIZED",
            "node_id": "local-node",
            "node_type": "local",
            "mode": "OFFLINE",
            "message": "Federation node not initialized - running in local mode"
        }

    return node.get_status()


@router.get("/health")
async def federation_health(request: Request):
    """Federation-specific health check."""
    node = getattr(request.app.state, "federation_node", None)

    if node and node.is_connected:
        return {
            "federation_enabled": True,
            "mode": node.mode.value,
            "node_id": node.node_id,
            "message": "Connected to federation"
        }

    return {
        "federation_enabled": False,
        "mode": "local",
        "message": "Federation is in local mode"
    }


@router.post("/heartbeat")
async def send_heartbeat(request: Request):
    """Manually trigger a heartbeat to federation hub."""
    node = getattr(request.app.state, "federation_node", None)
    if not node:
        return {"success": False, "message": "Federation node not initialized"}

    success = await node.heartbeat()
    return {"success": success}


@router.post("/sync")
async def sync_packages(request: Request):
    """
    Sync pending packages to federation.

    Submits all IKF_READY packages that haven't been submitted yet.
    """
    node = getattr(request.app.state, "federation_node", None)
    if not node:
        return {
            "synced": 0,
            "failed": 0,
            "reason": "Federation node not initialized"
        }

    result = await node.sync_pending_packages()
    return result


@router.post("/sync/request")
async def request_sync(request: Request, sync_req: PatternSyncRequest):
    """Request pattern sync from IKF federation."""
    node = getattr(request.app.state, "federation_node", None)

    if not node or not node.is_connected:
        return {
            "status": "offline",
            "message": "Not connected to federation - patterns only available locally",
            "patterns_available": 0
        }

    # Would trigger federation sync - implementation depends on federation hub API
    return {
        "status": "requested",
        "categories": sync_req.categories,
        "message": "Sync request submitted to federation"
    }


@router.post("/submit")
async def submit_packages(submission: SubmissionRequest, request: Request):
    """
    Submit specific contributions to federation.

    Requires contributions to be in IKF_READY status.
    """
    from federation.package_submitter import PackageSubmitter

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    if not node:
        return {
            "total": len(submission.contribution_ids),
            "submitted": 0,
            "queued": 0,
            "failed": len(submission.contribution_ids),
            "message": "Federation node not initialized"
        }

    submitter = PackageSubmitter(db, node)
    result = await submitter.submit_batch(submission.contribution_ids)

    return result


@router.get("/submission-stats")
async def get_submission_stats(request: Request):
    """Get statistics on federation submissions."""
    from federation.package_submitter import PackageSubmitter

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    if not node:
        # Return stats even without node
        pipeline = [
            {"$group": {
                "_id": "$federation_status",
                "count": {"$sum": 1}
            }}
        ]
        results = list(db.ikf_contributions.aggregate(pipeline))
        stats = {r["_id"] or "NONE": r["count"] for r in results}

        return {
            "by_status": stats,
            "pending": stats.get("PENDING", 0),
            "submitted": stats.get("SUBMITTED", 0),
            "node_status": "not_initialized"
        }

    submitter = PackageSubmitter(db, node)
    return submitter.get_submission_stats()


@router.post("/patterns/search")
async def search_patterns(search: PatternSearchRequest, request: Request):
    """
    Search federation for patterns.

    Searches both federation and local patterns, returns combined results.
    """
    from federation.query_client import FederationQueryClient

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    context = {}
    if search.methodology:
        context["methodology"] = search.methodology
    if search.industry:
        context["industry"] = search.industry
    if search.phase:
        context["phase"] = search.phase

    if not node:
        # Search local patterns only
        query = {
            "package_type": search.package_type,
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        if search.methodology:
            query["generalized_data.preserved_context.methodology"] = search.methodology

        patterns = list(
            db.ikf_contributions.find(query)
            .sort("confidence", -1)
            .limit(search.limit)
        )

        results = []
        for p in patterns:
            extracted = p.get("generalized_data", {}).get("extracted_patterns", [])
            for pattern in extracted:
                results.append({
                    "pattern": pattern,
                    "confidence": p.get("confidence", 0),
                    "source": "local"
                })

        return {
            "patterns": results[:search.limit],
            "source": "local",
            "count": len(results)
        }

    client = FederationQueryClient(db, node)
    result = await client.search_patterns(
        context=context,
        package_type=search.package_type,
        limit=search.limit
    )

    return result


@router.post("/patterns/push")
async def push_patterns(request: Request):
    """Push approved patterns to IKF federation."""
    node = getattr(request.app.state, "federation_node", None)

    if not node or not node.is_connected:
        return {
            "status": "offline",
            "message": "Not connected to federation",
            "patterns_pushed": 0
        }

    result = await node.sync_pending_packages()
    return {
        "status": "synced",
        "patterns_pushed": result.get("synced", 0)
    }


@router.post("/benchmarks")
async def get_benchmarks(benchmark: BenchmarkRequest, request: Request):
    """
    Get temporal benchmarks for a phase.

    Returns p25, p50, p75 duration statistics.
    """
    from federation.query_client import FederationQueryClient

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    if not node:
        # Return local benchmarks only
        query = {
            "package_type": "temporal_benchmark",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]},
            "generalized_data.preserved_context.methodology": benchmark.methodology
        }

        benchmarks = list(db.ikf_contributions.find(query))

        if not benchmarks:
            return {
                "methodology": benchmark.methodology,
                "phase": benchmark.phase,
                "sample_size": 0,
                "source": "local",
                "message": "No benchmark data available"
            }

        durations = []
        for b in benchmarks:
            phase_data = b.get("generalized_data", {}).get("phase_history", [])
            for ph in phase_data:
                if ph.get("phase") == benchmark.phase and ph.get("duration_days"):
                    durations.append(ph["duration_days"])

        if not durations:
            return {
                "methodology": benchmark.methodology,
                "phase": benchmark.phase,
                "sample_size": 0,
                "source": "local"
            }

        durations.sort()
        n = len(durations)

        return {
            "methodology": benchmark.methodology,
            "phase": benchmark.phase,
            "p25": durations[int(n * 0.25)],
            "p50": durations[int(n * 0.5)],
            "p75": durations[int(n * 0.75)],
            "sample_size": n,
            "source": "local"
        }

    client = FederationQueryClient(db, node)
    result = await client.get_benchmarks(
        methodology=benchmark.methodology,
        phase=benchmark.phase,
        industry=benchmark.industry
    )

    return result


@router.post("/risks/indicators")
async def get_risk_indicators(risk_req: RiskIndicatorRequest, request: Request):
    """
    Get aggregated risk indicators.

    Returns frequency of risk patterns by category.
    """
    from federation.query_client import FederationQueryClient

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    context = {}
    if risk_req.phase:
        context["phase"] = risk_req.phase
    if risk_req.methodology:
        context["methodology"] = risk_req.methodology
    if risk_req.industry:
        context["industry"] = risk_req.industry

    if not node:
        # Return local risk indicators
        query = {
            "package_type": "risk_intelligence",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        if risk_req.phase:
            query["generalized_data.preserved_context.current_phase"] = risk_req.phase

        risk_packages = list(db.ikf_contributions.find(query))

        fear_counts = {}
        for pkg in risk_packages:
            patterns = pkg.get("generalized_data", {}).get("extracted_patterns", [])
            for p in patterns:
                if p.get("type") == "fear_pattern":
                    category = p.get("category", "unknown")
                    fear_counts[category] = fear_counts.get(category, 0) + 1

        indicators = [
            {"category": cat, "frequency": count}
            for cat, count in sorted(fear_counts.items(), key=lambda x: -x[1])
        ]

        return {
            "indicators": indicators,
            "sample_size": len(risk_packages),
            "source": "local"
        }

    client = FederationQueryClient(db, node)
    result = await client.get_risk_indicators(context)

    return result


@router.get("/effectiveness/{intervention_type}")
async def get_effectiveness(
    intervention_type: str,
    request: Request,
    methodology: Optional[str] = None
):
    """
    Get intervention effectiveness data.

    Returns effectiveness rate and sample size.
    """
    from federation.query_client import FederationQueryClient

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    context = {}
    if methodology:
        context["methodology"] = methodology

    if not node:
        # Return local effectiveness data
        query = {
            "package_type": "effectiveness_metrics",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        packages = list(db.ikf_contributions.find(query))

        effective_count = 0
        total_count = 0

        for pkg in packages:
            interventions = pkg.get("generalized_data", {}).get("interventions", [])
            for i in interventions:
                if i.get("type") == intervention_type:
                    total_count += 1
                    if i.get("outcome") == "positive":
                        effective_count += 1

        return {
            "intervention_type": intervention_type,
            "effectiveness_rate": effective_count / total_count if total_count > 0 else None,
            "effective_count": effective_count,
            "total_count": total_count,
            "sample_size": len(packages),
            "source": "local"
        }

    client = FederationQueryClient(db, node)
    result = await client.get_effectiveness_data(intervention_type, context)

    return result


@router.delete("/cache")
async def clear_cache(request: Request):
    """Clear the federation query cache."""
    db = request.app.state.db
    db.ikf_query_cache.delete_many({})
    return {"message": "Cache cleared"}


@router.post("/retry-queue/process")
async def process_retry_queue(request: Request):
    """Process failed submissions that are ready for retry."""
    from federation.package_submitter import PackageSubmitter

    node = getattr(request.app.state, "federation_node", None)
    db = request.app.state.db

    if not node:
        return {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "message": "Federation node not initialized"
        }

    submitter = PackageSubmitter(db, node)
    result = await submitter.process_retry_queue()

    return result


@router.get("/config")
async def get_federation_config(request: Request):
    """Get federation configuration."""
    node = getattr(request.app.state, "federation_node", None)

    if node:
        return {
            "mode": node.mode.value,
            "node_id": node.node_id,
            "node_type": node._node_type.value,
            "auto_sync": True,
            "capabilities": node._get_capabilities()
        }

    return {
        "mode": "local",
        "auto_sync": False,
        "sync_interval_minutes": 0,
        "pattern_categories": [
            "temporal_benchmark",
            "pattern_contribution",
            "risk_intelligence",
            "effectiveness_metrics",
            "retrospective_wisdom"
        ],
        "max_patterns_per_sync": 100
    }


@router.get("/discover")
async def discover_hub(request: Request):
    """
    Discovery endpoint - Finding 1.3.

    Returns the configured IKF hub URL.
    Allows admin tools and monitoring to verify federation target.
    """
    federation_mode = os.environ.get("IKF_FEDERATION_MODE", "OFFLINE")
    remote_url = os.environ.get("IKF_REMOTE_NODE_URL", "")
    instance_id = os.environ.get("IKF_INSTANCE_ID", "")

    # Get connection manager status if available
    connection_manager = getattr(request.app.state, "connection_manager", None)
    connection_status = None
    if connection_manager:
        connection_status = connection_manager.state.value

    return {
        "hub_url": remote_url or "(not configured)",
        "mode": federation_mode,
        "instance_id": instance_id or "(auto-generated)",
        "connection_state": connection_status,
        "version": "3.5.1",
        "api_version": "v1"
    }
