"""
InDE MVP v2.3 - Teleological Assessor

Analyzes pursuit along 8 teleological dimensions to enable invisible methodology selection.

This class NEVER exposes methodology names to users. It's internal orchestration logic.
The teleological profile determines which question bank to use for coaching,
providing goal-oriented guidance without methodology jargon.

Teleological Dimensions:
1. purpose_type - What kind of goal? (problem_solving, opportunity_creation, compliance, process_improvement)
2. beneficiary - Who benefits? (end_users, market, organization, society)
3. uncertainty_level - How much is unknown? (0.0-1.0)
4. value_creation_mode - What value type? (efficiency, experience, safety, knowledge)
5. resource_context - What constraints? (time/capital/expertise)
6. org_context - What setting? (startup, enterprise, public_sector, academic)
7. innovation_type - What scope? (incremental, architectural, radical, disruptive)
8. maturity_state - What stage? (spark, hypothesis, validated, scaling)

Question Banks:
- exploratory: High uncertainty, early stage
- validation: Known problem, testing solution
- scaling: Validated solution, growth phase
- technical: Engineering constraints dominant
- social_impact: Society beneficiary focus
"""

from typing import Dict, Optional


class TeleologicalAssessor:
    """
    Analyzes pursuit teleology for invisible methodology inference.

    This is internal orchestration - users never see methodology names.
    """

    def __init__(self, element_tracker, database):
        """
        Initialize TeleologicalAssessor.

        Args:
            element_tracker: ElementTracker instance for profile extraction
            database: Database instance for caching profiles
        """
        self.element_tracker = element_tracker
        self.db = database

    def assess_pursuit(self, pursuit_id: str) -> Dict:
        """
        Assess pursuit teleology and determine coaching approach.

        Returns:
            {
                "teleological_profile": {
                    "purpose_type": "problem_solving",
                    "beneficiary": "end_users",
                    "uncertainty_level": 0.7,
                    "value_creation_mode": "safety",
                    "resource_context": "time_constrained",
                    "org_context": "startup",
                    "innovation_type": "architectural",
                    "maturity_state": "hypothesis"
                },
                "_inferred_methodology": "LEAN_STARTUP",  # Internal only
                "confidence": 0.85,
                "question_bank": "validation"
            }
        """
        print(f"[TeleologicalAssessor] Assessing pursuit: {pursuit_id}")

        # Get teleological profile from ElementTracker
        tele_profile = self.element_tracker.get_teleological_profile(pursuit_id)

        # Infer methodology based on profile (v2.3: always LEAN_STARTUP as foundation)
        methodology = self._infer_methodology(tele_profile)

        # Select appropriate question bank
        question_bank = self._select_question_bank(tele_profile, methodology)

        # Calculate assessment confidence
        confidence = self._calculate_confidence(tele_profile)

        assessment = {
            "teleological_profile": tele_profile,
            "_inferred_methodology": methodology,  # Underscore = internal only
            "confidence": confidence,
            "question_bank": question_bank
        }

        print(f"[TeleologicalAssessor] Assessment complete: bank={question_bank}, confidence={confidence:.2f}")
        return assessment

    def _infer_methodology(self, profile: Dict) -> str:
        """
        Map teleological profile to methodology.

        For v2.3: Default to LEAN_STARTUP (single methodology foundation)
        For v2.4: Multi-methodology logic (DT, LS, SG, TRIZ)

        The methodology is NEVER shown to users - it's internal orchestration.
        """
        # Get values with safe defaults
        uncertainty = profile.get("uncertainty_level")
        if uncertainty is None:
            uncertainty = 0.5

        beneficiary = profile.get("beneficiary") or "unknown"
        maturity = profile.get("maturity_state") or "spark"
        purpose = profile.get("purpose_type") or "unknown"

        # v2.3: Foundation logic for future multi-methodology
        # High uncertainty + end-user focus hints at Design Thinking vibes
        # Low uncertainty + market focus hints at Lean Startup vibes
        # But for v2.3, all return LEAN_STARTUP as the foundation

        # This logic is ready for v2.4 expansion:
        # if uncertainty > 0.7 and beneficiary == "end_users":
        #     return "DESIGN_THINKING"
        # elif purpose == "process_improvement":
        #     return "SIX_SIGMA"
        # elif innovation_type == "radical":
        #     return "TRIZ"

        return "LEAN_STARTUP"

    def _select_question_bank(self, profile: Dict, methodology: str) -> str:
        """
        Select question bank based on teleological profile.

        Question banks provide coaching questions tailored to the pursuit's
        context WITHOUT exposing methodology terminology.

        Banks:
        - exploratory: High uncertainty, early stage, discovery-focused
        - validation: Medium uncertainty, testing assumptions
        - scaling: Low uncertainty, growth-focused
        - technical: Engineering/compliance constraints dominant
        - social_impact: Society/community beneficiary focus
        """
        # Get values with safe defaults
        uncertainty = profile.get("uncertainty_level")
        if uncertainty is None:
            uncertainty = 0.5  # Default neutral uncertainty

        maturity = profile.get("maturity_state") or "spark"
        beneficiary = profile.get("beneficiary") or "end_users"
        purpose = profile.get("purpose_type") or "problem_solving"

        # Social impact takes priority for society beneficiaries
        if beneficiary == "society":
            return "social_impact"

        # Technical bank for compliance or process improvement
        if purpose in ["compliance", "process_improvement"]:
            return "technical"

        # Maturity and uncertainty determine remaining banks
        if maturity in ["spark", "hypothesis"] and uncertainty > 0.5:
            return "exploratory"
        elif maturity == "validated" or uncertainty < 0.3:
            return "scaling"
        elif maturity == "scaling":
            return "scaling"
        else:
            return "validation"  # Default middle ground

    def _calculate_confidence(self, profile: Dict) -> float:
        """
        Calculate confidence in the teleological assessment.

        Higher confidence = more dimensions detected = better coaching alignment.
        """
        # Use profile's own confidence if available
        if "confidence" in profile:
            return profile["confidence"]

        # Fallback: count non-None dimensions
        dimension_keys = [
            "purpose_type", "beneficiary", "uncertainty_level",
            "value_creation_mode", "resource_context", "org_context",
            "innovation_type", "maturity_state"
        ]
        valid_dims = sum(1 for k in dimension_keys if profile.get(k) is not None)
        return valid_dims / len(dimension_keys)

    def get_coaching_context(self, pursuit_id: str) -> Dict:
        """
        Get full coaching context including assessment and element completeness.

        Used by ScaffoldingEngine to inform coaching response generation.
        """
        assessment = self.assess_pursuit(pursuit_id)
        completeness = self.element_tracker.get_48_element_completeness(pursuit_id)

        return {
            "assessment": assessment,
            "completeness": completeness,
            "question_bank": assessment["question_bank"],
            "coaching_style": self._get_coaching_style(assessment["question_bank"])
        }

    def _get_coaching_style(self, question_bank: str) -> Dict:
        """
        Get coaching style guidance for a question bank.

        This provides tone and emphasis guidance for LLM response generation.
        """
        styles = {
            "exploratory": {
                "tone": "curious, open-ended, hypothesis-generating",
                "emphasis": ["user understanding", "problem validation", "assumption surfacing"],
                "avoid": ["methodology jargon", "process terminology", "premature solutions"]
            },
            "validation": {
                "tone": "pragmatic, evidence-oriented, focused on learning",
                "emphasis": ["testability", "quick experiments", "user feedback"],
                "avoid": ["premature scaling", "perfect solution thinking"]
            },
            "scaling": {
                "tone": "strategic, growth-focused, optimization-oriented",
                "emphasis": ["metrics", "repeatability", "efficiency"],
                "avoid": ["over-experimentation", "unnecessary pivots"]
            },
            "technical": {
                "tone": "precise, systematic, constraint-aware",
                "emphasis": ["feasibility", "requirements", "risk mitigation"],
                "avoid": ["vague aspirations", "ignoring constraints"]
            },
            "social_impact": {
                "tone": "empathetic, community-focused, outcome-oriented",
                "emphasis": ["stakeholder needs", "sustainability", "systemic change"],
                "avoid": ["profit-first thinking", "ignoring unintended consequences"]
            }
        }
        return styles.get(question_bank, styles["validation"])

    def should_reassess(self, pursuit_id: str, turns_since_assessment: int = 5) -> bool:
        """
        Determine if teleological profile should be re-assessed.

        Profiles should be refreshed periodically as conversation reveals more context.
        """
        # Reassess every 5 conversation turns or if confidence is low
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return True

        profile = state.get("teleological_profile", {})
        confidence = profile.get("confidence", 0)

        # Low confidence = reassess more frequently
        if confidence < 0.5:
            return turns_since_assessment >= 3

        return turns_since_assessment >= 5
