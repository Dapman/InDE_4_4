"""
InDE MVP v3.0.2 - Decision Support
Enhanced advisory recommendations based on evidence and three-zone assessment.

Migrated from rve_lite/ and enhanced with:
- Integration with three-zone assessment
- Richer recommendation generation
- Better decision context

Features:
- Generate go/no-go recommendations
- Integrate with RiskAssessmentEngine
- Provide detailed rationale
- IMPORTANT: Advisory only - innovator decides
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from config import (
    RECOMMENDATION_TYPES, VALIDATION_STATUS,
    DECISION_SUPPORT_PROMPT, RVE_CONFIG
)


class DecisionSupport:
    """
    Provide advisory recommendations based on evidence.

    IMPORTANT: All recommendations are ADVISORY ONLY.
    The innovator makes all final decisions.

    v3.0.2: Enhanced with three-zone integration.
    """

    def __init__(self, db, llm=None):
        """
        Initialize decision support.

        Args:
            db: Database instance
            llm: Optional LLM interface for recommendation generation
        """
        self.db = db
        self.llm = llm
        self.config = RVE_CONFIG

    def generate_recommendation(self, risk_id: str) -> Dict:
        """
        Generate advisory recommendation for risk.

        Args:
            risk_id: ID of the risk

        Returns:
            Dict with recommendation and rationale
        """
        # Get risk and evidence
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        evidence = self.db.get_risk_evidence(risk_id)
        zone = risk.get("zone")

        # Generate recommendation based on zone if available
        if zone:
            recommendation = self._zone_based_recommendation(risk, evidence, zone)
        elif self.llm:
            recommendation = self._llm_generate_recommendation(risk, evidence)
        else:
            recommendation = self._default_generate_recommendation(risk, evidence)

        # Add advisory warning
        recommendation["advisory_notice"] = (
            "This recommendation is ADVISORY ONLY. "
            "You, the innovator, make all final decisions. "
            "InDE provides analysis to inform your judgment but does not enforce actions. "
            "Even RED zone findings do not automatically terminate your pursuit."
        )

        # Store recommendation in risk record
        self.db.update_risk_definition(risk_id, {
            "latest_recommendation": recommendation,
            "recommendation_generated_at": datetime.now(timezone.utc)
        })

        # Log activity
        self.db.log_activity(
            pursuit_id=risk.get("pursuit_id"),
            activity_type="recommendation_generated",
            description=f"Advisory recommendation: {recommendation.get('recommendation')}",
            metadata={
                "risk_id": risk_id,
                "recommendation": recommendation.get("recommendation"),
                "confidence": recommendation.get("confidence"),
                "zone": zone
            }
        )

        return recommendation

    def _zone_based_recommendation(self, risk: Dict, evidence: List[Dict],
                                    zone: str) -> Dict:
        """
        v3.0.2: Generate recommendation based on three-zone assessment.

        Args:
            risk: Risk definition
            evidence: Evidence list
            zone: GREEN, YELLOW, or RED

        Returns:
            Recommendation dict
        """
        if not evidence:
            return self._no_evidence_recommendation()

        # Calculate confidence from evidence
        total_confidence = sum(
            e.get("rigor_assessment", {}).get("overall_confidence", 0)
            for e in evidence
        )
        avg_confidence = total_confidence / len(evidence) if evidence else 0

        if zone == "GREEN":
            return {
                "status": "MITIGATED",
                "recommendation": "PROCEED",
                "zone": "GREEN",
                "confidence": round(avg_confidence, 2),
                "rationale": (
                    f"Evidence from {len(evidence)} sources demonstrates this risk "
                    f"is manageable. Confidence: {avg_confidence:.0%}. "
                    "You can proceed with implementation while maintaining standard monitoring."
                ),
                "key_considerations": [
                    "Continue monitoring for any late-emerging concerns",
                    "Document this risk as mitigated in your portfolio",
                    "Share learnings with future pursuits"
                ]
            }

        elif zone == "RED":
            return {
                "status": "UNMITIGATED",
                "recommendation": "EVALUATE_ALTERNATIVES",
                "zone": "RED",
                "confidence": round(avg_confidence, 2),
                "rationale": (
                    f"Evidence suggests this risk cannot be adequately mitigated "
                    f"with the current approach. This finding is significant but "
                    "does NOT automatically stop your pursuit. Consider your options."
                ),
                "key_considerations": [
                    "Evaluate whether a fundamental pivot could address this risk",
                    "Consider if this risk could be tolerated with explicit justification",
                    "Termination is an option but your choice - document your reasoning",
                    "If proceeding despite red zone, set clear stop-loss criteria"
                ],
                "options_to_consider": [
                    {"option": "TERMINATE", "description": "End pursuit and capture learnings"},
                    {"option": "PIVOT", "description": "Fundamentally change approach to address risk"},
                    {"option": "OVERRIDE_PROCEED", "description": "Proceed anyway with documented justification"}
                ]
            }

        else:  # YELLOW
            return {
                "status": "UNCERTAIN",
                "recommendation": "INVESTIGATE_OR_PROCEED_CAUTIOUSLY",
                "zone": "YELLOW",
                "confidence": round(avg_confidence, 2),
                "rationale": (
                    f"Evidence is mixed or inconclusive (confidence: {avg_confidence:.0%}). "
                    "You can either gather more evidence or proceed with enhanced monitoring."
                ),
                "key_considerations": [
                    "Consider refining your experiment and gathering more data",
                    "Alternative: proceed with explicit monitoring plan",
                    "Set clear criteria for when to reassess"
                ],
                "options_to_consider": [
                    {"option": "ADDITIONAL_VALIDATION", "description": "Design new experiment to clarify"},
                    {"option": "PROCEED_WITH_MONITORING", "description": "Move forward with enhanced tracking"},
                    {"option": "PIVOT", "description": "Try different approach to avoid uncertainty"}
                ]
            }

    def _no_evidence_recommendation(self) -> Dict:
        """Recommendation when no evidence exists."""
        return {
            "status": "UNCERTAIN",
            "recommendation": "INVESTIGATE_FURTHER",
            "zone": None,
            "confidence": 0.3,
            "rationale": "No validation evidence has been collected yet.",
            "key_considerations": [
                "Design a validation experiment to test this risk",
                "Collect initial evidence before making decisions",
                "Set clear success criteria for your experiment"
            ]
        }

    def _llm_generate_recommendation(self, risk: Dict,
                                      evidence: List[Dict]) -> Dict:
        """Use LLM to generate recommendation."""
        evidence_summary = self._build_evidence_summary(evidence)

        prompt = DECISION_SUPPORT_PROMPT.format(
            risk_parameter=risk.get("risk_parameter", ""),
            acceptable_threshold=risk.get("acceptable_threshold", ""),
            category=risk.get("risk_category", ""),
            priority=risk.get("validation_priority", ""),
            evidence_summary=evidence_summary
        )

        try:
            response = self.llm.generate(prompt, max_tokens=500)
            return self._parse_recommendation(response)
        except Exception as e:
            print(f"[DecisionSupport] LLM generation failed: {e}")
            return self._default_generate_recommendation(risk, evidence)

    def _parse_recommendation(self, response: str) -> Dict:
        """Parse LLM response for recommendation."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {
            "status": "UNCERTAIN",
            "recommendation": "INVESTIGATE_FURTHER",
            "confidence": 0.5,
            "rationale": "Unable to generate detailed recommendation",
            "key_considerations": ["Gather more evidence", "Review risk parameters"]
        }

    def _default_generate_recommendation(self, risk: Dict,
                                          evidence: List[Dict]) -> Dict:
        """Generate recommendation without LLM."""
        if not evidence:
            return self._no_evidence_recommendation()

        total_confidence = sum(
            e.get("rigor_assessment", {}).get("overall_confidence", 0)
            for e in evidence
        )
        avg_confidence = total_confidence / len(evidence)

        total_sample = sum(e.get("sample_size", 0) for e in evidence)

        # Analyze results for positive/negative signals
        positive_signals = 0
        negative_signals = 0

        for e in evidence:
            results = e.get("results", {})
            quant = results.get("quantitative_metrics", {})

            for key, value in quant.items():
                if isinstance(value, (int, float)):
                    if value > 0:
                        positive_signals += 1
                    else:
                        negative_signals += 1

        # Generate recommendation
        if avg_confidence >= 0.7 and positive_signals > negative_signals:
            status = "MITIGATED"
            recommendation = "PROCEED"
            rationale = f"Evidence from {len(evidence)} sources with {total_sample} data points suggests risk is manageable."
        elif avg_confidence >= 0.5:
            if positive_signals > negative_signals * 2:
                status = "MITIGATED"
                recommendation = "PROCEED"
                rationale = "Moderate evidence suggests positive outlook, though additional validation recommended."
            elif negative_signals > positive_signals:
                status = "UNMITIGATED"
                recommendation = "EVALUATE_ALTERNATIVES"
                rationale = "Evidence suggests significant concerns. Consider alternative approaches."
            else:
                status = "UNCERTAIN"
                recommendation = "INVESTIGATE_FURTHER"
                rationale = "Mixed signals in evidence. More data needed for confident decision."
        else:
            status = "UNCERTAIN"
            recommendation = "INVESTIGATE_FURTHER"
            rationale = f"Evidence confidence ({avg_confidence:.0%}) is below threshold for decision-making."

        return {
            "status": status,
            "recommendation": recommendation,
            "confidence": round(avg_confidence, 2),
            "rationale": rationale,
            "key_considerations": self._generate_considerations(risk, evidence, status)
        }

    def _generate_considerations(self, risk: Dict, evidence: List[Dict],
                                  status: str) -> List[str]:
        """Generate key considerations for decision."""
        considerations = []

        priority = risk.get("validation_priority", "MEDIUM")
        if priority == "CRITICAL":
            considerations.append("This is a CRITICAL risk - ensure thorough validation")

        total_sample = sum(e.get("sample_size", 0) for e in evidence)
        if total_sample < 30:
            considerations.append(f"Sample size ({total_sample}) is limited - larger sample recommended")

        if len(evidence) == 1:
            considerations.append("Only one evidence source - triangulation with additional methods recommended")

        if status == "UNCERTAIN":
            considerations.append("Consider structured experiment to generate clearer signal")

        return considerations[:4]

    def _build_evidence_summary(self, evidence: List[Dict]) -> str:
        """Build text summary of evidence for LLM."""
        if not evidence:
            return "No evidence collected yet."

        lines = []
        for i, e in enumerate(evidence, 1):
            lines.append(f"Evidence {i}:")
            lines.append(f"  Methodology: {e.get('methodology', 'Unknown')}")
            lines.append(f"  Sample Size: {e.get('sample_size', 0)}")

            results = e.get("results", {})
            quant = results.get("quantitative_metrics", {})
            if quant:
                lines.append(f"  Metrics: {quant}")

            qual = results.get("qualitative_insights", [])
            if qual:
                lines.append(f"  Insights: {qual[:2]}")

            rigor = e.get("rigor_assessment", {})
            lines.append(f"  Confidence: {rigor.get('confidence_level', 'Unknown')}")
            lines.append("")

        return "\n".join(lines)

    def get_pursuit_decision_summary(self, pursuit_id: str) -> Dict:
        """
        Get summary of all decisions for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with decision statistics
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        summary = {
            "total_risks": len(risks),
            "with_recommendation": 0,
            "with_decision": 0,
            "overrides": 0,
            "by_zone": {"GREEN": 0, "YELLOW": 0, "RED": 0, "UNASSESSED": 0},
            "by_recommendation": {},
            "by_decision": {},
            "risks": []
        }

        for risk in risks:
            zone = risk.get("zone") or "UNASSESSED"
            summary["by_zone"][zone] = summary["by_zone"].get(zone, 0) + 1

            rec = risk.get("latest_recommendation")
            if rec:
                summary["with_recommendation"] += 1
                rec_type = rec.get("recommendation", "UNKNOWN")
                summary["by_recommendation"][rec_type] = summary["by_recommendation"].get(rec_type, 0) + 1

            decision = risk.get("user_decision")
            if decision:
                summary["with_decision"] += 1
                if decision.get("was_override"):
                    summary["overrides"] += 1
                dec_type = decision.get("user_decision", "UNKNOWN")
                summary["by_decision"][dec_type] = summary["by_decision"].get(dec_type, 0) + 1

            summary["risks"].append({
                "risk_id": risk.get("risk_id"),
                "risk_parameter": risk.get("risk_parameter", "")[:50],
                "zone": zone,
                "recommendation": rec.get("recommendation") if rec else None,
                "user_decision": decision.get("user_decision") if decision else None,
                "was_override": decision.get("was_override") if decision else False
            })

        return summary

    def format_recommendation_display(self, recommendation: Dict) -> str:
        """
        Format recommendation for display to user.

        Args:
            recommendation: Recommendation dict

        Returns:
            Formatted string
        """
        zone = recommendation.get("zone", "UNKNOWN")
        zone_indicator = {
            "GREEN": "[GREEN ZONE]",
            "YELLOW": "[YELLOW ZONE]",
            "RED": "[RED ZONE]"
        }.get(zone, "")

        lines = [
            "## Advisory Recommendation",
            "",
            zone_indicator if zone_indicator else "",
            f"**Status:** {recommendation.get('status', 'Unknown')}",
            f"**Recommendation:** {recommendation.get('recommendation', 'Unknown')}",
            f"**Confidence:** {recommendation.get('confidence', 0):.0%}",
            "",
            "### Rationale",
            recommendation.get("rationale", "No rationale provided"),
            "",
            "### Key Considerations"
        ]

        for consideration in recommendation.get("key_considerations", []):
            lines.append(f"- {consideration}")

        # Add options if present
        if recommendation.get("options_to_consider"):
            lines.append("")
            lines.append("### Your Options")
            for opt in recommendation["options_to_consider"]:
                lines.append(f"- **{opt['option']}:** {opt['description']}")

        lines.extend([
            "",
            "---",
            "*" + recommendation.get("advisory_notice", "This is advisory only.") + "*"
        ])

        return "\n".join(lines)
