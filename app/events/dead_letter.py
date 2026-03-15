"""
InDE v3.2 - Dead Letter Queue
Manages events that failed processing after max retries.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional

logger = logging.getLogger("inde.events.deadletter")


class DeadLetterQueue:
    """
    Manages events that failed processing after max retries.

    Dead letters are persisted to MongoDB for admin review.
    Supports retry, purge, and stats operations.
    """

    def __init__(self, db):
        """
        Initialize dead letter queue.

        Args:
            db: Database instance
        """
        self._db = db

    def get_dead_letters(
        self,
        limit: int = 50,
        consumer_group: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[dict]:
        """
        Retrieve dead letter events for admin review.

        Args:
            limit: Maximum number of events to return
            consumer_group: Filter by consumer group
            since: Only return events since this timestamp

        Returns:
            List of dead letter documents
        """
        query = {}
        if consumer_group:
            query["consumer_group"] = consumer_group
        if since:
            query["failed_at"] = {"$gte": since}

        return list(
            self._db.db.event_dead_letters
            .find(query)
            .sort("failed_at", -1)
            .limit(limit)
        )

    def get_stats(self) -> dict:
        """
        Get dead letter queue statistics.

        Returns:
            Dict with count by consumer group and total
        """
        pipeline = [
            {"$group": {
                "_id": "$consumer_group",
                "count": {"$sum": 1},
                "oldest": {"$min": "$failed_at"},
                "newest": {"$max": "$failed_at"}
            }},
            {"$sort": {"count": -1}}
        ]

        groups = list(self._db.db.event_dead_letters.aggregate(pipeline))
        total = sum(g["count"] for g in groups)

        return {
            "total": total,
            "by_group": {
                g["_id"]: {
                    "count": g["count"],
                    "oldest": g["oldest"],
                    "newest": g["newest"]
                }
                for g in groups
            }
        }

    def retry_event(self, event_id: str) -> bool:
        """
        Re-publish a dead letter event for reprocessing.

        Args:
            event_id: The event ID to retry

        Returns:
            True if event was found and re-emitted
        """
        doc = self._db.db.event_dead_letters.find_one({"event_id": event_id})
        if not doc:
            logger.warning(f"Dead letter not found: {event_id}")
            return False

        try:
            # Re-emit through the dispatcher
            from events.dispatcher import get_dispatcher
            from events.schemas import DomainEvent

            data = doc.get("data", {})
            event_data = data.get("data", "{}")

            # Parse the event and re-emit
            event = DomainEvent.model_validate_json(event_data)
            dispatcher = get_dispatcher()
            dispatcher.emit(event)

            # Remove from dead letter queue
            self._db.db.event_dead_letters.delete_one({"event_id": event_id})
            logger.info(f"Retried dead letter event: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to retry dead letter {event_id}: {e}")
            return False

    def retry_all(self, consumer_group: Optional[str] = None) -> int:
        """
        Retry all dead letter events, optionally filtered by consumer group.

        Args:
            consumer_group: Only retry events from this consumer group

        Returns:
            Number of events successfully retried
        """
        query = {}
        if consumer_group:
            query["consumer_group"] = consumer_group

        events = list(self._db.db.event_dead_letters.find(query))
        retried = 0

        for doc in events:
            if self.retry_event(doc["event_id"]):
                retried += 1

        logger.info(f"Retried {retried}/{len(events)} dead letter events")
        return retried

    def purge_old(self, days: int = 30) -> int:
        """
        Remove dead letters older than specified days.

        Args:
            days: Remove events older than this many days

        Returns:
            Number of events purged
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = self._db.db.event_dead_letters.delete_many({
            "failed_at": {"$lt": cutoff}
        })
        logger.info(f"Purged {result.deleted_count} dead letter events older than {days} days")
        return result.deleted_count

    def purge_by_group(self, consumer_group: str) -> int:
        """
        Remove all dead letters for a specific consumer group.

        Args:
            consumer_group: Consumer group to purge

        Returns:
            Number of events purged
        """
        result = self._db.db.event_dead_letters.delete_many({
            "consumer_group": consumer_group
        })
        logger.info(f"Purged {result.deleted_count} dead letters for group '{consumer_group}'")
        return result.deleted_count
