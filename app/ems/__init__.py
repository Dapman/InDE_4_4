"""
InDE EMS (Emergent Methodology Synthesizer) - v3.7.1
Process Observation Engine & Ad-Hoc Pursuit Mode

The EMS module enables InDE to learn from innovators who work without
predefined methodologies. By silently observing their natural process,
InDE can identify patterns and eventually synthesize personalized
methodologies.

Components:
- ProcessObserver: Core observation engine
- ObservationTypes: Standardized observation taxonomy
- ObservationStore: Persistence layer interface
- (Future) PatternInference: Cross-pursuit pattern detection
- (Future) MethodologySynthesizer: Emergent methodology generation
"""

from .process_observer import (
    ProcessObserver,
    ObservationType,
    ProcessObservation,
    get_process_observer,
)
from .events import (
    EMSEventType,
    EMSEvent,
    EMSEventHandler,
    get_ems_handler,
    register_ems_handlers,
)

__all__ = [
    "ProcessObserver",
    "ObservationType",
    "ProcessObservation",
    "get_process_observer",
    "EMSEventType",
    "EMSEvent",
    "EMSEventHandler",
    "get_ems_handler",
    "register_ems_handlers",
]
