"""
InDE MVP v3.0.2 - Temporal Risk Detector
Three-horizon risk detection for pursuits.

Features:
- Short-term risk detection (0-14 days)
- Medium-term risk detection (14-60 days)
- Long-term risk detection (60+ days)
- Risk aggregation and prioritization
- Integration with health monitoring

Risk Horizons:
- SHORT_TERM: Immediate risks requiring attention now
- MEDIUM_TERM: Emerging risks to monitor
- LONG_TERM: Systemic risks affecting pursuit viability
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from config import (
    RISK_DETECTION_CONFIG, RISK_SEVERITY, OVERALL_RISK_LEVELS
)


class TemporalRiskDetector:
    """
    Detect risks across three time horizons.

    Analyzes pursuit state, velocity, health, and patterns
    to identify risks at different time scales.
    """

    def __init__(self, db, velocity_tracker=None, phase_manager=None,
                 health_monitor=None):
        """
        Initialize temporal risk detector.

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
        self.config = RISK_DETECTION_CONFIG
        self._last_detection = {}

    def detect_risks(self, pursuit_id: str) -> Dict:
        """
        Perform comprehensive risk detection across all horizons.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with risks by horizon and overall assessment
        """
        if not self.config.get("enable_risk_detection", True):
            return {"detection_disabled": True}

        # Get context
        context = self._get_detection_context(pursuit_id)

        # Detect risks in each horizon
        short_term = self._detect_short_term_risks(context)
        medium_term = self._detect_medium_term_risks(context)
        long_term = self._detect_long_term_risks(context)

        # Calculate overall risk level
        all_risks = short_term + medium_term + long_term
        overall_level = self._calculate_overall_risk_level(all_risks)

        # Build result
        result = {
            "pursuit_id": pursuit_id,
            "detected_at": datetime.now(timezone.utc).isoformat() + 'Z',
            "overall_risk_level": overall_level,
            "risk_count": len(all_risks),
            "horizons": {
                "short_term": {
                    "horizon_days": self.config.get("short_term_horizon_days", 14),
                    "risks": short_term,
                    "count": len(short_term)
                },
                "medium_term": {
                    "horizon_days": self.config.get("medium_term_horizon_days", 60),
                    "risks": medium_term,
                    "count": len(medium_term)
                },
                "long_term": {
                    "horizon_days": "60+",
                    "risks": long_term,
                    "count": len(long_term)
                }
            },
            "top_risks": self._get_top_risks(all_risks, limit=3),
            "recommendations": self._generate_recommendations(all_risks, overall_level)
        }

        # Save to database
        self.db.save_risk_detection(result)

        # Track last detection
        self._last_detection[pursuit_id] = datetime.now(timezone.utc)

        return result

    def _get_detection_context(self, pursuit_id: str) -> Dict:
        """Get context for risk detection."""
        pursuit = self.db.get_pursuit(pursuit_id)
        scaffolding = self.db.get_scaffolding_state(pursuit_id)
        allocation = self.db.get_time_allocation(pursuit_id)

        context = {
            "pursuit_id": pursuit_id,
            "pursuit": pursuit,
            "scaffolding": scaffolding,
            "allocation": allocation,
            "current_phase": "VISION",
            "completeness": scaffolding.get("completeness", {}) if scaffolding else {},
            "velocity_status": "unknown",
            "elements_per_week": 0,
            "days_remaining": 0,
            "health_zone": "HEALTHY",
            "health_score": 50,
            "rve_status": self.db.get_pursuit_rve_status(pursuit_id)
        }

        # Phase info
        if self.phase_manager:
            context["current_phase"] = self.phase_manager.get_current_phase(pursuit_id)
            phase_status = self.phase_manager.get_phase_status(
                pursuit_id, context["current_phase"]
            )
            context["phase_days_used"] = phase_status.get("days_used", 0)
            context["phase_days_allocated"] = phase_status.get("days_allocated", 30)

        # Velocity info
        if self.velocity_tracker:
            velocity = self.velocity_tracker.calculate_velocity(pursuit_id)
            context["velocity_status"] = velocity.get("status", "unknown")
            context["elements_per_week"] = velocity.get("elements_per_week", 0)
            context["velocity_trend"] = velocity.get("trend", "stable")

        # Health info
        if self.health_monitor:
            health = self.health_monitor.calculate_health(pursuit_id)
            context["health_zone"] = health.get("zone", "HEALTHY")
            context["health_score"] = health.get("health_score", 50)

        # Timeline info
        if allocation:
            target_str = allocation.get("target_completion")
            if target_str:
                target = datetime.fromisoformat(
                    target_str.replace('Z', '+00:00') if 'Z' in target_str else target_str
                )
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                context["days_remaining"] = (target - datetime.now(timezone.utc)).days

        return context

    def _detect_short_term_risks(self, context: Dict) -> List[Dict]:
        """Detect risks in the short-term horizon (0-14 days)."""
        risks = []
        horizon = self.config.get("short_term_horizon_days", 14)

        # Risk 1: Velocity crisis
        if context["velocity_status"] == "significantly_behind":
            risks.append({
                "id": "velocity_crisis",
                "horizon": "short_term",
                "severity": "HIGH",
                "title": "Velocity Crisis",
                "description": "Progress has significantly slowed. Risk of stalling.",
                "impact": "May miss near-term milestones",
                "mitigation": "Identify and address blockers immediately"
            })

        # Risk 2: Health in critical zone
        if context["health_zone"] == "CRITICAL":
            risks.append({
                "id": "health_critical",
                "horizon": "short_term",
                "severity": "CRITICAL",
                "title": "Health Critical",
                "description": "Pursuit health has dropped to critical levels.",
                "impact": "High risk of pursuit failure without intervention",
                "mitigation": "Review blockers and consider scope adjustment"
            })

        # Risk 3: Phase time running out
        phase_remaining = context.get("phase_days_allocated", 30) - context.get("phase_days_used", 0)
        if phase_remaining <= 7 and phase_remaining > 0:
            completeness = context["completeness"].get(
                context["current_phase"].lower().replace("de_risk", "fears"), 0
            )
            if completeness < 0.7:
                risks.append({
                    "id": "phase_deadline",
                    "horizon": "short_term",
                    "severity": "MEDIUM",
                    "title": "Phase Deadline Approaching",
                    "description": f"Only {phase_remaining} days left in {context['current_phase']} phase.",
                    "impact": "May need to extend phase or proceed with incomplete work",
                    "mitigation": "Focus on critical elements for phase completion"
                })

        # Risk 4: No activity risk
        history = list(self.db.db.conversation_history.find(
            {"pursuit_id": context["pursuit_id"]}
        ).sort("timestamp", -1).limit(1))

        if history:
            last_activity = history[0].get("timestamp")
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(
                    last_activity.replace('Z', '+00:00') if 'Z' in last_activity else last_activity
                )
            if isinstance(last_activity, datetime) and last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            days_inactive = (datetime.now(timezone.utc) - last_activity).days

            if days_inactive >= 7:
                risks.append({
                    "id": "inactivity",
                    "horizon": "short_term",
                    "severity": "MEDIUM",
                    "title": "Extended Inactivity",
                    "description": f"No activity in {days_inactive} days.",
                    "impact": "Risk of pursuit abandonment",
                    "mitigation": "Re-engage with pursuit to maintain momentum"
                })

        return risks

    def _detect_medium_term_risks(self, context: Dict) -> List[Dict]:
        """Detect risks in the medium-term horizon (14-60 days)."""
        risks = []

        # Risk 1: Timeline at risk
        days_remaining = context.get("days_remaining", 180)
        if 14 < days_remaining <= 60:
            # Check if completion is on track
            avg_completeness = (
                context["completeness"].get("vision", 0) +
                context["completeness"].get("fears", 0) +
                context["completeness"].get("hypothesis", 0)
            ) / 3

            expected_progress = 1 - (days_remaining / 180)  # Rough estimate
            if avg_completeness < expected_progress - 0.2:
                risks.append({
                    "id": "timeline_risk",
                    "horizon": "medium_term",
                    "severity": "MEDIUM",
                    "title": "Timeline at Risk",
                    "description": "Progress is behind schedule relative to target completion.",
                    "impact": f"May not complete by target date ({days_remaining} days remaining)",
                    "mitigation": "Consider scope reduction or timeline extension"
                })

        # Risk 2: Unvalidated high-priority risks
        rve_status = context.get("rve_status", {})
        if rve_status:
            total_risks = rve_status.get("total_risks_identified", 0)
            validated = rve_status.get("risks_validated", 0)

            if total_risks > 0 and validated / total_risks < 0.5:
                risks.append({
                    "id": "unvalidated_risks",
                    "horizon": "medium_term",
                    "severity": "MEDIUM",
                    "title": "Unvalidated Risks",
                    "description": f"Only {validated}/{total_risks} identified risks have been validated.",
                    "impact": "Unknown risks may impact later phases",
                    "mitigation": "Design experiments to validate critical risks"
                })

        # Risk 3: Declining health trend
        if self.health_monitor:
            trend = self.health_monitor.get_health_trend(context["pursuit_id"])
            if trend.get("trend") == "declining" and trend.get("change", 0) < -15:
                risks.append({
                    "id": "health_decline",
                    "horizon": "medium_term",
                    "severity": "MEDIUM",
                    "title": "Declining Health Trend",
                    "description": f"Health score has dropped {abs(trend['change']):.0f} points recently.",
                    "impact": "May worsen without intervention",
                    "mitigation": "Review and address weakest health components"
                })

        return risks

    def _detect_long_term_risks(self, context: Dict) -> List[Dict]:
        """Detect risks in the long-term horizon (60+ days)."""
        risks = []

        # Risk 1: Systemic red zone risks
        rve_status = context.get("rve_status", {})
        if rve_status:
            red_count = rve_status.get("risks_red", 0)
            unmitigated_proceeding = rve_status.get("risks_unmitigated_proceeding", 0)

            if red_count > 0:
                risks.append({
                    "id": "red_zone_systemic",
                    "horizon": "long_term",
                    "severity": "HIGH",
                    "title": "Unmitigated Critical Risks",
                    "description": f"{red_count} risk(s) remain in red zone.",
                    "impact": "Pursuit viability may be compromised",
                    "mitigation": "Address or accept with explicit justification"
                })

            if unmitigated_proceeding > 0:
                risks.append({
                    "id": "proceeding_despite_red",
                    "horizon": "long_term",
                    "severity": "MEDIUM",
                    "title": "Proceeding Despite Red Zones",
                    "description": f"Proceeding with {unmitigated_proceeding} unmitigated risk(s).",
                    "impact": "Explicit risk acceptance - monitor closely",
                    "mitigation": "Ensure monitoring plans and stop-loss criteria are active"
                })

        # Risk 2: Phase imbalance
        if context.get("allocation"):
            allocation = context["allocation"]
            current_phase = context["current_phase"]

            # Check if a phase consumed more than its allocation
            for pa in allocation.get("phase_allocations", []):
                if pa.get("status") == "COMPLETE":
                    actual_days = pa.get("days_used", 0)
                    allocated_days = pa.get("days_allocated", 30)
                    if actual_days > allocated_days * 1.5:
                        risks.append({
                            "id": "phase_overrun",
                            "horizon": "long_term",
                            "severity": "LOW",
                            "title": "Phase Overrun Pattern",
                            "description": f"{pa.get('phase')} phase exceeded allocation by {((actual_days / allocated_days) - 1) * 100:.0f}%.",
                            "impact": "May compress remaining phases",
                            "mitigation": "Review timeline allocation for remaining phases"
                        })
                        break

        # Risk 3: Scope creep indicators
        scaffolding = context.get("scaffolding", {})
        if scaffolding:
            # Check if elements keep getting added late
            important_elements = scaffolding.get("important_elements", {})
            if len(important_elements) > 15:
                risks.append({
                    "id": "scope_creep",
                    "horizon": "long_term",
                    "severity": "LOW",
                    "title": "Potential Scope Creep",
                    "description": f"High number of tracked elements ({len(important_elements)}).",
                    "impact": "May indicate expanding scope",
                    "mitigation": "Review and prioritize most critical elements"
                })

        return risks

    def _calculate_overall_risk_level(self, all_risks: List[Dict]) -> str:
        """Calculate overall risk level from individual risks."""
        if not all_risks:
            return "LOW"

        # Count by severity
        critical = sum(1 for r in all_risks if r["severity"] == "CRITICAL")
        high = sum(1 for r in all_risks if r["severity"] == "HIGH")
        medium = sum(1 for r in all_risks if r["severity"] == "MEDIUM")

        if critical > 0:
            return "CRITICAL"
        elif high >= 2 or (high >= 1 and medium >= 2):
            return "HIGH"
        elif high >= 1 or medium >= 2:
            return "MODERATE"
        else:
            return "LOW"

    def _get_top_risks(self, all_risks: List[Dict], limit: int = 3) -> List[Dict]:
        """Get top risks by severity."""
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_risks = sorted(all_risks, key=lambda r: severity_order.get(r["severity"], 4))
        return sorted_risks[:limit]

    def _generate_recommendations(self, all_risks: List[Dict],
                                   overall_level: str) -> List[str]:
        """Generate recommendations based on detected risks."""
        recommendations = []

        if overall_level == "CRITICAL":
            recommendations.append("Immediate attention required. Review critical risks.")
        elif overall_level == "HIGH":
            recommendations.append("Multiple significant risks detected. Prioritize risk mitigation.")

        # Specific recommendations based on risk types
        risk_ids = [r["id"] for r in all_risks]

        if "velocity_crisis" in risk_ids:
            recommendations.append("Address velocity blockers to restore progress.")

        if "unvalidated_risks" in risk_ids:
            recommendations.append("Design experiments to validate outstanding risks.")

        if "timeline_risk" in risk_ids:
            recommendations.append("Consider scope or timeline adjustments.")

        if not recommendations:
            recommendations.append("Continue monitoring. No immediate action required.")

        return recommendations[:3]

    def should_alert(self, pursuit_id: str) -> Optional[Dict]:
        """
        Determine if a risk alert should be surfaced.

        Returns highest severity risk if alerting is warranted.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Risk dict or None
        """
        max_alerts = self.config.get("max_risk_alerts_per_session", 2)

        # Check last detection time
        last = self._last_detection.get(pursuit_id)
        if last:
            minutes_since = (datetime.now(timezone.utc) - last).seconds / 60
            if minutes_since < 30:  # Minimum 30 minutes between detections
                return None

        detection = self.detect_risks(pursuit_id)

        if detection.get("overall_risk_level") in ["CRITICAL", "HIGH"]:
            top_risks = detection.get("top_risks", [])
            if top_risks:
                return top_risks[0]

        return None

    def get_risk_summary(self, pursuit_id: str) -> str:
        """
        Generate human-readable risk summary.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Formatted summary string
        """
        detection = self.detect_risks(pursuit_id)

        level = detection.get("overall_risk_level", "UNKNOWN")
        count = detection.get("risk_count", 0)

        lines = [
            f"## Risk Detection Summary",
            "",
            f"**Overall Risk Level:** {level}",
            f"**Total Risks Detected:** {count}",
            ""
        ]

        for horizon_name, horizon_data in detection.get("horizons", {}).items():
            horizon_risks = horizon_data.get("risks", [])
            if horizon_risks:
                lines.append(f"### {horizon_name.replace('_', ' ').title()} ({horizon_data.get('horizon_days')} days)")
                for risk in horizon_risks:
                    severity_marker = {"CRITICAL": "[!]", "HIGH": "[H]", "MEDIUM": "[M]", "LOW": "[L]"}.get(risk["severity"], "[ ]")
                    lines.append(f"- {severity_marker} **{risk['title']}**: {risk['description']}")
                lines.append("")

        if detection.get("recommendations"):
            lines.append("### Recommendations")
            for rec in detection["recommendations"]:
                lines.append(f"- {rec}")

        return "\n".join(lines)
