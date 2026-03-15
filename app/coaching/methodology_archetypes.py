"""
InDE MVP v3.4 - Methodology Archetypes
Design Thinking and Stage-Gate archetype definitions with coaching language adapters.

Archetypes:
1. lean_startup - Experiment-focused, hypothesis-driven (default, v3.3)
2. design_thinking - Empathy-oriented, human-centered
3. stage_gate - Governance-aware, gate-criteria-explicit
4. adhoc - Flexible, innovator-led
5. emergent - Discovery-oriented, pattern-recognition

Each archetype defines:
- Phases and their expected artifacts
- Transition criteria (required/optional)
- Coaching language style
- Backward iteration philosophy
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core.config import (
    METHODOLOGY_ARCHETYPES, DEFAULT_METHODOLOGY_ARCHETYPE,
    METHODOLOGY_COACHING_STYLES, CRITERIA_ENFORCEMENT
)


# =============================================================================
# ARCHETYPE DATA CLASSES
# =============================================================================

@dataclass
class ArchetypePhase:
    """A phase within a methodology archetype."""
    name: str
    description: str
    expected_artifacts: List[str]
    typical_duration_days: int
    coaching_focus: str
    success_indicators: List[str]


@dataclass
class TransitionCriterion:
    """Criterion for phase transition."""
    criterion_id: str
    criterion_type: str  # ARTIFACT_EXISTS, ARTIFACT_COMPLETE, VALIDATION, etc.
    description: str
    required: bool = True
    validation_fn: Optional[str] = None  # Name of validation function


@dataclass
class MethodologyArchetype:
    """Complete methodology archetype definition."""
    name: str
    display_name: str
    description: str
    phases: List[ArchetypePhase]
    transitions: Dict[str, List[TransitionCriterion]]  # from_phase -> criteria
    coaching_style: Dict[str, str]
    enforcement: str  # strict | advisory | suggestive | emergent
    backward_iteration_philosophy: str


# =============================================================================
# LEAN STARTUP ARCHETYPE (Default from v3.3)
# =============================================================================

LEAN_STARTUP_ARCHETYPE = MethodologyArchetype(
    name="lean_startup",
    display_name="Lean Startup",
    description="Experiment-focused methodology emphasizing rapid hypothesis testing and validated learning",
    phases=[
        ArchetypePhase(
            name="VISION",
            description="Articulate the problem and initial solution hypothesis",
            expected_artifacts=["vision", "fears"],
            typical_duration_days=14,
            coaching_focus="problem_definition_and_user_understanding",
            success_indicators=[
                "Clear problem statement",
                "Identified target user",
                "Initial value proposition"
            ]
        ),
        ArchetypePhase(
            name="DE_RISK",
            description="Test key hypotheses through experiments",
            expected_artifacts=["hypothesis", "validation_experiments"],
            typical_duration_days=45,
            coaching_focus="hypothesis_validation_and_pivots",
            success_indicators=[
                "Key assumptions identified",
                "Experiments designed",
                "Early validation data"
            ]
        ),
        ArchetypePhase(
            name="DEPLOY",
            description="Build and launch validated solution",
            expected_artifacts=["mvp", "launch_plan"],
            typical_duration_days=60,
            coaching_focus="execution_and_iteration",
            success_indicators=[
                "MVP launched",
                "User feedback collected",
                "Iteration plan defined"
            ]
        )
    ],
    transitions={
        "VISION→DE_RISK": [
            TransitionCriterion(
                criterion_id="vision_artifact",
                criterion_type="ARTIFACT_EXISTS",
                description="Vision artifact has been generated",
                required=True
            ),
            TransitionCriterion(
                criterion_id="fears_captured",
                criterion_type="ARTIFACT_EXISTS",
                description="Fears/concerns have been documented",
                required=False
            ),
            TransitionCriterion(
                criterion_id="coach_checkpoint",
                criterion_type="COACH_CHECKPOINT",
                description="Coach confirms readiness to test hypotheses",
                required=True
            )
        ],
        "DE_RISK→DEPLOY": [
            TransitionCriterion(
                criterion_id="hypothesis_tested",
                criterion_type="VALIDATION",
                description="At least one key hypothesis has been tested",
                required=True
            ),
            TransitionCriterion(
                criterion_id="risk_assessment",
                criterion_type="ARTIFACT_COMPLETE",
                description="Major risks assessed (RVE verdicts)",
                required=False
            )
        ]
    },
    coaching_style={
        "language_style": "experiment_focused",
        "framing": "hypothesis_driven",
        "backward_iteration": "pivot_is_progress",
        "encouragement_mode": "celebrate_learning"
    },
    enforcement="advisory",
    backward_iteration_philosophy="Pivots and iterations are signs of progress, not failure. Learning from 'failed' experiments is valuable."
)


# =============================================================================
# DESIGN THINKING ARCHETYPE
# =============================================================================

DESIGN_THINKING_ARCHETYPE = MethodologyArchetype(
    name="design_thinking",
    display_name="Design Thinking",
    description="Human-centered design approach emphasizing empathy and iterative prototyping",
    phases=[
        ArchetypePhase(
            name="EMPATHIZE",
            description="Deeply understand user needs and context",
            expected_artifacts=["user_research", "empathy_map"],
            typical_duration_days=21,
            coaching_focus="user_understanding_and_observation",
            success_indicators=[
                "User interviews conducted",
                "Needs identified",
                "Context understood"
            ]
        ),
        ArchetypePhase(
            name="DEFINE",
            description="Synthesize research into actionable problem statement",
            expected_artifacts=["vision", "point_of_view"],
            typical_duration_days=14,
            coaching_focus="problem_reframing_and_insights",
            success_indicators=[
                "Problem reframed",
                "Insights synthesized",
                "POV statement crafted"
            ]
        ),
        ArchetypePhase(
            name="IDEATE",
            description="Generate diverse solution concepts",
            expected_artifacts=["concept_sketches", "idea_portfolio"],
            typical_duration_days=14,
            coaching_focus="divergent_thinking_and_creativity",
            success_indicators=[
                "Multiple concepts generated",
                "Ideas evaluated",
                "Top concepts selected"
            ]
        ),
        ArchetypePhase(
            name="PROTOTYPE",
            description="Create rapid prototypes to test concepts",
            expected_artifacts=["prototype", "test_plan"],
            typical_duration_days=21,
            coaching_focus="rapid_prototyping_and_testing",
            success_indicators=[
                "Prototype created",
                "Test scenarios defined",
                "Feedback collected"
            ]
        ),
        ArchetypePhase(
            name="TEST",
            description="Test prototypes with users and iterate",
            expected_artifacts=["test_results", "iteration_plan"],
            typical_duration_days=21,
            coaching_focus="user_testing_and_refinement",
            success_indicators=[
                "User tests conducted",
                "Feedback analyzed",
                "Refinements identified"
            ]
        )
    ],
    transitions={
        "EMPATHIZE→DEFINE": [
            TransitionCriterion(
                criterion_id="user_research",
                criterion_type="ARTIFACT_EXISTS",
                description="User research documented",
                required=True
            ),
            TransitionCriterion(
                criterion_id="empathy_signals",
                criterion_type="CUSTOM",
                description="Evidence of user understanding in scaffolding",
                required=False
            )
        ],
        "DEFINE→IDEATE": [
            TransitionCriterion(
                criterion_id="problem_defined",
                criterion_type="ARTIFACT_COMPLETE",
                description="Clear problem statement exists",
                required=True
            )
        ],
        "IDEATE→PROTOTYPE": [
            TransitionCriterion(
                criterion_id="concepts_generated",
                criterion_type="CUSTOM",
                description="Multiple solution concepts documented",
                required=True
            )
        ],
        "PROTOTYPE→TEST": [
            TransitionCriterion(
                criterion_id="prototype_exists",
                criterion_type="ARTIFACT_EXISTS",
                description="At least one prototype ready for testing",
                required=True
            )
        ]
    },
    coaching_style={
        "language_style": "empathy_oriented",
        "framing": "human_centered",
        "backward_iteration": "feature_not_failure",
        "encouragement_mode": "user_voice_amplification"
    },
    enforcement="suggestive",
    backward_iteration_philosophy="Going back to earlier phases is a feature of the process, not a failure. Each iteration deepens understanding."
)


# =============================================================================
# STAGE-GATE ARCHETYPE
# =============================================================================

STAGE_GATE_ARCHETYPE = MethodologyArchetype(
    name="stage_gate",
    display_name="Stage-Gate",
    description="Structured innovation process with formal gate reviews",
    phases=[
        ArchetypePhase(
            name="DISCOVERY",
            description="Idea generation and opportunity identification",
            expected_artifacts=["opportunity_brief"],
            typical_duration_days=30,
            coaching_focus="opportunity_assessment",
            success_indicators=[
                "Opportunity identified",
                "Initial assessment complete",
                "Sponsor engagement"
            ]
        ),
        ArchetypePhase(
            name="SCOPING",
            description="Quick preliminary investigation",
            expected_artifacts=["vision", "preliminary_assessment"],
            typical_duration_days=21,
            coaching_focus="feasibility_and_alignment",
            success_indicators=[
                "Market assessment done",
                "Technical feasibility assessed",
                "Business case outline"
            ]
        ),
        ArchetypePhase(
            name="BUILD_BUSINESS_CASE",
            description="Detailed investigation and business case",
            expected_artifacts=["business_case", "project_plan"],
            typical_duration_days=45,
            coaching_focus="business_case_development",
            success_indicators=[
                "Detailed business case",
                "Resource plan",
                "Risk assessment"
            ]
        ),
        ArchetypePhase(
            name="DEVELOPMENT",
            description="Detailed design and development",
            expected_artifacts=["development_plan", "prototype"],
            typical_duration_days=90,
            coaching_focus="execution_tracking",
            success_indicators=[
                "Development milestones met",
                "Testing complete",
                "Launch readiness"
            ]
        ),
        ArchetypePhase(
            name="TESTING_VALIDATION",
            description="Testing and validation in market",
            expected_artifacts=["test_results", "launch_plan"],
            typical_duration_days=45,
            coaching_focus="validation_and_launch_prep",
            success_indicators=[
                "Market tests complete",
                "Business case validated",
                "Launch plan finalized"
            ]
        ),
        ArchetypePhase(
            name="LAUNCH",
            description="Full commercialization",
            expected_artifacts=["launch_report", "post_launch_review"],
            typical_duration_days=60,
            coaching_focus="launch_execution",
            success_indicators=[
                "Launched successfully",
                "Initial metrics captured",
                "Post-launch review complete"
            ]
        )
    ],
    transitions={
        "DISCOVERY→SCOPING": [
            TransitionCriterion(
                criterion_id="gate_1_review",
                criterion_type="COACH_CHECKPOINT",
                description="Gate 1 review: Idea screen passed",
                required=True
            )
        ],
        "SCOPING→BUILD_BUSINESS_CASE": [
            TransitionCriterion(
                criterion_id="gate_2_review",
                criterion_type="COACH_CHECKPOINT",
                description="Gate 2 review: Second screen passed",
                required=True
            ),
            TransitionCriterion(
                criterion_id="preliminary_assessment",
                criterion_type="ARTIFACT_EXISTS",
                description="Preliminary assessment documented",
                required=True
            )
        ],
        "BUILD_BUSINESS_CASE→DEVELOPMENT": [
            TransitionCriterion(
                criterion_id="gate_3_review",
                criterion_type="COACH_CHECKPOINT",
                description="Gate 3 review: Go to Development decision",
                required=True
            ),
            TransitionCriterion(
                criterion_id="business_case",
                criterion_type="ARTIFACT_COMPLETE",
                description="Full business case approved",
                required=True
            )
        ],
        "DEVELOPMENT→TESTING_VALIDATION": [
            TransitionCriterion(
                criterion_id="gate_4_review",
                criterion_type="COACH_CHECKPOINT",
                description="Gate 4 review: Go to Testing decision",
                required=True
            )
        ],
        "TESTING_VALIDATION→LAUNCH": [
            TransitionCriterion(
                criterion_id="gate_5_review",
                criterion_type="COACH_CHECKPOINT",
                description="Gate 5 review: Go to Launch decision",
                required=True
            ),
            TransitionCriterion(
                criterion_id="validation_complete",
                criterion_type="VALIDATION",
                description="Market validation complete",
                required=True
            )
        ]
    },
    coaching_style={
        "language_style": "governance_aware",
        "framing": "gate_criteria_explicit",
        "backward_iteration": "requires_gate_approval",
        "encouragement_mode": "milestone_celebration"
    },
    enforcement="strict",
    backward_iteration_philosophy="Moving back requires explicit gate review and approval. Each gate ensures proper due diligence."
)


# =============================================================================
# ADHOC AND EMERGENT ARCHETYPES
# =============================================================================

ADHOC_ARCHETYPE = MethodologyArchetype(
    name="ad_hoc",
    display_name="Freeform",
    description=(
        "Work without a predefined methodology. InDE observes your approach and "
        "offers to capture it as a reusable methodology when complete. All standard "
        "tools remain available. You lead; InDE learns."
    ),
    phases=[],  # v3.7.1: No predefined phases - innovator leads
    transitions={},  # No required transitions - innovator controls flow
    coaching_style={
        "language_style": "flexible",
        "framing": "innovator_led",
        "backward_iteration": "open",
        "encouragement_mode": "gentle_support"
    },
    enforcement="suggestive",
    backward_iteration_philosophy="The innovator determines the flow. Coach provides support without imposing structure."
)


EMERGENT_ARCHETYPE = MethodologyArchetype(
    name="emergent",
    display_name="Emergent",
    description="Discovery-oriented approach where methodology emerges from the work",
    phases=[
        ArchetypePhase(
            name="DISCOVER",
            description="Discovery and pattern recognition",
            expected_artifacts=[],
            typical_duration_days=45,
            coaching_focus="pattern_recognition",
            success_indicators=["Patterns emerging"]
        ),
        ArchetypePhase(
            name="EVOLVE",
            description="Evolution based on emerging patterns",
            expected_artifacts=["custom"],
            typical_duration_days=60,
            coaching_focus="pattern_application",
            success_indicators=["Progress aligned with patterns"]
        ),
        ArchetypePhase(
            name="MANIFEST",
            description="Manifestation of insights",
            expected_artifacts=["outcome_summary"],
            typical_duration_days=45,
            coaching_focus="integration",
            success_indicators=["Insights manifested"]
        )
    ],
    transitions={},  # Emergent - no predefined transitions
    coaching_style={
        "language_style": "discovery_oriented",
        "framing": "pattern_recognition",
        "backward_iteration": "natural_flow",
        "encouragement_mode": "emergence_celebration"
    },
    enforcement="emergent",
    backward_iteration_philosophy="The path unfolds naturally. What appears as 'going back' may be essential deepening."
)


# =============================================================================
# ARCHETYPE REGISTRY
# =============================================================================

ARCHETYPE_REGISTRY: Dict[str, MethodologyArchetype] = {
    "lean_startup": LEAN_STARTUP_ARCHETYPE,
    "design_thinking": DESIGN_THINKING_ARCHETYPE,
    "stage_gate": STAGE_GATE_ARCHETYPE,
    "adhoc": ADHOC_ARCHETYPE,
    "ad_hoc": ADHOC_ARCHETYPE,  # v3.7.1: Both keys point to same archetype
    "emergent": EMERGENT_ARCHETYPE
}

# v3.6.1/v3.7.1: Note - TRIZ, Blue Ocean, and detailed Ad-Hoc archetypes are defined
# in methodology.archetypes module (triz.py, blue_ocean.py, adhoc.py) with richer
# configuration. This registry provides the basic MethodologyArchetype compatibility
# layer for the coaching system.


def get_archetype(name: str) -> Optional[MethodologyArchetype]:
    """Get an archetype by name."""
    return ARCHETYPE_REGISTRY.get(name)


def get_default_archetype() -> MethodologyArchetype:
    """Get the default archetype (lean_startup)."""
    return ARCHETYPE_REGISTRY[DEFAULT_METHODOLOGY_ARCHETYPE]


def get_archetype_phases(archetype_name: str) -> List[str]:
    """Get phase names for an archetype."""
    archetype = get_archetype(archetype_name)
    if not archetype:
        return ["VISION", "DE_RISK", "DEPLOY"]  # Default
    return [p.name for p in archetype.phases]


def get_transition_criteria(archetype_name: str, from_phase: str, to_phase: str) -> List[TransitionCriterion]:
    """Get transition criteria for a phase transition."""
    archetype = get_archetype(archetype_name)
    if not archetype:
        return []
    transition_key = f"{from_phase}→{to_phase}"
    return archetype.transitions.get(transition_key, [])


def get_coaching_style(archetype_name: str) -> Dict[str, str]:
    """Get coaching style configuration for an archetype."""
    archetype = get_archetype(archetype_name)
    if not archetype:
        return METHODOLOGY_COACHING_STYLES.get("lean_startup", {})
    return archetype.coaching_style


def get_enforcement_mode(archetype_name: str) -> str:
    """Get enforcement mode for an archetype."""
    archetype = get_archetype(archetype_name)
    if not archetype:
        return "advisory"
    return archetype.enforcement


# =============================================================================
# COACHING LANGUAGE ADAPTER
# =============================================================================

class CoachingLanguageAdapter:
    """
    Adapts coaching language based on methodology archetype.

    Transforms generic coaching prompts into archetype-specific language.
    """

    # Language templates by style
    TEMPLATES = {
        "experiment_focused": {
            "transition_prompt": "Based on your hypothesis testing, you're ready to {action}.",
            "backward_iteration": "Let's pivot back to {phase} - this is valuable learning!",
            "encouragement": "Great experiment! The data tells us {insight}.",
            "milestone": "You've validated your {element} hypothesis."
        },
        "empathy_oriented": {
            "transition_prompt": "Your understanding of users suggests it's time to {action}.",
            "backward_iteration": "Let's return to {phase} to deepen our empathy for users.",
            "encouragement": "Wonderful insight about your users: {insight}.",
            "milestone": "You've captured a key user need: {element}."
        },
        "governance_aware": {
            "transition_prompt": "Gate review indicates readiness to {action}.",
            "backward_iteration": "Gate feedback suggests revisiting {phase} requirements.",
            "encouragement": "Excellent progress toward gate criteria: {insight}.",
            "milestone": "Gate criterion satisfied: {element}."
        },
        "flexible": {
            "transition_prompt": "You seem ready to {action}.",
            "backward_iteration": "Let's revisit {phase} as you suggested.",
            "encouragement": "Good progress: {insight}.",
            "milestone": "You've achieved: {element}."
        },
        "discovery_oriented": {
            "transition_prompt": "An emerging pattern suggests {action}.",
            "backward_iteration": "The pattern invites us to revisit {phase}.",
            "encouragement": "A pattern is emerging: {insight}.",
            "milestone": "Pattern confirmed: {element}."
        }
    }

    # v4.0: Momentum Bridge Templates for Session Close / Re-engagement
    # Goal: Create continuity between sessions for async coaching cadence
    MOMENTUM_BRIDGES = {
        "session_close": {
            "high_momentum": "Great progress today! Your idea is sharper now. "
                "When you return, we'll pick up right where you left off.",
            "moderate_momentum": "You've made some solid progress. "
                "Your idea will be here when you're ready to continue.",
            "low_momentum": "Even small steps count. "
                "Your idea is waiting for you whenever you're ready to come back.",
            "default": "Good session. Your progress is saved — "
                "come back anytime to continue."
        },
        "re_engagement": {
            "high_momentum": "Welcome back! You were on a roll. "
                "Let's pick up where you left off.",
            "moderate_momentum": "Good to have you back. "
                "Here's where we left off.",
            "low_momentum": "Your idea is still here. "
                "Let's pick it back up together.",
            "long_gap": "It's been a while, but your idea has been waiting. "
                "Let's revisit where you are.",
            "default": "Welcome back. Ready to continue?"
        },
        "depth_acknowledgment": {
            "idea_forming": "Your idea is taking shape.",
            "idea_sharpening": "Your idea is getting sharper.",
            "idea_tested": "Your idea is battle-tested.",
            "idea_advancing": "Your idea is moving forward.",
            "idea_ready": "Your idea is ready."
        },
        # v4.0: Artifact completion bridges - the critical momentum bridges
        # These replace session-close "What would you like to explore next?" language
        # Each bridge briefly acknowledges, then opens a forward-leaning question
        "artifact_completion": {
            "vision": [
                "Your story is taking shape. I'm curious — if you put this idea in front of someone who could fund it tomorrow, what's the one thing they'd probably push back on?",
                "You've described something real here. What's the part of this idea that still feels most uncertain to you?",
                "That's a strong foundation. What would have to be true for this to actually work — and what aren't you sure about yet?",
            ],
            "fear": [
                "You've identified what matters most to protect. Of everything we just talked about, which one would be most valuable to get some real-world evidence on?",
                "Good — you know what you're protecting against. If you could ask just one person who has this problem a single question this week, what would it be?",
                "Now that you can see the risks clearly, what's the fastest way to find out if the biggest one is actually a problem?",
            ],
            "validation": [
                "You've done the hard work of testing your assumptions. Based on what you've learned, what do you feel most ready to build next?",
                "The evidence is pointing somewhere. What does it tell you about what to do first?",
            ],
            "default": [
                "You've made real progress here. What's the next thing you find yourself wondering about?",
            ]
        }
    }

    def __init__(self, archetype_name: str):
        self.archetype_name = archetype_name
        self.archetype = get_archetype(archetype_name)
        self.style = self.archetype.coaching_style if self.archetype else {}
        self.language_style = self.style.get("language_style", "flexible")

    def adapt_transition_prompt(self, action: str) -> str:
        """Generate archetype-appropriate transition prompt."""
        template = self.TEMPLATES.get(self.language_style, self.TEMPLATES["flexible"])
        return template["transition_prompt"].format(action=action)

    def adapt_backward_iteration(self, phase: str) -> str:
        """Generate archetype-appropriate backward iteration message."""
        template = self.TEMPLATES.get(self.language_style, self.TEMPLATES["flexible"])
        return template["backward_iteration"].format(phase=phase)

    def adapt_encouragement(self, insight: str) -> str:
        """Generate archetype-appropriate encouragement."""
        template = self.TEMPLATES.get(self.language_style, self.TEMPLATES["flexible"])
        return template["encouragement"].format(insight=insight)

    def adapt_milestone(self, element: str) -> str:
        """Generate archetype-appropriate milestone message."""
        template = self.TEMPLATES.get(self.language_style, self.TEMPLATES["flexible"])
        return template["milestone"].format(element=element)

    def get_phase_introduction(self, phase_name: str) -> str:
        """Get introduction text for a phase."""
        if not self.archetype:
            return f"You're now in the {phase_name} phase."

        phase = next((p for p in self.archetype.phases if p.name == phase_name), None)
        if not phase:
            return f"You're now in the {phase_name} phase."

        return f"**{phase_name}**: {phase.description}"

    def get_phase_success_indicators(self, phase_name: str) -> List[str]:
        """Get success indicators for a phase."""
        if not self.archetype:
            return []

        phase = next((p for p in self.archetype.phases if p.name == phase_name), None)
        return phase.success_indicators if phase else []

    # =========================================================================
    # v4.0: Momentum Bridge Methods
    # =========================================================================

    def get_session_close_message(self, momentum_level: str = "moderate_momentum") -> str:
        """
        Get session close message with momentum bridge language.

        Args:
            momentum_level: One of 'high_momentum', 'moderate_momentum', 'low_momentum'

        Returns:
            Momentum-aware closing message for the session
        """
        bridges = self.MOMENTUM_BRIDGES.get("session_close", {})
        return bridges.get(momentum_level, bridges.get("default", "Good session."))

    def get_re_engagement_message(
        self,
        momentum_level: str = "moderate_momentum",
        days_since_last: int = 0
    ) -> str:
        """
        Get re-engagement message when innovator returns.

        Args:
            momentum_level: One of 'high_momentum', 'moderate_momentum', 'low_momentum'
            days_since_last: Days since last session

        Returns:
            Momentum-aware greeting for returning innovator
        """
        bridges = self.MOMENTUM_BRIDGES.get("re_engagement", {})

        # Long gap overrides momentum level
        if days_since_last > 7:
            return bridges.get("long_gap", bridges.get("default", "Welcome back."))

        return bridges.get(momentum_level, bridges.get("default", "Welcome back."))

    def get_depth_acknowledgment(self, depth_stage: str) -> str:
        """
        Get depth-framed progress acknowledgment.

        Args:
            depth_stage: One of 'idea_forming', 'idea_sharpening',
                        'idea_tested', 'idea_advancing', 'idea_ready'

        Returns:
            Depth-framed acknowledgment of progress
        """
        acknowledgments = self.MOMENTUM_BRIDGES.get("depth_acknowledgment", {})
        return acknowledgments.get(depth_stage, "Your idea is progressing.")

    def get_artifact_completion_bridge(self, artifact_type: str) -> str:
        """
        Get a momentum bridge question for artifact completion.

        v4.0: This is the critical replacement for session-close language.
        Instead of "What would you like to explore next?", the bridge
        briefly acknowledges what was built and immediately opens a
        forward-leaning question that leads to the next natural concern.

        Args:
            artifact_type: The type of artifact completed ('vision', 'fear', 'validation')

        Returns:
            A forward-leaning bridge question that maintains momentum
        """
        import random

        bridges = self.MOMENTUM_BRIDGES.get("artifact_completion", {})
        templates = bridges.get(artifact_type, bridges.get("default", []))

        if not templates:
            return "You've made real progress here. What's the next thing you find yourself wondering about?"

        return random.choice(templates)
