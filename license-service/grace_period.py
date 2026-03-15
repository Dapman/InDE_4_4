"""
InDE License Service - Grace Period State Machine
Manages license validation grace periods for offline tolerance.

Grace Period States:
- ACTIVE: License validated, all good
- GRACE_QUIET: Days 1-7 offline, admin warning only
- GRACE_VISIBLE: Days 8-21 offline, admin banner on every page
- GRACE_URGENT: Days 22-30 offline, all-user banner
- EXPIRED: Day 31+, read-only mode
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from models import GracePeriodState, GraceState
from config import config


class GracePeriodManager:
    """Manages grace period state transitions and persistence."""

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize the grace period manager.

        Args:
            state_file: Path to grace state JSON file. Uses config default if not provided.
        """
        self.state_file = state_file or config.GRACE_STATE_FILE
        self._state: Optional[GraceState] = None
        self._load_state()

    def _load_state(self) -> None:
        """Load grace state from disk."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self._state = GraceState(
                    last_successful_validation=datetime.fromisoformat(
                        data['last_successful_validation']
                    ) if data.get('last_successful_validation') else None,
                    offline_since=datetime.fromisoformat(
                        data['offline_since']
                    ) if data.get('offline_since') else None,
                    current_state=GracePeriodState(data.get('current_state', 'active'))
                )
            else:
                self._state = GraceState()
        except Exception:
            self._state = GraceState()

    def _save_state(self) -> None:
        """Persist grace state to disk."""
        if not self._state:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            data = {
                'last_successful_validation': self._state.last_successful_validation.isoformat()
                    if self._state.last_successful_validation else None,
                'offline_since': self._state.offline_since.isoformat()
                    if self._state.offline_since else None,
                'current_state': self._state.current_state.value
            }

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Fail silently on save errors

    def _calculate_days_offline(self) -> int:
        """Calculate number of days since last successful validation."""
        if not self._state or not self._state.offline_since:
            return 0

        now = datetime.now(timezone.utc)
        offline_since = self._state.offline_since
        if offline_since.tzinfo is None:
            offline_since = offline_since.replace(tzinfo=timezone.utc)

        delta = now - offline_since
        return max(0, delta.days)

    def _determine_state(self, days_offline: int) -> GracePeriodState:
        """
        Determine the grace period state based on days offline.

        Args:
            days_offline: Number of days since last successful validation

        Returns:
            Appropriate GracePeriodState
        """
        if days_offline == 0:
            return GracePeriodState.ACTIVE
        elif days_offline <= config.GRACE_QUIET_DAYS:
            return GracePeriodState.GRACE_QUIET
        elif days_offline <= config.GRACE_VISIBLE_DAYS:
            return GracePeriodState.GRACE_VISIBLE
        elif days_offline <= config.GRACE_URGENT_DAYS:
            return GracePeriodState.GRACE_URGENT
        else:
            return GracePeriodState.EXPIRED

    def get_current_state(self) -> GracePeriodState:
        """
        Get the current grace period state.

        Returns:
            Current GracePeriodState
        """
        if not self._state:
            return GracePeriodState.ACTIVE

        days_offline = self._calculate_days_offline()
        return self._determine_state(days_offline)

    def get_days_offline(self) -> int:
        """
        Get the number of days offline.

        Returns:
            Number of days since last successful validation
        """
        return self._calculate_days_offline()

    def record_successful_validation(self) -> None:
        """Record a successful license validation, resetting the grace period."""
        now = datetime.now(timezone.utc)
        self._state = GraceState(
            last_successful_validation=now,
            offline_since=None,
            current_state=GracePeriodState.ACTIVE
        )
        self._save_state()

    def record_failed_validation(self) -> None:
        """Record a failed license validation, starting or continuing the grace period."""
        now = datetime.now(timezone.utc)

        if not self._state:
            self._state = GraceState()

        # Start offline timer if not already running
        if not self._state.offline_since:
            self._state.offline_since = now

        # Update state based on days offline
        days_offline = self._calculate_days_offline()
        self._state.current_state = self._determine_state(days_offline)

        self._save_state()

    def get_warning_message(self) -> Optional[str]:
        """
        Get an appropriate warning message for the current state.

        Returns:
            Warning message string, or None if no warning needed
        """
        state = self.get_current_state()
        days_offline = self._calculate_days_offline()
        days_remaining = config.GRACE_URGENT_DAYS - days_offline

        if state == GracePeriodState.ACTIVE:
            return None

        elif state == GracePeriodState.GRACE_QUIET:
            return (
                f"License validation failed. InDE is operating in grace mode. "
                f"Please check your network connection. ({days_remaining} days remaining)"
            )

        elif state == GracePeriodState.GRACE_VISIBLE:
            return (
                f"License validation has been failing for {days_offline} days. "
                f"Please restore network connectivity or contact InDEVerse support. "
                f"({days_remaining} days until read-only mode)"
            )

        elif state == GracePeriodState.GRACE_URGENT:
            return (
                f"URGENT: License validation has failed for {days_offline} days. "
                f"InDE will enter read-only mode in {days_remaining} days. "
                f"Contact support@indeverse.com immediately."
            )

        elif state == GracePeriodState.EXPIRED:
            return (
                "License grace period has expired. InDE is now in read-only mode. "
                "All existing data is preserved. To restore full functionality, "
                "please renew your license at indeverse.com or contact support."
            )

        return None

    def is_read_only(self) -> bool:
        """
        Check if the system should be in read-only mode.

        Returns:
            True if grace period has expired, False otherwise
        """
        return self.get_current_state() == GracePeriodState.EXPIRED

    def get_last_validation(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful validation.

        Returns:
            Datetime of last validation, or None if never validated
        """
        if self._state:
            return self._state.last_successful_validation
        return None

    def reset(self) -> None:
        """Reset the grace period state (for testing)."""
        self._state = GraceState()
        self._save_state()


# Singleton instance
_grace_manager: Optional[GracePeriodManager] = None


def get_grace_manager() -> GracePeriodManager:
    """Get the singleton grace period manager instance."""
    global _grace_manager
    if _grace_manager is None:
        _grace_manager = GracePeriodManager()
    return _grace_manager
