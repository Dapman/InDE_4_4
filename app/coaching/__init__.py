"""
InDE MVP v3.9 - Coaching Module
Convergence-aware coaching with methodology archetypes and ODICM extensions.

v3.9 adds:
- Prompt Calibration - adapts coaching prompts based on LLM quality tier
- Air-gapped deployment support with local model optimization

v3.6.1 adds:
- Scenario Detection - recognizes decision forks in conversations
"""

from .convergence import (
    ConvergencePhase,
    ConvergenceSignalDetector,
    ConvergenceStateMachine,
    ConvergenceOrchestrator,
    get_convergence_orchestrator
)

from .prompt_calibration import (
    QualityTier,
    calibrate_system_prompt,
    get_max_response_tokens,
    get_context_budget,
    should_show_quality_indicator,
    get_quality_indicator_message,
    set_quality_tier,
    get_quality_tier
)

from .methodology_archetypes import (
    MethodologyArchetype,
    ARCHETYPE_REGISTRY,
    get_archetype,
    get_default_archetype,
    get_archetype_phases,
    get_transition_criteria,
    get_coaching_style,
    get_enforcement_mode,
    CoachingLanguageAdapter
)

from .odicm_extensions import (
    CoachingMode,
    ContextSource,
    CoachingContext,
    EnhancedCoachingResponse,
    ConvergenceAwareCoach,
    OrgIntelligenceProvider,
    get_convergence_coach,
    get_org_intelligence
)

from .scenario_detection import (
    ScenarioDetector,
    ScenarioExplorationState
)

__all__ = [
    # Convergence
    "ConvergencePhase",
    "ConvergenceSignalDetector",
    "ConvergenceStateMachine",
    "ConvergenceOrchestrator",
    "get_convergence_orchestrator",
    # Methodology Archetypes
    "MethodologyArchetype",
    "ARCHETYPE_REGISTRY",
    "get_archetype",
    "get_default_archetype",
    "get_archetype_phases",
    "get_transition_criteria",
    "get_coaching_style",
    "get_enforcement_mode",
    "CoachingLanguageAdapter",
    # ODICM Extensions
    "CoachingMode",
    "ContextSource",
    "CoachingContext",
    "EnhancedCoachingResponse",
    "ConvergenceAwareCoach",
    "OrgIntelligenceProvider",
    "get_convergence_coach",
    "get_org_intelligence",
    # Scenario Detection (v3.6.1)
    "ScenarioDetector",
    "ScenarioExplorationState",
    # Prompt Calibration (v3.9)
    "QualityTier",
    "calibrate_system_prompt",
    "get_max_response_tokens",
    "get_context_budget",
    "should_show_quality_indicator",
    "get_quality_indicator_message",
    "set_quality_tier",
    "get_quality_tier",
]
