"""
InDE MVP v2.9 - Activity Feed
Track and display pursuit activity timeline.

Features:
- Log various activity types
- Retrieve chronological feed
- Filter by activity type
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import ACTIVITY_TYPES


class ActivityFeed:
    """
    Manage activity feed for pursuits.

    Tracks all significant events and provides a timeline
    view for collaboration and transparency.
    """

    def __init__(self, db):
        """
        Initialize the activity feed.

        Args:
            db: Database instance
        """
        self.db = db
        self.valid_types = ACTIVITY_TYPES

    def log_activity(self, pursuit_id: str, activity_type: str,
                     description: str, metadata: Dict = None,
                     actor_name: str = None) -> bool:
        """
        Record pursuit activity.

        Args:
            pursuit_id: ID of the pursuit
            activity_type: Type from ACTIVITY_TYPES
            description: Human-readable description
            metadata: Optional additional data
            actor_name: Name of who performed the action

        Returns:
            True if logged successfully
        """
        if activity_type not in self.valid_types:
            # Allow unknown types but log warning
            print(f"[ActivityFeed] Unknown activity type: {activity_type}")

        full_metadata = metadata or {}
        if actor_name:
            full_metadata["actor"] = actor_name

        return self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type=activity_type,
            description=description,
            metadata=full_metadata
        )

    def get_feed(self, pursuit_id: str, filters: List[str] = None,
                 limit: int = 50) -> List[Dict]:
        """
        Retrieve activity timeline.

        Args:
            pursuit_id: ID of the pursuit
            filters: Optional list of activity types to include
            limit: Maximum items to return

        Returns:
            Chronological list of activities (newest first)
        """
        feed = self.db.get_activity_feed(pursuit_id, limit=limit * 2)  # Get more for filtering

        if filters:
            feed = [
                item for item in feed
                if item.get("activity_type") in filters
            ]

        # Format for display
        formatted = [self._format_activity(item) for item in feed[:limit]]

        return formatted

    def get_feed_by_type(self, pursuit_id: str, activity_type: str) -> List[Dict]:
        """
        Get all activities of a specific type.

        Args:
            pursuit_id: ID of the pursuit
            activity_type: Type to filter by

        Returns:
            List of matching activities
        """
        return self.get_feed(pursuit_id, filters=[activity_type], limit=100)

    def _format_activity(self, activity: Dict) -> Dict:
        """Format activity for display."""
        activity_type = activity.get("activity_type", "unknown")

        # Get icon and color for activity type
        type_config = {
            "artifact_created": {"icon": "document_add", "color": "green"},
            "artifact_updated": {"icon": "document_edit", "color": "blue"},
            "decision_made": {"icon": "check", "color": "purple"},
            "stakeholder_feedback": {"icon": "users", "color": "orange"},
            "comment_added": {"icon": "message", "color": "gray"},
            "phase_transition": {"icon": "arrow_right", "color": "blue"},
            "risk_defined": {"icon": "warning", "color": "red"},
            "evidence_captured": {"icon": "clipboard", "color": "green"},
            "share_link_created": {"icon": "link", "color": "blue"},
            "share_link_revoked": {"icon": "link_off", "color": "red"},
            "mention_notification": {"icon": "at", "color": "blue"},
            "comment_resolved": {"icon": "check_circle", "color": "green"},
            "innovator_replied": {"icon": "reply", "color": "blue"}
        }.get(activity_type, {"icon": "circle", "color": "gray"})

        return {
            "timestamp": activity.get("timestamp"),
            "activity_type": activity_type,
            "description": activity.get("description"),
            "metadata": activity.get("metadata", {}),
            "icon": type_config["icon"],
            "color": type_config["color"],
            "formatted_time": self._format_timestamp(activity.get("timestamp"))
        }

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return ""

        if isinstance(timestamp, str):
            return timestamp

        now = datetime.now(timezone.utc)
        if hasattr(timestamp, 'date'):
            diff = now - timestamp

            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    if minutes == 0:
                        return "just now"
                    return f"{minutes}m ago"
                return f"{hours}h ago"
            elif diff.days == 1:
                return "yesterday"
            elif diff.days < 7:
                return f"{diff.days}d ago"
            else:
                return timestamp.strftime("%b %d, %Y")

        return str(timestamp)

    def get_activity_summary(self, pursuit_id: str, days: int = 7) -> Dict:
        """
        Get activity summary for a time period.

        Args:
            pursuit_id: ID of the pursuit
            days: Number of days to look back

        Returns:
            Dict with activity statistics
        """
        feed = self.get_feed(pursuit_id, limit=500)

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        summary = {
            "period_days": days,
            "total_activities": len(feed),
            "by_type": {},
            "daily_counts": {},
            "most_active_day": None,
            "activity_streak": 0
        }

        # Count by type
        for activity in feed:
            activity_type = activity.get("activity_type", "unknown")
            if activity_type not in summary["by_type"]:
                summary["by_type"][activity_type] = 0
            summary["by_type"][activity_type] += 1

            # Count by day
            timestamp = activity.get("timestamp")
            if timestamp and hasattr(timestamp, 'date'):
                day_str = timestamp.strftime("%Y-%m-%d")
                if day_str not in summary["daily_counts"]:
                    summary["daily_counts"][day_str] = 0
                summary["daily_counts"][day_str] += 1

        # Find most active day
        if summary["daily_counts"]:
            most_active = max(summary["daily_counts"], key=summary["daily_counts"].get)
            summary["most_active_day"] = {
                "date": most_active,
                "count": summary["daily_counts"][most_active]
            }

        return summary

    def get_public_feed(self, pursuit_id: str, limit: int = 20) -> List[Dict]:
        """
        Get activity feed suitable for public view (shared pursuits).

        Filters out internal activities.

        Args:
            pursuit_id: ID of the pursuit
            limit: Maximum items to return

        Returns:
            Filtered activity list
        """
        public_types = [
            "artifact_created",
            "artifact_updated",
            "decision_made",
            "phase_transition",
            "risk_defined",
            "evidence_captured"
        ]

        return self.get_feed(pursuit_id, filters=public_types, limit=limit)

    def format_for_display(self, feed: List[Dict], format_type: str = "list") -> str:
        """
        Format activity feed for display.

        Args:
            feed: List of activity items
            format_type: "list" or "timeline"

        Returns:
            Formatted string
        """
        if not feed:
            return "*No activity yet*"

        if format_type == "timeline":
            lines = ["### Activity Timeline\n"]
            for item in feed:
                time = item.get("formatted_time", "")
                desc = item.get("description", "")
                lines.append(f"- **{time}**: {desc}")
            return "\n".join(lines)

        else:  # list format
            lines = []
            for item in feed:
                time = item.get("formatted_time", "")
                desc = item.get("description", "")
                lines.append(f"[{time}] {desc}")
            return "\n".join(lines)
