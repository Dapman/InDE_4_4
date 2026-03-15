"""
InDE MVP v3.0.2 - Evidence Framework
Capture validation evidence for identified risks.

Migrated from rve_lite/evidence_capture.py and enhanced with:
- Integration with experiment wizard
- Three-zone assessment support
- Enhanced rigor assessment
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from config import (
    EVIDENCE_CONFIDENCE_LEVELS, EVIDENCE_ASSESSMENT_PROMPT,
    RVE_CONFIG
)


class EvidenceFramework:
    """
    Capture and assess validation evidence for risks.

    Records evidence from experiments, interviews, and other
    validation activities with rigor assessment.

    v3.0.2: Enhanced with experiment linking and three-zone compatibility.
    """

    def __init__(self, db, llm=None):
        """
        Initialize the evidence framework.

        Args:
            db: Database instance
            llm: Optional LLM interface for rigor assessment
        """
        self.db = db
        self.llm = llm
        self.config = RVE_CONFIG

    def capture_evidence(self, risk_id: str, pursuit_id: str,
                         methodology: str, sample_size: int,
                         results: Dict,
                         experiment_id: str = None,
                         notes: str = None) -> str:
        """
        Record validation evidence for risk.

        Args:
            risk_id: ID of the risk being validated
            pursuit_id: ID of the pursuit
            methodology: How evidence was collected (interviews, survey, etc.)
            sample_size: Number of data points
            results: Dict with quantitative_metrics and qualitative_insights
            experiment_id: Optional linked experiment (v3.0.2)
            notes: Additional notes

        Returns:
            evidence_id of created package
        """
        # Verify risk exists
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        # Assess rigor
        rigor_assessment = self.assess_rigor(
            methodology=methodology,
            sample_size=sample_size,
            results=results,
            risk=risk
        )

        # Create evidence package with v3.0.2 enhanced fields
        evidence_record = {
            "pursuit_id": pursuit_id,
            "risk_id": risk_id,
            "collection_date": datetime.now(timezone.utc),
            "methodology": methodology,
            "sample_size": sample_size,
            "results": results,
            "rigor_assessment": rigor_assessment,
            "notes": notes,
            # v3.0.2: Enhanced fields for three-zone assessment
            "experiment_id": experiment_id,
            "verdict": None,  # Will be set by RiskAssessmentEngine
            "recommendation": None,
            "confidence": rigor_assessment.get("overall_confidence", 0),
            "rigor_score": rigor_assessment.get("overall_confidence", 0),
            "innovator_decision": None,
            "decision_rationale": None,
            "monitoring_plan": None
        }

        evidence_id = self.db.create_evidence_package(evidence_record)

        # Link to risk
        self.db.link_evidence_to_risk(risk_id, evidence_id)

        # Update risk validation status if warranted
        self._update_risk_status(risk_id)

        # v3.0.2: Update experiment if linked
        if experiment_id:
            self.db.update_validation_experiment(experiment_id, {
                "evidence_id": evidence_id,
                "has_evidence": True
            })

        # Create .evidence artifact
        artifact_content = self._generate_evidence_artifact(
            risk, evidence_record, rigor_assessment
        )

        artifact = self.db.create_artifact(
            pursuit_id=pursuit_id,
            artifact_type="evidence",
            content=artifact_content,
            elements_used=["risk_validation"],
            completeness=rigor_assessment.get("overall_confidence", 0.5),
            generation_method="evidence_capture"
        )

        # Update evidence with artifact link
        self.db.update_evidence_package(evidence_id, {
            "artifact_id": artifact.get("artifact_id")
        })

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="evidence_captured",
            description=f"Captured evidence via {methodology} (n={sample_size})",
            metadata={
                "evidence_id": evidence_id,
                "risk_id": risk_id,
                "experiment_id": experiment_id,
                "confidence": rigor_assessment.get("confidence_level")
            }
        )

        return evidence_id

    def capture_experiment_evidence(self, experiment_id: str,
                                     results: Dict) -> str:
        """
        v3.0.2: Capture evidence from a completed experiment.

        Args:
            experiment_id: Completed experiment ID
            results: Results from the experiment

        Returns:
            evidence_id of created package
        """
        experiment = self.db.get_validation_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        return self.capture_evidence(
            risk_id=experiment.get("risk_id"),
            pursuit_id=experiment.get("pursuit_id"),
            methodology=experiment.get("methodology", "experiment"),
            sample_size=results.get("sample_size", 0),
            results=results,
            experiment_id=experiment_id,
            notes=f"Evidence from experiment: {experiment.get('title', 'Untitled')}"
        )

    def assess_rigor(self, methodology: str, sample_size: int,
                     results: Dict, risk: Dict = None) -> Dict:
        """
        Comprehensive rigor scoring of evidence.

        Args:
            methodology: Collection method
            sample_size: Sample size
            results: Results data
            risk: Optional risk being validated

        Returns:
            Dict with confidence assessment
        """
        # Base confidence from sample size
        if sample_size >= 30:
            sample_score = 0.8
            sample_adequacy = "Adequate sample for statistical significance"
        elif sample_size >= 10:
            sample_score = 0.6
            sample_adequacy = "Moderate sample, directionally useful"
        elif sample_size >= 5:
            sample_score = 0.4
            sample_adequacy = "Small sample, preliminary findings"
        else:
            sample_score = 0.2
            sample_adequacy = "Very small sample, anecdotal only"

        # Methodology confidence
        methodology_scores = {
            "controlled_experiment": 0.9,
            "a/b_test": 0.85,
            "landing_page_test": 0.7,
            "user_interviews": 0.65,
            "customer_survey": 0.6,
            "expert_interviews": 0.55,
            "competitive_analysis": 0.5,
            "desk_research": 0.4,
            "informal_feedback": 0.3,
            "gut_feel": 0.1,
            # v3.0.2: Additional experiment methodologies
            "concierge_mvp": 0.75,
            "smoke_test": 0.70,
            "wizard_of_oz": 0.72,
            "split_test": 0.85,
            "prototype_test": 0.68,
            "observation_study": 0.60,
            "co_creation_session": 0.55,
            "diary_study": 0.58,
            "technical_feasibility": 0.70,
            "market_assessment": 0.55,
            "financial_analysis": 0.65,
            "competitive_scan": 0.50,
            "regulatory_review": 0.75
        }
        methodology_lower = methodology.lower().replace(" ", "_")
        methodology_score = methodology_scores.get(methodology_lower, 0.5)

        # Bias controls (simplified assessment)
        bias_controls = []
        if sample_size >= 10:
            bias_controls.append("Reasonable sample size")
        if methodology_score >= 0.6:
            bias_controls.append("Structured methodology")
        if results.get("quantitative_metrics"):
            bias_controls.append("Quantitative data collected")
        if results.get("qualitative_insights"):
            bias_controls.append("Qualitative insights captured")

        # v3.0.2: Additional rigor factors
        if results.get("control_group"):
            bias_controls.append("Control group used")
            methodology_score += 0.05
        if results.get("blind_methodology"):
            bias_controls.append("Blinded methodology")
            methodology_score += 0.05

        # Overall confidence
        overall_confidence = min(1.0, sample_score * 0.4 + methodology_score * 0.6)

        # Determine confidence level
        for level, config in EVIDENCE_CONFIDENCE_LEVELS.items():
            if overall_confidence >= config["min_score"]:
                confidence_level = level
                break
        else:
            confidence_level = "LOW"

        return {
            "confidence_level": confidence_level,
            "overall_confidence": round(overall_confidence, 2),
            "sample_adequacy": sample_adequacy,
            "methodology_strength": round(methodology_score, 2),
            "bias_controls": bias_controls,
            "recommendation": self._generate_recommendation(
                confidence_level, overall_confidence
            ),
            # v3.0.2: Three-zone suggestion
            "suggested_zone": self._suggest_zone(overall_confidence, results)
        }

    def _suggest_zone(self, confidence: float, results: Dict) -> str:
        """v3.0.2: Suggest three-zone assessment based on evidence."""
        quant = results.get("quantitative_metrics", {})

        # Count positive vs negative signals
        positive = 0
        negative = 0
        for key, value in quant.items():
            if isinstance(value, (int, float)):
                if value > 0:
                    positive += 1
                else:
                    negative += 1

        if confidence >= 0.7 and positive > negative:
            return "GREEN"
        elif confidence < 0.4 or negative > positive * 2:
            return "RED"
        else:
            return "YELLOW"

    def _generate_recommendation(self, confidence_level: str,
                                  confidence_score: float) -> str:
        """Generate interpretation of evidence."""
        if confidence_level == "HIGH":
            return "Evidence is strong enough for decision-making"
        elif confidence_level == "MEDIUM":
            return "Evidence provides direction but additional validation recommended"
        else:
            return "Evidence is preliminary; gather more data before deciding"

    def _update_risk_status(self, risk_id: str) -> None:
        """Update risk validation status based on evidence."""
        evidence = self.db.get_risk_evidence(risk_id)

        if not evidence:
            return

        # Calculate aggregate confidence
        total_confidence = sum(
            e.get("rigor_assessment", {}).get("overall_confidence", 0)
            for e in evidence
        )
        avg_confidence = total_confidence / len(evidence)

        # Update validation state
        if avg_confidence >= 0.7 and len(evidence) >= 2:
            new_state = "VALIDATED"
        elif avg_confidence >= 0.4:
            new_state = "PARTIALLY_VALIDATED"
        else:
            new_state = "ASSUMPTION"

        # Update status
        if avg_confidence >= 0.7:
            status = "VALIDATED"
        elif len(evidence) > 0:
            status = "IN_PROGRESS"
        else:
            status = "NOT_STARTED"

        self.db.update_risk_definition(risk_id, {
            "current_validation_state": new_state,
            "validation_status": status
        })

    def _generate_evidence_artifact(self, risk: Dict, evidence: Dict,
                                    rigor: Dict) -> str:
        """Generate .evidence artifact content."""
        results = evidence.get("results", {})
        quant = results.get("quantitative_metrics", {})
        qual = results.get("qualitative_insights", [])

        quant_str = "\n".join([f"- {k}: {v}" for k, v in quant.items()]) if quant else "None recorded"
        qual_str = "\n".join([f"- {i}" for i in qual]) if qual else "None recorded"

        experiment_note = ""
        if evidence.get("experiment_id"):
            experiment_note = f"\n## Linked Experiment\nExperiment ID: {evidence.get('experiment_id')}\n"

        return f"""# Evidence Package

## Risk Being Validated
{risk.get('risk_parameter', 'Unknown')}

## Collection Details
- **Methodology:** {evidence.get('methodology', 'Unknown')}
- **Sample Size:** {evidence.get('sample_size', 0)}
- **Collection Date:** {evidence.get('collection_date', datetime.now(timezone.utc)).strftime('%Y-%m-%d')}
{experiment_note}
## Results

### Quantitative Metrics
{quant_str}

### Qualitative Insights
{qual_str}

## Rigor Assessment
- **Confidence Level:** {rigor.get('confidence_level', 'UNKNOWN')}
- **Overall Confidence:** {rigor.get('overall_confidence', 0):.0%}
- **Sample Adequacy:** {rigor.get('sample_adequacy', 'Not assessed')}
- **Suggested Zone:** {rigor.get('suggested_zone', 'YELLOW')}

### Bias Controls
{chr(10).join(['- ' + c for c in rigor.get('bias_controls', ['None identified'])])}

## Recommendation
{rigor.get('recommendation', 'No recommendation')}

---
*Evidence captured - RVE v3.0.2*
"""

    def get_risk_evidence_summary(self, risk_id: str) -> Dict:
        """
        Get summary of all evidence for a risk.

        Args:
            risk_id: Risk ID

        Returns:
            Dict with evidence summary
        """
        evidence = self.db.get_risk_evidence(risk_id)

        if not evidence:
            return {
                "evidence_count": 0,
                "aggregate_confidence": 0,
                "recommendation": "No evidence collected yet",
                "suggested_zone": "YELLOW"
            }

        total_confidence = sum(
            e.get("rigor_assessment", {}).get("overall_confidence", 0)
            for e in evidence
        )
        avg_confidence = total_confidence / len(evidence)

        total_sample = sum(e.get("sample_size", 0) for e in evidence)

        methodologies = list(set(e.get("methodology") for e in evidence))

        # v3.0.2: Count zone suggestions
        zone_votes = {"GREEN": 0, "YELLOW": 0, "RED": 0}
        for e in evidence:
            zone = e.get("rigor_assessment", {}).get("suggested_zone", "YELLOW")
            zone_votes[zone] = zone_votes.get(zone, 0) + 1

        suggested_zone = max(zone_votes, key=zone_votes.get) if evidence else "YELLOW"

        return {
            "evidence_count": len(evidence),
            "total_sample_size": total_sample,
            "methodologies_used": methodologies,
            "aggregate_confidence": round(avg_confidence, 2),
            "confidence_level": "HIGH" if avg_confidence >= 0.7 else "MEDIUM" if avg_confidence >= 0.4 else "LOW",
            "suggested_zone": suggested_zone,  # v3.0.2
            "zone_distribution": zone_votes,    # v3.0.2
            "evidence_items": [
                {
                    "evidence_id": e.get("evidence_id"),
                    "methodology": e.get("methodology"),
                    "sample_size": e.get("sample_size"),
                    "confidence": e.get("rigor_assessment", {}).get("overall_confidence", 0),
                    "date": e.get("collection_date"),
                    "experiment_id": e.get("experiment_id"),
                    "suggested_zone": e.get("rigor_assessment", {}).get("suggested_zone")
                }
                for e in evidence
            ]
        }

    def display_on_shared_pursuit(self, pursuit_id: str) -> List[Dict]:
        """
        Format risk validation for stakeholders viewing shared pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of risks with validation status for display
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        display_data = []
        for risk in risks:
            evidence_summary = self.get_risk_evidence_summary(risk.get("risk_id"))

            # v3.0.2: Use three-zone colors
            zone = risk.get("zone") or evidence_summary.get("suggested_zone", "YELLOW")
            zone_colors = {
                "GREEN": "green",
                "YELLOW": "yellow",
                "RED": "red"
            }

            display_data.append({
                "risk": risk.get("risk_parameter", "")[:100],
                "category": risk.get("risk_category"),
                "priority": risk.get("validation_priority"),
                "evidence_count": evidence_summary.get("evidence_count", 0),
                "confidence": evidence_summary.get("aggregate_confidence", 0),
                "status": risk.get("validation_status", "NOT_STARTED"),
                "zone": zone,  # v3.0.2
                "status_color": zone_colors.get(zone, "yellow")
            })

        return display_data
