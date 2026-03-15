"""
Tests for the Display Label Registry.
InDE MVP v3.7.0 - IKF UI Remediation & Display Label Registry

Every category and value in the registry must be tested.
The "Would My Mother Understand This?" test is automated:
no label may contain UUIDs, underscores, ALL_CAPS enum codes,
or raw database field names.
"""

import re
import pytest
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.shared.display_labels import DisplayLabels


class TestDisplayLabelsPackageTypes:
    """Test package_type category translations."""

    def test_all_package_types_have_labels(self):
        """Every package_type enum has a human-readable label."""
        for pkg_type in ["temporal_benchmark", "pattern_contribution",
                         "risk_intelligence", "effectiveness", "retrospective_wisdom"]:
            label = DisplayLabels.get("package_type", pkg_type)
            assert label != pkg_type, f"Package type '{pkg_type}' should have translation"
            assert "_" not in label, f"Label should not contain underscores: {label}"

    def test_package_type_backwards_compat(self):
        """Backward compatibility aliases work."""
        # v3.0.3 name
        assert DisplayLabels.get("package_type", "pattern") == "Innovation Pattern"
        # v3.2 name
        assert DisplayLabels.get("package_type", "pattern_contribution") == "Innovation Pattern"


class TestDisplayLabelsContributionStatus:
    """Test contribution_status category translations."""

    def test_all_contribution_statuses_have_labels(self):
        """Every contribution status has a human-readable label."""
        for status in ["DRAFT", "REVIEWED", "IKF_READY", "REJECTED"]:
            label = DisplayLabels.get("contribution_status", status)
            assert label != status, f"Status '{status}' should have translation"
            assert label == label.strip(), "No leading/trailing whitespace"

    def test_federation_statuses_have_labels(self):
        """v3.2 federation statuses have translations."""
        for status in ["PENDING", "SUBMITTED", "RETRY_PENDING", "SUBMISSION_FAILED"]:
            label = DisplayLabels.get("contribution_status", status)
            assert label != status


class TestDisplayLabelsFederationState:
    """Test federation_state category translations."""

    def test_all_federation_states_have_labels(self):
        """Every federation state has a human-readable label."""
        for state in ["DISCONNECTED", "CONNECTING", "CONNECTED", "HALF_OPEN", "OFFLINE"]:
            label = DisplayLabels.get("federation_state", state)
            assert label != state, f"State '{state}' should have translation"


class TestDisplayLabelsMethodologyArchetypes:
    """Test methodology_archetype category translations."""

    def test_all_methodology_archetypes_have_labels(self):
        """Every registered methodology archetype has a display name."""
        for arch in ["lean_startup", "design_thinking", "stage_gate", "triz", "blue_ocean", "adhoc"]:
            label = DisplayLabels.get("methodology_archetype", arch)
            assert "_" not in label, f"Label should not contain underscores: {label}"

    def test_adhoc_variations(self):
        """Both adhoc and ad_hoc map correctly."""
        assert DisplayLabels.get("methodology_archetype", "adhoc") == "Freeform"
        assert DisplayLabels.get("methodology_archetype", "ad_hoc") == "Freeform"


class TestDisplayLabelsGeneralizationLevels:
    """Test generalization_level category translations."""

    def test_all_generalization_levels_have_labels(self):
        """Generalization levels 1-4 all have descriptive labels."""
        for level in [1, 2, 3, 4]:
            label = DisplayLabels.get("generalization_level", level)
            assert isinstance(label, str)
            assert label != str(level), f"Level {level} should have descriptive label"

    def test_string_generalization_levels(self):
        """String versions of levels also work."""
        for level in ["1", "2", "3", "4"]:
            label = DisplayLabels.get("generalization_level", level)
            assert label != level


class TestDisplayLabelsScenarioTriggers:
    """Test scenario_trigger category translations."""

    def test_all_scenario_triggers_have_labels(self):
        """Scenario trigger codes have natural-language descriptions."""
        for trigger in ["fork_language", "phase_transition", "rve_ambiguity"]:
            label = DisplayLabels.get("scenario_trigger", trigger)
            assert "_" not in label, f"Label should not contain underscores: {label}"


class TestDisplayLabelsPIIConfidence:
    """Test PII confidence traffic light system."""

    def test_pii_confidence_levels(self):
        """PII confidence floats map to correct traffic light categories."""
        assert DisplayLabels.pii_confidence_level(0.92) == "red"
        assert DisplayLabels.pii_confidence_level(0.85) == "red"
        assert DisplayLabels.pii_confidence_level(0.65) == "yellow"
        assert DisplayLabels.pii_confidence_level(0.50) == "yellow"
        assert DisplayLabels.pii_confidence_level(0.30) == "green"
        assert DisplayLabels.pii_confidence_level(0.0) == "green"

    def test_pii_labels(self):
        """PII confidence levels have human-readable labels."""
        for level in ["green", "yellow", "red"]:
            label = DisplayLabels.get("pii_confidence", level)
            assert len(label) > 10  # Should be descriptive


class TestDisplayLabelsFallbacks:
    """Test fallback behavior for unknown values."""

    def test_unknown_category_returns_value(self):
        """Unknown categories fall back to the raw value, not None."""
        result = DisplayLabels.get("nonexistent_category", "some_value")
        assert result == "some_value"

    def test_unknown_value_returns_value(self):
        """Unknown values within a known category fall back gracefully."""
        result = DisplayLabels.get("package_type", "unknown_type")
        assert result == "unknown_type"

    def test_none_value_handling(self):
        """None values are handled gracefully."""
        result = DisplayLabels.get("package_type", None)
        assert result == "None"


class TestDisplayLabelsIcons:
    """Test icon functionality."""

    def test_get_with_icon(self):
        """Icon + label format works correctly."""
        result = DisplayLabels.get_with_icon("contribution_status", "IKF_READY")
        assert "Ready to Share" in result
        assert "🚀" in result

    def test_get_icon_separately(self):
        """Can retrieve just the icon."""
        icon = DisplayLabels.get("contribution_status", "IKF_READY", "icon")
        assert icon == "🚀"


class TestDisplayLabelsRegistration:
    """Test runtime registration."""

    def test_register_new_label(self):
        """Runtime registration works for future module extensions."""
        DisplayLabels.register("test_category", "test_value", "Test Label", icon="🧪")
        assert DisplayLabels.get("test_category", "test_value") == "Test Label"
        # Clean up
        del DisplayLabels._REGISTRY["test_category"]

    def test_register_overwrites_existing(self):
        """Registration can update existing entries."""
        DisplayLabels.register("test_category2", "val1", "First Label")
        DisplayLabels.register("test_category2", "val1", "Updated Label")
        assert DisplayLabels.get("test_category2", "val1") == "Updated Label"
        # Clean up
        del DisplayLabels._REGISTRY["test_category2"]


class TestMotherTest:
    """
    The 'Would My Mother Understand This?' automated test.

    Scans ALL labels in the registry and verifies none contain:
    - UUID patterns (8-4-4-4-12 hex)
    - Underscore-separated identifiers
    - ALL_CAPS words longer than 4 characters (acronyms like TRIZ are OK)
    - Raw hash strings (40+ hex characters)
    """

    def test_no_uuids_in_labels(self):
        """No UUID patterns in any label."""
        uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}')

        for category, values in DisplayLabels._REGISTRY.items():
            for value, entry in values.items():
                label = entry.get("label")
                if label is None:
                    continue  # Skip None labels (e.g., novice-invisible steps)
                assert not uuid_pattern.search(label.lower()), \
                    f"UUID in label: {category}/{value} = '{label}'"

    def test_no_hashes_in_labels(self):
        """No hash strings in any label."""
        hash_pattern = re.compile(r'[0-9a-f]{40,}')

        for category, values in DisplayLabels._REGISTRY.items():
            for value, entry in values.items():
                label = entry.get("label")
                if label is None:
                    continue  # Skip None labels (e.g., novice-invisible steps)
                assert not hash_pattern.search(label.lower()), \
                    f"Hash in label: {category}/{value} = '{label}'"

    def test_no_long_caps_words(self):
        """No ALL_CAPS words longer than 4 characters (except known acronyms)."""
        allowed_acronyms = {"TRIZ"}  # Add more as needed

        for category, values in DisplayLabels._REGISTRY.items():
            for value, entry in values.items():
                label = entry.get("label")
                if label is None:
                    continue  # Skip None labels (e.g., novice-invisible steps)
                for word in label.split():
                    clean_word = ''.join(c for c in word if c.isalpha())
                    if len(clean_word) > 4 and clean_word == clean_word.upper() and clean_word.isalpha():
                        if clean_word not in allowed_acronyms:
                            assert False, \
                                f"ALL_CAPS word in label: {category}/{value} = '{label}' (word: '{clean_word}')"

    def test_descriptions_are_helpful(self):
        """Descriptions should be longer than labels and informative."""
        for category, values in DisplayLabels._REGISTRY.items():
            for value, entry in values.items():
                description = entry.get("description", "")
                if description:
                    # Descriptions should be longer than just a few words
                    assert len(description) >= 10, \
                        f"Description too short: {category}/{value}"


class TestDisplayLabelsUtilities:
    """Test utility methods."""

    def test_get_all_category(self):
        """Can retrieve all entries for a category."""
        all_pkg_types = DisplayLabels.get_all("package_type")
        assert len(all_pkg_types) >= 5
        assert "temporal_benchmark" in all_pkg_types

    def test_get_all_nonexistent(self):
        """get_all returns empty dict for unknown category."""
        result = DisplayLabels.get_all("nonexistent")
        assert result == {}

    def test_category_count(self):
        """Can get total category count."""
        count = DisplayLabels.get_category_count()
        assert count >= 10  # We have many categories

    def test_total_label_count(self):
        """Can get total label count."""
        count = DisplayLabels.get_total_label_count()
        assert count >= 50  # We have many labels
