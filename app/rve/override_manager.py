"""
InDE MVP v3.0.2 - Override Manager
Capture innovator rationale when overriding recommendations.

Features:
- Capture override decisions with rationale
- Track override patterns for learning
- Generate override reports
- Maintain audit trail

CRITICAL: Overrides are NORMAL and EXPECTED. The innovator has full authority.
Red zone findings do NOT auto-terminate - overrides are explicitly supported.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class OverrideManager:
    """
    Manage innovator override decisions.

    When an innovator chooses to proceed despite recommendations
    (especially red zone findings), this manager captures:
    - The decision made
    - Explicit rationale
    - Monitoring plan
    - Acknowledgment of risks

    This is NOT punitive - it's organizational memory.
    """

    # Override decision types
    OVERRIDE_DECISIONS = [
        "ACCEPTED",          # Accepted the recommendation
        "OVERRIDE_PROCEED",  # Proceeding despite recommendation
        "PIVOTED",           # Pivoting to different approach
        "DEFERRED",          # Deferring decision
        "TERMINATED"         # Terminating pursuit
    ]

    def __init__(self, db):
        """
        Initialize override manager.

        Args:
            db: Database instance
        """
        self.db = db

    def record_decision(self, evidence_id: str, decision: str,
                       rationale: str = None, monitoring_plan: str = None,
                       user_id: str = None) -> Dict:
        """
        Record innovator's decision on evidence/assessment.

        Args:
            evidence_id: Evidence package being decided on
            decision: ACCEPTED | OVERRIDE_PROCEED | PIVOTED | DEFERRED | TERMINATED
            rationale: Required for OVERRIDE_PROCEED and TERMINATED
            monitoring_plan: Optional plan for monitoring the risk
            user_id: User making the decision

        Returns:
            Decision record
        """
        if decision not in self.OVERRIDE_DECISIONS:
            raise ValueError(f"Invalid decision: {decision}. Must be one of {self.OVERRIDE_DECISIONS}")

        evidence = self.db.get_evidence_package(evidence_id)
        if not evidence:
            raise ValueError(f"Evidence not found: {evidence_id}")

        # Validate rationale for override and termination
        if decision in ["OVERRIDE_PROCEED", "TERMINATED"] and not rationale:
            raise ValueError(f"Rationale required for {decision} decision")

        # Record the decision
        success = self.db.record_innovator_decision(
            evidence_id=evidence_id,
            decision=decision,
            rationale=rationale,
            monitoring_plan=monitoring_plan
        )

        # Also update the risk
        risk_id = evidence.get("risk_id")
        if risk_id:
            self._update_risk_decision(risk_id, decision, rationale, user_id)

            # Update RVE status if override proceeding with unmitigated risk
            if decision == "OVERRIDE_PROCEED" and evidence.get("verdict") == "RED":
                self._increment_unmitigated_proceeding(evidence.get("pursuit_id"))

        # Log activity
        action_desc = {
            "ACCEPTED": "accepted recommendation",
            "OVERRIDE_PROCEED": "chose to proceed despite recommendation",
            "PIVOTED": "decided to pivot approach",
            "DEFERRED": "deferred decision",
            "TERMINATED": "terminated pursuit"
        }.get(decision, decision)

        self.db.log_activity(
            pursuit_id=evidence.get("pursuit_id"),
            activity_type="decision_recorded",
            description=f"Innovator {action_desc}",
            metadata={
                "evidence_id": evidence_id,
                "risk_id": risk_id,
                "decision": decision,
                "was_override": decision == "OVERRIDE_PROCEED"
            }
        )

        return {
            "success": success,
            "evidence_id": evidence_id,
            "decision": decision,
            "was_override": decision == "OVERRIDE_PROCEED",
            "message": self._get_decision_message(decision)
        }

    def _update_risk_decision(self, risk_id: str, decision: str,
                               rationale: str = None, user_id: str = None) -> None:
        """Update risk record with decision."""
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            return

        latest_rec = risk.get("latest_recommendation", {})
        was_override = decision != latest_rec.get("recommendation")

        decision_record = {
            "user_id": user_id,
            "user_decision": decision,
            "system_recommendation": latest_rec.get("recommendation"),
            "system_zone": risk.get("zone"),
            "was_override": was_override,
            "override_reason": rationale if was_override else None,
            "recorded_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

        self.db.update_risk_definition(risk_id, {
            "user_decision": decision_record,
            "final_decision": decision
        })

    def _increment_unmitigated_proceeding(self, pursuit_id: str) -> None:
        """Track that innovator is proceeding with an unmitigated risk."""
        rve_status = self.db.get_pursuit_rve_status(pursuit_id)
        if rve_status:
            rve_status["risks_unmitigated_proceeding"] = rve_status.get("risks_unmitigated_proceeding", 0) + 1
            self.db.update_pursuit_rve_status(pursuit_id, rve_status)

    def _get_decision_message(self, decision: str) -> str:
        """Get confirmation message for decision."""
        messages = {
            "ACCEPTED": "Decision recorded. Proceeding as recommended.",
            "OVERRIDE_PROCEED": (
                "Override recorded with your rationale. You're proceeding despite "
                "the recommendation. Your reasoning has been documented for organizational memory."
            ),
            "PIVOTED": "Pivot decision recorded. Consider documenting your new approach.",
            "DEFERRED": "Decision deferred. Remember to revisit this when you have more information.",
            "TERMINATED": "Termination recorded. Learnings from this pursuit will inform future work."
        }
        return messages.get(decision, "Decision recorded.")

    def capture_red_zone_override(self, risk_id: str, rationale: str,
                                   monitoring_plan: str = None,
                                   stop_loss_criteria: List[str] = None,
                                   user_id: str = None) -> Dict:
        """
        Specialized capture for proceeding despite red zone finding.

        This is a normal and supported action - not punitive.
        Captures richer context for organizational learning.

        Args:
            risk_id: Risk in red zone
            rationale: Why proceeding despite red zone
            monitoring_plan: How the risk will be monitored
            stop_loss_criteria: Criteria that would trigger reassessment
            user_id: User making decision

        Returns:
            Override record
        """
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        if risk.get("zone") != "RED":
            raise ValueError("This method is for red zone overrides only")

        # Get most recent evidence
        evidence = self.db.get_risk_evidence(risk_id)
        if not evidence:
            raise ValueError("No evidence found for this risk")

        latest_evidence = evidence[0]  # Most recent

        # Record detailed override
        override_record = {
            "risk_id": risk_id,
            "evidence_id": latest_evidence.get("evidence_id"),
            "override_type": "RED_ZONE_PROCEED",
            "rationale": rationale,
            "monitoring_plan": monitoring_plan,
            "stop_loss_criteria": stop_loss_criteria or [],
            "acknowledged_risks": [
                "Proceeding with known unmitigated risk",
                f"Risk parameter: {risk.get('risk_parameter', '')[:100]}"
            ],
            "user_id": user_id,
            "recorded_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

        # Store override details on risk
        self.db.update_risk_definition(risk_id, {
            "red_zone_override": override_record,
            "final_decision": "OVERRIDE_PROCEED"
        })

        # Record on evidence
        self.db.record_innovator_decision(
            evidence_id=latest_evidence.get("evidence_id"),
            decision="OVERRIDE_PROCEED",
            rationale=rationale,
            monitoring_plan=monitoring_plan
        )

        # Update RVE status
        self._increment_unmitigated_proceeding(risk.get("pursuit_id"))

        # Log activity
        self.db.log_activity(
            pursuit_id=risk.get("pursuit_id"),
            activity_type="red_zone_override",
            description="Innovator proceeding despite red zone finding",
            metadata={
                "risk_id": risk_id,
                "has_monitoring_plan": monitoring_plan is not None,
                "has_stop_loss": len(stop_loss_criteria or []) > 0
            }
        )

        return {
            "success": True,
            "risk_id": risk_id,
            "override_type": "RED_ZONE_PROCEED",
            "message": (
                "Red zone override recorded. Your rationale and monitoring plan "
                "have been documented. This is your decision and it is respected. "
                "Consider setting up alerts for your stop-loss criteria."
            )
        }

    def get_override_report(self, pursuit_id: str) -> Dict:
        """
        Generate report of all overrides for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Override report dict
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        report = {
            "pursuit_id": pursuit_id,
            "total_risks": len(risks),
            "total_overrides": 0,
            "red_zone_overrides": 0,
            "overrides": []
        }

        for risk in risks:
            decision = risk.get("user_decision", {})
            if decision.get("was_override"):
                report["total_overrides"] += 1

                override_info = {
                    "risk_id": risk.get("risk_id"),
                    "risk_parameter": risk.get("risk_parameter", "")[:100],
                    "zone": risk.get("zone"),
                    "system_recommendation": decision.get("system_recommendation"),
                    "user_decision": decision.get("user_decision"),
                    "rationale": decision.get("override_reason"),
                    "recorded_at": decision.get("recorded_at")
                }

                if risk.get("zone") == "RED":
                    report["red_zone_overrides"] += 1
                    red_override = risk.get("red_zone_override", {})
                    override_info["monitoring_plan"] = red_override.get("monitoring_plan")
                    override_info["stop_loss_criteria"] = red_override.get("stop_loss_criteria")

                report["overrides"].append(override_info)

        return report

    def generate_override_summary(self, pursuit_id: str) -> str:
        """
        Generate human-readable override summary.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Formatted summary string
        """
        report = self.get_override_report(pursuit_id)

        if report["total_overrides"] == 0:
            return "## Decision Summary\n\nNo overrides recorded. All decisions aligned with recommendations."

        lines = [
            "## Decision Override Summary",
            "",
            f"**Total Overrides:** {report['total_overrides']}",
            f"**Red Zone Overrides:** {report['red_zone_overrides']}",
            ""
        ]

        if report["red_zone_overrides"] > 0:
            lines.append("### Red Zone Overrides (Proceeding Despite Significant Risk)")
            for override in report["overrides"]:
                if override.get("zone") == "RED":
                    lines.append(f"")
                    lines.append(f"**Risk:** {override.get('risk_parameter')}")
                    lines.append(f"**Rationale:** {override.get('rationale', 'Not provided')}")
                    if override.get("monitoring_plan"):
                        lines.append(f"**Monitoring Plan:** {override.get('monitoring_plan')}")
                    if override.get("stop_loss_criteria"):
                        lines.append("**Stop-Loss Criteria:**")
                        for criteria in override["stop_loss_criteria"]:
                            lines.append(f"- {criteria}")
                    lines.append("")

        lines.append("---")
        lines.append("*Override decisions are normal and expected. This summary is for organizational memory.*")

        return "\n".join(lines)

    def check_stop_loss_criteria(self, risk_id: str, current_metrics: Dict) -> Dict:
        """
        Check if stop-loss criteria have been triggered.

        Args:
            risk_id: Risk with stop-loss criteria
            current_metrics: Current metric values

        Returns:
            Dict indicating if criteria triggered
        """
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            return {"error": "Risk not found"}

        red_override = risk.get("red_zone_override", {})
        stop_loss = red_override.get("stop_loss_criteria", [])

        if not stop_loss:
            return {"triggered": False, "message": "No stop-loss criteria defined"}

        # This is a simplified check - real implementation would parse criteria
        triggered = []
        for criteria in stop_loss:
            # Check if any metric indicates the criteria might be triggered
            # This is placeholder logic - would need actual criteria parsing
            for key, value in current_metrics.items():
                if key.lower() in criteria.lower():
                    if isinstance(value, (int, float)) and value < 0:
                        triggered.append({
                            "criteria": criteria,
                            "metric": key,
                            "value": value
                        })

        if triggered:
            return {
                "triggered": True,
                "triggered_criteria": triggered,
                "message": "One or more stop-loss criteria may have been triggered. Review recommended."
            }

        return {
            "triggered": False,
            "message": "No stop-loss criteria triggered based on current metrics."
        }
