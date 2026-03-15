"""
InDE IKF Service v3.5.2 - Contribution Management API
Handles IKF contribution package CRUD, review workflows, and auto-preparation.

v3.5.2: Added outbox integration for guaranteed delivery when contributions
are approved to IKF_READY status.

Package Types:
- temporal_benchmark: Phase timing patterns
- pattern_contribution: Success/failure patterns
- risk_intelligence: Risk indicators
- effectiveness_metrics: Intervention effectiveness
- retrospective_wisdom: Retrospective learnings
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger("inde.ikf.contributions")

router = APIRouter(prefix="/ikf", tags=["contributions"])


class ContributionPreviewResponse(BaseModel):
    """Preview response with side-by-side comparison."""
    contribution_id: str
    package_type: str
    status: str
    auto_triggered: bool
    preview: dict  # {original_summary, generalized_summary, side_by_side}
    pii_scan: dict
    confidence: float
    warnings: List[str]


class ReviewRequest(BaseModel):
    """Review decision request."""
    approved: bool
    notes: Optional[str] = None
    override_pii_warnings: bool = False


class PrepareRequest(BaseModel):
    """Manual preparation request."""
    pursuit_id: str
    package_type: str


@router.get("/contributions")
async def list_contributions(
    request: Request,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    package_type: Optional[str] = None,
    limit: int = 50
):
    """List contributions with optional status/user filtering."""
    db = request.app.state.db
    query = {}
    if status:
        query["status"] = status
    if user_id:
        query["user_id"] = user_id
    if package_type:
        query["package_type"] = package_type

    contributions = list(
        db.ikf_contributions.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )

    # Convert ObjectId to str for JSON serialization
    for c in contributions:
        c["_id"] = str(c["_id"])

    return {"contributions": contributions, "count": len(contributions)}


@router.get("/contributions/{contribution_id}")
async def get_contribution(contribution_id: str, request: Request):
    """Get a specific contribution package."""
    db = request.app.state.db
    doc = db.ikf_contributions.find_one({"contribution_id": contribution_id})
    if not doc:
        raise HTTPException(404, "Contribution not found")

    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/contributions/{contribution_id}/preview")
async def get_preview(contribution_id: str, request: Request):
    """Get side-by-side original vs. generalized preview for review."""
    db = request.app.state.db
    doc = db.ikf_contributions.find_one({"contribution_id": contribution_id})
    if not doc:
        raise HTTPException(404, "Contribution not found")

    # Build preview structure
    preview = {
        "original_summary": doc.get("original_summary", ""),
        "generalized_summary": doc.get("generalized_summary", ""),
        "transformations_log": doc.get("transformations_log", []),
        "side_by_side": {
            "original": doc.get("original_data", {}),
            "generalized": doc.get("generalized_data", {})
        }
    }

    return ContributionPreviewResponse(
        contribution_id=contribution_id,
        package_type=doc.get("package_type", "unknown"),
        status=doc.get("status", "DRAFT"),
        auto_triggered=doc.get("auto_triggered", False),
        preview=preview,
        pii_scan=doc.get("pii_scan", {"passed": True, "warnings": [], "high_confidence_flags": []}),
        confidence=doc.get("confidence", 0.0),
        warnings=doc.get("warnings", [])
    )


@router.post("/contributions/{contribution_id}/review")
async def review_contribution(contribution_id: str, review: ReviewRequest, request: Request):
    """
    Submit human review decision.

    CRITICAL: This is the human-in-the-loop gate.
    No package reaches IKF_READY without explicit approval.
    """
    db = request.app.state.db
    doc = db.ikf_contributions.find_one({"contribution_id": contribution_id})
    if not doc:
        raise HTTPException(404, "Contribution not found")

    if doc["status"] not in ("DRAFT", "REVIEWED"):
        raise HTTPException(400, f"Cannot review contribution in {doc['status']} status")

    # Check PII override requirement
    pii_scan = doc.get("pii_scan", {})
    if review.approved and pii_scan.get("high_confidence_flags"):
        if not review.override_pii_warnings:
            raise HTTPException(
                400,
                "Contribution has HIGH-confidence PII flags. "
                "Set override_pii_warnings=true to approve anyway."
            )

    new_status = "IKF_READY" if review.approved else "REJECTED"

    db.ikf_contributions.update_one(
        {"contribution_id": contribution_id},
        {"$set": {
            "status": new_status,
            "review_notes": review.notes,
            "reviewed_at": datetime.now(timezone.utc),
            "pii_override": review.override_pii_warnings
        }}
    )

    # Publish review event
    try:
        publisher = request.app.state.publisher
        await publisher.publish_ikf_event("ikf.package.reviewed", {
            "contribution_id": contribution_id,
            "status": new_status,
            "user_id": doc.get("user_id"),
            "pursuit_id": doc.get("pursuit_id")
        })
    except Exception as e:
        logger.warning(f"Failed to publish review event: {e}")

    # v3.5.2: Enqueue for federation submission when approved
    if review.approved:
        outbox = getattr(request.app.state, "contribution_outbox", None)
        if outbox:
            try:
                await outbox.enqueue(contribution_id)
                logger.info(f"Contribution {contribution_id} enqueued for federation")
            except Exception as e:
                logger.warning(f"Failed to enqueue contribution: {e}")

    logger.info(f"Contribution {contribution_id} reviewed: {new_status}")
    return {"contribution_id": contribution_id, "status": new_status}


@router.post("/contributions/prepare")
async def manual_prepare(prepare: PrepareRequest, request: Request):
    """Manually trigger contribution preparation for a pursuit."""
    from contribution.preparer import IKFContributionPreparer

    db = request.app.state.db
    publisher = request.app.state.publisher

    preparer = IKFContributionPreparer(db, publisher)
    result = await preparer.prepare(
        pursuit_id=prepare.pursuit_id,
        package_type=prepare.package_type,
        auto_triggered=False
    )

    return result


@router.get("/contributions/stats")
async def contribution_stats(request: Request, user_id: Optional[str] = None):
    """Contribution statistics: counts by status, type, and time period."""
    db = request.app.state.db

    pipeline = [
        {"$group": {
            "_id": {"status": "$status", "package_type": "$package_type"},
            "count": {"$sum": 1}
        }}
    ]

    if user_id:
        pipeline.insert(0, {"$match": {"user_id": user_id}})

    results = list(db.ikf_contributions.aggregate(pipeline))

    # Also get totals by status
    status_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    if user_id:
        status_pipeline.insert(0, {"$match": {"user_id": user_id}})

    status_totals = {r["_id"]: r["count"] for r in db.ikf_contributions.aggregate(status_pipeline)}

    return {
        "by_status_and_type": results,
        "by_status": status_totals,
        "total": sum(status_totals.values())
    }


@router.get("/contributions/pending")
async def list_pending_reviews(request: Request, user_id: Optional[str] = None):
    """Get contributions pending human review."""
    db = request.app.state.db

    query = {"status": "DRAFT"}
    if user_id:
        query["user_id"] = user_id

    pending = list(db.ikf_contributions.find(query).sort("created_at", -1).limit(20))

    for p in pending:
        p["_id"] = str(p["_id"])

    return {"count": len(pending), "contributions": pending}
