"""
InDE MVP v2.7 - Portfolio Manager

Organizes pursuits by state and provides portfolio-level analytics.
Tracks terminal state distribution and learning accumulation.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from collections import Counter

from config import TERMINAL_STATES, SUSPENDED_STATES, DEMO_USER_ID


class PortfolioManager:
    """
    Manages innovation portfolio with terminal state tracking.
    """

    def __init__(self, database):
        """
        Initialize PortfolioManager.

        Args:
            database: Database instance
        """
        self.db = database

    def get_portfolio_summary(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        Get comprehensive portfolio summary for a user.

        Args:
            user_id: User ID

        Returns:
            {
                "total_pursuits": int,
                "state_distribution": {...},
                "completion_rate": float,
                "learning_velocity": float,
                "recent_activity": [...],
                "metrics": {...}
            }
        """
        pursuits = list(self.db.db.pursuits.find({"user_id": user_id}))

        if not pursuits:
            return self._empty_summary()

        # Calculate state distribution
        state_dist = self._calculate_state_distribution(pursuits)

        # Calculate metrics
        metrics = self._calculate_portfolio_metrics(pursuits, user_id)

        # Get recent activity
        recent = self._get_recent_activity(pursuits)

        return {
            "total_pursuits": len(pursuits),
            "state_distribution": state_dist,
            "active_count": state_dist.get("ACTIVE", 0),
            "completed_count": sum(state_dist.get(s, 0) for s in TERMINAL_STATES if s.startswith("COMPLETED")),
            "terminated_count": sum(state_dist.get(s, 0) for s in TERMINAL_STATES if s.startswith("TERMINATED")),
            "suspended_count": sum(state_dist.get(s, 0) for s in SUSPENDED_STATES),
            "completion_rate": metrics["completion_rate"],
            "learning_velocity": metrics["learning_velocity"],
            "patterns_extracted": metrics["patterns_extracted"],
            "recent_activity": recent,
            "metrics": metrics
        }

    def get_pursuits_by_state(self, user_id: str = DEMO_USER_ID,
                              state: str = None) -> List[Dict]:
        """
        Get pursuits filtered by state.

        Args:
            user_id: User ID
            state: State filter (or None for all)

        Returns:
            List of pursuit dicts
        """
        query = {"user_id": user_id}
        if state:
            query["state"] = state

        pursuits = list(self.db.db.pursuits.find(query).sort("updated_at", -1))

        # Enrich with summary data
        enriched = []
        for p in pursuits:
            enriched.append({
                "pursuit_id": p.get("pursuit_id"),
                "title": p.get("title"),
                "state": p.get("state", "ACTIVE"),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
                "terminal_info": p.get("terminal_info"),
                "learning_summary": p.get("learning_summary"),
                "has_retrospective": p.get("terminal_info", {}).get("retrospective_id") is not None
            })

        return enriched

    def get_terminal_pursuits(self, user_id: str = DEMO_USER_ID) -> List[Dict]:
        """Get all terminal pursuits."""
        pursuits = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "state": {"$in": TERMINAL_STATES}
        }).sort("updated_at", -1))

        return pursuits

    def get_active_pursuits(self, user_id: str = DEMO_USER_ID) -> List[Dict]:
        """Get all active pursuits."""
        return self.get_pursuits_by_state(user_id, "ACTIVE")

    def get_portfolio_timeline(self, user_id: str = DEMO_USER_ID,
                              days: int = 90) -> List[Dict]:
        """
        Get portfolio activity timeline.

        Args:
            user_id: User ID
            days: Number of days to include

        Returns:
            List of timeline events
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get pursuits created in period
        pursuits = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "created_at": {"$gte": cutoff}
        }))

        # Get retrospectives completed in period
        retros = list(self.db.db.retrospectives.find({
            "completed_at": {"$gte": cutoff}
        }))

        # Build timeline
        events = []

        for p in pursuits:
            events.append({
                "type": "pursuit_created",
                "timestamp": p.get("created_at"),
                "pursuit_id": p.get("pursuit_id"),
                "title": p.get("title")
            })

            if p.get("state") in TERMINAL_STATES:
                terminal_info = p.get("terminal_info", {})
                events.append({
                    "type": "pursuit_terminal",
                    "timestamp": terminal_info.get("terminated_at", p.get("updated_at")),
                    "pursuit_id": p.get("pursuit_id"),
                    "title": p.get("title"),
                    "state": p.get("state")
                })

        for r in retros:
            events.append({
                "type": "retrospective_completed",
                "timestamp": r.get("completed_at"),
                "pursuit_id": r.get("pursuit_id"),
                "retrospective_id": r.get("retrospective_id"),
                "patterns_extracted": r.get("patterns_extracted", 0)
            })

        # Sort by timestamp
        events.sort(key=lambda e: e.get("timestamp") or datetime.min, reverse=True)

        return events

    def get_learning_metrics(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        Get learning accumulation metrics.

        Args:
            user_id: User ID

        Returns:
            {
                "total_patterns": int,
                "patterns_by_type": {...},
                "fear_validation_rate": float,
                "hypothesis_validation_rate": float
            }
        """
        # Get all patterns for user's pursuits
        user_pursuits = [p["pursuit_id"] for p in self.db.db.pursuits.find({"user_id": user_id})]

        patterns = list(self.db.db.learning_patterns.find({
            "pursuit_id": {"$in": user_pursuits}
        }))

        # Count by type
        type_counts = Counter(p.get("pattern_type", "UNKNOWN") for p in patterns)

        # Get fear resolutions
        resolutions = list(self.db.db.fear_resolutions.find({
            "pursuit_id": {"$in": user_pursuits}
        }))

        fear_materialized = sum(1 for r in resolutions if r.get("materialized") is True)
        fear_unfounded = sum(1 for r in resolutions if r.get("materialized") is False)
        total_fears = len(resolutions)

        return {
            "total_patterns": len(patterns),
            "patterns_by_type": dict(type_counts),
            "total_fears_analyzed": total_fears,
            "fears_materialized": fear_materialized,
            "fears_unfounded": fear_unfounded,
            "fear_validation_rate": fear_materialized / total_fears if total_fears > 0 else 0.0
        }

    def update_portfolio_on_terminal(self, pursuit_id: str) -> bool:
        """
        Update portfolio tracking when pursuit reaches terminal state.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            True if updated successfully
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return False

        # Update terminal_info
        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "terminal_info.portfolio_updated": True,
                "terminal_info.portfolio_updated_at": datetime.now(timezone.utc)
            }}
        )

        return True

    def _calculate_state_distribution(self, pursuits: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of pursuits by state."""
        dist = Counter(p.get("state", "ACTIVE") for p in pursuits)
        return dict(dist)

    def _calculate_portfolio_metrics(self, pursuits: List[Dict],
                                     user_id: str) -> Dict:
        """Calculate portfolio-level metrics."""
        total = len(pursuits)

        # Completion rate
        completed = sum(1 for p in pursuits if p.get("state", "").startswith("COMPLETED"))
        terminal = sum(1 for p in pursuits if p.get("state") in TERMINAL_STATES)

        completion_rate = completed / terminal if terminal > 0 else 0.0

        # Learning velocity (patterns per month)
        user_pursuit_ids = [p["pursuit_id"] for p in pursuits]
        patterns = list(self.db.db.learning_patterns.find({
            "pursuit_id": {"$in": user_pursuit_ids}
        }))

        # Calculate time span
        if pursuits:
            oldest = min(p.get("created_at", datetime.now(timezone.utc)) for p in pursuits)
            if isinstance(oldest, str):
                try:
                    oldest = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
                except:
                    oldest = datetime.now(timezone.utc)
            # Ensure timezone-aware comparison
            if isinstance(oldest, datetime) and oldest.tzinfo is None:
                oldest = oldest.replace(tzinfo=timezone.utc)
            months = max(1, (datetime.now(timezone.utc) - oldest).days / 30)
            learning_velocity = len(patterns) / months
        else:
            learning_velocity = 0.0

        return {
            "total_pursuits": total,
            "terminal_pursuits": terminal,
            "completion_rate": completion_rate,
            "patterns_extracted": len(patterns),
            "learning_velocity": round(learning_velocity, 2),
            "avg_duration_days": self._calculate_avg_duration(pursuits)
        }

    def _calculate_avg_duration(self, pursuits: List[Dict]) -> float:
        """Calculate average pursuit duration for terminal pursuits."""
        durations = []
        for p in pursuits:
            if p.get("state") in TERMINAL_STATES:
                created = p.get("created_at")
                terminal_info = p.get("terminal_info", {})
                ended = terminal_info.get("terminated_at", p.get("updated_at"))

                if created and ended:
                    if isinstance(created, str):
                        try:
                            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except:
                            continue
                    if isinstance(ended, str):
                        try:
                            ended = datetime.fromisoformat(ended.replace("Z", "+00:00"))
                        except:
                            continue
                    # Ensure both are timezone-aware for comparison
                    if isinstance(created, datetime) and created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if isinstance(ended, datetime) and ended.tzinfo is None:
                        ended = ended.replace(tzinfo=timezone.utc)

                    durations.append((ended - created).days)

        return sum(durations) / len(durations) if durations else 0.0

    def _get_recent_activity(self, pursuits: List[Dict], limit: int = 5) -> List[Dict]:
        """Get recent portfolio activity."""
        sorted_pursuits = sorted(
            pursuits,
            key=lambda p: p.get("updated_at") or datetime.min,
            reverse=True
        )

        recent = []
        for p in sorted_pursuits[:limit]:
            recent.append({
                "pursuit_id": p.get("pursuit_id"),
                "title": p.get("title"),
                "state": p.get("state", "ACTIVE"),
                "updated_at": p.get("updated_at")
            })

        return recent

    def _empty_summary(self) -> Dict:
        """Return empty portfolio summary."""
        return {
            "total_pursuits": 0,
            "state_distribution": {},
            "active_count": 0,
            "completed_count": 0,
            "terminated_count": 0,
            "suspended_count": 0,
            "completion_rate": 0.0,
            "learning_velocity": 0.0,
            "patterns_extracted": 0,
            "recent_activity": [],
            "metrics": {}
        }
