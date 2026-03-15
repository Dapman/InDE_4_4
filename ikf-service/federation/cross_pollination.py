"""
Cross-Pollination Detection

Detects when an innovator successfully applies a pattern from a
different domain and creates contribution proposals for IKF pattern
enhancement.

Cross-pollination occurs when:
1. An IKF pattern from industry A is surfaced to an innovator in industry B
2. The innovator applies the pattern (detected via feedback tracking)
3. Success is observed (problem resolved, element completed, etc.)

This creates "domain bridge" contributions - patterns that have proven
to transfer across industries.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("inde.ikf.cross_pollination")


class CrossPollinationDetector:
    """
    Detects successful cross-domain pattern applications.

    Monitors pattern feedback events and correlates with
    pursuit progress to identify domain transfers.
    """

    def __init__(self, db, event_publisher, config):
        """
        Initialize the Cross-Pollination Detector.

        Args:
            db: MongoDB database instance
            event_publisher: Event publisher for notifications
            config: Configuration object
        """
        self._db = db
        self._publisher = event_publisher
        self._config = config

    async def on_pattern_applied(
        self,
        pattern_id: str,
        pursuit_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Called when a pattern is marked as "applied" by the innovator.

        Checks for cross-domain transfer and creates proposal if detected.

        Args:
            pattern_id: The applied pattern
            pursuit_id: The pursuit where it was applied
            user_id: The innovator

        Returns:
            CrossPollination event dict if detected, else None
        """
        # Get the pattern
        pattern = self._db.ikf_federation_patterns.find_one({"pattern_id": pattern_id})
        if not pattern:
            return None

        # Get the pursuit
        pursuit = self._db.pursuits.find_one({"pursuit_id": pursuit_id})
        if not pursuit:
            return None

        # Check for domain difference
        pattern_industries = pattern.get("applicability", {}).get("industries", [])
        pursuit_industry = pursuit.get("industry_code")

        if not pursuit_industry:
            return None

        # Skip if pattern already includes this industry or is universal
        if "ALL" in pattern_industries or pursuit_industry in pattern_industries:
            return None

        # Cross-pollination detected!
        event = {
            "type": "cross_pollination",
            "pattern_id": pattern_id,
            "pattern_source_industries": pattern_industries,
            "target_industry": pursuit_industry,
            "pursuit_id": pursuit_id,
            "user_id": user_id,
            "detected_at": datetime.now(timezone.utc)
        }

        # Record the event
        self._db.ikf_cross_pollination_events.insert_one(event)

        logger.info(
            f"Cross-pollination detected: pattern {pattern_id} "
            f"({pattern_industries} -> {pursuit_industry})"
        )

        # Publish event
        try:
            await self._publisher.publish_ikf_event("cross_pollination.detected", {
                "pattern_id": pattern_id,
                "source_industries": pattern_industries,
                "target_industry": pursuit_industry,
                "pursuit_id": pursuit_id
            })
        except Exception as e:
            logger.warning(f"Failed to publish cross_pollination event: {e}")

        return event

    async def check_success(
        self,
        pursuit_id: str,
        success_indicator: str
    ) -> List[Dict[str, Any]]:
        """
        Check if pending cross-pollination events should be confirmed.

        Called when positive signals are detected (problem resolved,
        element completed, phase transition, etc.)

        Args:
            pursuit_id: The pursuit showing success
            success_indicator: Type of success (element_completed, phase_transition, etc.)

        Returns:
            List of confirmed cross-pollination events
        """
        # Find pending cross-pollination events for this pursuit
        pending = list(self._db.ikf_cross_pollination_events.find({
            "pursuit_id": pursuit_id,
            "confirmed": {"$ne": True}
        }))

        confirmed = []
        for event in pending:
            # Create domain bridge proposal
            proposal = self._create_domain_bridge_proposal(event, success_indicator)

            # Update event as confirmed
            self._db.ikf_cross_pollination_events.update_one(
                {"_id": event["_id"]},
                {"$set": {
                    "confirmed": True,
                    "confirmed_at": datetime.now(timezone.utc),
                    "success_indicator": success_indicator,
                    "proposal_id": proposal.get("contribution_id")
                }}
            )

            confirmed.append(event)

            # Publish confirmation
            try:
                await self._publisher.publish_ikf_event("cross_pollination.confirmed", {
                    "pattern_id": event.get("pattern_id"),
                    "source_industries": event.get("pattern_source_industries"),
                    "target_industry": event.get("target_industry"),
                    "success_indicator": success_indicator,
                    "proposal_id": proposal.get("contribution_id")
                })
            except Exception as e:
                logger.warning(f"Failed to publish confirmation event: {e}")

        return confirmed

    def _create_domain_bridge_proposal(
        self,
        event: dict,
        success_indicator: str
    ) -> dict:
        """
        Create a domain bridge contribution proposal.

        This proposal suggests enhancing the original pattern to include
        the new industry in its applicability.

        Args:
            event: The cross-pollination event
            success_indicator: What success was observed

        Returns:
            Created contribution proposal dict
        """
        import uuid

        contribution_id = f"cp-{uuid.uuid4().hex[:12]}"

        proposal = {
            "contribution_id": contribution_id,
            "package_type": "domain_bridge",
            "status": "DRAFT",
            "auto_triggered": True,
            "source_pattern_id": event.get("pattern_id"),
            "source_industries": event.get("pattern_source_industries", []),
            "bridge_to_industry": event.get("target_industry"),
            "pursuit_id": event.get("pursuit_id"),
            "user_id": event.get("user_id"),
            "success_indicator": success_indicator,
            "created_at": datetime.now(timezone.utc),
            "generalized_content": {
                "type": "domain_bridge",
                "original_pattern_id": event.get("pattern_id"),
                "original_industries": event.get("pattern_source_industries", []),
                "new_industry": event.get("target_industry"),
                "application_outcome": success_indicator,
                "bridge_summary": (
                    f"Pattern originally applicable to {event.get('pattern_source_industries')} "
                    f"successfully applied in {event.get('target_industry')} context"
                ),
                "suggested_enhancement": (
                    f"Consider adding {event.get('target_industry')} to pattern applicability"
                )
            },
            "generalization_level": 2,  # Already generalized by nature
            "pii_scan": {"passed": True, "warnings": [], "high_confidence_flags": []}
        }

        self._db.ikf_contributions.insert_one(proposal)

        logger.info(
            f"Created domain bridge proposal {contribution_id} for pattern "
            f"{event.get('pattern_id')}"
        )

        return proposal

    def get_cross_pollination_stats(self) -> Dict[str, Any]:
        """Get cross-pollination statistics for admin dashboard."""
        total = self._db.ikf_cross_pollination_events.count_documents({})
        confirmed = self._db.ikf_cross_pollination_events.count_documents({"confirmed": True})

        # Get top industry bridges
        pipeline = [
            {"$match": {"confirmed": True}},
            {"$group": {
                "_id": {
                    "from": "$pattern_source_industries",
                    "to": "$target_industry"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        top_bridges = list(self._db.ikf_cross_pollination_events.aggregate(pipeline))

        return {
            "total_detected": total,
            "confirmed": confirmed,
            "confirmation_rate": confirmed / total if total > 0 else 0,
            "top_bridges": [
                {
                    "from": b["_id"]["from"],
                    "to": b["_id"]["to"],
                    "count": b["count"]
                }
                for b in top_bridges
            ]
        }
