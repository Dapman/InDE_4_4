"""
InDE MVP v3.3 - Team Context Assembler
Multi-user context assembly for team-aware coaching.

Features:
- Team scaffolding context aggregation
- Privacy-aware fear handling
- Cross-member insight correlation
- Coaching pattern application
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

from database import db
from config import TEAM_CONFIG, TEAM_COACHING_PATTERNS

logger = logging.getLogger("inde.teams.context")


class TeamContextAssembler:
    """
    Assembles team context for ODICM coaching.

    Aggregates multi-user scaffolding while respecting privacy
    boundaries for fears and personal coaching sessions.
    """

    def __init__(self):
        """Initialize team context assembler."""
        self.db = db
        self.max_team_tokens = TEAM_CONFIG.get("team_context_max_tokens", 1500)
        self.max_org_tokens = TEAM_CONFIG.get("org_context_max_tokens", 500)

    def assemble_team_context(self, pursuit_id: str,
                               current_user_id: str) -> Dict:
        """
        Assemble team context for coaching session.

        Args:
            pursuit_id: Pursuit ID
            current_user_id: Current user in coaching session

        Returns:
            {
                "team_members": [...],
                "team_completeness": float,
                "element_summary": {...},
                "shared_fears": [...],
                "anonymized_fears": [...],
                "convergence_areas": [...],
                "gaps_for_user": [...],
                "coaching_suggestions": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {}

        # Check if pursuit is shared
        sharing = pursuit.get("sharing", {})
        if not sharing.get("is_shared", False):
            return {"is_shared": False}

        # Get team members
        team_members = self._get_team_members_summary(pursuit)

        # Get team scaffolding
        team_scaffolding = pursuit.get("team_scaffolding", {})
        element_attribution = team_scaffolding.get("element_attribution", {})

        # Build element summary (excluding fears initially)
        element_summary = self._build_element_summary(
            pursuit_id, element_attribution, current_user_id
        )

        # Handle fears with privacy
        shared_fears, anonymized_fears = self._process_fears(
            pursuit_id, pursuit, current_user_id
        )

        # Detect convergence areas
        convergence_areas = self._detect_convergence(pursuit_id)

        # Get gaps this user could address
        gaps_for_user = self._get_user_gap_opportunities(
            pursuit_id, current_user_id, element_attribution
        )

        # Generate coaching suggestions
        coaching_suggestions = self._generate_coaching_suggestions(
            pursuit_id, current_user_id, team_scaffolding, shared_fears
        )

        return {
            "is_shared": True,
            "team_members": team_members,
            "team_completeness": team_scaffolding.get("team_completeness", 0.0),
            "element_summary": element_summary,
            "shared_fears": shared_fears,
            "anonymized_fears": anonymized_fears,
            "convergence_areas": convergence_areas,
            "gaps_for_user": gaps_for_user,
            "coaching_suggestions": coaching_suggestions
        }

    def _get_team_members_summary(self, pursuit: Dict) -> List[Dict]:
        """Get summarized team member info."""
        members = []

        # Add owner
        owner_id = pursuit.get("user_id")
        owner = self.db.get_user(owner_id)
        members.append({
            "user_id": owner_id,
            "name": owner.get("name") if owner else "Unknown",
            "role": "owner",
            "is_active": True
        })

        # Add team members
        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            user = self.db.get_user(member.get("user_id"))
            members.append({
                "user_id": member.get("user_id"),
                "name": user.get("name") if user else "Unknown",
                "role": member.get("role"),
                "is_active": self._is_recently_active(member.get("last_active_at"))
            })

        return members

    def _is_recently_active(self, last_active: datetime, hours: int = 24) -> bool:
        """Check if member was active within time window."""
        if not last_active:
            return False
        from datetime import timedelta
        return last_active > datetime.now(timezone.utc) - timedelta(hours=hours)

    def _build_element_summary(self, pursuit_id: str,
                                 attribution: Dict,
                                 current_user_id: str) -> Dict:
        """
        Build summary of scaffolding elements.

        Groups by element type and notes who contributed.
        """
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        if not scaffolding:
            return {}

        summary = {
            "vision": {"elements": [], "completeness": 0},
            "fears": {"elements": [], "completeness": 0},
            "hypothesis": {"elements": [], "completeness": 0}
        }

        type_map = {
            "vision": ("vision_elements", "vision"),
            "fears": ("fear_elements", "fears"),
            "hypothesis": ("hypothesis_elements", "hypothesis")
        }

        for element_type, (field_name, type_key) in type_map.items():
            elements_data = scaffolding.get(field_name, {})
            filled = 0
            total = 0

            for element_name, data in elements_data.items():
                total += 1
                if data and data.get("text"):
                    filled += 1

                    # Get attribution
                    attr_key = f"{element_type}.{element_name}"
                    attr_info = attribution.get(attr_key, {})
                    contributor_id = attr_info.get("user_id")

                    # For fears, only include if current user contributed
                    # or if fear is explicitly shared
                    if element_type == "fears" and contributor_id != current_user_id:
                        continue

                    contributor = self.db.get_user(contributor_id) if contributor_id else None

                    summary[element_type]["elements"].append({
                        "name": element_name,
                        "text": data.get("text"),
                        "contributed_by": contributor.get("name") if contributor else None,
                        "is_own": contributor_id == current_user_id
                    })

            summary[element_type]["completeness"] = filled / total if total > 0 else 0

        return summary

    def _process_fears(self, pursuit_id: str, pursuit: Dict,
                        current_user_id: str) -> tuple:
        """
        Process fears with privacy boundaries.

        Returns:
            (shared_fears, anonymized_fears)
            - shared_fears: Full text of fears explicitly shared
            - anonymized_fears: Theme summaries for unshared fears
        """
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        if not scaffolding:
            return [], []

        fear_elements = scaffolding.get("fear_elements", {})
        fear_sharing = pursuit.get("fear_sharing", {})
        team_scaffolding = pursuit.get("team_scaffolding", {})
        attribution = team_scaffolding.get("element_attribution", {})

        shared_fears = []
        anonymized_fears = []

        for fear_name, data in fear_elements.items():
            if not data or not data.get("text"):
                continue

            attr_key = f"fears.{fear_name}"
            attr_info = attribution.get(attr_key, {})
            contributor_id = attr_info.get("user_id")

            # Always show own fears
            if contributor_id == current_user_id:
                contributor = self.db.get_user(contributor_id)
                shared_fears.append({
                    "name": fear_name,
                    "text": data.get("text"),
                    "contributed_by": contributor.get("name") if contributor else "You",
                    "is_own": True
                })
                continue

            # Check if fear is explicitly shared with team
            sharing_info = fear_sharing.get(fear_name, {})
            if sharing_info.get("shared_with_team", False):
                contributor = self.db.get_user(contributor_id)
                shared_fears.append({
                    "name": fear_name,
                    "text": data.get("text"),
                    "contributed_by": contributor.get("name") if contributor else "Unknown",
                    "is_own": False
                })
            else:
                # Anonymize - just show theme
                theme = self._extract_fear_theme(fear_name, data.get("text", ""))
                anonymized_fears.append({
                    "theme": theme,
                    "contributors": 1  # Don't reveal who
                })

        # Aggregate similar anonymized themes
        anonymized_fears = self._aggregate_fear_themes(anonymized_fears)

        return shared_fears, anonymized_fears

    def _extract_fear_theme(self, fear_name: str, text: str) -> str:
        """Extract theme from fear for anonymization."""
        themes = {
            "capability_fears": "Technical capability concerns",
            "market_fears": "Market/competition concerns",
            "resource_fears": "Resource/time constraints",
            "timing_fears": "Timing considerations",
            "adoption_fears": "Adoption/acceptance concerns",
            "execution_fears": "Execution/implementation risks"
        }
        return themes.get(fear_name, "General concerns")

    def _aggregate_fear_themes(self, fears: List[Dict]) -> List[Dict]:
        """Aggregate similar fear themes."""
        theme_counts = {}
        for fear in fears:
            theme = fear.get("theme")
            theme_counts[theme] = theme_counts.get(theme, 0) + fear.get("contributors", 1)

        return [
            {"theme": theme, "contributors": count}
            for theme, count in theme_counts.items()
        ]

    def _detect_convergence(self, pursuit_id: str) -> List[Dict]:
        """
        Detect areas where multiple team members reached similar conclusions.

        Returns areas with convergence and confidence level.
        """
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        if not scaffolding:
            return []

        pursuit = self.db.get_pursuit(pursuit_id)
        team_scaffolding = pursuit.get("team_scaffolding", {}) if pursuit else {}
        attribution = team_scaffolding.get("element_attribution", {})

        convergence_areas = []

        # Check for multiple contributors to same element type
        type_contributors = {"vision": set(), "fears": set(), "hypothesis": set()}

        for key, attr in attribution.items():
            element_type = key.split(".")[0]
            user_id = attr.get("user_id")
            if user_id:
                type_contributors[element_type].add(user_id)

        for element_type, contributors in type_contributors.items():
            if len(contributors) >= 2:
                convergence_areas.append({
                    "area": element_type,
                    "contributors": len(contributors),
                    "confidence": "high" if len(contributors) >= 3 else "moderate"
                })

        return convergence_areas

    def _get_user_gap_opportunities(self, pursuit_id: str,
                                      user_id: str,
                                      attribution: Dict) -> List[Dict]:
        """
        Identify gaps this user could address based on expertise.

        Uses the team scaffolding engine's gap analysis.
        """
        from teams.team_scaffolding import TeamScaffoldingEngine

        engine = TeamScaffoldingEngine()
        gap_analysis = engine.analyze_gaps(pursuit_id)

        # Filter suggestions to this user
        user_suggestions = [
            s for s in gap_analysis.get("expertise_suggestions", [])
            if s.get("user_id") == user_id
        ]

        return user_suggestions

    def _generate_coaching_suggestions(self, pursuit_id: str,
                                         current_user_id: str,
                                         team_scaffolding: Dict,
                                         shared_fears: List) -> List[Dict]:
        """
        Generate coaching suggestions based on team context.

        Uses TEAM_COACHING_PATTERNS to select appropriate interventions.
        """
        suggestions = []

        # Check for expertise referral opportunity
        contributions = team_scaffolding.get("member_contributions", {})
        if len(contributions) > 1:
            # Find another member who has addressed areas current user hasn't
            current_types = contributions.get(current_user_id, {}).get("element_types", {})

            for other_id, other_stats in contributions.items():
                if other_id == current_user_id:
                    continue

                other_types = other_stats.get("element_types", {})

                # Find types other has but current doesn't
                for element_type, count in other_types.items():
                    if count > 0 and current_types.get(element_type, 0) == 0:
                        other_user = self.db.get_user(other_id)
                        pattern = TEAM_COACHING_PATTERNS.get("expertise_referral", {})
                        suggestions.append({
                            "pattern": "expertise_referral",
                            "template": pattern.get("template", ""),
                            "context": {
                                "member_name": other_user.get("name") if other_user else "A team member",
                                "concern_type": element_type,
                                "element_summary": f"{element_type} elements"
                            },
                            "priority": "medium"
                        })
                        break

        # Check for cross-fear correlation
        if len(shared_fears) >= 2:
            # Group by theme
            themes = {}
            for fear in shared_fears:
                theme = self._extract_fear_theme(fear.get("name", ""), fear.get("text", ""))
                if theme not in themes:
                    themes[theme] = []
                themes[theme].append(fear)

            for theme, fears_list in themes.items():
                if len(fears_list) >= 2:
                    pattern = TEAM_COACHING_PATTERNS.get("cross_fear_correlation", {})
                    suggestions.append({
                        "pattern": "cross_fear_correlation",
                        "template": pattern.get("template", ""),
                        "context": {
                            "count": len(fears_list),
                            "fear_theme": theme
                        },
                        "priority": "high"
                    })

        # Check for milestone celebration
        completeness = team_scaffolding.get("team_completeness", 0)
        if completeness >= 0.5 and completeness < 0.75:
            pattern = TEAM_COACHING_PATTERNS.get("team_milestone_celebration", {})
            suggestions.append({
                "pattern": "team_milestone_celebration",
                "template": pattern.get("template", ""),
                "context": {
                    "new_state": f"{int(completeness * 100)}% complete",
                    "contributor_count": len(contributions)
                },
                "priority": "low"
            })

        return suggestions

    def get_org_context(self, org_id: str, user_id: str) -> Dict:
        """
        Assemble organization context for coaching.

        Used for org-level insights and pattern library access.

        Args:
            org_id: Organization ID
            user_id: Current user ID

        Returns:
            {
                "org_name": str,
                "user_role": str,
                "org_pursuits_count": int,
                "org_patterns_available": bool
            }
        """
        org = self.db.get_organization(org_id)
        if not org:
            return {}

        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("status") != "active":
            return {}

        org_pursuits = self.db.get_org_pursuits(org_id, status="active")

        return {
            "org_name": org.get("name"),
            "org_id": org_id,
            "user_role": membership.get("role"),
            "org_pursuits_count": len(org_pursuits),
            "org_patterns_available": org.get("settings", {}).get("ikf_sharing_level") != "NONE"
        }

    def format_for_llm(self, team_context: Dict, max_tokens: int = None) -> str:
        """
        Format team context for LLM prompt inclusion.

        Args:
            team_context: Full team context dict
            max_tokens: Maximum token budget (default from config)

        Returns:
            Formatted context string
        """
        if not team_context.get("is_shared", False):
            return ""

        max_tokens = max_tokens or self.max_team_tokens
        lines = []

        # Team overview
        members = team_context.get("team_members", [])
        active_count = sum(1 for m in members if m.get("is_active"))
        lines.append(f"Team Context: {len(members)} members ({active_count} recently active)")

        # Completeness
        completeness = team_context.get("team_completeness", 0)
        lines.append(f"Team Progress: {int(completeness * 100)}% complete")

        # Convergence
        convergence = team_context.get("convergence_areas", [])
        if convergence:
            areas = [c.get("area") for c in convergence]
            lines.append(f"Convergence detected in: {', '.join(areas)}")

        # Shared fears summary
        shared_fears = team_context.get("shared_fears", [])
        if shared_fears:
            fear_count = len(shared_fears)
            lines.append(f"Shared concerns: {fear_count} fears openly discussed by team")

        # Anonymous fear themes
        anon_fears = team_context.get("anonymized_fears", [])
        if anon_fears:
            themes = [f.get("theme") for f in anon_fears]
            lines.append(f"Other team concerns (anonymized): {', '.join(themes)}")

        # Gap opportunities for user
        gaps = team_context.get("gaps_for_user", [])
        if gaps:
            gap_areas = [g.get("element_type") for g in gaps[:2]]
            lines.append(f"You could help with: {', '.join(gap_areas)}")

        return "\n".join(lines)


# Singleton instance
team_context_assembler = TeamContextAssembler()
