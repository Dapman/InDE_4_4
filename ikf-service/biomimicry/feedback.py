"""
Biomimicry Feedback Tracker

Records innovator responses to biomimicry coaching offers and updates
pattern effectiveness scores. Feeds the organizational learning loop.

Response types:
- explored: Innovator asked follow-up questions (engagement signal)
- accepted: Innovator applied insight to their pursuit (strong positive)
- deferred: Innovator saved for later (weak positive)
- dismissed: Innovator said "not relevant" (negative signal)

This module also handles:
- Pattern effectiveness scoring (acceptance_rate, feedback_scores)
- Intelligence Panel storage for deferred insights
- Event emission for analytics and federation
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("inde.ikf.biomimicry.feedback")


class BiomimicryFeedback:
    """
    Tracks innovator responses to biomimicry insights.

    The feedback loop is critical for:
    1. Improving pattern effectiveness scores (better patterns surface first)
    2. Avoiding dismissed patterns (don't re-offer what was rejected)
    3. Feeding organizational learning through IKF federation
    4. Storing deferred insights for later access

    All feedback events are emitted for downstream processing.
    """

    def __init__(self, db, event_publisher):
        """
        Initialize the Biomimicry Feedback tracker.

        Args:
            db: MongoDB database instance
            event_publisher: Event publisher for emitting biomimicry events
        """
        self._db = db
        self._events = event_publisher

    async def record_response(
        self,
        match_id: str,
        pattern_id: str,
        pursuit_id: str,
        response: str,  # explored | accepted | deferred | dismissed
        feedback_rating: Optional[int] = None,  # 1-5
        methodology: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record innovator's response to a biomimicry coaching offer.

        This is the main entry point called when an innovator responds
        to a biomimicry insight (via coaching interaction or explicit action).

        Args:
            match_id: The biomimicry match ID
            pattern_id: The pattern that was offered
            pursuit_id: The pursuit context
            response: One of: explored, accepted, deferred, dismissed
            feedback_rating: Optional 1-5 rating if provided
            methodology: Active methodology at time of response

        Returns:
            Result dict with status and updated pattern stats
        """
        valid_responses = ["explored", "accepted", "deferred", "dismissed"]
        if response not in valid_responses:
            raise ValueError(f"Invalid response: {response}. Must be one of {valid_responses}")

        now = datetime.now(timezone.utc)

        # Update match record
        update_result = self._db.biomimicry_matches.update_one(
            {"match_id": match_id},
            {"$set": {
                "innovator_response": response,
                "feedback_rating": feedback_rating,
                "methodology": methodology,
                "responded_at": now
            }}
        )

        if update_result.modified_count == 0:
            logger.warning(f"Match not found for update: {match_id}")

        # Update pattern effectiveness
        pattern_stats = await self._update_pattern_effectiveness(
            pattern_id, response, feedback_rating
        )

        # Emit event
        event_type = f"biomimicry.insight_{response}"
        if self._events:
            await self._events.publish(event_type, {
                "match_id": match_id,
                "pattern_id": pattern_id,
                "pursuit_id": pursuit_id,
                "response": response,
                "methodology": methodology,
                "feedback_rating": feedback_rating,
                "timestamp": now.isoformat()
            })

        # If deferred, store in Intelligence Panel
        if response == "deferred":
            await self._store_deferred_insight(match_id, pattern_id, pursuit_id)

        logger.info(
            f"Recorded biomimicry response: {response} for pattern {pattern_id} "
            f"(match: {match_id})"
        )

        return {
            "status": "recorded",
            "response": response,
            "pattern_stats": pattern_stats
        }

    async def _update_pattern_effectiveness(
        self, pattern_id: str, response: str, rating: Optional[int]
    ) -> Dict[str, Any]:
        """
        Update biomimicry pattern acceptance rate and scores.

        The effectiveness algorithm:
        - match_count: Incremented for every response
        - acceptance_rate: (accepted count) / (total responses)
        - feedback_scores: Array of ratings for calculating average

        Explored is counted as 0.5 acceptance (engagement but not full adoption).
        Deferred is counted as 0.25 (some interest but delayed).
        Dismissed is counted as 0 (rejection).

        Args:
            pattern_id: The pattern to update
            response: The innovator's response
            rating: Optional feedback rating

        Returns:
            Updated pattern stats
        """
        pattern = self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})
        if not pattern:
            return {"error": "pattern_not_found"}

        # Calculate new stats
        old_match_count = pattern.get("match_count", 0)
        old_acceptance_rate = pattern.get("acceptance_rate", 0.0)

        # Weighted response values
        response_weights = {
            "accepted": 1.0,
            "explored": 0.5,
            "deferred": 0.25,
            "dismissed": 0.0
        }
        response_value = response_weights.get(response, 0.0)

        # Recalculate acceptance rate
        new_match_count = old_match_count + 1
        total_weighted = (old_acceptance_rate * old_match_count) + response_value
        new_acceptance_rate = total_weighted / new_match_count

        update = {
            "$set": {
                "match_count": new_match_count,
                "acceptance_rate": new_acceptance_rate,
                "updated_at": datetime.now(timezone.utc)
            }
        }

        if rating is not None:
            update["$push"] = {"feedback_scores": rating}

        self._db.biomimicry_patterns.update_one(
            {"pattern_id": pattern_id},
            update
        )

        return {
            "pattern_id": pattern_id,
            "match_count": new_match_count,
            "acceptance_rate": new_acceptance_rate
        }

    async def _store_deferred_insight(
        self, match_id: str, pattern_id: str, pursuit_id: str
    ):
        """
        Store deferred insight in Intelligence Panel for later access.

        Deferred insights appear in the Intelligence Panel so innovators
        can revisit them later without losing track.
        """
        pattern = self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})
        if not pattern:
            return

        # Check if already stored
        existing = self._db.intelligence_panel_items.find_one({
            "pursuit_id": pursuit_id,
            "type": "biomimicry_deferred",
            "pattern_id": pattern_id
        })
        if existing:
            return

        self._db.intelligence_panel_items.insert_one({
            "pursuit_id": pursuit_id,
            "type": "biomimicry_deferred",
            "source_match_id": match_id,
            "pattern_id": pattern_id,
            "organism": pattern.get("organism", ""),
            "strategy_name": pattern.get("strategy_name", ""),
            "description": pattern.get("description", "")[:200],
            "category": pattern.get("category", ""),
            "status": "deferred",
            "created_at": datetime.now(timezone.utc)
        })

        logger.debug(f"Stored deferred insight for pursuit {pursuit_id}: {pattern_id}")

    async def get_deferred_insights(self, pursuit_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve deferred biomimicry insights for a pursuit.

        Returns insights that were deferred for later consideration.
        """
        items = list(self._db.intelligence_panel_items.find({
            "pursuit_id": pursuit_id,
            "type": "biomimicry_deferred",
            "status": "deferred"
        }))
        return items

    async def activate_deferred_insight(
        self, pursuit_id: str, pattern_id: str
    ) -> bool:
        """
        Activate a previously deferred insight.

        Called when an innovator revisits a deferred insight and
        wants to explore or apply it.
        """
        result = self._db.intelligence_panel_items.update_one(
            {
                "pursuit_id": pursuit_id,
                "type": "biomimicry_deferred",
                "pattern_id": pattern_id,
                "status": "deferred"
            },
            {"$set": {
                "status": "activated",
                "activated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    async def get_pattern_feedback_summary(
        self, pattern_id: str
    ) -> Dict[str, Any]:
        """
        Get feedback summary for a specific pattern.

        Returns:
            Dict with match_count, acceptance_rate, response breakdown,
            and average rating.
        """
        pattern = self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})
        if not pattern:
            return {"error": "pattern_not_found"}

        # Get response breakdown
        pipeline = [
            {"$match": {"pattern_id": pattern_id}},
            {"$group": {
                "_id": "$innovator_response",
                "count": {"$sum": 1}
            }}
        ]
        response_counts = list(self._db.biomimicry_matches.aggregate(pipeline))
        response_breakdown = {r["_id"]: r["count"] for r in response_counts}

        # Calculate average rating
        feedback_scores = pattern.get("feedback_scores", [])
        avg_rating = sum(feedback_scores) / len(feedback_scores) if feedback_scores else None

        return {
            "pattern_id": pattern_id,
            "organism": pattern.get("organism"),
            "strategy_name": pattern.get("strategy_name"),
            "match_count": pattern.get("match_count", 0),
            "acceptance_rate": pattern.get("acceptance_rate", 0.0),
            "response_breakdown": response_breakdown,
            "average_rating": avg_rating,
            "rating_count": len(feedback_scores)
        }

    async def get_pursuit_biomimicry_history(
        self, pursuit_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all biomimicry interactions for a pursuit.

        Returns chronological list of all biomimicry matches and responses
        for the specified pursuit.
        """
        matches = list(
            self._db.biomimicry_matches.find({"pursuit_id": pursuit_id})
            .sort("created_at", 1)
        )

        # Enrich with pattern info
        enriched = []
        for match in matches:
            pattern = self._db.biomimicry_patterns.find_one(
                {"pattern_id": match.get("pattern_id")}
            )
            enriched.append({
                "match_id": match.get("match_id"),
                "pattern_id": match.get("pattern_id"),
                "organism": pattern.get("organism", "") if pattern else "",
                "strategy_name": pattern.get("strategy_name", "") if pattern else "",
                "match_score": match.get("match_score"),
                "response": match.get("innovator_response"),
                "feedback_rating": match.get("feedback_rating"),
                "created_at": match.get("created_at"),
                "responded_at": match.get("responded_at")
            })

        return enriched
