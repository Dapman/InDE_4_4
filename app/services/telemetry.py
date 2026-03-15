"""
InDE Behavioral Telemetry Service
Lightweight local event tracking — stored in MongoDB, visible in admin panel.
No external services. No PII. All events are keyed by GII, not email or display_name.

v3.16: Initial implementation
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("inde.telemetry")

# Event taxonomy — extend as needed
EVENTS = {
    # Session lifecycle
    "session.started": "User opened InDE (authenticated)",
    "session.ended": "Session ended (logout or timeout)",

    # Onboarding funnel
    "onboarding.screen_viewed": "Onboarding screen rendered",
    "onboarding.screen_completed": "Onboarding screen criterion met",
    "onboarding.completed": "All 4 onboarding criteria satisfied",
    "onboarding.abandoned": "User left onboarding mid-flow",

    # Pursuit lifecycle
    "pursuit.created": "New pursuit created",
    "pursuit.first_coaching": "First coaching message sent in pursuit",
    "pursuit.artifact_generated": "First artifact created in pursuit",
    "pursuit.archived": "Pursuit archived",
    "pursuit.completed": "Pursuit reached terminal state",

    # Coaching engagement
    "coaching.message_sent": "User sent coaching message",
    "coaching.rate_limited": "User hit coaching rate limit",
    "coaching.timeout": "Coaching response timed out",
    "coaching.cancelled": "User cancelled pending coaching request",

    # GII
    "gii.issued": "New PROVISIONAL GII issued",
    "gii.profile_viewed": "User viewed their GII profile",

    # =========================================================================
    # v4.0: MOMENTUM MANAGEMENT EVENTS
    # Properties schema: { momentum_level: str, days_since_last: int, depth_stage: str }
    # =========================================================================

    # Session momentum
    "momentum.session_opened": "Session opened with momentum context",
    "momentum.session_closed": "Session closed with momentum bridge shown",

    # Re-engagement
    "momentum.re_engaged": "User returned after gap (with momentum greeting)",
    "momentum.long_gap_return": "User returned after extended absence (7+ days)",

    # Depth progression
    "momentum.depth_advanced": "User idea depth advanced to new stage",
    "momentum.depth_acknowledged": "Depth acknowledgment shown to user",

    # Coaching continuity
    "momentum.bridge_shown": "Momentum bridge message displayed",
    "momentum.context_restored": "Previous session context restored for user",
}

# Module-level db reference (set during app startup)
_db = None


def init_telemetry(db):
    """Initialize telemetry with database reference."""
    global _db
    _db = db
    logger.info("Telemetry service initialized")


def track(event_name: str, gii_id: Optional[str], properties: Optional[Dict[str, Any]] = None):
    """
    Record a behavioral event. Fire-and-forget — never blocks user operations.
    Events are keyed by GII, never by email or display_name.

    Args:
        event_name: Event type from EVENTS taxonomy
        gii_id: User's Global Innovator Identifier (no PII)
        properties: Additional event context
    """
    if event_name not in EVENTS:
        logger.warning(f"Unknown telemetry event: {event_name}")

    record = {
        "event": event_name,
        "gii_id": gii_id,  # Attribution via GII only — no PII
        "properties": properties or {},
        "recorded_at": datetime.utcnow()
    }

    try:
        if _db is not None:
            _db.db.telemetry_events.insert_one(record)
        else:
            logger.warning(f"Telemetry not initialized, event dropped: {event_name}")
    except Exception as e:
        logger.error(f"Telemetry write failed: {event_name}: {e}")
        # Never raise — telemetry failure must never impact user experience


# =============================================================================
# v4.0: Momentum Telemetry Helpers
# =============================================================================

def track_momentum(
    event_type: str,
    gii_id: Optional[str],
    momentum_level: str = "moderate",
    days_since_last: int = 0,
    depth_stage: str = "idea_forming",
    pursuit_id: Optional[str] = None
):
    """
    Track momentum-related events with standard properties.

    Args:
        event_type: Momentum event suffix (e.g., "session_opened", "re_engaged")
        gii_id: User's Global Innovator Identifier
        momentum_level: One of 'high', 'moderate', 'low'
        days_since_last: Days since last session
        depth_stage: Current idea depth stage
        pursuit_id: Optional pursuit context
    """
    event_name = f"momentum.{event_type}"
    properties = {
        "momentum_level": momentum_level,
        "days_since_last": days_since_last,
        "depth_stage": depth_stage,
    }
    if pursuit_id:
        properties["pursuit_id"] = pursuit_id

    track(event_name, gii_id, properties)


def get_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get aggregated telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary

    Returns:
        Summary dict with event totals and funnel metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"recorded_at": {"$gte": since}}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    results = list(_db.db.telemetry_events.aggregate(pipeline))

    # Onboarding funnel specific
    funnel_stages = [
        "onboarding.screen_viewed",
        "onboarding.screen_completed",
        "onboarding.completed"
    ]
    funnel = {}
    for stage in funnel_stages:
        funnel[stage] = _db.db.telemetry_events.count_documents(
            {"event": stage, "recorded_at": {"$gte": since}}
        )

    return {
        "period_days": days,
        "event_totals": {r["_id"]: r["count"] for r in results},
        "onboarding_funnel": funnel,
        "total_events": sum(r["count"] for r in results)
    }
