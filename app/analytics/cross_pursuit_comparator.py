"""
InDE MVP v3.0.3 - Cross-Pursuit Comparator
Benchmark individual pursuit performance against portfolio averages.

CRITICAL: All language is INFORMATIONAL, never judgmental.
- "15% faster than portfolio average" - NOT "outperforming others"
- "In the top quartile" - NOT "best performing"
- "8% below typical rate" - NOT "underperforming"

Features:
- Velocity comparison with percentile ranking
- Health trajectory comparison with time-series alignment
- Risk profile comparison vs peers at similar maturity
- Element completion rate comparison
- RVE effectiveness comparison
- Natural language summaries for ODICM coaching
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics

from config import IKF_PHASES


class CrossPursuitComparator:
    """
    Enables portfolio-relative benchmarking.
    CRITICAL: All language is INFORMATIONAL, never judgmental.
    """

    def __init__(self, db, portfolio_intelligence=None):
        """
        Initialize cross-pursuit comparator.

        Args:
            db: Database instance
            portfolio_intelligence: Optional PortfolioIntelligenceEngine
        """
        self.db = db
        self.portfolio_intelligence = portfolio_intelligence

    def compare_velocity(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Compare pursuit velocity against portfolio average.

        Returns:
            {
                'pursuit_velocity': float,
                'portfolio_avg': float,
                'phase_avg': float,  # avg for same phase only
                'percentile': int,
                'delta_pct': float,
                'summary': str  # natural language for ODICM
            }
        """
        # Get pursuit velocity
        velocity_data = self.db.db.velocity_metrics.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("calculated_at", -1)]
        )

        pursuit_velocity = velocity_data.get("elements_per_week", 0) if velocity_data else 0

        # Get portfolio velocities
        pursuits = self.db.get_user_pursuits(user_id, status="active")
        velocities = []
        phase_velocities = []
        pursuit_phase = self._get_pursuit_phase(pursuit_id)

        for p in pursuits:
            p_id = p["pursuit_id"]
            v_data = self.db.db.velocity_metrics.find_one(
                {"pursuit_id": p_id},
                sort=[("calculated_at", -1)]
            )
            if v_data:
                v = v_data.get("elements_per_week", 0)
                velocities.append(v)

                # Same phase velocities
                p_phase = self._get_pursuit_phase(p_id)
                if p_phase == pursuit_phase:
                    phase_velocities.append(v)

        portfolio_avg = statistics.mean(velocities) if velocities else 0
        phase_avg = statistics.mean(phase_velocities) if phase_velocities else portfolio_avg

        # Calculate percentile
        sorted_velocities = sorted(velocities)
        percentile = self._calculate_percentile(pursuit_velocity, sorted_velocities)

        # Calculate delta
        delta_pct = ((pursuit_velocity - portfolio_avg) / portfolio_avg * 100) if portfolio_avg > 0 else 0

        # Generate summary (INFORMATIONAL, not judgmental)
        summary = self._generate_velocity_summary(
            pursuit_velocity, portfolio_avg, phase_avg, percentile, delta_pct, pursuit_phase
        )

        return {
            "pursuit_velocity": round(pursuit_velocity, 2),
            "portfolio_avg": round(portfolio_avg, 2),
            "phase_avg": round(phase_avg, 2),
            "percentile": percentile,
            "delta_pct": round(delta_pct, 1),
            "summary": summary
        }

    def compare_health_trajectory(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Health score trajectory compared to portfolio norm at equivalent phase progress.
        Uses time-series alignment to compare trajectories fairly.

        Returns:
            {
                'pursuit_trajectory': [{phase_percent, health_score}],
                'portfolio_norm': [{phase_percent, avg_health}],
                'current_delta': float,
                'trajectory_trend': str,
                'summary': str
            }
        """
        # Get pursuit health history
        pursuit_history = self.db.get_health_score_history(pursuit_id, limit=20)

        # Get all pursuits' health histories
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        # Aggregate by phase percentage
        all_by_phase = {}

        for p in pursuits:
            p_id = p["pursuit_id"]
            if p_id == pursuit_id:
                continue

            history = self.db.get_health_score_history(p_id, limit=20)
            for h in history:
                phase_pct = h.get("phase_percent", 50)
                bucket = int(phase_pct / 10) * 10  # 0, 10, 20, ...
                if bucket not in all_by_phase:
                    all_by_phase[bucket] = []
                all_by_phase[bucket].append(h.get("health_score", 50))

        # Calculate portfolio norm
        portfolio_norm = []
        for bucket in sorted(all_by_phase.keys()):
            scores = all_by_phase[bucket]
            avg = statistics.mean(scores) if scores else 50
            portfolio_norm.append({
                "phase_percent": bucket,
                "avg_health": round(avg, 1)
            })

        # Get current pursuit position
        pursuit_trajectory = []
        for h in pursuit_history:
            pursuit_trajectory.append({
                "phase_percent": h.get("phase_percent", 50),
                "health_score": h.get("health_score", 50),
                "calculated_at": h.get("calculated_at")
            })

        # Calculate current delta
        current_health = pursuit_history[0].get("health_score", 50) if pursuit_history else 50
        current_phase_pct = pursuit_history[0].get("phase_percent", 50) if pursuit_history else 50
        bucket = int(current_phase_pct / 10) * 10

        norm_at_bucket = next(
            (n for n in portfolio_norm if n["phase_percent"] == bucket),
            {"avg_health": 50}
        )
        current_delta = current_health - norm_at_bucket["avg_health"]

        # Determine trajectory trend
        if len(pursuit_trajectory) >= 3:
            recent = [t["health_score"] for t in pursuit_trajectory[:3]]
            if recent[0] > recent[-1] + 5:
                trajectory_trend = "improving"
            elif recent[0] < recent[-1] - 5:
                trajectory_trend = "declining"
            else:
                trajectory_trend = "stable"
        else:
            trajectory_trend = "insufficient_data"

        summary = self._generate_trajectory_summary(current_delta, trajectory_trend, current_phase_pct)

        return {
            "pursuit_trajectory": pursuit_trajectory[:10],  # Limit
            "portfolio_norm": portfolio_norm,
            "current_delta": round(current_delta, 1),
            "trajectory_trend": trajectory_trend,
            "summary": summary
        }

    def compare_risk_profile(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Risk density and severity compared to portfolio peers at similar maturity.

        Returns:
            {
                'pursuit_risk_count': int,
                'portfolio_avg_risks': float,
                'high_severity_delta': int,
                'phase_comparison': str,
                'summary': str
            }
        """
        pursuit_detection = self.db.get_latest_risk_detection(pursuit_id)
        pursuit_risks = pursuit_detection.get("risk_count", 0) if pursuit_detection else 0
        pursuit_high = 0
        if pursuit_detection:
            for horizon in ["short_term", "medium_term", "long_term"]:
                for risk in pursuit_detection.get("risks_by_horizon", {}).get(horizon, []):
                    if risk.get("severity") in ["HIGH", "CRITICAL"]:
                        pursuit_high += 1

        # Get portfolio risk counts
        pursuits = self.db.get_user_pursuits(user_id, status="active")
        pursuit_phase = self._get_pursuit_phase(pursuit_id)

        all_risks = []
        phase_risks = []
        all_high = []

        for p in pursuits:
            p_id = p["pursuit_id"]
            if p_id == pursuit_id:
                continue

            detection = self.db.get_latest_risk_detection(p_id)
            if detection:
                count = detection.get("risk_count", 0)
                all_risks.append(count)

                p_phase = self._get_pursuit_phase(p_id)
                if p_phase == pursuit_phase:
                    phase_risks.append(count)

                high_count = 0
                for horizon in ["short_term", "medium_term", "long_term"]:
                    for risk in detection.get("risks_by_horizon", {}).get(horizon, []):
                        if risk.get("severity") in ["HIGH", "CRITICAL"]:
                            high_count += 1
                all_high.append(high_count)

        portfolio_avg = statistics.mean(all_risks) if all_risks else 0
        avg_high = statistics.mean(all_high) if all_high else 0
        high_delta = pursuit_high - avg_high

        # Phase comparison
        if phase_risks:
            phase_avg = statistics.mean(phase_risks)
            if pursuit_risks < phase_avg - 1:
                phase_comparison = "fewer risks than typical for this phase"
            elif pursuit_risks > phase_avg + 1:
                phase_comparison = "more risks than typical for this phase"
            else:
                phase_comparison = "typical risk level for this phase"
        else:
            phase_comparison = "insufficient data for phase comparison"

        summary = self._generate_risk_summary(
            pursuit_risks, portfolio_avg, high_delta, phase_comparison
        )

        return {
            "pursuit_risk_count": pursuit_risks,
            "portfolio_avg_risks": round(portfolio_avg, 1),
            "pursuit_high_severity": pursuit_high,
            "high_severity_delta": round(high_delta, 1),
            "phase_comparison": phase_comparison,
            "summary": summary
        }

    def compare_element_completion(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Scaffolding element completion rate vs. portfolio norms by phase.

        Returns:
            {
                'pursuit_completion': float,
                'portfolio_avg': float,
                'phase_avg': float,
                'delta_pct': float,
                'summary': str
            }
        """
        # Get pursuit scaffolding
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        completeness = scaffolding.get("completeness", {}) if scaffolding else {}

        # Calculate average completion
        pursuit_completion = self._calculate_overall_completeness(completeness)

        # Get portfolio completeness
        pursuits = self.db.get_user_pursuits(user_id, status="active")
        pursuit_phase = self._get_pursuit_phase(pursuit_id)

        all_completions = []
        phase_completions = []

        for p in pursuits:
            p_id = p["pursuit_id"]
            if p_id == pursuit_id:
                continue

            s = self.db.get_scaffolding_state(p_id)
            if s:
                c = s.get("completeness", {})
                comp = self._calculate_overall_completeness(c)
                all_completions.append(comp)

                p_phase = self._get_pursuit_phase(p_id)
                if p_phase == pursuit_phase:
                    phase_completions.append(comp)

        portfolio_avg = statistics.mean(all_completions) if all_completions else 0.5
        phase_avg = statistics.mean(phase_completions) if phase_completions else portfolio_avg
        delta_pct = (pursuit_completion - phase_avg) * 100

        summary = self._generate_completion_summary(pursuit_completion, phase_avg, delta_pct, pursuit_phase)

        return {
            "pursuit_completion": round(pursuit_completion * 100, 1),
            "portfolio_avg": round(portfolio_avg * 100, 1),
            "phase_avg": round(phase_avg * 100, 1),
            "delta_pct": round(delta_pct, 1),
            "summary": summary
        }

    def compare_rve_effectiveness(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Experiment design quality and pass rate vs. portfolio averages.

        Returns:
            {
                'pursuit_pass_rate': float,
                'portfolio_pass_rate': float,
                'pursuit_experiment_count': int,
                'avg_evidence_quality': float,
                'summary': str
            }
        """
        # Get pursuit experiments
        experiments = self.db.get_pursuit_experiments(pursuit_id)
        completed = [e for e in experiments if e.get("status") == "COMPLETE"]

        pursuit_passes = sum(1 for e in completed if e.get("verdict") == "PASS")
        pursuit_pass_rate = (pursuit_passes / len(completed) * 100) if completed else 0

        quality_sum = sum(e.get("rigor_score", 0.5) for e in completed)
        pursuit_quality = (quality_sum / len(completed)) if completed else 0.5

        # Get portfolio stats
        pursuits = self.db.get_user_pursuits(user_id, status="active")
        all_pass_rates = []
        all_qualities = []

        for p in pursuits:
            p_id = p["pursuit_id"]
            if p_id == pursuit_id:
                continue

            exps = self.db.get_pursuit_experiments(p_id)
            comp = [e for e in exps if e.get("status") == "COMPLETE"]

            if comp:
                passes = sum(1 for e in comp if e.get("verdict") == "PASS")
                all_pass_rates.append(passes / len(comp) * 100)

                q_sum = sum(e.get("rigor_score", 0.5) for e in comp)
                all_qualities.append(q_sum / len(comp))

        portfolio_pass_rate = statistics.mean(all_pass_rates) if all_pass_rates else 50
        portfolio_quality = statistics.mean(all_qualities) if all_qualities else 0.5

        summary = self._generate_rve_summary(
            pursuit_pass_rate, portfolio_pass_rate, pursuit_quality, portfolio_quality
        )

        return {
            "pursuit_pass_rate": round(pursuit_pass_rate, 1),
            "portfolio_pass_rate": round(portfolio_pass_rate, 1),
            "pursuit_experiment_count": len(experiments),
            "pursuit_completed": len(completed),
            "avg_evidence_quality": round(pursuit_quality, 2),
            "portfolio_avg_quality": round(portfolio_quality, 2),
            "summary": summary
        }

    def generate_comparison_summary(self, pursuit_id: str, user_id: str) -> str:
        """
        Natural language summary for ODICM coaching context.
        Example: "Your velocity is in the top 25% of your active pursuits"
        NEVER: "This pursuit is outperforming/underperforming"
        """
        velocity = self.compare_velocity(pursuit_id, user_id)
        health = self.compare_health_trajectory(pursuit_id, user_id)

        summaries = []

        # Velocity insight
        if velocity["percentile"] >= 75:
            summaries.append(f"Velocity is in the top {100 - velocity['percentile']}% of your pursuits")
        elif velocity["percentile"] <= 25:
            summaries.append(f"Velocity is progressing more slowly than most of your pursuits")
        else:
            summaries.append(f"Velocity is typical for your portfolio")

        # Health insight
        if abs(health["current_delta"]) > 10:
            direction = "above" if health["current_delta"] > 0 else "below"
            summaries.append(f"Health is {abs(health['current_delta']):.0f} points {direction} your portfolio norm for this phase")

        return ". ".join(summaries) + "." if summaries else "Performing in line with portfolio norms."

    def get_historical_benchmarks(self, phase: str, methodology: str) -> Dict:
        """
        Historical performance data for pursuits at this phase with this methodology.

        Returns:
            {
                'avg_phase_duration': float (days),
                'avg_velocity': float,
                'avg_health': float,
                'sample_size': int
            }
        """
        # Query historical completed pursuits
        completed_pursuits = list(self.db.db.pursuits.find({
            "status": {"$in": ["launched", "integrated", "documented"]},
            "methodology": methodology
        }))

        durations = []
        velocities = []
        healths = []

        for p in completed_pursuits:
            # Get phase duration
            transitions = list(self.db.db.phase_transitions.find({
                "pursuit_id": p["pursuit_id"],
                "$or": [{"from_phase": phase}, {"to_phase": phase}]
            }))

            # Calculate phase duration
            phase_start = None
            phase_end = None
            for t in transitions:
                if t.get("to_phase") == phase:
                    phase_start = t.get("transitioned_at")
                elif t.get("from_phase") == phase:
                    phase_end = t.get("transitioned_at")

            if phase_start and phase_end:
                start = datetime.fromisoformat(phase_start.replace('Z', '+00:00'))
                end = datetime.fromisoformat(phase_end.replace('Z', '+00:00'))
                durations.append((end - start).days)

            # Get average velocity during phase
            velocity = self.db.db.velocity_metrics.find_one(
                {"pursuit_id": p["pursuit_id"]},
                sort=[("calculated_at", -1)]
            )
            if velocity:
                velocities.append(velocity.get("elements_per_week", 0))

            # Get average health during phase
            health = self.db.get_latest_health_score(p["pursuit_id"])
            if health:
                healths.append(health.get("health_score", 50))

        return {
            "avg_phase_duration": statistics.mean(durations) if durations else 30,
            "avg_velocity": statistics.mean(velocities) if velocities else 3.0,
            "avg_health": statistics.mean(healths) if healths else 60,
            "sample_size": len(completed_pursuits)
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_pursuit_phase(self, pursuit_id: str) -> str:
        """Get current phase for a pursuit."""
        transition = self.db.db.phase_transitions.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("transitioned_at", -1)]
        )
        if transition:
            return transition.get("to_phase", "VISION")
        return "VISION"

    def _calculate_percentile(self, value: float, sorted_values: List[float]) -> int:
        """Calculate percentile of a value in a sorted list."""
        if not sorted_values:
            return 50
        count_below = sum(1 for v in sorted_values if v < value)
        return int(count_below / len(sorted_values) * 100)

    def _calculate_overall_completeness(self, completeness: Dict) -> float:
        """Calculate overall completeness from component scores."""
        if not completeness:
            return 0
        values = [v for v in completeness.values() if isinstance(v, (int, float))]
        return statistics.mean(values) if values else 0

    def _generate_velocity_summary(self, pursuit: float, portfolio: float,
                                   phase: float, percentile: int,
                                   delta: float, phase_name: str) -> str:
        """Generate INFORMATIONAL velocity summary."""
        if percentile >= 75:
            return f"Velocity ({pursuit:.1f}/week) is in the top quartile for your portfolio"
        elif percentile >= 50:
            return f"Velocity ({pursuit:.1f}/week) is above your portfolio median ({portfolio:.1f}/week)"
        elif percentile >= 25:
            return f"Velocity ({pursuit:.1f}/week) is below your portfolio median"
        else:
            return f"Velocity ({pursuit:.1f}/week) is in the lower quartile - typical for {phase_name} phase in some cases"

    def _generate_trajectory_summary(self, delta: float, trend: str, phase_pct: float) -> str:
        """Generate INFORMATIONAL trajectory summary."""
        if abs(delta) <= 5:
            return f"Health trajectory is in line with your portfolio norm at {phase_pct:.0f}% through the phase"
        elif delta > 0:
            return f"Health is {delta:.0f} points above your typical trajectory at this phase progress"
        else:
            return f"Health is {abs(delta):.0f} points below your typical trajectory at this phase progress"

    def _generate_risk_summary(self, pursuit_risks: int, portfolio_avg: float,
                               high_delta: float, phase_comparison: str) -> str:
        """Generate INFORMATIONAL risk summary."""
        risk_context = f"This pursuit has {pursuit_risks} identified risks"
        if abs(portfolio_avg - pursuit_risks) < 2:
            return f"{risk_context}, which is typical for your portfolio"
        elif pursuit_risks < portfolio_avg:
            return f"{risk_context}, which is fewer than your portfolio average ({portfolio_avg:.1f})"
        else:
            return f"{risk_context}, {phase_comparison}"

    def _generate_completion_summary(self, pursuit: float, phase_avg: float,
                                     delta: float, phase: str) -> str:
        """Generate INFORMATIONAL completion summary."""
        pursuit_pct = pursuit * 100
        phase_pct = phase_avg * 100
        if abs(delta) < 5:
            return f"Element completion ({pursuit_pct:.0f}%) is typical for {phase} phase"
        elif delta > 0:
            return f"Element completion ({pursuit_pct:.0f}%) is {delta:.0f}% above phase average"
        else:
            return f"Element completion ({pursuit_pct:.0f}%) is {abs(delta):.0f}% below phase average"

    def _generate_rve_summary(self, pursuit_rate: float, portfolio_rate: float,
                              pursuit_quality: float, portfolio_quality: float) -> str:
        """Generate INFORMATIONAL RVE summary."""
        if pursuit_rate > portfolio_rate + 10:
            return f"Experiment pass rate ({pursuit_rate:.0f}%) is higher than portfolio average ({portfolio_rate:.0f}%)"
        elif pursuit_rate < portfolio_rate - 10:
            return f"Experiment pass rate ({pursuit_rate:.0f}%) is lower than portfolio average ({portfolio_rate:.0f}%)"
        else:
            return f"Experiment pass rate ({pursuit_rate:.0f}%) is in line with portfolio average"
