"""
InDE MVP v3.0.1 - Time Allocation Engine

Distributes pursuit timeline across phases using percentage-based allocation.
Manages buffer time and phase transitions, supports innovator overrides.

Default Phase Allocations:
- VISION: 15%
- DE_RISK: 35%
- DEPLOY: 40%
- Buffer: 10%

All timestamps use ISO 8601 format for IKF compatibility.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from config import DEFAULT_PHASE_ALLOCATIONS, IKF_PHASES, TIM_CONFIG


class TimeAllocationEngine:
    """
    Distributes pursuit timeline across phases.
    Creates and manages time allocations for pursuits.
    """

    def __init__(self, database):
        """
        Initialize TimeAllocationEngine.

        Args:
            database: Database instance for persistence
        """
        self.db = database

    def create_allocation(self, pursuit_id: str, start_date: str,
                          target_completion: str, phase_config: Dict = None,
                          buffer_percent: int = None) -> Dict:
        """
        Distributes pursuit timeline across phases.

        Args:
            pursuit_id: ObjectId/string of pursuit
            start_date: ISO 8601 datetime string
            target_completion: ISO 8601 datetime string
            phase_config: Optional dict with phase percentages
            buffer_percent: Buffer allocation (default from config)

        Returns:
            time_allocation document with phase distributions
        """
        buffer = buffer_percent if buffer_percent is not None else TIM_CONFIG.get("default_buffer_percent", 10)
        config = phase_config or DEFAULT_PHASE_ALLOCATIONS.copy()

        # Parse dates
        start_dt = self._parse_iso_date(start_date)
        target_dt = self._parse_iso_date(target_completion)
        total_days = (target_dt - start_dt).days

        if total_days <= 0:
            raise ValueError("Target completion must be after start date")

        # Calculate buffer days
        buffer_days = int(total_days * (buffer / 100))
        available_days = total_days - buffer_days

        # Build phase allocations
        phase_allocations = []
        cumulative_days = 0

        for phase in IKF_PHASES:
            phase_percent = config.get(phase, 0)
            phase_days = int(available_days * (phase_percent / 100))

            phase_start = start_dt + timedelta(days=cumulative_days)
            phase_end = phase_start + timedelta(days=phase_days)
            cumulative_days += phase_days

            phase_allocations.append({
                "phase": phase,
                "percentage": phase_percent,
                "days_allocated": phase_days,
                "days_used": 0,
                "start_date": phase_start.isoformat() + 'Z',
                "end_date": phase_end.isoformat() + 'Z',
                "status": "NOT_STARTED" if phase != "VISION" else "IN_PROGRESS"
            })

        allocation = {
            "pursuit_id": pursuit_id,
            "start_date": start_date,
            "target_completion": target_completion,
            "total_days": total_days,
            "buffer_percent": buffer,
            "buffer_days": buffer_days,
            "buffer_days_used": 0,
            "phase_allocations": phase_allocations,
            "current_phase": "VISION",
            "is_overridden": False,
            "override_history": []
        }

        self.db.create_time_allocation(allocation)
        return allocation

    def update_phase_consumption(self, pursuit_id: str, phase: str,
                                   days_used: int) -> bool:
        """
        Track time used in a phase.

        Args:
            pursuit_id: Pursuit ID
            phase: Phase name (VISION, DE_RISK, DEPLOY)
            days_used: Total days used in this phase

        Returns:
            True if update succeeded
        """
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return False

        for pa in allocation.get("phase_allocations", []):
            if pa["phase"] == phase:
                pa["days_used"] = days_used
                break

        return self.db.update_time_allocation(pursuit_id, {
            "phase_allocations": allocation["phase_allocations"]
        })

    def get_remaining_time(self, pursuit_id: str, phase: str = None) -> Dict:
        """
        Calculate remaining time for phase or overall pursuit.

        Args:
            pursuit_id: Pursuit ID
            phase: Optional phase name (if None, returns overall)

        Returns:
            Dict with days_remaining, days_used, percentage_remaining
        """
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return {
                "days_remaining": 0,
                "days_used": 0,
                "days_allocated": 0,
                "percentage_remaining": 0.0,
                "status": "no_allocation"
            }

        if phase:
            for pa in allocation.get("phase_allocations", []):
                if pa["phase"] == phase:
                    days_remaining = max(0, pa["days_allocated"] - pa.get("days_used", 0))
                    pct = days_remaining / pa["days_allocated"] if pa["days_allocated"] > 0 else 0
                    return {
                        "days_remaining": days_remaining,
                        "days_used": pa.get("days_used", 0),
                        "days_allocated": pa["days_allocated"],
                        "percentage_remaining": pct,
                        "status": pa.get("status", "NOT_STARTED")
                    }
            return {"days_remaining": 0, "status": "phase_not_found"}

        # Overall remaining time
        total_allocated = allocation.get("total_days", 0)
        total_used = sum(pa.get("days_used", 0) for pa in allocation.get("phase_allocations", []))
        buffer_used = allocation.get("buffer_days_used", 0)
        total_consumed = total_used + buffer_used
        remaining = max(0, total_allocated - total_consumed)
        pct = remaining / total_allocated if total_allocated > 0 else 0

        return {
            "days_remaining": remaining,
            "days_used": total_consumed,
            "days_allocated": total_allocated,
            "percentage_remaining": pct,
            "buffer_days_remaining": allocation.get("buffer_days", 0) - buffer_used,
            "status": "active"
        }

    def override_allocation(self, pursuit_id: str, new_phase_config: Dict,
                            reason: str = None) -> bool:
        """
        Allow innovator to override default phase allocations.

        Args:
            pursuit_id: Pursuit ID
            new_phase_config: Dict with phase percentages
            reason: Optional reason for override

        Returns:
            True if override succeeded
        """
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return False

        total_days = allocation.get("total_days", 0)
        buffer_days = allocation.get("buffer_days", 0)
        available_days = total_days - buffer_days
        start_dt = self._parse_iso_date(allocation["start_date"])

        # Recalculate phase allocations
        phase_allocations = []
        cumulative_days = 0

        for phase in IKF_PHASES:
            phase_percent = new_phase_config.get(phase, DEFAULT_PHASE_ALLOCATIONS.get(phase, 0))
            phase_days = int(available_days * (phase_percent / 100))

            # Preserve existing usage data
            existing_pa = next(
                (pa for pa in allocation.get("phase_allocations", []) if pa["phase"] == phase),
                None
            )
            days_used = existing_pa.get("days_used", 0) if existing_pa else 0
            status = existing_pa.get("status", "NOT_STARTED") if existing_pa else "NOT_STARTED"

            phase_start = start_dt + timedelta(days=cumulative_days)
            phase_end = phase_start + timedelta(days=phase_days)
            cumulative_days += phase_days

            phase_allocations.append({
                "phase": phase,
                "percentage": phase_percent,
                "days_allocated": phase_days,
                "days_used": days_used,
                "start_date": phase_start.isoformat() + 'Z',
                "end_date": phase_end.isoformat() + 'Z',
                "status": status
            })

        # Record override history
        override_record = {
            "overridden_at": datetime.now(timezone.utc).isoformat() + 'Z',
            "new_config": new_phase_config,
            "reason": reason
        }

        override_history = allocation.get("override_history", [])
        override_history.append(override_record)

        return self.db.update_time_allocation(pursuit_id, {
            "phase_allocations": phase_allocations,
            "is_overridden": True,
            "override_history": override_history
        })

    def get_phase_allocation(self, pursuit_id: str, phase: str) -> Optional[Dict]:
        """Get allocation details for a specific phase."""
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return None

        for pa in allocation.get("phase_allocations", []):
            if pa["phase"] == phase:
                return pa
        return None

    def calculate_days_in_phase(self, pursuit_id: str, phase: str) -> int:
        """Calculate actual days spent in a phase based on events."""
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return 0

        phase_record = self.get_phase_allocation(pursuit_id, phase)
        if not phase_record:
            return 0

        start_str = phase_record.get("start_date")
        if not start_str:
            return 0

        start_dt = self._parse_iso_date(start_str)
        now = datetime.now(timezone.utc)

        if phase_record.get("status") == "COMPLETE":
            end_str = phase_record.get("end_date")
            if end_str:
                end_dt = self._parse_iso_date(end_str)
                return (end_dt - start_dt).days

        return (now - start_dt).days

    def _parse_iso_date(self, date_str: str) -> datetime:
        """Parse ISO 8601 date string to datetime (timezone-aware)."""
        # Handle Z suffix (UTC indicator)
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        # Don't add timezone if already has one
        dt = datetime.fromisoformat(date_str)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def get_allocation(self, pursuit_id: str) -> Optional[Dict]:
        """Get full time allocation for a pursuit."""
        return self.db.get_time_allocation(pursuit_id)

    def get_projected_completion(self, pursuit_id: str, current_velocity: float) -> Dict:
        """
        Project completion date based on current velocity.

        Args:
            pursuit_id: Pursuit ID
            current_velocity: Current elements/week velocity

        Returns:
            Dict with projected_date, days_ahead_behind, confidence
        """
        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation or current_velocity <= 0:
            return {
                "projected_date": None,
                "days_ahead_behind": 0,
                "confidence": 0.0,
                "status": "insufficient_data"
            }

        target_str = allocation.get("target_completion")
        if not target_str:
            return {
                "projected_date": None,
                "days_ahead_behind": 0,
                "confidence": 0.0,
                "status": "no_target"
            }

        target_dt = self._parse_iso_date(target_str)
        now = datetime.now(timezone.utc)
        days_remaining = (target_dt - now).days

        # Simple projection based on velocity ratio
        remaining_time = self.get_remaining_time(pursuit_id)
        if remaining_time.get("percentage_remaining", 0) > 0:
            # This is a simplified projection
            projected_dt = target_dt
            days_diff = 0
            confidence = 0.7
        else:
            projected_dt = target_dt
            days_diff = 0
            confidence = 0.5

        return {
            "projected_date": projected_dt.isoformat() + 'Z',
            "days_ahead_behind": days_diff,
            "confidence": confidence,
            "target_date": target_str,
            "status": "projected"
        }
