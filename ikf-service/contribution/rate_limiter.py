"""
InDE v3.2 - Contribution Rate Limiter
Prevents contribution fatigue by limiting auto-preparation frequency.

Rules:
- Max 3 packages queued for review per user at any time
- Min 24-hour cooldown between same-type auto-preparations
- pursuit.completed triggers take priority over periodic triggers
- Respects user contribution preferences
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

logger = logging.getLogger("inde.ikf.rate_limiter")


class ContributionRateLimiter:
    """
    Prevents contribution fatigue by limiting auto-preparation frequency.

    Rules:
    - Max 3 packages queued for review per user at any time
    - Min 24-hour cooldown between same-type auto-preparations
    - pursuit.completed triggers take priority over periodic triggers
    - Respects user contribution preferences
    """

    def __init__(self, db, max_pending: int = 3, cooldown_hours: int = 24):
        """
        Initialize rate limiter.

        Args:
            db: MongoDB database instance
            max_pending: Maximum pending contributions per user
            cooldown_hours: Minimum hours between same-type auto-preparations
        """
        self._db = db
        self._max_pending = max_pending
        self._cooldown = timedelta(hours=cooldown_hours)

    def can_auto_prepare(
        self,
        user_id: str,
        package_type: str,
        trigger_priority: str = "normal"
    ) -> Tuple[bool, str]:
        """
        Check if auto-preparation is allowed.

        Args:
            user_id: User to check
            package_type: Type of package being prepared
            trigger_priority: "high" for pursuit.completed, "normal" otherwise

        Returns: (allowed: bool, reason: str)
        """
        # Check user preferences
        user = self._db.users.find_one({"_id": user_id})
        if user:
            pref = user.get("ikf_preferences", {}).get("sharing_level", "MODERATE")
            if pref == "NONE":
                return False, "User has disabled IKF contributions"
            if pref == "MINIMAL" and trigger_priority != "high":
                return False, "User set MINIMAL — only pursuit.completed triggers allowed"

        # Check pending count
        pending = self._db.ikf_contributions.count_documents({
            "user_id": user_id,
            "status": "DRAFT"
        })
        if pending >= self._max_pending:
            return False, f"Max pending ({self._max_pending}) reached"

        # Check cooldown for same package type
        cutoff = datetime.now(timezone.utc) - self._cooldown
        recent = self._db.ikf_contributions.find_one({
            "user_id": user_id,
            "package_type": package_type,
            "auto_triggered": True,
            "created_at": {"$gte": cutoff}
        })
        if recent and trigger_priority != "high":
            hours_remaining = self._cooldown_remaining(recent["created_at"])
            return False, f"Cooldown active for {package_type} ({hours_remaining}h remaining)"

        return True, "OK"

    def _cooldown_remaining(self, created_at: datetime) -> int:
        """Calculate hours remaining in cooldown."""
        elapsed = datetime.now(timezone.utc) - created_at
        remaining = self._cooldown - elapsed
        return max(0, int(remaining.total_seconds() / 3600))

    def get_user_status(self, user_id: str) -> dict:
        """
        Get rate limiter status for a user.

        Returns:
            {
                'pending_count': int,
                'max_pending': int,
                'recent_by_type': {type: datetime},
                'cooldown_hours': int,
                'sharing_level': str
            }
        """
        # Get pending count
        pending = self._db.ikf_contributions.count_documents({
            "user_id": user_id,
            "status": "DRAFT"
        })

        # Get recent by type
        cutoff = datetime.now(timezone.utc) - self._cooldown
        recent_docs = self._db.ikf_contributions.find({
            "user_id": user_id,
            "auto_triggered": True,
            "created_at": {"$gte": cutoff}
        })
        recent_by_type = {}
        for doc in recent_docs:
            pkg_type = doc.get("package_type")
            if pkg_type:
                recent_by_type[pkg_type] = doc.get("created_at")

        # Get user preferences
        user = self._db.users.find_one({"_id": user_id})
        sharing_level = "MODERATE"
        if user:
            sharing_level = user.get("ikf_preferences", {}).get("sharing_level", "MODERATE")

        return {
            "pending_count": pending,
            "max_pending": self._max_pending,
            "recent_by_type": recent_by_type,
            "cooldown_hours": int(self._cooldown.total_seconds() / 3600),
            "sharing_level": sharing_level
        }

    def reset_cooldown(self, user_id: str, package_type: str = None) -> bool:
        """
        Reset cooldown for a user (admin function).

        Args:
            user_id: User to reset
            package_type: Specific type to reset, or None for all

        Returns:
            True if reset was applied
        """
        query = {"user_id": user_id, "auto_triggered": True}
        if package_type:
            query["package_type"] = package_type

        # Set created_at to old date to bypass cooldown
        old_date = datetime.now(timezone.utc) - self._cooldown - timedelta(hours=1)
        result = self._db.ikf_contributions.update_many(
            query,
            {"$set": {"created_at": old_date}}
        )

        logger.info(f"Reset cooldown for user {user_id}: {result.modified_count} records")
        return result.modified_count > 0
