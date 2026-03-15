"""
InDE MVP v3.3 - Team Scaffolding Engine
Element attribution, gap analysis, and expertise matching for shared pursuits.

Features:
- Element Attribution: Track who contributed each scaffolding element
- Gap Analysis: Identify missing elements and suggest who can address them
- Expertise Matching: Match team members to gaps based on contribution history
- Team Completeness: Aggregate view of team's collective contribution
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

from database import db
from config import CRITICAL_ELEMENTS

logger = logging.getLogger("inde.teams.scaffolding")


class TeamScaffoldingEngine:
    """
    Manages team scaffolding for shared pursuits.

    Tracks element attribution, analyzes gaps, and matches expertise
    to help teams collaboratively build complete artifacts.
    """

    def __init__(self, event_dispatcher=None):
        """
        Initialize team scaffolding engine.

        Args:
            event_dispatcher: Optional event dispatcher for team events
        """
        self.db = db
        self.event_dispatcher = event_dispatcher

    def attribute_element(self, pursuit_id: str, user_id: str,
                           element_type: str, element_name: str,
                           timestamp: datetime = None) -> Dict:
        """
        Attribute an element contribution to a user.

        Args:
            pursuit_id: Pursuit ID
            user_id: Contributing user ID
            element_type: vision | fears | hypothesis
            element_name: Element name (e.g., "problem_statement")
            timestamp: Contribution timestamp (default: now)

        Returns:
            Attribution record
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        # Get current team scaffolding data
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        team_scaffolding = pursuit.get("team_scaffolding", {
            "element_attribution": {},
            "team_completeness": 0.0,
            "member_contributions": {},
            "gap_analysis": {}
        })

        # Build element key
        element_key = f"{element_type}.{element_name}"

        # Record attribution
        team_scaffolding["element_attribution"][element_key] = {
            "user_id": user_id,
            "contributed_at": timestamp,
            "updated_at": timestamp
        }

        # Update member contribution count
        if user_id not in team_scaffolding["member_contributions"]:
            team_scaffolding["member_contributions"][user_id] = {
                "element_count": 0,
                "element_types": {},
                "first_contribution": timestamp,
                "last_contribution": timestamp
            }

        member_contrib = team_scaffolding["member_contributions"][user_id]
        member_contrib["element_count"] += 1
        member_contrib["last_contribution"] = timestamp

        if element_type not in member_contrib["element_types"]:
            member_contrib["element_types"][element_type] = 0
        member_contrib["element_types"][element_type] += 1

        # Recalculate team completeness
        team_scaffolding["team_completeness"] = self._calculate_team_completeness(
            team_scaffolding["element_attribution"]
        )

        # Save updates
        self.db.update_pursuit_team_scaffolding(pursuit_id, team_scaffolding)

        logger.info(f"Attributed {element_key} to user {user_id} in pursuit {pursuit_id}")

        return team_scaffolding["element_attribution"][element_key]

    def _calculate_team_completeness(self, attribution: Dict) -> float:
        """Calculate overall team completeness based on attributions."""
        total_elements = 0
        attributed_elements = 0

        for element_type, elements in CRITICAL_ELEMENTS.items():
            total_elements += len(elements)
            for element in elements:
                key = f"{element_type}.{element}"
                if key in attribution:
                    attributed_elements += 1

        return attributed_elements / total_elements if total_elements > 0 else 0.0

    def get_attribution_summary(self, pursuit_id: str) -> Dict:
        """
        Get element attribution summary for a pursuit.

        Returns:
            {
                "element_attribution": dict,
                "team_completeness": float,
                "member_contributions": dict,
                "by_member": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {}

        team_scaffolding = pursuit.get("team_scaffolding", {})
        attribution = team_scaffolding.get("element_attribution", {})
        contributions = team_scaffolding.get("member_contributions", {})

        # Build member summary with names
        by_member = []
        for user_id, stats in contributions.items():
            user = self.db.get_user(user_id)
            by_member.append({
                "user_id": user_id,
                "user_name": user.get("name") if user else "Unknown",
                "element_count": stats.get("element_count", 0),
                "element_types": stats.get("element_types", {}),
                "first_contribution": stats.get("first_contribution"),
                "last_contribution": stats.get("last_contribution")
            })

        # Sort by contribution count
        by_member.sort(key=lambda x: x["element_count"], reverse=True)

        return {
            "element_attribution": attribution,
            "team_completeness": team_scaffolding.get("team_completeness", 0.0),
            "member_contributions": contributions,
            "by_member": by_member
        }

    def analyze_gaps(self, pursuit_id: str) -> Dict:
        """
        Analyze scaffolding gaps and suggest expertise matches.

        Returns:
            {
                "missing_elements": [...],
                "gap_by_type": {vision: [...], fears: [...], hypothesis: [...]},
                "expertise_suggestions": [...],
                "critical_gaps": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {}

        # Get current scaffolding state
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        if not scaffolding:
            scaffolding = {}

        team_scaffolding = pursuit.get("team_scaffolding", {})
        attribution = team_scaffolding.get("element_attribution", {})

        missing_elements = []
        gap_by_type = {"vision": [], "fears": [], "hypothesis": []}
        critical_gaps = []

        # Identify missing elements
        for element_type, elements in CRITICAL_ELEMENTS.items():
            type_key = f"{element_type}_elements"
            if element_type == "fears":
                type_key = "fear_elements"

            elements_data = scaffolding.get(type_key, {})

            for element in elements:
                element_data = elements_data.get(element)
                if not element_data or not element_data.get("text"):
                    missing_elements.append({
                        "element_type": element_type,
                        "element_name": element,
                        "key": f"{element_type}.{element}"
                    })
                    gap_by_type[element_type].append(element)

                    # Critical elements for each type (first 3 are most critical)
                    if elements.index(element) < 3:
                        critical_gaps.append({
                            "element_type": element_type,
                            "element_name": element,
                            "priority": "high"
                        })

        # Get expertise suggestions from team members
        expertise_suggestions = self._match_expertise_to_gaps(
            pursuit_id, gap_by_type
        )

        # Save gap analysis
        team_scaffolding["gap_analysis"] = {
            "missing_count": len(missing_elements),
            "by_type": {k: len(v) for k, v in gap_by_type.items()},
            "critical_count": len(critical_gaps),
            "analyzed_at": datetime.now(timezone.utc)
        }
        self.db.update_pursuit_team_scaffolding(pursuit_id, team_scaffolding)

        return {
            "missing_elements": missing_elements,
            "gap_by_type": gap_by_type,
            "expertise_suggestions": expertise_suggestions,
            "critical_gaps": critical_gaps
        }

    def _match_expertise_to_gaps(self, pursuit_id: str,
                                   gaps_by_type: Dict) -> List[Dict]:
        """
        Match team members to gaps based on their expertise.

        Uses member contribution history across all their pursuits
        to identify who has experience with each element type.
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return []

        suggestions = []

        # Get team members
        owner_id = pursuit.get("user_id")
        team_members = [owner_id]

        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            team_members.append(member.get("user_id"))

        # For each gap type with missing elements
        for element_type, missing in gaps_by_type.items():
            if not missing:
                continue

            # Find team members with experience in this element type
            for user_id in team_members:
                # Check their contribution history across pursuits
                expertise_score = self._calculate_expertise_score(
                    user_id, element_type
                )

                if expertise_score > 0:
                    user = self.db.get_user(user_id)
                    suggestions.append({
                        "user_id": user_id,
                        "user_name": user.get("name") if user else "Unknown",
                        "element_type": element_type,
                        "missing_elements": missing,
                        "expertise_score": expertise_score,
                        "reason": self._expertise_reason(element_type, expertise_score)
                    })

        # Sort by expertise score
        suggestions.sort(key=lambda x: x["expertise_score"], reverse=True)

        return suggestions

    def _calculate_expertise_score(self, user_id: str,
                                     element_type: str) -> float:
        """
        Calculate expertise score for a user in an element type.

        Based on their contribution history across all pursuits.
        """
        # Get user's pursuits (owned and shared)
        owned = self.db.get_user_pursuits(user_id)
        shared = self.db.get_user_shared_pursuits(user_id)

        all_pursuits = owned + [p for p in shared if p.get("user_id") != user_id]

        total_contributions = 0

        for pursuit in all_pursuits:
            team_scaffolding = pursuit.get("team_scaffolding", {})
            contributions = team_scaffolding.get("member_contributions", {})

            if user_id in contributions:
                element_types = contributions[user_id].get("element_types", {})
                total_contributions += element_types.get(element_type, 0)

        # Normalize to 0-1 score (cap at 10 contributions)
        return min(total_contributions / 10.0, 1.0)

    def _expertise_reason(self, element_type: str, score: float) -> str:
        """Generate human-readable expertise reason."""
        if score >= 0.8:
            return f"Has extensive experience with {element_type} elements"
        elif score >= 0.5:
            return f"Has solid experience with {element_type} elements"
        elif score >= 0.3:
            return f"Has some experience with {element_type} elements"
        else:
            return f"Has contributed to {element_type} elements before"

    async def detect_team_milestone(self, pursuit_id: str) -> Optional[Dict]:
        """
        Check if pursuit has crossed a team milestone threshold.

        Milestones:
        - 25% complete
        - 50% complete
        - 75% complete
        - 100% complete

        Returns:
            Milestone info if crossed, None otherwise
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        team_scaffolding = pursuit.get("team_scaffolding", {})
        completeness = team_scaffolding.get("team_completeness", 0.0)

        # Check if we crossed a threshold
        thresholds = [
            (1.00, "completeness_100", "Fully Complete"),
            (0.75, "completeness_75", "75% Complete"),
            (0.50, "completeness_50", "50% Complete"),
            (0.25, "completeness_25", "25% Complete"),
        ]

        last_milestone = team_scaffolding.get("last_milestone", "")

        for threshold, milestone_id, label in thresholds:
            if completeness >= threshold and milestone_id != last_milestone:
                # Milestone crossed!
                team_scaffolding["last_milestone"] = milestone_id
                team_scaffolding["milestone_crossed_at"] = datetime.now(timezone.utc)
                self.db.update_pursuit_team_scaffolding(pursuit_id, team_scaffolding)

                # Count contributors
                contributor_count = len(team_scaffolding.get("member_contributions", {}))

                # Publish event
                if self.event_dispatcher:
                    await self._publish_event("team.milestone.reached", {
                        "pursuit_id": pursuit_id,
                        "milestone_id": milestone_id,
                        "label": label,
                        "completeness": completeness,
                        "contributor_count": contributor_count
                    })

                logger.info(f"Pursuit {pursuit_id} reached milestone: {label}")

                return {
                    "milestone_id": milestone_id,
                    "label": label,
                    "completeness": completeness,
                    "contributor_count": contributor_count
                }

        return None

    async def publish_gap_alert(self, pursuit_id: str,
                                  element_type: str,
                                  suggested_user_id: str) -> None:
        """
        Publish a gap identification event for team notification.

        Args:
            pursuit_id: Pursuit ID
            element_type: The gap area (vision, fears, hypothesis)
            suggested_user_id: User suggested to address the gap
        """
        if self.event_dispatcher:
            await self._publish_event("team.gap.identified", {
                "pursuit_id": pursuit_id,
                "element_type": element_type,
                "suggested_user_id": suggested_user_id
            })

    def get_member_contribution_details(self, pursuit_id: str,
                                          user_id: str) -> Dict:
        """
        Get detailed contribution information for a specific member.

        Returns:
            {
                "elements_contributed": [...],
                "contribution_timeline": [...],
                "expertise_areas": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {}

        team_scaffolding = pursuit.get("team_scaffolding", {})
        attribution = team_scaffolding.get("element_attribution", {})

        elements_contributed = []
        contribution_timeline = []

        for key, data in attribution.items():
            if data.get("user_id") == user_id:
                element_type, element_name = key.split(".", 1)
                elements_contributed.append({
                    "element_type": element_type,
                    "element_name": element_name,
                    "contributed_at": data.get("contributed_at")
                })
                contribution_timeline.append({
                    "timestamp": data.get("contributed_at"),
                    "action": "contributed",
                    "element": key
                })

        # Sort timeline
        contribution_timeline.sort(
            key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min
        )

        # Identify expertise areas
        type_counts = {}
        for e in elements_contributed:
            t = e["element_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        expertise_areas = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "elements_contributed": elements_contributed,
            "contribution_timeline": contribution_timeline,
            "expertise_areas": [{"type": t, "count": c} for t, c in expertise_areas],
            "total_contributions": len(elements_contributed)
        }

    async def _publish_event(self, event_type: str, payload: Dict) -> None:
        """Publish event to Redis Streams."""
        if self.event_dispatcher:
            try:
                await self.event_dispatcher.emit(event_type, payload)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")


# Singleton instance
team_scaffolding_engine = TeamScaffoldingEngine()
