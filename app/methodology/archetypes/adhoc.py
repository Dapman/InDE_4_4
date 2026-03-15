"""
Ad-Hoc (Freeform) Archetype Definition
v3.7.1 - EMS Process Observation Engine & Ad-Hoc Pursuit Mode

The Ad-Hoc archetype represents methodology-free innovation. Instead of guiding
the innovator through predefined phases, InDE observes their natural process
and learns from it. This is the foundation of the Emergent Methodology Synthesizer.

Central Question: "What does my best work look like?"

This archetype enables:
- Non-directive coaching (responds when asked, doesn't proactively guide)
- Process observation (silently captures behavioral patterns)
- Manual state transitions (innovator controls their own flow)
- Methodology synthesis (after multiple pursuits, patterns emerge)
"""

from typing import Dict, Any


ADHOC_ARCHETYPE: Dict[str, Any] = {
    "id": "ad_hoc",
    "name": "Freeform",
    "version": "1.0",
    "description": (
        "Work without a predefined methodology. InDE observes your approach and "
        "offers to capture it as a reusable methodology when complete. All standard "
        "tools remain available - telling your story, protecting your idea, testing assumptions, "
        "and coaching on request. You lead; InDE learns."
    ),
    "central_question": "What does my best work look like?",
    "origin": "InDE EMS v3.7.1, February 2026",

    # Transition philosophy - innovator-led
    "transition_philosophy": "emergent",
    "criteria_enforcement": "none",  # No gates, no criteria
    "backward_iteration": "open",    # Innovator can move freely

    # NO predefined phases - the innovator defines their own path
    "phases": [],

    # Empty transition criteria - manual transitions only
    "transition_criteria": {},

    # Coaching configuration - non-directive mode
    "coaching_config": {
        "mode": "NON_DIRECTIVE",
        "proactive_triggers_enabled": False,
        "socratic_questioning_enabled": False,   # Only on direct ask
        "convergence_detection_enabled": False,  # No convergence without methodology
        "methodology_vocabulary_visible": False,
        "available_on_request": True,            # Coach answers when asked
        "tag_interactions_as_influence": True,   # All coaching tagged for filtering
        "language_style": "supportive_responsive",
        "framing": "innovator_led",
        "backward_iteration": "open",
        "key_questions": [],  # No proactive questions
        "common_pitfalls": [],
        "convergence_moments": [],
    },

    # EMS configuration
    "ems_config": {
        "observation_enabled": True,
        "synthesis_threshold_pursuits": 3,       # Minimum pursuits before synthesis offered
        "high_confidence_threshold": 5,          # Pursuits for high-confidence synthesis
        "synthesis_trigger_on_completion": True,  # Offer synthesis when pursuit completes
        "synthesis_trigger_on_threshold": True,   # Offer when accumulation threshold reached
        "synthesis_trigger_manual": True,         # Innovator can request synthesis anytime
    },

    # Convergence config - disabled
    "convergence_config": {
        "min_phases_before_convergence": 0,
        "coach_checkpoint_weight": 0.0,
        "artifact_completion_weight": 0.0,
        "validation_weight": 0.0,
        "allow_phase_skip": True,
        "backward_iteration_enabled": True,
    },

    # Retrospective template - EMS-specific questions
    "retrospective_template": {
        "archetype_specific_questions": [
            "Looking back, what sequence of steps did you naturally follow?",
            "Were there any steps you consistently repeated? Why?",
            "If you were to advise someone else approaching a similar problem, what process would you recommend?",
            "What did you do differently from how others might have approached this?",
            "Was there a moment where your process surprised you - where you did something you didn't plan to do?",
        ],
        "questions": [
            "What was the most valuable insight you gained during this pursuit?",
            "What would you do differently if you started over?",
            "What tools or capabilities were most helpful?",
            "What was missing that would have helped?",
        ],
        "metrics_to_capture": [
            "observation_count",
            "tool_invocations",
            "decision_points",
            "time_in_each_state",
            "coaching_interactions",
        ],
    },

    # Metadata
    "metadata": {
        "added_version": "3.7.1",
        "documentation_url": "",
        "typical_duration_days": "varies",
        "best_for": [
            "Experienced innovators with established processes",
            "Novel problem domains without established methodologies",
            "Process discovery and methodology synthesis",
            "Those who want InDE's tools without prescriptive guidance",
        ],
        "less_suited_for": [
            "Novice innovators who need structure",
            "Regulated environments requiring documented process",
            "Team pursuits requiring coordination (initially)",
        ],
    },
}


# Non-directive coaching system prompt modifier
NON_DIRECTIVE_COACHING_MODIFIER = """
This innovator has chosen to work without a predefined methodology.
Your role is to be a RESPONSIVE coach, not a PROACTIVE one:

- Answer questions fully and helpfully when asked
- Do NOT initiate Socratic questioning unprompted
- Do NOT suggest next steps unless explicitly asked
- Do NOT reference methodology frameworks by name
- Do NOT suggest phase transitions or convergence
- If the innovator asks "what should I do next?", provide thoughtful
  guidance based on their context - but frame it as YOUR suggestion,
  not a methodology prescription
- If the innovator seems stuck, you may gently offer: "Would you
  like to talk through where you are?" - but only after a significant
  gap in activity (not proactively during active work)

You are an expert mentor who respects that this innovator has their
own process. Your job is to support it, not redirect it.
"""


# Confirmation message for ad-hoc pursuit creation
# v4.0: Updated to use goal vocabulary
ADHOC_CONFIRMATION_MESSAGE = """
Great - I'll let you lead the way.

All of InDE's tools are available to you: telling your story, identifying what
could get in the way, testing your assumptions, and everything else. I'll be
here if you need me, but I won't interrupt your flow with suggestions unless
you ask.

When your pursuit is complete, I can help you capture and name your approach
so others can learn from it.

Where would you like to start?
"""


# Synthesis eligibility message (shown when threshold reached)
SYNTHESIS_ELIGIBLE_MESSAGE = """
You've now completed {count} freeform pursuits. I've been observing your approach
across all of them, and I'm seeing some interesting patterns.

When you're ready, I can help you name and capture your methodology so others
can learn from it. Just say the word.
"""


# Pre-eligibility message (shown before threshold)
PRE_SYNTHESIS_MESSAGE = """
I've captured your process observations from this pursuit. After a few more
freeform pursuits, I'll be able to identify patterns in your approach.
"""


def is_adhoc_pursuit(pursuit: dict) -> bool:
    """Check if a pursuit is ad-hoc (freeform) mode."""
    return pursuit.get("archetype") == "ad_hoc"


def get_adhoc_confirmation() -> str:
    """Get the confirmation message for ad-hoc pursuit creation."""
    return ADHOC_CONFIRMATION_MESSAGE.strip()


def get_nondirective_modifier() -> str:
    """Get the non-directive coaching system prompt modifier."""
    return NON_DIRECTIVE_COACHING_MODIFIER.strip()


def get_synthesis_message(completed_pursuits: int, threshold: int = 3) -> str:
    """
    Get the appropriate synthesis message based on completed pursuit count.

    Args:
        completed_pursuits: Number of completed ad-hoc pursuits
        threshold: Minimum pursuits for synthesis eligibility

    Returns:
        Either the eligible or pre-eligible message
    """
    if completed_pursuits >= threshold:
        return SYNTHESIS_ELIGIBLE_MESSAGE.format(count=completed_pursuits).strip()
    return PRE_SYNTHESIS_MESSAGE.strip()
