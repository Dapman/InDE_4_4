"""
Momentum Persistence

Handles storage of momentum snapshots to MongoDB and writing of
momentum patterns to the IML pattern store.

Two storage targets:
1. momentum_snapshots collection — raw session snapshots (90-day TTL)
2. iml_patterns collection — aggregated momentum patterns (permanent)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from .momentum_engine import MomentumSnapshot

logger = logging.getLogger(__name__)


class MomentumPersistence:
    """
    Saves momentum snapshots and contributes patterns to IML.

    Usage:
        persistence = MomentumPersistence(db)
        persistence.save_snapshot(snapshot)
        persistence.contribute_pattern(snapshot, pursuit_outcome)
    """

    def __init__(self, db):
        self.db = db
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Ensure TTL and query indexes exist."""
        try:
            # 90-day TTL on momentum snapshots (same as telemetry)
            self.db.momentum_snapshots.create_index(
                "recorded_at",
                expireAfterSeconds=60 * 60 * 24 * 90
            )
            self.db.momentum_snapshots.create_index("pursuit_id")
            self.db.momentum_snapshots.create_index("gii_id")
        except Exception as e:
            logger.warning(f"Momentum index creation warning: {e}")

    def save_snapshot(self, snapshot: MomentumSnapshot) -> bool:
        """
        Persist a session momentum snapshot. Fire-and-forget safe.

        Returns True on success, False on failure. Never raises.
        """
        try:
            doc = {
                "session_id":      snapshot.session_id,
                "pursuit_id":      snapshot.pursuit_id,
                "gii_id":          snapshot.gii_id,
                "recorded_at":     snapshot.recorded_at,
                "turn_count":      snapshot.turn_count,
                "composite_score": snapshot.composite_score,
                "momentum_tier":   snapshot.momentum_tier,
                "signal_history":  snapshot.signal_history,
                "artifact_at_exit": snapshot.artifact_at_exit,
                "bridge_delivered": snapshot.bridge_delivered,
                "bridge_responded": snapshot.bridge_responded,
                "exit_reason":     snapshot.exit_reason,
            }
            self.db.momentum_snapshots.insert_one(doc)
            logger.info(
                f"Momentum snapshot saved: session={snapshot.session_id}, "
                f"score={snapshot.composite_score:.2f}, tier={snapshot.momentum_tier}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save momentum snapshot: {e}")
            return False

    def contribute_iml_pattern(
        self,
        snapshot: MomentumSnapshot,
        pursuit_outcome: Optional[str] = None
    ) -> bool:
        """
        Write a momentum pattern to the IML when a pursuit reaches
        a terminal or success state. This enables cross-pursuit learning:
        "What momentum trajectories correlate with successful outcomes?"

        Only called at pursuit completion — not every session.

        Args:
            snapshot: The final session snapshot
            pursuit_outcome: The pursuit terminal state (if known)

        Returns True on success, False on failure. Never raises.
        """
        try:
            pattern = {
                "pattern_type":    "momentum_trajectory",
                "source_gii":      snapshot.gii_id,
                "created_at":      datetime.utcnow(),
                "pattern_data": {
                    "final_tier":        snapshot.momentum_tier,
                    "final_score":       snapshot.composite_score,
                    "total_turns":       snapshot.turn_count,
                    "bridge_delivered":  snapshot.bridge_delivered,
                    "bridge_responded":  snapshot.bridge_responded,
                    "exit_reason":       snapshot.exit_reason,
                    "pursuit_outcome":   pursuit_outcome,
                    "artifact_at_exit":  snapshot.artifact_at_exit,
                },
                # IML metadata
                "generalization_status": "raw",   # Awaiting generalization pipeline
                "privacy_cleared":       True,    # GII is already hashed
            }
            self.db.iml_patterns.insert_one(pattern)
            logger.info(
                f"Momentum IML pattern contributed: tier={snapshot.momentum_tier}, "
                f"outcome={pursuit_outcome}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to contribute momentum IML pattern: {e}")
            return False

    def get_momentum_summary(self, pursuit_id: str) -> dict:
        """
        Returns momentum health summary for a pursuit.
        Used by the admin dashboard.
        """
        try:
            snapshots = list(self.db.momentum_snapshots.find(
                {"pursuit_id": pursuit_id},
                sort=[("recorded_at", 1)]
            ))
            if not snapshots:
                return {"sessions": 0, "avg_score": None, "trend": "no_data"}

            scores = [s["composite_score"] for s in snapshots]
            avg = round(sum(scores) / len(scores), 3)

            # Trend: compare first half vs second half of sessions
            if len(scores) >= 4:
                mid = len(scores) // 2
                first_half = sum(scores[:mid]) / mid
                second_half = sum(scores[mid:]) / (len(scores) - mid)
                trend = "improving" if second_half > first_half + 0.05 else \
                        "declining" if second_half < first_half - 0.05 else "stable"
            else:
                trend = "insufficient_data"

            return {
                "sessions": len(snapshots),
                "avg_score": avg,
                "latest_score": scores[-1],
                "latest_tier": snapshots[-1]["momentum_tier"],
                "trend": trend,
                "bridge_delivery_rate": round(
                    sum(1 for s in snapshots if s["bridge_delivered"]) / len(snapshots), 2
                ),
                "bridge_response_rate": round(
                    sum(1 for s in snapshots if s["bridge_responded"]) /
                    max(1, sum(1 for s in snapshots if s["bridge_delivered"])), 2
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get momentum summary: {e}")
            return {"sessions": 0, "avg_score": None, "trend": "error"}
