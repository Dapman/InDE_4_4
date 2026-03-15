"""
InDE MVP v3.0.3 - SILR Temporal Enrichment
Enhance all SILR report types with temporal intelligence data and visualizations.

8 Visualization Types:
1. Timeline Journey Chart - Horizontal Gantt-style with milestones
2. Velocity Curve - Expected vs actual with confidence band
3. Health Score Trend - Area chart with zone-colored bands
4. Risk Horizon Map - Three-column grouped bar chart
5. RVE Outcomes Donut - PASS/GREY/FAIL distribution
6. Portfolio Health Heatmap - Grid by pursuit/time
7. Prediction Accuracy Gauge - Semi-circular gauge
8. Learning Velocity Sparkline - Compact inline chart

Report Type Integration:
- Terminal State Report: All visualizations
- Living Snapshot Report: Velocity sparkline, health trend, active risk summary
- Portfolio Analytics Report: Portfolio heatmap, velocity distribution, aggregate risk

All visualizations null-safe for pre-v3.0.1 pursuits (no temporal data).
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from ui.analytics_visualizations import (
    create_timeline_journey_chart,
    create_velocity_curve_chart,
    create_health_trend_chart,
    create_risk_horizon_map,
    create_rve_status_chart,
    create_portfolio_heatmap,
    create_prediction_gauge,
    create_learning_sparkline,
    create_health_badge,
    create_velocity_bar_chart,
    create_effectiveness_summary_chart
)

from config import SILR_ENRICHMENT_CONFIG


class SILRTemporalEnrichment:
    """
    Enrichment layer callable from existing SILR report generators.
    Generates matplotlib visualizations and returns them as image bytes
    for embedding in report outputs.
    """

    def __init__(self, db, portfolio_intelligence=None, effectiveness_scorecard=None):
        """
        Initialize SILR temporal enrichment.

        Args:
            db: Database instance
            portfolio_intelligence: Optional PortfolioIntelligenceEngine
            effectiveness_scorecard: Optional InnovationEffectivenessScorecard
        """
        self.db = db
        self.portfolio_intelligence = portfolio_intelligence
        self.effectiveness_scorecard = effectiveness_scorecard
        self.config = SILR_ENRICHMENT_CONFIG

    def enrich_terminal_report(self, pursuit_id: str) -> Dict[str, bytes]:
        """
        Generate all applicable visualizations for a terminal state report.

        Returns:
            dict of {viz_name: image_bytes} for each generated visualization.
            Skips visualizations where source data is insufficient.
        """
        if not self.config.get("enable_temporal_enrichment", True):
            return {}

        visualizations = {}

        # 1. Timeline Journey
        try:
            timeline_data = self._get_timeline_data(pursuit_id)
            if timeline_data:
                visualizations["timeline_journey"] = create_timeline_journey_chart(
                    timeline_data.get("phases", []),
                    timeline_data.get("milestones", [])
                )
        except Exception as e:
            print(f"[SILREnrichment] Timeline journey error: {e}")

        # 2. Velocity Curve
        try:
            velocity_data = self._get_velocity_history(pursuit_id)
            if velocity_data:
                visualizations["velocity_curve"] = create_velocity_curve_chart(
                    velocity_data.get("actual", []),
                    velocity_data.get("expected", [])
                )
        except Exception as e:
            print(f"[SILREnrichment] Velocity curve error: {e}")

        # 3. Health Trend
        try:
            health_history = self.db.get_health_score_history(pursuit_id, limit=30)
            if health_history:
                visualizations["health_trend"] = create_health_trend_chart(health_history)
        except Exception as e:
            print(f"[SILREnrichment] Health trend error: {e}")

        # 4. Risk Horizon Map
        try:
            risk_detection = self.db.get_latest_risk_detection(pursuit_id)
            if risk_detection:
                risks_by_horizon = {
                    "short": len(risk_detection.get("risks_by_horizon", {}).get("short_term", [])),
                    "medium": len(risk_detection.get("risks_by_horizon", {}).get("medium_term", [])),
                    "long": len(risk_detection.get("risks_by_horizon", {}).get("long_term", []))
                }
                visualizations["risk_horizon_map"] = create_risk_horizon_map(risks_by_horizon)
        except Exception as e:
            print(f"[SILREnrichment] Risk horizon map error: {e}")

        # 5. RVE Outcomes Donut
        try:
            experiments = self.db.get_pursuit_experiments(pursuit_id)
            completed = [e for e in experiments if e.get("status") == "COMPLETE"]
            if completed:
                by_zone = {"PASS": 0, "GREY": 0, "FAIL": 0}
                for exp in completed:
                    verdict = exp.get("verdict", "GREY")
                    if verdict in by_zone:
                        by_zone[verdict] += 1
                visualizations["rve_outcomes_donut"] = create_rve_status_chart(by_zone)
        except Exception as e:
            print(f"[SILREnrichment] RVE outcomes error: {e}")

        # 6. Prediction Accuracy Gauge
        try:
            accuracy = self._calculate_prediction_accuracy(pursuit_id)
            if accuracy is not None:
                visualizations["prediction_gauge"] = create_prediction_gauge(accuracy)
        except Exception as e:
            print(f"[SILREnrichment] Prediction gauge error: {e}")

        return visualizations

    def enrich_living_snapshot(self, pursuit_id: str) -> Dict[str, bytes]:
        """
        Generate visualizations for living snapshot report.

        Returns:
            dict of {viz_name: image_bytes}
        """
        if not self.config.get("enable_temporal_enrichment", True):
            return {}

        visualizations = {}

        # 1. Health Badge
        try:
            health = self.db.get_latest_health_score(pursuit_id)
            if health:
                visualizations["health_badge"] = create_health_badge(
                    health.get("health_score", 50),
                    health.get("zone", "HEALTHY")
                )
        except Exception as e:
            print(f"[SILREnrichment] Health badge error: {e}")

        # 2. Health Trend (last 10 points)
        try:
            health_history = self.db.get_health_score_history(pursuit_id, limit=10)
            if health_history:
                visualizations["health_trend"] = create_health_trend_chart(health_history)
        except Exception as e:
            print(f"[SILREnrichment] Health trend error: {e}")

        # 3. Velocity Sparkline
        try:
            velocity_data = self._get_velocity_history(pursuit_id)
            if velocity_data and velocity_data.get("actual"):
                visualizations["velocity_sparkline"] = create_learning_sparkline(
                    velocity_data["actual"][-10:]  # Last 10 points
                )
        except Exception as e:
            print(f"[SILREnrichment] Velocity sparkline error: {e}")

        return visualizations

    def enrich_portfolio_report(self, user_id: str) -> Dict[str, bytes]:
        """
        Generate visualizations for portfolio analytics report.

        Returns:
            dict of {viz_name: image_bytes}
        """
        if not self.config.get("enable_temporal_enrichment", True):
            return {}

        visualizations = {}

        # 1. Portfolio Health Heatmap
        try:
            pursuit_health_data = self._get_portfolio_health_data(user_id)
            if pursuit_health_data:
                visualizations["portfolio_heatmap"] = create_portfolio_heatmap(pursuit_health_data)
        except Exception as e:
            print(f"[SILREnrichment] Portfolio heatmap error: {e}")

        # 2. Velocity Comparison Bar Chart
        try:
            if self.portfolio_intelligence:
                velocity_dist = self.portfolio_intelligence.get_velocity_distribution(user_id)
                if velocity_dist.get("per_pursuit"):
                    visualizations["velocity_comparison"] = create_velocity_bar_chart(
                        velocity_dist["per_pursuit"],
                        velocity_dist.get("mean", 0)
                    )
        except Exception as e:
            print(f"[SILREnrichment] Velocity comparison error: {e}")

        # 3. Aggregate Risk Landscape
        try:
            if self.portfolio_intelligence:
                risk_profile = self.portfolio_intelligence.aggregate_risk_profile(user_id)
                if risk_profile.get("total_risks", 0) > 0:
                    visualizations["aggregate_risk"] = create_risk_horizon_map(
                        risk_profile.get("by_horizon", {})
                    )
        except Exception as e:
            print(f"[SILREnrichment] Aggregate risk error: {e}")

        # 4. Effectiveness Scorecard Summary
        try:
            if self.effectiveness_scorecard:
                scorecard = self.effectiveness_scorecard.calculate_full_scorecard(user_id)
                if scorecard.get("metrics"):
                    visualizations["effectiveness_summary"] = create_effectiveness_summary_chart(
                        scorecard["metrics"]
                    )
        except Exception as e:
            print(f"[SILREnrichment] Effectiveness summary error: {e}")

        # 5. Learning Velocity Sparkline
        try:
            learning_data = self._get_learning_velocity_data(user_id)
            if learning_data:
                visualizations["learning_sparkline"] = create_learning_sparkline(learning_data)
        except Exception as e:
            print(f"[SILREnrichment] Learning sparkline error: {e}")

        return visualizations

    # =========================================================================
    # DATA RETRIEVAL HELPERS
    # =========================================================================

    def _get_timeline_data(self, pursuit_id: str) -> Optional[Dict]:
        """Get timeline data for a pursuit."""
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get phase transitions
        transitions = list(
            self.db.db.phase_transitions.find({"pursuit_id": pursuit_id})
            .sort("transitioned_at", 1)
        )

        if not transitions:
            return None

        # Build phase data
        phases = []
        current_start = 0

        for i, trans in enumerate(transitions):
            phase_name = trans.get("from_phase") if i == 0 else transitions[i-1].get("to_phase")

            # Calculate duration
            trans_time = trans.get("transitioned_at")
            if isinstance(trans_time, str):
                trans_dt = datetime.fromisoformat(trans_time.replace('Z', '+00:00'))
            else:
                trans_dt = trans_time

            pursuit_created = pursuit.get("created_at")
            if isinstance(pursuit_created, str):
                start_dt = datetime.fromisoformat(pursuit_created.replace('Z', '+00:00'))
            else:
                start_dt = pursuit_created

            if i == 0:
                duration = (trans_dt - start_dt).days
            else:
                prev_time = transitions[i-1].get("transitioned_at")
                if isinstance(prev_time, str):
                    prev_dt = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                else:
                    prev_dt = prev_time
                duration = (trans_dt - prev_dt).days

            phases.append({
                "name": phase_name,
                "start_day": current_start,
                "duration_days": max(1, duration)
            })

            current_start += max(1, duration)

        # Add current phase
        if transitions:
            last_phase = transitions[-1].get("to_phase", "VISION")
            last_time = transitions[-1].get("transitioned_at")
            if isinstance(last_time, str):
                last_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
            else:
                last_dt = last_time

            current_duration = (datetime.now(timezone.utc) - last_dt.replace(tzinfo=None)).days
            phases.append({
                "name": last_phase,
                "start_day": current_start,
                "duration_days": max(1, current_duration)
            })

        # Get milestones from temporal events
        milestones = []
        events = list(
            self.db.db.temporal_events.find({
                "pursuit_id": pursuit_id,
                "event_type": {"$in": ["ARTIFACT_GENERATED", "PHASE_TRANSITION", "RVE_EXPERIMENT_COMPLETE"]}
            }).limit(10)
        )

        for event in events:
            event_time = event.get("timestamp")
            if isinstance(event_time, str):
                event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
            else:
                event_dt = event_time

            day = (event_dt - start_dt.replace(tzinfo=None)).days
            milestones.append({
                "day": max(0, day),
                "name": event.get("event_type", "Event")[:15]
            })

        return {
            "phases": phases,
            "milestones": milestones[:5]  # Limit milestones
        }

    def _get_velocity_history(self, pursuit_id: str) -> Optional[Dict]:
        """Get velocity history for a pursuit."""
        velocity_metrics = list(
            self.db.db.velocity_metrics.find({"pursuit_id": pursuit_id})
            .sort("calculated_at", 1)
            .limit(30)
        )

        if not velocity_metrics:
            return None

        actual = [v.get("elements_per_week", 0) for v in velocity_metrics]

        # Calculate expected based on allocation
        allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})
        if allocation:
            expected_per_week = allocation.get("expected_elements_per_week", 3.0)
            expected = [expected_per_week] * len(actual)
        else:
            # Use portfolio average as expected
            expected = None

        return {
            "actual": actual,
            "expected": expected
        }

    def _calculate_prediction_accuracy(self, pursuit_id: str) -> Optional[float]:
        """Calculate prediction accuracy for a pursuit."""
        # Get predictions made for this pursuit
        predictions = list(self.db.db.patterns.find({
            "pursuit_id": pursuit_id,
            "pattern_type": "PREDICTION",
            "verified": True
        }))

        if len(predictions) < 3:
            return None

        accurate = sum(1 for p in predictions if p.get("outcome_matched", False))
        return (accurate / len(predictions)) * 100

    def _get_portfolio_health_data(self, user_id: str) -> List[Dict]:
        """Get health data for all pursuits for heatmap."""
        pursuits = self.db.get_user_pursuits(user_id, status="active")

        result = []
        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            history = self.db.get_health_score_history(pursuit_id, limit=10)

            scores = [h.get("health_score", 50) for h in history]
            scores.reverse()  # Oldest first

            if scores:
                result.append({
                    "name": pursuit.get("title", "Unknown"),
                    "health_history": scores
                })

        return result

    def _get_learning_velocity_data(self, user_id: str) -> List[float]:
        """Get learning velocity trend data."""
        # Get completed pursuits ordered by completion
        pursuits = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "status": {"$in": ["launched", "integrated", "documented", "pivoted"]}
        }).sort("created_at", 1).limit(10))

        # Calculate time to insight for each
        learning_values = []
        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            created = pursuit.get("created_at")
            terminal_info = pursuit.get("terminal_info", {})
            detected = terminal_info.get("detected_at")

            if created and detected:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if isinstance(detected, str):
                    detected = datetime.fromisoformat(detected.replace('Z', '+00:00'))

                days = (detected - created).days
                # Invert so higher = better (faster learning)
                learning_values.append(max(0, 100 - days))

        return learning_values if len(learning_values) >= 3 else []

    def get_enrichment_summary(self, pursuit_id: str = None, user_id: str = None,
                               report_type: str = "terminal") -> Dict:
        """
        Get summary of available enrichments for a report.

        Args:
            pursuit_id: For pursuit-level reports
            user_id: For portfolio-level reports
            report_type: terminal | living_snapshot | portfolio

        Returns:
            {
                'available_visualizations': [str],
                'data_completeness': float,
                'recommendations': [str]
            }
        """
        available = []
        recommendations = []

        if report_type == "terminal" and pursuit_id:
            if self._get_timeline_data(pursuit_id):
                available.append("timeline_journey")
            else:
                recommendations.append("Add phase transitions to enable timeline visualization")

            if self._get_velocity_history(pursuit_id):
                available.append("velocity_curve")
            else:
                recommendations.append("Track velocity metrics for velocity visualization")

            health = self.db.get_health_score_history(pursuit_id, limit=1)
            if health:
                available.append("health_trend")

            detection = self.db.get_latest_risk_detection(pursuit_id)
            if detection:
                available.append("risk_horizon_map")

            experiments = self.db.get_pursuit_experiments(pursuit_id)
            completed = [e for e in experiments if e.get("status") == "COMPLETE"]
            if completed:
                available.append("rve_outcomes_donut")

        elif report_type == "portfolio" and user_id:
            pursuits = self.db.get_user_pursuits(user_id, status="active")
            if len(pursuits) >= 2:
                available.extend(["portfolio_heatmap", "velocity_comparison", "aggregate_risk"])
            else:
                recommendations.append("Create more pursuits for portfolio visualizations")

        data_completeness = len(available) / 6 * 100  # 6 main viz types

        return {
            "available_visualizations": available,
            "data_completeness": round(data_completeness, 1),
            "recommendations": recommendations
        }
