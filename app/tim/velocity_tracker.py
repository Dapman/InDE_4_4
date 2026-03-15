"""
InDE MVP v3.0.1 - Velocity Tracker

Monitors progress pace (elements/week), calculates velocity ratios,
determines status (ahead/on-track/behind), and projects completion dates.

Velocity Calculation:
- Count elements captured in last N days
- Normalize to weekly rate (elements/week)
- Compare against expected pace from time allocation
- Status thresholds: ahead (>110%), on_track (90-110%), behind (<90%)

All timestamps use ISO 8601 format for IKF compatibility.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from functools import lru_cache

from config import VELOCITY_THRESHOLDS, TIM_CONFIG


class VelocityTracker:
    """
    Monitors progress velocity and projects completion.
    Calculates elements/week pace and trend analysis.
    """

    def __init__(self, database, allocation_engine=None):
        """
        Initialize VelocityTracker.

        Args:
            database: Database instance
            allocation_engine: Optional TimeAllocationEngine for projections
        """
        self.db = database
        self.allocation_engine = allocation_engine
        self._cache = {}
        self._cache_ttl = TIM_CONFIG.get("velocity_cache_ttl_seconds", 3600)

    def calculate_velocity(self, pursuit_id: str, window_days: int = 7) -> Dict:
        """
        Calculate current velocity (elements/week).

        Args:
            pursuit_id: Pursuit ID
            window_days: Days to look back (default 7)

        Returns:
            {
                'elements_per_week': float,
                'velocity_ratio': float,  # actual/expected
                'status': 'ahead' | 'on_track' | 'behind' | 'insufficient_data',
                'trend': 'accelerating' | 'stable' | 'decelerating' | 'unknown'
            }
        """
        # Check cache
        cache_key = f"{pursuit_id}_{window_days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Get element capture events in window
        since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat() + 'Z'
        element_count = self.db.count_events_by_type(
            pursuit_id, "ELEMENT_CAPTURED", since
        )

        # Also count artifacts generated as significant progress
        artifact_count = self.db.count_events_by_type(
            pursuit_id, "ARTIFACT_GENERATED", since
        )

        # Weight artifacts more heavily (1 artifact = 3 elements worth)
        total_progress = element_count + (artifact_count * 3)

        # Normalize to weekly rate
        elements_per_week = (total_progress / window_days) * 7 if window_days > 0 else 0

        # Calculate expected velocity from time allocation
        expected_velocity = self._calculate_expected_velocity(pursuit_id)

        # Calculate velocity ratio
        if expected_velocity > 0:
            velocity_ratio = elements_per_week / expected_velocity
        else:
            velocity_ratio = 1.0 if elements_per_week > 0 else 0.0

        # Determine status
        status = self._determine_status(velocity_ratio, element_count + artifact_count)

        # Determine trend
        trend = self._calculate_trend(pursuit_id)

        result = {
            'elements_per_week': round(elements_per_week, 2),
            'velocity_ratio': round(velocity_ratio, 2),
            'status': status,
            'trend': trend,
            'elements_in_window': element_count,
            'artifacts_in_window': artifact_count,
            'window_days': window_days,
            'expected_velocity': round(expected_velocity, 2)
        }

        # Cache result
        self._set_cached(cache_key, result)

        # Save to database for history
        self._save_velocity_metric(pursuit_id, result)

        return result

    def _calculate_expected_velocity(self, pursuit_id: str) -> float:
        """Calculate expected velocity based on time allocation."""
        if not self.allocation_engine:
            return 5.0  # Default expected velocity

        allocation = self.db.get_time_allocation(pursuit_id)
        if not allocation:
            return 5.0

        # Get scaffolding state for total elements
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return 5.0

        # Count total elements to capture (20 critical)
        total_elements = 20  # CRITICAL_ELEMENTS total

        # Calculate expected rate based on remaining time
        remaining = self.allocation_engine.get_remaining_time(pursuit_id)
        days_remaining = remaining.get("days_remaining", 180)
        weeks_remaining = days_remaining / 7 if days_remaining > 0 else 1

        # Count already captured elements
        captured = self._count_captured_elements(state)
        remaining_elements = max(0, total_elements - captured)

        expected = remaining_elements / weeks_remaining if weeks_remaining > 0 else 5.0
        return max(expected, 1.0)  # Minimum 1 element/week expected

    def _count_captured_elements(self, state: Dict) -> int:
        """Count captured elements from scaffolding state."""
        count = 0
        for elem_type in ["vision_elements", "fear_elements", "hypothesis_elements"]:
            elements = state.get(elem_type, {})
            for elem in elements.values():
                if elem and elem.get("text"):
                    count += 1
        return count

    def _determine_status(self, velocity_ratio: float, event_count: int) -> str:
        """Determine velocity status based on ratio and thresholds."""
        if event_count < 2:
            return "insufficient_data"

        ahead_threshold = VELOCITY_THRESHOLDS.get("ahead", 1.10)
        behind_threshold = VELOCITY_THRESHOLDS.get("behind", 0.90)

        if velocity_ratio >= ahead_threshold:
            return "ahead"
        elif velocity_ratio <= behind_threshold:
            return "behind"
        else:
            return "on_track"

    def _calculate_trend(self, pursuit_id: str) -> str:
        """Calculate velocity trend from history."""
        history = self.db.get_velocity_history(pursuit_id, limit=5)

        if len(history) < 3:
            return "unknown"

        # Compare recent vs older velocity
        recent = sum(h.get("elements_per_week", 0) for h in history[:2]) / 2
        older = sum(h.get("elements_per_week", 0) for h in history[2:]) / len(history[2:])

        if older == 0:
            return "unknown"

        change = (recent - older) / older

        if change > 0.15:
            return "accelerating"
        elif change < -0.15:
            return "decelerating"
        else:
            return "stable"

    def project_completion(self, pursuit_id: str) -> Dict:
        """
        Project completion date based on current velocity.

        Returns:
            {
                'projected_date': ISO 8601 string,
                'confidence_interval': (lower_bound, upper_bound),
                'days_ahead_behind': int  # negative = behind
            }
        """
        velocity = self.calculate_velocity(pursuit_id)
        allocation = self.db.get_time_allocation(pursuit_id)

        if not allocation:
            return {
                'projected_date': None,
                'confidence_interval': (None, None),
                'days_ahead_behind': 0,
                'status': 'no_allocation'
            }

        target_str = allocation.get("target_completion")
        if not target_str:
            return {
                'projected_date': None,
                'confidence_interval': (None, None),
                'days_ahead_behind': 0,
                'status': 'no_target'
            }

        target_dt = self._parse_iso_date(target_str)
        now = datetime.now(timezone.utc)

        # Get remaining elements
        state = self.db.get_scaffolding_state(pursuit_id)
        captured = self._count_captured_elements(state) if state else 0
        remaining_elements = max(0, 20 - captured)

        # Calculate weeks needed at current velocity
        current_velocity = velocity.get("elements_per_week", 0)
        if current_velocity > 0:
            weeks_needed = remaining_elements / current_velocity
            days_needed = int(weeks_needed * 7)
            projected_dt = now + timedelta(days=days_needed)
        else:
            projected_dt = target_dt + timedelta(days=30)  # Assume behind

        days_ahead_behind = (target_dt - projected_dt).days

        # Confidence interval based on velocity trend
        confidence_window = TIM_CONFIG.get("projection_confidence_window_days", 14)
        trend = velocity.get("trend", "unknown")

        if trend == "accelerating":
            lower_dt = projected_dt - timedelta(days=confidence_window)
            upper_dt = projected_dt + timedelta(days=confidence_window // 2)
        elif trend == "decelerating":
            lower_dt = projected_dt - timedelta(days=confidence_window // 2)
            upper_dt = projected_dt + timedelta(days=confidence_window * 2)
        else:
            lower_dt = projected_dt - timedelta(days=confidence_window)
            upper_dt = projected_dt + timedelta(days=confidence_window)

        return {
            'projected_date': projected_dt.isoformat() + 'Z',
            'confidence_interval': (
                lower_dt.isoformat() + 'Z',
                upper_dt.isoformat() + 'Z'
            ),
            'days_ahead_behind': days_ahead_behind,
            'target_date': target_str,
            'remaining_elements': remaining_elements,
            'current_velocity': current_velocity,
            'status': 'ahead' if days_ahead_behind > 0 else 'behind' if days_ahead_behind < 0 else 'on_track'
        }

    def _save_velocity_metric(self, pursuit_id: str, velocity_data: Dict) -> None:
        """Save velocity calculation to database for history."""
        metric = {
            "pursuit_id": pursuit_id,
            "elements_per_week": velocity_data.get("elements_per_week", 0),
            "velocity_ratio": velocity_data.get("velocity_ratio", 1.0),
            "status": velocity_data.get("status", "unknown"),
            "trend": velocity_data.get("trend", "unknown"),
            "window_days": velocity_data.get("window_days", 7)
        }
        self.db.save_velocity_metric(metric)

    def get_velocity_summary(self, pursuit_id: str) -> Dict:
        """Get a summary of velocity metrics for display."""
        velocity = self.calculate_velocity(pursuit_id)
        projection = self.project_completion(pursuit_id)

        return {
            "current": velocity,
            "projection": projection,
            "display": {
                "velocity": f"{velocity.get('elements_per_week', 0):.1f} elem/wk",
                "status": velocity.get("status", "unknown"),
                "trend": velocity.get("trend", "unknown"),
                "days_ahead_behind": projection.get("days_ahead_behind", 0)
            }
        }

    def _parse_iso_date(self, date_str: str) -> datetime:
        """Parse ISO 8601 date string to datetime (timezone-aware)."""
        # Handle Z suffix (UTC indicator)
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        # Don't add timezone if already has one (contains + or - after T, excluding the T itself)
        dt = datetime.fromisoformat(date_str)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached velocity calculation."""
        if key not in self._cache:
            return None

        cached_at, data = self._cache[key]
        if (datetime.now(timezone.utc) - cached_at).total_seconds() > self._cache_ttl:
            del self._cache[key]
            return None

        return data

    def _set_cached(self, key: str, data: Dict) -> None:
        """Cache velocity calculation."""
        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][0]
            )[:50]
            for k in oldest_keys:
                del self._cache[k]

        self._cache[key] = (datetime.now(timezone.utc), data)

    def clear_cache(self, pursuit_id: str = None) -> None:
        """Clear velocity cache."""
        if pursuit_id:
            keys_to_remove = [k for k in self._cache if k.startswith(pursuit_id)]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            self._cache.clear()
