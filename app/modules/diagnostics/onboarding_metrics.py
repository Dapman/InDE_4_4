"""
Onboarding Funnel Metrics
Records and reports on new user onboarding completion.
Instrumentation only — does not alter onboarding flow behavior.

v3.14: Operational Readiness
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class OnboardingMetricsService:
    """
    Service for recording and reporting onboarding completion metrics.

    Tracks four completion criteria:
    - vision_artifact_created: User has created a vision artifact
    - fear_identified: User has identified at least one fear
    - methodology_selected: User has selected a methodology archetype
    - iml_pattern_engaged: User has engaged with IML pattern (viewed >=1 insight)

    Provides both sync and async methods. Sync methods are suffixed with _sync
    for use in synchronous contexts like the ScaffoldingEngine.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    # =========================================================================
    # SYNCHRONOUS METHODS (for ScaffoldingEngine and other sync contexts)
    # =========================================================================

    def record_session_start_sync(self, user_id: str) -> str:
        """
        Called when a new user begins the onboarding flow (Screen 1).
        Creates a metrics record and returns its ID.
        Idempotent: if a record already exists for this user, returns its ID.

        Args:
            user_id: The user starting onboarding

        Returns:
            The metrics record ID as a string
        """
        existing = self.db.onboarding_metrics.find_one(
            {"user_id": user_id},
            sort=[("started_at", -1)]
        )

        # If a recent incomplete session exists (within 24h), return it
        if existing and not existing.get("completed_at"):
            started = datetime.fromisoformat(existing["started_at"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - started).total_seconds() < 86400:
                return str(existing["_id"])

        # Start a new metrics session
        result = self.db.onboarding_metrics.insert_one({
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "criteria": {
                "vision_artifact_created": False,
                "fear_identified": False,
                "methodology_selected": False,
                "iml_pattern_engaged": False,
            },
            "screen_reached": 1,
            "duration_seconds": None,
        })
        return str(result.inserted_id)

    def record_screen_reached_sync(self, user_id: str, screen_number: int) -> None:
        """
        Update the highest screen reached during onboarding.

        Args:
            user_id: The user progressing through onboarding
            screen_number: The screen number reached (1-5)
        """
        self.db.onboarding_metrics.update_one(
            {"user_id": user_id, "completed_at": None},
            {"$max": {"screen_reached": screen_number}}
        )

    def record_criterion_met_sync(self, user_id: str, criterion: str) -> None:
        """
        Record that an onboarding completion criterion has been met.

        Args:
            user_id: The user who met the criterion
            criterion: Must be one of:
                - "vision_artifact_created"
                - "fear_identified"
                - "methodology_selected"
                - "iml_pattern_engaged"
        """
        valid_criteria = {
            "vision_artifact_created", "fear_identified",
            "methodology_selected", "iml_pattern_engaged"
        }
        if criterion not in valid_criteria:
            logger.warning(f"Unknown onboarding criterion: {criterion}")
            return

        # Set criterion to True
        self.db.onboarding_metrics.update_one(
            {"user_id": user_id, "completed_at": None},
            {"$set": {f"criteria.{criterion}": True}}
        )

        # Check completion
        record = self.db.onboarding_metrics.find_one(
            {"user_id": user_id, "completed_at": None},
            sort=[("started_at", -1)]
        )

        if record and all(record.get("criteria", {}).values()):
            started = datetime.fromisoformat(record["started_at"].replace("Z", "+00:00"))
            duration = int((datetime.now(timezone.utc) - started).total_seconds())
            self.db.onboarding_metrics.update_one(
                {"_id": record["_id"]},
                {"$set": {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": duration
                }}
            )
            logger.info(f"Onboarding fully completed for user {user_id} in {duration}s.")

    def get_funnel_stats_sync(self, days: int = 30) -> dict:
        """
        Return onboarding funnel statistics for the diagnostics panel.
        Aggregates over the last N days.

        Args:
            days: Number of days to aggregate (default 30)

        Returns:
            dict with funnel statistics
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        total = self.db.onboarding_metrics.count_documents(
            {"started_at": {"$gte": since}}
        )

        if total == 0:
            return {
                "period_days": days,
                "total_sessions": 0,
                "completed_sessions": 0,
                "completion_rate": 0.0,
                "criteria_rates": {},
                "average_duration_seconds": None,
                "screen_drop_off": {}
            }

        # Criterion completion rates
        criteria_names = [
            "vision_artifact_created", "fear_identified",
            "methodology_selected", "iml_pattern_engaged"
        ]

        criteria_rates = {}
        for criterion in criteria_names:
            count = self.db.onboarding_metrics.count_documents({
                "started_at": {"$gte": since},
                f"criteria.{criterion}": True
            })
            criteria_rates[criterion] = round(count / total, 3)

        # Completion rate (all four criteria)
        completed = self.db.onboarding_metrics.count_documents({
            "started_at": {"$gte": since},
            "completed_at": {"$ne": None}
        })

        # Average duration for completed sessions
        pipeline = [
            {"$match": {"started_at": {"$gte": since}, "duration_seconds": {"$ne": None}}},
            {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_seconds"}}}
        ]
        avg_result = list(self.db.onboarding_metrics.aggregate(pipeline))
        avg_duration = round(avg_result[0]["avg_duration"]) if avg_result else None

        # Screen drop-off counts
        screen_drop_off = {}
        for screen in range(1, 6):
            count = self.db.onboarding_metrics.count_documents({
                "started_at": {"$gte": since},
                "screen_reached": screen,
                "completed_at": None
            })
            screen_drop_off[f"screen_{screen}"] = count

        return {
            "period_days": days,
            "total_sessions": total,
            "completed_sessions": completed,
            "completion_rate": round(completed / total, 3),
            "criteria_rates": criteria_rates,
            "average_duration_seconds": avg_duration,
            "screen_drop_off": screen_drop_off
        }

    # =========================================================================
    # ASYNC METHODS (for FastAPI endpoints)
    # Wrap sync methods since pymongo is synchronous anyway
    # =========================================================================

    async def record_session_start(self, user_id: str) -> str:
        """Async wrapper for record_session_start_sync."""
        return self.record_session_start_sync(user_id)

    async def record_screen_reached(self, user_id: str, screen_number: int) -> None:
        """Async wrapper for record_screen_reached_sync."""
        return self.record_screen_reached_sync(user_id, screen_number)

    async def record_criterion_met(self, user_id: str, criterion: str) -> None:
        """Async wrapper for record_criterion_met_sync."""
        return self.record_criterion_met_sync(user_id, criterion)

    async def get_funnel_stats(self, days: int = 30) -> dict:
        """Async wrapper for get_funnel_stats_sync."""
        return self.get_funnel_stats_sync(days)
