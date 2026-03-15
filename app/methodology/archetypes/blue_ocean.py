"""
Blue Ocean Strategy Archetype Definition

Blue Ocean Strategy is a methodology for creating uncontested market space
through value innovation - achieving differentiation AND lower cost simultaneously.

Central Question: "Are we in the right ocean?"

This archetype guides innovators through strategic reconstruction using
the Strategy Canvas, Four Actions Framework (ERRC), and non-customer analysis.
"""

from typing import Dict, Any


BLUE_OCEAN_ARCHETYPE: Dict[str, Any] = {
    "id": "blue_ocean",
    "name": "Blue Ocean Strategy",
    "version": "1.0",
    "description": (
        "A strategic methodology for creating uncontested market space rather than "
        "competing in crowded existing markets (red oceans). Blue Ocean focuses on "
        "value innovation - simultaneously pursuing differentiation AND low cost by "
        "reconstructing industry boundaries."
    ),
    "central_question": "Are we in the right ocean?",
    "origin": "W. Chan Kim & Renee Mauborgne, 2005",

    # Transition philosophy
    "transition_philosophy": "guided",
    "criteria_enforcement": "suggestive",
    "backward_iteration": "rethink_value_curve",

    # 5 Phases mapping to Universal Innovation States
    "phases": [
        {
            "name": "As-Is Analysis",
            "universal_state": "DISCOVERY",
            "description": (
                "Map the current industry strategy canvas, identify competitive "
                "factors everyone competes on, and begin exploring the Six Paths."
            ),
            "activities": [
                "strategy_canvas_current",
                "industry_assumptions_mapping",
                "six_paths_exploration",
                "buyer_utility_analysis",
            ],
            "key_artifacts": [
                ".strategy_canvas",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": ".strategy_canvas",
                    "description": "Current strategy canvas documented",
                    "required": True,
                },
                {
                    "type": "ARTIFACT_COMPLETE",
                    "description": "Competitive factors identified with industry ratings",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "Help the innovator see their industry's assumptions clearly. "
                "What does everyone compete on? What factors are taken for granted? "
                "Push them to articulate WHY the industry competes this way."
            ),
        },
        {
            "name": "Strategic Reconstruction",
            "universal_state": "DISCOVERY_DEFINITION",
            "description": (
                "Apply the Four Actions Framework (ERRC), design a divergent value "
                "curve, explore non-customers, and identify uncontested space."
            ),
            "activities": [
                "four_actions_framework",
                "value_curve_design",
                "non_customer_analysis",
                "uncontested_space_identification",
            ],
            "key_artifacts": [
                ".four_actions",
                ".strategy_canvas",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_COMPLETE",
                    "artifact_type": ".four_actions",
                    "description": "ERRC grid completed with rationale",
                    "required": True,
                },
                {
                    "type": "ARTIFACT_EXISTS",
                    "description": "Value curve diverges from industry norms",
                    "required": True,
                },
                {
                    "type": "COACH_CHECKPOINT",
                    "description": "Non-customers explored (at least one tier)",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "The Four Actions are the heart of reconstruction. Challenge every "
                "factor: What can be ELIMINATED? What reduced? What raised? What "
                "created that the industry never offered? Push toward non-customers - "
                "they reveal why people REJECT the industry."
            ),
        },
        {
            "name": "Value Innovation",
            "universal_state": "DEFINITION_VALIDATION",
            "description": (
                "Articulate the value innovation clearly, align with a viable "
                "business model, and map the buyer experience cycle."
            ),
            "activities": [
                "blue_ocean_idea_articulation",
                "business_model_alignment",
                "buyer_experience_cycle",
                "price_corridor_of_the_mass",
            ],
            "key_artifacts": [
                ".value_innovation_statement",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_COMPLETE",
                    "artifact_type": ".value_innovation_statement",
                    "description": "Value innovation statement articulated",
                    "required": True,
                },
                {
                    "type": "COACH_CHECKPOINT",
                    "description": "Business model is viable with the new value curve",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "Value innovation must be BOTH differentiation AND lower cost. "
                "If it's only one, it's not Blue Ocean. Help them see where "
                "cost savings fund the new factors they're creating."
            ),
        },
        {
            "name": "Fair Process Execution",
            "universal_state": "VALIDATION_REFINEMENT",
            "description": (
                "Engage stakeholders, conduct rapid market tests, assess execution "
                "risks, and identify tipping points for adoption."
            ),
            "activities": [
                "stakeholder_engagement",
                "rapid_market_test",
                "execution_risk_assessment",
                "tipping_point_leadership",
            ],
            "key_artifacts": [
                ".validation_result",
                ".stakeholder_map",
            ],
            "transition_criteria": [
                {
                    "type": "VALIDATION",
                    "description": "Stakeholders engaged and aligned",
                    "required": True,
                },
                {
                    "type": "VALIDATION",
                    "description": "Market signal received from non-customers",
                    "required": True,
                },
            ],
            "coaching_focus": (
                "Fair process means stakeholders understand WHY the shift is "
                "happening. Don't skip this - Blue Ocean moves often fail on "
                "execution because stakeholders weren't brought along. Test "
                "with non-customers, not existing customers."
            ),
        },
        {
            "name": "Launch Preparation",
            "universal_state": "PREPARATION",
            "description": (
                "Document the strategic move, assess sustainability, identify "
                "imitation barriers, and plan for eventual renewal."
            ),
            "activities": [
                "blue_ocean_move_documentation",
                "sustainability_assessment",
                "imitation_barrier_analysis",
                "renewal_roadmap",
            ],
            "key_artifacts": [
                ".strategic_move",
                ".sustainability_plan",
            ],
            "transition_criteria": [
                {
                    "type": "ARTIFACT_COMPLETE",
                    "artifact_type": ".strategic_move",
                    "description": "Strategic move fully documented",
                    "required": True,
                },
                {
                    "type": "ARTIFACT_EXISTS",
                    "artifact_type": ".sustainability_plan",
                    "description": "Sustainability and renewal considerations captured",
                    "required": False,
                },
            ],
            "coaching_focus": (
                "Blue oceans eventually turn red. Help them think about "
                "sustainability - what makes this hard to imitate? When will "
                "renewal be needed? Capture the full strategic move for "
                "organizational learning."
            ),
        },
    ],

    # Coaching configuration
    "coaching_config": {
        "language_style": "strategic_expansive",
        "framing": "value_innovation",
        "backward_iteration": "rethink_value_curve",
        "key_questions": [
            "What factors does your industry compete on that customers don't actually value?",
            "Who are the non-customers - the people who actively choose NOT to use what's available?",
            "What would you eliminate entirely if you could redesign the industry from scratch?",
            "Can you achieve differentiation AND lower cost simultaneously?",
            "What would make competitors irrelevant rather than beaten?",
        ],
        "common_pitfalls": [
            "incremental_improvement_instead_of_reconstruction",
            "focusing_on_existing_customers_instead_of_non_customers",
            "competing_on_existing_factors_instead_of_creating_new_ones",
            "value_curve_too_similar_to_industry_norms",
            "differentiation_without_cost_reduction",
        ],
        "convergence_moments": [
            "strategy_canvas_divergent",
            "errc_completed",
            "value_innovation_articulated",
            "stakeholders_aligned",
        ],
    },

    # Convergence protocol
    "convergence_config": {
        "min_phases_before_convergence": 2,
        "coach_checkpoint_weight": 0.35,
        "artifact_completion_weight": 0.35,
        "validation_weight": 0.30,
        "allow_phase_skip": False,
        "backward_iteration_enabled": True,
    },

    # Retrospective template
    "retrospective_template": {
        "questions": [
            "Did your value curve diverge meaningfully from the industry norms?",
            "What factors did you eliminate or reduce, and were those decisions validated?",
            "Did you discover non-customer insights that changed your approach?",
            "Was value innovation achieved - differentiation AND lower cost simultaneously?",
            "How sustainable is the blue ocean position? What imitation barriers exist?",
            "What would you explore differently in the Six Paths analysis?",
        ],
        "metrics_to_capture": [
            "factors_eliminated",
            "factors_reduced",
            "factors_raised",
            "factors_created",
            "non_customer_tier_explored",
            "value_curve_divergence_score",
        ],
    },

    # Metadata
    "metadata": {
        "added_version": "3.6.1",
        "documentation_url": "https://www.blueoceanstrategy.com/",
        "typical_duration_days": "30-90",
        "best_for": [
            "Strategic repositioning",
            "Market creation",
            "Escaping price competition",
            "Reaching non-customers",
        ],
        "less_suited_for": [
            "Technical problem-solving",
            "Pure process improvement",
            "Cost cutting without strategic shift",
        ],
    },
}


# Six Paths Framework reference for coaching
SIX_PATHS_FRAMEWORK = {
    "path_1": {
        "name": "Look Across Alternative Industries",
        "question": "What industries serve the same purpose differently?",
        "coaching_prompt": "What substitutes do non-customers use instead?",
    },
    "path_2": {
        "name": "Look Across Strategic Groups",
        "question": "What if you moved between premium and budget offerings?",
        "coaching_prompt": "Why do customers trade up or down?",
    },
    "path_3": {
        "name": "Look Across Buyer Groups",
        "question": "Who influences vs. uses vs. pays? What if you targeted a different group?",
        "coaching_prompt": "Who makes the real decision?",
    },
    "path_4": {
        "name": "Look Across Complementary Products/Services",
        "question": "What happens before, during, and after your product is used?",
        "coaching_prompt": "What pain points exist in the total solution?",
    },
    "path_5": {
        "name": "Look Across Functional or Emotional Appeal",
        "question": "Does your industry compete on function or emotion? What if you switched?",
        "coaching_prompt": "Are customers over-served functionally or emotionally?",
    },
    "path_6": {
        "name": "Look Across Time",
        "question": "What trends are shaping your industry? Can you lead them?",
        "coaching_prompt": "What will non-customers want in 5 years?",
    },
}


# Non-customer tiers reference
NON_CUSTOMER_TIERS = {
    "tier_1": {
        "name": "Soon-to-be Non-customers",
        "description": "Currently using offerings but mentally ready to leave",
        "coaching_prompt": "What frustrates them about current offerings?",
    },
    "tier_2": {
        "name": "Refusing Non-customers",
        "description": "Consciously chose against the industry's offerings",
        "coaching_prompt": "Why do they actively reject what's available?",
    },
    "tier_3": {
        "name": "Unexplored Non-customers",
        "description": "In distant markets, never considered as customers",
        "coaching_prompt": "What keeps them completely outside the industry?",
    },
}


def get_blue_ocean_phase_by_state(universal_state: str) -> dict:
    """Get the Blue Ocean phase for a given universal innovation state."""
    for phase in BLUE_OCEAN_ARCHETYPE["phases"]:
        if phase["universal_state"] == universal_state:
            return phase
    return None


def get_blue_ocean_coaching_hints(phase_name: str) -> str:
    """Get coaching focus hints for a specific Blue Ocean phase."""
    for phase in BLUE_OCEAN_ARCHETYPE["phases"]:
        if phase["name"] == phase_name:
            return phase.get("coaching_focus", "")
    return ""
