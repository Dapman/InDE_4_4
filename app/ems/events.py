"""
InDE EMS v3.7.1 - Event Definitions and Consumer

Defines EMS-specific event types and the consumer that triggers
process observations based on domain events.

The EMS consumer listens to the main InDE event bus and records
observations for ad-hoc pursuits. It operates as a silent subscriber
that never interrupts the innovator's flow.

Event Types (consumed):
- pursuit.created (to start observation if ad_hoc)
- artifact.created
- artifact.updated
- element.captured
- coaching.message (to record coaching interactions)
- rve.experiment.started
- rve.experiment.completed
- pursuit.state_changed
- pursuit.completed
- pursuit.terminated
- pursuit.abandoned

Event Types (emitted):
- ems.observation.recorded
- ems.synthesis.eligible
- ems.observation.completed
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("inde.ems.events")


class EMSEventType(str, Enum):
    """EMS-specific event types."""
    OBSERVATION_RECORDED = "ems.observation.recorded"
    SYNTHESIS_ELIGIBLE = "ems.synthesis.eligible"
    SYNTHESIS_REQUESTED = "ems.synthesis.requested"
    OBSERVATION_STARTED = "ems.observation.started"
    OBSERVATION_PAUSED = "ems.observation.paused"
    OBSERVATION_COMPLETED = "ems.observation.completed"
    OBSERVATION_ABANDONED = "ems.observation.abandoned"


@dataclass
class EMSEvent:
    """An EMS-specific domain event."""
    event_type: EMSEventType
    pursuit_id: str
    innovator_id: str
    timestamp: datetime
    details: Dict

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "pursuit_id": self.pursuit_id,
            "innovator_id": self.innovator_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class EMSEventHandler:
    """
    Event handler that triggers EMS observations from domain events.

    This handler is registered with the main event bus to receive
    events that should trigger process observations.
    """

    def __init__(self):
        """Initialize the EMS event handler."""
        self._observer = None
        self._enabled = True

    def _get_observer(self):
        """Lazy-load the process observer to avoid circular imports."""
        if self._observer is None:
            from ems.process_observer import get_process_observer
            self._observer = get_process_observer()
        return self._observer

    def is_adhoc_pursuit(self, pursuit_id: str) -> bool:
        """Check if pursuit is ad-hoc."""
        return self._get_observer().is_adhoc_pursuit(pursuit_id)

    async def handle_pursuit_created(self, event: Dict) -> None:
        """Handle pursuit creation - start observation if ad-hoc."""
        pursuit_id = event.get("pursuit_id")
        archetype = event.get("payload", {}).get("archetype", "")

        if archetype == "ad_hoc":
            observer = self._get_observer()
            observer.start_observation(pursuit_id)
            logger.info(f"EMS: Started observation for ad-hoc pursuit {pursuit_id}")

    async def handle_artifact_created(self, event: Dict) -> None:
        """Handle artifact creation."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()
        observer.record_artifact_created(
            pursuit_id=pursuit_id,
            artifact_type=payload.get("artifact_type", "unknown"),
            artifact_id=payload.get("artifact_id", ""),
            artifact_name=payload.get("artifact_name", ""),
            context={"source": "event", "event_id": event.get("event_id")}
        )

    async def handle_element_captured(self, event: Dict) -> None:
        """Handle element capture."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()
        observer.record_element_captured(
            pursuit_id=pursuit_id,
            element_type=payload.get("element_type", "unknown"),
            element_id=payload.get("element_id", ""),
            element_summary=payload.get("summary", ""),
            context={"source": "event", "event_id": event.get("event_id")}
        )

    async def handle_coaching_message(self, event: Dict) -> None:
        """Handle coaching interaction."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()

        # Only record if innovator initiated (asked a question)
        if payload.get("direction") == "user_to_coach":
            observer.record_coaching_interaction(
                pursuit_id=pursuit_id,
                interaction_type=payload.get("interaction_type", "question"),
                user_request=payload.get("user_message", "")[:500],  # Truncate for privacy
                coach_response_summary=payload.get("response_summary", ""),
                context={"source": "event", "session_id": payload.get("session_id")}
            )

    async def handle_rve_experiment(self, event: Dict) -> None:
        """Handle RVE experiment events."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()
        observer.record_risk_validation(
            pursuit_id=pursuit_id,
            risk_id=payload.get("risk_id", ""),
            validation_type=payload.get("experiment_type", "unknown"),
            outcome=payload.get("outcome"),
            context={"source": "event", "event_id": event.get("event_id")}
        )

    async def handle_tool_invoked(self, event: Dict) -> None:
        """Handle tool invocation."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()
        observer.record_tool_invoked(
            pursuit_id=pursuit_id,
            tool_name=payload.get("tool_name", "unknown"),
            tool_parameters=payload.get("parameters", {}),
            context={"source": "event", "event_id": event.get("event_id")}
        )

    async def handle_pursuit_state_changed(self, event: Dict) -> None:
        """Handle pursuit state changes (for decision detection)."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        payload = event.get("payload", {})
        observer = self._get_observer()

        # State changes often indicate decisions
        observer.record_decision_made(
            pursuit_id=pursuit_id,
            decision_type="state_transition",
            decision_summary=f"Transitioned from {payload.get('from_state')} to {payload.get('to_state')}",
            alternatives_considered=[],
            context={"source": "event", "event_id": event.get("event_id")}
        )

    async def handle_pursuit_completed(self, event: Dict) -> None:
        """Handle pursuit completion - finalize observation."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        observer = self._get_observer()
        observer.complete_observation(pursuit_id)

        # Check synthesis eligibility
        innovator_id = event.get("user_id", "")
        if innovator_id:
            eligibility = observer.get_synthesis_eligibility(innovator_id)
            if eligibility["eligibility"] in ["ELIGIBLE", "HIGH_CONFIDENCE"]:
                logger.info(
                    f"EMS: Innovator {innovator_id} eligible for synthesis "
                    f"({eligibility['completed_adhoc_pursuits']} pursuits)"
                )
                # Could emit a synthesis_eligible event here for UI notification

    async def handle_pursuit_abandoned(self, event: Dict) -> None:
        """Handle pursuit abandonment."""
        pursuit_id = event.get("pursuit_id")
        if not pursuit_id or not self.is_adhoc_pursuit(pursuit_id):
            return

        observer = self._get_observer()
        observer.abandon_observation(pursuit_id)


# Global handler instance
_ems_handler: Optional[EMSEventHandler] = None


def get_ems_handler() -> EMSEventHandler:
    """Get the singleton EMS event handler."""
    global _ems_handler
    if _ems_handler is None:
        _ems_handler = EMSEventHandler()
    return _ems_handler


def register_ems_handlers(event_bus) -> None:
    """
    Register EMS handlers with the application event bus.

    Called during application startup to wire EMS into the event flow.

    Args:
        event_bus: The application's event bus/publisher instance
    """
    handler = get_ems_handler()

    # Map event types to handlers
    event_mappings = [
        ("pursuit.created", handler.handle_pursuit_created),
        ("artifact.created", handler.handle_artifact_created),
        ("artifact.updated", handler.handle_artifact_created),  # Same handling
        ("element.captured", handler.handle_element_captured),
        ("coaching.message", handler.handle_coaching_message),
        ("coaching.response", handler.handle_coaching_message),
        ("rve.experiment.started", handler.handle_rve_experiment),
        ("rve.experiment.completed", handler.handle_rve_experiment),
        ("tool.invoked", handler.handle_tool_invoked),
        ("pursuit.state_changed", handler.handle_pursuit_state_changed),
        ("pursuit.completed", handler.handle_pursuit_completed),
        ("pursuit.terminated", handler.handle_pursuit_completed),
        ("pursuit.abandoned", handler.handle_pursuit_abandoned),
    ]

    for event_type, handler_fn in event_mappings:
        try:
            event_bus.register_handler(event_type, handler_fn)
            logger.debug(f"EMS: Registered handler for {event_type}")
        except Exception as e:
            logger.warning(f"EMS: Could not register handler for {event_type}: {e}")

    logger.info(f"EMS: Registered {len(event_mappings)} event handlers")
