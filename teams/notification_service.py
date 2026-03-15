"""
InDE MVP v3.3 - Notification Service
Real-time notification delivery for team collaboration.

Features:
- Mention notifications
- Gap alert notifications
- Milestone celebrations
- Activity digests
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging

from database import db

logger = logging.getLogger("inde.teams.notifications")


class NotificationService:
    """
    Notification management for team collaboration.

    Handles notification creation, delivery, and preferences.
    """

    def __init__(self, event_dispatcher=None, websocket_manager=None):
        """
        Initialize notification service.

        Args:
            event_dispatcher: Event dispatcher for async notification
            websocket_manager: WebSocket manager for real-time delivery
        """
        self.db = db
        self.event_dispatcher = event_dispatcher
        self.websocket_manager = websocket_manager

    async def notify_mention(self, pursuit_id: str, actor_id: str,
                              mentioned_user_ids: List[str],
                              context: str = None) -> int:
        """
        Send mention notifications to users.

        Args:
            pursuit_id: Pursuit where mention occurred
            actor_id: User who made the mention
            mentioned_user_ids: Users who were mentioned
            context: Optional context/snippet

        Returns:
            Number of notifications sent
        """
        actor = self.db.get_user(actor_id)
        pursuit = self.db.get_pursuit(pursuit_id)

        count = 0
        for user_id in mentioned_user_ids:
            if user_id == actor_id:
                continue  # Don't notify self

            notification = {
                "type": "mention",
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit.get("title") if pursuit else "Unknown",
                "actor_id": actor_id,
                "actor_name": actor.get("name") if actor else "Someone",
                "context": context,
                "timestamp": datetime.now(timezone.utc)
            }

            # Send via WebSocket if available
            if self.websocket_manager:
                await self.websocket_manager.send_to_user(user_id, notification)

            count += 1
            logger.debug(f"Sent mention notification to {user_id}")

        return count

    async def notify_gap_opportunity(self, pursuit_id: str,
                                       suggested_user_id: str,
                                       element_type: str,
                                       gap_description: str = None) -> bool:
        """
        Notify user of a gap they can help address.

        Args:
            pursuit_id: Pursuit with the gap
            suggested_user_id: User suggested for the gap
            element_type: Type of element needed
            gap_description: Description of what's missing

        Returns:
            True if notification sent
        """
        pursuit = self.db.get_pursuit(pursuit_id)

        notification = {
            "type": "gap_opportunity",
            "pursuit_id": pursuit_id,
            "pursuit_title": pursuit.get("title") if pursuit else "A shared pursuit",
            "element_type": element_type,
            "description": gap_description or f"Your expertise with {element_type} could help fill a gap",
            "timestamp": datetime.now(timezone.utc)
        }

        if self.websocket_manager:
            await self.websocket_manager.send_to_user(suggested_user_id, notification)
            logger.info(f"Sent gap opportunity notification to {suggested_user_id}")
            return True

        return False

    async def notify_milestone(self, pursuit_id: str, milestone: Dict,
                                team_member_ids: List[str]) -> int:
        """
        Notify team of milestone achievement.

        Args:
            pursuit_id: Pursuit that reached milestone
            milestone: Milestone info
            team_member_ids: Team members to notify

        Returns:
            Number of notifications sent
        """
        pursuit = self.db.get_pursuit(pursuit_id)

        notification = {
            "type": "milestone",
            "pursuit_id": pursuit_id,
            "pursuit_title": pursuit.get("title") if pursuit else "Your pursuit",
            "milestone_label": milestone.get("label"),
            "completeness": milestone.get("completeness"),
            "timestamp": datetime.now(timezone.utc)
        }

        count = 0
        for user_id in team_member_ids:
            if self.websocket_manager:
                await self.websocket_manager.send_to_user(user_id, notification)
                count += 1

        logger.info(f"Sent milestone notification to {count} team members")
        return count

    async def notify_team_change(self, pursuit_id: str, change_type: str,
                                   affected_user_id: str,
                                   team_member_ids: List[str]) -> int:
        """
        Notify team of membership changes.

        Args:
            pursuit_id: Pursuit where change occurred
            change_type: joined | departed | role_changed
            affected_user_id: User affected by change
            team_member_ids: Other team members to notify

        Returns:
            Number of notifications sent
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        affected_user = self.db.get_user(affected_user_id)

        action_text = {
            "joined": "joined the team",
            "departed": "left the team",
            "role_changed": "had their role updated"
        }.get(change_type, change_type)

        notification = {
            "type": "team_change",
            "pursuit_id": pursuit_id,
            "pursuit_title": pursuit.get("title") if pursuit else "A shared pursuit",
            "change_type": change_type,
            "affected_user_name": affected_user.get("name") if affected_user else "A team member",
            "action": action_text,
            "timestamp": datetime.now(timezone.utc)
        }

        count = 0
        for user_id in team_member_ids:
            if user_id == affected_user_id:
                continue

            if self.websocket_manager:
                await self.websocket_manager.send_to_user(user_id, notification)
                count += 1

        return count

    def get_user_notification_preferences(self, user_id: str) -> Dict:
        """
        Get user's notification preferences.

        Returns:
            {
                "mentions": True,
                "milestones": True,
                "gaps": True,
                "team_changes": True,
                "digest_frequency": "daily"
            }
        """
        user = self.db.get_user(user_id)
        if not user:
            return {}

        preferences = user.get("preferences", {}).get("notifications", {})

        # Apply defaults
        defaults = {
            "mentions": True,
            "milestones": True,
            "gaps": True,
            "team_changes": True,
            "digest_frequency": "daily"
        }

        return {**defaults, **preferences}

    def update_notification_preferences(self, user_id: str,
                                          preferences: Dict) -> bool:
        """Update user's notification preferences."""
        user = self.db.get_user(user_id)
        if not user:
            return False

        current_prefs = user.get("preferences", {})
        current_prefs["notifications"] = preferences

        # Update user
        self.db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"preferences": current_prefs}}
        )

        return True

    def generate_activity_digest(self, user_id: str,
                                   period: str = "daily") -> Dict:
        """
        Generate activity digest for a user.

        Args:
            user_id: User ID
            period: daily | weekly

        Returns:
            Digest summary
        """
        # Calculate time range
        if period == "weekly":
            since = datetime.now(timezone.utc) - timedelta(days=7)
        else:
            since = datetime.now(timezone.utc) - timedelta(days=1)

        # Get user's pursuits (owned and shared)
        owned = self.db.get_user_pursuits(user_id)
        shared = self.db.get_user_shared_pursuits(user_id)

        all_pursuit_ids = [p.get("pursuit_id") for p in owned + shared]

        # Aggregate activity across pursuits
        total_events = 0
        pursuit_summaries = []

        for pursuit_id in all_pursuit_ids:
            events = self.db.get_pursuit_activity(pursuit_id, limit=100)
            recent_events = [e for e in events if e.get("timestamp", datetime.min) >= since]

            if recent_events:
                pursuit = self.db.get_pursuit(pursuit_id)
                pursuit_summaries.append({
                    "pursuit_id": pursuit_id,
                    "pursuit_title": pursuit.get("title") if pursuit else "Unknown",
                    "event_count": len(recent_events),
                    "latest_event": recent_events[0] if recent_events else None
                })
                total_events += len(recent_events)

        # Get mentions
        mentions = self.db.get_user_mentions(user_id, unread_only=True)

        return {
            "period": period,
            "since": since,
            "total_events": total_events,
            "pursuit_summaries": pursuit_summaries,
            "unread_mentions": len(mentions),
            "generated_at": datetime.now(timezone.utc)
        }


# Singleton instance
notification_service = NotificationService()
