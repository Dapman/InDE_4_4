"""
InDE MVP v3.0.3 - Innovation Effectiveness Scorecard
Organizational-level metrics measuring innovation effectiveness over time.

7 Key Metrics:
1. Learning Velocity Trend - Rate of change in time-to-insight
2. Prediction Accuracy - % of predictive guidance matching outcomes
3. Risk Validation ROI - Validated risks to total risks ratio
4. Pattern Application Success - Outcomes when patterns applied vs ignored
5. Fear Resolution Rate - % of fears resolved before completion
6. Retrospective Completeness - Average completion of retrospective prompts
7. Time-to-Decision - Average time from risk identification to RVE verdict

All metrics demonstrate InDE's value and organizational learning capability.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import statistics

from config import EFFECTIVENESS_METRICS


class InnovationEffectivenessScorecard:
    """
    Calculates organizational-level innovation effectiveness metrics.
    Each metric returns a value, trend, and natural language interpretation.
    """

    def __init__(self, db):
        """
        Initialize effectiveness scorecard.

        Args:
            db: Database instance
        """
        self.db = db
        self.config = EFFECTIVENESS_METRICS

    def calculate_full_scorecard(self, user_id: str) -> Dict:
        """
        Calculate all 7 effectiveness metrics.

        Returns:
            {
                'metrics': {
                    'learning_velocity_trend': {'value': float, 'trend': str, 'interpretation': str},
                    'prediction_accuracy': {'value': float, 'trend': str, 'interpretation': str},
                    ...
                },
                'overall_assessment': str,
                'calculated_at': ISO 8601
            }
        """
        metrics = {
            "learning_velocity_trend": self._calculate_learning_velocity_trend(user_id),
            "prediction_accuracy": self._calculate_prediction_accuracy(user_id),
            "risk_validation_roi": self._calculate_risk_validation_roi(user_id),
            "pattern_application_success": self._calculate_pattern_application_success(user_id),
            "fear_resolution_rate": self._calculate_fear_resolution_rate(user_id),
            "retrospective_completeness": self._calculate_retrospective_completeness(user_id),
            "time_to_decision": self._calculate_time_to_decision(user_id)
        }

        # Generate overall assessment
        overall = self._generate_overall_assessment(metrics)

        return {
            "metrics": metrics,
            "overall_assessment": overall,
            "calculated_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

    def _calculate_learning_velocity_trend(self, user_id: str) -> Dict:
        """
        Calculate learning velocity trend across sequential pursuits.

        Measures: Rate of change in time-to-insight (time to reach 50% vision completeness)
        """
        config = self.config["learning_velocity_trend"]

        # Get completed pursuits ordered by creation
        pursuits = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "status": {"$in": ["launched", "integrated", "documented", "pivoted"]}
        }).sort("created_at", 1))

        if len(pursuits) < config["min_pursuits_required"]:
            return self._insufficient_data("learning_velocity_trend",
                                           config["min_pursuits_required"] - len(pursuits),
                                           "pursuits")

        # Calculate time to 50% vision completeness for each pursuit
        times_to_insight = []

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]
            created = pursuit.get("created_at")

            # Get scaffolding history (simplified - use final state)
            scaffolding = self.db.get_scaffolding_state(pursuit_id)
            if scaffolding:
                vision_complete = scaffolding.get("completeness", {}).get("vision", 0)
                if vision_complete >= 0.5:
                    # Estimate time to insight (simplified)
                    # In production, would track actual timeline to 50%
                    terminal_info = pursuit.get("terminal_info", {})
                    if terminal_info:
                        detected = terminal_info.get("detected_at")
                        if detected and created:
                            if isinstance(created, str):
                                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            if isinstance(detected, str):
                                detected = datetime.fromisoformat(detected.replace('Z', '+00:00'))
                            total_days = (detected - created).days
                            # Estimate time to 50% as portion of total
                            times_to_insight.append(total_days * 0.4)

        if len(times_to_insight) < 2:
            return self._insufficient_data("learning_velocity_trend", 2, "completed pursuits")

        # Calculate trend (are we getting faster?)
        first_half = times_to_insight[:len(times_to_insight)//2]
        second_half = times_to_insight[len(times_to_insight)//2:]

        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)

        # Ratio: <1 means faster, >1 means slower
        if avg_first > 0:
            ratio = avg_second / avg_first
            improvement = (1 - ratio) * 100  # positive = faster
        else:
            ratio = 1.0
            improvement = 0

        trend = "improving" if ratio < 0.9 else ("declining" if ratio > 1.1 else "stable")

        interpretation = self._interpret_learning_velocity(ratio, improvement)

        return {
            "value": round(ratio, 2),
            "improvement_percent": round(improvement, 1),
            "trend": trend,
            "interpretation": interpretation,
            "sample_size": len(times_to_insight)
        }

    def _calculate_prediction_accuracy(self, user_id: str) -> Dict:
        """
        Calculate percentage of predictive guidance matching actual outcomes.
        """
        config = self.config["prediction_accuracy"]

        # Get all predictions made
        predictions = list(self.db.db.patterns.find({
            "user_id": user_id,
            "pattern_type": "PREDICTION",
            "verified": True
        }))

        if len(predictions) < config["min_predictions_required"]:
            return self._insufficient_data("prediction_accuracy",
                                           config["min_predictions_required"] - len(predictions),
                                           "verified predictions")

        # Count accurate predictions
        accurate = sum(1 for p in predictions if p.get("outcome_matched", False))
        accuracy = (accurate / len(predictions)) * 100 if predictions else 0

        # Trend from recent vs older
        predictions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        recent = predictions[:len(predictions)//2]
        older = predictions[len(predictions)//2:]

        recent_acc = sum(1 for p in recent if p.get("outcome_matched", False)) / len(recent) * 100 if recent else 0
        older_acc = sum(1 for p in older if p.get("outcome_matched", False)) / len(older) * 100 if older else 0

        trend = "improving" if recent_acc > older_acc + 5 else ("declining" if recent_acc < older_acc - 5 else "stable")

        is_good = accuracy >= config["good_threshold"] * 100
        interpretation = self._interpret_prediction_accuracy(accuracy, is_good)

        return {
            "value": round(accuracy, 1),
            "trend": trend,
            "interpretation": interpretation,
            "sample_size": len(predictions)
        }

    def _calculate_risk_validation_roi(self, user_id: str) -> Dict:
        """
        Calculate ratio of validated risks to total risks, weighted by severity.
        """
        config = self.config["risk_validation_roi"]

        # Get all risk definitions
        risks = list(self.db.db.risk_definitions.find({"user_id": user_id}))

        if len(risks) < config["min_risks_required"]:
            return self._insufficient_data("risk_validation_roi",
                                           config["min_risks_required"] - len(risks),
                                           "identified risks")

        # Weight by severity
        severity_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

        total_weighted = 0
        validated_weighted = 0

        for risk in risks:
            severity = risk.get("severity", "MEDIUM")
            weight = severity_weights.get(severity, 2)
            total_weighted += weight

            # Check if validated (has experiments with results)
            risk_id = risk.get("risk_id")
            if risk_id:
                experiments = self.db.get_risk_experiments(risk_id)
                completed = [e for e in experiments if e.get("status") == "COMPLETE"]
                if completed:
                    validated_weighted += weight

        roi = (validated_weighted / total_weighted) if total_weighted > 0 else 0

        is_good = roi >= config["good_threshold"]
        interpretation = self._interpret_risk_roi(roi * 100, is_good)

        return {
            "value": round(roi * 100, 1),
            "trend": "stable",  # Would need historical data
            "interpretation": interpretation,
            "total_risks": len(risks),
            "validated_risks": sum(1 for r in risks if self._is_risk_validated(r))
        }

    def _calculate_pattern_application_success(self, user_id: str) -> Dict:
        """
        Calculate outcomes of pursuits where IML patterns were applied vs ignored.
        """
        config = self.config["pattern_application_success"]

        # Get pattern applications
        applications = list(self.db.db.pattern_effectiveness.find({"user_id": user_id}))

        if len(applications) < config["min_patterns_required"]:
            return self._insufficient_data("pattern_application_success",
                                           config["min_patterns_required"] - len(applications),
                                           "pattern applications")

        applied_success = sum(1 for a in applications
                             if a.get("was_applied") and a.get("outcome") == "SUCCESS")
        applied_total = sum(1 for a in applications if a.get("was_applied"))

        ignored_success = sum(1 for a in applications
                             if not a.get("was_applied") and a.get("outcome") == "SUCCESS")
        ignored_total = sum(1 for a in applications if not a.get("was_applied"))

        applied_rate = (applied_success / applied_total * 100) if applied_total > 0 else 0
        ignored_rate = (ignored_success / ignored_total * 100) if ignored_total > 0 else 0

        # Success differential
        differential = applied_rate - ignored_rate

        is_good = applied_rate >= config["good_threshold"] * 100
        interpretation = self._interpret_pattern_success(applied_rate, differential)

        return {
            "value": round(applied_rate, 1),
            "applied_success_rate": round(applied_rate, 1),
            "ignored_success_rate": round(ignored_rate, 1),
            "differential": round(differential, 1),
            "trend": "stable",
            "interpretation": interpretation,
            "sample_size": len(applications)
        }

    def _calculate_fear_resolution_rate(self, user_id: str) -> Dict:
        """
        Calculate percentage of fears resolved before pursuit completion.
        """
        config = self.config["fear_resolution_rate"]

        # Get fear resolutions
        resolutions = list(self.db.db.fear_resolutions.find({"user_id": user_id}))

        if len(resolutions) < config["min_fears_required"]:
            return self._insufficient_data("fear_resolution_rate",
                                           config["min_fears_required"] - len(resolutions),
                                           "tracked fears")

        resolved = sum(1 for r in resolutions
                      if r.get("resolution") in ["MITIGATED", "INVALIDATED", "ADDRESSED"])
        total = len(resolutions)

        rate = (resolved / total * 100) if total > 0 else 0

        is_good = rate >= config["good_threshold"] * 100
        interpretation = self._interpret_fear_resolution(rate, is_good)

        return {
            "value": round(rate, 1),
            "resolved_count": resolved,
            "total_fears": total,
            "trend": "stable",
            "interpretation": interpretation
        }

    def _calculate_retrospective_completeness(self, user_id: str) -> Dict:
        """
        Calculate average completion of retrospective prompts.
        """
        config = self.config["retrospective_completeness"]

        # Get retrospectives
        retros = list(self.db.db.retrospectives.find({"user_id": user_id}))

        if len(retros) < config["min_retrospectives_required"]:
            return self._insufficient_data("retrospective_completeness",
                                           config["min_retrospectives_required"] - len(retros),
                                           "retrospectives")

        # Calculate average completeness
        completeness_values = []
        for retro in retros:
            sections = retro.get("sections_completed", {})
            if sections:
                section_count = len(sections)
                completed = sum(1 for v in sections.values() if v)
                completeness_values.append(completed / section_count if section_count > 0 else 0)

        if not completeness_values:
            avg_completeness = 0
        else:
            avg_completeness = statistics.mean(completeness_values) * 100

        is_good = avg_completeness >= config["good_threshold"] * 100
        interpretation = self._interpret_retro_completeness(avg_completeness, is_good)

        return {
            "value": round(avg_completeness, 1),
            "retrospective_count": len(retros),
            "trend": "stable",
            "interpretation": interpretation
        }

    def _calculate_time_to_decision(self, user_id: str) -> Dict:
        """
        Calculate average time from risk identification to RVE verdict.
        """
        config = self.config["time_to_decision"]

        # Get completed experiments
        experiments = list(self.db.db.validation_experiments.find({
            "user_id": user_id,
            "status": "COMPLETE"
        }))

        if len(experiments) < config["min_experiments_required"]:
            return self._insufficient_data("time_to_decision",
                                           config["min_experiments_required"] - len(experiments),
                                           "completed experiments")

        # Calculate time from creation to completion
        durations = []
        for exp in experiments:
            created = exp.get("created_at")
            completed = exp.get("completion_date")

            if created and completed:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if isinstance(completed, str):
                    completed = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                duration = (completed - created).days
                durations.append(duration)

        if not durations:
            return self._insufficient_data("time_to_decision", 1, "experiments with timing")

        avg_days = statistics.mean(durations)

        # Lower is better for this metric
        is_good = avg_days <= config["good_threshold"]
        interpretation = self._interpret_time_to_decision(avg_days, is_good)

        return {
            "value": round(avg_days, 1),
            "unit": "days",
            "experiment_count": len(experiments),
            "trend": "stable",
            "interpretation": interpretation
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _insufficient_data(self, metric: str, needed: int, data_type: str) -> Dict:
        """Return insufficient data response."""
        return {
            "value": None,
            "trend": "insufficient_data",
            "interpretation": f"Not enough data yet (need {needed} more {data_type})",
            "data_needed": needed
        }

    def _is_risk_validated(self, risk: Dict) -> bool:
        """Check if a risk has been validated with experiments."""
        risk_id = risk.get("risk_id")
        if not risk_id:
            return False
        experiments = self.db.get_risk_experiments(risk_id)
        return any(e.get("status") == "COMPLETE" for e in experiments)

    def _interpret_learning_velocity(self, ratio: float, improvement: float) -> str:
        """Generate interpretation for learning velocity."""
        if ratio < 0.8:
            return f"Learning velocity improving - reaching insights {improvement:.0f}% faster than earlier"
        elif ratio > 1.2:
            return f"Learning velocity has slowed - insights taking longer than earlier pursuits"
        else:
            return "Learning velocity is stable across your pursuits"

    def _interpret_prediction_accuracy(self, accuracy: float, is_good: bool) -> str:
        """Generate interpretation for prediction accuracy."""
        if is_good:
            return f"InDE predictions are accurate {accuracy:.0f}% of the time - guidance is well-calibrated"
        elif accuracy >= 50:
            return f"InDE predictions are accurate {accuracy:.0f}% - room for calibration improvement"
        else:
            return f"Prediction accuracy is {accuracy:.0f}% - patterns may not match your context well"

    def _interpret_risk_roi(self, roi_pct: float, is_good: bool) -> str:
        """Generate interpretation for risk validation ROI."""
        if is_good:
            return f"{roi_pct:.0f}% of risks have been validated through experiments - strong risk discipline"
        elif roi_pct >= 40:
            return f"{roi_pct:.0f}% risk validation coverage - consider experiments for more high-severity risks"
        else:
            return f"Only {roi_pct:.0f}% of risks validated - many assumptions remain untested"

    def _interpret_pattern_success(self, applied_rate: float, differential: float) -> str:
        """Generate interpretation for pattern application success."""
        if differential > 10:
            return f"Pursuits applying patterns succeed {differential:.0f}% more often"
        elif differential < -10:
            return "Pattern application hasn't correlated with better outcomes in your context"
        else:
            return "Pattern application shows moderate correlation with success"

    def _interpret_fear_resolution(self, rate: float, is_good: bool) -> str:
        """Generate interpretation for fear resolution rate."""
        if is_good:
            return f"{rate:.0f}% of fears resolved before completion - proactive risk management"
        elif rate >= 50:
            return f"{rate:.0f}% fear resolution - about half of concerns addressed proactively"
        else:
            return f"Only {rate:.0f}% of fears resolved - many concerns carried through to completion"

    def _interpret_retro_completeness(self, rate: float, is_good: bool) -> str:
        """Generate interpretation for retrospective completeness."""
        if is_good:
            return f"Retrospectives {rate:.0f}% complete on average - thorough learning capture"
        elif rate >= 50:
            return f"Retrospectives {rate:.0f}% complete - some learning may be missed"
        else:
            return f"Retrospectives only {rate:.0f}% complete - significant learning capture gap"

    def _interpret_time_to_decision(self, days: float, is_good: bool) -> str:
        """Generate interpretation for time to decision."""
        if is_good:
            return f"Average {days:.0f} days from risk to decision - efficient validation pipeline"
        elif days <= 30:
            return f"Average {days:.0f} days to decision - reasonable but could be faster"
        else:
            return f"Average {days:.0f} days to decision - consider streamlining validation process"

    def _generate_overall_assessment(self, metrics: Dict) -> str:
        """Generate overall effectiveness assessment."""
        good_count = 0
        total_count = 0

        for metric in metrics.values():
            if metric.get("value") is not None:
                total_count += 1
                # Check if metric is "good" based on interpretation
                interp = metric.get("interpretation", "").lower()
                if "strong" in interp or "improving" in interp or "efficient" in interp:
                    good_count += 1

        if total_count == 0:
            return "Not enough data to assess innovation effectiveness yet"

        ratio = good_count / total_count

        if ratio >= 0.7:
            return "Your innovation effectiveness is strong and showing good practices"
        elif ratio >= 0.4:
            return "Innovation effectiveness is developing - some areas show strength, others need attention"
        else:
            return "Innovation effectiveness has room for improvement - focus on completing retrospectives and validating risks"

    def get_metric_summary(self, user_id: str, metric_name: str) -> Dict:
        """Get a single metric with detailed breakdown."""
        method_map = {
            "learning_velocity_trend": self._calculate_learning_velocity_trend,
            "prediction_accuracy": self._calculate_prediction_accuracy,
            "risk_validation_roi": self._calculate_risk_validation_roi,
            "pattern_application_success": self._calculate_pattern_application_success,
            "fear_resolution_rate": self._calculate_fear_resolution_rate,
            "retrospective_completeness": self._calculate_retrospective_completeness,
            "time_to_decision": self._calculate_time_to_decision
        }

        if metric_name not in method_map:
            return {"error": f"Unknown metric: {metric_name}"}

        return method_map[metric_name](user_id)
