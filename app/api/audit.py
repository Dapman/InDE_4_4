"""
InDE MVP v3.4 - Audit API Routes
SOC 2-ready audit log query and export endpoints.

Endpoints:
- GET /orgs/{org_id}/audit - Query audit events
- GET /orgs/{org_id}/audit/export - Export audit events
- GET /orgs/{org_id}/audit/{event_id} - Get single audit event
- GET /orgs/{org_id}/audit/correlation/{correlation_id} - Get correlated events

All audit endpoints require can_manage_audit_logs permission.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import csv
import io
import logging

from core.database import db
from middleware.rbac import check_user_has_permission
from events.audit import audit_data_export

logger = logging.getLogger("inde.api.audit")

router = APIRouter(prefix="/orgs/{org_id}/audit", tags=["audit"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AuditEventResponse(BaseModel):
    """Audit event details response."""
    event_id: str
    timestamp: datetime
    event_type: str
    actor_id: str
    actor_role: Optional[str] = None
    org_id: Optional[str] = None
    resource_type: str
    resource_id: str
    action_detail: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    outcome: str
    correlation_id: Optional[str] = None


class AuditQueryResponse(BaseModel):
    """Paginated audit query response."""
    events: List[AuditEventResponse]
    total_count: int
    offset: int
    limit: int
    has_more: bool


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_audit_access(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Verify user has audit log access permission."""
    user_id = current_user.get("user_id")
    if not check_user_has_permission(user_id, org_id, "can_manage_audit_logs"):
        raise HTTPException(status_code=403, detail="Audit log access permission required")
    return current_user


# =============================================================================
# QUERY ENDPOINT
# =============================================================================

@router.get("", response_model=AuditQueryResponse)
async def query_audit_events(
    org_id: str,
    actor_id: Optional[str] = Query(None, description="Filter by actor"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (SUCCESS|FAILURE|DENIED)"),
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict = Depends(require_audit_access)
):
    """
    Query audit events with filtering and pagination.

    Filters:
    - actor_id: User who performed the action
    - event_type: Type of audit event (AUTH_LOGIN, RESOURCE_ACCESS, etc.)
    - resource_type: Type of affected resource
    - resource_id: ID of affected resource
    - outcome: SUCCESS, FAILURE, or DENIED
    - start_date / end_date: Date range filter

    Requires can_manage_audit_logs permission.
    """
    # Build query
    events = db.get_audit_events(
        org_id=org_id,
        actor_id=actor_id,
        event_type=event_type,
        resource_type=resource_type,
        start_time=start_date,
        end_time=end_date,
        limit=limit + 1,  # Get one extra to check has_more
        offset=offset
    )

    # Filter by additional criteria not in db method
    if outcome:
        events = [e for e in events if e.get("outcome") == outcome]
    if resource_id:
        events = [e for e in events if e.get("resource_id") == resource_id]

    # Check if there are more results
    has_more = len(events) > limit
    if has_more:
        events = events[:limit]

    # Get total count (expensive for large datasets)
    total_count = len(db.get_audit_events(
        org_id=org_id,
        actor_id=actor_id,
        event_type=event_type,
        resource_type=resource_type,
        start_time=start_date,
        end_time=end_date,
        limit=10000,  # Cap for performance
        offset=0
    ))

    return AuditQueryResponse(
        events=[AuditEventResponse(**e) for e in events],
        total_count=total_count,
        offset=offset,
        limit=limit,
        has_more=has_more
    )


# =============================================================================
# SINGLE EVENT ENDPOINT
# =============================================================================

@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    org_id: str,
    event_id: str,
    current_user: Dict = Depends(require_audit_access)
):
    """
    Get a single audit event by ID.

    Requires can_manage_audit_logs permission.
    """
    # Query for the specific event
    events = db.get_audit_events(org_id=org_id, limit=10000, offset=0)
    event = next((e for e in events if e.get("event_id") == event_id), None)

    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")

    return AuditEventResponse(**event)


# =============================================================================
# CORRELATION ENDPOINT
# =============================================================================

@router.get("/correlation/{correlation_id}", response_model=List[AuditEventResponse])
async def get_correlated_events(
    org_id: str,
    correlation_id: str,
    current_user: Dict = Depends(require_audit_access)
):
    """
    Get all audit events with the same correlation ID.

    Useful for tracking multi-step operations.
    Requires can_manage_audit_logs permission.
    """
    events = db.get_audit_event_by_correlation(correlation_id)

    # Filter to only this org's events
    events = [e for e in events if e.get("org_id") == org_id]

    if not events:
        raise HTTPException(status_code=404, detail="No events found for correlation ID")

    return [AuditEventResponse(**e) for e in events]


# =============================================================================
# EXPORT ENDPOINT
# =============================================================================

@router.get("/export")
async def export_audit_events(
    org_id: str,
    format: str = Query("csv", description="Export format (csv|json)"),
    actor_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    max_records: int = Query(10000, ge=1, le=100000),
    current_user: Dict = Depends(require_audit_access)
):
    """
    Export audit events to CSV or JSON.

    Maximum 100,000 records per export.
    Requires can_manage_audit_logs permission.

    This endpoint creates an audit event for the export itself.
    """
    # Fetch events
    events = db.get_audit_events(
        org_id=org_id,
        actor_id=actor_id,
        event_type=event_type,
        resource_type=resource_type,
        start_time=start_date,
        end_time=end_date,
        limit=max_records,
        offset=0
    )

    # Create audit event for the export
    audit_data_export(
        actor_id=current_user["user_id"],
        export_type="audit_events",
        org_id=org_id,
        record_count=len(events),
        actor_role=current_user.get("role")
    )

    if format == "json":
        import json
        content = json.dumps([_serialize_event(e) for e in events], indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_export_{org_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
            }
        )
    else:
        # CSV export
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "event_id", "timestamp", "event_type", "actor_id", "actor_role",
            "resource_type", "resource_id", "outcome", "correlation_id",
            "ip_address", "action_detail"
        ])
        writer.writeheader()
        for event in events:
            writer.writerow(_flatten_event(event))

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_export_{org_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
            }
        )


def _serialize_event(event: Dict) -> Dict:
    """Serialize event for JSON export."""
    result = dict(event)
    if "timestamp" in result and isinstance(result["timestamp"], datetime):
        result["timestamp"] = result["timestamp"].isoformat()
    return result


def _flatten_event(event: Dict) -> Dict:
    """Flatten event for CSV export."""
    result = {
        "event_id": event.get("event_id", ""),
        "timestamp": event.get("timestamp", "").isoformat() if isinstance(event.get("timestamp"), datetime) else event.get("timestamp", ""),
        "event_type": event.get("event_type", ""),
        "actor_id": event.get("actor_id", ""),
        "actor_role": event.get("actor_role", ""),
        "resource_type": event.get("resource_type", ""),
        "resource_id": event.get("resource_id", ""),
        "outcome": event.get("outcome", ""),
        "correlation_id": event.get("correlation_id", ""),
        "ip_address": event.get("ip_address", ""),
        "action_detail": str(event.get("action_detail", {}))
    }
    return result


# =============================================================================
# STATISTICS ENDPOINT
# =============================================================================

@router.get("/stats")
async def get_audit_statistics(
    org_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict = Depends(require_audit_access)
):
    """
    Get audit event statistics for the organization.

    Returns counts by event type, outcome, and top actors.
    Requires can_manage_audit_logs permission.
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    events = db.get_audit_events(
        org_id=org_id,
        start_time=start_date,
        limit=50000,
        offset=0
    )

    # Calculate statistics
    total_events = len(events)
    by_type = {}
    by_outcome = {}
    by_actor = {}

    for event in events:
        # By type
        event_type = event.get("event_type", "UNKNOWN")
        by_type[event_type] = by_type.get(event_type, 0) + 1

        # By outcome
        outcome = event.get("outcome", "UNKNOWN")
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

        # By actor
        actor = event.get("actor_id", "UNKNOWN")
        by_actor[actor] = by_actor.get(actor, 0) + 1

    # Sort actors by count and get top 10
    top_actors = sorted(by_actor.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "period_days": days,
        "total_events": total_events,
        "events_by_type": by_type,
        "events_by_outcome": by_outcome,
        "top_actors": [{"actor_id": a, "count": c} for a, c in top_actors],
        "failure_rate": by_outcome.get("FAILURE", 0) / total_events if total_events > 0 else 0,
        "denial_rate": by_outcome.get("DENIED", 0) / total_events if total_events > 0 else 0
    }
