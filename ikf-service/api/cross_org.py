"""
Cross-Organization IDTFS API Routes

All cross-org discovery operations require:
- Active trust relationships
- CONTRIBUTOR or STEWARD verification level
- Organization setting: cross_org_discovery_enabled = true

PRIVACY: UNAVAILABLE innovators are NEVER included in results.

Routes:
POST  /api/v1/federation/discovery/search         - Search cross-org profiles
POST  /api/v1/federation/discovery/introduction   - Request introduction
GET   /api/v1/federation/discovery/introduction/{id} - Check introduction status
GET   /api/v1/federation/discovery/prerequisites  - Check discovery prerequisites
"""

import os
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/v1/federation/discovery", tags=["cross-org-discovery"])


class SearchRequest(BaseModel):
    """Request body for cross-org innovator search."""
    required_skills: Optional[List[str]] = None
    methodology_alignment: Optional[str] = None
    industry_focus: Optional[str] = None
    minimum_experience: Optional[int] = None
    max_results: int = 10


class IntroductionRequest(BaseModel):
    """Request body for mediated introduction."""
    target_gii: str
    context: str
    purpose: str


def get_federation_status(request: Request) -> str:
    """Get current federation status."""
    conn_manager = getattr(request.app.state, "connection_manager", None)
    if conn_manager and conn_manager.is_connected:
        return "CONNECTED"
    if os.environ.get("IKF_FEDERATION_MODE") == "simulation":
        return "SIMULATION"
    return "DISCONNECTED"


@router.get("/prerequisites")
async def check_prerequisites(request: Request):
    """
    Check prerequisites for cross-org discovery.

    Returns status of trust relationships, verification level,
    and organization settings.
    """
    cross_org_service = getattr(request.app.state, "cross_org_discovery", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "prerequisites_met": False,
            "federation_status": "SIMULATION",
            "reason": "Cross-org discovery not available in simulation mode"
        }

    if not cross_org_service:
        return {
            "prerequisites_met": False,
            "federation_status": federation_status,
            "reason": "Cross-org discovery service not available"
        }

    prereqs = await cross_org_service._check_prerequisites()
    prereqs["federation_status"] = federation_status
    return prereqs


@router.post("/search")
async def search_cross_org(body: SearchRequest, request: Request):
    """
    Search for innovators across trusted organizations.

    PRIVACY: UNAVAILABLE innovators are never included in results.
    Results are ranked below local equivalents.

    Requires: Active trust + CONTRIBUTOR/STEWARD verification
    """
    cross_org_service = getattr(request.app.state, "cross_org_discovery", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "results": [],
            "total_found": 0,
            "federation_status": "SIMULATION",
            "message": "Cross-org discovery not available in simulation mode"
        }

    if not cross_org_service:
        raise HTTPException(
            status_code=503,
            detail="Cross-org discovery service not available"
        )

    gap_context = {
        "required_skills": body.required_skills,
        "methodology_alignment": body.methodology_alignment,
        "industry_focus": body.industry_focus,
        "minimum_experience": body.minimum_experience
    }

    result = await cross_org_service.discover_cross_org(
        gap_context=gap_context,
        max_results=body.max_results
    )

    result["federation_status"] = federation_status
    return result


@router.post("/introduction")
async def request_introduction(body: IntroductionRequest, request: Request):
    """
    Request a mediated introduction to a cross-org innovator.

    Introductions are MEDIATED through the IKF - no direct contact
    information is exchanged. The target innovator must accept.

    Requires: Active trust + CONTRIBUTOR/STEWARD verification
    """
    cross_org_service = getattr(request.app.state, "cross_org_discovery", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "success": False,
            "federation_status": "SIMULATION",
            "message": "Introductions not available in simulation mode"
        }

    if not cross_org_service:
        raise HTTPException(
            status_code=503,
            detail="Cross-org discovery service not available"
        )

    result = await cross_org_service.request_introduction(
        target_gii=body.target_gii,
        context=body.context,
        purpose=body.purpose
    )

    result["federation_status"] = federation_status
    return result


@router.get("/introduction/{introduction_id}")
async def get_introduction_status(introduction_id: str, request: Request):
    """
    Check the status of an introduction request.

    Statuses: PENDING, ACCEPTED, DECLINED, EXPIRED
    """
    cross_org_service = getattr(request.app.state, "cross_org_discovery", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "status": None,
            "federation_status": "SIMULATION",
            "message": "Introduction status not available in simulation mode"
        }

    if not cross_org_service:
        raise HTTPException(
            status_code=503,
            detail="Cross-org discovery service not available"
        )

    result = await cross_org_service.get_introduction_status(introduction_id)

    if result:
        result["federation_status"] = federation_status
        return result
    else:
        raise HTTPException(status_code=404, detail="Introduction not found")
