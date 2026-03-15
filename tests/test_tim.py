"""
InDE MVP v3.0.1 - TIM Test Suite

Tests for the Temporal Intelligence Module:
1. TimeAllocationEngine - Phase distribution and time tracking
2. VelocityTracker - Progress velocity calculation
3. TemporalEventLogger - Event stream with IKF timestamps
4. PhaseManager - Phase transitions and detection
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
import unittest

# Set environment for test mode
os.environ["USE_MONGOMOCK"] = "true"

from core.database import Database
from tim import TimeAllocationEngine, VelocityTracker, TemporalEventLogger, PhaseManager
from core.config import IKF_PHASES, DEFAULT_PHASE_ALLOCATIONS


class TestTimeAllocationEngine(unittest.TestCase):
    """Tests for TimeAllocationEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database()
        self.engine = TimeAllocationEngine(self.db)

    def test_create_allocation(self):
        """Test creating a time allocation with default phases."""
        start = datetime.now(timezone.utc).isoformat() + 'Z'
        target = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat() + 'Z'

        allocation = self.engine.create_allocation(
            pursuit_id="test-pursuit-1",
            start_date=start,
            target_completion=target
        )

        self.assertIsNotNone(allocation)
        self.assertEqual(allocation["pursuit_id"], "test-pursuit-1")
        self.assertEqual(len(allocation["phase_allocations"]), 3)  # VISION, DE_RISK, DEPLOY

        # Check phase percentages match defaults
        for pa in allocation["phase_allocations"]:
            expected_pct = DEFAULT_PHASE_ALLOCATIONS.get(pa["phase"], 0)
            self.assertEqual(pa["percentage"], expected_pct)

    def test_get_remaining_time(self):
        """Test calculating remaining time."""
        start = datetime.now(timezone.utc).isoformat() + 'Z'
        target = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat() + 'Z'

        self.engine.create_allocation(
            pursuit_id="test-pursuit-2",
            start_date=start,
            target_completion=target
        )

        remaining = self.engine.get_remaining_time("test-pursuit-2")
        self.assertEqual(remaining["status"], "active")
        self.assertGreater(remaining["days_remaining"], 0)

    def test_override_allocation(self):
        """Test overriding phase allocations."""
        start = datetime.now(timezone.utc).isoformat() + 'Z'
        target = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat() + 'Z'

        self.engine.create_allocation(
            pursuit_id="test-pursuit-3",
            start_date=start,
            target_completion=target
        )

        # Override with custom percentages
        new_config = {"VISION": 20, "DE_RISK": 40, "DEPLOY": 30}
        result = self.engine.override_allocation(
            "test-pursuit-3", new_config, "Testing override"
        )

        self.assertTrue(result)

        allocation = self.engine.get_allocation("test-pursuit-3")
        self.assertTrue(allocation["is_overridden"])


class TestVelocityTracker(unittest.TestCase):
    """Tests for VelocityTracker."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database()
        self.allocation_engine = TimeAllocationEngine(self.db)
        self.tracker = VelocityTracker(self.db, self.allocation_engine)

    def test_calculate_velocity_no_data(self):
        """Test velocity calculation with no events."""
        velocity = self.tracker.calculate_velocity("nonexistent-pursuit")

        self.assertIn("elements_per_week", velocity)
        self.assertIn("status", velocity)

    def test_velocity_caching(self):
        """Test velocity caching behavior."""
        # First call
        v1 = self.tracker.calculate_velocity("test-pursuit-v1")

        # Second call should be cached
        v2 = self.tracker.calculate_velocity("test-pursuit-v1")

        # Both should be similar (cached)
        self.assertEqual(v1["elements_per_week"], v2["elements_per_week"])

        # Clear cache and verify
        self.tracker.clear_cache("test-pursuit-v1")


class TestTemporalEventLogger(unittest.TestCase):
    """Tests for TemporalEventLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database()
        self.logger = TemporalEventLogger(self.db)

    def test_log_pursuit_start(self):
        """Test logging pursuit start event."""
        event_id = self.logger.log_pursuit_start(
            pursuit_id="test-pursuit-e1",
            title="Test Pursuit",
            user_id="test-user"
        )

        self.assertIsNotNone(event_id)

        events = self.logger.get_event_stream("test-pursuit-e1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "PURSUIT_START")
        self.assertEqual(events[0]["phase"], "VISION")

    def test_log_element_captured(self):
        """Test logging element capture event."""
        event_id = self.logger.log_element_captured(
            pursuit_id="test-pursuit-e2",
            phase="VISION",
            element_type="vision",
            element_key="problem_statement",
            confidence=0.85
        )

        self.assertIsNotNone(event_id)

        events = self.logger.get_events_by_type("test-pursuit-e2", "ELEMENT_CAPTURED")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["metadata"]["element_key"], "problem_statement")

    def test_iso8601_timestamps(self):
        """Test that all timestamps are ISO 8601 format."""
        self.logger.log_pursuit_start("test-pursuit-e3", "Test")

        events = self.logger.get_event_stream("test-pursuit-e3")
        timestamp = events[0]["timestamp"]

        # Should end with Z (UTC)
        self.assertTrue(timestamp.endswith("Z"))

        # Should be parseable as ISO 8601
        ts_clean = timestamp.rstrip("Z")
        try:
            datetime.fromisoformat(ts_clean)
        except ValueError:
            self.fail(f"Timestamp {timestamp} is not valid ISO 8601")

    def test_get_timeline_summary(self):
        """Test timeline summary generation."""
        # Log several events
        self.logger.log_pursuit_start("test-pursuit-e4", "Test")
        self.logger.log_element_captured("test-pursuit-e4", "VISION", "vision", "problem_statement")
        self.logger.log_element_captured("test-pursuit-e4", "VISION", "vision", "target_user")
        self.logger.log_artifact_generated("test-pursuit-e4", "VISION", "vision", "art-1")

        summary = self.logger.get_timeline_summary("test-pursuit-e4")

        self.assertEqual(summary["total_events"], 4)
        self.assertIn("PURSUIT_START", summary["events_by_type"])
        self.assertIn("ELEMENT_CAPTURED", summary["events_by_type"])
        self.assertIn("VISION", summary["phases_touched"])


class TestPhaseManager(unittest.TestCase):
    """Tests for PhaseManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database()
        self.allocation_engine = TimeAllocationEngine(self.db)
        self.event_logger = TemporalEventLogger(self.db)
        self.manager = PhaseManager(
            self.db, self.allocation_engine, self.event_logger
        )

    def test_get_current_phase_default(self):
        """Test that default phase is VISION."""
        phase = self.manager.get_current_phase("new-pursuit")
        self.assertEqual(phase, "VISION")

    def test_detect_phase_transition(self):
        """Test phase transition detection."""
        # Simulate high vision completeness
        completeness = {"vision": 0.80, "fears": 0.10, "hypothesis": 0.05}

        suggestion = self.manager.detect_phase_transition("test-pursuit-p1", completeness)

        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion["from_phase"], "VISION")
        self.assertEqual(suggestion["to_phase"], "DE_RISK")
        self.assertEqual(suggestion["trigger"], "automatic")

    def test_execute_transition(self):
        """Test executing a phase transition."""
        # Create allocation first
        start = datetime.now(timezone.utc).isoformat() + 'Z'
        target = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat() + 'Z'
        self.allocation_engine.create_allocation("test-pursuit-p2", start, target)

        # Execute transition
        record = self.manager.execute_transition(
            pursuit_id="test-pursuit-p2",
            to_phase="DE_RISK",
            trigger="automatic",
            reason="Vision complete"
        )

        self.assertEqual(record["from_phase"], "VISION")
        self.assertEqual(record["to_phase"], "DE_RISK")

        # Verify phase changed
        current = self.manager.get_current_phase("test-pursuit-p2")
        self.assertEqual(current, "DE_RISK")

    def test_can_transition_to(self):
        """Test transition validation."""
        completeness = {"vision": 0.50, "fears": 0.0, "hypothesis": 0.0}

        # Can't transition with low completeness
        result = self.manager.can_transition_to("test-p3", "DE_RISK", completeness)
        self.assertFalse(result["allowed"])
        self.assertIn("requirements", result)

        # Can transition with high completeness
        completeness["vision"] = 0.80
        result = self.manager.can_transition_to("test-p3", "DE_RISK", completeness)
        self.assertTrue(result["allowed"])

    def test_get_phase_summary(self):
        """Test getting phase summary."""
        summary = self.manager.get_phase_summary("test-pursuit-p4")

        self.assertEqual(summary["current_phase"], "VISION")
        self.assertIn("phases", summary)
        self.assertEqual(len(summary["phases"]), 3)
        self.assertEqual(summary["phase_order"], IKF_PHASES)


class TestTIMIntegration(unittest.TestCase):
    """Integration tests for TIM components working together."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = Database()
        self.allocation_engine = TimeAllocationEngine(self.db)
        self.event_logger = TemporalEventLogger(self.db)
        self.velocity_tracker = VelocityTracker(self.db, self.allocation_engine)
        self.phase_manager = PhaseManager(
            self.db, self.allocation_engine, self.event_logger
        )

    def test_full_pursuit_lifecycle(self):
        """Test TIM through a simulated pursuit lifecycle."""
        pursuit_id = "integration-test-1"

        # 1. Create allocation
        start = datetime.now(timezone.utc).isoformat() + 'Z'
        target = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat() + 'Z'
        allocation = self.allocation_engine.create_allocation(pursuit_id, start, target)
        self.assertIsNotNone(allocation)

        # 2. Log pursuit start
        self.event_logger.log_pursuit_start(pursuit_id, "Integration Test Pursuit")

        # 3. Log some element captures
        for i in range(5):
            self.event_logger.log_element_captured(
                pursuit_id, "VISION", "vision", f"element_{i}"
            )

        # 4. Check velocity
        velocity = self.velocity_tracker.calculate_velocity(pursuit_id)
        self.assertIn("elements_per_week", velocity)

        # 5. Simulate phase transition
        completeness = {"vision": 0.80, "fears": 0.10, "hypothesis": 0.05}
        transition = self.phase_manager.detect_phase_transition(pursuit_id, completeness)
        self.assertIsNotNone(transition)

        if transition:
            self.phase_manager.execute_transition(
                pursuit_id, transition["to_phase"], transition["trigger"]
            )

        # 6. Verify current phase
        current = self.phase_manager.get_current_phase(pursuit_id)
        self.assertEqual(current, "DE_RISK")

        # 7. Check timeline
        summary = self.event_logger.get_timeline_summary(pursuit_id)
        self.assertGreater(summary["total_events"], 5)


if __name__ == "__main__":
    print("=" * 60)
    print("InDE MVP v3.0.1 - TIM Test Suite")
    print("=" * 60)

    # Run tests
    unittest.main(verbosity=2)
