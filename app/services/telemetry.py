"""
InDE Behavioral Telemetry Service
Lightweight local event tracking — stored in MongoDB, visible in admin panel.
No external services. No PII. All events are keyed by GII, not email or display_name.

v3.16: Initial implementation
v4.4.0: Added IML momentum learning telemetry events
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

    # =========================================================================
    # v4.4: IML MOMENTUM LEARNING EVENTS
    # Properties schema: { pattern_type: str, confidence: float, sample_size: int }
    # =========================================================================

    # Pattern aggregation
    "iml.pattern_created": "New momentum pattern created from aggregation",
    "iml.pattern_updated": "Existing momentum pattern updated with new sample",
    "iml.aggregation_cycle": "IML aggregation cycle completed",

    # Feedback loop
    "iml.bridge_recommended": "IML recommended a bridge (vs static library)",
    "iml.bridge_fallback": "IML fell back to static library (no strong recommendation)",
    "iml.circuit_breaker_opened": "IML feedback receiver circuit breaker opened",
    "iml.circuit_breaker_closed": "IML feedback receiver circuit breaker closed",

    # Knowledge surfacing
    "iml.insight_lift_scored": "Insight scored with momentum-lift factor",
    "iml.insight_boosted": "Insight ranking boosted by momentum-lift score",

    # IKF contribution
    "ikf.momentum_pattern_eligible": "Momentum pattern reached IKF contribution threshold",
    "ikf.momentum_pattern_contributed": "Momentum pattern contributed to IKF",
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


# =============================================================================
# v4.4: IML Momentum Telemetry Helpers
# =============================================================================

def track_iml(
    event_type: str,
    pattern_type: str = "unknown",
    confidence: float = 0.0,
    sample_size: int = 0,
    context_hash: str = None,
    selection_source: str = None
):
    """
    Track IML momentum learning events.

    Args:
        event_type: IML event suffix (e.g., "pattern_created", "bridge_recommended")
        pattern_type: Type of momentum pattern
        confidence: Pattern confidence score (0-1)
        sample_size: Number of samples in pattern
        context_hash: Optional context fingerprint
        selection_source: Source of selection ("iml" or "static")
    """
    event_name = f"iml.{event_type}"
    properties = {
        "pattern_type": pattern_type,
        "confidence": round(confidence, 3),
        "sample_size": sample_size,
    }
    if context_hash:
        properties["context_hash"] = context_hash
    if selection_source:
        properties["selection_source"] = selection_source

    track(event_name, None, properties)  # IML events are not user-specific


def get_iml_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get IML momentum learning telemetry summary.

    Args:
        days: Number of days to include in summary

    Returns:
        Summary dict with IML pattern and feedback loop metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    # Aggregate IML events
    iml_events = [
        "iml.pattern_created",
        "iml.pattern_updated",
        "iml.aggregation_cycle",
        "iml.bridge_recommended",
        "iml.bridge_fallback",
        "iml.circuit_breaker_opened",
        "iml.insight_lift_scored",
        "ikf.momentum_pattern_contributed"
    ]

    event_counts = {}
    for event in iml_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Calculate IML effectiveness
    bridge_recommended = event_counts.get("iml.bridge_recommended", 0)
    bridge_fallback = event_counts.get("iml.bridge_fallback", 0)
    total_bridge_selections = bridge_recommended + bridge_fallback

    iml_selection_rate = (
        bridge_recommended / total_bridge_selections
        if total_bridge_selections > 0 else 0
    )

    return {
        "period_days": days,
        "event_counts": event_counts,
        "patterns_created": event_counts.get("iml.pattern_created", 0),
        "patterns_updated": event_counts.get("iml.pattern_updated", 0),
        "iml_selection_rate": round(iml_selection_rate, 3),
        "circuit_breaker_trips": event_counts.get("iml.circuit_breaker_opened", 0),
        "ikf_contributions": event_counts.get("ikf.momentum_pattern_contributed", 0)
    }


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
