"""
InDE EMS v3.7.2 - ADL (Archetype Definition Language) Generator

Transforms pattern inference results into methodology archetypes
compatible with InDE's existing archetype infrastructure.

ADL Format:
The generated archetype follows the EXACT same structure as pre-built
methodology archetypes (TRIZ, Lean Startup, etc.) ensuring full
compatibility with the scaffolding engine and coaching system.

Key outputs:
- Archetype definition matching hand-authored format
- Phase structure with universal_state and transition_criteria
- coaching_config with language_style, framing, backward_iteration
- Provenance metadata for EMS-synthesized archetypes
- draft: true flag to prevent premature publication
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import re

from ems.pattern_inference import PatternInferenceEngine, get_pattern_inference_engine

logger = logging.getLogger("inde.ems.adl_generator")


# Universal Innovation States mapping
UNIVERSAL_STATES = {
    "early": "DISCOVERY",
    "middle": "DEFINITION_VALIDATION",
    "late": "PREPARATION",
}

# Extended state mapping for more granular phases
UNIVERSAL_STATE_EXTENDED = {
    "ideation": "DISCOVERY",
    "research": "DISCOVERY",
    "exploration": "DISCOVERY",
    "problem": "DISCOVERY",
    "validation": "VALIDATION_REFINEMENT",
    "testing": "VALIDATION_REFINEMENT",
    "feedback": "DEFINITION_VALIDATION",
    "refinement": "REFINEMENT",
    "implementation": "PREPARATION",
    "building": "PREPARATION",
    "deployment": "PREPARATION",
    "launch": "PREPARATION",
}

# Transition criteria type mappings
TRANSITION_CRITERIA_TYPES = [
    "ARTIFACT_EXISTS",
    "ARTIFACT_COMPLETE",
    "VALIDATION",
    "COACH_CHECKPOINT",
    "TIME_INVESTMENT",
    "CUSTOM",
]


class ADLGenerator:
    """
    Generates methodology archetypes from inferred patterns.

    Transforms PatternInferenceEngine output into archetype definitions
    that are FULLY COMPATIBLE with hand-authored archetypes like TRIZ,
    Lean Startup, Design Thinking, etc.
    """

    # ADL schema version
    ADL_VERSION = "1.0"

    # Archetype naming prefix for emergent methodologies
    ARCHETYPE_PREFIX = "emergent"

    # Required fields for ADL compatibility
    REQUIRED_TOP_LEVEL_FIELDS = [
        "id", "name", "version", "description", "transition_philosophy",
        "criteria_enforcement", "backward_iteration", "phases", "coaching_config"
    ]

    REQUIRED_PHASE_FIELDS = [
        "name", "universal_state", "description", "activities", "transition_criteria"
    ]

    def __init__(self, inference_engine: Optional[PatternInferenceEngine] = None):
        """
        Args:
            inference_engine: PatternInferenceEngine for pattern data.
                            If None, uses singleton.
        """
        self.engine = inference_engine or get_pattern_inference_engine()

    def generate_archetype(
        self,
        innovator_id: str,
        inference_result: Optional[Dict] = None,
        archetype_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a methodology archetype from inference results.

        The generated archetype is FULLY COMPATIBLE with hand-authored
        archetypes, containing all required fields in the correct structure.

        Args:
            innovator_id: The innovator whose patterns to use
            inference_result: Pre-computed inference result (optional)
            archetype_name: Custom name for archetype (optional)

        Returns:
            Complete archetype definition matching hand-authored format,
            wrapped in ADL metadata envelope.
        """
        # Get or compute inference result
        if inference_result is None:
            inference_result = self.engine.infer_patterns(innovator_id)

        if not inference_result.get("synthesis_ready", False):
            logger.warning(
                f"Inference not ready for synthesis: "
                f"confidence={inference_result.get('confidence', {}).get('overall', 0)}"
            )
            return self._generate_insufficient_data_response(
                innovator_id, inference_result
            )

        # Generate archetype ID (slugified)
        archetype_id = self._generate_archetype_id(innovator_id)

        # Determine archetype display name
        if archetype_name is None:
            display_name = self._infer_archetype_name(inference_result)
        else:
            display_name = archetype_name

        # Generate timestamp
        generated_at = datetime.now(timezone.utc)

        # Build the archetype in hand-authored compatible format
        archetype = self._build_compatible_archetype(
            archetype_id, display_name, inference_result, generated_at
        )

        # Validate ADL compatibility
        validation_result = self.validate_adl_compatibility(archetype)

        result = {
            "archetype_id": archetype_id,
            "adl_version": self.ADL_VERSION,
            "generated_at": generated_at.isoformat(),
            "source": {
                "innovator_id": innovator_id,
                "pursuit_count": inference_result.get("pursuit_count", 0),
                "confidence": inference_result.get("confidence", {}),
            },
            "archetype": archetype,
            "validation": validation_result,
            "synthesis_metadata": {
                "pattern_count": self._count_patterns(inference_result),
                "algorithm_versions": {
                    "sequence_mining": "1.0",
                    "phase_clustering": "1.0",
                    "transition_inference": "1.0",
                    "dependency_mapping": "1.0",
                },
            },
        }

        logger.info(
            f"Generated ADL archetype {archetype_id} for innovator {innovator_id} "
            f"(valid={validation_result['valid']})"
        )

        return result

    def _build_compatible_archetype(
        self,
        archetype_id: str,
        display_name: str,
        inference_result: Dict,
        generated_at: datetime
    ) -> Dict[str, Any]:
        """
        Build archetype in format compatible with hand-authored archetypes.

        This method produces output matching TRIZ, Lean Startup, etc.
        """
        patterns = inference_result.get("patterns", {})
        confidence = inference_result.get("confidence", {})
        pursuit_count = inference_result.get("pursuit_count", 0)

        # Build phases with full structure
        phases = self._build_compatible_phases(
            patterns.get("phases", []),
            patterns.get("transitions", [])
        )

        # Build coaching config
        coaching_config = self._build_coaching_config(patterns, phases)

        # Build convergence config
        convergence_config = self._build_convergence_config(confidence)

        # Build retrospective template
        retrospective_template = self._build_retrospective_template(phases)

        # Build metadata
        metadata = self._build_metadata(confidence, pursuit_count, generated_at)

        # Build provenance (EMS-specific)
        provenance = {
            "source": "EMS",
            "version": "3.7.2",
            "confidence": confidence.get("overall", 0),
            "source_pursuit_count": pursuit_count,
            "inference_date": generated_at.isoformat(),
        }

        archetype = {
            # Required top-level fields (matching hand-authored)
            "id": archetype_id,
            "name": display_name,
            "version": "1.0",
            "description": self._generate_description(display_name, phases, confidence),
            "central_question": self._infer_central_question(phases),
            "origin": f"Synthesized by EMS from {pursuit_count} ad-hoc pursuits",

            # Transition and enforcement philosophy
            "transition_philosophy": "fluid",  # Emergent methodologies are fluid
            "criteria_enforcement": "advisory",  # Non-directive by default
            "backward_iteration": "revisit_as_needed",

            # Draft flag - CRITICAL for preventing premature publication
            "draft": True,

            # Phases with full structure
            "phases": phases,

            # Coaching configuration
            "coaching_config": coaching_config,

            # Convergence protocol
            "convergence_config": convergence_config,

            # Retrospective template
            "retrospective_template": retrospective_template,

            # Metadata
            "metadata": metadata,

            # EMS-specific provenance
            "provenance": provenance,
        }

        return archetype

    def _build_compatible_phases(
        self,
        phase_data: List[Dict],
        transition_data: List[Dict]
    ) -> List[Dict]:
        """
        Build phases with structure matching hand-authored archetypes.

        Each phase includes:
        - name
        - universal_state
        - description
        - activities
        - key_artifacts
        - transition_criteria
        - coaching_focus
        """
        phases = []

        # Build transition map for quick lookup
        transition_map = self._build_transition_map(transition_data)

        for i, phase in enumerate(phase_data):
            phase_id = phase.get("phase_id", f"phase_{i}")
            name = phase.get("name", f"Phase {i + 1}")
            position = phase.get("position", "middle")
            activities = phase.get("typical_activities", [])

            # Map to Universal Innovation State
            universal_state = self._map_to_universal_state(name, position)

            # Build transition criteria from inferred transitions
            transition_criteria = self._build_transition_criteria(
                phase_id, transition_map
            )

            # Extract key artifacts from activities
            key_artifacts = self._extract_phase_artifacts(activities)

            phases.append({
                "name": name,
                "universal_state": universal_state,
                "description": self._generate_phase_description(phase),
                "activities": self._normalize_activities(activities),
                "key_artifacts": key_artifacts,
                "transition_criteria": transition_criteria,
                "coaching_focus": self._generate_coaching_focus(name, activities),
            })

        return phases

    def _map_to_universal_state(self, phase_name: str, position: str) -> str:
        """
        Map phase to Universal Innovation State.

        Uses phase name keywords first, falls back to position.
        """
        name_lower = phase_name.lower()

        # Check for keyword matches
        for keyword, state in UNIVERSAL_STATE_EXTENDED.items():
            if keyword in name_lower:
                return state

        # Fall back to position-based mapping
        return UNIVERSAL_STATES.get(position, "DEFINITION_VALIDATION")

    def _build_transition_map(self, transition_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Build map of phase_id -> transitions from that phase."""
        transition_map = {}
        for trans in transition_data:
            from_phase = trans.get("from_phase", "")
            if from_phase not in transition_map:
                transition_map[from_phase] = []
            transition_map[from_phase].append(trans)
        return transition_map

    def _build_transition_criteria(
        self,
        phase_id: str,
        transition_map: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Build transition criteria matching hand-authored format.

        Transition criteria have:
        - id: unique identifier
        - type: one of TRANSITION_CRITERIA_TYPES
        - description: human-readable description
        - required: whether this is mandatory
        """
        criteria = []
        transitions = transition_map.get(phase_id, [])

        for i, trans in enumerate(transitions):
            # Add criteria for trigger artifacts
            for artifact in trans.get("trigger_artifacts", []):
                artifact_name = artifact.split(":")[-1] if ":" in artifact else artifact
                criteria.append({
                    "id": f"tc_{phase_id}_{i}_artifact",
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": f".{artifact_name}",
                    "description": f"{artifact_name.replace('_', ' ').title()} created",
                    "required": True,
                })

            # Add criteria for trigger activities (as validation checkpoints)
            for activity in trans.get("trigger_activities", []):
                activity_name = activity.replace("_", " ").title()
                criteria.append({
                    "id": f"tc_{phase_id}_{i}_validation",
                    "type": "VALIDATION",
                    "description": f"{activity_name} completed",
                    "required": True,
                })

        # Always include a coach checkpoint as optional
        if not criteria:
            criteria.append({
                "id": f"tc_{phase_id}_coach",
                "type": "COACH_CHECKPOINT",
                "description": "Ready to progress to next phase",
                "required": False,
            })

        return criteria

    def _extract_phase_artifacts(self, activities: List[str]) -> List[str]:
        """Extract artifact references from activity list."""
        artifacts = []
        for activity in activities:
            if "ARTIFACT" in activity.upper():
                # Extract artifact type
                parts = activity.split(":")
                if len(parts) > 1:
                    artifacts.append(f".{parts[-1]}")
        return artifacts if artifacts else [".phase_output"]

    def _normalize_activities(self, activities: List[str]) -> List[str]:
        """Normalize activity names to simple snake_case."""
        normalized = []
        for activity in activities:
            # Remove enrichment prefixes
            if ":" in activity:
                activity = activity.split(":")[-1]
            # Convert to snake_case
            activity = activity.lower().replace(" ", "_").replace("-", "_")
            # Remove duplicates
            if activity not in normalized:
                normalized.append(activity)
        return normalized

    def _generate_coaching_focus(self, phase_name: str, activities: List[str]) -> str:
        """Generate coaching focus guidance for a phase."""
        activity_str = ", ".join(self._normalize_activities(activities)[:3])
        return (
            f"Support the innovator through {phase_name.lower()} by encouraging "
            f"reflection on their natural approach. Key activities observed: "
            f"{activity_str}. Use non-directive questions to help them recognize "
            f"patterns in their own process."
        )

    def _build_coaching_config(
        self,
        patterns: Dict,
        phases: List[Dict]
    ) -> Dict[str, Any]:
        """
        Build coaching_config matching hand-authored format.

        Includes:
        - language_style
        - framing
        - backward_iteration
        - key_questions
        - common_pitfalls
        - convergence_moments
        """
        # Generate key questions from phases
        key_questions = []
        for phase in phases:
            phase_name = phase.get("name", "this phase")
            key_questions.append(
                f"What activities feel most natural to you during {phase_name.lower()}?"
            )
        key_questions.append("What patterns do you notice in how you approach innovation?")
        key_questions.append("When do you feel most productive in your process?")

        # Generate common pitfalls
        common_pitfalls = [
            "forcing_prescribed_methodology_over_natural_flow",
            "skipping_reflection_on_what_works",
            "ignoring_intuitive_process_preferences",
        ]

        # Generate convergence moments from transitions
        convergence_moments = []
        for trans in patterns.get("transitions", []):
            from_phase = trans.get("from_phase", "")
            to_phase = trans.get("to_phase", "")
            if from_phase and to_phase:
                convergence_moments.append(f"transition_{from_phase}_to_{to_phase}")

        return {
            "language_style": "exploratory_reflective",
            "framing": "emergence_discovery",
            "backward_iteration": "revisit_as_needed",
            "key_questions": key_questions,
            "common_pitfalls": common_pitfalls,
            "convergence_moments": convergence_moments if convergence_moments else [
                "phase_completion",
                "pattern_recognition",
            ],
        }

    def _build_convergence_config(self, confidence: Dict) -> Dict[str, Any]:
        """Build convergence configuration for the archetype."""
        return {
            "min_phases_before_convergence": 1,
            "coach_checkpoint_weight": 0.4,
            "artifact_completion_weight": 0.3,
            "validation_weight": 0.3,
            "allow_phase_skip": True,  # Emergent methodologies are flexible
            "backward_iteration_enabled": True,
        }

    def _build_retrospective_template(self, phases: List[Dict]) -> Dict[str, Any]:
        """Build retrospective template for the archetype."""
        questions = [
            "What patterns did you notice in your natural innovation process?",
            "Which phases felt most comfortable? Which were challenging?",
            "Were there activities you found yourself returning to frequently?",
            "What would you do differently next time?",
            "Did any unexpected insights emerge from your approach?",
        ]

        metrics_to_capture = [
            "phases_completed",
            "natural_flow_observed",
            "iteration_patterns",
            "time_per_phase",
        ]

        return {
            "questions": questions,
            "metrics_to_capture": metrics_to_capture,
        }

    def _build_metadata(
        self,
        confidence: Dict,
        pursuit_count: int,
        generated_at: datetime
    ) -> Dict[str, Any]:
        """Build metadata section for the archetype."""
        confidence_level = confidence.get("overall", 0)
        confidence_tier = (
            "high" if confidence_level >= 0.7 else
            "moderate" if confidence_level >= 0.5 else
            "emerging"
        )

        return {
            "added_version": "3.7.2",
            "synthesis_date": generated_at.strftime("%Y-%m-%d"),
            "confidence_tier": confidence_tier,
            "source_pursuits": pursuit_count,
            "best_for": [
                "Innovators who prefer organic process discovery",
                "Situations where prescribed methodologies feel constraining",
                "Building on natural innovation instincts",
            ],
            "less_suited_for": [
                "Highly regulated environments requiring specific methodologies",
                "Team contexts requiring shared process vocabulary",
            ],
        }

    def _generate_archetype_id(self, innovator_id: str) -> str:
        """Generate unique archetype ID (slugified)."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        hash_input = f"{innovator_id}:{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{self.ARCHETYPE_PREFIX}_{hash_suffix}"

    def _infer_archetype_name(self, inference_result: Dict) -> str:
        """Infer a descriptive display name from patterns."""
        patterns = inference_result.get("patterns", {})
        phases = patterns.get("phases", [])

        if not phases:
            return "Emergent Methodology"

        # Build name from dominant phases
        phase_names = [p.get("name", "Unknown") for p in phases[:3]]

        if len(phase_names) == 1:
            return f"{phase_names[0]}-Focused Approach"
        elif len(phase_names) == 2:
            return f"{phase_names[0]}-to-{phase_names[1]} Process"
        else:
            return f"{phase_names[0]}-{phase_names[1]}-{phase_names[2]} Methodology"

    def _infer_central_question(self, phases: List[Dict]) -> str:
        """Infer a central question from the phase structure."""
        if not phases:
            return "How do I approach innovation naturally?"

        first_phase = phases[0].get("name", "").lower()
        last_phase = phases[-1].get("name", "").lower() if len(phases) > 1 else ""

        if "idea" in first_phase or "discovery" in first_phase:
            return "How do I move from initial idea to concrete outcome?"
        elif "valid" in last_phase or "test" in last_phase:
            return "How do I validate my innovation approach?"
        else:
            return "What is my natural path through innovation?"

    def _generate_description(
        self,
        name: str,
        phases: List[Dict],
        confidence: Dict
    ) -> str:
        """Generate archetype description."""
        phase_count = len(phases)
        confidence_level = confidence.get("overall", 0)

        confidence_str = (
            "high" if confidence_level >= 0.7 else
            "moderate" if confidence_level >= 0.5 else
            "emerging"
        )

        return (
            f"{name} is an emergent methodology synthesized from observed "
            f"innovator behavior. It consists of {phase_count} distinct phases "
            f"with {confidence_str} confidence ({confidence_level:.0%}) based on "
            f"pattern analysis across multiple pursuits. This methodology reflects "
            f"your natural innovation approach rather than a prescribed process."
        )

    def _generate_phase_description(self, phase: Dict) -> str:
        """Generate a human-readable phase description."""
        activities = phase.get("typical_activities", [])
        position = phase.get("position", "middle")
        name = phase.get("name", "this phase")

        if not activities:
            return f"A {position} phase in your natural process."

        # Simplify activity names for description
        simple_activities = []
        for act in activities[:3]:
            # Extract base type (remove enrichment suffix)
            base = act.split(":")[0] if ":" in act else act
            base = base.replace("_", " ").lower()
            simple_activities.append(base)

        activity_str = ", ".join(simple_activities)
        return (
            f"{name} is a {position} phase in your methodology, "
            f"characterized by {activity_str} activities."
        )

    def _count_patterns(self, inference_result: Dict) -> int:
        """Count total patterns discovered."""
        patterns = inference_result.get("patterns", {})
        return (
            len(patterns.get("sequences", [])) +
            len(patterns.get("phases", [])) +
            len(patterns.get("transitions", [])) +
            len(patterns.get("dependencies", []))
        )

    def validate_adl_compatibility(self, archetype: Dict) -> Dict[str, Any]:
        """
        Validate that the generated archetype is compatible with hand-authored format.

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []

        # Check required top-level fields
        for field in self.REQUIRED_TOP_LEVEL_FIELDS:
            if field not in archetype:
                errors.append(f"Missing required top-level field: {field}")
            elif archetype[field] is None:
                errors.append(f"Required field is None: {field}")

        # Check draft flag
        if not archetype.get("draft"):
            warnings.append("draft flag should be True for synthesized archetypes")

        # Check phases structure
        phases = archetype.get("phases", [])
        if not phases:
            errors.append("No phases defined")
        else:
            for i, phase in enumerate(phases):
                for field in self.REQUIRED_PHASE_FIELDS:
                    if field not in phase:
                        errors.append(f"Phase {i} missing required field: {field}")

                # Check universal_state is valid
                universal_state = phase.get("universal_state", "")
                valid_states = list(UNIVERSAL_STATES.values()) + list(UNIVERSAL_STATE_EXTENDED.values())
                if universal_state and universal_state not in valid_states:
                    warnings.append(
                        f"Phase {i} universal_state '{universal_state}' may not be recognized"
                    )

                # Check transition_criteria structure
                criteria = phase.get("transition_criteria", [])
                for j, criterion in enumerate(criteria):
                    if "type" not in criterion:
                        errors.append(f"Phase {i} criterion {j} missing 'type'")
                    elif criterion["type"] not in TRANSITION_CRITERIA_TYPES:
                        warnings.append(
                            f"Phase {i} criterion {j} type '{criterion['type']}' not standard"
                        )

        # Check coaching_config structure
        coaching_config = archetype.get("coaching_config", {})
        required_coaching_fields = ["language_style", "framing", "backward_iteration"]
        for field in required_coaching_fields:
            if field not in coaching_config:
                errors.append(f"coaching_config missing required field: {field}")

        # Check provenance for EMS archetypes
        provenance = archetype.get("provenance", {})
        if provenance.get("source") != "EMS":
            warnings.append("provenance.source should be 'EMS' for synthesized archetypes")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _generate_insufficient_data_response(
        self,
        innovator_id: str,
        inference_result: Dict
    ) -> Dict[str, Any]:
        """Generate response when insufficient data for synthesis."""
        return {
            "archetype_id": None,
            "adl_version": self.ADL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "innovator_id": innovator_id,
                "pursuit_count": inference_result.get("pursuit_count", 0),
                "confidence": inference_result.get("confidence", {}),
            },
            "archetype": None,
            "validation": {
                "valid": False,
                "errors": ["Insufficient data for synthesis"],
                "warnings": [],
            },
            "synthesis_metadata": {
                "status": "insufficient_data",
                "reason": self._get_insufficiency_reason(inference_result),
                "requirements": {
                    "min_pursuits": 3,
                    "min_confidence": 0.5,
                    "min_sequences": 2,
                    "min_phases": 2,
                },
            },
        }

    def _get_insufficiency_reason(self, inference_result: Dict) -> str:
        """Determine why synthesis is not ready."""
        reasons = []

        pursuit_count = inference_result.get("pursuit_count", 0)
        if pursuit_count < 3:
            reasons.append(f"Only {pursuit_count} pursuits (need 3+)")

        confidence = inference_result.get("confidence", {}).get("overall", 0)
        if confidence < 0.5:
            reasons.append(f"Low confidence ({confidence:.0%})")

        patterns = inference_result.get("patterns", {})
        if len(patterns.get("sequences", [])) < 2:
            reasons.append("Insufficient recurring sequences")
        if len(patterns.get("phases", [])) < 2:
            reasons.append("Insufficient distinct phases")

        return "; ".join(reasons) if reasons else "Unknown"


# Singleton instance
_adl_generator_instance = None


def get_adl_generator() -> ADLGenerator:
    """Get or create the ADLGenerator singleton."""
    global _adl_generator_instance
    if _adl_generator_instance is None:
        _adl_generator_instance = ADLGenerator()
    return _adl_generator_instance


def validate_adl_compatibility(archetype: Dict) -> Dict[str, Any]:
    """
    Standalone function to validate ADL compatibility.

    This function can be called without instantiating ADLGenerator.
    """
    generator = get_adl_generator()
    return generator.validate_adl_compatibility(archetype)
