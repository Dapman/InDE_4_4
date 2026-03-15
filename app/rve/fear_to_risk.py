"""
InDE MVP v3.0.2 - Fear-to-Risk Converter
Convert subjective fears into measurable risk parameters.

Migrated from rve_lite/ and enhanced with:
- Integration with experiment wizard
- Three-zone assessment compatibility
- Improved risk categorization
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from config import (
    RISK_CATEGORIES, RISK_PRIORITIES, VALIDATION_STATES,
    FEAR_TO_RISK_PROMPT, RVE_CONFIG
)


class FearToRiskConverter:
    """
    Convert subjective fears into measurable risk definitions.

    Guides innovators through defining specific metrics and thresholds
    that would indicate a fear is materializing.

    v3.0.2: Enhanced with experiment suggestion and three-zone compatibility.
    """

    def __init__(self, db, llm=None):
        """
        Initialize the converter.

        Args:
            db: Database instance
            llm: Optional LLM interface for guided conversion
        """
        self.db = db
        self.llm = llm
        self.config = RVE_CONFIG

    def convert_fear_to_risk(self, fear_id: str, pursuit_id: str,
                              conversational_context: str = None) -> Dict:
        """
        ODICM-guided conversion of fear to risk.

        Args:
            fear_id: ID of the fear artifact to convert
            pursuit_id: ID of the pursuit
            conversational_context: Recent conversation for context

        Returns:
            Dict with risk_id and extraction details
        """
        # Get the fear artifact
        fear_artifact = self.db.get_artifact(fear_id)
        if not fear_artifact:
            raise ValueError(f"Fear artifact not found: {fear_id}")

        fear_content = fear_artifact.get("content", "")

        # Get pursuit context
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError(f"Pursuit not found: {pursuit_id}")

        # Get vision summary for context
        vision_artifacts = self.db.get_pursuit_artifacts(pursuit_id, artifact_type="vision")
        vision_summary = ""
        if vision_artifacts:
            vision_summary = vision_artifacts[0].get("content", "")[:500]

        # Use LLM for guided extraction if available
        if self.llm:
            extraction = self._llm_extract_risk_parameters(
                fear_content=fear_content,
                pursuit_title=pursuit.get("title", ""),
                vision_summary=vision_summary,
                conversational_context=conversational_context
            )
        else:
            # Default extraction without LLM
            extraction = self._default_extract_risk_parameters(fear_content)

        # Create risk definition with v3.0.2 enhanced fields
        risk_record = {
            "pursuit_id": pursuit_id,
            "source_fear_id": fear_id,
            "risk_parameter": extraction.get("risk_parameter", ""),
            "acceptable_threshold": extraction.get("acceptable_threshold", ""),
            "current_validation_state": "ASSUMPTION",
            "risk_category": extraction.get("category", "MARKET"),
            "validation_priority": extraction.get("priority", "MEDIUM"),
            "impact_if_unmitigated": extraction.get("impact_if_unmitigated", ""),
            "suggested_validation_method": extraction.get("suggested_validation_method", ""),
            "validation_status": "NOT_STARTED",
            # v3.0.2: Enhanced fields
            "suggested_experiment_type": extraction.get("suggested_experiment_type"),
            "zone": None,  # Will be set by three-zone assessment
            "requires_experiment": True,  # Default to true
            "experiment_ids": []
        }

        risk_id = self.db.create_risk_definition(risk_record)

        # Create .risk artifact
        artifact_content = self._generate_risk_artifact_content(
            pursuit.get("title", ""),
            risk_record
        )

        artifact = self.db.create_artifact(
            pursuit_id=pursuit_id,
            artifact_type="risk",
            content=artifact_content,
            elements_used=["source_fear"],
            completeness=1.0,
            generation_method="fear_conversion"
        )

        # Update risk record with artifact link
        self.db.update_risk_definition(risk_id, {
            "artifact_id": artifact.get("artifact_id")
        })

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="risk_defined",
            description=f"Converted fear to measurable risk: {extraction.get('risk_parameter', '')[:50]}",
            metadata={
                "risk_id": risk_id,
                "source_fear_id": fear_id,
                "category": extraction.get("category")
            }
        )

        # v3.0.2: Update RVE status
        self._update_pursuit_rve_status(pursuit_id)

        return {
            "risk_id": risk_id,
            "artifact_id": artifact.get("artifact_id"),
            "risk_parameter": extraction.get("risk_parameter"),
            "threshold": extraction.get("acceptable_threshold"),
            "category": extraction.get("category"),
            "priority": extraction.get("priority"),
            "suggested_experiment_type": extraction.get("suggested_experiment_type")
        }

    def _update_pursuit_rve_status(self, pursuit_id: str) -> None:
        """v3.0.2: Update pursuit's RVE status after risk creation."""
        current_status = self.db.get_pursuit_rve_status(pursuit_id)
        if not current_status:
            current_status = {"enabled": True}

        current_status["enabled"] = True
        current_status["total_risks_identified"] = current_status.get("total_risks_identified", 0) + 1

        self.db.update_pursuit_rve_status(pursuit_id, current_status)

    def _llm_extract_risk_parameters(self, fear_content: str, pursuit_title: str,
                                       vision_summary: str,
                                       conversational_context: str = None) -> Dict:
        """Use LLM to extract risk parameters from fear."""
        prompt = FEAR_TO_RISK_PROMPT.format(
            fear_content=fear_content,
            pursuit_title=pursuit_title,
            vision_summary=vision_summary[:300] if vision_summary else "Not yet defined"
        )

        try:
            response = self.llm.generate(prompt, max_tokens=500)
            return self._parse_llm_response(response)
        except Exception as e:
            print(f"[FearToRisk] LLM extraction failed: {e}")
            return self._default_extract_risk_parameters(fear_content)

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract risk parameters."""
        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fallback: try to extract key fields
        return self._default_extract_risk_parameters(response)

    def _default_extract_risk_parameters(self, fear_content: str) -> Dict:
        """Default extraction when LLM unavailable."""
        content_lower = fear_content.lower()

        # Determine category based on keywords
        category = "MARKET"
        if any(w in content_lower for w in ["technical", "build", "technology", "engineering"]):
            category = "TECHNICAL"
        elif any(w in content_lower for w in ["resource", "money", "budget", "team", "time"]):
            category = "RESOURCE"
        elif any(w in content_lower for w in ["regulation", "legal", "compliance", "law"]):
            category = "REGULATORY"
        elif any(w in content_lower for w in ["timing", "late", "early", "when", "deadline"]):
            category = "TIMING"

        # Determine priority based on intensity words
        priority = "MEDIUM"
        if any(w in content_lower for w in ["critical", "essential", "must", "fatal", "killer"]):
            priority = "CRITICAL"
        elif any(w in content_lower for w in ["important", "significant", "major"]):
            priority = "HIGH"
        elif any(w in content_lower for w in ["minor", "slight", "small"]):
            priority = "LOW"

        # v3.0.2: Suggest experiment type based on category
        experiment_suggestions = {
            "MARKET": "landing_page_test",
            "TECHNICAL": "technical_feasibility",
            "RESOURCE": "financial_analysis",
            "REGULATORY": "regulatory_review",
            "TIMING": "market_assessment"
        }

        return {
            "risk_parameter": f"Validation of: {fear_content[:100]}",
            "acceptable_threshold": "To be defined through validation",
            "category": category,
            "priority": priority,
            "impact_if_unmitigated": "Could affect pursuit viability",
            "suggested_validation_method": "Customer interviews or market research",
            "suggested_experiment_type": experiment_suggestions.get(category, "user_interviews")
        }

    def _generate_risk_artifact_content(self, pursuit_title: str,
                                         risk_record: Dict) -> str:
        """Generate formatted .risk artifact content."""
        return f"""# Risk Definition: {pursuit_title}

## Risk Parameter
{risk_record.get('risk_parameter', 'Not specified')}

## Acceptable Threshold
{risk_record.get('acceptable_threshold', 'Not specified')}

## Classification
- **Category:** {risk_record.get('risk_category', 'MARKET')}
- **Priority:** {risk_record.get('validation_priority', 'MEDIUM')}
- **Validation State:** {risk_record.get('current_validation_state', 'ASSUMPTION')}

## Impact if Unmitigated
{risk_record.get('impact_if_unmitigated', 'Not assessed')}

## Suggested Validation Method
{risk_record.get('suggested_validation_method', 'To be determined')}

## Suggested Experiment Type
{risk_record.get('suggested_experiment_type', 'To be determined')}

---
*Generated from fear conversion - RVE v3.0.2*
"""

    def get_pursuit_risks(self, pursuit_id: str) -> List[Dict]:
        """
        Get all risk definitions for a pursuit.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            List of risk definitions with status
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        return [
            {
                "risk_id": r.get("risk_id"),
                "risk_parameter": r.get("risk_parameter"),
                "threshold": r.get("acceptable_threshold"),
                "category": r.get("risk_category"),
                "priority": r.get("validation_priority"),
                "validation_status": r.get("validation_status"),
                "evidence_count": len(r.get("linked_evidence", [])),
                "zone": r.get("zone"),  # v3.0.2
                "experiment_count": len(r.get("experiment_ids", []))  # v3.0.2
            }
            for r in risks
        ]

    def get_risk_summary(self, pursuit_id: str) -> Dict:
        """
        Get summary of risks for a pursuit.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            Dict with risk statistics
        """
        risks = self.db.get_pursuit_risks(pursuit_id)

        summary = {
            "total_risks": len(risks),
            "by_category": {},
            "by_priority": {},
            "by_status": {},
            "by_zone": {"GREEN": 0, "YELLOW": 0, "RED": 0, "UNASSESSED": 0},  # v3.0.2
            "critical_unvalidated": 0,
            "needs_experiment": 0  # v3.0.2
        }

        for risk in risks:
            category = risk.get("risk_category", "UNKNOWN")
            priority = risk.get("validation_priority", "UNKNOWN")
            status = risk.get("validation_status", "UNKNOWN")
            zone = risk.get("zone") or "UNASSESSED"

            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            summary["by_zone"][zone] = summary["by_zone"].get(zone, 0) + 1

            if priority == "CRITICAL" and status != "VALIDATED":
                summary["critical_unvalidated"] += 1

            if risk.get("requires_experiment") and not risk.get("experiment_ids"):
                summary["needs_experiment"] += 1

        return summary

    def suggest_conversion_prompt(self, fear_content: str) -> str:
        """
        Generate a coaching prompt to guide fear-to-risk conversion.

        Args:
            fear_content: Content of the fear

        Returns:
            Coaching prompt for ODICM to use
        """
        return (
            f"Let's make this fear more actionable. You mentioned: \"{fear_content[:100]}...\"\n\n"
            f"To convert this into a measurable risk, help me understand:\n"
            f"1. What specific metric or signal would prove this fear is real?\n"
            f"2. What's the minimum acceptable value that would still allow you to proceed?\n\n"
            f"For example, if you fear 'no one will want this', a metric might be "
            f"'At least 5 out of 20 prospects express interest in a pilot.'"
        )
