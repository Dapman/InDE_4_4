"""
InDE MVP v3.4 - Portfolio Dashboard API Routes
Endpoints for Org-Level Portfolio Dashboard.

Endpoints:
- GET /orgs/{org_id}/portfolio/dashboard - Full dashboard with all panels
- GET /orgs/{org_id}/portfolio/panels/{panel_type} - Get specific panel
- POST /orgs/{org_id}/portfolio/dashboard/refresh - Force refresh dashboard
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from core.database import db
from portfolio.dashboard import get_portfolio_dashboard, PanelType
from middleware.rbac import require_permission

logger = logging.getLogger("inde.api.portfolio_dashboard")

router = APIRouter(tags=["portfolio-dashboard"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DashboardPanelResponse(BaseModel):
    """Dashboard panel response."""
    panel_type: str
    title: str
    data: Dict[str, Any]
    updated_at: str
    cache_duration_seconds: int


class FullDashboardResponse(BaseModel):
    """Full dashboard response with all panels."""
    org_id: str
    generated_at: str
    panels: Dict[str, DashboardPanelResponse]


class RefreshDashboardRequest(BaseModel):
    """Request to refresh dashboard."""
    panels: Optional[List[str]] = Field(None, description="Specific panels to refresh (all if not specified)")


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def verify_org_access(org_id: str, current_user: Dict) -> Dict:
    """Verify user has access to organization."""
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/portfolio/dashboard", response_model=FullDashboardResponse)
async def get_full_dashboard(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get the full portfolio dashboard with all 7 panels.

    Panels:
    1. portfolio_health - Aggregate health across all pursuits
    2. stage_distribution - Pursuits by methodology stage
    3. resource_allocation - Team capacity and allocation
    4. innovation_pipeline - Pipeline flow and velocity
    5. risk_radar - Aggregated risk signals
    6. convergence_insights - Coaching convergence patterns
    7. talent_formation - IDTFS insights and formation activity

    Returns cached data if available (5 minute cache).
    """
    membership = await verify_org_access(org_id, current_user)

    # Check permission for portfolio dashboard access
    if not require_permission(current_user["user_id"], org_id, "can_view_portfolio_dashboard"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied: can_view_portfolio_dashboard required"
        )

    dashboard = get_portfolio_dashboard()
    result = dashboard.get_full_dashboard(org_id)

    # Convert to response format
    panels_response = {}
    for panel_type, panel_data in result.get("panels", {}).items():
        panels_response[panel_type] = DashboardPanelResponse(
            panel_type=panel_data["panel_type"],
            title=panel_data["title"],
            data=panel_data["data"],
            updated_at=panel_data["updated_at"],
            cache_duration_seconds=panel_data["cache_duration_seconds"]
        )

    logger.info(f"Portfolio dashboard retrieved for org {org_id} by user {current_user['user_id']}")

    return FullDashboardResponse(
        org_id=result["org_id"],
        generated_at=result["generated_at"],
        panels=panels_response
    )


@router.get("/orgs/{org_id}/portfolio/panels/{panel_type}", response_model=DashboardPanelResponse)
async def get_dashboard_panel(
    org_id: str,
    panel_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific dashboard panel.

    Valid panel types:
    - portfolio_health
    - stage_distribution
    - resource_allocation
    - innovation_pipeline
    - risk_radar
    - convergence_insights
    - talent_formation
    """
    await verify_org_access(org_id, current_user)

    # Validate panel type
    try:
        panel_type_enum = PanelType(panel_type)
    except ValueError:
        valid_types = [pt.value for pt in PanelType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid panel type. Must be one of: {valid_types}"
        )

    # Check permission
    if not require_permission(current_user["user_id"], org_id, "can_view_portfolio_dashboard"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied: can_view_portfolio_dashboard required"
        )

    dashboard = get_portfolio_dashboard()
    panel = dashboard.get_panel(org_id, panel_type_enum)

    return DashboardPanelResponse(
        panel_type=panel.panel_type.value,
        title=panel.title,
        data=panel.data,
        updated_at=panel.updated_at.isoformat(),
        cache_duration_seconds=panel.cache_duration_seconds
    )


@router.post("/orgs/{org_id}/portfolio/dashboard/refresh", response_model=FullDashboardResponse)
async def refresh_dashboard(
    org_id: str,
    request: RefreshDashboardRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Force refresh the portfolio dashboard.

    Optionally specify which panels to refresh.
    """
    membership = await verify_org_access(org_id, current_user)

    # Check permission
    if not require_permission(current_user["user_id"], org_id, "can_view_portfolio_dashboard"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied: can_view_portfolio_dashboard required"
        )

    dashboard = get_portfolio_dashboard()

    if request.panels:
        # Refresh specific panels
        result = {"org_id": org_id, "generated_at": datetime.now(timezone.utc).isoformat(), "panels": {}}
        for panel_name in request.panels:
            try:
                panel_type = PanelType(panel_name)
                panel = dashboard.get_panel(org_id, panel_type, force_refresh=True)
                result["panels"][panel_name] = panel.to_dict()
            except ValueError:
                continue  # Skip invalid panel types
    else:
        # Refresh all panels
        result = dashboard.get_full_dashboard(org_id, force_refresh=True)

    # Convert to response format
    panels_response = {}
    for panel_type, panel_data in result.get("panels", {}).items():
        panels_response[panel_type] = DashboardPanelResponse(
            panel_type=panel_data["panel_type"],
            title=panel_data["title"],
            data=panel_data["data"],
            updated_at=panel_data["updated_at"],
            cache_duration_seconds=panel_data["cache_duration_seconds"]
        )

    logger.info(f"Portfolio dashboard refreshed for org {org_id} by user {current_user['user_id']}")

    return FullDashboardResponse(
        org_id=result["org_id"],
        generated_at=result["generated_at"],
        panels=panels_response
    )


# =============================================================================
# PANEL-SPECIFIC SUMMARY ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/portfolio/health-summary")
async def get_health_summary(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get portfolio health summary (quick endpoint).

    Returns key health metrics without full dashboard.
    """
    await verify_org_access(org_id, current_user)

    dashboard = get_portfolio_dashboard()
    panel = dashboard.get_panel(org_id, PanelType.PORTFOLIO_HEALTH)

    metrics = panel.data.get("metrics", {})

    return {
        "org_id": org_id,
        "total_pursuits": metrics.get("total_pursuits", 0),
        "active_pursuits": metrics.get("active_pursuits", 0),
        "average_health_score": metrics.get("average_health_score", 0),
        "health_distribution": metrics.get("health_distribution", {}),
        "updated_at": panel.updated_at.isoformat()
    }


@router.get("/orgs/{org_id}/portfolio/pipeline-summary")
async def get_pipeline_summary(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get innovation pipeline summary (quick endpoint).

    Returns pipeline stages and velocity metrics.
    """
    await verify_org_access(org_id, current_user)

    dashboard = get_portfolio_dashboard()
    panel = dashboard.get_panel(org_id, PanelType.INNOVATION_PIPELINE)

    return {
        "org_id": org_id,
        "pipeline_stages": panel.data.get("pipeline_stages", {}),
        "velocity_metrics": panel.data.get("velocity_metrics", {}),
        "funnel_conversion": panel.data.get("funnel_conversion", {}),
        "updated_at": panel.updated_at.isoformat()
    }


@router.get("/orgs/{org_id}/portfolio/risk-summary")
async def get_risk_summary(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get risk radar summary (quick endpoint).

    Returns portfolio risk score and high-risk pursuits.
    """
    await verify_org_access(org_id, current_user)

    dashboard = get_portfolio_dashboard()
    panel = dashboard.get_panel(org_id, PanelType.RISK_RADAR)

    return {
        "org_id": org_id,
        "portfolio_risk_score": panel.data.get("portfolio_risk_score", 1.0),
        "high_risk_count": len(panel.data.get("high_risk_pursuits", [])),
        "risk_by_category": panel.data.get("risk_by_category", {}),
        "emerging_risks_count": len(panel.data.get("emerging_risks", [])),
        "updated_at": panel.updated_at.isoformat()
    }
