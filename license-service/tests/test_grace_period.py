"""
Tests for InDE License Grace Period State Machine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
import json
from datetime import datetime, timezone, timedelta

from grace_period import GracePeriodManager
from models import GracePeriodState


class TestGracePeriodStates:
    """Test grace period state transitions."""

    @pytest.fixture
    def manager(self):
        """Create a manager with temporary state file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        manager = GracePeriodManager(state_file=temp_file)
        yield manager
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def test_initial_state_is_active(self, manager):
        """Test that initial state is ACTIVE."""
        assert manager.get_current_state() == GracePeriodState.ACTIVE

    def test_successful_validation_keeps_active(self, manager):
        """Test that successful validation keeps state ACTIVE."""
        manager.record_successful_validation()
        assert manager.get_current_state() == GracePeriodState.ACTIVE
        assert manager.get_days_offline() == 0

    def test_failed_validation_starts_grace(self, manager):
        """Test that failed validation starts grace period."""
        manager.record_failed_validation()
        # Still day 0, should be ACTIVE or GRACE_QUIET
        state = manager.get_current_state()
        assert state in [GracePeriodState.ACTIVE, GracePeriodState.GRACE_QUIET]

    def test_read_only_initially_false(self, manager):
        """Test that read-only is initially false."""
        assert manager.is_read_only() is False

    def test_no_warning_when_active(self, manager):
        """Test no warning message when active."""
        manager.record_successful_validation()
        assert manager.get_warning_message() is None


class TestGracePeriodTransitions:
    """Test grace period state transitions based on days offline."""

    @pytest.fixture
    def manager(self):
        """Create a manager with temporary state file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        manager = GracePeriodManager(state_file=temp_file)
        yield manager
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def _set_offline_since(self, manager, days_ago):
        """Helper to set offline_since to a specific number of days ago."""
        offline_since = datetime.now(timezone.utc) - timedelta(days=days_ago)
        manager._state.offline_since = offline_since
        manager._state.last_successful_validation = offline_since - timedelta(days=1)
        manager._save_state()

    def test_day_1_is_grace_quiet(self, manager):
        """Test that day 1 offline is GRACE_QUIET."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 1)
        assert manager.get_current_state() == GracePeriodState.GRACE_QUIET

    def test_day_7_is_grace_quiet(self, manager):
        """Test that day 7 offline is GRACE_QUIET."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 7)
        assert manager.get_current_state() == GracePeriodState.GRACE_QUIET

    def test_day_8_is_grace_visible(self, manager):
        """Test that day 8 offline is GRACE_VISIBLE."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 8)
        assert manager.get_current_state() == GracePeriodState.GRACE_VISIBLE

    def test_day_21_is_grace_visible(self, manager):
        """Test that day 21 offline is GRACE_VISIBLE."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 21)
        assert manager.get_current_state() == GracePeriodState.GRACE_VISIBLE

    def test_day_22_is_grace_urgent(self, manager):
        """Test that day 22 offline is GRACE_URGENT."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 22)
        assert manager.get_current_state() == GracePeriodState.GRACE_URGENT

    def test_day_30_is_grace_urgent(self, manager):
        """Test that day 30 offline is GRACE_URGENT."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 30)
        assert manager.get_current_state() == GracePeriodState.GRACE_URGENT

    def test_day_31_is_expired(self, manager):
        """Test that day 31 offline is EXPIRED."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 31)
        assert manager.get_current_state() == GracePeriodState.EXPIRED
        assert manager.is_read_only() is True


class TestWarningMessages:
    """Test warning message generation."""

    @pytest.fixture
    def manager(self):
        """Create a manager with temporary state file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        manager = GracePeriodManager(state_file=temp_file)
        yield manager
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def _set_offline_since(self, manager, days_ago):
        """Helper to set offline_since to a specific number of days ago."""
        offline_since = datetime.now(timezone.utc) - timedelta(days=days_ago)
        manager._state.offline_since = offline_since
        manager._save_state()

    def test_grace_quiet_has_warning(self, manager):
        """Test GRACE_QUIET has appropriate warning."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 3)
        warning = manager.get_warning_message()
        assert warning is not None
        assert "grace mode" in warning.lower()

    def test_grace_visible_has_warning(self, manager):
        """Test GRACE_VISIBLE has appropriate warning."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 15)
        warning = manager.get_warning_message()
        assert warning is not None
        assert "days" in warning.lower()

    def test_grace_urgent_has_urgent_warning(self, manager):
        """Test GRACE_URGENT has urgent warning."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 25)
        warning = manager.get_warning_message()
        assert warning is not None
        assert "URGENT" in warning

    def test_expired_has_readonly_message(self, manager):
        """Test EXPIRED has read-only message."""
        manager.record_failed_validation()
        self._set_offline_since(manager, 35)
        warning = manager.get_warning_message()
        assert warning is not None
        assert "read-only" in warning.lower()


class TestStatePersistence:
    """Test grace period state persistence."""

    def test_state_persists_across_instances(self):
        """Test that state persists to disk."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            # First instance
            manager1 = GracePeriodManager(state_file=temp_file)
            manager1.record_successful_validation()
            last_validation = manager1.get_last_validation()

            # Second instance (simulating restart)
            manager2 = GracePeriodManager(state_file=temp_file)
            assert manager2.get_last_validation() is not None

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_reset_clears_state(self):
        """Test that reset clears all state."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            manager = GracePeriodManager(state_file=temp_file)
            manager.record_failed_validation()
            manager.reset()
            assert manager.get_current_state() == GracePeriodState.ACTIVE
            assert manager.get_days_offline() == 0

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
