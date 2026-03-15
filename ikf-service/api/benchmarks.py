"""
Benchmark API Routes - Dashboard & Coaching Access

These routes serve cached benchmark data to the Org Portfolio Dashboard
and to the coaching context assembler. They ONLY read from the local
ikf_benchmarks cache - they never call the IKF directly.

All endpoints require portfolio_dashboard_access permission
(consistent with v3.4 Org Portfolio access control).

Routes:
- GET  /api/v1/org/{org_id}/benchmarks          Full benchmarking panel data
- GET  /api/v1/org/{org_id}/benchmarks/industry  Industry-specific benchmarks
- GET  /api/v1/org/{org_id}/benchmarks/methodology  Methodology effectiveness
- GET  /api/v1/org/{org_id}/benchmarks/percentile  Organization's percentile ranking
- GET  /api/v1/org/{org_id}/benchmarks/trends  Historical benchmark trends
"""

import os
from fastapi import APIRouter, Depends, Request, HTTPException
from datetime import datetime, timezone
from typing import Optional

router = APIRouter(prefix="/api/v1/org", tags=["benchmarks"])


def get_federation_status(request: Request) -> str:
    """Get current federation status."""
    conn_manager = getattr(request.app.state, "connection_manager", None)
    if conn_manager and conn_manager.is_connected:
        return "CONNECTED"
    if os.environ.get("IKF_FEDERATION_MODE") == "simulation":
        return "SIMULATION"
    return "DISCONNECTED"


def check_stale(fetched_at: Optional[datetime]) -> bool:
    """Check if data is stale (> 24 hours old)."""
    if not fetched_at:
        return True
    age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    stale_threshold = int(os.environ.get("BENCHMARK_STALE_THRESHOLD", "86400"))
    return age > stale_threshold


@router.get("/{org_id}/benchmarks")
async def get_all_benchmarks(org_id: str, request: Request):
    """
    Get full benchmarking panel data for Org Portfolio Dashboard.

    Returns industry, methodology, percentile, and trend data.
    Includes staleness indicator and federation status.

    Permission: portfolio_dashboard_access
    """
    benchmark_engine = getattr(request.app.state, "benchmark_engine", None)
    federation_status = get_federation_status(request)

    # Simulation mode or no benchmarks
    if federation_status == "SIMULATION" or not benchmark_engine:
        return {
            "data": None,
            "message": "No federation data available",
            "federation_status": federation_status,
            "stale": False
        }

    try:
        all_data = await benchmark_engine.get_all_benchmarks()
        return {
            "data": {
                "industry": all_data.get("industry"),
                "methodology": all_data.get("methodology"),
                "comparison": all_data.get("comparison"),
                "trends": all_data.get("trends")
            },
            "fetched_at": all_data.get("fetched_at"),
            "source": "ikf_federation",
            "federation_status": all_data.get("federation_status", federation_status),
            "stale": all_data.get("stale", True)
        }
    except Exception as e:
        return {
            "data": None,
            "message": f"Error retrieving benchmarks: {str(e)}",
            "federation_status": federation_status,
            "stale": True
        }


@router.get("/{org_id}/benchmarks/industry")
async def get_industry_benchmarks(org_id: str, request: Request,
                                   naics_code: Optional[str] = None):
    """
    Get industry-specific benchmark comparisons.

    Query params:
    - naics_code: Specific NAICS code (optional, defaults to org's primary)

    Permission: portfolio_dashboard_access
    """
    benchmark_engine = getattr(request.app.state, "benchmark_engine", None)
    db = request.app.state.db
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION" or not benchmark_engine:
        return {
            "data": None,
            "message": "No federation data available",
            "federation_status": federation_status,
            "stale": False
        }

    # Get NAICS code
    if not naics_code:
        fed_state = db.ikf_federation_state.find_one({"type": "registration"})
        naics_code = fed_state.get("primary_naics") if fed_state else None

    if not naics_code:
        return {
            "data": None,
            "message": "No industry code configured",
            "federation_status": federation_status,
            "stale": False
        }

    # Query cached benchmark
    benchmark = db.ikf_benchmarks.find_one(
        {"type": "industry", "key": naics_code}
    )

    if not benchmark:
        return {
            "data": None,
            "message": f"No benchmark data for industry {naics_code}",
            "federation_status": federation_status,
            "stale": True
        }

    return {
        "data": benchmark.get("data"),
        "fetched_at": benchmark.get("fetched_at"),
        "source": "ikf_federation",
        "federation_status": federation_status,
        "stale": check_stale(benchmark.get("fetched_at"))
    }


@router.get("/{org_id}/benchmarks/methodology")
async def get_methodology_benchmarks(org_id: str, request: Request,
                                       archetype_id: Optional[str] = None):
    """
    Get methodology effectiveness vs InDEVerse averages.

    Query params:
    - archetype_id: Specific archetype (optional, returns all if omitted)

    Permission: portfolio_dashboard_access
    """
    benchmark_engine = getattr(request.app.state, "benchmark_engine", None)
    db = request.app.state.db
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION" or not benchmark_engine:
        return {
            "data": None,
            "message": "No federation data available",
            "federation_status": federation_status,
            "stale": False
        }

    if archetype_id:
        # Single archetype
        benchmark = db.ikf_benchmarks.find_one(
            {"type": "methodology", "key": archetype_id}
        )
        if not benchmark:
            return {
                "data": None,
                "message": f"No benchmark data for methodology {archetype_id}",
                "federation_status": federation_status,
                "stale": True
            }
        return {
            "data": benchmark.get("data"),
            "fetched_at": benchmark.get("fetched_at"),
            "source": "ikf_federation",
            "federation_status": federation_status,
            "stale": check_stale(benchmark.get("fetched_at"))
        }

    # All methodology benchmarks
    benchmarks = list(db.ikf_benchmarks.find({"type": "methodology"}))
    if not benchmarks:
        return {
            "data": [],
            "message": "No methodology benchmark data available",
            "federation_status": federation_status,
            "stale": True
        }

    return {
        "data": [
            {"archetype_id": b.get("key"), "metrics": b.get("data")}
            for b in benchmarks
        ],
        "fetched_at": benchmarks[0].get("fetched_at") if benchmarks else None,
        "source": "ikf_federation",
        "federation_status": federation_status,
        "stale": check_stale(benchmarks[0].get("fetched_at")) if benchmarks else True
    }


@router.get("/{org_id}/benchmarks/percentile")
async def get_percentile_ranking(org_id: str, request: Request):
    """
    Get organization's percentile ranking across all metrics.

    Returns percentile position (0-100) for each benchmark metric,
    comparing against industry and global baselines.

    Permission: portfolio_dashboard_access
    """
    benchmark_engine = getattr(request.app.state, "benchmark_engine", None)
    db = request.app.state.db
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION" or not benchmark_engine:
        return {
            "data": None,
            "message": "No federation data available",
            "federation_status": federation_status,
            "stale": False
        }

    benchmark = db.ikf_benchmarks.find_one(
        {"type": "comparison", "key": "latest"}
    )

    if not benchmark:
        return {
            "data": None,
            "message": "No percentile ranking data available",
            "federation_status": federation_status,
            "stale": True
        }

    return {
        "data": benchmark.get("data"),
        "fetched_at": benchmark.get("fetched_at"),
        "source": "ikf_federation",
        "federation_status": federation_status,
        "stale": check_stale(benchmark.get("fetched_at"))
    }


@router.get("/{org_id}/benchmarks/trends")
async def get_benchmark_trends(org_id: str, request: Request):
    """
    Get historical benchmark trends.

    Shows how industry and global baselines have evolved over time.

    Permission: portfolio_dashboard_access
    """
    benchmark_engine = getattr(request.app.state, "benchmark_engine", None)
    db = request.app.state.db
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION" or not benchmark_engine:
        return {
            "data": None,
            "message": "No federation data available",
            "federation_status": federation_status,
            "stale": False
        }

    benchmark = db.ikf_benchmarks.find_one(
        {"type": "trends", "key": "latest"}
    )

    if not benchmark:
        return {
            "data": None,
            "message": "No trend data available",
            "federation_status": federation_status,
            "stale": True
        }

    return {
        "data": benchmark.get("data"),
        "fetched_at": benchmark.get("fetched_at"),
        "source": "ikf_federation",
        "federation_status": federation_status,
        "stale": check_stale(benchmark.get("fetched_at"))
    }
