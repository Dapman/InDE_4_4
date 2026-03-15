"""
Momentum Pattern Engine

InDE MVP v4.4.0 — The Learning Engine

Ingests momentum snapshots from the MME and aggregates cross-pursuit
momentum signals into learnable IML patterns.

The engine runs as a background aggregation process — it is NOT called
on the critical path of a coaching turn. Each aggregation cycle:

  1. Reads recent momentum snapshots from `momentum_snapshots` collection
     (produced by MomentumPersistence.save_snapshot() since v4.1)
  2. Pairs each snapshot with its preceding snapshot for the same pursuit
     to compute actual momentum_lift_delta (score_after - score_before)
  3. Groups by context fingerprint (pursuit_stage + artifact_type + momentum_tier)
  4. Upserts the aggregated pattern into `momentum_patterns` via
     MomentumPatternPersistence

Design Rules:
  - Aggregation is idempotent: running twice on the same data produces
    the same result
  - No PII enters any pattern record — context is structural only
  - Minimum sample requirement (MIN_SAMPLE_FOR_CONFIDENCE = 10) ensures
    patterns are not surfaced until statistically meaningful
  - The engine fails silently: if aggregation errors, coaching is unaffected

© 2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from .momentum_pattern_persistence import (
    MomentumPatternType,
    make_context_hash,
    upsert_pattern,
    MIN_SAMPLE_FOR_CONFIDENCE,
)

logger = logging.getLogger("inde.iml.momentum_pattern_engine")

SNAPSHOT_COLLECTION = "momentum_snapshots"
AGGREGATION_LOOKBACK_HOURS = 48  # How far back each aggregation run looks


def _get_db():
    """Get database reference - imported lazily to avoid circular imports."""
    try:
        from core.database import db
        return db.db
    except Exception:
        return None


class MomentumPatternEngine:
    """
    Aggregates momentum snapshots into cross-innovator IML patterns.
    Called by a background task — not on the coaching turn critical path.
    """

    def run_aggregation_cycle(self) -> dict:
        """
        Execute one aggregation cycle.
        Returns a summary dict: {processed, patterns_created, patterns_updated, errors}
        """
        summary = {"processed": 0, "patterns_created": 0, "patterns_updated": 0, "errors": 0}
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=AGGREGATION_LOOKBACK_HOURS)
            snapshots = self._fetch_recent_snapshots(cutoff)
            paired = self._pair_snapshots_by_pursuit(snapshots)
            for pair in paired:
                try:
                    self._process_snapshot_pair(pair, summary)
                    summary["processed"] += 1
                except Exception as e:
                    logger.warning(f"Error processing snapshot pair: {e}")
                    summary["errors"] += 1
        except Exception as e:
            logger.error(f"Aggregation cycle failed: {e}")
            summary["errors"] += 1
        return summary

    def _fetch_recent_snapshots(self, since: datetime) -> List[Dict[str, Any]]:
        """Fetch momentum snapshots updated since `since`."""
        db = _get_db()
        if db is None:
            return []

        try:
            cursor = db[SNAPSHOT_COLLECTION].find(
                {"recorded_at": {"$gte": since.isoformat()}},
            ).sort([("pursuit_id", 1), ("recorded_at", 1)]).limit(2000)
            return list(cursor)
        except Exception as e:
            logger.error(f"Snapshot fetch failed: {e}")
            return []

    def _pair_snapshots_by_pursuit(self, snapshots: List[Dict[str, Any]]) -> List[dict]:
        """
        Pair consecutive snapshots within the same pursuit to compute
        before/after momentum deltas. Returns list of pair dicts.
        """
        by_pursuit: Dict[str, List[Dict[str, Any]]] = {}
        for s in snapshots:
            pid = s.get("pursuit_id", "")
            by_pursuit.setdefault(pid, []).append(s)
        pairs = []
        for pid, snaps in by_pursuit.items():
            snaps.sort(key=lambda x: x.get("recorded_at", ""))
            for i in range(1, len(snaps)):
                pairs.append({"before": snaps[i - 1], "after": snaps[i]})
        return pairs

    def _process_snapshot_pair(self, pair: dict, summary: dict) -> None:
        """
        Derive a momentum pattern from a before/after snapshot pair
        and upsert it into the momentum_patterns collection.
        """
        before = pair["before"]
        after = pair["after"]

        before_score = before.get("composite_score", 0.5)
        after_score = after.get("composite_score", 0.5)
        lift_delta = after_score - before_score

        # Extract context from the 'before' snapshot (state at entry)
        pursuit_stage = before.get("pursuit_stage", "unknown")
        artifact_type = before.get("artifact_at_exit", "unknown")
        momentum_tier = before.get("momentum_tier", "MEDIUM")
        bridge_id = before.get("selected_bridge_question_id")
        insight_cat = before.get("last_surfaced_insight_category")

        if not bridge_id and not insight_cat:
            return  # No actionable signal; skip

        pattern_type = (
            MomentumPatternType.BRIDGE_LIFT if (bridge_id and lift_delta >= 0)
            else MomentumPatternType.BRIDGE_STALL if bridge_id
            else MomentumPatternType.INSIGHT_LIFT if (insight_cat and lift_delta >= 0)
            else MomentumPatternType.INSIGHT_STALL
        )

        ctx_hash = make_context_hash(pursuit_stage, artifact_type, momentum_tier)
        confidence = self._estimate_confidence(1, lift_delta)

        result = upsert_pattern({
            "pattern_id": str(uuid.uuid4()),
            "pattern_type": pattern_type.value,
            "context_hash": ctx_hash,
            "bridge_question_id": bridge_id,
            "insight_category": insight_cat,
            "momentum_lift_delta": lift_delta,
            "return_rate_7d": 0.0,  # Updated separately by return-rate aggregator
            "confidence_score": confidence,
            "sample_count_delta": 1,
        })

        if result:
            summary["patterns_updated"] += 1

    def _estimate_confidence(self, sample_count: int, lift_delta: float) -> float:
        """
        Rough confidence estimate for a single new observation.
        Grows toward 1.0 as sample_count reaches MIN_SAMPLE_FOR_CONFIDENCE.
        """
        base = min(sample_count / MIN_SAMPLE_FOR_CONFIDENCE, 1.0)
        signal_strength = min(abs(lift_delta) / 0.3, 1.0)
        return round(base * 0.6 + signal_strength * 0.4, 4)
