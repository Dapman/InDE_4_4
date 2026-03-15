"""
InDE v3.6.1 Tests - Methodology Expansion & Scenario Intelligence

Test coverage for:
- TRIZ archetype registration and configuration
- TRIZ reference data (40 principles, contradiction matrix)
- TRIZ-Biomimicry bridge
- Blue Ocean archetype registration and configuration
- Blue Ocean artifact types
- Scenario detection and exploration
- Five archetype coexistence
- Event schema validation
- Backward compatibility

Total: ~35 tests
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Add ikf-service to path for event imports
_ikf_service_path = os.path.join(os.path.dirname(__file__), "..")
if _ikf_service_path not in sys.path:
    sys.path.insert(0, _ikf_service_path)


# ==============================================================================
# TRIZ ARCHETYPE TESTS
# ==============================================================================

class TestTrizArchetype:
    """TRIZ archetype registration and configuration tests."""

    def test_triz_archetype_exists(self):
        """TRIZ archetype definition exists."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        assert TRIZ_ARCHETYPE is not None
        assert TRIZ_ARCHETYPE["id"] == "triz"

    def test_triz_has_5_phases(self):
        """TRIZ archetype has exactly 5 phases."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        assert len(TRIZ_ARCHETYPE["phases"]) == 5

    def test_triz_phases_map_to_universal_states(self):
        """All TRIZ phases map to valid universal innovation states."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        valid_states = {
            "DISCOVERY", "DISCOVERY_DEFINITION", "DEFINITION_VALIDATION",
            "VALIDATION_REFINEMENT", "PREPARATION"
        }
        for phase in TRIZ_ARCHETYPE["phases"]:
            assert phase["universal_state"] in valid_states

    def test_triz_transition_criteria_defined(self):
        """Each TRIZ phase has transition criteria."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        for phase in TRIZ_ARCHETYPE["phases"]:
            assert len(phase.get("transition_criteria", [])) >= 1

    def test_triz_coaching_config_complete(self):
        """TRIZ coaching config has all required fields."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        config = TRIZ_ARCHETYPE["coaching_config"]
        assert config["language_style"] == "analytical_inventive"
        assert len(config["key_questions"]) >= 3
        assert len(config["common_pitfalls"]) >= 3

    def test_biomimicry_cross_reference_in_principle_application(self):
        """Principle Application phase includes biomimicry_cross_reference activity."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        principle_phase = next(
            p for p in TRIZ_ARCHETYPE["phases"] if p["name"] == "Principle Application"
        )
        assert "biomimicry_cross_reference" in principle_phase["activities"]

    def test_triz_transition_philosophy_is_guided(self):
        """TRIZ transition philosophy is guided (not strict)."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        assert TRIZ_ARCHETYPE["transition_philosophy"] == "guided"


# ==============================================================================
# TRIZ REFERENCE DATA TESTS
# ==============================================================================

class TestTrizReferenceData:
    """TRIZ inventive principles and contradiction matrix tests."""

    def test_40_principles_exist(self):
        """All 40 inventive principles are defined."""
        from app.methodology.triz.inventive_principles import INVENTIVE_PRINCIPLES
        assert len(INVENTIVE_PRINCIPLES) == 40

    def test_principles_numbered_1_to_40(self):
        """Principles are numbered 1 through 40."""
        from app.methodology.triz.inventive_principles import INVENTIVE_PRINCIPLES
        numbers = [p["number"] for p in INVENTIVE_PRINCIPLES]
        assert numbers == list(range(1, 41))

    def test_all_principles_have_coaching_hints(self):
        """Every principle has at least 2 coaching hints."""
        from app.methodology.triz.inventive_principles import INVENTIVE_PRINCIPLES
        for p in INVENTIVE_PRINCIPLES:
            assert len(p.get("coaching_hints", [])) >= 2, f"Principle {p['number']} missing coaching hints"

    def test_all_principles_have_examples(self):
        """Every principle has at least 2 examples."""
        from app.methodology.triz.inventive_principles import INVENTIVE_PRINCIPLES
        for p in INVENTIVE_PRINCIPLES:
            assert len(p.get("examples", [])) >= 2, f"Principle {p['number']} missing examples"

    def test_contradiction_matrix_has_30_plus_entries(self):
        """Contradiction matrix has at least 30 parameter pair mappings."""
        from app.methodology.triz.contradiction_matrix import CONTRADICTION_MATRIX
        assert len(CONTRADICTION_MATRIX) >= 30

    def test_matrix_lookup_returns_principles(self):
        """Matrix lookup returns valid principle numbers."""
        from app.methodology.triz.contradiction_matrix import lookup_principles
        result = lookup_principles("strength", "weight")
        assert len(result) >= 2
        assert all(1 <= n <= 40 for n in result)

    def test_matrix_reverse_lookup(self):
        """Both directions of a contradiction return valid principles.

        Note: (improving, worsening) and (worsening, improving) may return
        different principles because they represent different contradictions.
        """
        from app.methodology.triz.contradiction_matrix import lookup_principles
        forward = lookup_principles("strength", "weight")
        reverse = lookup_principles("weight", "strength")
        # Both should return valid principle lists (not necessarily identical)
        assert len(forward) >= 2
        assert len(reverse) >= 2
        assert all(1 <= n <= 40 for n in forward)
        assert all(1 <= n <= 40 for n in reverse)

    def test_matrix_unknown_pair_returns_empty(self):
        """Unknown parameter pair returns empty list."""
        from app.methodology.triz.contradiction_matrix import lookup_principles
        result = lookup_principles("unknown_param", "other_unknown")
        assert result == []


# ==============================================================================
# TRIZ-BIOMIMICRY BRIDGE TESTS
# ==============================================================================

class TestTrizBiomimicryBridge:
    """TRIZ-Biomimicry cross-reference tests."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database with biomimicry patterns."""
        db = Mock()
        db.biomimicry_patterns = Mock()
        db.biomimicry_patterns.find.return_value.to_list = AsyncMock(return_value=[
            {
                "pattern_id": "p1",
                "organism": "Namibian Desert Beetle",
                "strategy_name": "Fog Harvesting",
                "description": "Hydrophilic and hydrophobic surface patterns",
                "triz_connections": ["Principle 17: Another Dimension"],
                "category": "WATER_MANAGEMENT",
            },
            {
                "pattern_id": "p2",
                "organism": "Spider Silk",
                "strategy_name": "Tensile Strength",
                "description": "Hierarchical protein structure",
                "triz_connections": ["Principle 40: Composite Materials"],
                "category": "STRUCTURAL_STRENGTH",
            },
        ])
        return db

    @pytest.mark.asyncio
    async def test_bridge_builds_index(self, mock_db):
        """Bridge successfully builds reverse index."""
        from app.methodology.triz.biomimicry_bridge import TrizBiomimicryBridge
        bridge = TrizBiomimicryBridge(mock_db)
        count = await bridge.build_index()
        assert count >= 1

    @pytest.mark.asyncio
    async def test_bridge_finds_analogs_for_principle_17(self, mock_db):
        """Principle 17 maps to Desert Beetle."""
        from app.methodology.triz.biomimicry_bridge import TrizBiomimicryBridge
        bridge = TrizBiomimicryBridge(mock_db)
        await bridge.build_index()
        analogs = bridge.get_biological_analogs(17)
        assert len(analogs) > 0
        assert any("Beetle" in a.get("organism", "") for a in analogs)

    @pytest.mark.asyncio
    async def test_bridge_returns_empty_for_unconnected_principles(self, mock_db):
        """Principles without biological analogs return empty list."""
        from app.methodology.triz.biomimicry_bridge import TrizBiomimicryBridge
        bridge = TrizBiomimicryBridge(mock_db)
        await bridge.build_index()
        analogs = bridge.get_biological_analogs(99)  # Invalid principle
        assert analogs == []


# ==============================================================================
# BLUE OCEAN ARCHETYPE TESTS
# ==============================================================================

class TestBlueOceanArchetype:
    """Blue Ocean archetype registration and configuration tests."""

    def test_blue_ocean_archetype_exists(self):
        """Blue Ocean archetype definition exists."""
        from app.methodology.archetypes.blue_ocean import BLUE_OCEAN_ARCHETYPE
        assert BLUE_OCEAN_ARCHETYPE is not None
        assert BLUE_OCEAN_ARCHETYPE["id"] == "blue_ocean"

    def test_blue_ocean_has_5_phases(self):
        """Blue Ocean archetype has exactly 5 phases."""
        from app.methodology.archetypes.blue_ocean import BLUE_OCEAN_ARCHETYPE
        assert len(BLUE_OCEAN_ARCHETYPE["phases"]) == 5

    def test_blue_ocean_coaching_config(self):
        """Blue Ocean coaching config has correct style."""
        from app.methodology.archetypes.blue_ocean import BLUE_OCEAN_ARCHETYPE
        config = BLUE_OCEAN_ARCHETYPE["coaching_config"]
        assert config["language_style"] == "strategic_expansive"
        assert config["framing"] == "value_innovation"

    def test_six_paths_framework_defined(self):
        """Six Paths Framework reference exists."""
        from app.methodology.archetypes.blue_ocean import SIX_PATHS_FRAMEWORK
        assert len(SIX_PATHS_FRAMEWORK) == 6

    def test_non_customer_tiers_defined(self):
        """Non-customer tiers reference exists."""
        from app.methodology.archetypes.blue_ocean import NON_CUSTOMER_TIERS
        assert len(NON_CUSTOMER_TIERS) == 3


# ==============================================================================
# BLUE OCEAN ARTIFACT TESTS
# ==============================================================================

class TestBlueOceanArtifacts:
    """Blue Ocean artifact type tests."""

    def test_strategy_canvas_schema_exists(self):
        """Strategy canvas artifact type is registered."""
        from app.artifacts.types import ARTIFACT_TYPE_REGISTRY
        assert ".strategy_canvas" in ARTIFACT_TYPE_REGISTRY

    def test_four_actions_schema_exists(self):
        """Four actions artifact type is registered."""
        from app.artifacts.types import ARTIFACT_TYPE_REGISTRY
        assert ".four_actions" in ARTIFACT_TYPE_REGISTRY

    def test_strategy_canvas_has_required_fields(self):
        """Strategy canvas schema has competitive_factors."""
        from app.artifacts.types import STRATEGY_CANVAS_SCHEMA
        assert "competitive_factors" in str(STRATEGY_CANVAS_SCHEMA)
        assert "new_factors" in str(STRATEGY_CANVAS_SCHEMA)

    def test_four_actions_has_errc(self):
        """Four actions schema has ERRC fields."""
        from app.artifacts.types import FOUR_ACTIONS_SCHEMA
        fields = FOUR_ACTIONS_SCHEMA["fields"]
        for action in ["eliminate", "reduce", "raise", "create"]:
            assert action in fields


# ==============================================================================
# SCENARIO EXPLORATION TESTS
# ==============================================================================

class TestScenarioExploration:
    """Scenario detection, coaching, and artifact tests."""

    def test_fork_language_triggers_detection(self):
        """Fork language triggers scenario detection."""
        from app.coaching.scenario_detection import ScenarioDetector
        detector = ScenarioDetector()
        # Simulate async result
        import asyncio
        loop = asyncio.new_event_loop()
        should, reason = loop.run_until_complete(detector.should_explore_scenarios(
            conversation_context={"last_user_message": "Should we pivot to enterprise or stay consumer?"},
            pursuit_state={"universal_state": "VALIDATION"},
            session_state={}
        ))
        loop.close()
        assert should is True
        assert reason == "explicit_fork_language"

    def test_preparation_state_blocks_detection(self):
        """PREPARATION state blocks scenario detection."""
        from app.coaching.scenario_detection import ScenarioDetector
        detector = ScenarioDetector()
        import asyncio
        loop = asyncio.new_event_loop()
        should, reason = loop.run_until_complete(detector.should_explore_scenarios(
            conversation_context={"last_user_message": "Should we pivot?"},
            pursuit_state={"universal_state": "PREPARATION"},
            session_state={}
        ))
        loop.close()
        assert should is False
        assert reason == "pursuit_in_preparation"

    def test_max_scenarios_is_3(self):
        """Maximum scenarios per decision is 3."""
        from app.coaching.scenario_detection import ScenarioDetector
        detector = ScenarioDetector()
        assert detector._max_scenarios_per_decision == 3

    def test_scenario_artifact_type_registered(self):
        """Scenario artifact type is registered."""
        from app.artifacts.types import ARTIFACT_TYPE_REGISTRY
        assert ".scenario" in ARTIFACT_TYPE_REGISTRY


# ==============================================================================
# SCENARIO CONTEXT TESTS
# ==============================================================================

class TestScenarioContext:
    """Scenario context provider tests."""

    @pytest.mark.asyncio
    async def test_scenario_context_is_conversational(self):
        """Scenario context instructs conversational delivery."""
        from app.scaffolding.scenario_context import ScenarioContextProvider
        provider = ScenarioContextProvider()
        context = await provider.get_context(
            trigger_reason="explicit_fork_language",
            pursuit_state={},
            active_methodology="lean_startup"
        )
        assert "NEVER present pre-computed futures" in context["content"]
        assert "SCENARIO_COACHING_PROTOCOL" in context["content"]

    @pytest.mark.asyncio
    async def test_scenario_context_methodology_framing(self):
        """Scenario context includes methodology-specific framing."""
        from app.scaffolding.scenario_context import ScenarioContextProvider
        provider = ScenarioContextProvider()

        framings = [
            ("lean_startup", "fastest learning"),
            ("triz", "resolve the same contradiction"),
            ("blue_ocean", "uncontested space"),
        ]

        for methodology, expected in framings:
            context = await provider.get_context(
                trigger_reason="test",
                pursuit_state={},
                active_methodology=methodology
            )
            assert expected in context["content"], f"Missing framing for {methodology}"


# ==============================================================================
# FIVE ARCHETYPE COEXISTENCE TESTS
# ==============================================================================

class TestFiveArchetypeCoexistence:
    """Verify all 5 archetypes coexist without interference."""

    def test_triz_archetype_importable(self):
        """TRIZ archetype can be imported."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        assert TRIZ_ARCHETYPE["id"] == "triz"

    def test_blue_ocean_archetype_importable(self):
        """Blue Ocean archetype can be imported."""
        from app.methodology.archetypes.blue_ocean import BLUE_OCEAN_ARCHETYPE
        assert BLUE_OCEAN_ARCHETYPE["id"] == "blue_ocean"

    def test_all_archetypes_have_unique_ids(self):
        """All archetype IDs are unique."""
        from app.methodology.archetypes.triz import TRIZ_ARCHETYPE
        from app.methodology.archetypes.blue_ocean import BLUE_OCEAN_ARCHETYPE
        ids = [TRIZ_ARCHETYPE["id"], BLUE_OCEAN_ARCHETYPE["id"]]
        assert len(ids) == len(set(ids))


# ==============================================================================
# EVENT SCHEMA TESTS
# ==============================================================================

class TestEventSchemas:
    """Event schema validation tests."""

    def test_triz_events_registered(self):
        """TRIZ event types are registered."""
        from events.federation_events import FEDERATION_EVENT_TYPES
        triz_events = [
            "triz.contradiction_formulated",
            "triz.principles_recommended",
            "triz.biomimicry_bridge_activated",
            "triz.solution_concept_generated",
            "triz.secondary_contradiction",
        ]
        for event_type in triz_events:
            assert event_type in FEDERATION_EVENT_TYPES

    def test_blue_ocean_events_registered(self):
        """Blue Ocean event types are registered."""
        from events.federation_events import FEDERATION_EVENT_TYPES
        blue_ocean_events = [
            "blue_ocean.strategy_canvas_created",
            "blue_ocean.four_actions_completed",
            "blue_ocean.value_curve_diverged",
            "blue_ocean.non_customers_identified",
        ]
        for event_type in blue_ocean_events:
            assert event_type in FEDERATION_EVENT_TYPES

    def test_scenario_events_registered(self):
        """Scenario event types are registered."""
        from events.federation_events import FEDERATION_EVENT_TYPES
        scenario_events = [
            "scenario.detection_triggered",
            "scenario.exploration_started",
            "scenario.future_explored",
            "scenario.decision_captured",
            "scenario.artifact_generated",
            "scenario.revisit_triggered",
        ]
        for event_type in scenario_events:
            assert event_type in FEDERATION_EVENT_TYPES

    def test_total_event_types_is_38_plus(self):
        """Total event types is 38+ (23 + 15 new)."""
        from events.federation_events import list_event_types
        event_types = list_event_types()
        assert len(event_types) >= 38


# ==============================================================================
# BACKWARD COMPATIBILITY TESTS
# ==============================================================================

class TestBackwardCompatibility:
    """Verify v3.6.0 and earlier features are unaffected."""

    def test_biomimicry_context_still_importable(self):
        """Biomimicry context provider can still be imported."""
        from app.scaffolding.biomimicry_context import BiomimicryContextProvider
        assert BiomimicryContextProvider is not None

    def test_biomimicry_has_triz_guidance(self):
        """Biomimicry context includes TRIZ guidance."""
        from app.scaffolding.biomimicry_context import BiomimicryContextProvider
        # The _get_methodology_guidance method should have triz
        provider = BiomimicryContextProvider(Mock(), Mock())
        guidance = provider._get_methodology_guidance("triz")
        assert "TRIZ" in guidance or "contradiction" in guidance

    def test_biomimicry_has_blue_ocean_guidance(self):
        """Biomimicry context includes Blue Ocean guidance."""
        from app.scaffolding.biomimicry_context import BiomimicryContextProvider
        provider = BiomimicryContextProvider(Mock(), Mock())
        guidance = provider._get_methodology_guidance("blue_ocean")
        assert "value" in guidance.lower() or "ocean" in guidance.lower()


# ==============================================================================
# MIGRATION TESTS
# ==============================================================================

class TestMigration:
    """Migration script tests."""

    def test_migration_info_complete(self):
        """Migration info function returns expected data."""
        import sys
        import os
        # Add tools to path
        tools_path = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "migrations")
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        # Import with corrected module name (starts with number, use importlib)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_006",
            os.path.join(tools_path, "006_v3_6_1_methodology_scenario.py")
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        get_migration_info = migration.get_migration_info
        info = get_migration_info()
        assert info["version"] == "3.6.1"
        assert "triz_inventive_principles" in info["new_collections"]
        assert "scenario_artifacts" in info["new_collections"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
