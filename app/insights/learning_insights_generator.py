"""
InDE MVP v2.7 - Learning Insights Generator

Analyzes pursuit history to identify personal patterns and generate
proactive guidance based on historical outcomes.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

from config import TERMINAL_STATES, DEMO_USER_ID


class LearningInsightsGenerator:
    """
    Generates learning insights from pursuit history.
    Identifies personal patterns and correlates outcomes with early indicators.
    """

    # Insight categories
    INSIGHT_CATEGORIES = [
        "TIMING_PATTERN",       # Patterns related to timing/duration
        "BEHAVIOR_PATTERN",     # Patterns in user behavior
        "SUCCESS_INDICATOR",    # Early indicators of success
        "RISK_INDICATOR",       # Early indicators of risk
        "STAKEHOLDER_PATTERN",  # Patterns in stakeholder engagement
        "METHODOLOGY_PATTERN",  # Patterns in methodology effectiveness
        "LEARNING_PATTERN"      # Patterns in how user learns
    ]

    # Insight templates
    INSIGHT_TEMPLATES = {
        "abandonment_timing": {
            "category": "TIMING_PATTERN",
            "template": "You tend to abandon pursuits after {days} days without {activity}",
            "recommendation": "Consider setting earlier checkpoints for {activity}"
        },
        "success_stakeholder": {
            "category": "SUCCESS_INDICATOR",
            "template": "Your successful pursuits had {count}+ stakeholders engaged by day {day}",
            "recommendation": "Prioritize early stakeholder engagement"
        },
        "methodology_fit": {
            "category": "METHODOLOGY_PATTERN",
            "template": "{methodology} has been {effectiveness}% effective for you",
            "recommendation": "Consider {recommendation}"
        },
        "fear_accuracy": {
            "category": "BEHAVIOR_PATTERN",
            "template": "Your initial fears materialized {rate}% of the time",
            "recommendation": "{recommendation}"
        },
        "pivot_pattern": {
            "category": "BEHAVIOR_PATTERN",
            "template": "You pivot most often when {trigger}",
            "recommendation": "Watch for early signs of {trigger}"
        },
        "learning_velocity": {
            "category": "LEARNING_PATTERN",
            "template": "You extract {count} learnings per pursuit on average",
            "recommendation": "{recommendation}"
        }
    }

    def __init__(self, database):
        """
        Initialize LearningInsightsGenerator.

        Args:
            database: Database instance
        """
        self.db = database

    def generate_insights(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        Generate comprehensive insights for a user.

        Args:
            user_id: User ID

        Returns:
            {
                "insights": [...],
                "summary": {...},
                "recommendations": [...]
            }
        """
        # Get all user data
        pursuits = list(self.db.db.pursuits.find({"user_id": user_id}))

        if len(pursuits) < 2:
            return {
                "insights": [],
                "summary": {"message": "Need more pursuit history to generate insights"},
                "recommendations": []
            }

        # Generate various insights
        insights = []
        recommendations = []

        # Timing patterns
        timing_insights = self._analyze_timing_patterns(pursuits, user_id)
        insights.extend(timing_insights["insights"])
        recommendations.extend(timing_insights["recommendations"])

        # Stakeholder patterns
        stakeholder_insights = self._analyze_stakeholder_patterns(pursuits, user_id)
        insights.extend(stakeholder_insights["insights"])
        recommendations.extend(stakeholder_insights["recommendations"])

        # Methodology patterns
        methodology_insights = self._analyze_methodology_patterns(pursuits, user_id)
        insights.extend(methodology_insights["insights"])
        recommendations.extend(methodology_insights["recommendations"])

        # Fear accuracy patterns
        fear_insights = self._analyze_fear_patterns(pursuits, user_id)
        insights.extend(fear_insights["insights"])
        recommendations.extend(fear_insights["recommendations"])

        # Success indicators
        success_insights = self._analyze_success_indicators(pursuits, user_id)
        insights.extend(success_insights["insights"])
        recommendations.extend(success_insights["recommendations"])

        # Learning velocity
        learning_insights = self._analyze_learning_velocity(pursuits, user_id)
        insights.extend(learning_insights["insights"])
        recommendations.extend(learning_insights["recommendations"])

        # Generate summary
        summary = self._generate_summary(pursuits, insights)

        return {
            "insights": insights,
            "summary": summary,
            "recommendations": list(set(recommendations)),  # Deduplicate
            "generated_at": datetime.now(timezone.utc)
        }

    def get_proactive_guidance(self, pursuit_id: str) -> Dict:
        """
        Generate proactive guidance for active pursuit based on history.

        Args:
            pursuit_id: Current pursuit ID

        Returns:
            {
                "warnings": [...],
                "suggestions": [...],
                "similar_pursuits": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {"warnings": [], "suggestions": [], "similar_pursuits": []}

        user_id = pursuit.get("user_id", DEMO_USER_ID)

        # Get historical pursuits
        historical = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "pursuit_id": {"$ne": pursuit_id},
            "state": {"$in": TERMINAL_STATES}
        }))

        if not historical:
            return {"warnings": [], "suggestions": [], "similar_pursuits": []}

        warnings = []
        suggestions = []
        similar_pursuits = []

        # Calculate current pursuit age
        created_at = pursuit.get("created_at", datetime.now(timezone.utc))
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = datetime.now(timezone.utc)
        pursuit_age = (datetime.now(timezone.utc) - created_at).days

        # Check for abandonment risk based on history
        abandonment_risk = self._check_abandonment_risk(pursuit, historical, pursuit_age)
        if abandonment_risk:
            warnings.append(abandonment_risk)

        # Check stakeholder engagement
        stakeholder_warning = self._check_stakeholder_engagement(pursuit, historical, pursuit_age)
        if stakeholder_warning:
            warnings.append(stakeholder_warning)

        # Find similar pursuits
        similar = self._find_similar_pursuits(pursuit, historical)
        similar_pursuits.extend(similar[:3])  # Top 3

        # Generate suggestions based on successful patterns
        suggestions.extend(self._generate_success_suggestions(pursuit, historical))

        return {
            "warnings": warnings,
            "suggestions": suggestions,
            "similar_pursuits": similar_pursuits
        }

    def _analyze_timing_patterns(self, pursuits: List[Dict],
                                  user_id: str) -> Dict:
        """Analyze timing patterns in pursuit lifecycle."""
        insights = []
        recommendations = []

        # Calculate duration for terminal pursuits
        abandoned = []
        successful = []

        for p in pursuits:
            state = p.get("state", "ACTIVE")
            if state not in TERMINAL_STATES:
                continue

            created = p.get("created_at")
            terminal_info = p.get("terminal_info", {})
            ended = terminal_info.get("terminated_at", p.get("updated_at"))

            if not created or not ended:
                continue

            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except:
                    continue
            if isinstance(ended, str):
                try:
                    ended = datetime.fromisoformat(ended)
                except:
                    continue

            duration = (ended - created).days

            if state == "TERMINATED.ABANDONED":
                abandoned.append(duration)
            elif state == "COMPLETED.SUCCESSFUL":
                successful.append(duration)

        # Generate abandonment timing insight
        if len(abandoned) >= 2:
            avg_abandon = sum(abandoned) / len(abandoned)
            insights.append({
                "id": f"timing_abandon_{user_id}",
                "category": "TIMING_PATTERN",
                "insight": f"You tend to abandon pursuits after approximately {int(avg_abandon)} days",
                "confidence": min(0.5 + len(abandoned) * 0.1, 0.9),
                "data_points": len(abandoned)
            })
            recommendations.append(f"Set a checkpoint review at day {int(avg_abandon) - 7}")

        # Generate success timing insight
        if len(successful) >= 2:
            avg_success = sum(successful) / len(successful)
            insights.append({
                "id": f"timing_success_{user_id}",
                "category": "SUCCESS_INDICATOR",
                "insight": f"Your successful pursuits take approximately {int(avg_success)} days to complete",
                "confidence": min(0.5 + len(successful) * 0.1, 0.9),
                "data_points": len(successful)
            })

        return {"insights": insights, "recommendations": recommendations}

    def _analyze_stakeholder_patterns(self, pursuits: List[Dict],
                                      user_id: str) -> Dict:
        """Analyze stakeholder engagement patterns."""
        insights = []
        recommendations = []

        successful_stakeholder_counts = []
        failed_stakeholder_counts = []

        for p in pursuits:
            state = p.get("state", "ACTIVE")
            if state not in TERMINAL_STATES:
                continue

            # Get stakeholder count for pursuit
            stakeholder_count = self.db.db.stakeholder_feedback.count_documents({
                "pursuit_id": p.get("pursuit_id")
            })

            if state == "COMPLETED.SUCCESSFUL":
                successful_stakeholder_counts.append(stakeholder_count)
            elif state.startswith("TERMINATED"):
                failed_stakeholder_counts.append(stakeholder_count)

        # Compare stakeholder engagement
        if successful_stakeholder_counts and failed_stakeholder_counts:
            avg_success = sum(successful_stakeholder_counts) / len(successful_stakeholder_counts)
            avg_failed = sum(failed_stakeholder_counts) / len(failed_stakeholder_counts)

            if avg_success > avg_failed + 1:
                insights.append({
                    "id": f"stakeholder_success_{user_id}",
                    "category": "SUCCESS_INDICATOR",
                    "insight": f"Your successful pursuits average {avg_success:.1f} stakeholders vs {avg_failed:.1f} for terminated ones",
                    "confidence": 0.75,
                    "data_points": len(successful_stakeholder_counts) + len(failed_stakeholder_counts)
                })
                recommendations.append("Aim for early stakeholder engagement (3+ stakeholders)")

        return {"insights": insights, "recommendations": recommendations}

    def _analyze_methodology_patterns(self, pursuits: List[Dict],
                                       user_id: str) -> Dict:
        """Analyze methodology effectiveness patterns."""
        insights = []
        recommendations = []

        methodology_outcomes = defaultdict(list)

        for p in pursuits:
            state = p.get("state", "ACTIVE")
            if state not in TERMINAL_STATES:
                continue

            methodology = p.get("methodology", "Unknown")
            success = 1 if state == "COMPLETED.SUCCESSFUL" else 0
            methodology_outcomes[methodology].append(success)

        # Calculate effectiveness by methodology
        for methodology, outcomes in methodology_outcomes.items():
            if len(outcomes) >= 2:
                effectiveness = sum(outcomes) / len(outcomes) * 100
                insights.append({
                    "id": f"methodology_{methodology}_{user_id}",
                    "category": "METHODOLOGY_PATTERN",
                    "insight": f"{methodology} has been {effectiveness:.0f}% effective for your pursuits",
                    "confidence": min(0.5 + len(outcomes) * 0.1, 0.85),
                    "data_points": len(outcomes)
                })

                if effectiveness < 40:
                    recommendations.append(f"Consider alternative methodologies to {methodology}")

        return {"insights": insights, "recommendations": recommendations}

    def _analyze_fear_patterns(self, pursuits: List[Dict],
                               user_id: str) -> Dict:
        """Analyze fear accuracy patterns."""
        insights = []
        recommendations = []

        # Get all fear resolutions for user
        pursuit_ids = [p["pursuit_id"] for p in pursuits]
        resolutions = list(self.db.db.fear_resolutions.find({
            "pursuit_id": {"$in": pursuit_ids}
        }))

        if len(resolutions) >= 3:
            materialized = sum(1 for r in resolutions if r.get("materialized") is True)
            total = len(resolutions)
            rate = materialized / total * 100

            insights.append({
                "id": f"fear_accuracy_{user_id}",
                "category": "BEHAVIOR_PATTERN",
                "insight": f"Your initial fears materialized {rate:.0f}% of the time ({materialized}/{total})",
                "confidence": min(0.5 + total * 0.05, 0.9),
                "data_points": total
            })

            if rate < 30:
                recommendations.append("Your fears often don't materialize - consider being more optimistic")
            elif rate > 70:
                recommendations.append("Your intuition about risks is accurate - trust your instincts")

        return {"insights": insights, "recommendations": recommendations}

    def _analyze_success_indicators(self, pursuits: List[Dict],
                                    user_id: str) -> Dict:
        """Identify early indicators of success."""
        insights = []
        recommendations = []

        successful = [p for p in pursuits if p.get("state") == "COMPLETED.SUCCESSFUL"]
        terminated = [p for p in pursuits if p.get("state", "").startswith("TERMINATED")]

        if len(successful) < 2 or len(terminated) < 2:
            return {"insights": insights, "recommendations": recommendations}

        # Compare hypothesis validation rates
        successful_validated = []
        terminated_validated = []

        for p in successful:
            pursuit_id = p.get("pursuit_id")
            # Check retrospective for hypothesis outcomes
            retro = self.db.db.retrospectives.find_one({"pursuit_id": pursuit_id})
            if retro:
                artifact = retro.get("artifact", {})
                outcomes = artifact.get("hypothesis_outcomes", [])
                validated = sum(1 for o in outcomes if o.get("outcome") == "VALIDATED")
                if outcomes:
                    successful_validated.append(validated / len(outcomes))

        for p in terminated:
            pursuit_id = p.get("pursuit_id")
            retro = self.db.db.retrospectives.find_one({"pursuit_id": pursuit_id})
            if retro:
                artifact = retro.get("artifact", {})
                outcomes = artifact.get("hypothesis_outcomes", [])
                validated = sum(1 for o in outcomes if o.get("outcome") == "VALIDATED")
                if outcomes:
                    terminated_validated.append(validated / len(outcomes))

        if successful_validated and terminated_validated:
            avg_successful = sum(successful_validated) / len(successful_validated) * 100
            avg_terminated = sum(terminated_validated) / len(terminated_validated) * 100

            if avg_successful > avg_terminated + 20:
                insights.append({
                    "id": f"hypothesis_indicator_{user_id}",
                    "category": "SUCCESS_INDICATOR",
                    "insight": f"Successful pursuits had {avg_successful:.0f}% hypothesis validation vs {avg_terminated:.0f}% for terminated",
                    "confidence": 0.7,
                    "data_points": len(successful_validated) + len(terminated_validated)
                })
                recommendations.append("Focus on validating core hypotheses early")

        return {"insights": insights, "recommendations": recommendations}

    def _analyze_learning_velocity(self, pursuits: List[Dict],
                                   user_id: str) -> Dict:
        """Analyze learning extraction patterns."""
        insights = []
        recommendations = []

        pursuit_ids = [p["pursuit_id"] for p in pursuits]

        # Get patterns extracted per pursuit
        patterns_per_pursuit = []
        for pursuit_id in pursuit_ids:
            count = self.db.db.learning_patterns.count_documents({"pursuit_id": pursuit_id})
            patterns_per_pursuit.append(count)

        if patterns_per_pursuit:
            avg_patterns = sum(patterns_per_pursuit) / len(patterns_per_pursuit)
            insights.append({
                "id": f"learning_velocity_{user_id}",
                "category": "LEARNING_PATTERN",
                "insight": f"You extract {avg_patterns:.1f} learning patterns per pursuit on average",
                "confidence": 0.8,
                "data_points": len(patterns_per_pursuit)
            })

            if avg_patterns < 2:
                recommendations.append("Consider more structured retrospectives to capture learnings")
            elif avg_patterns > 5:
                recommendations.append("Great learning velocity - consider sharing patterns with team")

        return {"insights": insights, "recommendations": recommendations}

    def _check_abandonment_risk(self, pursuit: Dict, historical: List[Dict],
                                 age: int) -> Optional[Dict]:
        """Check if current pursuit shows abandonment risk based on history."""
        # Find abandoned pursuits
        abandoned = [p for p in historical if p.get("state") == "TERMINATED.ABANDONED"]
        if len(abandoned) < 2:
            return None

        # Calculate average abandonment age
        abandon_ages = []
        for p in abandoned:
            created = p.get("created_at")
            terminal_info = p.get("terminal_info", {})
            ended = terminal_info.get("terminated_at", p.get("updated_at"))

            if created and ended:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except:
                        continue
                if isinstance(ended, str):
                    try:
                        ended = datetime.fromisoformat(ended)
                    except:
                        continue
                abandon_ages.append((ended - created).days)

        if not abandon_ages:
            return None

        avg_abandon_age = sum(abandon_ages) / len(abandon_ages)

        # Warn if approaching typical abandonment point
        if age >= avg_abandon_age * 0.8:
            return {
                "warning_type": "ABANDONMENT_RISK",
                "message": f"This pursuit is {age} days old. You typically abandon pursuits around day {int(avg_abandon_age)}.",
                "recommendation": "Consider a milestone check-in or explicit decision point"
            }

        return None

    def _check_stakeholder_engagement(self, pursuit: Dict, historical: List[Dict],
                                       age: int) -> Optional[Dict]:
        """Check stakeholder engagement against successful patterns."""
        successful = [p for p in historical if p.get("state") == "COMPLETED.SUCCESSFUL"]
        if len(successful) < 2:
            return None

        # Get current pursuit stakeholder count
        current_count = self.db.db.stakeholder_feedback.count_documents({
            "pursuit_id": pursuit.get("pursuit_id")
        })

        # Get successful pursuit stakeholder counts
        successful_counts = []
        for p in successful:
            count = self.db.db.stakeholder_feedback.count_documents({
                "pursuit_id": p.get("pursuit_id")
            })
            successful_counts.append(count)

        avg_successful = sum(successful_counts) / len(successful_counts)

        if current_count < avg_successful - 1 and age > 14:
            return {
                "warning_type": "LOW_STAKEHOLDER_ENGAGEMENT",
                "message": f"You have {current_count} stakeholders. Successful pursuits typically have {avg_successful:.1f}.",
                "recommendation": "Consider increasing stakeholder outreach"
            }

        return None

    def _find_similar_pursuits(self, pursuit: Dict,
                               historical: List[Dict]) -> List[Dict]:
        """Find similar historical pursuits."""
        similar = []
        current_methodology = pursuit.get("methodology", "")

        for p in historical:
            similarity_score = 0

            # Same methodology
            if p.get("methodology") == current_methodology:
                similarity_score += 0.4

            # Similar duration range (if terminal)
            if p.get("state") in TERMINAL_STATES:
                similarity_score += 0.3

            if similarity_score > 0.3:
                similar.append({
                    "pursuit_id": p.get("pursuit_id"),
                    "title": p.get("title"),
                    "outcome": p.get("state"),
                    "similarity_score": similarity_score
                })

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar

    def _generate_success_suggestions(self, pursuit: Dict,
                                       historical: List[Dict]) -> List[str]:
        """Generate suggestions based on successful pursuit patterns."""
        suggestions = []

        successful = [p for p in historical if p.get("state") == "COMPLETED.SUCCESSFUL"]
        if not successful:
            return suggestions

        # Check if any successful pursuits had similar methodology
        current_methodology = pursuit.get("methodology", "")
        same_methodology_success = [
            p for p in successful if p.get("methodology") == current_methodology
        ]

        if same_methodology_success:
            suggestions.append(
                f"You've succeeded with {current_methodology} before - apply those learnings"
            )

        return suggestions

    def _generate_summary(self, pursuits: List[Dict],
                          insights: List[Dict]) -> Dict:
        """Generate overall summary."""
        total = len(pursuits)
        terminal = [p for p in pursuits if p.get("state") in TERMINAL_STATES]
        successful = [p for p in pursuits if p.get("state") == "COMPLETED.SUCCESSFUL"]

        success_rate = len(successful) / len(terminal) * 100 if terminal else 0

        # Categorize insights
        categories = Counter(i["category"] for i in insights)

        return {
            "total_pursuits": total,
            "terminal_pursuits": len(terminal),
            "success_rate": round(success_rate, 1),
            "total_insights": len(insights),
            "insights_by_category": dict(categories),
            "strongest_pattern": max(insights, key=lambda x: x.get("confidence", 0))["category"] if insights else None
        }

    def get_portfolio_insights(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        Generate portfolio-level insights.

        Args:
            user_id: User ID

        Returns:
            Portfolio insights dict
        """
        insights = self.generate_insights(user_id)

        # Add portfolio-specific analysis
        pursuits = list(self.db.db.pursuits.find({"user_id": user_id}))

        # Calculate portfolio health score
        active = [p for p in pursuits if p.get("state") == "ACTIVE"]
        terminal = [p for p in pursuits if p.get("state") in TERMINAL_STATES]

        health_factors = []

        # Factor 1: Success rate
        successful = [p for p in pursuits if p.get("state") == "COMPLETED.SUCCESSFUL"]
        if terminal:
            success_rate = len(successful) / len(terminal)
            health_factors.append(success_rate)

        # Factor 2: Learning velocity (patterns per pursuit)
        pursuit_ids = [p["pursuit_id"] for p in pursuits]
        total_patterns = self.db.db.learning_patterns.count_documents({
            "pursuit_id": {"$in": pursuit_ids}
        })
        if pursuits:
            learning_factor = min(total_patterns / len(pursuits) / 5, 1.0)  # 5 patterns = 100%
            health_factors.append(learning_factor)

        # Factor 3: Active pursuit ratio
        if pursuits:
            active_ratio = len(active) / len(pursuits)
            health_factors.append(min(active_ratio * 2, 1.0))  # 50% active = 100%

        portfolio_health = sum(health_factors) / len(health_factors) * 100 if health_factors else 50

        insights["portfolio_health"] = {
            "score": round(portfolio_health, 1),
            "active_pursuits": len(active),
            "terminal_pursuits": len(terminal),
            "total_patterns": total_patterns
        }

        return insights
