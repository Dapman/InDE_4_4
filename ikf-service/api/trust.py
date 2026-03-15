"""
Trust Network API Routes

All trust operations require org admin or federation_admin role.
All operations are audit-logged.

Routes:
POST   /api/v1/federation/trust/request        - Request trust relationship
POST   /api/v1/federation/trust/respond        - Accept/reject trust request
DELETE /api/v1/federation/trust/{id}           - Revoke trust
GET    /api/v1/federation/trust/network        - List all trust relationships
GET    /api/v1/federation/trust/{id}           - Get relationship details
GET    /api/v1/federation/trust/prerequisites  - Check trust prerequisites
GET    /api/v1/federation/reputation           - Get org reputation
GET    /api/v1/federation/reputation/leaderboard - Anonymized leaderboard
POST   /api/v1/federation/reputation/feedback  - Submit contribution feedback
"""

import os
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/federation/trust", tags=["trust"])


class TrustRequestBody(BaseModel):
    """Request body for trust relationship request."""
    target_org_id: str
    relationship_type: str = "BILATERAL"
    sharing_level: str = "INDUSTRY"
    justification: Optional[str] = None
    expiration_date: Optional[str] = None


class TrustResponseBody(BaseModel):
    """Request body for trust relationship response."""
    relationship_id: str
    accept: bool
    terms: Optional[Dict[str, Any]] = None


class TrustRevokeBody(BaseModel):
    """Request body for trust revocation."""
    reason: Optional[str] = None


class FeedbackBody(BaseModel):
    """Request body for contribution feedback."""
    contribution_id: str
    feedback_type: str  # "applied", "dismissed", "validated", "disputed"
    effectiveness_rating: Optional[int] = None  # 1-5
    comments: Optional[str] = None


def get_federation_status(request: Request) -> str:
    """Get current federation status."""
    conn_manager = getattr(request.app.state, "connection_manager", None)
    if conn_manager and conn_manager.is_connected:
        return "CONNECTED"
    if os.environ.get("IKF_FEDERATION_MODE") == "simulation":
        return "SIMULATION"
    return "DISCONNECTED"


@router.post("/request")
async def request_trust(body: TrustRequestBody, request: Request):
    """
    Request a trust relationship with another organization.

    Requires: federation_admin permission
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "status": "error",
            "message": "Trust management not available in simulation mode"
        }

    if not trust_manager:
        raise HTTPException(status_code=503, detail="Trust manager not available")

    result = await trust_manager.request_trust(
        target_org_id=body.target_org_id,
        relationship_type=body.relationship_type,
        sharing_level=body.sharing_level,
        justification=body.justification,
        expiration_date=body.expiration_date
    )

    if result:
        return {
            "status": "success",
            "relationship": result
        }
    else:
        raise HTTPException(status_code=500, detail="Trust request failed")


@router.post("/respond")
async def respond_to_trust(body: TrustResponseBody, request: Request):
    """
    Accept or reject a trust relationship request.

    Requires: federation_admin permission
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "status": "error",
            "message": "Trust management not available in simulation mode"
        }

    if not trust_manager:
        raise HTTPException(status_code=503, detail="Trust manager not available")

    result = await trust_manager.respond_to_trust(
        relationship_id=body.relationship_id,
        accept=body.accept,
        terms=body.terms
    )

    if result:
        return {
            "status": "success",
            "relationship": result
        }
    else:
        raise HTTPException(status_code=500, detail="Trust response failed")


@router.delete("/{relationship_id}")
async def revoke_trust(relationship_id: str, request: Request,
                       reason: Optional[str] = None):
    """
    Revoke a trust relationship.

    Immediate effect: cross-org features disabled for this partner.

    Requires: federation_admin permission
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "status": "error",
            "message": "Trust management not available in simulation mode"
        }

    if not trust_manager:
        raise HTTPException(status_code=503, detail="Trust manager not available")

    success = await trust_manager.revoke_trust(relationship_id, reason)

    if success:
        return {
            "status": "success",
            "message": f"Trust relationship {relationship_id} revoked"
        }
    else:
        raise HTTPException(status_code=500, detail="Trust revocation failed")


@router.get("/network")
async def get_trust_network(request: Request):
    """
    Get the organization's complete trust network.

    Returns all trust relationships (active, proposed, expired).
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "relationships": [],
            "federation_status": "SIMULATION",
            "message": "Trust network not available in simulation mode"
        }

    if not trust_manager:
        return {
            "relationships": [],
            "federation_status": federation_status,
            "message": "Trust manager not available"
        }

    relationships = await trust_manager.get_trust_network()

    return {
        "relationships": relationships,
        "federation_status": federation_status,
        "count": len(relationships),
        "active_count": sum(1 for r in relationships if r.get("status") == "ACTIVE")
    }


@router.get("/prerequisites")
async def check_trust_prerequisites(request: Request):
    """
    Check prerequisites for trust-dependent features.

    Returns status of cross-org IDTFS and partner sharing availability.
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "has_active_trust": False,
            "active_trust_count": 0,
            "can_use_cross_org_idtfs": False,
            "can_use_partner_sharing": False,
            "verification_level": "N/A",
            "federation_status": "SIMULATION"
        }

    if not trust_manager:
        return {
            "has_active_trust": False,
            "active_trust_count": 0,
            "can_use_cross_org_idtfs": False,
            "can_use_partner_sharing": False,
            "verification_level": "UNKNOWN",
            "federation_status": federation_status
        }

    prerequisites = await trust_manager.check_trust_prerequisites()
    prerequisites["federation_status"] = federation_status
    return prerequisites


@router.get("/{relationship_id}")
async def get_trust_relationship(relationship_id: str, request: Request):
    """
    Get details of a specific trust relationship.
    """
    trust_manager = getattr(request.app.state, "trust_manager", None)

    if not trust_manager:
        raise HTTPException(status_code=503, detail="Trust manager not available")

    relationship = await trust_manager.get_relationship(relationship_id)

    if relationship:
        return relationship
    else:
        raise HTTPException(status_code=404, detail="Relationship not found")


# =========================================================================
# REPUTATION ROUTES
# =========================================================================

reputation_router = APIRouter(prefix="/api/v1/federation/reputation", tags=["reputation"])


@reputation_router.get("")
async def get_org_reputation(request: Request):
    """
    Get the organization's reputation score.

    Returns reputation components and overall score.
    """
    reputation_tracker = getattr(request.app.state, "reputation_tracker", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "data": None,
            "federation_status": "SIMULATION",
            "message": "Reputation not available in simulation mode"
        }

    if not reputation_tracker:
        return {
            "data": None,
            "federation_status": federation_status,
            "message": "Reputation tracker not available"
        }

    reputation = await reputation_tracker.get_org_reputation()

    return {
        "data": reputation,
        "federation_status": federation_status
    }


@reputation_router.get("/leaderboard")
async def get_reputation_leaderboard(request: Request):
    """
    Get anonymized reputation leaderboard.

    Shows relative rankings without identifying organizations.
    """
    reputation_tracker = getattr(request.app.state, "reputation_tracker", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "entries": [],
            "federation_status": "SIMULATION",
            "message": "Leaderboard not available in simulation mode"
        }

    if not reputation_tracker:
        return {
            "entries": [],
            "federation_status": federation_status,
            "message": "Reputation tracker not available"
        }

    leaderboard = await reputation_tracker.get_leaderboard()

    return {
        "entries": leaderboard or [],
        "federation_status": federation_status
    }


@reputation_router.post("/feedback")
async def submit_feedback(body: FeedbackBody, request: Request):
    """
    Submit quality feedback for a received contribution.

    This feedback helps the IKF calculate contributor reputation.
    """
    reputation_tracker = getattr(request.app.state, "reputation_tracker", None)
    federation_status = get_federation_status(request)

    if federation_status == "SIMULATION":
        return {
            "status": "error",
            "message": "Feedback not available in simulation mode"
        }

    if not reputation_tracker:
        raise HTTPException(status_code=503, detail="Reputation tracker not available")

    success = await reputation_tracker.submit_contribution_feedback(
        contribution_id=body.contribution_id,
        feedback_type=body.feedback_type,
        effectiveness_rating=body.effectiveness_rating,
        comments=body.comments
    )

    if success:
        return {
            "status": "success",
            "message": "Feedback submitted"
        }
    else:
        raise HTTPException(status_code=500, detail="Feedback submission failed")
