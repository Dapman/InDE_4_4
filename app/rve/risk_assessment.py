"""
InDE MVP v3.0.2 - Risk Assessment Engine
Three-zone (GREEN/YELLOW/RED) assessment based on evidence.

Features:
- Aggregate evidence into zone assessment
- Calculate confidence scores
- Generate recommendations per zone
- Track assessment history
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from config import RVE_CONFIG, RVE_ZONES


class RiskAssessmentEngine:
    """
    Three-zone assessment engine for risk validation.

    Aggregates evidence and assigns risks to:
    - GREEN: Risk mitigated, proceed with confidence
    - YELLOW: Uncertain, more validation needed or proceed with monitoring
    - RED: Unmitigated, consider termination or fundamental pivot

    CRITICAL: All assessments are ADVISORY ONLY.
    The innovator retains full decision authority.
    """

    def __init__(self, db, llm=None):
        """
        Initialize the assessment engine.

        Args:
            db: Database instance
            llm: Optional LLM interface for sophisticated assessment
        """
        self.db = db
        self.llm = llm
        self.config = RVE_CONFIG
        self.zones = RVE_ZONES

    def assess_risk(self, risk_id: str, evidence_ids: List[str] = None) -> Dict:
        """
        Perform three-zone assessment on a risk.

        Args:
            risk_id: Risk to assess
            evidence_ids: Optional specific evidence to consider (defaults to all)

        Returns:
            Dict with zone assessment and recommendations
        """
        if not self.config.get("enable_three_zone_assessment", True):
            raise ValueError("Three-zone assessment is disabled")

        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        # Get evidence
        if evidence_ids:
            evidence = [self.db.get_evidence_package(eid) for eid in evidence_ids]
            evidence = [e for e in evidence if e is not None]
        else:
            evidence = self.db.get_risk_evidence(risk_id)

        # Perform assessment
        assessment = self._calculate_zone(risk, evidence)

        # Store assessment on each evidence package
        for e in evidence:
            self.db.update_evidence_verdict(
                evidence_id=e.get("evidence_id"),
                verdict=assessment.get("zone"),
                recommendation=assessment.get("primary_recommendation"),
                confidence=assessment.get("confidence"),
                rigor_score=assessment.get("aggregate_rigor")
            )

        # Update risk with zone
        self.db.update_risk_definition(risk_id, {
            "zone": assessment.get("zone"),
            "latest_assessment": assessment,
            "assessed_at": datetime.now(timezone.utc).isoformat() + 'Z'
        })

        # Update pursuit RVE zone counts
        self._update_pursuit_zone_counts(risk.get("pursuit_id"))

        # Log activity
        self.db.log_activity(
            pursuit_id=risk.get("pursuit_id"),
            activity_type="risk_assessed",
            description=f"Risk assessed as {assessment.get('zone')}: {risk.get('risk_parameter', '')[:50]}",
            metadata={
                "risk_id": risk_id,
                "zone": assessment.get("zone"),
                "confidence": assessment.get("confidence")
            }
        )

        return assessment

    def _calculate_zone(self, risk: Dict, evidence: List[Dict]) -> Dict:
        """
        Calculate zone assignment based on evidence.

        Args:
            risk: Risk definition
            evidence: List of evidence packages

        Returns:
            Zone assessment dict
        """
        if not evidence:
            return {
                "zone": "YELLOW",
                "confidence": 0.3,
                "aggregate_rigor": 0.0,
                "evidence_count": 0,
                "rationale": "No evidence collected yet. Zone defaulted to YELLOW.",
                "primary_recommendation": "Design and run validation experiment",
                "recommendations": [
                    "Design validation experiment",
                    "Collect initial evidence",
                    "Define clear success criteria"
                ],
                "advisory_notice": self._get_advisory_notice()
            }

        # Aggregate evidence metrics
        total_confidence = 0
        total_rigor = 0
        positive_signals = 0
        negative_signals = 0
        total_sample = 0

        for e in evidence:
            rigor = e.get("rigor_assessment", {})
            conf = rigor.get("overall_confidence", 0.5)
            total_confidence += conf
            total_rigor += rigor.get("methodology_strength", 0.5)

            results = e.get("results", {})
            quant = results.get("quantitative_metrics", {})

            total_sample += e.get("sample_size", 0)

            for key, value in quant.items():
                if isinstance(value, (int, float)):
                    if value > 0:
                        positive_signals += 1
                    else:
                        negative_signals += 1

        evidence_count = len(evidence)
        avg_confidence = total_confidence / evidence_count
        avg_rigor = total_rigor / evidence_count

        # Zone determination logic
        priority = risk.get("validation_priority", "MEDIUM")
        priority_multiplier = {"CRITICAL": 1.2, "HIGH": 1.1, "MEDIUM": 1.0, "LOW": 0.9}.get(priority, 1.0)

        # Threshold adjustments based on priority
        green_threshold = self.config.get("default_confidence_threshold", 0.80) / priority_multiplier
        red_threshold = 0.35

        # Calculate zone
        if avg_confidence >= green_threshold and positive_signals > negative_signals * 1.5:
            zone = "GREEN"
            recommendations = self._get_green_recommendations()
            rationale = f"Evidence (n={total_sample}) demonstrates risk is manageable. Confidence: {avg_confidence:.0%}"
            primary_rec = "Proceed with confidence"

        elif avg_confidence < red_threshold or negative_signals > positive_signals * 2:
            zone = "RED"
            recommendations = self._get_red_recommendations()
            rationale = f"Evidence suggests significant risk exposure. {negative_signals} negative signals vs {positive_signals} positive."
            primary_rec = "Consider termination or fundamental pivot"

        else:
            zone = "YELLOW"
            recommendations = self._get_yellow_recommendations()
            rationale = f"Evidence is mixed or insufficient. Confidence: {avg_confidence:.0%}. Additional validation recommended."
            primary_rec = "Proceed with monitoring or collect more evidence"

        return {
            "zone": zone,
            "zone_info": self.zones.get(zone, {}),
            "confidence": round(avg_confidence, 2),
            "aggregate_rigor": round(avg_rigor, 2),
            "evidence_count": evidence_count,
            "total_sample_size": total_sample,
            "signal_analysis": {
                "positive": positive_signals,
                "negative": negative_signals,
                "net": positive_signals - negative_signals
            },
            "rationale": rationale,
            "primary_recommendation": primary_rec,
            "recommendations": recommendations,
            "advisory_notice": self._get_advisory_notice(),
            "risk_priority": priority
        }

    def _get_green_recommendations(self) -> List[str]:
        """Get recommendations for GREEN zone."""
        return [
            "Proceed with implementation",
            "Document risk as mitigated in portfolio",
            "Monitor for any late-emerging concerns"
        ]

    def _get_yellow_recommendations(self) -> List[str]:
        """Get recommendations for YELLOW zone."""
        return [
            "Refine experiment design and re-test",
            "Proceed with enhanced monitoring",
            "Consider alternative validation approaches",
            "Pivot to different solution approach if patterns persist"
        ]

    def _get_red_recommendations(self) -> List[str]:
        """Get recommendations for RED zone."""
        return [
            "Consider termination of current approach",
            "Evaluate fundamental pivot options",
            "If proceeding despite red zone, document explicit justification",
            "Set up enhanced monitoring with clear stop-loss criteria"
        ]

    def _get_advisory_notice(self) -> str:
        """Get the standard advisory notice."""
        return (
            "This assessment is ADVISORY ONLY. You, the innovator, retain full decision "
            "authority. InDE provides analysis to inform your judgment but does not "
            "make decisions for you. Red zone findings do NOT automatically terminate "
            "your pursuit - they surface important information for your consideration."
        )

    def _update_pursuit_zone_counts(self, pursuit_id: str) -> None:
        """Update pursuit RVE status with zone counts."""
        risks = self.db.get_pursuit_risks(pursuit_id)

        zone_counts = {"green": 0, "yellow": 0, "red": 0}
        validated = 0

        for risk in risks:
            zone = risk.get("zone")
            if zone:
                zone_lower = zone.lower()
                zone_counts[zone_lower] = zone_counts.get(zone_lower, 0) + 1
                validated += 1

        rve_status = self.db.get_pursuit_rve_status(pursuit_id)
        if rve_status:
            rve_status["risks_green"] = zone_counts["green"]
            rve_status["risks_yellow"] = zone_counts["yellow"]
            rve_status["risks_red"] = zone_counts["red"]
            rve_status["risks_validated"] = validated
            self.db.update_pursuit_rve_status(pursuit_id, rve_status)

    def get_pursuit_risk_landscape(self, pursuit_id: str) -> Dict:
        """
        Get overall risk landscape for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with risk landscape summary
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        landscape = {
            "total_risks": len(risks),
            "assessed": 0,
            "by_zone": {"GREEN": [], "YELLOW": [], "RED": [], "UNASSESSED": []},
            "critical_in_red": 0,
            "needs_assessment": [],
            "overall_risk_level": "LOW"
        }

        for risk in risks:
            zone = risk.get("zone")
            if zone:
                landscape["assessed"] += 1
                landscape["by_zone"][zone].append({
                    "risk_id": risk.get("risk_id"),
                    "parameter": risk.get("risk_parameter", "")[:50],
                    "priority": risk.get("validation_priority")
                })
                if zone == "RED" and risk.get("validation_priority") == "CRITICAL":
                    landscape["critical_in_red"] += 1
            else:
                landscape["by_zone"]["UNASSESSED"].append({
                    "risk_id": risk.get("risk_id"),
                    "parameter": risk.get("risk_parameter", "")[:50],
                    "priority": risk.get("validation_priority")
                })
                landscape["needs_assessment"].append(risk.get("risk_id"))

        # Calculate overall risk level
        red_count = len(landscape["by_zone"]["RED"])
        yellow_count = len(landscape["by_zone"]["YELLOW"])
        total = landscape["total_risks"]

        if landscape["critical_in_red"] > 0 or red_count > total * 0.3:
            landscape["overall_risk_level"] = "CRITICAL"
        elif red_count > 0 or yellow_count > total * 0.5:
            landscape["overall_risk_level"] = "HIGH"
        elif yellow_count > 0:
            landscape["overall_risk_level"] = "MODERATE"
        else:
            landscape["overall_risk_level"] = "LOW"

        return landscape

    def generate_assessment_summary(self, pursuit_id: str) -> str:
        """
        Generate a human-readable assessment summary for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Formatted summary string
        """
        landscape = self.get_pursuit_risk_landscape(pursuit_id)

        green_count = len(landscape["by_zone"]["GREEN"])
        yellow_count = len(landscape["by_zone"]["YELLOW"])
        red_count = len(landscape["by_zone"]["RED"])
        unassessed = len(landscape["by_zone"]["UNASSESSED"])

        summary = f"""## Risk Validation Summary

**Overall Risk Level:** {landscape["overall_risk_level"]}

### Zone Distribution
- **GREEN** (Mitigated): {green_count} risks
- **YELLOW** (Uncertain): {yellow_count} risks
- **RED** (Unmitigated): {red_count} risks
- **Unassessed**: {unassessed} risks

"""

        if landscape["critical_in_red"] > 0:
            summary += f"**ATTENTION:** {landscape['critical_in_red']} CRITICAL risk(s) in RED zone.\n\n"

        if red_count > 0:
            summary += "### Red Zone Risks Requiring Attention\n"
            for risk in landscape["by_zone"]["RED"]:
                summary += f"- [{risk['priority']}] {risk['parameter']}\n"
            summary += "\n"

        if unassessed:
            summary += f"### {unassessed} Risks Need Assessment\n"
            summary += "Run experiments and capture evidence to assess these risks.\n\n"

        summary += "---\n*This summary is advisory only. You retain full decision authority.*"

        return summary

    def recommend_next_action(self, pursuit_id: str) -> Dict:
        """
        Recommend the most important next action for risk validation.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with recommended action
        """
        landscape = self.get_pursuit_risk_landscape(pursuit_id)

        # Priority 1: Critical risks in red zone
        if landscape["critical_in_red"] > 0:
            red_critical = [
                r for r in landscape["by_zone"]["RED"]
                if r.get("priority") == "CRITICAL"
            ]
            return {
                "action": "address_critical_red",
                "urgency": "HIGH",
                "description": f"Address {landscape['critical_in_red']} critical risk(s) in red zone",
                "risks": red_critical,
                "message": "Critical risks have been flagged as unmitigated. Review and decide on path forward."
            }

        # Priority 2: Unassessed high-priority risks
        high_unassessed = [
            r for r in landscape["by_zone"]["UNASSESSED"]
            if r.get("priority") in ["CRITICAL", "HIGH"]
        ]
        if high_unassessed:
            return {
                "action": "assess_high_priority",
                "urgency": "MEDIUM",
                "description": f"Validate {len(high_unassessed)} high-priority unassessed risk(s)",
                "risks": high_unassessed,
                "message": "Design experiments to validate these high-priority risks."
            }

        # Priority 3: Any unassessed risks
        if landscape["needs_assessment"]:
            return {
                "action": "assess_remaining",
                "urgency": "LOW",
                "description": f"Validate {len(landscape['needs_assessment'])} remaining unassessed risk(s)",
                "risk_ids": landscape["needs_assessment"],
                "message": "Continue risk validation to complete your risk landscape."
            }

        # All assessed
        if landscape["overall_risk_level"] in ["LOW", "MODERATE"]:
            return {
                "action": "proceed",
                "urgency": "INFO",
                "description": "Risk landscape looks manageable",
                "message": "All identified risks have been assessed. Overall risk level is acceptable."
            }
        else:
            return {
                "action": "review_landscape",
                "urgency": "MEDIUM",
                "description": "Review risk landscape and make decisions",
                "message": "All risks assessed but overall risk level is elevated. Review and decide."
            }
