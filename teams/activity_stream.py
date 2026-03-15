"""
InDE MVP v3.3 - Activity Stream Service
Real-time collaboration event tracking and persistence.

Features:
- Redis Stream consumer for team activity events
- MongoDB persistence for activity history
- Activity aggregation and summarization
- Mention extraction and notification triggering
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json

from database import db
from config import ACTIVITY_EVENT_TYPES, TEAM_EVENT_TYPES

logger = logging.getLogger("inde.teams.activity")


class ActivityStreamService:
    """
    Activity stream management for team collaboration.

    Handles event persistence, aggregation, and retrieval.
    """

    def __init__(self, redis_client=None, event_dispatcher=None):
        """
        Initialize activity stream service.

        Args:
            redis_client: Optional Redis client for stream consumption
            event_dispatcher: Optional event dispatcher for emitting events
        """
        self.db = db
        self.redis_client = redis_client
        self.event_dispatcher = event_dispatcher
        self.running = False

    async def start_consumer(self):
        """
        Start Redis stream consumer for activity events.

        Consumes events from the activity stream and persists to MongoDB.
        """
        if not self.redis_client:
            logger.warning("No Redis client configured, activity consumer not starting")
            return

        self.running = True
        stream_key = "inde:activity_events"
        consumer_group = "activity-persister"
        consumer_name = "activity-consumer-1"

        # Create consumer group if not exists
        try:
            await self.redis_client.xgroup_create(
                stream_key, consumer_group, id='0', mkstream=True
            )
        except Exception:
            pass  # Group already exists

        logger.info(f"Activity stream consumer started for {stream_key}")

        while self.running:
            try:
                # Read from stream
                messages = await self.redis_client.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {stream_key: '>'},
                    count=10,
                    block=5000
                )

                for stream, message_list in messages:
                    for message_id, data in message_list:
                        try:
                            await self._process_activity_message(data)
                            # Acknowledge message
                            await self.redis_client.xack(stream_key, consumer_group, message_id)
                        except Exception as e:
                            logger.error(f"Error processing activity message: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Activity consumer error: {e}")
                await asyncio.sleep(1)

        logger.info("Activity stream consumer stopped")

    async def stop_consumer(self):
        """Stop the activity stream consumer."""
        self.running = False

    async def _process_activity_message(self, data: Dict):
        """
        Process and persist an activity message.

        Args:
            data: Raw message data from Redis stream
        """
        # Parse event data
        event_type = data.get("event_type", "").decode() if isinstance(data.get("event_type"), bytes) else data.get("event_type", "")
        payload_str = data.get("payload", "{}").decode() if isinstance(data.get("payload"), bytes) else data.get("payload", "{}")

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            payload = {}

        # Build activity event record
        event_data = {
            "event_type": event_type,
            "pursuit_id": payload.get("pursuit_id"),
            "org_id": payload.get("org_id"),
            "actor_id": payload.get("actor_id") or payload.get("user_id"),
            "payload": {
                "summary": self._generate_summary(event_type, payload),
                "details": payload,
                "mentions": self._extract_mentions(payload)
            }
        }

        # Persist to MongoDB
        event_id = self.db.create_activity_event(event_data)
        logger.debug(f"Persisted activity event {event_id}: {event_type}")

    def _generate_summary(self, event_type: str, payload: Dict) -> str:
        """Generate human-readable summary for an event."""
        summaries = {
            "element.contributed": lambda p: f"contributed a {p.get('element_type', 'element')} element",
            "artifact.created": lambda p: f"created a {p.get('artifact_type', 'artifact')}",
            "session.started": lambda p: "started a coaching session",
            "session.completed": lambda p: "completed a coaching session",
            "state.changed": lambda p: f"changed state to {p.get('new_state', 'unknown')}",
            "member.joined": lambda p: "joined the team",
            "member.departed": lambda p: "left the team",
            "mention.created": lambda p: f"mentioned {len(p.get('mentioned_users', []))} team member(s)",
            "risk.evidence.submitted": lambda p: f"submitted evidence for {p.get('risk_name', 'a risk')}",
            "convergence.detected": lambda p: f"reached convergence on {p.get('area', 'an area')}",
            "report.generated": lambda p: f"generated a {p.get('report_type', 'report')}",
            "team.member.added": lambda p: f"added a team member as {p.get('role', 'member')}",
            "team.member.departed": lambda p: "removed a team member",
            "team.role.changed": lambda p: f"changed role to {p.get('new_role', 'member')}",
            "team.gap.identified": lambda p: f"identified a gap in {p.get('element_type', 'scaffolding')}",
            "team.milestone.reached": lambda p: f"reached {p.get('label', 'a milestone')}",
            "org.created": lambda p: "created the organization",
            "org.member.joined": lambda p: "joined the organization",
        }

        generator = summaries.get(event_type, lambda p: event_type.replace(".", " "))
        return generator(payload)

    def _extract_mentions(self, payload: Dict) -> List[str]:
        """Extract mentioned user IDs from payload."""
        mentions = []

        # Direct mentions field
        if "mentions" in payload:
            mentions.extend(payload["mentions"])

        # Mentioned users list
        if "mentioned_users" in payload:
            mentions.extend(payload["mentioned_users"])

        # Suggested user in gap events
        if "suggested_user_id" in payload:
            mentions.append(payload["suggested_user_id"])

        return list(set(mentions))  # Dedupe

    def create_activity_event(self, event_type: str, pursuit_id: str = None,
                               org_id: str = None, actor_id: str = None,
                               details: Dict = None, mentions: List[str] = None) -> str:
        """
        Create an activity event directly (synchronous).

        For use when Redis is not available or for immediate persistence.

        Returns:
            Created event ID
        """
        event_data = {
            "event_type": event_type,
            "pursuit_id": pursuit_id,
            "org_id": org_id,
            "actor_id": actor_id,
            "payload": {
                "summary": self._generate_summary(event_type, details or {}),
                "details": details or {},
                "mentions": mentions or []
            }
        }

        return self.db.create_activity_event(event_data)

    def get_pursuit_activity(self, pursuit_id: str, limit: int = 50,
                              offset: int = 0, event_types: List[str] = None) -> List[Dict]:
        """
        Get activity events for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            limit: Max events to return
            offset: Pagination offset
            event_types: Optional filter by event types

        Returns:
            List of activity events
        """
        events = self.db.get_pursuit_activity(pursuit_id, limit, offset)

        if event_types:
            events = [e for e in events if e.get("event_type") in event_types]

        return events

    def get_org_activity(self, org_id: str, limit: int = 50,
                          offset: int = 0) -> List[Dict]:
        """
        Get activity events for an organization.

        Args:
            org_id: Organization ID
            limit: Max events to return
            offset: Pagination offset

        Returns:
            List of activity events
        """
        return self.db.get_org_activity(org_id, limit, offset)

    def get_user_notifications(self, user_id: str,
                                unread_only: bool = True) -> Dict:
        """
        Get notifications for a user (events mentioning them).

        Args:
            user_id: User ID
            unread_only: Only return unread notifications

        Returns:
            {
                "notifications": [...],
                "unread_count": int,
                "total_count": int
            }
        """
        mentions = self.db.get_user_mentions(user_id, unread_only)

        # Enrich with actor names
        for event in mentions:
            actor = self.db.get_user(event.get("actor_id"))
            event["actor_name"] = actor.get("name") if actor else "Unknown"
            event["is_read"] = user_id in event.get("read_by", [])

        unread = [e for e in mentions if not e.get("is_read", True)]

        return {
            "notifications": mentions,
            "unread_count": len(unread),
            "total_count": len(mentions)
        }

    def mark_as_read(self, user_id: str, event_ids: List[str]) -> int:
        """
        Mark activity events as read by user.

        Returns:
            Number of events marked
        """
        return self.db.mark_activity_read(event_ids, user_id)

    def aggregate_activity(self, pursuit_id: str = None, org_id: str = None,
                            since: datetime = None) -> Dict:
        """
        Aggregate activity statistics.

        Args:
            pursuit_id: Filter by pursuit
            org_id: Filter by org
            since: Only count events since this time

        Returns:
            {
                "total_events": int,
                "by_type": {...},
                "top_contributors": [...],
                "active_members": int
            }
        """
        # Get events
        if pursuit_id:
            events = self.db.get_pursuit_activity(pursuit_id, limit=1000)
        elif org_id:
            events = self.db.get_org_activity(org_id, limit=1000)
        else:
            return {}

        # Filter by time if specified
        if since:
            events = [e for e in events if e.get("timestamp", datetime.min) >= since]

        # Aggregate
        by_type = {}
        contributors = {}

        for event in events:
            # Count by type
            event_type = event.get("event_type", "unknown")
            by_type[event_type] = by_type.get(event_type, 0) + 1

            # Count by contributor
            actor_id = event.get("actor_id")
            if actor_id:
                contributors[actor_id] = contributors.get(actor_id, 0) + 1

        # Top contributors
        top_contributors = []
        for user_id, count in sorted(contributors.items(), key=lambda x: x[1], reverse=True)[:5]:
            user = self.db.get_user(user_id)
            top_contributors.append({
                "user_id": user_id,
                "user_name": user.get("name") if user else "Unknown",
                "event_count": count
            })

        return {
            "total_events": len(events),
            "by_type": by_type,
            "top_contributors": top_contributors,
            "active_members": len(contributors)
        }


# Singleton instance
activity_stream_service = ActivityStreamService()
