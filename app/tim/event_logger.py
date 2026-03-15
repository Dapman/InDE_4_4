"""
InDE MVP v3.0.1 - Temporal Event Logger

Logs pursuit lifecycle events with IKF-compatible ISO 8601 timestamps.
Provides event stream for timeline visualization and velocity calculation.

Event Types (IKF-compatible):
- PURSUIT_START: New pursuit created
- PHASE_START: Phase transitioned to
- ELEMENT_CAPTURED: Scaffolding element captured
- ARTIFACT_GENERATED: Artifact created or versioned
- INTERVENTION_TRIGGERED: System intervention occurred
- PHASE_COMPLETE: Phase marked complete
- PURSUIT_COMPLETE: Pursuit reached terminal state

All timestamps use ISO 8601 format: '2026-02-13T14:30:00Z'
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import TEMPORAL_EVENT_TYPES, IKF_PHASES


class TemporalEventLogger:
    """
    Logs and queries temporal events for pursuits.
    All events are IKF-compatible with ISO 8601 timestamps.
    """

    def __init__(self, database):
        """
        Initialize TemporalEventLogger.

        Args:
            database: Database instance
        """
        self.db = database

    def log_event(self, pursuit_id: str, event_type: str, phase: str = None,
                  metadata: Dict = None) -> str:
        """
        Logs a temporal event.

        Args:
            pursuit_id: Pursuit ID
            event_type: One of TEMPORAL_EVENT_TYPES
            phase: Current phase (VISION, DE_RISK, DEPLOY) or None
            metadata: Optional additional data

        Returns:
            event_id of logged event
        """
        if event_type not in TEMPORAL_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type}. Must be one of {TEMPORAL_EVENT_TYPES}")

        if phase and phase not in IKF_PHASES:
            raise ValueError(f"Invalid phase: {phase}. Must be one of {IKF_PHASES}")

        event = {
            "pursuit_id": pursuit_id,
            "event_type": event_type,
            "phase": phase,
            "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
            "metadata": metadata or {}
        }

        return self.db.log_temporal_event(event)

    def log_pursuit_start(self, pursuit_id: str, title: str = None,
                          user_id: str = None) -> str:
        """Log pursuit creation event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="PURSUIT_START",
            phase="VISION",
            metadata={
                "title": title,
                "user_id": user_id
            }
        )

    def log_element_captured(self, pursuit_id: str, phase: str,
                              element_type: str, element_key: str,
                              confidence: float = None) -> str:
        """Log element capture event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="ELEMENT_CAPTURED",
            phase=phase,
            metadata={
                "element_type": element_type,
                "element_key": element_key,
                "confidence": confidence
            }
        )

    def log_artifact_generated(self, pursuit_id: str, phase: str,
                                artifact_type: str, artifact_id: str,
                                version: int = 1) -> str:
        """Log artifact generation event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="ARTIFACT_GENERATED",
            phase=phase,
            metadata={
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "version": version
            }
        )

    def log_intervention_triggered(self, pursuit_id: str, phase: str,
                                    intervention_type: str,
                                    suggestion: str = None) -> str:
        """Log intervention event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="INTERVENTION_TRIGGERED",
            phase=phase,
            metadata={
                "intervention_type": intervention_type,
                "suggestion": suggestion
            }
        )

    def log_phase_start(self, pursuit_id: str, phase: str,
                         from_phase: str = None) -> str:
        """Log phase transition start event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="PHASE_START",
            phase=phase,
            metadata={
                "from_phase": from_phase
            }
        )

    def log_phase_complete(self, pursuit_id: str, phase: str,
                            completion_percentage: float = None) -> str:
        """Log phase completion event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="PHASE_COMPLETE",
            phase=phase,
            metadata={
                "completion_percentage": completion_percentage
            }
        )

    def log_pursuit_complete(self, pursuit_id: str, final_state: str,
                              phase: str = None) -> str:
        """Log pursuit completion (terminal state) event."""
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="PURSUIT_COMPLETE",
            phase=phase,
            metadata={
                "final_state": final_state
            }
        )

    def log_milestone_extracted(self, pursuit_id: str, phase: str,
                                 milestone: dict) -> str:
        """
        Log milestone extraction event (v3.9).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            milestone: Extracted milestone dict with title, target_date, etc.

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="MILESTONE_EXTRACTED",
            phase=phase,
            metadata={
                "milestone_id": milestone.get("milestone_id"),
                "title": milestone.get("title"),
                "target_date": milestone.get("target_date"),
                "date_precision": milestone.get("date_precision"),
                "milestone_type": milestone.get("milestone_type"),
                "confidence": milestone.get("confidence")
            }
        )

    def log_milestone_updated(self, pursuit_id: str, phase: str,
                               milestone_id: str, changes: dict) -> str:
        """
        Log milestone update event (v3.9).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            milestone_id: ID of the milestone being updated
            changes: Dict describing what changed

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="MILESTONE_UPDATED",
            phase=phase,
            metadata={
                "milestone_id": milestone_id,
                "changes": changes
            }
        )

    # =========================================================================
    # v3.10: Timeline Integrity Events (TD-001, TD-002, TD-005)
    # =========================================================================

    def log_timeline_conflict(self, pursuit_id: str, phase: str,
                               conflict_data: dict) -> str:
        """
        Log timeline conflict detection event (v3.10 TD-001).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            conflict_data: Dict with existing_milestone_id, proposed_date, severity, etc.

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="TIMELINE_CONFLICT",
            phase=phase,
            metadata=conflict_data
        )

    def log_conflict_resolved(self, pursuit_id: str, phase: str,
                               resolution_data: dict) -> str:
        """
        Log conflict resolution event (v3.10 TD-001).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            resolution_data: Dict with milestone_id, resolution_strategy, old_date, new_date

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="CONFLICT_RESOLVED",
            phase=phase,
            metadata=resolution_data
        )

    def log_timeline_inconsistency(self, pursuit_id: str, phase: str,
                                    inconsistency_data: dict) -> str:
        """
        Log timeline inconsistency detection event (v3.10 TD-002).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            inconsistency_data: Dict with allocation_end, milestone_end, day_difference

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="TIMELINE_INCONSISTENCY",
            phase=phase,
            metadata=inconsistency_data
        )

    def log_inconsistency_resolved(self, pursuit_id: str, phase: str,
                                    resolution_data: dict) -> str:
        """
        Log inconsistency resolution event (v3.10 TD-002).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            resolution_data: Dict with source_of_truth, old_values, new_values

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="INCONSISTENCY_RESOLVED",
            phase=phase,
            metadata=resolution_data
        )

    def log_relative_date_prompted(self, pursuit_id: str, phase: str,
                                    prompt_data: dict) -> str:
        """
        Log relative date confirmation prompt event (v3.10 TD-005).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            prompt_data: Dict with milestone_id, date_expression, resolved_date

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="RELATIVE_DATE_PROMPTED",
            phase=phase,
            metadata=prompt_data
        )

    def log_relative_date_confirmed(self, pursuit_id: str, phase: str,
                                     confirmation_data: dict) -> str:
        """
        Log relative date confirmation event (v3.10 TD-005).

        Args:
            pursuit_id: Pursuit ID
            phase: Current pursuit phase
            confirmation_data: Dict with milestone_id, original_date, confirmed_date

        Returns:
            Event ID
        """
        return self.log_event(
            pursuit_id=pursuit_id,
            event_type="RELATIVE_DATE_CONFIRMED",
            phase=phase,
            metadata=confirmation_data
        )

    def get_event_stream(self, pursuit_id: str, limit: int = 100) -> List[Dict]:
        """
        Returns all events for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            limit: Maximum events to return

        Returns:
            List of events, most recent first
        """
        return self.db.get_recent_events(pursuit_id, limit)

    def get_events_by_type(self, pursuit_id: str, event_type: str,
                           limit: int = 50) -> List[Dict]:
        """Get events of a specific type."""
        return self.db.get_temporal_events(
            pursuit_id=pursuit_id,
            event_type=event_type,
            limit=limit
        )

    def get_events_in_range(self, pursuit_id: str, start_date: str,
                            end_date: str, limit: int = 100) -> List[Dict]:
        """
        Get events within a date range.

        Args:
            pursuit_id: Pursuit ID
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date
            limit: Maximum events to return

        Returns:
            List of events in range, most recent first
        """
        return self.db.get_temporal_events(
            pursuit_id=pursuit_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_phase_events(self, pursuit_id: str, phase: str,
                          limit: int = 50) -> List[Dict]:
        """Get all events for a specific phase."""
        events = self.get_event_stream(pursuit_id, limit=500)
        return [e for e in events if e.get("phase") == phase][:limit]

    def get_event_count_by_type(self, pursuit_id: str, event_type: str,
                                 since: str = None) -> int:
        """Count events of a specific type, optionally since a date."""
        return self.db.count_events_by_type(pursuit_id, event_type, since)

    def get_timeline_summary(self, pursuit_id: str) -> Dict:
        """
        Get a summary suitable for timeline visualization.

        Returns:
            {
                'total_events': int,
                'events_by_type': dict,
                'events_by_phase': dict,
                'first_event': datetime,
                'last_event': datetime,
                'phases_touched': list
            }
        """
        events = self.get_event_stream(pursuit_id, limit=1000)

        if not events:
            return {
                'total_events': 0,
                'events_by_type': {},
                'events_by_phase': {},
                'first_event': None,
                'last_event': None,
                'phases_touched': []
            }

        events_by_type = {}
        events_by_phase = {}
        phases_touched = set()

        for event in events:
            etype = event.get("event_type", "UNKNOWN")
            phase = event.get("phase")

            events_by_type[etype] = events_by_type.get(etype, 0) + 1

            if phase:
                events_by_phase[phase] = events_by_phase.get(phase, 0) + 1
                phases_touched.add(phase)

        return {
            'total_events': len(events),
            'events_by_type': events_by_type,
            'events_by_phase': events_by_phase,
            'first_event': events[-1].get("timestamp") if events else None,
            'last_event': events[0].get("timestamp") if events else None,
            'phases_touched': list(phases_touched)
        }

    def get_recent_activity(self, pursuit_id: str, hours: int = 24) -> List[Dict]:
        """Get events from the last N hours."""
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat() + 'Z'
        return self.db.get_temporal_events(
            pursuit_id=pursuit_id,
            start_date=since,
            limit=100
        )
