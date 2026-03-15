"""
InDE MVP v3.0.2 - Temporal Pattern Intelligence
Enrich IML pattern matching with temporal signals.

Features:
- Temporal similarity scoring in pattern matching
- Anti-pattern detection based on temporal signals
- Phase benchmark comparisons
- Velocity-correlated pattern relevance
- GPU-accelerated similarity computations

Pattern Matching Weights (v3.0.2):
- domain_match: 28%
- methodology_match: 20%
- tag_overlap: 20%
- phase_relevance: 12%
- temporal_similarity: 20% (NEW)
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import math

from config import (
    TEMPORAL_PATTERN_CONFIG, PATTERN_MATCHING_WEIGHTS,
    TEMPORAL_ANTIPATTERNS, IKF_PHASES
)


class TemporalPatternIntelligence:
    """
    Enrich pattern matching with temporal context.

    Adds temporal signals to the existing IML pattern matching
    to improve relevance of surfaced patterns.
    """

    def __init__(self, db, velocity_tracker=None, phase_manager=None,
                 event_logger=None):
        """
        Initialize temporal pattern intelligence.

        Args:
            db: Database instance
            velocity_tracker: Optional VelocityTracker from TIM
            phase_manager: Optional PhaseManager from TIM
            event_logger: Optional TemporalEventLogger from TIM
        """
        self.db = db
        self.velocity_tracker = velocity_tracker
        self.phase_manager = phase_manager
        self.event_logger = event_logger
        self.config = TEMPORAL_PATTERN_CONFIG
        self.weights = PATTERN_MATCHING_WEIGHTS

    def enrich_pattern_matches(self, pursuit_id: str,
                                base_matches: List[Dict]) -> List[Dict]:
        """
        Enrich pattern matches with temporal relevance scoring.

        Args:
            pursuit_id: Current pursuit ID
            base_matches: Pattern matches from existing IML

        Returns:
            Enriched matches with temporal scores and adjusted relevance
        """
        if not self.config.get("enable_temporal_enrichment", True):
            return base_matches

        if not base_matches:
            return []

        # Get current pursuit temporal context
        pursuit_context = self._get_pursuit_temporal_context(pursuit_id)

        enriched_matches = []
        for match in base_matches:
            enriched = self._enrich_single_match(match, pursuit_context)
            enriched_matches.append(enriched)

        # Re-sort by enriched relevance
        enriched_matches.sort(key=lambda x: x.get("enriched_relevance", 0), reverse=True)

        return enriched_matches

    def _get_pursuit_temporal_context(self, pursuit_id: str) -> Dict:
        """Get temporal context for the current pursuit."""
        context = {
            "pursuit_id": pursuit_id,
            "current_phase": "VISION",
            "velocity_status": "unknown",
            "elements_per_week": 0,
            "days_in_current_phase": 0,
            "phase_percent_complete": 0,
            "days_since_start": 0
        }

        # Get current phase
        if self.phase_manager:
            context["current_phase"] = self.phase_manager.get_current_phase(pursuit_id)
            phase_status = self.phase_manager.get_phase_status(
                pursuit_id, context["current_phase"]
            )
            context["days_in_current_phase"] = phase_status.get("days_used", 0)
            allocated = phase_status.get("days_allocated", 30)
            if allocated > 0:
                context["phase_percent_complete"] = (
                    context["days_in_current_phase"] / allocated * 100
                )

        # Get velocity
        if self.velocity_tracker:
            velocity = self.velocity_tracker.calculate_velocity(pursuit_id)
            context["velocity_status"] = velocity.get("status", "unknown")
            context["elements_per_week"] = velocity.get("elements_per_week", 0)

        # Get pursuit start date
        allocation = self.db.get_time_allocation(pursuit_id)
        if allocation:
            start_str = allocation.get("start_date")
            if start_str:
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00') if 'Z' in start_str else start_str)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                context["days_since_start"] = (datetime.now(timezone.utc) - start).days

        return context

    def _enrich_single_match(self, match: Dict, pursuit_context: Dict) -> Dict:
        """Enrich a single pattern match with temporal scoring."""
        pattern = match.get("pattern", {})
        base_relevance = match.get("relevance_score", 0.5)

        # Calculate temporal similarity
        temporal_score = self._calculate_temporal_similarity(pattern, pursuit_context)

        # Calculate enriched relevance using new weights
        temporal_weight = self.config.get("temporal_weight_in_matching", 0.20)

        # Adjust base relevance (reduce to 80% to make room for temporal)
        adjusted_base = base_relevance * (1 - temporal_weight)
        temporal_contribution = temporal_score * temporal_weight

        enriched_relevance = adjusted_base + temporal_contribution

        # Add enrichment data to match
        match["temporal_score"] = round(temporal_score, 3)
        match["enriched_relevance"] = round(enriched_relevance, 3)
        match["temporal_context"] = {
            "phase_match": pattern.get("source_phase") == pursuit_context["current_phase"],
            "velocity_correlation": self._get_velocity_correlation(pattern, pursuit_context),
            "timing_similarity": self._calculate_timing_similarity(pattern, pursuit_context)
        }

        return match

    def _calculate_temporal_similarity(self, pattern: Dict,
                                        pursuit_context: Dict) -> float:
        """
        Calculate temporal similarity between pattern and current pursuit.

        Considers:
        - Phase alignment
        - Velocity correlation
        - Timing in phase similarity
        """
        scores = []

        # 1. Phase alignment (40% of temporal score)
        phase_score = 1.0 if pattern.get("source_phase") == pursuit_context["current_phase"] else 0.3
        scores.append(("phase", phase_score, 0.4))

        # 2. Velocity correlation (30% of temporal score)
        velocity_score = self._get_velocity_correlation(pattern, pursuit_context)
        scores.append(("velocity", velocity_score, 0.3))

        # 3. Timing similarity (30% of temporal score)
        timing_score = self._calculate_timing_similarity(pattern, pursuit_context)
        scores.append(("timing", timing_score, 0.3))

        # Weighted sum
        total = sum(score * weight for _, score, weight in scores)
        return total

    def _get_velocity_correlation(self, pattern: Dict, context: Dict) -> float:
        """Calculate velocity correlation between pattern and current pursuit."""
        pattern_velocity = pattern.get("metadata", {}).get("velocity_at_capture")
        current_velocity = context.get("elements_per_week", 0)

        if not pattern_velocity:
            return 0.5  # Neutral if unknown

        # Calculate similarity
        if pattern_velocity == 0:
            return 0.5

        ratio = current_velocity / pattern_velocity
        if 0.8 <= ratio <= 1.2:
            return 1.0  # Very similar
        elif 0.5 <= ratio <= 1.5:
            return 0.7  # Somewhat similar
        else:
            return 0.3  # Different velocity contexts

    def _calculate_timing_similarity(self, pattern: Dict, context: Dict) -> float:
        """Calculate timing similarity based on phase progression."""
        pattern_phase_percent = pattern.get("metadata", {}).get("phase_percent_at_capture", 50)
        current_percent = context.get("phase_percent_complete", 50)

        # Calculate difference
        diff = abs(pattern_phase_percent - current_percent)

        if diff <= 10:
            return 1.0  # Very similar timing
        elif diff <= 25:
            return 0.7  # Reasonably similar
        elif diff <= 50:
            return 0.4  # Different but potentially relevant
        else:
            return 0.2  # Very different timing

    def detect_antipatterns(self, pursuit_id: str) -> List[Dict]:
        """
        Detect temporal anti-patterns in the pursuit.

        Anti-patterns indicate potential issues that should be
        surfaced to guide coaching interventions.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of detected anti-patterns
        """
        if not self.config.get("antipattern_detection_enabled", True):
            return []

        detected = []

        # Get temporal context
        context = self._get_pursuit_temporal_context(pursuit_id)

        # Check each anti-pattern
        for antipattern in TEMPORAL_ANTIPATTERNS:
            result = self._check_antipattern(antipattern, pursuit_id, context)
            if result["detected"]:
                detected.append(result)

        return detected

    def _check_antipattern(self, antipattern: str, pursuit_id: str,
                           context: Dict) -> Dict:
        """Check for a specific anti-pattern."""
        result = {
            "antipattern": antipattern,
            "detected": False,
            "severity": "LOW",
            "description": "",
            "recommendation": ""
        }

        if antipattern == "VISION_STALL":
            # >30% of total time in VISION phase
            allocation = self.db.get_time_allocation(pursuit_id)
            if allocation and context["current_phase"] == "VISION":
                total_days = allocation.get("total_days", 180)
                vision_days = context.get("days_in_current_phase", 0)
                if total_days > 0 and vision_days / total_days > 0.30:
                    result["detected"] = True
                    result["severity"] = "MEDIUM"
                    result["description"] = f"Vision phase is consuming {vision_days / total_days * 100:.0f}% of allocated time"
                    result["recommendation"] = "Consider transitioning to de-risk phase to maintain momentum"

        elif antipattern == "VELOCITY_COLLAPSE":
            # >50% velocity drop over 2-week window
            if self.velocity_tracker:
                history = self.db.get_velocity_history(pursuit_id, limit=4)
                if len(history) >= 2:
                    current = history[0].get("elements_per_week", 0)
                    previous = history[-1].get("elements_per_week", 1)
                    if previous > 0:
                        change = (current - previous) / previous
                        if change < -0.50:
                            result["detected"] = True
                            result["severity"] = "HIGH"
                            result["description"] = f"Velocity dropped {abs(change) * 100:.0f}% recently"
                            result["recommendation"] = "Review potential blockers or scope concerns"

        elif antipattern == "PHASE_SKIP":
            # Moved to DEPLOY without adequate DE_RISK time
            if context["current_phase"] == "DEPLOY":
                phase_history = self.db.get_phase_history(pursuit_id)
                derisk_duration = self._get_phase_duration(phase_history, "DE_RISK")
                if derisk_duration and derisk_duration < 14:  # Less than 2 weeks
                    result["detected"] = True
                    result["severity"] = "HIGH"
                    result["description"] = f"DE_RISK phase lasted only {derisk_duration} days"
                    result["recommendation"] = "Consider revisiting risk validation before proceeding"

        elif antipattern == "BUFFER_EXHAUSTION":
            # Buffer consumed before 60% completion
            allocation = self.db.get_time_allocation(pursuit_id)
            if allocation:
                scaffolding = self.db.get_scaffolding_state(pursuit_id)
                if scaffolding:
                    completeness = scaffolding.get("completeness", {})
                    avg_complete = (
                        completeness.get("vision", 0) +
                        completeness.get("fears", 0) +
                        completeness.get("hypothesis", 0)
                    ) / 3

                    total_days = allocation.get("total_days", 180)
                    elapsed = context.get("days_since_start", 0)
                    buffer_days = allocation.get("buffer_days", total_days * 0.1)

                    if elapsed > total_days - buffer_days and avg_complete < 0.60:
                        result["detected"] = True
                        result["severity"] = "HIGH"
                        result["description"] = "Timeline buffer being used at low completion"
                        result["recommendation"] = "Reassess timeline or scope to ensure completion"

        elif antipattern == "ELEMENT_DROUGHT":
            # No new elements captured in >10 days
            if self.event_logger:
                recent_events = self.event_logger.get_events_by_type(
                    pursuit_id, "ELEMENT_CAPTURED"
                )
                if recent_events:
                    last_event = recent_events[0]
                    ts_str = last_event.get("timestamp", "")
                    last_ts = datetime.fromisoformat(
                        ts_str.replace('Z', '+00:00') if 'Z' in ts_str else ts_str.rstrip('Z')
                    )
                    if last_ts.tzinfo is None:
                        last_ts = last_ts.replace(tzinfo=timezone.utc)
                    days_since = (datetime.now(timezone.utc) - last_ts).days
                    if days_since > 10:
                        result["detected"] = True
                        result["severity"] = "MEDIUM"
                        result["description"] = f"No new elements captured in {days_since} days"
                        result["recommendation"] = "Re-engage with the pursuit to maintain progress"
                else:
                    result["detected"] = True
                    result["severity"] = "LOW"
                    result["description"] = "No elements captured yet"
                    result["recommendation"] = "Begin capturing your vision and concerns"

        return result

    def _get_phase_duration(self, history: List[Dict], phase: str) -> Optional[int]:
        """Get duration of a specific phase from history."""
        for i, record in enumerate(history):
            if record.get("to_phase") == phase:
                start_str = record.get("transitioned_at")
                if start_str:
                    start = datetime.fromisoformat(start_str.replace('Z', '+00:00') if 'Z' in start_str else start_str)
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)

                    # Find end
                    if i + 1 < len(history):
                        end_str = history[i + 1].get("transitioned_at")
                        if end_str:
                            end = datetime.fromisoformat(end_str.replace('Z', '+00:00') if 'Z' in end_str else end_str)
                            if end.tzinfo is None:
                                end = end.replace(tzinfo=timezone.utc)
                            return (end - start).days

                    # Phase is current
                    return (datetime.now(timezone.utc) - start).days

        return None

    def get_phase_benchmarks(self, phase: str) -> Dict:
        """
        Get benchmarks for a phase based on historical patterns.

        Args:
            phase: Phase to get benchmarks for

        Returns:
            Dict with benchmark metrics
        """
        if not self.config.get("phase_benchmark_enabled", True):
            return {}

        # Query patterns completed in this phase
        patterns = list(self.db.db.patterns.find({
            "source_phase": phase,
            "outcome": {"$in": ["SUCCESS", "PIVOT_SUCCESS"]}
        }).limit(100))

        if not patterns:
            # Default benchmarks
            defaults = {
                "VISION": {"avg_days": 20, "avg_elements": 8, "avg_velocity": 3},
                "DE_RISK": {"avg_days": 50, "avg_elements": 12, "avg_velocity": 2},
                "DEPLOY": {"avg_days": 60, "avg_elements": 6, "avg_velocity": 1}
            }
            return defaults.get(phase, {})

        # Calculate benchmarks from patterns
        days = [p.get("metadata", {}).get("phase_days", 30) for p in patterns]
        elements = [p.get("metadata", {}).get("elements_captured", 5) for p in patterns]
        velocities = [p.get("metadata", {}).get("avg_velocity", 2) for p in patterns]

        return {
            "avg_days": sum(days) / len(days) if days else 30,
            "avg_elements": sum(elements) / len(elements) if elements else 5,
            "avg_velocity": sum(velocities) / len(velocities) if velocities else 2,
            "sample_size": len(patterns)
        }

    def compare_to_benchmarks(self, pursuit_id: str) -> Dict:
        """
        Compare pursuit to phase benchmarks.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with comparison results
        """
        context = self._get_pursuit_temporal_context(pursuit_id)
        phase = context["current_phase"]
        benchmarks = self.get_phase_benchmarks(phase)

        if not benchmarks:
            return {"message": "No benchmarks available"}

        # Compare
        days_vs_avg = context["days_in_current_phase"] / max(1, benchmarks.get("avg_days", 30))
        velocity_vs_avg = context["elements_per_week"] / max(0.1, benchmarks.get("avg_velocity", 2))

        return {
            "phase": phase,
            "benchmarks": benchmarks,
            "current": {
                "days_in_phase": context["days_in_current_phase"],
                "velocity": context["elements_per_week"]
            },
            "comparisons": {
                "days_ratio": round(days_vs_avg, 2),
                "velocity_ratio": round(velocity_vs_avg, 2)
            },
            "assessment": self._assess_benchmark_comparison(days_vs_avg, velocity_vs_avg)
        }

    def _assess_benchmark_comparison(self, days_ratio: float,
                                      velocity_ratio: float) -> str:
        """Generate assessment message for benchmark comparison."""
        messages = []

        if days_ratio > 1.5:
            messages.append("Taking longer than typical in this phase")
        elif days_ratio < 0.5:
            messages.append("Moving faster than typical through this phase")

        if velocity_ratio > 1.3:
            messages.append("Progress velocity is above average")
        elif velocity_ratio < 0.7:
            messages.append("Progress velocity is below average")

        if not messages:
            return "Progressing normally compared to similar pursuits"

        return ". ".join(messages) + "."
