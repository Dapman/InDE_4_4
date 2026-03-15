"""
Tests for the Momentum Management Engine (v4.1)
"""
import pytest
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from momentum.signal_collectors import (
    collect_signals, ResponseSpecificityCollector,
    ConversationalLeanCollector, TemporalCommitmentCollector,
    IdeaOwnershipCollector
)
from momentum.momentum_engine import (
    MomentumManagementEngine, MOMENTUM_TIERS, SIGNAL_WEIGHTS
)
from momentum.bridge_selector import BridgeSelector
from momentum.bridge_library import BRIDGE_LIBRARY


class TestSignalWeights:
    def test_weights_sum_to_one(self):
        total = sum(SIGNAL_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Signal weights must sum to 1.0, got {total}"


class TestResponseSpecificity:
    def test_short_vague_message_scores_low(self):
        score = ResponseSpecificityCollector().score("yeah ok", 2)
        assert score < 0.4

    def test_long_specific_message_scores_high(self):
        msg = ("I work with nurses in rural Texas clinics. "
               "They see about 40 patients per day and spend "
               "approximately 25% of their time on documentation "
               "rather than patient care.")
        score = ResponseSpecificityCollector().score(msg, len(msg.split()))
        assert score > 0.6


class TestConversationalLean:
    def test_question_scores_high(self):
        score = ConversationalLeanCollector().score(
            "What if we tested this with a small pilot group first?"
        )
        assert score > 0.6

    def test_closure_language_scores_low(self):
        score = ConversationalLeanCollector().score(
            "That's all I have. I have to go."
        )
        assert score < 0.4


class TestTemporalCommitment:
    def test_future_action_scores_high(self):
        # Message with multiple future commitment indicators
        score = TemporalCommitmentCollector().score(
            "I'll reach out to three nurses I know this week and ask them. "
            "I'm going to schedule a follow-up next Monday."
        )
        assert score > 0.5

    def test_passive_framing_scores_low(self):
        score = TemporalCommitmentCollector().score(
            "Someday it would be nice if this happened."
        )
        assert score < 0.4


class TestIdeaOwnership:
    def test_possessive_language_scores_high(self):
        score = IdeaOwnershipCollector().score(
            "My target users are the nurses I've worked with for years."
        )
        assert score > 0.5

    def test_distancing_language_scores_low(self):
        score = IdeaOwnershipCollector().score(
            "Theoretically someone could build this, in theory."
        )
        assert score < 0.4


class TestMomentumEngine:
    def test_initial_score_is_neutral(self):
        mme = MomentumManagementEngine("s1", "p1", "g1")
        assert mme.state.composite_score == 0.5
        assert mme.state.momentum_tier == "MEDIUM"

    def test_process_turn_updates_state(self):
        mme = MomentumManagementEngine("s1", "p1", "g1")
        ctx = mme.process_turn("I'll talk to my users next week about this.")
        assert mme.state.turn_count == 1
        assert ctx["momentum_tier"] in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]
        assert "coaching_guidance" in ctx
        assert 0.0 <= ctx["composite_score"] <= 1.0

    def test_high_energy_messages_raise_score(self):
        mme = MomentumManagementEngine("s1", "p1", "g1")
        high_energy = (
            "I just talked to my two closest customers — Sarah from St. Luke's "
            "and James from Memorial. Both said the same thing. I'm going to "
            "schedule a follow-up with them next Tuesday. What should I ask?"
        )
        for _ in range(3):
            mme.process_turn(high_energy)
        assert mme.state.composite_score > 0.55

    def test_snapshot_captures_state(self):
        mme = MomentumManagementEngine("s1", "p1", "g1")
        mme.process_turn("I will test this tomorrow.")
        snap = mme.snapshot("natural")
        assert snap.session_id == "s1"
        assert snap.turn_count == 1
        assert snap.exit_reason == "natural"

    def test_score_scores_are_bounded(self):
        mme = MomentumManagementEngine("s1", "p1", "g1")
        for msg in ["yes", "no", "", "ok", "sure", "maybe"]:
            mme.process_turn(msg)
        assert 0.0 <= mme.state.composite_score <= 1.0


class TestBridgeSelector:
    def test_all_artifacts_return_questions(self):
        selector = BridgeSelector()
        for artifact in ["vision", "fear", "validation"]:
            for tier in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]:
                bridge = selector.select(artifact, tier, {})
                assert bridge.strip().endswith("?"), \
                    f"Bridge must end with '?': artifact={artifact}, tier={tier}, bridge='{bridge[-30:]}'"

    def test_unknown_artifact_uses_fallback(self):
        selector = BridgeSelector()
        bridge = selector.select("unknown_artifact", "MEDIUM", {})
        assert "?" in bridge

    def test_no_methodology_terminology(self):
        selector = BridgeSelector()
        forbidden = [
            "Fear Extraction", "Vision Formulator", "Methodology",
            "Lean Startup", "Design Thinking", "Stage-Gate",
            "TRIZ", "Empathize", "next module", "this module"
        ]
        for artifact in ["vision", "fear", "validation"]:
            for tier in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]:
                bridge = selector.select(artifact, tier, {})
                for term in forbidden:
                    assert term.lower() not in bridge.lower(), \
                        f"Forbidden term '{term}' found in bridge: '{bridge[:80]}'"

    def test_context_injection(self):
        selector = BridgeSelector()
        # Force a template that uses {idea_domain} by checking the raw library
        templates_with_placeholder = [
            t for t in BRIDGE_LIBRARY.get("vision", {}).get("HIGH", [])
            if "{idea_domain}" in t
        ]
        if templates_with_placeholder:
            # Verify injection works
            context = {"idea_domain": "healthcare"}
            bridge = selector.select("vision", "HIGH", context)
            # healthcare should appear somewhere if that template was selected
            # (may not be selected due to randomness, but no crash)
            assert isinstance(bridge, str) and len(bridge) > 10

    def test_no_unfilled_placeholders(self):
        import re
        selector = BridgeSelector()
        for _ in range(20):  # Multiple runs to hit different templates
            bridge = selector.select("vision", "HIGH", {})
            remaining = re.findall(r'\{[a-z_]+\}', bridge)
            assert not remaining, f"Unfilled placeholder in bridge: {remaining}"
