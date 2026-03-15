"""
InDE EMS v3.7.2 - Process Observation Engine

The Process Observer silently captures behavioral observations during
ad-hoc (freeform) pursuits. It never interrupts the innovator; it simply
records what they do.

Observations are weighted by signal strength:
- ARTIFACT_CREATED: 0.8 (strong signal of process intent)
- TOOL_INVOKED: 0.7 (clear action taken)
- DECISION_MADE: 0.9 (highest signal - explicit choice)
- TEMPORAL_PATTERN: 0.5 (time gaps reveal rhythm)
- COACHING_INTERACTION: 0.3 (external influence, filtered for synthesis)
- ELEMENT_CAPTURED: 0.7 (innovation building blocks)
- RISK_VALIDATION: 0.8 (structured de-risking activity)

The observer is triggered by domain events via the EMS consumer group.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

from core.database import db
from core.config import (
    EMS_CONFIG,
    EMS_OBSERVATION_TYPES,
    EMS_OBSERVATION_STATUS,
)

logger = logging.getLogger("inde.ems.observer")


class ObservationType(str, Enum):
    """Types of observations captured by the Process Observer."""
    ARTIFACT_CREATED = "ARTIFACT_CREATED"
    TOOL_INVOKED = "TOOL_INVOKED"
    DECISION_MADE = "DECISION_MADE"
    TEMPORAL_PATTERN = "TEMPORAL_PATTERN"
    COACHING_INTERACTION = "COACHING_INTERACTION"
    ELEMENT_CAPTURED = "ELEMENT_CAPTURED"
    RISK_VALIDATION = "RISK_VALIDATION"


class ObservationStatus(str, Enum):
    """Status of observation collection for a pursuit."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


@dataclass
class ProcessObservation:
    """
    A single observation of innovator behavior.

    Attributes:
        pursuit_id: The ad-hoc pursuit being observed
        innovator_id: The innovator (for cross-pursuit analysis)
        observation_type: Type from ObservationType enum
        timestamp: When the observation was recorded (UTC)
        sequence_number: Order within this pursuit
        details: Observation-specific data
        context: Additional context (phase, prior activity, etc.)
        signal_weight: Weight for synthesis (0.0-1.0)
        is_external_influence: True if coaching/external input involved
    """
    pursuit_id: str
    innovator_id: str
    observation_type: ObservationType
    timestamp: datetime
    sequence_number: int
    details: Dict[str, Any]
    context: Dict[str, Any]
    signal_weight: float
    is_external_influence: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "pursuit_id": self.pursuit_id,
            "innovator_id": self.innovator_id,
            "observation_type": self.observation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "details": self.details,
            "context": self.context,
            "signal_weight": self.signal_weight,
            "is_external_influence": self.is_external_influence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessObservation":
        """Create from dictionary (storage retrieval)."""
        return cls(
            pursuit_id=data["pursuit_id"],
            innovator_id=data["innovator_id"],
            observation_type=ObservationType(data["observation_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                      if isinstance(data["timestamp"], str) else data["timestamp"],
            sequence_number=data["sequence_number"],
            details=data.get("details", {}),
            context=data.get("context", {}),
            signal_weight=data.get("signal_weight", 0.5),
            is_external_influence=data.get("is_external_influence", False),
        )


class ProcessObserver:
    """
    The Process Observation Engine.

    Silently observes and records innovator behavior during ad-hoc pursuits.
    Does not interrupt or guide - only observes and persists.

    Usage:
        observer = ProcessObserver()
        observer.record_artifact_created(pursuit_id, artifact_data, context)
    """

    def __init__(self):
        """Initialize the Process Observer."""
        self.config = EMS_CONFIG
        self.observation_weights = {
            ObservationType.ARTIFACT_CREATED: EMS_OBSERVATION_TYPES["ARTIFACT_CREATED"]["weight"],
            ObservationType.TOOL_INVOKED: EMS_OBSERVATION_TYPES["TOOL_INVOKED"]["weight"],
            ObservationType.DECISION_MADE: EMS_OBSERVATION_TYPES["DECISION_MADE"]["weight"],
            ObservationType.TEMPORAL_PATTERN: EMS_OBSERVATION_TYPES["TEMPORAL_PATTERN"]["weight"],
            ObservationType.COACHING_INTERACTION: EMS_OBSERVATION_TYPES["COACHING_INTERACTION"]["weight"],
            ObservationType.ELEMENT_CAPTURED: EMS_OBSERVATION_TYPES["ELEMENT_CAPTURED"]["weight"],
            ObservationType.RISK_VALIDATION: EMS_OBSERVATION_TYPES["RISK_VALIDATION"]["weight"],
        }
        self.significant_gap_hours = self.config.get("significant_gap_hours", 24)

    def is_adhoc_pursuit(self, pursuit_id: str) -> bool:
        """Check if pursuit is an ad-hoc (freeform) pursuit."""
        pursuit = db.get_pursuit(pursuit_id)
        return pursuit and pursuit.get("archetype") == "ad_hoc"

    def is_observation_enabled(self, pursuit_id: str) -> bool:
        """
        Check if observation is enabled for this pursuit.

        Returns True if:
        - Global observation is enabled
        - Pursuit is ad-hoc
        - Observation status is ACTIVE
        """
        if not self.config.get("observation_enabled", True):
            return False

        pursuit = db.get_pursuit(pursuit_id)
        if not pursuit:
            return False

        if pursuit.get("archetype") != "ad_hoc":
            return False

        adhoc_metadata = pursuit.get("adhoc_metadata", {})
        status = adhoc_metadata.get("observation_status", "ACTIVE")
        return status == "ACTIVE"

    def _get_next_sequence(self, pursuit_id: str) -> int:
        """Get the next sequence number for a pursuit."""
        latest = db.get_latest_observation(pursuit_id)
        if latest:
            return latest.get("sequence_number", 0) + 1
        return 1

    def _check_temporal_gap(self, pursuit_id: str) -> Optional[Dict]:
        """
        Check for significant temporal gap since last activity.

        Returns gap info if gap exceeds threshold, None otherwise.
        """
        latest = db.get_latest_non_temporal_observation(pursuit_id)
        if not latest:
            return None

        last_timestamp = latest.get("timestamp")
        if isinstance(last_timestamp, str):
            last_timestamp = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))

        now = datetime.now(timezone.utc)
        gap = now - last_timestamp

        if gap.total_seconds() >= self.significant_gap_hours * 3600:
            return {
                "gap_hours": round(gap.total_seconds() / 3600, 1),
                "last_activity_type": latest.get("observation_type"),
                "last_timestamp": last_timestamp.isoformat(),
            }
        return None

    def _record_observation(
        self,
        pursuit_id: str,
        observation_type: ObservationType,
        details: Dict[str, Any],
        context: Dict[str, Any] = None,
        is_external_influence: bool = False,
    ) -> Optional[str]:
        """
        Core observation recording method.

        Args:
            pursuit_id: The pursuit being observed
            observation_type: Type of observation
            details: Observation-specific data
            context: Additional context
            is_external_influence: True if coaching/external input

        Returns:
            Observation ID if recorded, None if observation disabled
        """
        if not self.is_observation_enabled(pursuit_id):
            logger.debug(f"Observation disabled for pursuit {pursuit_id}")
            return None

        # Get pursuit info for innovator_id
        pursuit = db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.warning(f"Pursuit {pursuit_id} not found for observation")
            return None

        innovator_id = pursuit.get("user_id", "")

        # Check for temporal gap (if not already recording a temporal pattern)
        if observation_type != ObservationType.TEMPORAL_PATTERN:
            gap_info = self._check_temporal_gap(pursuit_id)
            if gap_info:
                # Record temporal pattern first
                self._record_observation(
                    pursuit_id=pursuit_id,
                    observation_type=ObservationType.TEMPORAL_PATTERN,
                    details=gap_info,
                    context={"trigger": "activity_gap_detected"},
                    is_external_influence=False,
                )

        # Create observation
        observation = ProcessObservation(
            pursuit_id=pursuit_id,
            innovator_id=innovator_id,
            observation_type=observation_type,
            timestamp=datetime.now(timezone.utc),
            sequence_number=self._get_next_sequence(pursuit_id),
            details=details,
            context=context or {},
            signal_weight=self.observation_weights.get(observation_type, 0.5),
            is_external_influence=is_external_influence,
        )

        # Persist
        observation_id = db.create_observation(observation.to_dict())
        db.increment_observation_count(pursuit_id)

        logger.info(
            f"Observation recorded: {observation_type.value} for pursuit {pursuit_id} "
            f"(seq: {observation.sequence_number}, weight: {observation.signal_weight})"
        )

        return observation_id

    # =========================================================================
    # PUBLIC OBSERVATION METHODS
    # =========================================================================

    def record_artifact_created(
        self,
        pursuit_id: str,
        artifact_type: str,
        artifact_id: str,
        artifact_name: str = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record an artifact creation event.

        Args:
            pursuit_id: The pursuit
            artifact_type: Type of artifact created
            artifact_id: ID of the new artifact
            artifact_name: Human-readable name
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "artifact_name": artifact_name or "",
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.ARTIFACT_CREATED,
            details=details,
            context=context,
        )

    def record_tool_invoked(
        self,
        pursuit_id: str,
        tool_name: str,
        tool_parameters: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record a tool invocation event.

        Args:
            pursuit_id: The pursuit
            tool_name: Name of tool invoked
            tool_parameters: Parameters passed to tool (sanitized)
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "tool_name": tool_name,
            "parameters": tool_parameters or {},
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.TOOL_INVOKED,
            details=details,
            context=context,
        )

    def record_decision_made(
        self,
        pursuit_id: str,
        decision_type: str,
        decision_summary: str,
        alternatives_considered: List[str] = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record an explicit decision point.

        Args:
            pursuit_id: The pursuit
            decision_type: Category of decision
            decision_summary: Brief summary of what was decided
            alternatives_considered: Other options considered
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "decision_type": decision_type,
            "decision_summary": decision_summary,
            "alternatives_considered": alternatives_considered or [],
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.DECISION_MADE,
            details=details,
            context=context,
        )

    def record_coaching_interaction(
        self,
        pursuit_id: str,
        interaction_type: str,
        user_request: str,
        coach_response_summary: str = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record a coaching interaction (tagged as external influence).

        Args:
            pursuit_id: The pursuit
            interaction_type: Type of interaction (question, guidance, etc.)
            user_request: What the user asked/requested
            coach_response_summary: Brief summary of coach response
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "interaction_type": interaction_type,
            "user_request": user_request,
            "coach_response_summary": coach_response_summary or "",
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.COACHING_INTERACTION,
            details=details,
            context=context,
            is_external_influence=True,  # Always tagged
        )

    def record_element_captured(
        self,
        pursuit_id: str,
        element_type: str,
        element_id: str,
        element_summary: str = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record an element capture event.

        Args:
            pursuit_id: The pursuit
            element_type: Type of element captured
            element_id: ID of the element
            element_summary: Brief summary of element content
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "element_type": element_type,
            "element_id": element_id,
            "element_summary": element_summary or "",
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.ELEMENT_CAPTURED,
            details=details,
            context=context,
        )

    def record_risk_validation(
        self,
        pursuit_id: str,
        risk_id: str,
        validation_type: str,
        outcome: str = None,
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Record a risk validation activity (RVE experiment).

        Args:
            pursuit_id: The pursuit
            risk_id: ID of the risk being validated
            validation_type: Type of validation activity
            outcome: Outcome if known
            context: Additional context

        Returns:
            Observation ID if recorded
        """
        details = {
            "risk_id": risk_id,
            "validation_type": validation_type,
            "outcome": outcome or "pending",
        }
        return self._record_observation(
            pursuit_id=pursuit_id,
            observation_type=ObservationType.RISK_VALIDATION,
            details=details,
            context=context,
        )

    # =========================================================================
    # OBSERVATION LIFECYCLE METHODS
    # =========================================================================

    def start_observation(self, pursuit_id: str) -> bool:
        """
        Start observation for an ad-hoc pursuit.

        Called when an ad-hoc pursuit is created.
        """
        if not self.is_adhoc_pursuit(pursuit_id):
            logger.warning(f"Cannot start observation for non-adhoc pursuit {pursuit_id}")
            return False

        db.update_pursuit_adhoc_metadata(pursuit_id, {
            "observation_status": ObservationStatus.ACTIVE.value,
            "observation_started_at": datetime.now(timezone.utc).isoformat(),
            "observation_count": 0,
        })

        logger.info(f"Observation started for pursuit {pursuit_id}")
        return True

    def pause_observation(self, pursuit_id: str) -> bool:
        """
        Pause observation for a pursuit.

        User can resume later.
        """
        return db.update_observation_status(pursuit_id, ObservationStatus.PAUSED.value)

    def resume_observation(self, pursuit_id: str) -> bool:
        """Resume paused observation."""
        return db.update_observation_status(pursuit_id, ObservationStatus.ACTIVE.value)

    def complete_observation(self, pursuit_id: str) -> bool:
        """
        Complete observation for a pursuit.

        Called when the pursuit is completed or terminal state reached.
        v3.7.2: Also triggers pattern inference if innovator is eligible.
        """
        success = db.update_observation_status(pursuit_id, ObservationStatus.COMPLETED.value)

        if success:
            # v3.7.2: Trigger synthesis check after completion
            self._trigger_synthesis_check_if_eligible(pursuit_id)

        return success

    def _trigger_synthesis_check_if_eligible(self, pursuit_id: str) -> None:
        """
        v3.7.2: Check if innovator is eligible for synthesis and run inference.

        This runs asynchronously after observation completion. It does not
        block the completion flow.
        """
        try:
            pursuit = db.get_pursuit(pursuit_id)
            if not pursuit:
                return

            innovator_id = pursuit.get("user_id")
            if not innovator_id:
                return

            eligibility = self.get_synthesis_eligibility(innovator_id)

            if eligibility["eligibility"] in ["ELIGIBLE", "HIGH_CONFIDENCE"]:
                logger.info(
                    f"Innovator {innovator_id} eligible for synthesis "
                    f"({eligibility['completed_adhoc_pursuits']} pursuits). "
                    f"Triggering pattern inference."
                )

                # Import here to avoid circular dependency
                from ems.pattern_inference import get_pattern_inference_engine

                engine = get_pattern_inference_engine()
                result = engine.infer_patterns(innovator_id)

                # Store result
                db.store_inference_result(innovator_id, result)

                logger.info(
                    f"Pattern inference complete for {innovator_id}: "
                    f"synthesis_ready={result.get('synthesis_ready', False)}"
                )

        except Exception as e:
            # Don't let inference errors break observation completion
            logger.warning(f"Error during synthesis check for {pursuit_id}: {e}")

    def abandon_observation(self, pursuit_id: str) -> bool:
        """
        Mark observation as abandoned.

        Called when pursuit is abandoned.
        """
        return db.update_observation_status(pursuit_id, ObservationStatus.ABANDONED.value)

    # =========================================================================
    # OBSERVATION RETRIEVAL METHODS
    # =========================================================================

    def get_observations(
        self,
        pursuit_id: str,
        exclude_coaching: bool = False,
        min_weight: float = 0.0,
    ) -> List[ProcessObservation]:
        """
        Get all observations for a pursuit.

        Args:
            pursuit_id: The pursuit
            exclude_coaching: If True, exclude coaching interactions
            min_weight: Minimum signal weight threshold

        Returns:
            List of ProcessObservation objects, ordered by sequence
        """
        raw = db.get_observations_for_pursuit(
            pursuit_id=pursuit_id,
            exclude_coaching=exclude_coaching,
            min_weight=min_weight,
        )
        return [ProcessObservation.from_dict(r) for r in raw]

    def get_observation_summary(self, pursuit_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for observations.

        Returns:
            Summary including counts by type, total weight, timeline
        """
        observations = self.get_observations(pursuit_id)

        if not observations:
            return {
                "total_observations": 0,
                "by_type": {},
                "total_weight": 0.0,
                "external_influence_count": 0,
                "timeline_start": None,
                "timeline_end": None,
                "duration_hours": 0,
            }

        by_type = {}
        total_weight = 0.0
        external_count = 0

        for obs in observations:
            type_key = obs.observation_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            total_weight += obs.signal_weight
            if obs.is_external_influence:
                external_count += 1

        first = observations[0]
        last = observations[-1]
        duration = (last.timestamp - first.timestamp).total_seconds() / 3600

        return {
            "total_observations": len(observations),
            "by_type": by_type,
            "total_weight": round(total_weight, 2),
            "external_influence_count": external_count,
            "timeline_start": first.timestamp.isoformat(),
            "timeline_end": last.timestamp.isoformat(),
            "duration_hours": round(duration, 1),
        }

    def get_synthesis_eligibility(self, innovator_id: str) -> Dict[str, Any]:
        """
        Check if innovator is eligible for methodology synthesis.

        Returns eligibility status and count of qualifying pursuits.
        """
        completed_count = db.get_adhoc_pursuit_count(innovator_id)
        threshold = self.config.get("synthesis_threshold_pursuits", 3)
        high_threshold = self.config.get("high_confidence_threshold", 5)

        if completed_count >= high_threshold:
            eligibility = "HIGH_CONFIDENCE"
        elif completed_count >= threshold:
            eligibility = "ELIGIBLE"
        else:
            eligibility = "NOT_ENOUGH_DATA"

        return {
            "eligibility": eligibility,
            "completed_adhoc_pursuits": completed_count,
            "threshold_for_eligibility": threshold,
            "threshold_for_high_confidence": high_threshold,
            "pursuits_until_eligible": max(0, threshold - completed_count),
            "pursuits_until_high_confidence": max(0, high_threshold - completed_count),
        }


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_process_observer: Optional[ProcessObserver] = None


def get_process_observer() -> ProcessObserver:
    """Get the singleton ProcessObserver instance."""
    global _process_observer
    if _process_observer is None:
        _process_observer = ProcessObserver()
    return _process_observer
