"""
Momentum Pattern Persistence

InDE MVP v4.4.0 — The Learning Engine

Handles read/write operations for the `momentum_patterns` MongoDB collection.
Implements idempotent upsert logic with conflict-safe writes. Every write is
tagged with a schema_version for forward-compatibility.

Momentum patterns are NEVER stored with PII or pursuit-specific identifiers
at this layer. Anonymization happens in momentum_contribution.py before
federation. This collection stores generalized patterns for in-system use.

Pattern Schema:
  pattern_id        UUID — unique identifier
  schema_version    "4.4.0" — version this pattern was written under
  pattern_type      MomentumPatternType enum (see momentum_pattern_engine.py)
  context_hash      SHA-256 of: pursuit_stage + artifact_type + momentum_tier_at_entry
                    (no PII — purely structural context fingerprint)
  bridge_question_id  ID from bridge_library (or None for insight patterns)
  insight_category  IML insight category (or None for bridge patterns)
  sample_count      Number of innovator sessions contributing to this pattern
  momentum_lift_delta  Average momentum_score change in the turn AFTER this
                       bridge/insight was delivered
  return_rate_7d    % of innovators who returned within 7 days after this
                    bridge/insight was delivered (float 0.0–1.0)
  confidence_score  Composite confidence: min(sample_count/MIN_SAMPLE, 1.0) *
                    statistical_significance (Welch's t-test vs. static baseline)
  created_at        ISO timestamp
  last_updated      ISO timestamp (updated on each aggregation run)

© 2026 Yul Williams | InDEVerse, Incorporated
"""

import hashlib
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger("inde.iml.momentum_persistence")

COLLECTION = "momentum_patterns"
SCHEMA_VERSION = "4.4.0"
MIN_SAMPLE_FOR_CONFIDENCE = 10  # Minimum sample count before confidence > 0

# Minimum confidence score required to publish pattern to IKF contribution
IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD = 0.7


class MomentumPatternType(str, Enum):
    BRIDGE_LIFT = "bridge_lift"          # Bridge questions that lifted momentum
    BRIDGE_STALL = "bridge_stall"        # Bridge questions that stalled momentum
    INSIGHT_LIFT = "insight_lift"        # IML insights that lifted momentum
    INSIGHT_STALL = "insight_stall"      # IML insights that stalled momentum
    REENTRY_CONTINUATION = "reentry_continuation"  # Re-entry patterns that led to resumed sessions


def make_context_hash(
    pursuit_stage: str,
    artifact_type: str,
    momentum_tier: str
) -> str:
    """
    Compute a deterministic, PII-free context fingerprint.
    Used as the grouping key for pattern aggregation.
    """
    raw = f"{pursuit_stage}:{artifact_type}:{momentum_tier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_db():
    """Get database reference - imported lazily to avoid circular imports."""
    try:
        from core.database import db
        return db.db
    except Exception:
        return None


def upsert_pattern(pattern_data: dict) -> Optional[str]:
    """
    Idempotent upsert for a momentum pattern record.
    Matches on (context_hash, pattern_type, bridge_question_id, insight_category).
    Updates sample_count, momentum_lift_delta, return_rate_7d, confidence_score.
    Returns the pattern_id of the upserted document.
    """
    db = _get_db()
    if db is None:
        logger.warning("Database not available for momentum pattern upsert")
        return None

    try:
        filter_doc = {
            "context_hash": pattern_data["context_hash"],
            "pattern_type": pattern_data["pattern_type"],
            "bridge_question_id": pattern_data.get("bridge_question_id"),
            "insight_category": pattern_data.get("insight_category"),
        }
        update_doc = {
            "$set": {
                "schema_version": SCHEMA_VERSION,
                "momentum_lift_delta": pattern_data.get("momentum_lift_delta", 0.0),
                "return_rate_7d": pattern_data.get("return_rate_7d", 0.0),
                "confidence_score": pattern_data.get("confidence_score", 0.0),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            "$inc": {"sample_count": pattern_data.get("sample_count_delta", 1)},
            "$setOnInsert": {
                "pattern_id": pattern_data["pattern_id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        result = db[COLLECTION].update_one(filter_doc, update_doc, upsert=True)
        return str(result.upserted_id) if result.upserted_id else pattern_data["pattern_id"]
    except Exception as e:
        logger.error(f"momentum_pattern upsert failed: {e}")
        return None


def get_patterns_for_context(
    context_hash: str,
    pattern_types: List[str],
    min_confidence: float = 0.3,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve top patterns for a given context fingerprint.
    Ordered by momentum_lift_delta descending.
    Only returns patterns above min_confidence threshold.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        cursor = db[COLLECTION].find(
            {
                "context_hash": context_hash,
                "pattern_type": {"$in": pattern_types},
                "confidence_score": {"$gte": min_confidence},
            },
        ).sort("momentum_lift_delta", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"momentum_pattern query failed: {e}")
        return []


def get_contribution_eligible_patterns(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Return patterns eligible for IKF federation contribution.
    Eligibility: confidence_score >= IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        cursor = db[COLLECTION].find(
            {"confidence_score": {"$gte": IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD}},
        ).sort("last_updated", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"contribution-eligible pattern query failed: {e}")
        return []
