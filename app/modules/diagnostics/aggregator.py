"""
Diagnostics Aggregator
Fan-out module that collects health metrics from multiple sources.

v3.14: Operational Readiness
v4.1: Momentum health metrics (MME telemetry)
v4.2: Re-entry and re-engagement health metrics
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .error_buffer import error_buffer
from .onboarding_metrics import OnboardingMetricsService

logger = logging.getLogger(__name__)


class DiagnosticsAggregator:
    """
    Collects and aggregates diagnostics from all health sources.

    Returns a combined dict with:
    - error_counts: Error buffer statistics
    - onboarding_funnel: Onboarding completion metrics
    - system_health: System-level health indicators
    - recent_errors: Most recent error entries
    """

    def __init__(self, db=None):
        """
        Initialize with optional database connection.

        Args:
            db: Database instance (required for onboarding metrics)
        """
        self.db = db

    def collect_all(self, include_errors: bool = True, error_limit: int = 20) -> dict:
        """
        Collect diagnostics from all sources.

        Args:
            include_errors: Whether to include recent error entries
            error_limit: Maximum number of error entries to return

        Returns:
            Combined diagnostics dict
        """
        result = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "error_counts": self._get_error_counts(),
            "innovator_stats": self._get_innovator_stats(),
            "onboarding_funnel": self._get_onboarding_funnel(),
            "momentum_health": self._get_momentum_health(),  # v4.1
            "reentry_health": self._get_reentry_health(),    # v4.2
            "system_health": self._get_system_health(),
        }

        if include_errors:
            result["recent_errors"] = self._get_recent_errors(error_limit)

        return result

    def _get_error_counts(self) -> dict:
        """
        Get error counts from the error buffer.

        Returns:
            Dict with counts by level
        """
        try:
            return error_buffer.get_counts()
        except Exception as e:
            logger.warning(f"Error buffer access failed: {e}")
            return {"ERROR": 0, "WARNING": 0, "CRITICAL": 0, "error": str(e)}

    def _get_innovator_stats(self) -> dict:
        """
        Get innovator (user) statistics.

        Returns:
            Dict with total users and activity breakdowns
        """
        if self.db is None:
            return {
                "status": "unavailable",
                "reason": "Database connection not provided"
            }

        try:
            from datetime import timedelta
            raw_db = self.db.db if hasattr(self.db, 'db') else self.db
            now = datetime.now(timezone.utc)

            # Total registered users
            total_users = raw_db.users.count_documents({})

            # Active in last 24 hours
            active_24h = raw_db.users.count_documents({
                "last_active": {"$gte": now - timedelta(hours=24)}
            })

            # Active in last 7 days
            active_7d = raw_db.users.count_documents({
                "last_active": {"$gte": now - timedelta(days=7)}
            })

            # Active in last 30 days
            active_30d = raw_db.users.count_documents({
                "last_active": {"$gte": now - timedelta(days=30)}
            })

            # New registrations this week
            new_this_week = raw_db.users.count_documents({
                "created_at": {"$gte": now - timedelta(days=7)}
            })

            return {
                "total": total_users,
                "active_24h": active_24h,
                "active_7d": active_7d,
                "active_30d": active_30d,
                "new_this_week": new_this_week,
            }
        except Exception as e:
            logger.warning(f"Innovator stats access failed: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def _get_onboarding_funnel(self) -> dict:
        """
        Get onboarding funnel statistics.

        Returns:
            Funnel stats dict or placeholder if db not available
        """
        if self.db is None:
            return {
                "status": "unavailable",
                "reason": "Database connection not provided"
            }

        try:
            metrics_service = OnboardingMetricsService(self.db)
            return metrics_service.get_funnel_stats_sync(days=30)
        except Exception as e:
            logger.warning(f"Onboarding metrics access failed: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def _get_system_health(self) -> dict:
        """
        Get system-level health indicators.

        Placeholder for future metrics like:
        - Database connection status
        - Redis connection status
        - LLM gateway availability
        - License status

        Returns:
            System health dict
        """
        health = {
            "database": self._check_database_health(),
            "license": self._check_license_status(),
        }

        # Calculate overall status
        statuses = [v.get("status", "unknown") for v in health.values() if isinstance(v, dict)]
        if all(s == "healthy" for s in statuses):
            health["overall"] = "healthy"
        elif any(s == "critical" for s in statuses):
            health["overall"] = "critical"
        elif any(s == "degraded" for s in statuses):
            health["overall"] = "degraded"
        else:
            health["overall"] = "unknown"

        return health

    def _check_database_health(self) -> dict:
        """Check database connectivity."""
        if self.db is None:
            return {"status": "unknown", "message": "No database connection"}

        try:
            raw_db = self.db.db if hasattr(self.db, 'db') else self.db
            # Simple ping
            raw_db.command("ping")
            return {"status": "healthy", "message": "Connected"}
        except Exception as e:
            return {"status": "critical", "message": str(e)}

    def _check_license_status(self) -> dict:
        """Check license status (placeholder)."""
        # TODO: Integrate with actual license service
        return {"status": "healthy", "message": "License check not implemented"}

    def _get_momentum_health(self, days: int = 7) -> dict:
        """
        v4.1: Get momentum health metrics from MME telemetry.

        Aggregates momentum_snapshots collection data to provide:
        - Session tier distribution (HIGH/MEDIUM/LOW/CRITICAL)
        - Bridge delivery and response rates
        - Post-vision exit rate (primary success metric)

        Args:
            days: Number of days to aggregate

        Returns:
            Momentum health summary dict
        """
        if self.db is None:
            return {
                "status": "unavailable",
                "reason": "Database connection not provided"
            }

        try:
            from datetime import timedelta
            raw_db = self.db.db if hasattr(self.db, 'db') else self.db
            since = datetime.now(timezone.utc) - timedelta(days=days)

            # Aggregate momentum health across all sessions in period
            pipeline = [
                {"$match": {"recorded_at": {"$gte": since}}},
                {"$group": {
                    "_id": None,
                    "total_sessions": {"$sum": 1},
                    "avg_score": {"$avg": "$composite_score"},
                    "high_tier_sessions": {
                        "$sum": {"$cond": [{"$eq": ["$momentum_tier", "HIGH"]}, 1, 0]}
                    },
                    "medium_tier_sessions": {
                        "$sum": {"$cond": [{"$eq": ["$momentum_tier", "MEDIUM"]}, 1, 0]}
                    },
                    "low_tier_sessions": {
                        "$sum": {"$cond": [{"$eq": ["$momentum_tier", "LOW"]}, 1, 0]}
                    },
                    "critical_tier_sessions": {
                        "$sum": {"$cond": [{"$eq": ["$momentum_tier", "CRITICAL"]}, 1, 0]}
                    },
                    "bridges_delivered": {
                        "$sum": {"$cond": ["$bridge_delivered", 1, 0]}
                    },
                    "bridges_responded": {
                        "$sum": {"$cond": ["$bridge_responded", 1, 0]}
                    },
                    "post_vision_exits": {
                        "$sum": {"$cond": [{"$eq": ["$artifact_at_exit", "vision"]}, 1, 0]}
                    },
                }}
            ]

            agg_result = list(raw_db.momentum_snapshots.aggregate(pipeline))
            m = agg_result[0] if agg_result else {}

            total = m.get("total_sessions", 0)
            bridges_delivered = m.get("bridges_delivered", 0)

            if total == 0:
                return {
                    "period_days": days,
                    "total_sessions": 0,
                    "avg_momentum_score": None,
                    "tier_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "CRITICAL": 0},
                    "bridge_delivery_rate": None,
                    "bridge_response_rate": None,
                    "post_vision_exit_rate": None,
                    "status": "no_data"
                }

            return {
                "period_days": days,
                "total_sessions": total,
                "avg_momentum_score": round(m.get("avg_score", 0), 3),
                "tier_distribution": {
                    "HIGH": m.get("high_tier_sessions", 0),
                    "MEDIUM": m.get("medium_tier_sessions", 0),
                    "LOW": m.get("low_tier_sessions", 0),
                    "CRITICAL": m.get("critical_tier_sessions", 0),
                },
                "bridge_delivery_rate": round(bridges_delivered / total, 3),
                "bridge_response_rate": round(
                    m.get("bridges_responded", 0) / max(1, bridges_delivered), 3
                ) if bridges_delivered > 0 else None,
                # The primary metric we are solving for in v4.x series:
                "post_vision_exit_rate": round(
                    m.get("post_vision_exits", 0) / total, 3
                ),
                "status": "ok"
            }

        except Exception as e:
            logger.warning(f"Momentum health access failed: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def _get_reentry_health(self, days: int = 7) -> dict:
        """
        v4.2: Get re-entry and re-engagement health metrics.

        Aggregates:
        - Re-entry openings delivered (momentum-aware first turns)
        - Async re-engagement messages sent and resumption rates
        - Coaching cadence opt-in statistics

        Args:
            days: Number of days to aggregate

        Returns:
            Re-entry health summary dict
        """
        if self.db is None:
            return {
                "status": "unavailable",
                "reason": "Database connection not provided"
            }

        try:
            from datetime import timedelta
            raw_db = self.db.db if hasattr(self.db, 'db') else self.db
            since = datetime.now(timezone.utc) - timedelta(days=days)

            # Re-entry openings delivered (from reentry_events collection)
            reentry_events = list(raw_db.reentry_events.aggregate([
                {"$match": {
                    "event_type": "opening_delivered",
                    "timestamp": {"$gte": since}
                }},
                {"$group": {
                    "_id": "$momentum_tier",
                    "count": {"$sum": 1},
                    "avg_gap_hours": {"$avg": "$gap_hours"}
                }}
            ]))

            reentry_total = sum(e["count"] for e in reentry_events)
            reentry_by_tier = {
                (e["_id"] or "unknown"): {
                    "count": e["count"],
                    "avg_gap_hours": round(e.get("avg_gap_hours") or 0, 1)
                }
                for e in reentry_events
            }

            # Async re-engagement analytics
            reengagement_total = raw_db.reengagement_events.count_documents(
                {"sent_at": {"$gte": since}}
            )
            reengagement_resumed = raw_db.reengagement_events.count_documents(
                {"sent_at": {"$gte": since}, "session_resumed": True}
            )
            reengagement_opened = raw_db.reengagement_events.count_documents(
                {"sent_at": {"$gte": since}, "opened": True}
            )

            # Coaching cadence opt-in statistics
            total_users = raw_db.users.count_documents({})
            opted_in = raw_db.users.count_documents(
                {"preferences.coaching_cadence": {"$in": ["gentle", "active"]}}
            )

            return {
                "period_days": days,

                # Re-entry openings (momentum-aware first turns for returning users)
                "reentry_openings_delivered": reentry_total,
                "reentry_by_momentum_tier": reentry_by_tier,

                # Async re-engagement (the async outreach pipeline)
                "reengagement_messages_sent": reengagement_total,
                "reengagement_open_rate": round(
                    reengagement_opened / max(1, reengagement_total), 3
                ),
                "reengagement_resumption_rate": round(
                    reengagement_resumed / max(1, reengagement_total), 3
                ),
                # Target: ≥30% resumption rate (from v4.0 roadmap success metrics)

                # Opt-in rate
                "coaching_cadence_opted_in": opted_in,
                "coaching_cadence_opt_in_rate": round(
                    opted_in / max(1, total_users), 3
                ),

                "status": "ok"
            }

        except Exception as e:
            logger.warning(f"Re-entry health access failed: {e}")
            return {
                "status": "error",
                "reason": str(e)
            }

    def _get_recent_errors(self, limit: int = 20) -> list:
        """
        Get recent error entries from the buffer.

        Args:
            limit: Maximum entries to return

        Returns:
            List of error entries
        """
        try:
            return error_buffer.get_recent(limit=limit)
        except Exception as e:
            logger.warning(f"Error buffer access failed: {e}")
            return []


# Module-level convenience function
def get_diagnostics(db=None, include_errors: bool = True, error_limit: int = 20) -> dict:
    """
    Convenience function to collect all diagnostics.

    Args:
        db: Database instance
        include_errors: Whether to include recent error entries
        error_limit: Maximum number of error entries

    Returns:
        Combined diagnostics dict
    """
    aggregator = DiagnosticsAggregator(db)
    return aggregator.collect_all(include_errors=include_errors, error_limit=error_limit)
