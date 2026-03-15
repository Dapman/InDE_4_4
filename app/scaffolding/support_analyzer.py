"""
InDE MVP v2.6 - Support Landscape Analyzer

Aggregates and analyzes stakeholder feedback to provide support intelligence.
Calculates support distribution, identifies concerns, and assesses consensus readiness.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import Counter

try:
    from config import SUPPORT_LEVELS, STAKEHOLDER_CONFIG
except ImportError:
    SUPPORT_LEVELS = ["supportive", "conditional", "neutral", "opposed", "unclear"]
    STAKEHOLDER_CONFIG = {"max_concerns_displayed": 5}


class SupportLandscapeAnalyzer:
    """
    Analyzes stakeholder feedback to provide support intelligence.
    """

    def __init__(self, database, pattern_engine=None):
        """
        Initialize SupportLandscapeAnalyzer.

        Args:
            database: Database instance
            pattern_engine: Optional PatternEngine for pattern-based insights
        """
        self.db = database
        self.pattern_engine = pattern_engine

    def analyze_pursuit_support(self, pursuit_id: str) -> Dict:
        """
        Generate comprehensive support landscape analysis.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            {
                "total_engaged": int,
                "support_distribution": {...},
                "support_percentage": float,
                "top_concerns": [...],
                "resources_committed": [...],
                "consensus_readiness": float,
                "risk_areas": [...],
                "champions": [...],
                "blockers": [...]
            }
        """
        feedback_list = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)

        if not feedback_list:
            return self._empty_analysis()

        analysis = {
            "total_engaged": len(feedback_list),
            "support_distribution": self._calculate_distribution(feedback_list),
            "support_percentage": self._calculate_support_percentage(feedback_list),
            "top_concerns": self._extract_top_concerns(feedback_list),
            "resources_committed": self._compile_resources(feedback_list),
            "consensus_readiness": self._assess_consensus_readiness(feedback_list),
            "risk_areas": self._identify_risks(feedback_list),
            "champions": self._identify_champions(feedback_list),
            "blockers": self._identify_blockers(feedback_list),
            "analyzed_at": datetime.now(timezone.utc)
        }

        # Update pursuit with summary
        self._update_pursuit_summary(pursuit_id, analysis)

        return analysis

    def _calculate_distribution(self, feedback_list: List[Dict]) -> Dict[str, int]:
        """Count stakeholders by support level."""
        distribution = {level: 0 for level in SUPPORT_LEVELS}

        for feedback in feedback_list:
            level = feedback.get("support_level", "unclear")
            if level in distribution:
                distribution[level] += 1

        return distribution

    def _calculate_support_percentage(self, feedback_list: List[Dict]) -> float:
        """Calculate percentage of supportive + conditional stakeholders."""
        if not feedback_list:
            return 0.0

        supportive = sum(1 for f in feedback_list
                        if f.get("support_level") in ["supportive", "conditional"])

        return supportive / len(feedback_list)

    def _extract_top_concerns(self, feedback_list: List[Dict],
                              top_n: int = None) -> List[Dict]:
        """
        Extract most frequently mentioned concerns.

        Args:
            feedback_list: List of feedback documents
            top_n: Number of top concerns to return (default from config)

        Returns:
            List of {"concern": str, "mentions": int}
        """
        if top_n is None:
            top_n = STAKEHOLDER_CONFIG.get("max_concerns_displayed", 5)

        concern_counts = Counter()

        for feedback in feedback_list:
            concerns = feedback.get("concerns", [])
            if isinstance(concerns, list):
                for concern in concerns:
                    if concern:
                        # Normalize: lowercase, strip whitespace
                        normalized = concern.lower().strip()
                        concern_counts[normalized] += 1
            elif concerns:
                normalized = str(concerns).lower().strip()
                concern_counts[normalized] += 1

        # Get top N concerns
        top_concerns = concern_counts.most_common(top_n)

        return [
            {"concern": concern, "mentions": count}
            for concern, count in top_concerns
        ]

    def _compile_resources(self, feedback_list: List[Dict]) -> List[Dict]:
        """Compile all resources offered by stakeholders."""
        resources = []

        for feedback in feedback_list:
            resource = feedback.get("resources_offered", "").strip()
            if resource and resource.lower() not in ["none", "n/a", ""]:
                resources.append({
                    "stakeholder": feedback.get("stakeholder_name", "Unknown"),
                    "role": feedback.get("role", ""),
                    "resource": resource,
                    "conditional": feedback.get("support_level") == "conditional"
                })

        return resources

    def _assess_consensus_readiness(self, feedback_list: List[Dict]) -> float:
        """
        Calculate consensus readiness score (0.0-1.0).

        Factors:
        - Support percentage (60% weight)
        - Engagement breadth (20% weight)
        - Lack of blockers (20% weight)
        """
        if not feedback_list:
            return 0.0

        # Support percentage
        support_pct = self._calculate_support_percentage(feedback_list)

        # Engagement breadth: >= 5 stakeholders = 1.0, linear below that
        engagement_score = min(len(feedback_list) / 5.0, 1.0)

        # Blocker penalty
        opposed_count = sum(1 for f in feedback_list
                          if f.get("support_level") == "opposed")
        blocker_score = max(0.0, 1.0 - (opposed_count * 0.25))

        # Weighted combination
        readiness = (
            (support_pct * 0.60) +
            (engagement_score * 0.20) +
            (blocker_score * 0.20)
        )

        return max(0.0, min(1.0, readiness))

    def _identify_risks(self, feedback_list: List[Dict]) -> List[Dict]:
        """Identify risk areas based on feedback patterns."""
        risks = []

        # Risk: Low engagement
        if len(feedback_list) < 3:
            risks.append({
                "type": "low_engagement",
                "severity": "medium",
                "description": "Few stakeholders engaged - may miss critical concerns"
            })

        # Risk: High opposition
        opposed = [f for f in feedback_list if f.get("support_level") == "opposed"]
        if len(opposed) > 0:
            risks.append({
                "type": "opposition",
                "severity": "high",
                "description": f"{len(opposed)} stakeholder(s) actively opposed",
                "stakeholders": [f.get("stakeholder_name") for f in opposed]
            })

        # Risk: Many conditionals without addressing conditions
        conditionals = [f for f in feedback_list if f.get("support_level") == "conditional"]
        if len(conditionals) >= len(feedback_list) * 0.5 and len(conditionals) > 1:
            risks.append({
                "type": "conditional_majority",
                "severity": "medium",
                "description": f"{len(conditionals)} stakeholders have conditions for support"
            })

        # Risk: Consistent concern theme (majority raised same concern)
        top_concerns = self._extract_top_concerns(feedback_list, 1)
        if top_concerns and len(feedback_list) >= 2:
            top_mentions = top_concerns[0]["mentions"]
            if top_mentions >= len(feedback_list) * 0.5:
                risks.append({
                    "type": "common_concern",
                    "severity": "medium",
                    "description": f"Majority raised concern: {top_concerns[0]['concern']}",
                    "mentions": top_mentions
                })

        # Risk: No champions identified
        champions = self._identify_champions(feedback_list)
        if not champions and len(feedback_list) >= 3:
            risks.append({
                "type": "no_champions",
                "severity": "low",
                "description": "No strong champions identified (supportive + resources)"
            })

        return risks

    def _identify_champions(self, feedback_list: List[Dict]) -> List[Dict]:
        """Identify potential champions (supportive + offered resources)."""
        champions = []

        for feedback in feedback_list:
            is_supportive = feedback.get("support_level") == "supportive"
            has_resources = bool(feedback.get("resources_offered", "").strip())

            if is_supportive and has_resources:
                champions.append({
                    "name": feedback.get("stakeholder_name", "Unknown"),
                    "role": feedback.get("role", ""),
                    "resources": feedback.get("resources_offered", "")
                })
            elif is_supportive:
                # Still a champion even without explicit resources
                champions.append({
                    "name": feedback.get("stakeholder_name", "Unknown"),
                    "role": feedback.get("role", ""),
                    "resources": None
                })

        return champions

    def _identify_blockers(self, feedback_list: List[Dict]) -> List[Dict]:
        """Identify potential blockers (opposed or conditional with critical concerns)."""
        blockers = []

        for feedback in feedback_list:
            support_level = feedback.get("support_level", "unclear")

            if support_level == "opposed":
                blockers.append({
                    "name": feedback.get("stakeholder_name", "Unknown"),
                    "role": feedback.get("role", ""),
                    "type": "opposed",
                    "concerns": feedback.get("concerns", [])
                })
            elif support_level == "conditional":
                conditions = feedback.get("conditions", "")
                if conditions:
                    blockers.append({
                        "name": feedback.get("stakeholder_name", "Unknown"),
                        "role": feedback.get("role", ""),
                        "type": "conditional",
                        "conditions": conditions
                    })

        return blockers

    def _update_pursuit_summary(self, pursuit_id: str, analysis: Dict):
        """Update pursuit record with stakeholder summary."""
        summary = {
            "total_engaged": analysis["total_engaged"],
            "support_distribution": analysis["support_distribution"],
            "support_percentage": analysis["support_percentage"],
            "top_concerns": analysis["top_concerns"],
            "resources_committed": [r["resource"] for r in analysis["resources_committed"]],
            "consensus_readiness": analysis["consensus_readiness"],
            "last_analyzed": datetime.now(timezone.utc)
        }

        self.db.update_pursuit_stakeholder_summary(pursuit_id, summary)

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure."""
        return {
            "total_engaged": 0,
            "support_distribution": {level: 0 for level in SUPPORT_LEVELS},
            "support_percentage": 0.0,
            "top_concerns": [],
            "resources_committed": [],
            "consensus_readiness": 0.0,
            "risk_areas": [],
            "champions": [],
            "blockers": [],
            "analyzed_at": None
        }

    def generate_dashboard_data(self, pursuit_id: str) -> Dict:
        """
        Generate data structure for UI dashboard visualization.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dashboard-ready data structure
        """
        analysis = self.analyze_pursuit_support(pursuit_id)

        return {
            "summary_stats": {
                "total_engaged": analysis["total_engaged"],
                "support_percentage": f"{analysis['support_percentage']*100:.0f}%",
                "consensus_readiness": f"{analysis['consensus_readiness']*100:.0f}%"
            },
            "chart_data": {
                "support_distribution": analysis["support_distribution"],
                "labels": SUPPORT_LEVELS,
                "values": [analysis["support_distribution"][level] for level in SUPPORT_LEVELS]
            },
            "concerns_table": analysis["top_concerns"],
            "resources_list": analysis["resources_committed"],
            "risk_alerts": analysis["risk_areas"],
            "key_people": {
                "champions": analysis["champions"],
                "blockers": analysis["blockers"]
            }
        }

    def generate_summary_text(self, pursuit_id: str) -> str:
        """
        Generate human-readable summary of support landscape.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Summary text for display
        """
        analysis = self.analyze_pursuit_support(pursuit_id)

        if analysis["total_engaged"] == 0:
            return "No stakeholder feedback captured yet."

        lines = []

        # Overview
        support_pct = int(analysis["support_percentage"] * 100)
        lines.append(f"Engaged {analysis['total_engaged']} stakeholder(s) with {support_pct}% support.")

        # Distribution
        dist = analysis["support_distribution"]
        dist_parts = []
        if dist["supportive"] > 0:
            dist_parts.append(f"{dist['supportive']} supportive")
        if dist["conditional"] > 0:
            dist_parts.append(f"{dist['conditional']} conditional")
        if dist["neutral"] > 0:
            dist_parts.append(f"{dist['neutral']} neutral")
        if dist["opposed"] > 0:
            dist_parts.append(f"{dist['opposed']} opposed")
        if dist_parts:
            lines.append(f"Distribution: {', '.join(dist_parts)}")

        # Top concerns
        if analysis["top_concerns"]:
            top = analysis["top_concerns"][0]
            lines.append(f"Top concern: {top['concern']} ({top['mentions']} mention(s))")

        # Resources
        if analysis["resources_committed"]:
            resource_count = len(analysis["resources_committed"])
            lines.append(f"Resources offered: {resource_count} commitment(s)")

        # Consensus readiness
        readiness_pct = int(analysis["consensus_readiness"] * 100)
        if readiness_pct >= 70:
            lines.append(f"Consensus readiness: {readiness_pct}% (strong foundation)")
        elif readiness_pct >= 50:
            lines.append(f"Consensus readiness: {readiness_pct}% (moderate)")
        else:
            lines.append(f"Consensus readiness: {readiness_pct}% (needs attention)")

        # Risks
        high_risks = [r for r in analysis["risk_areas"] if r["severity"] == "high"]
        if high_risks:
            lines.append(f"Warning: {len(high_risks)} high-priority risk(s) identified")

        return "\n".join(lines)

    def compare_with_similar_pursuits(self, pursuit_id: str) -> Optional[Dict]:
        """
        v2.6: Compare current support landscape with similar completed pursuits.

        Uses pattern engine if available.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Comparison insights or None
        """
        if not self.pattern_engine:
            return None

        current_analysis = self.analyze_pursuit_support(pursuit_id)

        if current_analysis["total_engaged"] < 2:
            return None

        # Find similar pursuits via pattern engine
        try:
            similar = self.pattern_engine.find_similar_engagement_patterns(pursuit_id)

            if not similar:
                return None

            # Compare metrics
            similar_support = [p.get("support_percentage", 0) for p in similar]
            avg_similar_support = sum(similar_support) / len(similar_support) if similar_support else 0

            comparison = {
                "current_support": current_analysis["support_percentage"],
                "avg_similar_support": avg_similar_support,
                "comparison": "above" if current_analysis["support_percentage"] > avg_similar_support else "below",
                "similar_count": len(similar),
                "insight": None
            }

            if comparison["comparison"] == "above":
                comparison["insight"] = f"Your support level ({current_analysis['support_percentage']*100:.0f}%) is above average for similar pursuits ({avg_similar_support*100:.0f}%)."
            else:
                comparison["insight"] = f"Similar pursuits averaged {avg_similar_support*100:.0f}% support. Consider addressing top concerns to improve."

            return comparison

        except Exception:
            return None
