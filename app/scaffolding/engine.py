"""
InDE MVP v3.6.1 - Scaffolding Engine "Intelligence Layer"

Main orchestrator that coordinates all scaffolding components.
This is what the UI calls for processing messages.

v3.6.1 Enhancement: Methodology Expansion & Scenario Intelligence
- TrizContextProvider: TRIZ contradiction-based coaching context
- BlueOceanContextProvider: Value innovation coaching context
- ScenarioContextProvider: Decision fork exploration coaching
- ScenarioDetector: Heuristic detection of decision forks
- Support for 5 archetypes: Lean Startup, Design Thinking, Stage-Gate, TRIZ, Blue Ocean

v3.6.0 Enhancement: Biomimicry Coaching Integration
- BiomimicryContextProvider: Nature-inspired innovation suggestions
- Conversational delivery (NOT wizard-like)
- Methodology-adaptive guidance (Lean Startup, Design Thinking, etc.)
- Accept/explore/defer/dismiss response handling
- Session-level cooldown tracking (5 turns between offers)

v3.5.2 Enhancement: IKF Pattern Integration
- IKF Pattern Context: Retrieves relevant global patterns from ikf_federation_patterns
- Attribution Language: "Innovators across the InDEVerse have found..."
- Per-turn token budget increased to 12,000 (+500 for IKF patterns)

v3.0.2 Enhancement: Intelligence Layer
- HealthMonitor: Real-time pursuit health scoring (0-100) with 5 zones
- TemporalPatternIntelligence: Enriched IML pattern matching with temporal signals
- PredictiveGuidanceEngine: Forward-looking predictions based on historical patterns
- TemporalRiskDetector: Three-horizon risk detection
- Full RVE: Experiment wizard, three-zone assessment, override capture
- Zone-specific coaching tone adjustment

v3.0.1 Features (maintained):
- TimeAllocationEngine: Phase-based timeline distribution
- VelocityTracker: Progress pace monitoring (elements/week)
- TemporalEventLogger: IKF-compatible event stream with ISO 8601 timestamps
- PhaseManager: Automatic phase transition detection

v2.7 Features (maintained):
- Terminal State Detection (6 terminal states)
- Retrospective Orchestrator for guided end-of-pursuit conversations
- Terminal Report Generation (SILR reports)
- Portfolio Manager for tracking terminal state distribution
- Stakeholder Notifier for terminal state notifications
- Learning Insights Generator for historical pattern analysis
- Retrospective mode handling with amber glow UI indicator

v2.6 Features (maintained):
- Support Landscape Analyzer for stakeholder feedback aggregation
- Fear Extractor for cross-validation with stakeholder concerns
- Pitch Orchestrator for stakeholder-informed pitch preparation
- Stakeholder engagement prompts at key transitions
- Pattern learning from stakeholder engagement outcomes

v2.5 Features (maintained):
- Pattern Engine for IML integration and historical pattern matching
- Adaptive Intervention Manager for engagement-based cooldowns
- 3 new intervention types: PATTERN_RELEVANT, CROSS_PURSUIT_INSIGHT, METHODOLOGY_GUIDANCE
- Important element extraction for richer pattern matching

Flow:
1. Check if in retrospective mode -> handle retrospective conversation
2. Check for pending artifact regeneration acceptance
3. Check for innovation intent -> auto-create pursuit if detected (+ TIM: init allocation)
4. Detect terminal state intent -> trigger retrospective if detected (+ TIM: log completion)
5. Extract critical + important elements from message (+ TIM: log element events)
6. Track user engagement metrics
7. Assess teleological profile (periodic)
8. Detect intervention moments (9 types with adaptive cooldowns) (+ TIM: log interventions)
9. v3.0.1: Check for automatic phase transitions based on completeness
10. v3.0.2: Calculate health score and adjust coaching tone
11. v3.0.2: Check for predictions and risk alerts to surface
12. Find relevant patterns if intervention warranted (with temporal enrichment)
13. Include stakeholder context in coaching response
14. Return response + updated history + pattern insights + velocity data + health status
"""

import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from config import DEMO_USER_ID

# v3.14: Onboarding metrics instrumentation
_onboarding_logger = logging.getLogger("inde.onboarding")


class ScaffoldingEngine:
    """
    Main orchestrator that coordinates all scaffolding components.
    This is what the UI calls.
    """

    def __init__(self, database, llm_interface):
        """
        Initialize ScaffoldingEngine.

        Args:
            database: Database instance
            llm_interface: LLMInterface instance
        """
        self.db = database
        self.llm = llm_interface

        # Import here to avoid circular imports
        from .intent_detector import IntentDetector
        from .element_tracker import ElementTracker
        from .moment_detector import MomentDetector
        from .artifact_generator import ArtifactGenerator
        from .teleological_assessor import TeleologicalAssessor
        from .question_banks import get_question_bank, get_question_for_moment
        from .lifecycle_manager import ArtifactLifecycleManager
        from .pattern_engine import PatternEngine
        from .adaptive_manager import AdaptiveInterventionManager
        from .support_analyzer import SupportLandscapeAnalyzer
        from .fear_extractor import FearExtractor
        from .pitch_orchestrator import PitchOrchestrator
        from .timeline_extractor import TimelineExtractor  # v3.9

        # v2.7: Terminal intelligence imports
        from .terminal_state_detector import TerminalStateDetector
        from .retrospective_orchestrator import RetrospectiveOrchestrator
        from reporting.terminal_report_generator import TerminalReportGenerator
        from portfolio.portfolio_manager import PortfolioManager
        from notifications.stakeholder_notifier import StakeholderNotifier
        from insights.learning_insights_generator import LearningInsightsGenerator

        # v3.0.1: Temporal Intelligence Module (TIM) imports
        from tim import TimeAllocationEngine, VelocityTracker, TemporalEventLogger, PhaseManager

        # v3.0.2: Intelligence Layer imports
        from intelligence import (
            HealthMonitor, TemporalPatternIntelligence,
            PredictiveGuidanceEngine, TemporalRiskDetector
        )

        # v3.5.2: IKF Pattern Context import
        from scaffolding.ikf_pattern_context import build_ikf_coaching_context

        # v4.1: Momentum Management Engine import
        from momentum import MomentumManagementEngine
        from momentum.bridge_selector import BridgeSelector
        from momentum.momentum_persistence import MomentumPersistence

        # Store for later use
        self._build_ikf_coaching_context = build_ikf_coaching_context

        # v4.1: Store MME classes for lazy instantiation
        self._MomentumManagementEngine = MomentumManagementEngine
        self._BridgeSelector = BridgeSelector
        self._MomentumPersistence = MomentumPersistence

        # Initialize components
        self.intent_detector = IntentDetector(llm_interface, database)
        self.element_tracker = ElementTracker(llm_interface, database)
        self.artifact_generator = ArtifactGenerator(llm_interface, database)

        # v2.4: Lifecycle manager for artifact versioning
        self.lifecycle_manager = ArtifactLifecycleManager(database, self.element_tracker)

        # v2.5: Pattern engine for IML integration
        self.pattern_engine = PatternEngine(llm_interface, database)

        # v2.5: Adaptive intervention manager for engagement-based cooldowns
        self.adaptive_manager = AdaptiveInterventionManager(database)

        # v2.6: Support landscape analyzer for stakeholder feedback
        self.support_analyzer = SupportLandscapeAnalyzer(database, self.pattern_engine)

        # v2.6: Fear extractor for cross-validation with stakeholder concerns
        self.fear_extractor = FearExtractor(database, llm_interface)

        # v2.6: Pitch orchestrator for stakeholder-informed pitch preparation
        self.pitch_orchestrator = PitchOrchestrator(
            database, self.support_analyzer, self.fear_extractor, self.pattern_engine
        )

        # v2.5/v2.6: Pass all components to MomentDetector for full intervention support
        self.moment_detector = MomentDetector(
            self.element_tracker,
            database,
            self.lifecycle_manager,
            self.pattern_engine,
            self.adaptive_manager
        )

        # v2.3: Teleological assessor for goal-oriented coaching
        self.teleological_assessor = TeleologicalAssessor(self.element_tracker, database)

        # v2.7: Terminal intelligence components
        self.terminal_detector = TerminalStateDetector(llm_interface, database)
        self.retrospective_orchestrator = RetrospectiveOrchestrator(
            llm_interface, database, self.pattern_engine
        )
        self.report_generator = TerminalReportGenerator(database)
        self.portfolio_manager = PortfolioManager(database)
        self.stakeholder_notifier = StakeholderNotifier(database)
        self.insights_generator = LearningInsightsGenerator(database)

        # v3.0.1: TIM components
        self.allocation_engine = TimeAllocationEngine(database)
        self.event_logger = TemporalEventLogger(database)
        self.velocity_tracker = VelocityTracker(database, self.allocation_engine)
        self.phase_manager = PhaseManager(database, self.allocation_engine, self.event_logger)

        # v3.0.2: Intelligence Layer components
        self.health_monitor = HealthMonitor(
            database, self.velocity_tracker, self.phase_manager
        )
        self.temporal_patterns = TemporalPatternIntelligence(
            database, self.velocity_tracker, self.phase_manager, self.event_logger
        )
        self.predictive_guidance = PredictiveGuidanceEngine(
            database, self.velocity_tracker, self.phase_manager, self.health_monitor
        )
        self.risk_detector = TemporalRiskDetector(
            database, self.velocity_tracker, self.phase_manager, self.health_monitor
        )

        # v3.9: Timeline Extractor for automatic milestone detection
        self.timeline_extractor = TimelineExtractor(llm_interface, database)

        # Store question bank functions for use in response generation
        self._get_question_bank = get_question_bank
        self._get_question_for_moment = get_question_for_moment

        # Track pending artifact generation - now stored in DB for persistence
        # self._pending_artifact = {}  # Deprecated - use DB

        # v2.4: Track pending artifact regeneration - now stored in DB
        # self._pending_regeneration = {}  # Deprecated - use DB

        # v2.3: Track conversation turns since last teleological assessment
        self._turns_since_assessment = {}

        # v2.5: Track last intervention for response detection
        self._last_intervention = {}

        # v2.7: Track active retrospectives by pursuit
        self._active_retrospectives = {}

        # v2.7: Track pending terminal state confirmation
        self._pending_terminal_confirmation = {}

        # v3.10: Track pending timeline conflicts for resolution
        self._pending_timeline_conflicts = {}

        # v3.1: Current user ID for multi-user support
        self._current_user_id = DEMO_USER_ID

        # v3.6.0: Track biomimicry offer turns per pursuit for cooldown
        self._biomimicry_offer_turns = {}

        # v3.6.0: Biomimicry context provider (lazy loaded)
        self._biomimicry_provider = None

        # v3.6.1: TRIZ, Blue Ocean, and Scenario context providers (lazy loaded)
        self._triz_provider = None
        self._blue_ocean_provider = None
        self._scenario_provider = None
        self._scenario_detector = None

        # v3.6.1: Track active scenario exploration per pursuit
        self._scenario_exploration_active = {}

        # v4.1: Track active MME sessions per pursuit
        self._mme_sessions = {}

    # =========================================================================
    # v3.1: User Management
    # =========================================================================

    def set_user_id(self, user_id: str):
        """
        Set the current user ID for multi-user support.

        Args:
            user_id: The authenticated user's ID
        """
        self._current_user_id = user_id
        print(f"[ScaffoldingEngine] User context set to: {user_id}")

    def get_user_id(self) -> str:
        """Get the current user ID."""
        return self._current_user_id

    def set_llm_preference(self, preference: str):
        """
        v3.9: Set the user's LLM provider preference.

        Args:
            preference: 'auto', 'cloud', or 'local'
        """
        self._llm_preference = preference
        print(f"[ScaffoldingEngine] LLM preference set to: {preference}")

    def get_llm_preference(self) -> str:
        """v3.9: Get the user's LLM provider preference."""
        return getattr(self, '_llm_preference', 'auto')

    # =========================================================================
    # v4.1: Momentum Management Engine Session Lifecycle
    # =========================================================================

    def _get_or_create_mme(self, pursuit_id: str, user_id: str) -> Optional[object]:
        """
        Get or create a Momentum Management Engine instance for a pursuit.

        MME instances are per-pursuit, not per-request. They persist in memory
        for the duration of a session and are snapshotted to MongoDB on session end.

        Args:
            pursuit_id: The pursuit ID
            user_id: The user's GII (hashed)

        Returns:
            MomentumManagementEngine instance, or None if pursuit_id is None
        """
        if not pursuit_id:
            return None

        if pursuit_id not in self._mme_sessions:
            # Create new MME for this pursuit
            import uuid
            session_id = str(uuid.uuid4())
            self._mme_sessions[pursuit_id] = self._MomentumManagementEngine(
                session_id=session_id,
                pursuit_id=pursuit_id,
                gii_id=user_id
            )
            print(f"[Engine] v4.1: MME initialized for pursuit={pursuit_id}")

        return self._mme_sessions[pursuit_id]

    def _close_mme_session(self, pursuit_id: str, exit_reason: str = "natural"):
        """
        Close an MME session and persist the snapshot to MongoDB.

        Args:
            pursuit_id: The pursuit ID
            exit_reason: Why the session ended ("natural", "timeout", "bridge_exit")
        """
        if pursuit_id and pursuit_id in self._mme_sessions:
            mme = self._mme_sessions[pursuit_id]
            snapshot = mme.snapshot(exit_reason=exit_reason)

            # Persist to MongoDB
            persistence = self._MomentumPersistence(self.db.db)
            persistence.save_snapshot(snapshot)

            # Remove from active sessions
            del self._mme_sessions[pursuit_id]
            print(f"[Engine] v4.1: MME session closed for pursuit={pursuit_id}")

    # =========================================================================
    # v2.7 FIX: Database-backed pending state management
    # =========================================================================

    def _get_pending_artifact(self, pursuit_id: str) -> dict:
        """Get pending artifact from database for persistence across requests."""
        if not pursuit_id:
            return {}
        pending = self.db.db.pending_artifacts.find_one({"pursuit_id": pursuit_id})
        return pending or {}

    def _set_pending_artifact(self, pursuit_id: str, artifact_type: str):
        """Store pending artifact in database for persistence."""
        from datetime import datetime
        self.db.db.pending_artifacts.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "pursuit_id": pursuit_id,
                "artifact_type": artifact_type,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _clear_pending_artifact(self, pursuit_id: str):
        """Clear pending artifact from database."""
        if pursuit_id:
            self.db.db.pending_artifacts.delete_one({"pursuit_id": pursuit_id})

    def _get_pending_regeneration(self, pursuit_id: str) -> dict:
        """Get pending regeneration from database."""
        if not pursuit_id:
            return {}
        pending = self.db.db.pending_regenerations.find_one({"pursuit_id": pursuit_id})
        return pending or {}

    def _set_pending_regeneration(self, pursuit_id: str, artifact_id: str,
                                   artifact_type: str, change_severity: str = None):
        """Store pending regeneration in database."""
        from datetime import datetime
        self.db.db.pending_regenerations.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "pursuit_id": pursuit_id,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "change_severity": change_severity,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _clear_pending_regeneration(self, pursuit_id: str):
        """Clear pending regeneration from database."""
        if pursuit_id:
            self.db.db.pending_regenerations.delete_one({"pursuit_id": pursuit_id})

    # =========================================================================
    # v3.6.0: Biomimicry State Management
    # =========================================================================

    def _get_biomimicry_offer_turn(self, pursuit_id: str) -> Optional[int]:
        """Get the last turn number when biomimicry was offered for this pursuit."""
        return self._biomimicry_offer_turns.get(pursuit_id)

    def _set_biomimicry_offer_turn(self, pursuit_id: str, turn: int):
        """Record that biomimicry was offered on this turn."""
        self._biomimicry_offer_turns[pursuit_id] = turn

    def _get_biomimicry_provider(self):
        """
        Lazy-load the biomimicry context provider.

        Returns None if the IKF service is not available or biomimicry
        is not configured. The provider is cached for reuse.
        """
        if self._biomimicry_provider is not None:
            return self._biomimicry_provider

        try:
            from scaffolding.biomimicry_context import create_biomimicry_context_provider
            provider, analyzer, detector, feedback = create_biomimicry_context_provider(
                db=self.db.db,
                llm_gateway=self.llm,
                event_publisher=None,  # TODO: Wire event publisher
                config=None
            )
            self._biomimicry_provider = provider
            return provider
        except ImportError as e:
            print(f"[ScaffoldingEngine] Biomimicry provider not available: {e}")
            return None
        except Exception as e:
            print(f"[ScaffoldingEngine] Failed to initialize biomimicry provider: {e}")
            return None

    # =========================================================================
    # v3.6.1: TRIZ, Blue Ocean, and Scenario Context Providers
    # =========================================================================

    def _get_triz_provider(self):
        """
        Lazy-load the TRIZ context provider.

        Returns None if TRIZ methodology modules are not available.
        The provider is cached for reuse.
        """
        if self._triz_provider is not None:
            return self._triz_provider

        try:
            from scaffolding.triz_context import create_triz_context_provider
            import asyncio
            # Need to run async factory in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context - use existing approach
                return None  # Will be handled asynchronously
            provider = loop.run_until_complete(create_triz_context_provider(self.db.db))
            self._triz_provider = provider
            return provider
        except ImportError as e:
            print(f"[ScaffoldingEngine] TRIZ provider not available: {e}")
            return None
        except Exception as e:
            print(f"[ScaffoldingEngine] Failed to initialize TRIZ provider: {e}")
            return None

    def _get_blue_ocean_provider(self):
        """
        Lazy-load the Blue Ocean context provider.

        Returns None if Blue Ocean methodology modules are not available.
        The provider is cached for reuse.
        """
        if self._blue_ocean_provider is not None:
            return self._blue_ocean_provider

        try:
            from scaffolding.blue_ocean_context import create_blue_ocean_context_provider
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            provider = loop.run_until_complete(create_blue_ocean_context_provider())
            self._blue_ocean_provider = provider
            return provider
        except ImportError as e:
            print(f"[ScaffoldingEngine] Blue Ocean provider not available: {e}")
            return None
        except Exception as e:
            print(f"[ScaffoldingEngine] Failed to initialize Blue Ocean provider: {e}")
            return None

    def _get_scenario_provider(self):
        """
        Lazy-load the Scenario context provider.

        Returns None if scenario modules are not available.
        The provider is cached for reuse.
        """
        if self._scenario_provider is not None:
            return self._scenario_provider

        try:
            from scaffolding.scenario_context import create_scenario_context_provider
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            provider = loop.run_until_complete(create_scenario_context_provider())
            self._scenario_provider = provider
            return provider
        except ImportError as e:
            print(f"[ScaffoldingEngine] Scenario provider not available: {e}")
            return None
        except Exception as e:
            print(f"[ScaffoldingEngine] Failed to initialize scenario provider: {e}")
            return None

    def _get_scenario_detector(self):
        """
        Lazy-load the Scenario detector.

        Returns None if scenario modules are not available.
        The detector is cached for reuse.
        """
        if self._scenario_detector is not None:
            return self._scenario_detector

        try:
            from coaching.scenario_detection import ScenarioDetector
            self._scenario_detector = ScenarioDetector()
            return self._scenario_detector
        except ImportError as e:
            print(f"[ScaffoldingEngine] Scenario detector not available: {e}")
            return None
        except Exception as e:
            print(f"[ScaffoldingEngine] Failed to initialize scenario detector: {e}")
            return None

    def _is_scenario_exploration_active(self, pursuit_id: str) -> bool:
        """Check if scenario exploration is active for this pursuit."""
        return self._scenario_exploration_active.get(pursuit_id, False)

    def _set_scenario_exploration_active(self, pursuit_id: str, active: bool):
        """Set scenario exploration state for this pursuit."""
        self._scenario_exploration_active[pursuit_id] = active

    # =========================================================================
    # v3.2 FIX: Database-backed pending terminal confirmation
    # =========================================================================

    def _get_pending_terminal_confirmation(self, pursuit_id: str) -> dict:
        """Get pending terminal confirmation from database for persistence across requests."""
        if not pursuit_id:
            return {}
        pending = self.db.db.pending_terminal_confirmations.find_one({"pursuit_id": pursuit_id})
        return pending or {}

    def _set_pending_terminal_confirmation(self, pursuit_id: str, terminal_state: str,
                                            intent: dict = None):
        """Store pending terminal confirmation in database for persistence."""
        from datetime import datetime
        self.db.db.pending_terminal_confirmations.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "pursuit_id": pursuit_id,
                "terminal_state": terminal_state,
                "intent": intent or {},
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _clear_pending_terminal_confirmation(self, pursuit_id: str):
        """Clear pending terminal confirmation from database."""
        if pursuit_id:
            self.db.db.pending_terminal_confirmations.delete_one({"pursuit_id": pursuit_id})

    def process_message(self, message: str, current_pursuit_id: str = None,
                        user_id: str = DEMO_USER_ID) -> Dict:
        """
        Main processing pipeline for each user message.

        Args:
            message: User's message text
            current_pursuit_id: Current pursuit ID (or None/"New Conversation")
            user_id: User ID

        Returns:
            {
                "response": "assistant response text",
                "pursuit_id": "uuid or None",
                "pursuit_title": "string or None",
                "artifacts_generated": ["artifact_id", ...],
                "artifact_content": "artifact content if generated",
                "intervention_made": "moment_type or None",
                "retrospective_mode": bool,  # v2.7
                "retrospective_progress": int  # v2.7
            }
        """
        artifacts_generated = []
        artifact_content = None
        intervention_made = None
        retrospective_mode = False
        retrospective_progress = 0

        # v4.1: Initialize momentum context (will be populated after processing)
        momentum_context = None

        # v2.7 FIX: Check for pursuit recall/load commands FIRST
        recall_result = self._detect_pursuit_recall(message, user_id)
        if recall_result:
            return recall_result

        # v2.7 STEP 0: Check if pursuit is in retrospective mode
        # v3.7.4: Also check database for active retrospectives (survives server restart)
        if current_pursuit_id and self.is_in_retrospective_mode(current_pursuit_id):
            return self._handle_retrospective_message(
                message, current_pursuit_id, user_id
            )

        # v2.7/v3.2 FIX: Check for pending terminal state confirmation (DB-backed)
        # Note: Only check if current_pursuit_id is not None to avoid None == None matching
        pending_terminal = self._get_pending_terminal_confirmation(current_pursuit_id)
        if current_pursuit_id and pending_terminal.get("pursuit_id") == current_pursuit_id:
            if self._user_accepted_formalization(message):
                terminal_state = pending_terminal.get("terminal_state")
                return self._initiate_retrospective(
                    current_pursuit_id, terminal_state, user_id
                )
            elif self._user_declined_formalization(message):
                self._clear_pending_terminal_confirmation(current_pursuit_id)
                # Continue with normal processing

        # STEP 0: Check if user is accepting pending artifact generation (DB-backed for persistence)
        # Note: Only check if current_pursuit_id is not None to avoid None == None matching
        pending_artifact = self._get_pending_artifact(current_pursuit_id)
        print(f"[Engine] STEP 0 - pending_artifact: {pending_artifact}, current_pursuit: {current_pursuit_id}")
        if current_pursuit_id and pending_artifact.get("pursuit_id") == current_pursuit_id:
            print(f"[Engine] Checking if user accepted: '{message[:50]}...'")
            if self._user_accepted_formalization(message):
                artifact_type = pending_artifact.get("artifact_type")
                print(f"[Engine] User accepted formalization, artifact_type: {artifact_type}")

                if artifact_type:
                    artifact = self.artifact_generator.generate_artifact(
                        current_pursuit_id, artifact_type, method="user_requested"
                    )
                    if artifact:
                        artifacts_generated.append(artifact["artifact_id"])
                        artifact_content = artifact["content"]

                        # v3.0.1: Log artifact generation event
                        current_phase = self.phase_manager.get_current_phase(current_pursuit_id)
                        self.event_logger.log_artifact_generated(
                            pursuit_id=current_pursuit_id,
                            phase=current_phase,
                            artifact_type=artifact_type,
                            artifact_id=artifact["artifact_id"],
                            version=artifact.get("version", 1)
                        )

                        # Clear pending from DB
                        self._clear_pending_artifact(current_pursuit_id)

                        # v2.5: Record artifact interaction for engagement tracking
                        self.adaptive_manager.record_artifact_interaction(user_id, current_pursuit_id)

                        # Save conversation turns
                        self._save_conversation_turn(
                            pursuit_id=current_pursuit_id,
                            role="user",
                            content=message,
                            metadata={"accepted_artifact": artifact_type}
                        )

                        # Build response with artifact (wrapped in markers for frontend detection)
                        pursuit = self.db.get_pursuit(current_pursuit_id)

                        # v4.1: Use BridgeSelector with momentum-aware selection
                        mme = self._get_or_create_mme(current_pursuit_id, user_id)
                        if mme:
                            momentum_context = mme.process_turn(message=message, artifact_active=artifact_type)
                            momentum_tier = momentum_context.get("momentum_tier", "MEDIUM")
                        else:
                            momentum_tier = "MEDIUM"

                        bridge_selector = self._BridgeSelector()
                        bridge = bridge_selector.select(
                            completed_artifact=artifact_type,
                            momentum_tier=momentum_tier,
                            pursuit_context={
                                "idea_domain": pursuit.get("domain", "") if pursuit else "",
                                "idea_summary": pursuit.get("description", "") if pursuit else "",
                                "user_name": "",
                                "persona": pursuit.get("primary_persona", "") if pursuit else "",
                            }
                        )

                        # Notify MME that bridge was delivered
                        if mme:
                            mme.record_bridge_delivered()

                        response = f"Here's your {artifact_type} statement:\n\n[ARTIFACT:{artifact_type}]\n{artifact_content}\n[/ARTIFACT]\n\n{bridge}"

                        self._save_conversation_turn(
                            pursuit_id=current_pursuit_id,
                            role="assistant",
                            content=response,
                            metadata={"artifacts_generated": artifacts_generated}
                        )

                        return {
                            "response": response,
                            "pursuit_id": current_pursuit_id,
                            "pursuit_title": pursuit.get("title") if pursuit else None,
                            "artifacts_generated": artifacts_generated,
                            "artifact_content": artifact_content,
                            "intervention_made": "ARTIFACT_GENERATED",
                            "retrospective_mode": False,
                            "retrospective_progress": 0
                        }
                else:
                    print(f"[Engine] WARNING: No artifact_type in pending_artifact")
                    self._clear_pending_artifact(current_pursuit_id)

            # v2.5 FIX: Only clear pending if user explicitly declined
            # Don't clear just because they talked about something else
            if self._user_declined_formalization(message):
                self._clear_pending_artifact(current_pursuit_id)
            # Otherwise keep the pending artifact active for future turns (persisted in DB)

        # STEP 0.5 (v2.4): Check if user is accepting artifact regeneration (DB-backed)
        # Note: Only check if current_pursuit_id is not None to avoid None == None matching
        pending_regen = self._get_pending_regeneration(current_pursuit_id)
        if current_pursuit_id and pending_regen.get("pursuit_id") == current_pursuit_id:
            if self._user_accepted_formalization(message):
                artifact_id = pending_regen.get("artifact_id")
                artifact_type = pending_regen.get("artifact_type")

                # Regenerate artifact
                regen_result = self.lifecycle_manager.regenerate_artifact(
                    artifact_id, self.artifact_generator
                )

                if regen_result:
                    artifacts_generated.append(regen_result["artifact_id"])
                    artifact_content = regen_result["content"]
                    version = regen_result["version"]

                    # Clear pending from DB
                    self._clear_pending_regeneration(current_pursuit_id)

                    # Save conversation turns
                    self._save_conversation_turn(
                        pursuit_id=current_pursuit_id,
                        role="user",
                        content=message,
                        metadata={"accepted_regeneration": artifact_type, "version": version}
                    )

                    # Build response with regenerated artifact (wrapped in markers)
                    pursuit = self.db.get_pursuit(current_pursuit_id)

                    # v4.1: Use BridgeSelector with momentum-aware selection
                    mme = self._get_or_create_mme(current_pursuit_id, user_id)
                    if mme:
                        momentum_context = mme.process_turn(message=message, artifact_active=artifact_type)
                        momentum_tier = momentum_context.get("momentum_tier", "MEDIUM")
                    else:
                        momentum_tier = "MEDIUM"

                    bridge_selector = self._BridgeSelector()
                    bridge = bridge_selector.select(
                        completed_artifact=artifact_type,
                        momentum_tier=momentum_tier,
                        pursuit_context={
                            "idea_domain": pursuit.get("domain", "") if pursuit else "",
                            "idea_summary": pursuit.get("description", "") if pursuit else "",
                            "user_name": "",
                            "persona": pursuit.get("primary_persona", "") if pursuit else "",
                        }
                    )

                    # Notify MME that bridge was delivered
                    if mme:
                        mme.record_bridge_delivered()

                    response = (
                        f"Here's your updated {artifact_type} statement (v{version}):\n\n"
                        f"[ARTIFACT:{artifact_type}]\n{artifact_content}\n[/ARTIFACT]\n\n"
                        f"I've preserved the previous version (v{version - 1}) in your Innovation Memory "
                        f"so you can track how your thinking has evolved.\n\n{bridge}"
                    )

                    self._save_conversation_turn(
                        pursuit_id=current_pursuit_id,
                        role="assistant",
                        content=response,
                        metadata={"artifact_regenerated": artifact_id, "new_version": version}
                    )

                    return {
                        "response": response,
                        "pursuit_id": current_pursuit_id,
                        "pursuit_title": pursuit.get("title") if pursuit else None,
                        "artifacts_generated": artifacts_generated,
                        "artifact_content": artifact_content,
                        "intervention_made": "ARTIFACT_REGENERATED",
                        "retrospective_mode": False,
                        "retrospective_progress": 0
                    }

            # User didn't accept, clear pending from DB
            if self._user_declined_formalization(message):
                self._clear_pending_regeneration(current_pursuit_id)

        # STEP 1: Check for innovation intent (if no active pursuit)
        if not current_pursuit_id or current_pursuit_id == "New Conversation":
            intent_result = self.intent_detector.analyze_message(message, user_id)

            if intent_result.get("create_pursuit"):
                # Auto-create pursuit silently
                current_pursuit_id = self.intent_detector.create_pursuit_silently(
                    intent_result, user_id
                )
                # Note: We don't tell the user we created a pursuit
                # We just start coaching naturally

                # v3.0.1: Initialize TIM for new pursuit
                self._initialize_tim_for_pursuit(current_pursuit_id, intent_result.get("suggested_title"))
            else:
                # No innovation intent detected, have general conversation
                return {
                    "response": self._general_conversation_response(message),
                    "pursuit_id": None,
                    "pursuit_title": None,
                    "artifacts_generated": [],
                    "artifact_content": None,
                    "intervention_made": None
                }

        # v2.7 FIX STEP 1.5: Check for explicit artifact request
        # If user explicitly asks for an artifact, generate immediately without confirmation
        explicit_artifact_type = self._detect_explicit_artifact_request(message)
        if explicit_artifact_type and current_pursuit_id:
            print(f"[Engine] EXPLICIT ARTIFACT REQUEST detected: {explicit_artifact_type}")

            # Check if we have enough elements to generate
            completeness = self.element_tracker.get_completeness(current_pursuit_id)

            # v3.7.1: Experiment artifacts don't use element completeness - they always generate
            # because they pull from validation_experiments or hypothesis elements
            if explicit_artifact_type == "experiment":
                artifact_completeness = 1.0  # Always allow experiment artifacts
            else:
                artifact_completeness = completeness.get(explicit_artifact_type, 0)
            print(f"[Engine] Completeness for {explicit_artifact_type}: {artifact_completeness:.2f}")

            # v2.7.1: Very low threshold for explicit requests - user knows what they want
            # Even at 25% we can generate a partial artifact
            if artifact_completeness >= 0.25:
                # Check if artifact already exists
                existing = self.db.get_pursuit_artifacts(current_pursuit_id, explicit_artifact_type)
                if not existing:
                    # Generate immediately!
                    print(f"[Engine] Generating {explicit_artifact_type} artifact on explicit request")
                    artifact = self.artifact_generator.generate_artifact(
                        current_pursuit_id, explicit_artifact_type, method="explicit_request"
                    )
                    if artifact:
                        pursuit = self.db.get_pursuit(current_pursuit_id)

                        # Save conversation turns
                        self._save_conversation_turn(
                            pursuit_id=current_pursuit_id,
                            role="user",
                            content=message,
                            metadata={"explicit_artifact_request": explicit_artifact_type}
                        )

                        # v3.7.1: Use appropriate label for artifact type
                        artifact_label = "data collection sheet" if explicit_artifact_type == "experiment" else f"{explicit_artifact_type} statement"

                        # v4.1: Use BridgeSelector with momentum-aware selection
                        mme = self._get_or_create_mme(current_pursuit_id, user_id)
                        if mme:
                            momentum_context = mme.process_turn(message=message, artifact_active=explicit_artifact_type)
                            momentum_tier = momentum_context.get("momentum_tier", "MEDIUM")
                        else:
                            momentum_tier = "MEDIUM"

                        bridge_selector = self._BridgeSelector()
                        bridge = bridge_selector.select(
                            completed_artifact=explicit_artifact_type,
                            momentum_tier=momentum_tier,
                            pursuit_context={
                                "idea_domain": pursuit.get("domain", "") if pursuit else "",
                                "idea_summary": pursuit.get("description", "") if pursuit else "",
                                "user_name": "",
                                "persona": pursuit.get("primary_persona", "") if pursuit else "",
                            }
                        )

                        # Notify MME that bridge was delivered
                        if mme:
                            mme.record_bridge_delivered()

                        # v3.8: Wrap in artifact markers for popup display
                        response = f"Here's your {artifact_label}:\n\n[ARTIFACT:{explicit_artifact_type}]\n{artifact['content']}\n[/ARTIFACT]\n\n{bridge}"

                        self._save_conversation_turn(
                            pursuit_id=current_pursuit_id,
                            role="assistant",
                            content=response,
                            metadata={"artifacts_generated": [artifact["artifact_id"]]}
                        )

                        # Clear any pending artifact since we just generated
                        self._clear_pending_artifact(current_pursuit_id)

                        return {
                            "response": response,
                            "pursuit_id": current_pursuit_id,
                            "pursuit_title": pursuit.get("title") if pursuit else None,
                            "artifacts_generated": [artifact["artifact_id"]],
                            "artifact_content": artifact["content"],
                            "intervention_made": "EXPLICIT_ARTIFACT_GENERATED",
                            "retrospective_mode": False,
                            "retrospective_progress": 0
                        }
                    else:
                        print(f"[Engine] Artifact generator returned None for {explicit_artifact_type}")
                else:
                    # v2.7.1: Artifact already exists - return it to the user
                    print(f"[Engine] Artifact {explicit_artifact_type} already exists, returning existing")
                    pursuit = self.db.get_pursuit(current_pursuit_id)
                    latest_artifact = existing[0]  # Most recent

                    self._save_conversation_turn(
                        pursuit_id=current_pursuit_id,
                        role="user",
                        content=message,
                        metadata={"requested_existing_artifact": explicit_artifact_type}
                    )

                    # v3.7.1: Use appropriate label for artifact type
                    artifact_label = "data collection sheet" if explicit_artifact_type == "experiment" else f"{explicit_artifact_type} statement"
                    # v3.8: Wrap in artifact markers for popup display
                    artifact_content = latest_artifact.get('content', 'Content not available')
                    response = f"Here's your existing {artifact_label}:\n\n[ARTIFACT:{explicit_artifact_type}]\n{artifact_content}\n[/ARTIFACT]\n\nWould you like me to update this based on our recent conversation?"

                    self._save_conversation_turn(
                        pursuit_id=current_pursuit_id,
                        role="assistant",
                        content=response,
                        metadata={"returned_existing_artifact": latest_artifact.get("artifact_id")}
                    )

                    return {
                        "response": response,
                        "pursuit_id": current_pursuit_id,
                        "pursuit_title": pursuit.get("title") if pursuit else None,
                        "artifacts_generated": [],
                        "artifact_content": latest_artifact.get("content"),
                        "intervention_made": "EXISTING_ARTIFACT_RETURNED",
                        "retrospective_mode": False,
                        "retrospective_progress": 0
                    }
            else:
                print(f"[Engine] Completeness too low for {explicit_artifact_type}: {artifact_completeness:.2f}, need at least 0.25")

        # STEP 2: Extract elements from this message
        _t_start = time.time()
        extracted = self.element_tracker.extract_elements(message, current_pursuit_id)
        print(f"[Engine] STEP 2 element extraction: {time.time() - _t_start:.2f}s")

        # v3.0.1: Log element capture events for TIM
        if extracted.get("extracted_count", 0) > 0:
            current_phase = self.phase_manager.get_current_phase(current_pursuit_id)
            for elem_type, elements in extracted.get("elements", {}).items():
                for elem_key, elem_data in elements.items():
                    if elem_data and elem_data.get("text"):
                        self.event_logger.log_element_captured(
                            pursuit_id=current_pursuit_id,
                            phase=current_phase,
                            element_type=elem_type,
                            element_key=elem_key,
                            confidence=elem_data.get("confidence", 0.0)
                        )

        # STEP 2.1 (v2.5): Extract important elements for richer pattern matching
        _t_start = time.time()
        important_extracted = self.element_tracker.extract_important_elements(
            message, current_pursuit_id
        )
        print(f"[Engine] STEP 2.1 important elements: {time.time() - _t_start:.2f}s")

        # STEP 2.2 (v3.9/v3.10/v3.11): Extract timeline milestones from conversation
        _t_start = time.time()
        extraction_result = self.timeline_extractor.extract_milestones(
            message, current_pursuit_id, user_id  # v3.11: pass user_id for created_by tracking
        )
        print(f"[Engine] STEP 2.2 milestone extraction: {time.time() - _t_start:.2f}s")

        # v3.10: Handle new return format with stored milestones and pending conflicts
        stored_milestones = extraction_result.get("stored", []) if isinstance(extraction_result, dict) else extraction_result
        pending_conflicts = extraction_result.get("pending_conflicts", []) if isinstance(extraction_result, dict) else []

        # Log milestone events to TIM
        if stored_milestones:
            current_phase = self.phase_manager.get_current_phase(current_pursuit_id)
            for milestone in stored_milestones:
                self.event_logger.log_milestone_extracted(
                    pursuit_id=current_pursuit_id,
                    phase=current_phase,
                    milestone=milestone
                )
            print(f"[Engine] Extracted {len(stored_milestones)} milestones from turn")

        # v3.10: Log and track pending conflicts for resolution
        if pending_conflicts:
            current_phase = self.phase_manager.get_current_phase(current_pursuit_id)
            for conflict in pending_conflicts:
                self.event_logger.log_timeline_conflict(
                    pursuit_id=current_pursuit_id,
                    phase=current_phase,
                    conflict_data={
                        "milestone_title": conflict["milestone"].get("title"),
                        "proposed_date": conflict["conflict_result"].proposed_date,
                        "existing_date": conflict["conflict_result"].existing_date,
                        "existing_milestone_id": conflict["conflict_result"].existing_milestone_id,
                        "day_difference": conflict["conflict_result"].day_difference,
                        "severity": conflict["conflict_result"].severity.value
                    }
                )
            # Store pending conflicts in session state for coaching response
            self._pending_timeline_conflicts[current_pursuit_id] = pending_conflicts
            print(f"[Engine] {len(pending_conflicts)} milestone conflicts pending resolution")

        # STEP 2.3 (v2.5): Track engagement metrics for adaptive cooldowns
        self.adaptive_manager.record_user_message(user_id, current_pursuit_id, message)

        # Check if user responded to last intervention
        last_intervention = self._last_intervention.get(current_pursuit_id)
        if last_intervention:
            responded = self.adaptive_manager.detect_response_to_intervention(
                message, last_intervention
            )
            self.adaptive_manager.record_intervention_response(
                user_id, current_pursuit_id, responded
            )

        # v2.7 STEP 2.4: Check for terminal state intent
        # v2.7 FIX: Skip terminal detection if there's a pending artifact request
        # This prevents the retrospective flow from hijacking artifact generation
        pending_artifact = self._get_pending_artifact(current_pursuit_id)
        pending_regen = self._get_pending_regeneration(current_pursuit_id)
        skip_terminal = bool(pending_artifact.get("pursuit_id") or pending_regen.get("pursuit_id"))

        _t_start = time.time()
        terminal_intent = self.terminal_detector.detect_terminal_intent(
            message, current_pursuit_id, skip_semantic=skip_terminal
        )
        print(f"[Engine] STEP 2.4 terminal detection: {time.time() - _t_start:.2f}s (skipped={skip_terminal})")
        terminal_state = terminal_intent.get("state", "ACTIVE")
        if terminal_state != "ACTIVE" and terminal_intent.get("confidence", 0) >= 0.70:
            # Ask for confirmation before starting retrospective (v3.2 FIX: DB-backed)
            self._set_pending_terminal_confirmation(
                current_pursuit_id, terminal_state, terminal_intent
            )
            pursuit = self.db.get_pursuit(current_pursuit_id)
            pursuit_title = pursuit.get("title", "your pursuit") if pursuit else "your pursuit"

            # Generate confirmation prompt
            state_descriptions = {
                "COMPLETED.SUCCESSFUL": "achieved its goals",
                "COMPLETED.VALIDATED_NOT_PURSUED": "been validated but you've decided not to proceed",
                "TERMINATED.INVALIDATED": "been invalidated through testing",
                "TERMINATED.PIVOTED": "pivoted to a new direction",
                "TERMINATED.ABANDONED": "been discontinued",
                "TERMINATED.OBE": "been overtaken by events"
            }
            state_desc = state_descriptions.get(terminal_state, "reached its conclusion")

            response = (
                f"It sounds like **{pursuit_title}** has {state_desc}. "
                f"Would you like to conduct a brief retrospective to capture what you've learned? "
                f"This will help build your innovation memory and benefit future pursuits."
            )

            self._save_conversation_turn(
                pursuit_id=current_pursuit_id, role="user", content=message,
                metadata={"terminal_intent_detected": terminal_state}
            )
            self._save_conversation_turn(
                pursuit_id=current_pursuit_id, role="assistant", content=response,
                metadata={"awaiting_terminal_confirmation": True}
            )

            return {
                "response": response,
                "pursuit_id": current_pursuit_id,
                "pursuit_title": pursuit_title,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": "TERMINAL_TRANSITION",
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        # STEP 2.5 (v2.3): Periodic teleological assessment
        self._turns_since_assessment[current_pursuit_id] = \
            self._turns_since_assessment.get(current_pursuit_id, 0) + 1

        teleological_context = None
        if self.teleological_assessor.should_reassess(
            current_pursuit_id,
            self._turns_since_assessment.get(current_pursuit_id, 0)
        ):
            teleological_context = self.teleological_assessor.get_coaching_context(
                current_pursuit_id
            )
            self._turns_since_assessment[current_pursuit_id] = 0
        else:
            # Use cached assessment
            teleological_context = self.teleological_assessor.get_coaching_context(
                current_pursuit_id
            )

        # v3.0.1 STEP 2.6: Check for automatic phase transitions
        completeness = self.element_tracker.get_completeness(current_pursuit_id)
        phase_transition = self.phase_manager.detect_phase_transition(
            current_pursuit_id, completeness
        )
        if phase_transition and phase_transition.get("trigger") == "automatic":
            self.phase_manager.execute_transition(
                pursuit_id=current_pursuit_id,
                to_phase=phase_transition["to_phase"],
                trigger="automatic",
                reason=phase_transition.get("reason")
            )
            print(f"[Engine] Auto phase transition: {phase_transition['from_phase']} -> {phase_transition['to_phase']}")

        # STEP 3: Detect intervention moments (v2.5: includes user_id for cross-pursuit)
        moments = self.moment_detector.detect_moments(current_pursuit_id, message, user_id)
        intervention = moments[0] if moments else None  # Use highest priority

        # STEP 3.5 (v2.3): Select question from appropriate bank
        selected_question = None
        if intervention and teleological_context:
            question_bank = teleological_context.get("question_bank", "validation")
            moment_type = intervention.get("type")
            missing_element = intervention.get("missing_element")

            questions = self._get_question_for_moment(
                question_bank, moment_type, missing_element
            )

            # Select unused question
            if questions:
                selected_question = self._select_unused_question(
                    current_pursuit_id, questions
                )

        # STEP 4: Generate coaching response
        conversation_history = self._get_recent_history(current_pursuit_id, limit=5)
        pursuit_context = self._get_pursuit_context(current_pursuit_id)

        # v3.0.2: Get health context for zone-aware coaching
        health_context = None
        try:
            health = self.health_monitor.calculate_health(current_pursuit_id)
            predictions = self.predictive_guidance.get_high_confidence_predictions(current_pursuit_id)
            risks = self.risk_detector.detect_risks(current_pursuit_id)

            health_context = {
                "zone": health.get("zone", "HEALTHY"),
                "health_score": health.get("health_score", 50),
                "top_prediction": predictions[0] if predictions else None,
                "top_risk": risks.get("top_risks", [{}])[0] if risks.get("top_risks") else None
            }
            print(f"[Engine] Health context: zone={health_context['zone']}, score={health_context['health_score']}")
        except Exception as e:
            print(f"[Engine] Health context warning: {e}")
            # Non-fatal - coaching continues without health context

        # v3.5.2: Get IKF pattern context for global pattern attribution
        ikf_context = None
        try:
            ikf_context = self._build_ikf_coaching_context(self.db, pursuit_context)
            if ikf_context:
                print(f"[Engine] IKF context: {ikf_context.get('pattern_count', 0)} patterns")
                # v3.14: Record IML pattern engagement for onboarding metrics
                if ikf_context.get('pattern_count', 0) > 0:
                    try:
                        from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
                        metrics = OnboardingMetricsService(self.db)
                        metrics.record_criterion_met_sync(user_id, "iml_pattern_engaged")
                    except Exception as om_err:
                        _onboarding_logger.warning(f"IML engagement recording failed: {om_err}")
        except Exception as e:
            print(f"[Engine] IKF context warning: {e}")
            # Non-fatal - coaching continues without IKF patterns

        # v4.1: Process message through Momentum Management Engine
        try:
            mme = self._get_or_create_mme(current_pursuit_id, user_id)
            if mme:
                # Determine current artifact from pursuit context
                artifact_active = None
                if pursuit_context:
                    completeness = pursuit_context.get("completeness", {})
                    # Detect which artifact is being worked on based on completeness
                    if completeness.get("vision", 0) < 1.0:
                        artifact_active = "vision"
                    elif completeness.get("fears", 0) < 1.0:
                        artifact_active = "fear"
                    elif completeness.get("hypothesis", 0) < 1.0:
                        artifact_active = "validation"

                momentum_context = mme.process_turn(
                    message=message,
                    artifact_active=artifact_active
                )
                print(f"[Engine] v4.1 Momentum: tier={momentum_context.get('momentum_tier')}, score={momentum_context.get('composite_score', 0):.2f}")
        except Exception as e:
            print(f"[Engine] v4.1 Momentum context warning: {e}")
            # Non-fatal - coaching continues without momentum context

        # v2.3: Pass teleological context and selected question to LLM
        # v3.0.2: Also pass health context for zone-aware coaching
        # v3.5.2: Also pass IKF pattern context for global pattern attribution
        # v3.9: Also pass user's LLM provider preference
        # v4.1: Also pass momentum context for tone guidance
        _t_start = time.time()
        response = self.llm.generate_coaching_response(
            user_message=message,
            conversation_history=conversation_history,
            pursuit_context=pursuit_context,
            intervention=intervention,
            teleological_context=teleological_context,
            selected_question=selected_question,
            health_context=health_context,
            ikf_context=ikf_context,  # v3.5.2
            momentum_context=momentum_context,  # v4.1
            preferred_provider=self.get_llm_preference()  # v3.9
        )
        print(f"[Engine] STEP 4 coaching response: {time.time() - _t_start:.2f}s")

        # STEP 5: Track pending artifact generation/regeneration based on intervention type (DB-backed)
        print(f"[Engine] STEP 5 - intervention: {intervention.get('type') if intervention else None}")
        if intervention and intervention.get("type") == "READY_TO_FORMALIZE":
            # Store in DB for persistence across requests
            self._set_pending_artifact(current_pursuit_id, intervention.get("artifact_type"))
            print(f"[Engine] STEP 5 - SET pending_artifact in DB: {intervention.get('artifact_type')}")
            intervention_made = intervention["type"]

            # Record the intervention
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )

        # v2.4: Track pending artifact regeneration if ARTIFACT_DRIFT (DB-backed)
        elif intervention and intervention.get("type") == "ARTIFACT_DRIFT":
            # Store in DB for persistence across requests
            self._set_pending_regeneration(
                current_pursuit_id,
                intervention.get("artifact_id"),
                intervention.get("artifact_type"),
                intervention.get("change_severity")
            )
            intervention_made = intervention["type"]

            # Record the intervention
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )

        # v2.5: Handle pattern-related interventions
        elif intervention and intervention.get("type") == "PATTERN_RELEVANT":
            intervention_made = intervention["type"]
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )
            # Track intervention for response detection
            self._last_intervention[current_pursuit_id] = intervention
            self.adaptive_manager.record_intervention(
                user_id, current_pursuit_id, intervention["type"]
            )

        # v2.5: Handle cross-pursuit insight interventions
        elif intervention and intervention.get("type") == "CROSS_PURSUIT_INSIGHT":
            intervention_made = intervention["type"]
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )
            self._last_intervention[current_pursuit_id] = intervention
            self.adaptive_manager.record_intervention(
                user_id, current_pursuit_id, intervention["type"]
            )

        # v2.5: Handle methodology guidance interventions
        elif intervention and intervention.get("type") == "METHODOLOGY_GUIDANCE":
            intervention_made = intervention["type"]
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )
            self._last_intervention[current_pursuit_id] = intervention
            self.adaptive_manager.record_intervention(
                user_id, current_pursuit_id, intervention["type"]
            )
            # v3.14: Record methodology selection for onboarding metrics
            try:
                from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
                metrics = OnboardingMetricsService(self.db)
                metrics.record_criterion_met_sync(user_id, "methodology_selected")
            except Exception as om_err:
                _onboarding_logger.warning(f"Methodology selection recording failed: {om_err}")

            # v3.15: Update Getting Started checklist
            try:
                from api.user_discovery import update_checklist_item_sync
                update_checklist_item_sync(user_id, "methodology_selected")
            except Exception as checklist_err:
                _onboarding_logger.warning(f"Discovery checklist update failed: {checklist_err}")

        # v2.6: Handle stakeholder engagement prompts
        elif intervention and intervention.get("type") == "STAKEHOLDER_ENGAGEMENT_PROMPT":
            intervention_made = intervention["type"]
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )
            # Don't track for response detection - this is advisory only

        elif intervention:
            intervention_made = intervention["type"]
            self.moment_detector.record_intervention(
                current_pursuit_id,
                intervention["type"],
                intervention.get("suggestion", "")
            )
            # Track intervention for response detection
            self._last_intervention[current_pursuit_id] = intervention
            self.adaptive_manager.record_intervention(
                user_id, current_pursuit_id, intervention["type"]
            )

        # STEP 6: Store conversation turns
        self._save_conversation_turn(
            pursuit_id=current_pursuit_id,
            role="user",
            content=message,
            metadata={
                "elements_extracted": extracted.get("extracted_count", 0),
            }
        )

        self._save_conversation_turn(
            pursuit_id=current_pursuit_id,
            role="assistant",
            content=response,
            metadata={
                "intervention_made": intervention_made,
                "artifacts_generated": artifacts_generated
            }
        )

        return {
            "response": response,
            "pursuit_id": current_pursuit_id,
            "pursuit_title": pursuit_context.get("title"),
            "artifacts_generated": artifacts_generated,
            "artifact_content": artifact_content,
            "intervention_made": intervention_made,
            "retrospective_mode": False,
            "retrospective_progress": 0
        }

    # =========================================================================
    # v2.7: RETROSPECTIVE MODE HANDLING
    # =========================================================================

    def _handle_retrospective_message(self, message: str, pursuit_id: str,
                                       user_id: str) -> Dict:
        """
        Handle message while in retrospective mode.

        Args:
            message: User's message
            pursuit_id: Pursuit ID
            user_id: User ID

        Returns:
            Response dict with retrospective mode flags
        """
        retro_id = self._active_retrospectives.get(pursuit_id)
        if not retro_id:
            # Shouldn't happen, but handle gracefully
            return {
                "response": "It seems we lost track of the retrospective. Let me help you restart.",
                "pursuit_id": pursuit_id,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        # Check for cancel/pause commands
        if self._is_retrospective_cancel(message):
            self.retrospective_orchestrator.cancel_retrospective(retro_id)
            del self._active_retrospectives[pursuit_id]
            pursuit = self.db.get_pursuit(pursuit_id)
            return {
                "response": "No problem - I've paused the retrospective. Your pursuit is back to active status. We can conduct the retrospective whenever you're ready.",
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit.get("title") if pursuit else None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": "RETROSPECTIVE_CANCELLED",
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        # Process response and get next prompt
        try:
            result = self.retrospective_orchestrator.process_response(retro_id, message)
        except Exception as e:
            print(f"[Engine] Error in process_response: {e}")
            import traceback
            traceback.print_exc()
            # Return error response but keep in retrospective mode
            return {
                "response": "I encountered an issue processing your response. Let's try again - please share your thoughts.",
                "pursuit_id": pursuit_id,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": True,
                "retrospective_progress": 0
            }

        # v3.7.4: Check for error response from orchestrator
        if result.get("error"):
            print(f"[Engine] Retrospective orchestrator error: {result.get('error')}")
            # Try to recover by clearing stale retrospective state
            if pursuit_id in self._active_retrospectives:
                del self._active_retrospectives[pursuit_id]
            return {
                "response": f"There was an issue with the retrospective: {result.get('error')}. Let me know if you'd like to try again.",
                "pursuit_id": pursuit_id,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        # Save conversation turns
        self._save_conversation_turn(
            pursuit_id=pursuit_id, role="user", content=message,
            metadata={"retrospective_id": retro_id}
        )

        # v2.7.1 FIX: Check for "is_complete" (from orchestrator) not "completed"
        if result.get("is_complete") or result.get("completed"):
            # Retrospective complete!
            del self._active_retrospectives[pursuit_id]

            # v3.7.4: Early exit already completed everything in _complete_partial_retrospective
            # Only call complete_retrospective for normal (non-early-exit) completion
            if result.get("early_exit"):
                # Already completed by orchestrator
                patterns_count = result.get("patterns_extracted", 0)
                completion_message = result.get("completion_message", "")
            else:
                # Normal completion - finalize retrospective
                completion_result = self.retrospective_orchestrator.complete_retrospective(retro_id)
                patterns_count = completion_result.get("patterns_extracted", 0)
                completion_message = completion_result.get("completion_message", "")

            # Try to generate report and notify (non-critical, wrap in try/except)
            report_id = None
            try:
                report = self.report_generator.generate_terminal_report(pursuit_id, retro_id)
                report_id = report.get("report_id")
                self.stakeholder_notifier.notify_stakeholders(pursuit_id, retro_id, report_id)
                self.portfolio_manager.update_portfolio_on_terminal(pursuit_id)
            except Exception as e:
                print(f"[Engine] Non-critical error in retrospective finalization: {e}")

            pursuit = self.db.get_pursuit(pursuit_id)
            pursuit_title = pursuit.get('title', 'your pursuit') if pursuit else 'your pursuit'

            response = (
                f"Thank you for completing the retrospective for **{pursuit_title}**.\n\n"
                f"I've captured {patterns_count} learning pattern(s) that will inform your future pursuits.\n\n"
                f"This pursuit has been archived. Is there anything else you'd like to explore, or would you like to start a new pursuit?"
            )

            self._save_conversation_turn(
                pursuit_id=pursuit_id, role="assistant", content=response,
                metadata={"retrospective_completed": True, "report_id": report_id}
            )

            return {
                "response": response,
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit_title,
                "artifacts_generated": [report_id] if report_id else [],
                "artifact_content": None,
                "intervention_made": "RETROSPECTIVE_COMPLETED",
                "retrospective_mode": False,
                "retrospective_progress": 100
            }

        # Continue retrospective
        next_prompt = result.get("next_prompt")
        if not next_prompt:
            next_prompt = "Please continue sharing your thoughts about this pursuit."
        progress = int(result.get("progress", 0) * 100) if isinstance(result.get("progress"), float) else result.get("progress", 0)

        self._save_conversation_turn(
            pursuit_id=pursuit_id, role="assistant", content=next_prompt,
            metadata={"retrospective_id": retro_id, "progress": progress}
        )

        return {
            "response": next_prompt,
            "pursuit_id": pursuit_id,
            "pursuit_title": None,
            "artifacts_generated": [],
            "artifact_content": None,
            "intervention_made": None,
            "retrospective_mode": True,
            "retrospective_progress": progress
        }

    def _initiate_retrospective(self, pursuit_id: str, terminal_state: str,
                                 user_id: str) -> Dict:
        """
        Start a retrospective for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            terminal_state: Terminal state being transitioned to
            user_id: User ID

        Returns:
            Response dict with retrospective mode activated
        """
        # Clear pending confirmation (v3.2 FIX: DB-backed)
        self._clear_pending_terminal_confirmation(pursuit_id)

        # Initialize retrospective
        retro = self.retrospective_orchestrator.initialize_retrospective(
            pursuit_id, terminal_state
        )

        if not retro or retro.get("error"):
            return {
                "response": "I wasn't able to start the retrospective. Let me know if you'd like to try again.",
                "pursuit_id": pursuit_id,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        retro_id = retro.get("retrospective_id")
        self._active_retrospectives[pursuit_id] = retro_id

        # Get first prompt
        first_prompt = self.retrospective_orchestrator.get_first_prompt(retro_id)

        pursuit = self.db.get_pursuit(pursuit_id)

        self._save_conversation_turn(
            pursuit_id=pursuit_id, role="assistant", content=first_prompt,
            metadata={"retrospective_started": True, "retrospective_id": retro_id}
        )

        return {
            "response": first_prompt,
            "pursuit_id": pursuit_id,
            "pursuit_title": pursuit.get("title") if pursuit else None,
            "artifacts_generated": [],
            "artifact_content": None,
            "intervention_made": "RETROSPECTIVE_STARTED",
            "retrospective_mode": True,
            "retrospective_progress": 10
        }

    def _is_retrospective_cancel(self, message: str) -> bool:
        """Check if user wants to cancel/pause retrospective."""
        cancel_phrases = [
            "cancel", "stop", "pause", "later", "not now",
            "skip", "exit", "quit", "never mind", "nevermind"
        ]
        message_lower = message.lower().strip()
        return any(phrase in message_lower for phrase in cancel_phrases)

    def is_in_retrospective_mode(self, pursuit_id: str) -> bool:
        """Check if pursuit is currently in retrospective mode."""
        # Check in-memory cache first
        if pursuit_id in self._active_retrospectives:
            return True
        # v3.7.4: Also check database for active retrospectives (survives server restart)
        return self._get_active_retrospective_from_db(pursuit_id) is not None

    def _get_active_retrospective_from_db(self, pursuit_id: str) -> dict:
        """
        Check database for active retrospective for a pursuit.
        v3.7.4: Ensures retrospective state survives server restarts.
        """
        if not pursuit_id:
            return None
        retro = self.db.db.retrospectives.find_one({
            "pursuit_id": pursuit_id,
            "completion_status": {"$in": ["IN_PROGRESS", "PAUSED"]}
        })
        if retro:
            # Restore to in-memory cache
            self._active_retrospectives[pursuit_id] = retro.get("retrospective_id")
        return retro

    def get_retrospective_progress(self, pursuit_id: str) -> int:
        """Get retrospective progress percentage for a pursuit."""
        retro_id = self._active_retrospectives.get(pursuit_id)
        if not retro_id:
            return 0
        retro = self.db.db.retrospectives.find_one({"retrospective_id": retro_id})
        if not retro:
            return 0
        return retro.get("progress", 0)

    def get_user_pursuits(self, user_id: str = None) -> List[Dict]:
        """Get all pursuits for a user."""
        if user_id is None:
            user_id = self._current_user_id
        return self.db.get_user_pursuits(user_id)

    def get_pursuit_artifacts(self, pursuit_id: str) -> List[Dict]:
        """Get all artifacts for a pursuit."""
        return self.db.get_pursuit_artifacts(pursuit_id)

    def _get_recent_history(self, pursuit_id: str, limit: int = 5) -> List[Dict]:
        """Get last N conversation turns."""
        return self.db.get_conversation_history(pursuit_id, limit)

    def _get_pursuit_context(self, pursuit_id: str) -> Dict:
        """Get current pursuit state including completeness."""
        pursuit = self.db.get_pursuit(pursuit_id)
        completeness = self.element_tracker.get_completeness(pursuit_id)

        return {
            "pursuit_id": pursuit_id,
            "title": pursuit.get("title", "Unknown") if pursuit else "Unknown",
            "status": pursuit.get("status", "active") if pursuit else "active",
            "completeness": completeness
        }

    def _user_accepted_formalization(self, message: str) -> bool:
        """
        Check if user is accepting/requesting the pending artifact.

        v2.7 FIX: Enhanced to recognize:
        1. Simple affirmatives: "yes", "sure", "ok"
        2. Explicit requests: "go ahead and produce", "please generate"
        3. Implicit requests: "the vision statement wasn't produced", "where is the survey"
        4. Follow-up complaints: "I see your acknowledgement but..."
        """
        import re
        message_lower = message.lower().strip()

        # 1. Simple affirmative words
        affirmative_words = [
            "yes", "sure", "ok", "okay", "please", "yeah", "yep",
            "go ahead", "sounds good", "do it", "let's do it",
            "that would be great", "that'd be great", "absolutely",
            "definitely", "perfect", "great", "proceed", "continue"
        ]

        for word in affirmative_words:
            if message_lower.startswith(word) or f" {word}" in f" {message_lower}":
                return True

        # 2. Explicit generation requests
        # v3.7.2 FIX: Added "craft" to all patterns - user said "craft the vision statement"
        explicit_patterns = [
            r"\b(generate|create|produce|draft|write|make|craft|pull together)\b.{0,40}\b(vision|hypothesis|fears?|risks?|survey|questionnaire|questions?)\b",
            r"\b(vision|hypothesis|fears?|risks?|survey|questionnaire)\b.{0,40}\b(generate|create|produce|draft|craft|now|please)\b",
            r"\bgo ahead\b.{0,30}\b(and|to)?\s*(produce|generate|create|draft|make|craft)\b",
        ]

        for pattern in explicit_patterns:
            if re.search(pattern, message_lower):
                return True

        # 3. Implicit requests - user asking why artifact wasn't produced or where it is
        implicit_patterns = [
            r"\b(wasn't|wasn't|was not|weren't|were not|isn't|is not)\s*(produced|generated|created|shown|displayed|provided)\b",
            r"\bwhere\s*(is|are)\s*(the|my)?\s*(vision|hypothesis|survey|questionnaire|questions|statement)\b",
            r"\bi\s*(don't|do not)\s*see\s*(the|a|my)?\s*(vision|hypothesis|survey|questionnaire|questions|statement)\b",
            r"\b(still|yet)\s*(waiting|looking)\s*(for)?\s*(the|a|my)?\s*(vision|hypothesis|survey|questionnaire)\b",
            r"\byou\s*(said|mentioned|offered|promised).{0,30}(but|however).{0,30}(didn't|did not|haven't|have not)\b",
            r"\bi\s*see\s*(your)?\s*acknowledgement\s*but\b",
            r"\bthe\s*(vision|hypothesis|survey|questionnaire|questions)\s*(statement|list|document)?\s*(wasn't|was not|isn't|is not|didn't|did not)\b",
        ]

        for pattern in implicit_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] Implicit artifact request detected: '{message[:50]}...'")
                return True

        return False

    def _user_declined_formalization(self, message: str) -> bool:
        """
        v2.5: Check if user explicitly declined artifact generation.

        Only returns True if user said no/not now/later etc.
        Returns False if user just talked about something else.
        """
        import re

        # Patterns that indicate explicit decline (with word boundaries)
        decline_patterns = [
            r"^no\b",           # "no" at start
            r"^not now\b",
            r"^not yet\b",
            r"^later\b",
            r"^maybe later\b",
            r"\bdon't\b",
            r"^skip\b",
            r"^pass\b",
            r"^not ready\b",
            r"^hold off\b",
            r"^wait\b",         # "wait" at start only
            r"^let's wait\b"
        ]
        message_lower = message.lower().strip()

        # Check for explicit decline patterns
        for pattern in decline_patterns:
            if re.search(pattern, message_lower):
                return True

        return False

    def _detect_pursuit_recall(self, message: str, user_id: str) -> Optional[Dict]:
        """
        v2.7 FIX: Detect if user is trying to recall/load an existing pursuit by name.

        Handles natural language commands like:
        - "Recall the Inner Glow Purse pursuit"
        - "Load my Smart Widget project"
        - "Switch to the Coffee App pursuit"
        - "Open the Mobile Banking idea"
        - "Go back to Inner Glow Purse"

        Returns a response dict if recall detected and processed, None otherwise.
        """
        import re
        message_lower = message.lower()

        # Patterns for recall/load commands
        recall_patterns = [
            r"\b(recall|load|open|switch to|go back to|return to|continue with|resume)\b\s+(?:the\s+)?(?:my\s+)?(.+?)(?:\s+pursuit|\s+project|\s+idea|\s*$)",
            r"\b(bring up|pull up|show me|let'?s work on|work on)\b\s+(?:the\s+)?(?:my\s+)?(.+?)(?:\s+pursuit|\s+project|\s+idea|\s*$)",
        ]

        pursuit_name = None
        for pattern in recall_patterns:
            match = re.search(pattern, message_lower)
            if match:
                pursuit_name = match.group(2).strip()
                # Clean up common trailing words
                pursuit_name = re.sub(r'\s+(pursuit|project|idea|again)$', '', pursuit_name)
                break

        if not pursuit_name:
            return None

        print(f"[Engine] PURSUIT RECALL detected, searching for: '{pursuit_name}'")

        # Search for matching pursuit
        pursuits = self.db.get_user_pursuits(user_id)

        # Try exact match first (case-insensitive)
        matched_pursuit = None
        for p in pursuits:
            title_lower = p.get("title", "").lower()
            if pursuit_name in title_lower or title_lower in pursuit_name:
                matched_pursuit = p
                break

        # If no exact match, try fuzzy matching
        if not matched_pursuit:
            # Check if any word in pursuit name matches
            pursuit_words = set(pursuit_name.split())
            best_match = None
            best_score = 0
            for p in pursuits:
                title_words = set(p.get("title", "").lower().split())
                overlap = len(pursuit_words & title_words)
                if overlap > best_score:
                    best_score = overlap
                    best_match = p

            if best_score > 0:
                matched_pursuit = best_match

        if matched_pursuit:
            pursuit_id = matched_pursuit["pursuit_id"]
            pursuit_title = matched_pursuit.get("title", "your pursuit")

            print(f"[Engine] Found matching pursuit: '{pursuit_title}' ({pursuit_id})")

            # Get recent context
            history = self.db.get_conversation_history(pursuit_id, limit=3)
            completeness = self.element_tracker.get_completeness(pursuit_id)

            # Build a helpful summary response
            vision_pct = int(completeness.get("vision", 0) * 100)
            fears_pct = int(completeness.get("fears", 0) * 100)
            hypothesis_pct = int(completeness.get("hypothesis", 0) * 100)

            # v4.0: Use re-engagement bridge instead of generic session-close
            from coaching.methodology_archetypes import CoachingLanguageAdapter
            archetype = matched_pursuit.get("archetype", "lean_startup")
            coaching_style = CoachingLanguageAdapter(archetype)
            re_engagement = coaching_style.get_re_engagement_message()

            response = f"**{pursuit_title}**\n\n{re_engagement}\n\n"
            response += f"Here's where we are:\n"
            response += f"- Your story: {vision_pct}% developed\n"
            response += f"- Risks identified: {fears_pct}% captured\n"
            response += f"- Assumptions to test: {hypothesis_pct}% formed\n\n"
            response += "Where would you like to pick up?"

            # Save conversation turn
            self._save_conversation_turn(
                pursuit_id=pursuit_id,
                role="user",
                content=message,
                metadata={"recall_command": True}
            )
            self._save_conversation_turn(
                pursuit_id=pursuit_id,
                role="assistant",
                content=response,
                metadata={"pursuit_recalled": True}
            )

            return {
                "response": response,
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit_title,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": "PURSUIT_RECALLED",
                "retrospective_mode": False,
                "retrospective_progress": 0
            }
        else:
            # No matching pursuit found
            print(f"[Engine] No matching pursuit found for: '{pursuit_name}'")

            # List available pursuits
            if pursuits:
                pursuit_list = "\n".join([f"- {p.get('title', 'Untitled')}" for p in pursuits[:5]])
                response = f"I couldn't find a pursuit matching '{pursuit_name}'. Here are your recent pursuits:\n\n{pursuit_list}\n\nWhich one would you like to work on?"
            else:
                response = f"I couldn't find a pursuit matching '{pursuit_name}', and you don't have any saved pursuits yet. Would you like to start a new one?"

            return {
                "response": response,
                "pursuit_id": None,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

    def _detect_explicit_artifact_request(self, message: str) -> Optional[str]:
        """
        v2.7 FIX: Detect if user is explicitly requesting an artifact to be generated.

        Returns the artifact type if explicit request detected, None otherwise.

        Explicit requests bypass the confirmation step since the user is already
        directly asking for the artifact.

        v2.7.1 FIX: Enhanced patterns to catch:
        - "go ahead and produce a vision statement"
        - "produce a survey/questionnaire"
        - "pull everything together into a vision"
        - Implicit requests when artifact wasn't produced

        v3.7.1 FIX: Added patterns for:
        - Generic artifact requests ("produce that as an artifact", "can you produce that")
        - Data collection sheet / experiment documentation requests
        - Tracking sheets, experiment forms, recording sheets
        """
        import re
        message_lower = message.lower()

        # Patterns for explicit vision statement requests
        # v3.7.2 FIX: Added "craft" to all patterns
        vision_patterns = [
            r"\b(generate|create|produce|draft|write|make|craft|formalize)\b.{0,40}\bvision\s*(statement)?\b",
            r"\bvision\s*(statement)?\b.{0,40}\b(now|please|for me)\b",
            r"\b(can you|could you|would you|please)\b.{0,40}\b(vision|vision statement)\b",
            r"\b(i('d| would) like|i want|let's get|let's have)\b.{0,40}\bvision\b",
            r"\bcapture.{0,30}(vision|essence|idea)\b.{0,30}\b(statement)?\b",
            r"\bgo ahead\b.{0,40}\b(produce|generate|create|draft|make|craft).{0,40}\bvision\b",
            r"\bpull\s*(everything|it all|this all)\s*(together|into)\b.{0,40}\bvision\b",
            r"\bvision\s*(statement)?\s*(wasn't|was not|isn't|is not)\s*(produced|generated|created|shown)\b",
        ]

        # Patterns for explicit fears/risk document requests
        # v3.7.2 FIX: Added "craft" to all patterns
        fears_patterns = [
            r"\b(generate|create|produce|draft|write|make|craft|formalize)\b.{0,40}\b(fears?|risks?|concerns?)\b",
            r"\b(fears?|risks?|concerns?)\s*(document|statement)?\b.{0,40}\b(now|please|for me)\b",
            r"\b(can you|could you|would you|please)\b.{0,40}\b(fears?|risks?)\b",
            r"\bgo ahead\b.{0,40}\b(produce|generate|create|craft).{0,40}\b(fears?|risks?)\b",
        ]

        # Patterns for explicit hypothesis requests (including survey/questionnaire)
        # v3.7.2 FIX: Added "craft" to all patterns
        hypothesis_patterns = [
            r"\b(generate|create|produce|draft|write|make|craft|formalize)\b.{0,40}\bhypothesis\b",
            r"\bhypothesis\b.{0,40}\b(now|please|for me)\b",
            r"\b(can you|could you|would you|please)\b.{0,40}\bhypothesis\b",
            r"\bgo ahead\b.{0,40}\b(produce|generate|create|craft).{0,40}\bhypothesis\b",
            # Survey/questionnaire patterns - these map to hypothesis artifact
            r"\b(generate|create|produce|draft|write|make|craft)\b.{0,40}\b(survey|questionnaire|questions?\s*list)\b",
            r"\b(survey|questionnaire|questions?\s*list)\b.{0,40}\b(now|please|for me)\b",
            r"\b(can you|could you|would you|please)\b.{0,40}\b(survey|questionnaire|questions)\b",
            r"\bgo ahead\b.{0,40}\b(produce|generate|create|craft).{0,40}\b(survey|questionnaire|questions)\b",
            r"\b(survey|questionnaire|questions?\s*list)\s*(wasn't|was not|isn't|is not)\s*(produced|generated|created|shown)\b",
        ]

        # v3.7.1: Patterns for experiment/data collection artifacts
        # v3.7.2 FIX: Added "craft" to all patterns
        experiment_patterns = [
            # Data collection sheet patterns
            r"\b(generate|create|produce|draft|write|make|craft)\b.{0,40}\b(data\s*collection|tracking|recording|experiment)\s*(sheet|form|template|document)\b",
            r"\b(data\s*collection|tracking|recording|experiment)\s*(sheet|form|template|document)\b.{0,40}\b(now|please|for me)\b",
            r"\b(can you|could you|would you|please)\b.{0,40}\b(data\s*collection|tracking|recording|experiment)\s*(sheet|form|template)?\b",
            r"\bgo ahead\b.{0,40}\b(produce|generate|create|craft).{0,40}\b(data\s*collection|tracking|recording|experiment)\b",
            # Results tracking patterns
            r"\b(generate|create|produce|craft)\b.{0,40}\b(results?|outcomes?)\s*(tracker|sheet|form|template)\b",
            r"\b(track|record|log)\b.{0,40}\b(experiment|test|validation)\s*(results?|outcomes?|data)\b.{0,40}\b(sheet|form|template)\b",
        ]

        # v3.7.1: Generic artifact request patterns (context-aware)
        # These catch "produce that", "can you produce that as an artifact", etc.
        generic_artifact_patterns = [
            r"\b(can you|could you|would you|please)\b.{0,10}\b(produce|generate|create)\b.{0,10}\b(that|this|it)\b.{0,20}\b(as\s*(an)?\s*artifact)?\b",
            r"\b(produce|generate|create)\b.{0,10}\b(that|this|it)\b.{0,20}\b(as\s*(an)?\s*artifact)\b",
            r"\b(that|this)\b.{0,10}\b(as\s*(an)?\s*artifact)\b",
            r"\bproduce\s*(that|this|it)\b",
            r"\b(can you|could you)\b.{0,10}\bproduce\b.{0,10}\b(that|this|it)\b",
            # Frustration patterns - artifact wasn't produced
            r"\b(wasn't|was not|isn't|is not|didn't|did not)\b.{0,20}\b(produced|generated|created|shown|appear)\b",
            r"\bwhere\s*(is|'s)\s*(the|my)\s*artifact\b",
            r"\bi\s*(don't|do not)\s*see\s*(the|any|an)\s*artifact\b",
        ]

        # Check vision patterns
        for pattern in vision_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] EXPLICIT vision request detected: '{message[:50]}...'")
                return "vision"

        # Check fears patterns
        for pattern in fears_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] EXPLICIT fears request detected: '{message[:50]}...'")
                return "fears"

        # Check hypothesis patterns
        for pattern in hypothesis_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] EXPLICIT hypothesis request detected: '{message[:50]}...'")
                return "hypothesis"

        # v3.7.1: Check experiment/data collection patterns (maps to experiment artifact type)
        for pattern in experiment_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] EXPLICIT experiment artifact request detected: '{message[:50]}...'")
                return "experiment"

        # v3.7.1: Check generic artifact patterns (requires context - defaults to hypothesis for experiments)
        for pattern in generic_artifact_patterns:
            if re.search(pattern, message_lower):
                print(f"[Engine] GENERIC artifact request detected: '{message[:50]}...'")
                # For generic requests, we need to infer from context
                # Default to "experiment" for data collection, or check pending context
                return "experiment"

        return None

    def _save_conversation_turn(self, pursuit_id: str, role: str,
                                 content: str, metadata: Dict = None) -> None:
        """Save turn to conversation_history collection."""
        self.db.save_conversation_turn(pursuit_id, role, content, metadata)

    def _general_conversation_response(self, message: str) -> str:
        """Handle general chat when no pursuit active."""
        # Check if it might be a greeting or general question
        message_lower = message.lower()

        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "Hello! I'm your innovation coach. What idea or opportunity would you like to explore today?"

        if any(word in message_lower for word in ["help", "how do", "what can"]):
            return "I help innovators develop their ideas through natural conversation. Just tell me about a problem you're trying to solve or an opportunity you've spotted, and we'll explore it together."

        if any(word in message_lower for word in ["thanks", "thank you"]):
            return "You're welcome! Is there an innovation idea you'd like to explore?"

        # Default response
        return "Tell me about an innovation idea you're working on, or a problem you'd like to solve. We can explore it together."

    def _select_unused_question(self, pursuit_id: str, questions: list) -> str:
        """
        Select a question that hasn't been recently used.

        v2.3: Question rotation prevents repetitive coaching.

        Args:
            pursuit_id: Pursuit ID
            questions: List of candidate questions

        Returns:
            Selected question string
        """
        if not questions:
            return None

        # Get recently used questions
        used_questions = self.db.get_used_questions(pursuit_id, limit=20)

        # Find first unused question
        for question in questions:
            if question not in used_questions:
                # Record usage
                self.db.record_question_usage(pursuit_id, question)
                return question

        # All questions used, return first one and record it
        selected = questions[0]
        self.db.record_question_usage(pursuit_id, selected)
        return selected

    # =========================================================================
    # v2.6: STAKEHOLDER OPERATIONS
    # =========================================================================

    def get_support_landscape(self, pursuit_id: str) -> dict:
        """
        v2.6: Get stakeholder support landscape analysis.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Support landscape analysis dict
        """
        return self.support_analyzer.analyze_pursuit_support(pursuit_id)

    def get_fear_validation(self, pursuit_id: str) -> dict:
        """
        v2.6: Get fear cross-validation with stakeholder concerns.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Fear validation results
        """
        return self.fear_extractor.cross_validate_with_stakeholders(pursuit_id)

    def get_pitch_preparation(self, pursuit_id: str,
                              target_stakeholder: str = None) -> dict:
        """
        v2.6: Get pitch preparation with stakeholder intelligence.

        Args:
            pursuit_id: Pursuit ID
            target_stakeholder: Optional target stakeholder name

        Returns:
            Pitch preparation package
        """
        return self.pitch_orchestrator.generate_pitch_preparation(
            pursuit_id, target_stakeholder
        )

    def record_pursuit_outcome(self, pursuit_id: str, outcome: str) -> None:
        """
        v2.6: Record pursuit outcome and learn patterns.

        Args:
            pursuit_id: Pursuit ID
            outcome: success/fail/pivot
        """
        # Learn from stakeholder engagement patterns
        self.pattern_engine.learn_from_stakeholder_outcome(pursuit_id, outcome)

        # Extract proto-pattern from the pursuit itself
        self.pattern_engine.extract_proto_pattern(pursuit_id)

    # =========================================================================
    # v2.7: TERMINAL INTELLIGENCE OPERATIONS
    # =========================================================================

    def get_portfolio_summary(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        v2.7: Get portfolio summary with terminal state distribution.

        Args:
            user_id: User ID

        Returns:
            Portfolio summary dict
        """
        return self.portfolio_manager.get_portfolio_summary(user_id)

    def get_portfolio_timeline(self, user_id: str = DEMO_USER_ID,
                               days: int = 90) -> List[Dict]:
        """
        v2.7: Get portfolio activity timeline.

        Args:
            user_id: User ID
            days: Number of days to include

        Returns:
            List of timeline events
        """
        return self.portfolio_manager.get_portfolio_timeline(user_id, days)

    def get_learning_insights(self, user_id: str = DEMO_USER_ID) -> Dict:
        """
        v2.7: Get learning insights from pursuit history.

        Args:
            user_id: User ID

        Returns:
            Learning insights dict
        """
        return self.insights_generator.generate_insights(user_id)

    def get_proactive_guidance(self, pursuit_id: str) -> Dict:
        """
        v2.7: Get proactive guidance for active pursuit based on history.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Proactive guidance dict with warnings and suggestions
        """
        return self.insights_generator.get_proactive_guidance(pursuit_id)

    def get_terminal_pursuits(self, user_id: str = DEMO_USER_ID) -> List[Dict]:
        """
        v2.7: Get all terminal pursuits for a user.

        Args:
            user_id: User ID

        Returns:
            List of terminal pursuit dicts
        """
        return self.portfolio_manager.get_terminal_pursuits(user_id)

    def get_pursuit_retrospective(self, pursuit_id: str) -> Optional[Dict]:
        """
        v2.7: Get retrospective for a pursuit if it exists.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Retrospective dict or None
        """
        return self.db.db.retrospectives.find_one({"pursuit_id": pursuit_id})

    def get_pursuit_report(self, pursuit_id: str) -> Optional[Dict]:
        """
        v2.7: Get terminal report for a pursuit if it exists.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Report dict or None
        """
        reports = self.report_generator.get_reports_by_pursuit(pursuit_id)
        return reports[0] if reports else None

    def manually_trigger_retrospective(self, pursuit_id: str,
                                        terminal_state: str,
                                        user_id: str = DEMO_USER_ID) -> Dict:
        """
        v2.7: Manually trigger a retrospective for a pursuit.

        Used when user explicitly wants to conclude a pursuit.

        Args:
            pursuit_id: Pursuit ID
            terminal_state: Terminal state to transition to
            user_id: User ID

        Returns:
            Result dict with retrospective status
        """
        return self._initiate_retrospective(pursuit_id, terminal_state, user_id)

    # =========================================================================
    # v2.7: SURVEY DATA INGESTION
    # =========================================================================

    def process_survey_upload(self, file_path: str, filename: str,
                               pursuit_id: str, user_id: str = DEMO_USER_ID) -> Dict:
        """
        v2.7: Process uploaded survey file and integrate results.

        Args:
            file_path: Path to uploaded file
            filename: Original filename
            pursuit_id: Pursuit to associate data with
            user_id: User who uploaded

        Returns:
            Response dict suitable for chat display
        """
        from .survey_processor import SurveyProcessor

        if not pursuit_id:
            return {
                "response": "Please select a pursuit first before uploading survey data.",
                "pursuit_id": None,
                "pursuit_title": None,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

        processor = SurveyProcessor(self.llm, self.db)
        result = processor.process_file(file_path, pursuit_id, user_id)

        pursuit = self.db.get_pursuit(pursuit_id)
        pursuit_title = pursuit.get("title") if pursuit else None

        if result.get("success"):
            response = result.get("summary", "Survey data processed successfully.")

            # Save conversation turn
            self._save_conversation_turn(
                pursuit_id=pursuit_id,
                role="user",
                content=f"[Uploaded survey file: {filename}]",
                metadata={"file_upload": filename, "type": "survey"}
            )
            self._save_conversation_turn(
                pursuit_id=pursuit_id,
                role="assistant",
                content=response,
                metadata={
                    "survey_processed": True,
                    "response_count": result.get("response_count", 0),
                    "evidence_artifact_id": result.get("evidence_artifact_id")
                }
            )

            return {
                "response": response,
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit_title,
                "artifacts_generated": [result.get("evidence_artifact_id")] if result.get("evidence_artifact_id") else [],
                "artifact_content": None,
                "intervention_made": "SURVEY_PROCESSED",
                "retrospective_mode": False,
                "retrospective_progress": 0
            }
        else:
            error_msg = result.get("error", "Unknown error processing survey file.")
            return {
                "response": f"I couldn't process the survey file: {error_msg}",
                "pursuit_id": pursuit_id,
                "pursuit_title": pursuit_title,
                "artifacts_generated": [],
                "artifact_content": None,
                "intervention_made": None,
                "retrospective_mode": False,
                "retrospective_progress": 0
            }

    # =========================================================================
    # v3.0.1: TEMPORAL INTELLIGENCE MODULE (TIM) OPERATIONS
    # =========================================================================

    def _initialize_tim_for_pursuit(self, pursuit_id: str, title: str = None) -> None:
        """
        v3.0.1: Initialize TIM tracking for a new pursuit.

        Creates:
        - Time allocation with default phase distribution
        - PURSUIT_START event
        - PHASE_START event for VISION phase

        Args:
            pursuit_id: Pursuit ID
            title: Optional pursuit title for logging
        """
        from datetime import datetime, timedelta, timezone
        from config import TIM_CONFIG

        try:
            # Create default time allocation
            # Note: isoformat() on timezone-aware datetime already includes offset, don't add 'Z'
            start_date = datetime.now(timezone.utc).isoformat()
            default_duration = TIM_CONFIG.get("default_pursuit_duration_days", 180)
            target_date = (datetime.now(timezone.utc) + timedelta(days=default_duration)).isoformat()

            self.allocation_engine.create_allocation(
                pursuit_id=pursuit_id,
                start_date=start_date,
                target_completion=target_date
            )

            # Log pursuit start event
            self.event_logger.log_pursuit_start(
                pursuit_id=pursuit_id,
                title=title,
                user_id=DEMO_USER_ID
            )

            # Log initial VISION phase start
            self.event_logger.log_phase_start(
                pursuit_id=pursuit_id,
                phase="VISION",
                from_phase=None
            )

            print(f"[Engine] TIM initialized for pursuit: {pursuit_id}")

        except Exception as e:
            print(f"[Engine] TIM initialization warning: {e}")
            # Non-fatal - pursuit can work without TIM

    def get_velocity_summary(self, pursuit_id: str) -> Dict:
        """
        v3.0.1: Get velocity summary for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Velocity summary with current pace and projection
        """
        return self.velocity_tracker.get_velocity_summary(pursuit_id)

    def get_phase_summary(self, pursuit_id: str) -> Dict:
        """
        v3.0.1: Get phase summary for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Phase summary with all phase statuses
        """
        return self.phase_manager.get_phase_summary(pursuit_id)

    def get_timeline_events(self, pursuit_id: str, limit: int = 50) -> List[Dict]:
        """
        v3.0.1: Get timeline events for visualization.

        Args:
            pursuit_id: Pursuit ID
            limit: Maximum events to return

        Returns:
            List of temporal events
        """
        return self.event_logger.get_event_stream(pursuit_id, limit)

    def get_time_allocation(self, pursuit_id: str) -> Optional[Dict]:
        """
        v3.0.1: Get time allocation for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Time allocation document or None
        """
        return self.allocation_engine.get_allocation(pursuit_id)

    def override_phase_allocation(self, pursuit_id: str, new_config: Dict,
                                    reason: str = None) -> bool:
        """
        v3.0.1: Allow innovator to override phase allocations.

        Args:
            pursuit_id: Pursuit ID
            new_config: Dict with phase percentages
            reason: Optional reason for override

        Returns:
            True if override succeeded
        """
        return self.allocation_engine.override_allocation(
            pursuit_id, new_config, reason
        )

    def initiate_phase_transition(self, pursuit_id: str, to_phase: str,
                                    reason: str = None) -> Dict:
        """
        v3.0.1: Innovator-initiated phase transition.

        Args:
            pursuit_id: Pursuit ID
            to_phase: Target phase
            reason: Optional reason

        Returns:
            Transition record
        """
        return self.phase_manager.initiate_transition(
            pursuit_id, to_phase, reason
        )

    def get_projected_completion(self, pursuit_id: str) -> Dict:
        """
        v3.0.1: Get projected completion date based on velocity.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Projection with date and confidence interval
        """
        return self.velocity_tracker.project_completion(pursuit_id)

    # =========================================================================
    # v3.0.2: INTELLIGENCE LAYER METHODS
    # =========================================================================

    def get_health_score(self, pursuit_id: str) -> Dict:
        """
        v3.0.2: Get health score and zone for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with health_score, zone, and component breakdown
        """
        return self.health_monitor.calculate_health(pursuit_id)

    def get_health_trend(self, pursuit_id: str, window_days: int = 7) -> Dict:
        """
        v3.0.2: Get health trend analysis.

        Args:
            pursuit_id: Pursuit ID
            window_days: Days to analyze

        Returns:
            Dict with trend direction and change
        """
        return self.health_monitor.get_health_trend(pursuit_id, window_days)

    def get_coaching_context(self, pursuit_id: str) -> Dict:
        """
        v3.0.2: Get health-informed coaching context.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with zone-specific coaching guidelines
        """
        return self.health_monitor.get_coaching_context(pursuit_id)

    def get_predictions(self, pursuit_id: str) -> List[Dict]:
        """
        v3.0.2: Get predictions for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of predictions ordered by confidence
        """
        return self.predictive_guidance.generate_predictions(pursuit_id)

    def get_risk_detection(self, pursuit_id: str) -> Dict:
        """
        v3.0.2: Get risk detection results across all horizons.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with risks by horizon and overall level
        """
        return self.risk_detector.detect_risks(pursuit_id)

    def get_risk_summary(self, pursuit_id: str) -> str:
        """
        v3.0.2: Get formatted risk summary.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Human-readable risk summary
        """
        return self.risk_detector.get_risk_summary(pursuit_id)

    def detect_antipatterns(self, pursuit_id: str) -> List[Dict]:
        """
        v3.0.2: Detect temporal anti-patterns.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of detected anti-patterns
        """
        return self.temporal_patterns.detect_antipatterns(pursuit_id)

    def enrich_pattern_matches(self, pursuit_id: str,
                               base_matches: List[Dict]) -> List[Dict]:
        """
        v3.0.2: Enrich pattern matches with temporal relevance.

        Args:
            pursuit_id: Pursuit ID
            base_matches: Pattern matches from IML

        Returns:
            Enriched matches with temporal scores
        """
        return self.temporal_patterns.enrich_pattern_matches(
            pursuit_id, base_matches
        )

    def get_intelligence_summary(self, pursuit_id: str) -> Dict:
        """
        v3.0.2: Get comprehensive intelligence summary for UI.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict with health, predictions, and risks
        """
        health = self.get_health_score(pursuit_id)
        predictions = self.get_predictions(pursuit_id)
        risk_detection = self.get_risk_detection(pursuit_id)
        antipatterns = self.detect_antipatterns(pursuit_id)

        return {
            "pursuit_id": pursuit_id,
            "health": {
                "score": health.get("health_score", 50),
                "zone": health.get("zone", "HEALTHY"),
                "zone_info": health.get("zone_info", {}),
                "components": health.get("components", {}),
                "crisis_triggered": health.get("crisis_triggered", False)
            },
            "predictions": {
                "count": len(predictions),
                "top_prediction": predictions[0] if predictions else None,
                "all": predictions[:3]
            },
            "risks": {
                "overall_level": risk_detection.get("overall_risk_level", "LOW"),
                "count": risk_detection.get("risk_count", 0),
                "top_risks": risk_detection.get("top_risks", []),
                "recommendations": risk_detection.get("recommendations", [])
            },
            "antipatterns": {
                "detected": len(antipatterns),
                "items": antipatterns
            }
        }
