"""
InDE MVP v3.0.3 - Portfolio Intelligence Engine
Synthesizes pursuit-level intelligence into portfolio analytics.

Features:
- Weighted portfolio health calculation (priority × phase weights)
- Velocity distribution with statistical measures
- Aggregate risk profiling across three horizons
- RVE portfolio metrics aggregation
- AI-driven portfolio recommendations (max 3)
- Unified portfolio timeline with conflict detection
- Cross-pursuit pattern detection

Trigger Conditions:
- Session start (if >1 active pursuit)
- Pursuit state change (phase transition, terminal state, new pursuit)
- Explicit 'portfolio' command
- NOT on every message

All timestamps use ISO 8601 format for IKF compatibility.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import statistics
import uuid

from config import (
    PORTFOLIO_INTELLIGENCE_CONFIG, PORTFOLIO_PHASE_WEIGHTS,
    PORTFOLIO_HEALTH_ZONES, PORTFOLIO_PATTERN_TYPES, IKF_PHASES
)


class PortfolioIntelligenceEngine:
    """
    Synthesizes pursuit-level intelligence into portfolio analytics.
    Reads from health_scores, velocity_metrics, risk_detections,
    validation_experiments, and temporal_events collections.
    """

    def __init__(self, db, llm=None, health_monitor=None,
                 velocity_tracker=None, risk_detector=None):
        """
        Initialize portfolio intelligence engine.

        Args:
            db: Database instance
            llm: Optional LLM interface for recommendations
            health_monitor: Optional HealthMonitor instance
            velocity_tracker: Optional VelocityTracker instance
            risk_detector: Optional TemporalRiskDetector instance
        """
        self.db = db
        self.llm = llm
        self.health_monitor = health_monitor
        self.velocity_tracker = velocity_tracker
        self.risk_detector = risk_detector
        self.config = PORTFOLIO_INTELLIGENCE_CONFIG
        self._cache = {}
        self._cache_ttl = self.config.get("cache_ttl_seconds", 300)

    def calculate_portfolio_health(self, user_id: str) -> Dict:
        """
        Weighted average of all active pursuit health scores.

        Formula: Σ(pursuit_health × priority_weight × phase_weight) / Σ(priority_weight × phase_weight)

        Returns:
            {
                'score': int (0-100),
                'zone': str,  # THRIVING | HEALTHY | ATTENTION | AT_RISK | CRITICAL
                'trend': str,  # improving | stable | declining
                'pursuit_count': int,
                'pursuit_breakdown': [{pursuit_id, name, health, weight}],
                'calculated_at': ISO 8601
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        # Edge case: 0 pursuits
        if not pursuits:
            return {
                "score": 0,
                "zone": "N/A",
                "trend": "stable",
                "pursuit_count": 0,
                "pursuit_breakdown": [],
                "message": "No active pursuits",
                "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
            }

        weighted_sum = 0
        weight_total = 0
        breakdown = []
        pursuits_without_health = 0

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]

            # Get health score
            health_data = self.db.get_latest_health_score(pursuit_id)
            if not health_data:
                pursuits_without_health += 1
                continue

            health_score = health_data.get("health_score", 50)

            # Get weights
            priority_weight = pursuit.get("portfolio_priority", 1.0)
            phase = self._get_pursuit_phase(pursuit_id)
            phase_weight = PORTFOLIO_PHASE_WEIGHTS.get(phase, 1.0)

            combined_weight = priority_weight * phase_weight
            weighted_sum += health_score * combined_weight
            weight_total += combined_weight

            breakdown.append({
                "pursuit_id": pursuit_id,
                "name": pursuit.get("title", "Untitled"),
                "health": health_score,
                "zone": health_data.get("zone", "HEALTHY"),
                "priority_weight": priority_weight,
                "phase_weight": phase_weight,
                "combined_weight": combined_weight,
                "phase": phase
            })

        # Edge case: 1 pursuit
        if len(breakdown) == 1:
            single_health = breakdown[0]["health"]
            return {
                "score": single_health,
                "zone": self._get_zone(single_health),
                "trend": "stable",
                "pursuit_count": 1,
                "pursuit_breakdown": breakdown,
                "note": "Single pursuit - portfolio metrics limited",
                "pursuits_without_health_data": pursuits_without_health,
                "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
            }

        # Calculate weighted average
        portfolio_score = int(weighted_sum / weight_total) if weight_total > 0 else 50

        # Calculate trend
        trend = self._calculate_portfolio_trend(user_id)

        result = {
            "score": portfolio_score,
            "zone": self._get_zone(portfolio_score),
            "trend": trend,
            "pursuit_count": len(breakdown),
            "pursuit_breakdown": breakdown,
            "pursuits_without_health_data": pursuits_without_health,
            "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

        # Store snapshot
        self._save_analytics_snapshot(user_id, "portfolio_health", result)

        return result

    def get_velocity_distribution(self, user_id: str) -> Dict:
        """
        Statistical distribution of velocity across all pursuits.

        Returns:
            {
                'mean': float,
                'median': float,
                'std_dev': float,
                'percentiles': {25: float, 50: float, 75: float, 90: float},
                'per_pursuit': [{pursuit_id, name, velocity, phase, percentile}],
                'outliers': [{pursuit_id, name, velocity, direction}]
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        if not pursuits:
            return {
                "mean": 0,
                "median": 0,
                "std_dev": 0,
                "percentiles": {"25": 0, "50": 0, "75": 0, "90": 0},
                "per_pursuit": [],
                "outliers": [],
                "message": "No active pursuits"
            }

        velocities = []
        per_pursuit = []

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            velocity_data = self.db.db.velocity_metrics.find_one(
                {"pursuit_id": pursuit_id},
                sort=[("calculated_at", -1)]
            )

            if velocity_data:
                velocity = velocity_data.get("elements_per_week", 0)
                velocities.append(velocity)
                per_pursuit.append({
                    "pursuit_id": pursuit_id,
                    "name": pursuit.get("title", "Untitled"),
                    "velocity": velocity,
                    "phase": self._get_pursuit_phase(pursuit_id),
                    "status": velocity_data.get("status", "unknown")
                })

        if not velocities:
            return {
                "mean": 0,
                "median": 0,
                "std_dev": 0,
                "percentiles": {"25": 0, "50": 0, "75": 0, "90": 0},
                "per_pursuit": [],
                "outliers": [],
                "message": "No velocity data available"
            }

        # Calculate statistics
        mean = statistics.mean(velocities)
        median = statistics.median(velocities)
        std_dev = statistics.stdev(velocities) if len(velocities) > 1 else 0

        # Calculate percentiles
        sorted_velocities = sorted(velocities)
        n = len(sorted_velocities)
        percentiles = {
            "25": sorted_velocities[int(n * 0.25)] if n > 0 else 0,
            "50": sorted_velocities[int(n * 0.50)] if n > 0 else 0,
            "75": sorted_velocities[int(n * 0.75)] if n > 0 else 0,
            "90": sorted_velocities[int(n * 0.90)] if n > 0 else 0
        }

        # Add percentile ranking to each pursuit
        for item in per_pursuit:
            item["percentile"] = self._calculate_percentile(
                item["velocity"], sorted_velocities
            )

        # Detect outliers (>2 std dev from mean)
        outliers = []
        if std_dev > 0:
            for item in per_pursuit:
                z_score = (item["velocity"] - mean) / std_dev
                if abs(z_score) > 2:
                    outliers.append({
                        "pursuit_id": item["pursuit_id"],
                        "name": item["name"],
                        "velocity": item["velocity"],
                        "direction": "high" if z_score > 0 else "low"
                    })

        return {
            "mean": round(mean, 2),
            "median": round(median, 2),
            "std_dev": round(std_dev, 2),
            "percentiles": percentiles,
            "per_pursuit": per_pursuit,
            "outliers": outliers
        }

    def aggregate_risk_profile(self, user_id: str) -> Dict:
        """
        Consolidated risk landscape across all active pursuits by horizon.

        Returns:
            {
                'total_risks': int,
                'by_severity': {'high': int, 'medium': int, 'low': int},
                'by_horizon': {'short': int, 'medium': int, 'long': int},
                'top_risks': [{risk_id, pursuit_name, description, severity, horizon}],
                'mitigation_coverage': float,  # % with active RVE experiments
                'unaddressed_high_severity': int
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        if not pursuits:
            return {
                "total_risks": 0,
                "by_severity": {"high": 0, "medium": 0, "low": 0},
                "by_horizon": {"short": 0, "medium": 0, "long": 0},
                "top_risks": [],
                "mitigation_coverage": 0,
                "unaddressed_high_severity": 0,
                "message": "No active pursuits"
            }

        all_risks = []
        by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        by_horizon = {"short_term": 0, "medium_term": 0, "long_term": 0}

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            detection = self.db.get_latest_risk_detection(pursuit_id)

            if not detection:
                continue

            # Aggregate by horizon
            risks_by_horizon = detection.get("risks_by_horizon", {})
            for horizon in ["short_term", "medium_term", "long_term"]:
                horizon_risks = risks_by_horizon.get(horizon, [])
                by_horizon[horizon] += len(horizon_risks)

                for risk in horizon_risks:
                    risk_copy = dict(risk)
                    risk_copy["pursuit_id"] = pursuit_id
                    risk_copy["pursuit_name"] = pursuit.get("title", "Untitled")
                    risk_copy["horizon"] = horizon
                    all_risks.append(risk_copy)

                    severity = risk.get("severity", "MEDIUM")
                    if severity in by_severity:
                        by_severity[severity] += 1

        # Sort by severity to get top risks
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_risks.sort(key=lambda r: severity_order.get(r.get("severity", "LOW"), 4))
        top_risks = all_risks[:5]

        # Calculate mitigation coverage
        total_risks = len(all_risks)
        risks_with_experiments = 0
        unaddressed_high = 0

        for risk in all_risks:
            risk_id = risk.get("risk_id")
            if risk_id:
                experiments = self.db.get_risk_experiments(risk_id)
                if experiments:
                    risks_with_experiments += 1
                elif risk.get("severity") in ["HIGH", "CRITICAL"]:
                    unaddressed_high += 1

        mitigation_coverage = (risks_with_experiments / total_risks * 100) if total_risks > 0 else 0

        return {
            "total_risks": total_risks,
            "by_severity": {
                "high": by_severity["HIGH"],
                "medium": by_severity["MEDIUM"],
                "low": by_severity["LOW"]
            },
            "by_horizon": {
                "short": by_horizon["short_term"],
                "medium": by_horizon["medium_term"],
                "long": by_horizon["long_term"]
            },
            "top_risks": top_risks,
            "mitigation_coverage": round(mitigation_coverage, 1),
            "unaddressed_high_severity": unaddressed_high
        }

    def calculate_rve_portfolio_metrics(self, user_id: str) -> Dict:
        """
        RVE experiment outcomes aggregated across portfolio.

        Returns:
            {
                'total_experiments': int,
                'by_zone': {'PASS': int, 'GREY': int, 'FAIL': int},
                'pass_rate': float,
                'override_count': int,
                'override_rate': float,
                'avg_evidence_quality': float,
                'active_experiments': int,
                'by_pursuit': [{pursuit_id, name, experiment_count, pass_rate}]
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        if not pursuits:
            return {
                "total_experiments": 0,
                "by_zone": {"PASS": 0, "GREY": 0, "FAIL": 0},
                "pass_rate": 0,
                "override_count": 0,
                "override_rate": 0,
                "avg_evidence_quality": 0,
                "active_experiments": 0,
                "by_pursuit": [],
                "message": "No active pursuits"
            }

        total_experiments = 0
        by_zone = {"PASS": 0, "GREY": 0, "FAIL": 0}
        override_count = 0
        active_experiments = 0
        evidence_quality_sum = 0
        evidence_count = 0
        by_pursuit = []

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            experiments = self.db.get_pursuit_experiments(pursuit_id)

            pursuit_total = len(experiments)
            pursuit_pass = 0

            for exp in experiments:
                total_experiments += 1
                status = exp.get("status", "DESIGNED")

                if status in ["DESIGNED", "IN_PROGRESS"]:
                    active_experiments += 1
                elif status == "COMPLETE":
                    zone = exp.get("verdict", "GREY")
                    if zone in by_zone:
                        by_zone[zone] += 1
                    if zone == "PASS":
                        pursuit_pass += 1

                    # Check for override
                    if exp.get("innovator_decision") == "OVERRIDE_PROCEED":
                        override_count += 1

                    # Evidence quality
                    quality = exp.get("rigor_score")
                    if quality is not None:
                        evidence_quality_sum += quality
                        evidence_count += 1

            by_pursuit.append({
                "pursuit_id": pursuit_id,
                "name": pursuit.get("title", "Untitled"),
                "experiment_count": pursuit_total,
                "pass_rate": (pursuit_pass / pursuit_total * 100) if pursuit_total > 0 else 0
            })

        completed = by_zone["PASS"] + by_zone["GREY"] + by_zone["FAIL"]
        pass_rate = (by_zone["PASS"] / completed * 100) if completed > 0 else 0
        override_rate = (override_count / completed * 100) if completed > 0 else 0
        avg_quality = (evidence_quality_sum / evidence_count) if evidence_count > 0 else 0

        return {
            "total_experiments": total_experiments,
            "by_zone": by_zone,
            "pass_rate": round(pass_rate, 1),
            "override_count": override_count,
            "override_rate": round(override_rate, 1),
            "avg_evidence_quality": round(avg_quality, 2),
            "active_experiments": active_experiments,
            "by_pursuit": by_pursuit
        }

    def generate_portfolio_recommendations(self, user_id: str) -> List[Dict]:
        """
        AI-driven recommendations based on portfolio state.
        Uses LLM with portfolio context to generate max 3 recommendations.

        Returns:
            list of {
                'priority': int (1-3),
                'text': str,
                'rationale': str,
                'suggested_action': str,
                'related_pursuits': [pursuit_id]
            }
        """
        # Gather portfolio context
        health = self.calculate_portfolio_health(user_id)
        velocity = self.get_velocity_distribution(user_id)
        risks = self.aggregate_risk_profile(user_id)
        rve = self.calculate_rve_portfolio_metrics(user_id)

        recommendations = []

        # Rule-based recommendations (fallback if no LLM)
        # Recommendation 1: Critical health
        at_risk_pursuits = [
            p for p in health.get("pursuit_breakdown", [])
            if p.get("zone") in ["AT_RISK", "CRITICAL"]
        ]
        if at_risk_pursuits:
            recommendations.append({
                "priority": 1,
                "text": f"{len(at_risk_pursuits)} pursuit(s) need attention",
                "rationale": "Pursuits in AT_RISK or CRITICAL zone require immediate focus",
                "suggested_action": "Review blockers and consider scope adjustments",
                "related_pursuits": [p["pursuit_id"] for p in at_risk_pursuits]
            })

        # Recommendation 2: Unaddressed high-severity risks
        if risks.get("unaddressed_high_severity", 0) > 0:
            recommendations.append({
                "priority": 2,
                "text": f"{risks['unaddressed_high_severity']} high-severity risks without experiments",
                "rationale": "High-severity risks should have validation experiments",
                "suggested_action": "Design experiments for unvalidated high-severity risks",
                "related_pursuits": [r.get("pursuit_id") for r in risks.get("top_risks", [])]
            })

        # Recommendation 3: Low velocity outliers
        low_velocity = [
            o for o in velocity.get("outliers", [])
            if o.get("direction") == "low"
        ]
        if low_velocity:
            recommendations.append({
                "priority": 3,
                "text": f"{len(low_velocity)} pursuit(s) with unusually low velocity",
                "rationale": "These pursuits are progressing slower than portfolio average",
                "suggested_action": "Investigate blockers or reallocate resources",
                "related_pursuits": [o["pursuit_id"] for o in low_velocity]
            })

        # Limit to max 3
        return recommendations[:self.config.get("max_recommendations", 3)]

    def get_portfolio_timeline(self, user_id: str) -> Dict:
        """
        Unified timeline of all pursuits with overlapping phase visualization.

        Returns:
            {
                'pursuits': [{pursuit_id, name, start, projected_end, phases: [{name, start, end}]}],
                'conflicts': [{type, pursuit_ids, description}],
                'total_span_days': int
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        if not pursuits:
            return {
                "pursuits": [],
                "conflicts": [],
                "total_span_days": 0,
                "message": "No active pursuits"
            }

        timeline_data = []
        all_starts = []
        all_ends = []

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            created = pursuit.get("created_at")
            if isinstance(created, str):
                start = datetime.fromisoformat(created.replace('Z', '+00:00'))
            else:
                start = created
            # Ensure timezone-aware
            if isinstance(start, datetime) and start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            all_starts.append(start)

            # Get time allocation for projected end
            allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})
            if allocation:
                duration_days = allocation.get("total_duration_days", 90)
                projected_end = start + timedelta(days=duration_days)
            else:
                projected_end = start + timedelta(days=90)  # Default 90 days

            all_ends.append(projected_end)

            # Get phase transitions
            transitions = list(
                self.db.db.phase_transitions.find({"pursuit_id": pursuit_id})
                .sort("transitioned_at", 1)
            )

            phases = []
            current_phase = "VISION"
            phase_start = start

            for transition in transitions:
                trans_time = transition.get("transitioned_at")
                if isinstance(trans_time, str):
                    trans_time = datetime.fromisoformat(trans_time.replace('Z', '+00:00'))
                # Ensure timezone-aware
                if isinstance(trans_time, datetime) and trans_time.tzinfo is None:
                    trans_time = trans_time.replace(tzinfo=timezone.utc)

                phases.append({
                    "name": current_phase,
                    "start": phase_start.isoformat() + 'Z',
                    "end": trans_time.isoformat() + 'Z'
                })

                current_phase = transition.get("to_phase", current_phase)
                phase_start = trans_time

            # Add current phase
            phases.append({
                "name": current_phase,
                "start": phase_start.isoformat() + 'Z',
                "end": None  # Ongoing
            })

            timeline_data.append({
                "pursuit_id": pursuit_id,
                "name": pursuit.get("title", "Untitled"),
                "start": start.isoformat() + 'Z',
                "projected_end": projected_end.isoformat() + 'Z',
                "phases": phases
            })

        # Calculate total span
        if all_starts and all_ends:
            earliest = min(all_starts)
            latest = max(all_ends)
            total_span = (latest - earliest).days
        else:
            total_span = 0

        # Detect conflicts (overlapping DEPLOY phases)
        conflicts = self._detect_timeline_conflicts(timeline_data)

        return {
            "pursuits": timeline_data,
            "conflicts": conflicts,
            "total_span_days": total_span
        }

    def detect_portfolio_patterns(self, user_id: str) -> List[Dict]:
        """
        Cross-pursuit pattern analysis: shared risks, common blockers, synergies.

        Returns:
            list of {
                'pattern_type': str,  # SHARED_RISK | COMMON_BLOCKER | SYNERGY | VELOCITY_CORRELATION
                'pursuit_ids': [str],
                'description': str,
                'confidence': float,
                'actionable_insight': str
            }
        """
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        if len(pursuits) < 2:
            return []

        patterns = []

        # Pattern 1: Shared risks
        shared_risks = self._detect_shared_risks(pursuits)
        patterns.extend(shared_risks)

        # Pattern 2: Common blockers (similar low-velocity patterns)
        common_blockers = self._detect_common_blockers(pursuits)
        patterns.extend(common_blockers)

        # Pattern 3: Synergies (overlapping domains or customer segments)
        synergies = self._detect_synergies(pursuits)
        patterns.extend(synergies)

        # Pattern 4: Velocity correlations
        velocity_patterns = self._detect_velocity_correlations(pursuits)
        patterns.extend(velocity_patterns)

        return patterns

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

    def _get_zone(self, score: int) -> str:
        """Get health zone from score."""
        for zone, config in PORTFOLIO_HEALTH_ZONES.items():
            if config["min"] <= score <= config["max"]:
                return zone
        return "HEALTHY"

    def _calculate_portfolio_trend(self, user_id: str) -> str:
        """Calculate portfolio health trend from historical snapshots."""
        history = self.db.get_portfolio_analytics_history(user_id, limit=5)
        if len(history) < 2:
            return "stable"

        recent = [h.get("portfolio_health", {}).get("score", 50) for h in history[:3]]
        older = [h.get("portfolio_health", {}).get("score", 50) for h in history[2:5]]

        if not recent or not older:
            return "stable"

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if recent_avg > older_avg + 5:
            return "improving"
        elif recent_avg < older_avg - 5:
            return "declining"
        return "stable"

    def _calculate_percentile(self, value: float, sorted_values: List[float]) -> int:
        """Calculate percentile of a value in a sorted list."""
        if not sorted_values:
            return 50
        count_below = sum(1 for v in sorted_values if v < value)
        return int(count_below / len(sorted_values) * 100)

    def _save_analytics_snapshot(self, user_id: str, metric_type: str, data: Dict):
        """Save analytics snapshot for trend tracking."""
        snapshot = {
            "user_id": user_id,
            "metric_type": metric_type,
            "data": data
        }
        self.db.save_portfolio_analytics(snapshot)

    def _detect_timeline_conflicts(self, timeline_data: List[Dict]) -> List[Dict]:
        """Detect overlapping resource demands in timeline."""
        conflicts = []

        # Check for multiple DEPLOY phases at the same time
        deploy_ranges = []
        for pursuit in timeline_data:
            for phase in pursuit.get("phases", []):
                if phase["name"] == "DEPLOY":
                    deploy_ranges.append({
                        "pursuit_id": pursuit["pursuit_id"],
                        "name": pursuit["name"],
                        "start": phase["start"],
                        "end": phase["end"]
                    })

        # Check for overlaps
        for i, r1 in enumerate(deploy_ranges):
            for r2 in deploy_ranges[i+1:]:
                # Simple overlap check (both have no end = ongoing)
                if r1["end"] is None and r2["end"] is None:
                    conflicts.append({
                        "type": "CONCURRENT_DEPLOY",
                        "pursuit_ids": [r1["pursuit_id"], r2["pursuit_id"]],
                        "description": f"{r1['name']} and {r2['name']} are both in DEPLOY phase"
                    })

        return conflicts

    def _detect_shared_risks(self, pursuits: List[Dict]) -> List[Dict]:
        """Detect risks shared across multiple pursuits."""
        patterns = []

        # Get risk descriptions from all pursuits
        risk_texts = {}
        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            detection = self.db.get_latest_risk_detection(pursuit_id)
            if detection:
                for horizon in ["short_term", "medium_term", "long_term"]:
                    for risk in detection.get("risks_by_horizon", {}).get(horizon, []):
                        desc = risk.get("description", "").lower()
                        if desc:
                            if desc not in risk_texts:
                                risk_texts[desc] = []
                            risk_texts[desc].append(pursuit_id)

        # Find risks in multiple pursuits
        for desc, pursuit_ids in risk_texts.items():
            if len(set(pursuit_ids)) > 1:
                patterns.append({
                    "pattern_type": "SHARED_RISK",
                    "pursuit_ids": list(set(pursuit_ids)),
                    "description": f"Risk '{desc[:50]}...' appears in {len(set(pursuit_ids))} pursuits",
                    "confidence": 0.85,
                    "actionable_insight": "Consider addressing this risk portfolio-wide"
                })

        return patterns[:3]  # Limit

    def _detect_common_blockers(self, pursuits: List[Dict]) -> List[Dict]:
        """Detect common blockers across pursuits."""
        patterns = []

        # Check for pursuits with similar low health patterns
        low_health_pursuits = []
        for pursuit in pursuits:
            health = self.db.get_latest_health_score(pursuit["pursuit_id"])
            if health and health.get("zone") in ["AT_RISK", "CRITICAL"]:
                low_health_pursuits.append({
                    "pursuit_id": pursuit["pursuit_id"],
                    "name": pursuit.get("title"),
                    "zone": health.get("zone")
                })

        if len(low_health_pursuits) >= 2:
            patterns.append({
                "pattern_type": "COMMON_BLOCKER",
                "pursuit_ids": [p["pursuit_id"] for p in low_health_pursuits],
                "description": f"{len(low_health_pursuits)} pursuits experiencing similar health challenges",
                "confidence": 0.70,
                "actionable_insight": "Investigate if there's a shared organizational blocker"
            })

        return patterns

    def _detect_synergies(self, pursuits: List[Dict]) -> List[Dict]:
        """Detect synergies between pursuits."""
        patterns = []

        # Check for pursuits in same domain
        domains = {}
        for pursuit in pursuits:
            domain = pursuit.get("problem_context", {}).get("domain", "")
            if domain:
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(pursuit["pursuit_id"])

        for domain, pursuit_ids in domains.items():
            if len(pursuit_ids) > 1:
                patterns.append({
                    "pattern_type": "SYNERGY",
                    "pursuit_ids": pursuit_ids,
                    "description": f"{len(pursuit_ids)} pursuits in '{domain}' domain - potential synergies",
                    "confidence": 0.65,
                    "actionable_insight": "Look for shared learnings and resource synergies"
                })

        return patterns[:2]  # Limit

    def _detect_velocity_correlations(self, pursuits: List[Dict]) -> List[Dict]:
        """Detect velocity correlations between pursuits."""
        patterns = []

        # Check if multiple pursuits have declining velocity
        declining = []
        for pursuit in pursuits:
            velocity = self.db.db.velocity_metrics.find_one(
                {"pursuit_id": pursuit["pursuit_id"]},
                sort=[("calculated_at", -1)]
            )
            if velocity and velocity.get("trend") == "declining":
                declining.append(pursuit["pursuit_id"])

        if len(declining) >= 2:
            patterns.append({
                "pattern_type": "VELOCITY_CORRELATION",
                "pursuit_ids": declining,
                "description": f"{len(declining)} pursuits with declining velocity",
                "confidence": 0.75,
                "actionable_insight": "Portfolio-wide velocity decline - check for resource or focus issues"
            })

        return patterns

    def get_full_portfolio_snapshot(self, user_id: str) -> Dict:
        """Get complete portfolio analytics snapshot."""
        return {
            "portfolio_health": self.calculate_portfolio_health(user_id),
            "velocity_distribution": self.get_velocity_distribution(user_id),
            "risk_profile": self.aggregate_risk_profile(user_id),
            "rve_metrics": self.calculate_rve_portfolio_metrics(user_id),
            "recommendations": self.generate_portfolio_recommendations(user_id),
            "timeline": self.get_portfolio_timeline(user_id),
            "patterns": self.detect_portfolio_patterns(user_id),
            "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }
