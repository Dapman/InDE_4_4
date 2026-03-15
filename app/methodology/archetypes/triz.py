"""
TRIZ Archetype Definition

TRIZ (Theory of Inventive Problem Solving) is a systematic methodology
for solving technical contradictions through inventive principles.

Central Question: "How do we solve the impossible?"

This archetype guides innovators through contradiction identification
and resolution using Altshuller's 40 inventive principles, with
integration to biomimicry patterns via the triz_connections field.
"""

from typing import Dict, Any


TRIZ_ARCHETYPE: Dict[str, Any] = {
    "id": "triz",
    "name": "TRIZ (Systematic Innovation)",
    "version": "1.0",
    "description": (
        "Theory of Inventive Problem Solving - a systematic methodology for "
        "resolving technical contradictions through inventive principles. "
        "TRIZ helps when improving one parameter inherently worsens another, "
        "and conventional compromise is unacceptable."
    ),
    "central_question": "How do we solve the impossible?",
    "origin": "Genrich Altshuller, 1946-1985",

    # Transition philosophy
    "transition_philosophy": "guided",
    "criteria_enforcement": "advisory",
    "backward_iteration": "reformulate_contradiction",

    # 5 Phases mapping to Universal Innovation States
    "phases": [
        {
            "name": "Problem Analysis",
            "universal_state": "DISCOVERY",
            "description": (
                "Decompose the problem, identify the ideal final result, "
                "map system functions, and identify available resources."
            ),
            "activities": [
                "problem_decomposition",
                "ideal_final_result",
                "system_function_analysis",
                "resource_identification",
            ],
            "key_artifacts": [
                ".ideal_final_result",
                ".problem_decomposition",
            ],
            "transition_criteria": [
                {
                    "type": "COACH_CHECKPOINT",
                    "description": "Core problem isolated and understood",
                    "required": True,
                },
                {
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": ".ideal_final_result",
                    "description": "Ideal Final Result articulated",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "Help the innovator articulate what the IDEAL solution looks like - "
                "the system performing its function without the harmful side effects. "
                "Don't accept vague goals; push for specificity."
            ),
        },
        {
            "name": "Contradiction Formulation",
            "universal_state": "DISCOVERY_DEFINITION",
            "description": (
                "Identify technical and physical contradictions, map to "
                "parameter pairs, and consult the contradiction matrix."
            ),
            "activities": [
                "technical_contradiction_identification",
                "physical_contradiction_isolation",
                "parameter_pair_mapping",
                "contradiction_matrix_consultation",
            ],
            "key_artifacts": [
                ".contradiction",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_COMPLETE",
                    "artifact_type": ".contradiction",
                    "description": "Contradiction formulated with parameter pairs",
                    "required": True,
                },
                {
                    "type": "VALIDATION",
                    "description": "Inventive principles identified from matrix",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "The contradiction is the heart of TRIZ. Help the innovator find "
                "the REAL conflict - not symptoms. 'I want X but when I improve X, "
                "Y gets worse' is the pattern. Map to matrix parameters."
            ),
        },
        {
            "name": "Principle Application",
            "universal_state": "DEFINITION_VALIDATION",
            "description": (
                "Explore recommended inventive principles, generate solution "
                "concepts, and check against the Ideal Final Result."
            ),
            "activities": [
                "inventive_principle_exploration",
                "solution_concept_generation",
                "biomimicry_cross_reference",  # CRITICAL: TRIZ-Biomimicry bridge
                "ideal_final_result_evaluation",
            ],
            "key_artifacts": [
                ".solution_concept",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": ".solution_concept",
                    "min_count": 2,
                    "description": "At least 2 solution concepts generated",
                    "required": True,
                },
                {
                    "type": "COACH_CHECKPOINT",
                    "description": "Concept approaches the Ideal Final Result",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "This is where the magic happens. Present inventive principles as "
                "thinking tools, not answers. When a principle has a biomimicry "
                "analog, surface it: 'Nature solved this with...' The innovator "
                "generates the concepts; you provide the scaffolding."
            ),
        },
        {
            "name": "Solution Development",
            "universal_state": "VALIDATION_REFINEMENT",
            "description": (
                "Develop the most promising concept, test contradiction resolution, "
                "and check for secondary contradictions."
            ),
            "activities": [
                "prototype_contradiction_resolution",
                "edge_case_testing",
                "solution_refinement",
                "secondary_contradiction_check",
            ],
            "key_artifacts": [
                ".prototype",
                ".validation_result",
            ],
            "transition_criteria": [
                {
                    "type": "VALIDATION",
                    "description": "Contradiction resolution demonstrated",
                    "required": True,
                },
                {
                    "type": "COACH_CHECKPOINT",
                    "description": "No unresolved secondary contradictions",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "Test whether the solution ACTUALLY resolves the contradiction "
                "without creating new ones. Secondary contradictions are common - "
                "don't let them slip past. If they emerge, iterate back to "
                "Contradiction Formulation."
            ),
        },
        {
            "name": "Implementation",
            "universal_state": "PREPARATION",
            "description": (
                "Document the solution with principle mapping, capture "
                "effectiveness data, and plan implementation."
            ),
            "activities": [
                "solution_documentation",
                "implementation_planning",
                "principle_effectiveness_capture",
            ],
            "key_artifacts": [
                ".implementation_plan",
                ".principle_effectiveness",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_COMPLETE",
                    "artifact_type": ".implementation_plan",
                    "description": "Implementation plan documented",
                    "required": True,
                },
                {
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": ".principle_effectiveness",
                    "description": "Principle effectiveness captured for IKF",
                    "required": False,
                },
            ],
            "coaching_focus": (
                "Capture which principles worked and why. This data feeds the "
                "Innovation Knowledge Fabric. Ask: 'Which principle was most "
                "useful? Any surprises? What would you do differently?'"
            ),
        },
    ],

    # Coaching configuration
    "coaching_config": {
        "language_style": "analytical_inventive",
        "framing": "contradiction_resolution",
        "backward_iteration": "reformulate_contradiction",
        "key_questions": [
            "What contradiction are you trying to resolve?",
            "What is the Ideal Final Result - what would a perfect solution look like?",
            "Which parameters conflict? Can you make both better simultaneously?",
            "Have you considered the opposite approach entirely?",
            "What resources in the system are currently unused?",
        ],
        "common_pitfalls": [
            "accepting_compromise_instead_of_resolving_contradiction",
            "applying_principles_without_formulating_contradiction_first",
            "ignoring_secondary_contradictions_created_by_solution",
            "skipping_ideal_final_result_definition",
            "treating_symptoms_instead_of_root_contradiction",
        ],
        "convergence_moments": [
            "contradiction_identified",
            "principles_selected",
            "solution_concept_chosen",
            "implementation_ready",
        ],
    },

    # Convergence protocol
    "convergence_config": {
        "min_phases_before_convergence": 2,
        "coach_checkpoint_weight": 0.3,
        "artifact_completion_weight": 0.4,
        "validation_weight": 0.3,
        "allow_phase_skip": False,
        "backward_iteration_enabled": True,
    },

    # Retrospective template
    "retrospective_template": {
        "questions": [
            "What contradictions did you identify, and which proved most fundamental?",
            "Which inventive principles were most useful? Were any surprising?",
            "Did you encounter secondary contradictions? How did you resolve them?",
            "How close did your final solution come to the Ideal Final Result?",
            "Were any biological analogs useful in understanding the inventive principles?",
            "What would you do differently in formulating the contradiction?",
        ],
        "metrics_to_capture": [
            "principles_applied",
            "contradictions_resolved",
            "secondary_contradictions_encountered",
            "biomimicry_insights_used",
            "ifr_achievement_percent",
        ],
    },

    # Metadata
    "metadata": {
        "added_version": "3.6.1",
        "documentation_url": "https://www.triz-journal.com/",
        "typical_duration_days": "14-60",
        "best_for": [
            "Technical contradictions",
            "Engineering challenges",
            "When compromise is unacceptable",
            "Breakthrough innovation",
        ],
        "less_suited_for": [
            "Pure market validation",
            "Customer discovery",
            "Incremental improvements",
        ],
    },
}


def get_triz_phase_by_state(universal_state: str) -> dict:
    """Get the TRIZ phase for a given universal innovation state."""
    for phase in TRIZ_ARCHETYPE["phases"]:
        if phase["universal_state"] == universal_state:
            return phase
    return None


def get_triz_coaching_hints(phase_name: str) -> str:
    """Get coaching focus hints for a specific TRIZ phase."""
    for phase in TRIZ_ARCHETYPE["phases"]:
        if phase["name"] == phase_name:
            return phase.get("coaching_focus", "")
    return ""
