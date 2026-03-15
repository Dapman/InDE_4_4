"""
InDE MVP v3.0.2 - Predictive Guidance Engine
Forward-looking predictions based on historical patterns.

Features:
- Phase challenge predictions
- Upcoming risk predictions
- Opportunity window identification
- Stall warnings
- Methodology-specific hints

Prediction Types:
- PHASE_CHALLENGE: "Teams typically struggle with [X] at this phase"
- UPCOMING_RISK: "Based on velocity trajectory, [risk] likely in [timeframe]"
- OPPORTUNITY_WINDOW: "Similar pursuits that [action] at this point had [outcome]"
- STALL_WARNING: "Pursuits with this velocity pattern often stall in [N] days"
- METHODOLOGY_HINT: "This is a good moment to [methodology-specific action]"
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time

from config import (
    PREDICTIVE_GUIDANCE_CONFIG, PREDICTION_TYPES, IKF_PHASES
)


class PredictiveGuidanceEngine:
    """
    Generate forward-looking predictions for pursuits.

    Uses historical pattern data and current pursuit context
    to predict likely challenges, risks, and opportunities.
    """

    def __init__(self, db, velocity_tracker=None, phase_manager=None,
                 health_monitor=None):
        """
        Initialize predictive guidance engine.

        Args:
            db: Database instance
            velocity_tracker: Optional VelocityTracker from TIM
            phase_manager: Optional PhaseManager from TIM
            health_monitor: Optional HealthMonitor
        """
        self.db = db
        self.velocity_tracker = velocity_tracker
        self.phase_manager = phase_manager
        self.health_monitor = health_monitor
        self.config = PREDICTIVE_GUIDANCE_CONFIG
        self._cache = {}
        self._cache_ttl = self.config.get("prediction_cache_ttl_seconds", 600)

    def generate_predictions(self, pursuit_id: str) -> List[Dict]:
        """
        Generate predictions for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of predictions ordered by confidence
        """
        if not self.config.get("enable_predictions", True):
            return []

        # Check cache
        cache_key = f"predictions_{pursuit_id}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return cached["data"]

        # Get pursuit context
        context = self._get_prediction_context(pursuit_id)

        predictions = []

        # Generate each prediction type
        predictions.extend(self._predict_phase_challenges(context))
        predictions.extend(self._predict_upcoming_risks(context))
        predictions.extend(self._predict_opportunity_windows(context))
        predictions.extend(self._predict_stall_warnings(context))
        predictions.extend(self._predict_methodology_hints(context))

        # Filter by confidence threshold
        min_confidence = self.config.get("min_confidence_threshold", 0.60)
        predictions = [p for p in predictions if p["confidence"] >= min_confidence]

        # Sort by confidence and limit
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        max_predictions = self.config.get("max_predictions_per_invocation", 3)
        predictions = predictions[:max_predictions]

        # Cache results
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "data": predictions
        }

        return predictions

    def _get_prediction_context(self, pursuit_id: str) -> Dict:
        """Get context needed for predictions."""
        pursuit = self.db.get_pursuit(pursuit_id)
        scaffolding = self.db.get_scaffolding_state(pursuit_id)

        context = {
            "pursuit_id": pursuit_id,
            "pursuit": pursuit,
            "current_phase": "VISION",
            "completeness": scaffolding.get("completeness", {}) if scaffolding else {},
            "velocity_status": "unknown",
            "elements_per_week": 0,
            "days_in_phase": 0,
            "phase_percent": 0,
            "health_zone": "HEALTHY",
            "health_score": 50,
            "domain": pursuit.get("problem_context", {}).get("domain") if pursuit else None,
            "methodology": pursuit.get("methodology") if pursuit else None
        }

        # Get phase info
        if self.phase_manager:
            context["current_phase"] = self.phase_manager.get_current_phase(pursuit_id)
            phase_status = self.phase_manager.get_phase_status(
                pursuit_id, context["current_phase"]
            )
            context["days_in_phase"] = phase_status.get("days_used", 0)
            allocated = phase_status.get("days_allocated", 30)
            if allocated > 0:
                context["phase_percent"] = context["days_in_phase"] / allocated * 100

        # Get velocity info
        if self.velocity_tracker:
            velocity = self.velocity_tracker.calculate_velocity(pursuit_id)
            context["velocity_status"] = velocity.get("status", "unknown")
            context["elements_per_week"] = velocity.get("elements_per_week", 0)
            context["velocity_trend"] = velocity.get("trend", "stable")

        # Get health info
        if self.health_monitor:
            health = self.health_monitor.calculate_health(pursuit_id)
            context["health_zone"] = health.get("zone", "HEALTHY")
            context["health_score"] = health.get("health_score", 50)

        return context

    def _predict_phase_challenges(self, context: Dict) -> List[Dict]:
        """Predict challenges typical for the current phase."""
        predictions = []
        phase = context["current_phase"]

        # Query historical patterns for this phase
        patterns = list(self.db.db.patterns.find({
            "source_phase": phase,
            "pattern_type": "CHALLENGE"
        }).limit(50))

        if not patterns:
            # Use default predictions
            phase_challenges = {
                "VISION": [
                    {
                        "challenge": "scope creep",
                        "description": "Vision becomes too broad to validate",
                        "suggestion": "Focus on the core value proposition first"
                    },
                    {
                        "challenge": "solution fixation",
                        "description": "Focusing on solution before understanding problem",
                        "suggestion": "Spend more time understanding user pain points"
                    }
                ],
                "DE_RISK": [
                    {
                        "challenge": "confirmation bias",
                        "description": "Interpreting evidence to support preferred outcome",
                        "suggestion": "Actively seek disconfirming evidence"
                    },
                    {
                        "challenge": "insufficient sample size",
                        "description": "Drawing conclusions from too few data points",
                        "suggestion": "Aim for statistical significance in experiments"
                    }
                ],
                "DEPLOY": [
                    {
                        "challenge": "premature scaling",
                        "description": "Scaling before achieving product-market fit",
                        "suggestion": "Validate retention before scaling acquisition"
                    },
                    {
                        "challenge": "resource underestimation",
                        "description": "Underestimating resources needed for deployment",
                        "suggestion": "Build in buffer for unexpected challenges"
                    }
                ]
            }

            defaults = phase_challenges.get(phase, [])
            for challenge in defaults[:1]:  # Just top challenge
                predictions.append({
                    "type": "PHASE_CHALLENGE",
                    "confidence": 0.65,
                    "title": f"Common {phase} Challenge",
                    "description": f"Teams often struggle with {challenge['challenge']} during this phase.",
                    "detail": challenge["description"],
                    "suggestion": challenge["suggestion"],
                    "source": "default_knowledge"
                })

        else:
            # Use historical patterns
            # Aggregate common challenges
            challenge_counts = {}
            for pattern in patterns:
                challenge = pattern.get("insight", {}).get("challenge")
                if challenge:
                    challenge_counts[challenge] = challenge_counts.get(challenge, 0) + 1

            if challenge_counts:
                most_common = max(challenge_counts, key=challenge_counts.get)
                frequency = challenge_counts[most_common] / len(patterns)

                predictions.append({
                    "type": "PHASE_CHALLENGE",
                    "confidence": min(0.85, 0.5 + frequency * 0.5),
                    "title": "Frequent Challenge at This Stage",
                    "description": f"Based on similar pursuits, teams often face: {most_common}",
                    "suggestion": "Consider proactively addressing this before it becomes a blocker",
                    "source": "historical_patterns",
                    "pattern_count": len(patterns)
                })

        return predictions

    def _predict_upcoming_risks(self, context: Dict) -> List[Dict]:
        """Predict upcoming risks based on trajectory."""
        predictions = []

        # Risk 1: Velocity-based timeline risk
        if context["velocity_status"] in ["behind", "significantly_behind"]:
            days_in_phase = context.get("days_in_phase", 0)
            remaining_percent = 100 - context.get("phase_percent", 50)

            if remaining_percent < 30 and context["completeness"].get("vision", 0) < 0.6:
                predictions.append({
                    "type": "UPCOMING_RISK",
                    "confidence": 0.75,
                    "title": "Timeline Risk Detected",
                    "description": f"At current velocity, you may not complete {context['current_phase']} phase before allocation runs out.",
                    "timeframe": f"Within {int(remaining_percent / 10 * 3)} days",
                    "suggestion": "Consider scope reduction or timeline adjustment",
                    "source": "velocity_analysis"
                })

        # Risk 2: Phase transition risk
        if context["current_phase"] == "VISION" and context["phase_percent"] > 80:
            fears_complete = context["completeness"].get("fears", 0)
            if fears_complete < 0.3:
                predictions.append({
                    "type": "UPCOMING_RISK",
                    "confidence": 0.70,
                    "title": "Incomplete Fear Documentation",
                    "description": "Approaching phase transition with low fear documentation. This may lead to unaddressed risks.",
                    "timeframe": "At phase transition",
                    "suggestion": "Document known concerns before moving to de-risk phase",
                    "source": "completeness_analysis"
                })

        return predictions

    def _predict_opportunity_windows(self, context: Dict) -> List[Dict]:
        """Predict opportunity windows based on successful patterns."""
        predictions = []

        # Look for successful patterns at similar stage
        patterns = list(self.db.db.patterns.find({
            "source_phase": context["current_phase"],
            "outcome": {"$in": ["SUCCESS", "PIVOT_SUCCESS"]},
            "problem_context.domain": context.get("domain")
        }).limit(20))

        if patterns:
            # Analyze what successful pursuits did at this stage
            for pattern in patterns[:3]:
                insight = pattern.get("insight", {})
                action = insight.get("key_action")
                outcome = insight.get("outcome_description")

                if action:
                    phase_timing = pattern.get("metadata", {}).get("phase_percent_at_capture", 50)
                    current_timing = context.get("phase_percent", 50)

                    # Check if timing is similar (within 20%)
                    if abs(phase_timing - current_timing) < 20:
                        predictions.append({
                            "type": "OPPORTUNITY_WINDOW",
                            "confidence": 0.65,
                            "title": "Pattern from Successful Pursuit",
                            "description": f"A similar pursuit that succeeded took action at this stage.",
                            "action_taken": action,
                            "outcome": outcome,
                            "suggestion": f"Consider: {action}",
                            "source": "success_pattern"
                        })
                        break  # Just one for now

        return predictions

    def _predict_stall_warnings(self, context: Dict) -> List[Dict]:
        """Predict potential stalls based on velocity patterns."""
        predictions = []

        if not self.velocity_tracker:
            return predictions

        # Check velocity trend
        velocity_history = self.db.get_velocity_history(context["pursuit_id"], limit=4)

        if len(velocity_history) >= 3:
            # Check for declining trend
            velocities = [v.get("elements_per_week", 0) for v in velocity_history]

            if all(velocities[i] >= velocities[i+1] for i in range(len(velocities)-1)):
                # Consistent decline
                decline_rate = (velocities[0] - velocities[-1]) / max(1, velocities[-1])

                if decline_rate > 0.3:
                    predictions.append({
                        "type": "STALL_WARNING",
                        "confidence": 0.70,
                        "title": "Declining Velocity Pattern",
                        "description": f"Velocity has been declining. Pursuits with this pattern often stall.",
                        "timeframe": "Within 7-14 days without intervention",
                        "suggestion": "Review potential blockers or scope concerns",
                        "source": "velocity_trend"
                    })

        # Check for near-zero velocity
        current_velocity = context.get("elements_per_week", 0)
        if current_velocity < 0.5 and context.get("days_in_phase", 0) > 7:
            predictions.append({
                "type": "STALL_WARNING",
                "confidence": 0.75,
                "title": "Low Activity Warning",
                "description": "Very little progress in the past week. Risk of pursuit stalling.",
                "timeframe": "Immediate",
                "suggestion": "Re-engage with the pursuit to maintain momentum",
                "source": "activity_analysis"
            })

        return predictions

    def _predict_methodology_hints(self, context: Dict) -> List[Dict]:
        """Predict methodology-specific guidance."""
        predictions = []

        methodology = context.get("methodology", "LEAN_STARTUP")
        phase = context["current_phase"]
        phase_percent = context.get("phase_percent", 50)

        # Methodology-specific hints
        methodology_hints = {
            "LEAN_STARTUP": {
                "VISION": [
                    (20, "This is a good time to define your Minimum Viable Product (MVP)"),
                    (60, "Consider creating a lean canvas to clarify your business model"),
                    (80, "Time to identify your riskiest assumptions for testing")
                ],
                "DE_RISK": [
                    (20, "Start with your riskiest assumption first"),
                    (50, "Consider a smoke test to validate demand"),
                    (80, "Review pivots: what have you learned that changes direction?")
                ]
            },
            "DESIGN_THINKING": {
                "VISION": [
                    (30, "Empathy mapping can help deepen user understanding"),
                    (60, "Consider 'How Might We' statements to reframe problems"),
                    (80, "Synthesize insights before ideating solutions")
                ],
                "DE_RISK": [
                    (30, "Rapid prototyping can test ideas quickly"),
                    (60, "User testing provides valuable feedback - plan sessions"),
                    (80, "Iterate based on feedback before finalizing")
                ]
            }
        }

        hints = methodology_hints.get(methodology, {}).get(phase, [])

        for threshold, hint in hints:
            if phase_percent >= threshold - 10 and phase_percent <= threshold + 10:
                predictions.append({
                    "type": "METHODOLOGY_HINT",
                    "confidence": 0.65,
                    "title": f"{methodology.replace('_', ' ').title()} Guidance",
                    "description": hint,
                    "methodology": methodology,
                    "phase_timing": f"~{threshold}% through {phase}",
                    "source": "methodology_knowledge"
                })
                break  # One hint per call

        return predictions

    def get_high_confidence_predictions(self, pursuit_id: str) -> List[Dict]:
        """Get only high-confidence predictions."""
        all_predictions = self.generate_predictions(pursuit_id)
        threshold = self.config.get("high_confidence_threshold", 0.75)
        return [p for p in all_predictions if p["confidence"] >= threshold]

    def should_surface_prediction(self, pursuit_id: str) -> Optional[Dict]:
        """
        Determine if a prediction should be surfaced in conversation.

        Returns highest confidence prediction if one should be surfaced,
        None otherwise.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Prediction dict or None
        """
        predictions = self.get_high_confidence_predictions(pursuit_id)

        if not predictions:
            return None

        # Return highest confidence
        return predictions[0]

    def format_prediction_for_coaching(self, prediction: Dict) -> str:
        """
        Format a prediction for natural coaching integration.

        Args:
            prediction: Prediction dict

        Returns:
            Natural language string for coaching
        """
        pred_type = prediction.get("type", "GENERAL")

        templates = {
            "PHASE_CHALLENGE": (
                "I've noticed that teams at this stage sometimes encounter {title}. "
                "{description} {suggestion}"
            ),
            "UPCOMING_RISK": (
                "Looking ahead, {description} "
                "This might happen {timeframe}. {suggestion}"
            ),
            "OPPORTUNITY_WINDOW": (
                "Here's something interesting: {description} "
                "They found that {action_taken} led to {outcome}. "
                "Might be worth considering."
            ),
            "STALL_WARNING": (
                "{description} {suggestion}"
            ),
            "METHODOLOGY_HINT": (
                "{description}"
            )
        }

        template = templates.get(pred_type, "{description}")

        return template.format(**prediction)
