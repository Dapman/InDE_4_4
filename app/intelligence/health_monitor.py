"""
InDE MVP v3.0.2 - Health Monitor
Real-time pursuit health scoring system with five health zones.

Features:
- Composite health score (0-100) calculated from multiple signals
- Five health zones: THRIVING, HEALTHY, ATTENTION, AT_RISK, CRITICAL
- Zone-specific coaching guidelines for ODICM
- Health history tracking for trend analysis
- Crisis mode detection for rapid deterioration

Health Score Components:
- velocity_health (30%): Is progress pace on track?
- element_coverage (25%): Are critical elements being captured?
- phase_timing (20%): Is phase duration within allocation?
- engagement_rhythm (15%): Is the innovator consistently active?
- risk_posture (10%): Are identified risks being addressed?
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import time

from config import (
    HEALTH_MONITOR_CONFIG, HEALTH_ZONES, HEALTH_SCORE_WEIGHTS,
    ZONE_COACHING_GUIDELINES
)


class HealthMonitor:
    """
    Monitor and score pursuit health in real-time.

    Calculates a composite health score from multiple signals and
    assigns pursuits to one of five health zones for coaching guidance.
    """

    # Health zones ordered from best to worst
    ZONE_ORDER = ["THRIVING", "HEALTHY", "ATTENTION", "AT_RISK", "CRITICAL"]

    def __init__(self, db, velocity_tracker=None, phase_manager=None, ikf_insights=None):
        """
        Initialize health monitor.

        Args:
            db: Database instance
            velocity_tracker: Optional VelocityTracker from TIM
            phase_manager: Optional PhaseManager from TIM
            ikf_insights: Optional IKFInsightsProvider for federation benchmarks
        """
        self.db = db
        self.velocity_tracker = velocity_tracker
        self.phase_manager = phase_manager
        self.ikf_insights = ikf_insights
        self.config = HEALTH_MONITOR_CONFIG
        self.zones = HEALTH_ZONES
        self.weights = HEALTH_SCORE_WEIGHTS
        self._cache = {}
        self._cache_ttl = self.config.get("health_score_cache_ttl_seconds", 300)
        self._benchmark_cache = {}

    def calculate_health(self, pursuit_id: str, force_refresh: bool = False) -> Dict:
        """
        Calculate comprehensive health score for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            force_refresh: Force recalculation even if cached

        Returns:
            Dict with health score, zone, and component breakdown
        """
        if not self.config.get("enable_health_monitoring", True):
            return self._disabled_response()

        # Check cache
        cache_key = f"health_{pursuit_id}"
        if not force_refresh and cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return cached["data"]

        # Get pursuit context
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {"error": "Pursuit not found"}

        scaffolding_state = self.db.get_scaffolding_state(pursuit_id)

        # Calculate component scores
        components = {}

        # 1. Velocity Health (30%)
        components["velocity_health"] = self._calculate_velocity_health(pursuit_id)

        # 2. Element Coverage (25%)
        components["element_coverage"] = self._calculate_element_coverage(
            pursuit_id, scaffolding_state
        )

        # 3. Phase Timing (20%)
        components["phase_timing"] = self._calculate_phase_timing(pursuit_id)

        # 4. Engagement Rhythm (15%)
        components["engagement_rhythm"] = self._calculate_engagement_rhythm(pursuit_id)

        # 5. Risk Posture (10%)
        components["risk_posture"] = self._calculate_risk_posture(pursuit_id)

        # Calculate weighted composite score
        composite_score = 0.0
        for component, score in components.items():
            weight = self.weights.get(component, 0)
            composite_score += score * weight

        # Normalize to 0-100
        composite_score = min(100, max(0, composite_score * 100))

        # Determine zone
        zone = self._determine_zone(composite_score)

        # Check for crisis conditions
        crisis_triggered = self._check_crisis_conditions(
            pursuit_id, composite_score, zone
        )

        # Build result
        result = {
            "pursuit_id": pursuit_id,
            "health_score": round(composite_score, 1),
            "zone": zone,
            "zone_info": self.zones.get(zone, {}),
            "components": {
                k: round(v * 100, 1) for k, v in components.items()
            },
            "weights": self.weights,
            "coaching_guidelines": ZONE_COACHING_GUIDELINES.get(zone, {}),
            "crisis_triggered": crisis_triggered,
            "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

        # Save to database
        self._save_health_score(result)

        # Update cache
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "data": result
        }

        return result

    def _calculate_velocity_health(self, pursuit_id: str) -> float:
        """Calculate health based on progress velocity."""
        if not self.velocity_tracker:
            return 0.5  # Default if no tracker

        try:
            velocity = self.velocity_tracker.calculate_velocity(pursuit_id)
            status = velocity.get("status", "unknown")

            # Map status to health score
            status_scores = {
                "ahead": 1.0,
                "on_track": 0.8,
                "slightly_behind": 0.5,
                "behind": 0.3,
                "significantly_behind": 0.1,
                "unknown": 0.5
            }

            return status_scores.get(status, 0.5)
        except Exception:
            return 0.5

    def _calculate_element_coverage(self, pursuit_id: str,
                                     scaffolding_state: Dict) -> float:
        """Calculate health based on element capture completeness."""
        if not scaffolding_state:
            return 0.3  # Low score if no state

        # Get completeness from scaffolding state
        completeness = scaffolding_state.get("completeness", {})

        vision = completeness.get("vision", 0.0)
        fears = completeness.get("fears", 0.0)
        hypothesis = completeness.get("hypothesis", 0.0)

        # Get current phase to weight appropriately
        current_phase = "VISION"
        if self.phase_manager:
            current_phase = self.phase_manager.get_current_phase(pursuit_id)

        # Weight based on phase
        if current_phase == "VISION":
            # Vision most important
            return vision * 0.7 + fears * 0.2 + hypothesis * 0.1
        elif current_phase == "DE_RISK":
            # De-risk elements most important
            return vision * 0.3 + fears * 0.4 + hypothesis * 0.3
        else:  # DEPLOY
            # All should be near complete
            return (vision + fears + hypothesis) / 3

    def _calculate_phase_timing(self, pursuit_id: str) -> float:
        """Calculate health based on phase timing relative to allocation."""
        if not self.phase_manager:
            return 0.5

        try:
            # Get current phase and allocation
            current_phase = self.phase_manager.get_current_phase(pursuit_id)
            phase_status = self.phase_manager.get_phase_status(pursuit_id, current_phase)

            days_allocated = phase_status.get("days_allocated", 30)
            days_used = phase_status.get("days_used", 0)

            if days_allocated == 0:
                return 0.5

            # Calculate ratio
            usage_ratio = days_used / days_allocated

            # Score based on usage
            if usage_ratio <= 0.5:
                return 1.0  # Plenty of time
            elif usage_ratio <= 0.75:
                return 0.8  # On track
            elif usage_ratio <= 1.0:
                return 0.5  # Getting close
            elif usage_ratio <= 1.25:
                return 0.3  # Over time
            else:
                return 0.1  # Significantly over

        except Exception:
            return 0.5

    async def _calculate_phase_timing_with_ikf(
        self, pursuit_id: str, methodology: str, phase: str
    ) -> float:
        """
        Calculate phase timing health using IKF benchmarks.

        Compares actual duration against federation benchmark data.
        """
        if not self.phase_manager:
            return 0.5

        try:
            phase_status = self.phase_manager.get_phase_status(pursuit_id, phase)
            days_used = phase_status.get("days_used", 0)

            # Get IKF benchmarks
            if self.ikf_insights:
                benchmarks = await self.ikf_insights.get_phase_benchmarks(
                    methodology, phase
                )

                p50 = benchmarks.get("p50")
                p75 = benchmarks.get("p75")

                if p50 and p75:
                    if days_used <= p50 * 0.5:
                        return 1.0  # Well ahead
                    elif days_used <= p50:
                        return 0.85  # On track (faster than median)
                    elif days_used <= p75:
                        return 0.6  # Acceptable (between median and 75th)
                    elif days_used <= p75 * 1.25:
                        return 0.3  # Behind (past 75th percentile)
                    else:
                        return 0.1  # Significantly behind

            # Fallback to local calculation
            return self._calculate_phase_timing(pursuit_id)

        except Exception:
            return self._calculate_phase_timing(pursuit_id)

    def _calculate_engagement_rhythm(self, pursuit_id: str) -> float:
        """Calculate health based on engagement patterns."""
        # Get recent conversation history
        try:
            history = list(self.db.db.conversation_history.find(
                {"pursuit_id": pursuit_id}
            ).sort("timestamp", -1).limit(30))

            if not history:
                return 0.3  # Low if no history

            # Calculate days since last activity
            if history:
                last_activity = history[0].get("timestamp")
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(
                        last_activity.replace('Z', '+00:00') if 'Z' in last_activity else last_activity
                    )
                if isinstance(last_activity, datetime) and last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - last_activity).days

                if days_since == 0:
                    recency_score = 1.0
                elif days_since <= 2:
                    recency_score = 0.9
                elif days_since <= 7:
                    recency_score = 0.6
                elif days_since <= 14:
                    recency_score = 0.3
                else:
                    recency_score = 0.1
            else:
                recency_score = 0.3

            # Calculate consistency (variance in activity)
            if len(history) >= 5:
                # Simple measure: count of activities in last 7 days vs 7-14 days
                recent = sum(1 for h in history
                            if self._days_ago(h.get("timestamp")) <= 7)
                older = sum(1 for h in history
                           if 7 < self._days_ago(h.get("timestamp")) <= 14)

                if recent > 0 and older > 0:
                    consistency_score = min(1.0, recent / max(1, older))
                else:
                    consistency_score = 0.5
            else:
                consistency_score = 0.5

            return (recency_score * 0.6 + consistency_score * 0.4)

        except Exception:
            return 0.5

    def _days_ago(self, timestamp) -> int:
        """Calculate days since timestamp."""
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(
                timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp
            )
        if not timestamp:
            return 999
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - timestamp).days

    def _calculate_risk_posture(self, pursuit_id: str) -> float:
        """Calculate health based on risk validation status."""
        try:
            # Get RVE status
            rve_status = self.db.get_pursuit_rve_status(pursuit_id)
            if not rve_status or not rve_status.get("enabled"):
                return 0.5  # Neutral if RVE not enabled

            total = rve_status.get("total_risks_identified", 0)
            if total == 0:
                return 0.5  # No risks identified

            validated = rve_status.get("risks_validated", 0)
            green = rve_status.get("risks_green", 0)
            red = rve_status.get("risks_red", 0)

            # Score based on validation progress and outcomes
            validation_progress = validated / total
            green_ratio = green / max(1, validated) if validated > 0 else 0
            red_ratio = red / max(1, validated) if validated > 0 else 0

            # Calculate score
            progress_score = validation_progress * 0.4
            outcome_score = (green_ratio - red_ratio * 0.5) * 0.6

            return max(0, min(1, progress_score + outcome_score + 0.3))

        except Exception:
            return 0.5

    def _determine_zone(self, score: float) -> str:
        """Determine health zone based on score."""
        for zone, config in self.zones.items():
            if config["min"] <= score <= config["max"]:
                return zone
        return "ATTENTION"  # Default

    def _check_crisis_conditions(self, pursuit_id: str, score: float,
                                  zone: str) -> bool:
        """Check if crisis conditions are met."""
        if not self.config.get("crisis_mode_enabled", True):
            return False

        # Crisis triggered if:
        # 1. Score is CRITICAL
        # 2. Score dropped significantly recently

        if zone == "CRITICAL":
            return True

        # Check for rapid deterioration
        history = self.get_health_history(pursuit_id, limit=5)
        if len(history) >= 2:
            previous_score = history[1].get("health_score", score)
            drop = previous_score - score
            if drop >= 20:  # 20 point drop
                return True

        return False

    def _save_health_score(self, health_result: Dict) -> None:
        """Save health score to database."""
        self.db.save_health_score({
            "pursuit_id": health_result["pursuit_id"],
            "health_score": health_result["health_score"],
            "zone": health_result["zone"],
            "components": health_result["components"],
            "crisis_triggered": health_result["crisis_triggered"]
        })

    def _disabled_response(self) -> Dict:
        """Return response when health monitoring is disabled."""
        return {
            "health_score": 50,
            "zone": "HEALTHY",
            "monitoring_disabled": True,
            "message": "Health monitoring is disabled"
        }

    def get_health_history(self, pursuit_id: str, days: int = 30,
                           limit: int = 100) -> List[Dict]:
        """Get health score history for a pursuit."""
        return self.db.get_health_score_history(pursuit_id, days, limit)

    def get_health_trend(self, pursuit_id: str, window_days: int = 7) -> Dict:
        """
        Calculate health trend over time window.

        Args:
            pursuit_id: Pursuit ID
            window_days: Days to analyze

        Returns:
            Dict with trend analysis
        """
        history = self.get_health_history(pursuit_id, days=window_days)

        if len(history) < 2:
            return {
                "trend": "stable",
                "change": 0,
                "message": "Not enough data for trend analysis"
            }

        # Calculate trend
        scores = [h.get("health_score", 50) for h in history]
        oldest = scores[-1] if scores else 50
        newest = scores[0] if scores else 50
        change = newest - oldest

        if change > 10:
            trend = "improving"
        elif change < -10:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change": round(change, 1),
            "oldest_score": oldest,
            "newest_score": newest,
            "data_points": len(history),
            "message": self._get_trend_message(trend, change)
        }

    def _get_trend_message(self, trend: str, change: float) -> str:
        """Generate human-friendly trend message."""
        if trend == "improving":
            return f"Health has improved by {abs(change):.0f} points recently."
        elif trend == "declining":
            return f"Health has declined by {abs(change):.0f} points. Consider reviewing blockers."
        else:
            return "Health has been stable."

    def get_coaching_context(self, pursuit_id: str) -> Dict:
        """
        Get health context for coaching decisions.

        Provides zone-specific guidance for ODICM to adjust tone
        and intervention style.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with coaching context
        """
        health = self.calculate_health(pursuit_id)

        return {
            "zone": health.get("zone", "HEALTHY"),
            "health_score": health.get("health_score", 50),
            "coaching_guidelines": health.get("coaching_guidelines", {}),
            "crisis_mode": health.get("crisis_triggered", False),
            "weak_components": self._identify_weak_components(health),
            "suggested_focus": self._suggest_focus_area(health)
        }

    def _identify_weak_components(self, health: Dict) -> List[str]:
        """Identify components scoring below 50%."""
        components = health.get("components", {})
        weak = []

        for component, score in components.items():
            if score < 50:
                weak.append({
                    "component": component,
                    "score": score,
                    "label": component.replace("_", " ").title()
                })

        return sorted(weak, key=lambda x: x["score"])

    def _suggest_focus_area(self, health: Dict) -> str:
        """Suggest primary focus area based on health."""
        weak = self._identify_weak_components(health)

        if not weak:
            return "Continue current momentum"

        weakest = weak[0]["component"]

        suggestions = {
            "velocity_health": "Focus on making progress on key elements",
            "element_coverage": "Capture more details about your pursuit",
            "phase_timing": "Review timeline and consider scope adjustment",
            "engagement_rhythm": "Maintain consistent engagement with your pursuit",
            "risk_posture": "Address identified risks with validation experiments"
        }

        return suggestions.get(weakest, "Review overall pursuit health")

    def get_zone_distribution(self, user_id: str = None) -> Dict:
        """
        Get distribution of pursuits across health zones.

        Useful for portfolio-level health monitoring.

        Args:
            user_id: Optional user ID to filter

        Returns:
            Dict with zone distribution
        """
        # Get all active pursuits
        query = {"state": "ACTIVE"}
        if user_id:
            query["user_id"] = user_id

        pursuits = list(self.db.db.pursuits.find(query))

        distribution = {zone: [] for zone in self.ZONE_ORDER}

        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id")
            health = self.calculate_health(pursuit_id)
            zone = health.get("zone", "HEALTHY")

            distribution[zone].append({
                "pursuit_id": pursuit_id,
                "title": pursuit.get("title", "Untitled"),
                "score": health.get("health_score", 50)
            })

        return {
            "distribution": distribution,
            "counts": {zone: len(items) for zone, items in distribution.items()},
            "total_pursuits": len(pursuits),
            "needs_attention": len(distribution.get("AT_RISK", [])) + len(distribution.get("CRITICAL", []))
        }
