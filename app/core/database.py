"""
InDE MVP v3.1 - Database Layer "Platform Foundation & Innovator Maturity"
MongoDB operations with mongomock fallback for demo mode.

v3.1 Enhancements:
- 6 new collections for platform features (sessions, maturity_events, crisis_sessions,
  gii_profiles, domain_events, coaching_sessions)
- User scoping for multi-tenant support
- JWT session management
- Legacy data migration for v3.0.3 compatibility

41 Core Collections (v3.1: added 6 platform collections):
- users
- pursuits (enhanced with terminal_info, state, activity_feed, rve_status)
- scaffolding_states (enhanced with important_elements)
- artifacts (with versioning)
- conversation_history
- intervention_history
- patterns (v2.5: enhanced for IML pattern matching)
- system_config
- user_engagement_metrics (v2.5: for adaptive cooldowns)
- pattern_effectiveness (v2.5: for tracking pattern outcomes)
- stakeholder_feedback (v2.6: for organizational context)
- retrospectives (v2.7: terminal state retrospectives)
- learning_patterns (v2.7: patterns extracted from retrospectives)
- fear_resolutions (v2.7: fear outcome tracking)
- retrospective_conversations (v2.7: retrospective dialogue history)
- terminal_reports (v2.7: SILR report storage)
- outcome_artifacts (v2.7: terminal outcome artifacts)
- living_snapshot_reports (v2.8: progress reports for active pursuits)
- portfolio_analytics_reports (v2.8: cross-pursuit analytics)
- report_templates (v2.8: custom and system report templates)
- report_distributions (v2.9: track report distribution and engagement)
- shared_pursuits (v2.9: shareable pursuit links and analytics)
- stakeholder_responses (v2.9: feedback from shared pursuit views)
- artifact_comments (v2.9: collaboration comments on artifacts)
- risk_definitions (v2.9: RVE Lite fear-to-risk conversions)
- evidence_packages (v2.9: RVE Lite validation evidence, v3.0.2: extended for full RVE)
- time_allocations (v3.0.1: TIM phase-level time distribution)
- temporal_events (v3.0.1: TIM event stream with ISO 8601 timestamps)
- velocity_metrics (v3.0.1: TIM progress velocity tracking)
- phase_transitions (v3.0.1: TIM phase change history)
- health_scores (v3.0.2: NEW - Pursuit health score history)
- validation_experiments (v3.0.2: NEW - Full RVE experiment tracking)
- risk_detections (v3.0.2: NEW - Temporal risk detection results)
- portfolio_analytics (v3.0.3: NEW - Portfolio-level analytics snapshots)
- ikf_contributions (v3.0.3: NEW - IKF-ready contribution packages)

v3.0.3 Enhancements - Analytics & Synthesis:
- Portfolio Intelligence Engine: Cross-pursuit analytics with weighted health
- Cross-Pursuit Comparator: Benchmarking with percentile rankings
- Innovation Effectiveness Scorecard: 7 organizational metrics
- IKF Contribution Preparation: 4-stage generalization with human review
- Extended pursuits with portfolio_priority, ikf_contribution_status fields

v3.0.2 Enhancements - Intelligence Layer:
- Pursuit Health Monitor: Real-time health scoring (0-100) with 5 health zones
- Full RVE: Upgrade from Lite with experiment wizard, three-zone assessment, override capture
- Temporal Risk Detection: Short/medium/long-term risk identification
- Extended evidence_packages with verdict, recommendation, confidence fields
- Extended pursuits.rve_status with zone counts and experiment tracking

v3.0.1 Features (maintained):
- Time Allocation Engine: Phase-based timeline distribution
- Velocity Tracker: Progress pace monitoring (elements/week)
- Temporal Event Logger: IKF-compatible event stream
- Phase Manager: Automatic phase transition detection
- All timestamps use ISO 8601 format for IKF compatibility

v2.9 Features (maintained):
- Report Distribution: Email, share links, batch distribution tracking
- Pursuit Sharing: Public/unlisted/private pursuit views with analytics
- Stakeholder Response Capture: Feedback widgets and conversation threading
- Collaboration: Artifact comments, @mentions, activity feeds
- RVE Lite: Fear-to-risk conversion, evidence documentation, decision support

v2.8 Features (maintained):
- Living Snapshot Reports for active pursuit progress
- Portfolio Analytics Reports for cross-pursuit insights
- Custom and system report templates
- Unified report operations for review workflow

v2.7 Features (maintained):
- Terminal state management with 6 terminal states
- Retrospective conversation storage
- Learning patterns extraction and storage
- Fear resolution tracking for pattern learning
- Terminal reports for organizational closure

v2.6 Features (maintained):
- Stakeholder feedback collection for capturing organizational context
- Pursuit stakeholder_summary field for support landscape tracking
- Support distribution and consensus readiness metrics

v2.5 Features (maintained):
- Enhanced patterns collection with semantic matching support
- User engagement metrics for adaptive intervention cooldowns
- Pattern effectiveness tracking for learning
- Important elements tracking in scaffolding_states
- Cross-pursuit insight support
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from core.config import (
    MONGODB_URI, DATABASE_NAME, USE_MONGOMOCK, COLLECTIONS,
    CRITICAL_ELEMENTS, DEMO_USER_ID, DEMO_USER_NAME,
    LEGACY_USER_EMAIL, LEGACY_USER_NAME
)

# Database connection - try MongoDB first, fall back to in-memory if unavailable
_client = None
_use_inmemory = USE_MONGOMOCK  # Start with config setting

if not USE_MONGOMOCK:
    # Try to connect to MongoDB
    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        # Test connection
        _client.server_info()
        print(f"[Database] Connected to MongoDB at {MONGODB_URI}")
        print(f"[Database] Using database: {DATABASE_NAME}")
    except ImportError:
        print("[Database] pymongo not installed, using in-memory database")
        _client = None
        _use_inmemory = True
    except Exception as e:
        print(f"[Database] MongoDB connection failed: {e}")
        print("[Database] Falling back to in-memory database")
        _client = None
        _use_inmemory = True
else:
    print("[Database] Demo mode enabled, using in-memory database")


class Database:
    """
    Database operations for InDE v3.1 "Platform Foundation & Innovator Maturity".
    Provides CRUD operations for all 41 collections including platform features.

    v3.1 adds:
    - User authentication with JWT sessions
    - Innovator maturity tracking
    - Crisis mode management
    - GII (Global Innovator Identifier) profiles
    - Domain event persistence
    - Legacy data migration
    """

    def __init__(self):
        self.using_mongodb = _client is not None and not _use_inmemory

        if self.using_mongodb:
            self.db = _client[DATABASE_NAME]
            self._ensure_collections()
            self._ensure_tim_indexes()  # v3.0.1: TIM indexes
            self._ensure_intelligence_indexes()  # v3.0.2: Intelligence layer indexes
            self._ensure_analytics_indexes()  # v3.0.3: Analytics & IKF indexes
            self._ensure_platform_indexes()  # v3.1: Platform foundation indexes
            self._ensure_ems_indexes()  # v3.7.1: EMS observation engine indexes
            self._ensure_demo_user()
            self._migrate_legacy_data()  # v3.1: Migrate v3.0.3 data
            print(f"[Database] Initialized with MongoDB ({len(COLLECTIONS)} collections)")
        else:
            # Pure in-memory fallback
            self.db = InMemoryDB()
            self._ensure_demo_user()
            print("[Database] Initialized with in-memory storage")

    def _ensure_collections(self):
        """Ensure all collections exist."""
        existing = self.db.list_collection_names()
        for collection in COLLECTIONS:
            if collection not in existing:
                self.db.create_collection(collection)

    def _ensure_tim_indexes(self):
        """
        v3.0.1: Ensure TIM collection indexes exist for optimal temporal queries.
        Creates indexes for efficient querying by pursuit_id and timestamp.
        """
        try:
            # temporal_events: Query by pursuit + time, and by event_type
            self.db.temporal_events.create_index([("pursuit_id", 1), ("timestamp", -1)])
            self.db.temporal_events.create_index([("event_type", 1)])
            self.db.temporal_events.create_index([("phase", 1)])

            # velocity_metrics: Query by pursuit + calculation time
            self.db.velocity_metrics.create_index([("pursuit_id", 1), ("calculated_at", -1)])

            # phase_transitions: Query by pursuit + transition time
            self.db.phase_transitions.create_index([("pursuit_id", 1), ("transitioned_at", -1)])
            self.db.phase_transitions.create_index([("from_phase", 1), ("to_phase", 1)])

            # time_allocations: Query by pursuit
            self.db.time_allocations.create_index([("pursuit_id", 1)], unique=True)

            print("[Database] TIM indexes created successfully")
        except Exception as e:
            print(f"[Database] TIM index creation warning: {e}")

    def _ensure_intelligence_indexes(self):
        """
        v3.0.2: Ensure Intelligence Layer collection indexes exist.
        Creates indexes for health_scores, validation_experiments, and risk_detections.
        """
        try:
            # health_scores: Query by pursuit + time for health history
            self.db.health_scores.create_index([("pursuit_id", 1), ("calculated_at", -1)])
            self.db.health_scores.create_index([("zone", 1)])

            # validation_experiments: Query by pursuit, risk, status
            self.db.validation_experiments.create_index([("pursuit_id", 1), ("status", 1)])
            self.db.validation_experiments.create_index([("risk_id", 1)])
            self.db.validation_experiments.create_index([("methodology_template", 1)])

            # risk_detections: Query by pursuit + time
            self.db.risk_detections.create_index([("pursuit_id", 1), ("detected_at", -1)])
            self.db.risk_detections.create_index([("overall_risk_level", 1)])

            print("[Database] Intelligence Layer indexes created successfully")
        except Exception as e:
            print(f"[Database] Intelligence Layer index creation warning: {e}")

    def _ensure_analytics_indexes(self):
        """
        v3.0.3: Ensure Analytics & IKF collection indexes exist.
        Creates indexes for portfolio_analytics and ikf_contributions.
        """
        try:
            # portfolio_analytics: Query by user + time for latest snapshot
            self.db.portfolio_analytics.create_index(
                [("user_id", 1), ("calculated_at", -1)]
            )
            self.db.portfolio_analytics.create_index([("calculated_at", -1)])

            # ikf_contributions: Query by user + status for pending reviews
            self.db.ikf_contributions.create_index([("user_id", 1), ("status", 1)])
            self.db.ikf_contributions.create_index([("package_type", 1), ("status", 1)])
            self.db.ikf_contributions.create_index([("pursuit_id", 1)])

            print("[Database] Analytics & IKF indexes created successfully")
        except Exception as e:
            print(f"[Database] Analytics index creation warning: {e}")

    def _ensure_platform_indexes(self):
        """
        v3.1: Ensure Platform Foundation collection indexes exist.
        Creates indexes for sessions, maturity_events, crisis_sessions,
        gii_profiles, domain_events, and coaching_sessions.
        """
        try:
            # users: Unique email index for authentication
            self.db.users.create_index([("email", 1)], unique=True, sparse=True)
            self.db.users.create_index([("gii_id", 1)], sparse=True)

            # sessions: JWT session management with TTL
            self.db.sessions.create_index([("user_id", 1)])
            self.db.sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)

            # maturity_events: Behavioral events for maturity calculation
            self.db.maturity_events.create_index([("user_id", 1), ("timestamp", -1)])
            self.db.maturity_events.create_index([("dimension_affected", 1)])

            # crisis_sessions: Crisis mode records
            self.db.crisis_sessions.create_index([("pursuit_id", 1), ("started_at", -1)])
            self.db.crisis_sessions.create_index([("user_id", 1), ("resolved_at", 1)])

            # gii_profiles: Global Innovator Identifier
            self.db.gii_profiles.create_index([("gii_id", 1)], unique=True)
            self.db.gii_profiles.create_index([("user_id", 1)])

            # domain_events: Persistent event log
            self.db.domain_events.create_index([("event_type", 1), ("timestamp", -1)])
            self.db.domain_events.create_index([("pursuit_id", 1)])
            self.db.domain_events.create_index([("user_id", 1)])

            # coaching_sessions: Coaching session tracking
            self.db.coaching_sessions.create_index([("user_id", 1), ("pursuit_id", 1)])
            self.db.coaching_sessions.create_index([("created_at", -1)])

            # pursuits: Add user_id index for multi-tenant queries
            self.db.pursuits.create_index([("user_id", 1)])

            print("[Database] Platform Foundation indexes created successfully")
        except Exception as e:
            print(f"[Database] Platform index creation warning: {e}")

    def _ensure_ems_indexes(self):
        """
        v3.7.1: Ensure EMS Process Observation Engine collection indexes exist.
        Creates indexes for process_observations collection.
        """
        try:
            # process_observations: Primary query - all observations for a pursuit, ordered by time
            self.db.process_observations.create_index(
                [("pursuit_id", 1), ("timestamp", 1)],
                name="pursuit_timeline"
            )

            # Pattern inference query: all observations by innovator across pursuits
            self.db.process_observations.create_index(
                [("innovator_id", 1), ("timestamp", 1)],
                name="innovator_timeline"
            )

            # Observation type filtering
            self.db.process_observations.create_index(
                [("observation_type", 1)],
                name="by_type"
            )

            # Signal weight filtering for high-confidence observations
            self.db.process_observations.create_index(
                [("signal_weight", -1)],
                name="by_weight"
            )

            # Combined pursuit + type for filtered queries
            self.db.process_observations.create_index(
                [("pursuit_id", 1), ("observation_type", 1)],
                name="pursuit_by_type"
            )

            # Sequence number lookup within pursuit
            self.db.process_observations.create_index(
                [("pursuit_id", 1), ("sequence_number", -1)],
                name="pursuit_sequence"
            )

            # v3.7.3: Review sessions indexes
            self.db.review_sessions.create_index(
                [("innovator_id", 1), ("created_at", -1)],
                name="innovator_timeline"
            )
            self.db.review_sessions.create_index(
                [("inference_result_id", 1)],
                name="by_inference_result"
            )
            self.db.review_sessions.create_index(
                [("status", 1)],
                name="by_status"
            )

            print("[Database] EMS indexes created successfully")
        except Exception as e:
            print(f"[Database] EMS index creation warning: {e}")

    def _migrate_legacy_data(self):
        """
        v3.1: Migrate existing v3.0.3 data to v3.1 multi-user schema.

        Creates a 'legacy' system user and assigns all existing pursuits,
        sessions, memory records, and analytics data to this user.

        Idempotent: safe to run multiple times.
        """
        try:
            # Check if legacy user already exists
            legacy_user = self.db.users.find_one({"email": LEGACY_USER_EMAIL})

            if not legacy_user:
                # Create legacy system user
                legacy_user_id = str(uuid.uuid4())
                legacy_user = {
                    "user_id": legacy_user_id,
                    "email": LEGACY_USER_EMAIL,
                    "name": LEGACY_USER_NAME,
                    "display_name": LEGACY_USER_NAME,
                    "password_hash": "",  # No password - can't log in directly
                    "experience_level": "EXPERT",
                    "maturity_level": "EXPERT",
                    "maturity_scores": {
                        "discovery_competence": 100.0,
                        "validation_rigor": 100.0,
                        "reflective_practice": 100.0,
                        "velocity_management": 100.0,
                        "risk_awareness": 100.0,
                        "knowledge_contribution": 100.0,
                        "composite": 100.0
                    },
                    "gii_id": None,
                    "organization_id": None,
                    "preferences": {},
                    "is_legacy": True,
                    "created_at": datetime.now(timezone.utc),
                    "last_active": datetime.now(timezone.utc),
                    "pursuit_count": 0,
                    "completed_pursuits": 0
                }
                self.db.users.insert_one(legacy_user)
                print(f"[Database] Created legacy system user: {LEGACY_USER_EMAIL}")
            else:
                legacy_user_id = legacy_user.get("user_id")

            # Migrate pursuits without user_id
            pursuits_updated = self.db.pursuits.update_many(
                {"user_id": {"$exists": False}},
                {
                    "$set": {
                        "user_id": legacy_user_id,
                        "storage_election": "FULL_PARTICIPATION",
                        "crisis_history": []
                    }
                }
            )
            if pursuits_updated.modified_count > 0:
                print(f"[Database] Migrated {pursuits_updated.modified_count} pursuits to legacy user")

            # Migrate coaching_sessions without user_id
            sessions_updated = self.db.conversation_history.update_many(
                {"user_id": {"$exists": False}},
                {"$set": {"user_id": legacy_user_id}}
            )
            if sessions_updated.modified_count > 0:
                print(f"[Database] Migrated {sessions_updated.modified_count} conversations to legacy user")

            # Add storage_election to pursuits without it
            election_updated = self.db.pursuits.update_many(
                {"storage_election": {"$exists": False}},
                {"$set": {"storage_election": "FULL_PARTICIPATION"}}
            )

            # Add crisis_history to pursuits without it
            crisis_updated = self.db.pursuits.update_many(
                {"crisis_history": {"$exists": False}},
                {"$set": {"crisis_history": []}}
            )

            # Update legacy user's pursuit count
            pursuit_count = self.db.pursuits.count_documents({"user_id": legacy_user_id})
            completed_count = self.db.pursuits.count_documents({
                "user_id": legacy_user_id,
                "status": {"$regex": "^COMPLETED|^TERMINATED"}
            })
            self.db.users.update_one(
                {"user_id": legacy_user_id},
                {"$set": {
                    "pursuit_count": pursuit_count,
                    "completed_pursuits": completed_count
                }}
            )

            print("[Database] Legacy migration completed successfully")

        except Exception as e:
            print(f"[Database] Legacy migration warning: {e}")

    def _ensure_demo_user(self):
        """Ensure demo user exists."""
        if not self.get_user(DEMO_USER_ID):
            self.create_user(DEMO_USER_ID, DEMO_USER_NAME)

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def create_user(self, user_id: str, name: str, email: str = None) -> Dict:
        """Create a new user."""
        user = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "created_at": datetime.now(timezone.utc)
        }
        self.db.users.insert_one(user)
        return user

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        return self.db.users.find_one({"user_id": user_id})

    # =========================================================================
    # PURSUIT OPERATIONS
    # =========================================================================

    def create_pursuit(self, user_id: str, title: str) -> Dict:
        """Create a new pursuit."""
        pursuit_id = str(uuid.uuid4())
        pursuit = {
            "pursuit_id": pursuit_id,
            "user_id": user_id,
            "title": title,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "artifact_ids": []
        }
        self.db.pursuits.insert_one(pursuit)

        # Initialize empty scaffolding state
        self._init_scaffolding_state(pursuit_id)

        return pursuit

    def get_pursuit(self, pursuit_id: str) -> Optional[Dict]:
        """Get pursuit by ID."""
        return self.db.pursuits.find_one({"pursuit_id": pursuit_id})

    def get_user_pursuits(self, user_id: str, status: str = None) -> List[Dict]:
        """Get all pursuits for a user."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return list(self.db.pursuits.find(query).sort("updated_at", -1))

    def update_pursuit(self, pursuit_id: str, updates: Dict) -> bool:
        """Update pursuit fields."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def add_artifact_to_pursuit(self, pursuit_id: str, artifact_id: str) -> bool:
        """Add artifact reference to pursuit."""
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$push": {"artifact_ids": artifact_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0

    # =========================================================================
    # SCAFFOLDING STATE OPERATIONS
    # =========================================================================

    def _init_scaffolding_state(self, pursuit_id: str) -> Dict:
        """Initialize empty scaffolding state for a pursuit."""
        # Import here to avoid circular import at module level
        try:
            from config import V25_IMPORTANT_ELEMENTS
        except ImportError:
            V25_IMPORTANT_ELEMENTS = []

        state = {
            "pursuit_id": pursuit_id,
            "vision_elements": {elem: None for elem in CRITICAL_ELEMENTS["vision"]},
            "fear_elements": {elem: None for elem in CRITICAL_ELEMENTS["fears"]},
            "hypothesis_elements": {elem: None for elem in CRITICAL_ELEMENTS["hypothesis"]},
            # v2.5: Important elements for richer pattern matching
            "important_elements": {elem: None for elem in V25_IMPORTANT_ELEMENTS},
            # v2.3: Teleological profile for methodology inference
            "teleological_profile": {
                "purpose_type": None,
                "beneficiary": None,
                "uncertainty_level": 0.5,  # Default neutral
                "value_creation_mode": None,
                "resource_context": None,
                "org_context": None,
                "innovation_type": None,
                "maturity_state": "spark",  # Default early stage
                "confidence": 0.0,
                "last_assessed": None
            },
            # v2.3: Question usage tracking for rotation
            "question_usage_history": [],
            # v2.5: Track element update history for lifecycle
            "element_update_history": [],
            "updated_at": datetime.now(timezone.utc)
        }
        self.db.scaffolding_states.insert_one(state)
        return state

    def get_scaffolding_state(self, pursuit_id: str) -> Optional[Dict]:
        """Get scaffolding state for a pursuit."""
        return self.db.scaffolding_states.find_one({"pursuit_id": pursuit_id})

    def update_scaffolding_element(self, pursuit_id: str, element_type: str,
                                   element_name: str, text: str, confidence: float) -> bool:
        """
        Update a single scaffolding element.

        Args:
            pursuit_id: Pursuit ID
            element_type: 'vision', 'fears', or 'hypothesis'
            element_name: Name of the element (e.g., 'problem_statement')
            text: Extracted text
            confidence: Confidence score 0.0-1.0
        """
        field_map = {
            "vision": "vision_elements",
            "fears": "fear_elements",
            "hypothesis": "hypothesis_elements"
        }
        field = field_map.get(element_type)
        if not field:
            return False

        update_path = f"{field}.{element_name}"
        result = self.db.scaffolding_states.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$set": {
                    update_path: {
                        "text": text,
                        "confidence": confidence,
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def update_scaffolding_elements_batch(self, pursuit_id: str,
                                          elements: Dict[str, Dict]) -> bool:
        """
        Update multiple scaffolding elements at once.

        Args:
            pursuit_id: Pursuit ID
            elements: Dict like {"vision": {"problem_statement": {"text": "...", "confidence": 0.8}}}
        """
        field_map = {
            "vision": "vision_elements",
            "fears": "fear_elements",
            "hypothesis": "hypothesis_elements"
        }

        updates = {"updated_at": datetime.now(timezone.utc)}

        for element_type, element_dict in elements.items():
            field = field_map.get(element_type)
            if field and element_dict:
                for element_name, data in element_dict.items():
                    if data:
                        updates[f"{field}.{element_name}"] = {
                            "text": data.get("text", ""),
                            "confidence": data.get("confidence", 0.5),
                            "updated_at": datetime.now(timezone.utc)
                        }

        if len(updates) > 1:  # More than just updated_at
            result = self.db.scaffolding_states.update_one(
                {"pursuit_id": pursuit_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        return False

    def get_element_completeness(self, pursuit_id: str) -> Dict[str, float]:
        """
        Calculate completeness for each artifact type.

        Returns:
            {
                "vision": 0.625,      # 5/8 elements present
                "fears": 0.5,         # 3/6 elements present
                "hypothesis": 0.333,  # 2/6 elements present
                "overall": 0.476      # 10/20 elements present
            }
        """
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return {"vision": 0.0, "fears": 0.0, "hypothesis": 0.0, "overall": 0.0}

        def count_present(elements_dict):
            if not elements_dict:
                return 0
            return sum(1 for v in elements_dict.values() if v is not None and v.get("text"))

        vision_count = count_present(state.get("vision_elements", {}))
        fear_count = count_present(state.get("fear_elements", {}))
        hypothesis_count = count_present(state.get("hypothesis_elements", {}))

        vision_total = len(CRITICAL_ELEMENTS["vision"])
        fear_total = len(CRITICAL_ELEMENTS["fears"])
        hypothesis_total = len(CRITICAL_ELEMENTS["hypothesis"])
        total = vision_total + fear_total + hypothesis_total

        return {
            "vision": vision_count / vision_total if vision_total > 0 else 0.0,
            "fears": fear_count / fear_total if fear_total > 0 else 0.0,
            "hypothesis": hypothesis_count / hypothesis_total if hypothesis_total > 0 else 0.0,
            "overall": (vision_count + fear_count + hypothesis_count) / total if total > 0 else 0.0
        }

    def get_missing_elements(self, pursuit_id: str, artifact_type: str) -> List[str]:
        """Get list of missing elements for an artifact type."""
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return CRITICAL_ELEMENTS.get(artifact_type, [])

        field_map = {
            "vision": "vision_elements",
            "fears": "fear_elements",
            "hypothesis": "hypothesis_elements"
        }
        field = field_map.get(artifact_type)
        if not field:
            return []

        elements_dict = state.get(field, {})
        all_elements = CRITICAL_ELEMENTS.get(artifact_type, [])

        return [
            elem for elem in all_elements
            if not elements_dict.get(elem) or not elements_dict[elem].get("text")
        ]

    def get_present_elements(self, pursuit_id: str, artifact_type: str) -> Dict[str, str]:
        """Get dict of present elements with their text."""
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return {}

        field_map = {
            "vision": "vision_elements",
            "fears": "fear_elements",
            "hypothesis": "hypothesis_elements"
        }
        field = field_map.get(artifact_type)
        if not field:
            return {}

        elements_dict = state.get(field, {})
        return {
            elem: data.get("text", "")
            for elem, data in elements_dict.items()
            if data and data.get("text")
        }

    # =========================================================================
    # v2.3: TELEOLOGICAL PROFILE OPERATIONS
    # =========================================================================

    def update_teleological_profile(self, pursuit_id: str, profile: Dict) -> bool:
        """
        Update teleological profile for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            profile: Dict containing teleological dimensions
        """
        result = self.db.scaffolding_states.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$set": {
                    "teleological_profile": profile,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def get_teleological_profile(self, pursuit_id: str) -> Optional[Dict]:
        """Get teleological profile for a pursuit."""
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return None
        return state.get("teleological_profile", {})

    def record_question_usage(self, pursuit_id: str, question_text: str,
                              response_sentiment: str = "neutral") -> bool:
        """
        Record that a coaching question was used.

        This enables question rotation to prevent repetition.

        Args:
            pursuit_id: Pursuit ID
            question_text: The question that was used
            response_sentiment: User's response sentiment (positive/neutral/negative)
        """
        usage_record = {
            "question_text": question_text,
            "used_at": datetime.now(timezone.utc),
            "user_response_sentiment": response_sentiment
        }
        result = self.db.scaffolding_states.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$push": {"question_usage_history": usage_record},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0

    def get_used_questions(self, pursuit_id: str, limit: int = 20) -> List[str]:
        """Get list of recently used questions for a pursuit."""
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return []

        history = state.get("question_usage_history", [])
        # Get most recent questions
        recent = history[-limit:] if len(history) > limit else history
        return [q.get("question_text", "") for q in recent]

    # =========================================================================
    # ARTIFACT OPERATIONS (v2.4: added versioning support)
    # =========================================================================

    def create_artifact(self, pursuit_id: str, artifact_type: str,
                        content: str, elements_used: List[str],
                        completeness: float, generation_method: str = "automatic") -> Dict:
        """
        Create a new artifact with versioning support.

        v2.4: Added versioning fields for artifact lifecycle management.
        """
        artifact_id = str(uuid.uuid4())
        artifact = {
            "artifact_id": artifact_id,
            "pursuit_id": pursuit_id,
            "type": artifact_type,
            "content": content,
            "generated_from": {
                "elements_used": elements_used,
                "completeness": completeness,
                "generation_method": generation_method
            },
            "created_at": datetime.now(timezone.utc),
            # v2.4: Versioning fields
            "version": 1,
            "status": "CURRENT",           # CURRENT or SUPERSEDED
            "parent_artifact_id": None,    # Links to previous version
            "superseded_at": None,         # When this was replaced
            "superseded_by": None          # What replaced it
        }
        self.db.artifacts.insert_one(artifact)

        # Add reference to pursuit
        self.add_artifact_to_pursuit(pursuit_id, artifact_id)

        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[Dict]:
        """Get artifact by ID."""
        return self.db.artifacts.find_one({"artifact_id": artifact_id})

    def get_pursuit_artifacts(self, pursuit_id: str, artifact_type: str = None,
                              include_superseded: bool = False) -> List[Dict]:
        """
        Get artifacts for a pursuit.

        v2.4: Added include_superseded parameter for version history.

        Args:
            pursuit_id: Pursuit ID
            artifact_type: Optional filter by type
            include_superseded: If False (default), only return CURRENT artifacts

        Returns:
            List of artifact dicts, newest first
        """
        query = {"pursuit_id": pursuit_id}
        if artifact_type:
            query["type"] = artifact_type
        if not include_superseded:
            query["status"] = {"$ne": "SUPERSEDED"}

        return list(self.db.artifacts.find(query).sort("created_at", -1))

    def update_artifact(self, artifact_id: str, updates: Dict) -> bool:
        """
        Update artifact fields.

        v2.4: Used for version management (marking superseded, linking versions).

        Args:
            artifact_id: Artifact ID to update
            updates: Dict of fields to update

        Returns:
            True if update succeeded
        """
        result = self.db.artifacts.update_one(
            {"artifact_id": artifact_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def get_artifact_version_history(self, pursuit_id: str,
                                      artifact_type: str) -> List[Dict]:
        """
        v2.4: Get all versions of an artifact type for a pursuit.

        Returns versions sorted by version number descending (newest first).
        """
        artifacts = self.get_pursuit_artifacts(
            pursuit_id, artifact_type, include_superseded=True
        )

        # Sort by version descending
        return sorted(
            artifacts,
            key=lambda a: a.get("version", 1),
            reverse=True
        )

    # =========================================================================
    # CONVERSATION HISTORY OPERATIONS
    # =========================================================================

    def save_conversation_turn(self, pursuit_id: str, role: str, content: str,
                               metadata: Dict = None) -> Dict:
        """Save a conversation turn."""
        turn = {
            "pursuit_id": pursuit_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {}
        }
        self.db.conversation_history.insert_one(turn)
        return turn

    def get_conversation_history(self, pursuit_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for a pursuit."""
        return list(
            self.db.conversation_history
            .find({"pursuit_id": pursuit_id})
            .sort("timestamp", -1)
            .limit(limit)
        )[::-1]  # Reverse to get chronological order

    # =========================================================================
    # INTERVENTION HISTORY OPERATIONS
    # =========================================================================

    def record_intervention(self, pursuit_id: str, moment_type: str,
                            suggestion: str, user_response: str = None) -> Dict:
        """Record an intervention that was made."""
        intervention = {
            "pursuit_id": pursuit_id,
            "moment_type": moment_type,
            "timestamp": datetime.now(timezone.utc),
            "suggestion_made": suggestion,
            "user_response": user_response
        }
        self.db.intervention_history.insert_one(intervention)
        return intervention

    def get_last_intervention(self, pursuit_id: str, moment_type: str) -> Optional[Dict]:
        """Get the last intervention of a specific type for a pursuit."""
        return self.db.intervention_history.find_one(
            {"pursuit_id": pursuit_id, "moment_type": moment_type},
            sort=[("timestamp", -1)]
        )

    def update_intervention_response(self, pursuit_id: str, moment_type: str,
                                      response: str) -> bool:
        """Update the user response for the most recent intervention."""
        result = self.db.intervention_history.update_one(
            {"pursuit_id": pursuit_id, "moment_type": moment_type},
            {"$set": {"user_response": response}},
            sort=[("timestamp", -1)]
        )
        return result.modified_count > 0

    # =========================================================================
    # PATTERN OPERATIONS (v2.5: Enhanced for IML pattern matching)
    # =========================================================================

    def create_pattern(self, title: str, description: str,
                       domain: str, outcome: str) -> Dict:
        """Create a new pattern (legacy method, kept for backward compatibility)."""
        pattern_id = str(uuid.uuid4())
        pattern = {
            "pattern_id": pattern_id,
            "title": title,
            "description": description,
            "domain": domain,
            "outcome": outcome,
            "created_at": datetime.now(timezone.utc)
        }
        self.db.patterns.insert_one(pattern)
        return pattern

    def create_v25_pattern(self, pattern_name: str, problem_context: Dict,
                           solution_approach: str, key_insight: str,
                           source_pursuits: List[str],
                           pattern_type: str = "proto-pattern") -> Dict:
        """
        v2.5: Create a pattern with full IML schema.

        Args:
            pattern_name: Concise name for the pattern
            problem_context: {
                "domain": ["healthcare", "consumer"],
                "problem_type": ["resource_constraints", "market_timing"],
                "innovation_stage": ["vision", "hypothesis"]
            }
            solution_approach: Description of the approach
            key_insight: The core learning
            source_pursuits: List of pursuit IDs this pattern came from
            pattern_type: "proto-pattern" or "validated-pattern"

        Returns:
            Created pattern dict
        """
        pattern_id = str(uuid.uuid4())
        pattern = {
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "pattern_type": pattern_type,
            "problem_context": problem_context,
            "solution_approach": solution_approach,
            "key_insight": key_insight,
            "effectiveness": {
                "success_count": 0,
                "pivot_count": 0,
                "fail_count": 0,
                "total_applications": 0,
                "success_rate": 0.0
            },
            "source_pursuits": source_pursuits,
            "embedding_vector": None,  # To be set by pattern engine
            "created_at": datetime.now(timezone.utc),
            "validated_at": None,
            "last_applied": None
        }
        self.db.patterns.insert_one(pattern)
        return pattern

    def get_patterns(self, domain: str = None, outcome: str = None) -> List[Dict]:
        """Get patterns, optionally filtered (legacy method)."""
        query = {}
        if domain:
            query["domain"] = domain
        if outcome:
            query["outcome"] = outcome
        return list(self.db.patterns.find(query))

    def find_patterns_by_context(self, domains: List[str] = None,
                                  problem_types: List[str] = None,
                                  min_success_rate: float = 0.0) -> List[Dict]:
        """
        v2.5: Find patterns matching the given context criteria.

        Args:
            domains: List of domains to match (any match counts)
            problem_types: List of problem types to match
            min_success_rate: Minimum effectiveness threshold

        Returns:
            List of matching patterns
        """
        query = {}

        if domains:
            query["problem_context.domain"] = {"$in": domains}

        if problem_types:
            query["problem_context.problem_type"] = {"$in": problem_types}

        if min_success_rate > 0:
            query["effectiveness.success_rate"] = {"$gte": min_success_rate}

        return list(self.db.patterns.find(query))

    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """Get pattern by ID."""
        return self.db.patterns.find_one({"pattern_id": pattern_id})

    def update_pattern(self, pattern_id: str, updates: Dict) -> bool:
        """Update pattern fields."""
        result = self.db.patterns.update_one(
            {"pattern_id": pattern_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def update_pattern_effectiveness(self, pattern_id: str,
                                      outcome: str) -> bool:
        """
        v2.5: Update pattern effectiveness based on pursuit outcome.

        Args:
            pattern_id: Pattern ID
            outcome: "success" | "pivot" | "fail"

        Returns:
            True if update succeeded
        """
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return False

        effectiveness = pattern.get("effectiveness", {})

        if outcome == "success":
            effectiveness["success_count"] = effectiveness.get("success_count", 0) + 1
        elif outcome == "pivot":
            effectiveness["pivot_count"] = effectiveness.get("pivot_count", 0) + 1
        elif outcome == "fail":
            effectiveness["fail_count"] = effectiveness.get("fail_count", 0) + 1

        effectiveness["total_applications"] = effectiveness.get("total_applications", 0) + 1

        # Recalculate success rate (success / total)
        total = effectiveness["total_applications"]
        if total > 0:
            effectiveness["success_rate"] = effectiveness.get("success_count", 0) / total

        return self.update_pattern(pattern_id, {
            "effectiveness": effectiveness,
            "last_applied": datetime.now(timezone.utc)
        })

    def promote_pattern_to_validated(self, pattern_id: str) -> bool:
        """
        v2.5: Promote a proto-pattern to validated pattern.

        Called when pattern has been successfully applied N times.
        """
        return self.update_pattern(pattern_id, {
            "pattern_type": "validated-pattern",
            "validated_at": datetime.now(timezone.utc)
        })

    # =========================================================================
    # v2.5: USER ENGAGEMENT METRICS OPERATIONS
    # =========================================================================

    def create_engagement_record(self, user_id: str, pursuit_id: str) -> Dict:
        """
        v2.5: Create initial engagement metrics record for a user/pursuit.
        """
        record = {
            "user_id": user_id,
            "pursuit_id": pursuit_id,
            "session_start": datetime.now(timezone.utc),
            "last_active": datetime.now(timezone.utc),
            "metrics": {
                "message_count": 0,
                "total_message_length": 0,
                "avg_message_length": 0.0,
                "messages_per_hour": 0.0,
                "intervention_response_rate": 0.0,
                "interventions_shown": 0,
                "interventions_responded": 0,
                "artifact_interaction_count": 0,
                "session_duration_minutes": 0.0
            },
            "engagement_score": 0.5,  # Start neutral
            "engagement_tier": "medium",
            "calculated_at": datetime.now(timezone.utc)
        }
        self.db.user_engagement_metrics.insert_one(record)
        return record

    def get_engagement_metrics(self, user_id: str, pursuit_id: str) -> Optional[Dict]:
        """v2.5: Get engagement metrics for a user/pursuit."""
        return self.db.user_engagement_metrics.find_one({
            "user_id": user_id,
            "pursuit_id": pursuit_id
        })

    def update_engagement_metrics(self, user_id: str, pursuit_id: str,
                                   message_length: int = None,
                                   intervention_shown: bool = False,
                                   intervention_responded: bool = False,
                                   artifact_interaction: bool = False) -> bool:
        """
        v2.5: Update engagement metrics after user activity.

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            message_length: Length of user's message (if applicable)
            intervention_shown: Whether an intervention was shown
            intervention_responded: Whether user responded to intervention
            artifact_interaction: Whether user interacted with artifact
        """
        record = self.get_engagement_metrics(user_id, pursuit_id)

        if not record:
            record = self.create_engagement_record(user_id, pursuit_id)

        metrics = record.get("metrics", {})
        session_start = record.get("session_start", datetime.now(timezone.utc))

        # Update message metrics
        if message_length is not None:
            metrics["message_count"] = metrics.get("message_count", 0) + 1
            metrics["total_message_length"] = metrics.get("total_message_length", 0) + message_length

            if metrics["message_count"] > 0:
                metrics["avg_message_length"] = metrics["total_message_length"] / metrics["message_count"]

        # Update intervention metrics
        if intervention_shown:
            metrics["interventions_shown"] = metrics.get("interventions_shown", 0) + 1

        if intervention_responded:
            metrics["interventions_responded"] = metrics.get("interventions_responded", 0) + 1

        if metrics.get("interventions_shown", 0) > 0:
            metrics["intervention_response_rate"] = (
                metrics.get("interventions_responded", 0) /
                metrics["interventions_shown"]
            )

        # Update artifact interactions
        if artifact_interaction:
            metrics["artifact_interaction_count"] = metrics.get("artifact_interaction_count", 0) + 1

        # Calculate session duration
        now = datetime.now(timezone.utc)
        # Ensure session_start is timezone-aware for comparison
        if isinstance(session_start, datetime) and session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=timezone.utc)
        duration = (now - session_start).total_seconds() / 60.0
        metrics["session_duration_minutes"] = duration

        # Calculate messages per hour
        if duration > 0:
            metrics["messages_per_hour"] = metrics.get("message_count", 0) / (duration / 60.0)

        # Calculate overall engagement score
        engagement_score = self._calculate_engagement_score(metrics)

        # Determine tier
        if engagement_score >= 0.70:
            tier = "high"
        elif engagement_score >= 0.40:
            tier = "medium"
        else:
            tier = "low"

        # Update the record
        result = self.db.user_engagement_metrics.update_one(
            {"user_id": user_id, "pursuit_id": pursuit_id},
            {"$set": {
                "metrics": metrics,
                "last_active": now,
                "engagement_score": engagement_score,
                "engagement_tier": tier,
                "calculated_at": now
            }}
        )
        return result.modified_count > 0

    def _calculate_engagement_score(self, metrics: Dict) -> float:
        """
        v2.5: Calculate engagement score from metrics.

        Formula considers:
        - Message frequency (30% weight)
        - Message length (20% weight)
        - Intervention response rate (30% weight)
        - Artifact interactions (20% weight)
        """
        score = 0.0

        # Message frequency score (cap at 10 messages/hour = 1.0)
        mph = metrics.get("messages_per_hour", 0)
        freq_score = min(1.0, mph / 10.0)
        score += freq_score * 0.30

        # Message length score (normalize to 0-1, where 200+ words = 1.0)
        avg_len = metrics.get("avg_message_length", 0)
        len_score = min(1.0, avg_len / 200.0)
        score += len_score * 0.20

        # Intervention response rate (already 0-1)
        response_rate = metrics.get("intervention_response_rate", 0.5)
        score += response_rate * 0.30

        # Artifact interaction score (cap at 5 interactions = 1.0)
        artifact_count = metrics.get("artifact_interaction_count", 0)
        artifact_score = min(1.0, artifact_count / 5.0)
        score += artifact_score * 0.20

        return round(score, 3)

    # =========================================================================
    # v2.5: PATTERN EFFECTIVENESS TRACKING
    # =========================================================================

    def record_pattern_application(self, pattern_id: str, pursuit_id: str,
                                    relevance_score: float) -> Dict:
        """
        v2.5: Record that a pattern was suggested to a pursuit.

        Args:
            pattern_id: Pattern ID that was suggested
            pursuit_id: Pursuit ID where it was suggested
            relevance_score: Calculated relevance score

        Returns:
            Created record dict
        """
        record = {
            "pattern_id": pattern_id,
            "pursuit_id": pursuit_id,
            "relevance_score": relevance_score,
            "user_feedback": None,  # "helpful" | "not_applicable" | "ignored"
            "outcome_influenced": None,
            "applied_at": datetime.now(timezone.utc)
        }
        self.db.pattern_effectiveness.insert_one(record)
        return record

    def update_pattern_feedback(self, pattern_id: str, pursuit_id: str,
                                 feedback: str, outcome_influenced: bool = None) -> bool:
        """
        v2.5: Update pattern application with user feedback.

        Args:
            pattern_id: Pattern ID
            pursuit_id: Pursuit ID
            feedback: "helpful" | "not_applicable" | "ignored"
            outcome_influenced: Whether pattern influenced pursuit outcome
        """
        updates = {
            "user_feedback": feedback,
            "feedback_at": datetime.now(timezone.utc)
        }
        if outcome_influenced is not None:
            updates["outcome_influenced"] = outcome_influenced

        result = self.db.pattern_effectiveness.update_one(
            {"pattern_id": pattern_id, "pursuit_id": pursuit_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def get_pattern_applications(self, pattern_id: str) -> List[Dict]:
        """v2.5: Get all applications of a specific pattern."""
        return list(self.db.pattern_effectiveness.find({"pattern_id": pattern_id}))

    # =========================================================================
    # v2.5: IMPORTANT ELEMENTS TRACKING
    # =========================================================================

    def update_important_element(self, pursuit_id: str, element_name: str,
                                  text: str, confidence: float,
                                  extraction_method: str = "llm") -> bool:
        """
        v2.5: Update an important (non-critical) element.

        Args:
            pursuit_id: Pursuit ID
            element_name: Name from V25_IMPORTANT_ELEMENTS
            text: Extracted text
            confidence: Confidence score 0.0-1.0
            extraction_method: "llm" | "explicit" | "inferred"
        """
        update_path = f"important_elements.{element_name}"
        result = self.db.scaffolding_states.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$set": {
                    update_path: {
                        "text": text,
                        "confidence": confidence,
                        "extraction_method": extraction_method,
                        "extracted_at": datetime.now(timezone.utc),
                        "tier": "important"
                    },
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def get_important_elements(self, pursuit_id: str) -> Dict:
        """v2.5: Get all important elements for a pursuit."""
        state = self.get_scaffolding_state(pursuit_id)
        if not state:
            return {}
        return state.get("important_elements", {})

    # =========================================================================
    # SYSTEM CONFIG OPERATIONS
    # =========================================================================

    def get_config(self, key: str) -> Any:
        """Get a system config value."""
        doc = self.db.system_config.find_one({"key": key})
        return doc.get("value") if doc else None

    def set_config(self, key: str, value: Any) -> bool:
        """Set a system config value."""
        result = self.db.system_config.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )
        return result.acknowledged

    # =========================================================================
    # v2.6: STAKEHOLDER FEEDBACK OPERATIONS
    # =========================================================================

    def save_stakeholder_feedback(self, pursuit_id: str, stakeholder_name: str,
                                   role: str, support_level: str,
                                   concerns: List[str] = None,
                                   resources_offered: str = "",
                                   conditions: str = "",
                                   organization: str = "",
                                   notes: str = "",
                                   capture_method: str = "quick_form") -> str:
        """
        v2.6: Save stakeholder feedback record.

        Args:
            pursuit_id: Pursuit ID
            stakeholder_name: Name of stakeholder
            role: Role/title
            support_level: supportive/conditional/neutral/opposed/unclear
            concerns: List of concerns raised
            resources_offered: Resources the stakeholder offered
            conditions: Conditions for support
            organization: Organization name (optional)
            notes: Additional notes
            capture_method: How feedback was captured

        Returns:
            feedback_id of saved record
        """
        import uuid as uuid_module
        feedback_id = str(uuid_module.uuid4())

        feedback = {
            "feedback_id": feedback_id,
            "pursuit_id": pursuit_id,
            "stakeholder_name": stakeholder_name,
            "role": role,
            "organization": organization,
            "date": datetime.now(timezone.utc),
            "support_level": support_level.lower(),
            "concerns": concerns or [],
            "resources_offered": resources_offered,
            "conditions": conditions,
            "notes": notes,
            "capture_method": capture_method,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        self.db.stakeholder_feedback.insert_one(feedback)
        return feedback_id

    def get_stakeholder_feedback_by_pursuit(self, pursuit_id: str) -> List[Dict]:
        """v2.6: Get all stakeholder feedback for a pursuit."""
        return list(self.db.stakeholder_feedback.find({"pursuit_id": pursuit_id}))

    def get_stakeholder_feedback(self, feedback_id: str) -> Optional[Dict]:
        """v2.6: Get stakeholder feedback by ID."""
        return self.db.stakeholder_feedback.find_one({"feedback_id": feedback_id})

    def update_stakeholder_feedback(self, feedback_id: str, updates: Dict) -> bool:
        """v2.6: Update stakeholder feedback record."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.stakeholder_feedback.update_one(
            {"feedback_id": feedback_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def count_stakeholder_feedback(self, pursuit_id: str) -> int:
        """v2.6: Count stakeholder feedback entries for a pursuit."""
        return len(list(self.db.stakeholder_feedback.find({"pursuit_id": pursuit_id})))

    def update_pursuit_stakeholder_summary(self, pursuit_id: str,
                                            summary: Dict) -> bool:
        """
        v2.6: Update pursuit with stakeholder summary.

        Args:
            pursuit_id: Pursuit ID
            summary: {
                "total_engaged": int,
                "support_distribution": {...},
                "top_concerns": [...],
                "resources_committed": [...],
                "consensus_readiness": float
            }

        Returns:
            True if update succeeded
        """
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "stakeholder_summary": summary,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def get_pursuit_stakeholder_summary(self, pursuit_id: str) -> Optional[Dict]:
        """v2.6: Get stakeholder summary for a pursuit."""
        pursuit = self.get_pursuit(pursuit_id)
        if not pursuit:
            return None
        return pursuit.get("stakeholder_summary", {})

    # =========================================================================
    # v2.8: LIVING SNAPSHOT REPORT OPERATIONS
    # =========================================================================

    def create_living_snapshot_report(self, report_record: Dict) -> str:
        """v2.8: Create a living snapshot report."""
        if "report_id" not in report_record:
            report_record["report_id"] = str(uuid.uuid4())
        report_record["created_at"] = datetime.now(timezone.utc)
        self.db.living_snapshot_reports.insert_one(report_record)
        return report_record["report_id"]

    def get_living_snapshot_report(self, report_id: str) -> Optional[Dict]:
        """v2.8: Get a living snapshot report by ID."""
        return self.db.living_snapshot_reports.find_one({"report_id": report_id})

    def get_pursuit_snapshots(self, pursuit_id: str) -> List[Dict]:
        """v2.8: Get all snapshots for a pursuit."""
        return list(self.db.living_snapshot_reports.find(
            {"pursuit_id": pursuit_id}
        ).sort("generated_at", -1))

    # =========================================================================
    # v2.8: PORTFOLIO ANALYTICS REPORT OPERATIONS
    # =========================================================================

    def create_portfolio_analytics_report(self, report_record: Dict) -> str:
        """v2.8: Create a portfolio analytics report."""
        if "report_id" not in report_record:
            report_record["report_id"] = str(uuid.uuid4())
        report_record["created_at"] = datetime.now(timezone.utc)
        self.db.portfolio_analytics_reports.insert_one(report_record)
        return report_record["report_id"]

    def get_portfolio_analytics_report(self, report_id: str) -> Optional[Dict]:
        """v2.8: Get a portfolio analytics report by ID."""
        return self.db.portfolio_analytics_reports.find_one({"report_id": report_id})

    def get_user_portfolio_reports(self, user_id: str) -> List[Dict]:
        """v2.8: Get all portfolio reports for a user."""
        return list(self.db.portfolio_analytics_reports.find(
            {"scope_id": user_id}
        ).sort("generated_at", -1))

    # =========================================================================
    # v2.8: REPORT TEMPLATE OPERATIONS
    # =========================================================================

    def create_report_template(self, template_record: Dict) -> str:
        """v2.8: Create a custom report template."""
        if "template_id" not in template_record:
            template_record["template_id"] = str(uuid.uuid4())
        template_record["created_at"] = datetime.now(timezone.utc)
        self.db.report_templates.insert_one(template_record)
        return template_record["template_id"]

    def get_report_template(self, template_id: str) -> Optional[Dict]:
        """v2.8: Get a report template by ID."""
        return self.db.report_templates.find_one({"template_id": template_id})

    def get_user_templates(self, user_id: str) -> List[Dict]:
        """v2.8: Get custom templates for a user."""
        return list(self.db.report_templates.find({"created_by": user_id}))

    def get_system_templates(self) -> List[Dict]:
        """v2.8: Get all system templates."""
        return list(self.db.report_templates.find({"is_system": True}))

    # =========================================================================
    # v2.8: UNIFIED REPORT OPERATIONS (for review workflow)
    # =========================================================================

    def get_report(self, report_id: str) -> Optional[Dict]:
        """v2.8: Get any report by ID (tries all report collections)."""
        report = self.db.terminal_reports.find_one({"report_id": report_id})
        if report:
            return report
        report = self.db.living_snapshot_reports.find_one({"report_id": report_id})
        if report:
            return report
        report = self.db.portfolio_analytics_reports.find_one({"report_id": report_id})
        return report

    def update_report(self, report_id: str, updates: Dict) -> bool:
        """v2.8: Update any report by ID (tries all report collections)."""
        updates["updated_at"] = datetime.now(timezone.utc)

        # Try terminal reports first
        result = self.db.terminal_reports.update_one(
            {"report_id": report_id},
            {"$set": updates}
        )
        if result.modified_count > 0:
            return True

        # Try living snapshot reports
        result = self.db.living_snapshot_reports.update_one(
            {"report_id": report_id},
            {"$set": updates}
        )
        if result.modified_count > 0:
            return True

        # Try portfolio analytics reports
        result = self.db.portfolio_analytics_reports.update_one(
            {"report_id": report_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def create_report(self, report_record: Dict) -> str:
        """v2.8: Create a new report record (for versioning)."""
        report_type = report_record.get("report_type", "TERMINAL")
        if "report_id" not in report_record:
            report_record["report_id"] = str(uuid.uuid4())
        report_record["created_at"] = datetime.now(timezone.utc)

        if report_type == "TERMINAL":
            self.db.terminal_reports.insert_one(report_record)
        elif report_type == "LIVING_SNAPSHOT":
            self.db.living_snapshot_reports.insert_one(report_record)
        elif report_type == "PORTFOLIO_ANALYTICS":
            self.db.portfolio_analytics_reports.insert_one(report_record)

        return report_record["report_id"]

    # =========================================================================
    # v2.9: REPORT DISTRIBUTION OPERATIONS
    # =========================================================================

    def create_report_distribution(self, distribution_record: Dict) -> str:
        """v2.9: Create a report distribution record."""
        if "distribution_id" not in distribution_record:
            distribution_record["distribution_id"] = str(uuid.uuid4())
        distribution_record["created_at"] = datetime.now(timezone.utc)
        distribution_record["updated_at"] = datetime.now(timezone.utc)
        self.db.report_distributions.insert_one(distribution_record)
        return distribution_record["distribution_id"]

    def get_report_distribution(self, distribution_id: str) -> Optional[Dict]:
        """v2.9: Get a distribution record by ID."""
        return self.db.report_distributions.find_one({"distribution_id": distribution_id})

    def get_report_distributions(self, report_id: str) -> List[Dict]:
        """v2.9: Get all distributions for a report."""
        return list(self.db.report_distributions.find({"report_id": report_id}))

    def update_report_distribution(self, distribution_id: str, updates: Dict) -> bool:
        """v2.9: Update a distribution record."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.report_distributions.update_one(
            {"distribution_id": distribution_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def get_distribution_by_token(self, token: str) -> Optional[Dict]:
        """v2.9: Get distribution by share token."""
        return self.db.report_distributions.find_one({"share_link.token": token})

    # =========================================================================
    # v2.9: SHARED PURSUITS OPERATIONS
    # =========================================================================

    def create_shared_pursuit(self, shared_record: Dict) -> str:
        """v2.9: Create a shared pursuit record."""
        if "share_id" not in shared_record:
            shared_record["share_id"] = str(uuid.uuid4())
        shared_record["created_at"] = datetime.now(timezone.utc)
        shared_record["updated_at"] = datetime.now(timezone.utc)
        shared_record["is_active"] = True
        if "access_analytics" not in shared_record:
            shared_record["access_analytics"] = {
                "total_views": 0,
                "unique_visitors": 0,
                "last_viewed": None,
                "avg_time_on_page": 0.0,
                "sections_viewed": {},
                "referral_signups": 0
            }
        self.db.shared_pursuits.insert_one(shared_record)
        return shared_record["share_id"]

    def get_shared_pursuit(self, share_id: str) -> Optional[Dict]:
        """v2.9: Get a shared pursuit by ID."""
        return self.db.shared_pursuits.find_one({"share_id": share_id})

    def get_shared_pursuit_by_token(self, share_token: str) -> Optional[Dict]:
        """v2.9: Get a shared pursuit by share token."""
        return self.db.shared_pursuits.find_one({
            "share_token": share_token,
            "is_active": True
        })

    def get_pursuit_shares(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get all share links for a pursuit."""
        return list(self.db.shared_pursuits.find({"pursuit_id": pursuit_id}))

    def update_shared_pursuit(self, share_id: str, updates: Dict) -> bool:
        """v2.9: Update a shared pursuit record."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.shared_pursuits.update_one(
            {"share_id": share_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def increment_share_analytics(self, share_token: str, field: str,
                                   increment: int = 1) -> bool:
        """v2.9: Increment an analytics counter for a shared pursuit."""
        result = self.db.shared_pursuits.update_one(
            {"share_token": share_token},
            {
                "$inc": {f"access_analytics.{field}": increment},
                "$set": {
                    "access_analytics.last_viewed": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def revoke_share_link(self, share_token: str) -> bool:
        """v2.9: Revoke a share link."""
        result = self.db.shared_pursuits.update_one(
            {"share_token": share_token},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    # =========================================================================
    # v2.9: STAKEHOLDER RESPONSE OPERATIONS
    # =========================================================================

    def create_stakeholder_response(self, response_record: Dict) -> str:
        """v2.9: Create a stakeholder response from shared pursuit."""
        if "response_id" not in response_record:
            response_record["response_id"] = str(uuid.uuid4())
        response_record["submitted_at"] = datetime.now(timezone.utc)
        response_record["threaded_to_conversation"] = False
        response_record["updated_at"] = datetime.now(timezone.utc)
        self.db.stakeholder_responses.insert_one(response_record)
        return response_record["response_id"]

    def get_stakeholder_response(self, response_id: str) -> Optional[Dict]:
        """v2.9: Get a stakeholder response by ID."""
        return self.db.stakeholder_responses.find_one({"response_id": response_id})

    def get_pursuit_stakeholder_responses(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get all stakeholder responses for a pursuit."""
        return list(self.db.stakeholder_responses.find(
            {"pursuit_id": pursuit_id}
        ).sort("submitted_at", -1))

    def get_unthreaded_responses(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get responses not yet threaded to conversation."""
        return list(self.db.stakeholder_responses.find({
            "pursuit_id": pursuit_id,
            "threaded_to_conversation": False
        }))

    def update_stakeholder_response(self, response_id: str, updates: Dict) -> bool:
        """v2.9: Update a stakeholder response."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.stakeholder_responses.update_one(
            {"response_id": response_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def mark_response_threaded(self, response_id: str) -> bool:
        """v2.9: Mark a response as threaded to conversation."""
        return self.update_stakeholder_response(response_id, {
            "threaded_to_conversation": True,
            "threaded_at": datetime.now(timezone.utc)
        })

    # =========================================================================
    # v2.9: ARTIFACT COMMENTS OPERATIONS
    # =========================================================================

    def create_artifact_comment(self, comment_record: Dict) -> str:
        """v2.9: Create a comment on an artifact."""
        if "comment_id" not in comment_record:
            comment_record["comment_id"] = str(uuid.uuid4())
        comment_record["created_at"] = datetime.now(timezone.utc)
        comment_record["resolved"] = False
        self.db.artifact_comments.insert_one(comment_record)
        return comment_record["comment_id"]

    def get_artifact_comment(self, comment_id: str) -> Optional[Dict]:
        """v2.9: Get a comment by ID."""
        return self.db.artifact_comments.find_one({"comment_id": comment_id})

    def get_artifact_comments(self, artifact_id: str) -> List[Dict]:
        """v2.9: Get all comments for an artifact."""
        return list(self.db.artifact_comments.find(
            {"artifact_id": artifact_id}
        ).sort("created_at", 1))

    def get_pursuit_comments(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get all comments for a pursuit."""
        return list(self.db.artifact_comments.find(
            {"pursuit_id": pursuit_id}
        ).sort("created_at", -1))

    def resolve_artifact_comment(self, comment_id: str, resolver_id: str) -> bool:
        """v2.9: Mark a comment as resolved."""
        result = self.db.artifact_comments.update_one(
            {"comment_id": comment_id},
            {"$set": {
                "resolved": True,
                "resolved_by": resolver_id,
                "resolved_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    # =========================================================================
    # v2.9: ACTIVITY FEED OPERATIONS
    # =========================================================================

    def log_activity(self, pursuit_id: str, activity_type: str,
                     description: str, metadata: Dict = None) -> bool:
        """v2.9: Log an activity to pursuit's activity feed."""
        activity = {
            "timestamp": datetime.now(timezone.utc),
            "activity_type": activity_type,
            "description": description,
            "metadata": metadata or {}
        }
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$push": {"activity_feed": activity},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0

    def get_activity_feed(self, pursuit_id: str, limit: int = 50) -> List[Dict]:
        """v2.9: Get activity feed for a pursuit."""
        pursuit = self.get_pursuit(pursuit_id)
        if not pursuit:
            return []
        feed = pursuit.get("activity_feed", [])
        # Return most recent first, limited
        return sorted(feed, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    # =========================================================================
    # v2.9: RVE LITE - RISK DEFINITIONS OPERATIONS
    # =========================================================================

    def create_risk_definition(self, risk_record: Dict) -> str:
        """v2.9: Create a risk definition from fear conversion."""
        if "risk_id" not in risk_record:
            risk_record["risk_id"] = str(uuid.uuid4())
        risk_record["created_at"] = datetime.now(timezone.utc)
        risk_record["updated_at"] = datetime.now(timezone.utc)
        risk_record["validation_status"] = risk_record.get("validation_status", "NOT_STARTED")
        risk_record["linked_evidence"] = risk_record.get("linked_evidence", [])
        self.db.risk_definitions.insert_one(risk_record)
        return risk_record["risk_id"]

    def get_risk_definition(self, risk_id: str) -> Optional[Dict]:
        """v2.9: Get a risk definition by ID."""
        return self.db.risk_definitions.find_one({"risk_id": risk_id})

    def get_pursuit_risks(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get all risk definitions for a pursuit."""
        return list(self.db.risk_definitions.find({"pursuit_id": pursuit_id}))

    def get_risks_by_fear(self, fear_id: str) -> List[Dict]:
        """v2.9: Get risk definitions derived from a specific fear."""
        return list(self.db.risk_definitions.find({"source_fear_id": fear_id}))

    def update_risk_definition(self, risk_id: str, updates: Dict) -> bool:
        """v2.9: Update a risk definition."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.risk_definitions.update_one(
            {"risk_id": risk_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def link_evidence_to_risk(self, risk_id: str, evidence_id: str) -> bool:
        """v2.9: Link evidence to a risk definition."""
        result = self.db.risk_definitions.update_one(
            {"risk_id": risk_id},
            {
                "$push": {"linked_evidence": evidence_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0

    # =========================================================================
    # v2.9: RVE LITE - EVIDENCE PACKAGES OPERATIONS
    # =========================================================================

    def create_evidence_package(self, evidence_record: Dict) -> str:
        """v2.9: Create an evidence package for risk validation."""
        if "evidence_id" not in evidence_record:
            evidence_record["evidence_id"] = str(uuid.uuid4())
        evidence_record["created_at"] = datetime.now(timezone.utc)
        evidence_record["updated_at"] = datetime.now(timezone.utc)
        self.db.evidence_packages.insert_one(evidence_record)
        return evidence_record["evidence_id"]

    def get_evidence_package(self, evidence_id: str) -> Optional[Dict]:
        """v2.9: Get an evidence package by ID."""
        return self.db.evidence_packages.find_one({"evidence_id": evidence_id})

    def get_risk_evidence(self, risk_id: str) -> List[Dict]:
        """v2.9: Get all evidence packages for a risk."""
        return list(self.db.evidence_packages.find({"risk_id": risk_id}))

    def get_pursuit_evidence(self, pursuit_id: str) -> List[Dict]:
        """v2.9: Get all evidence packages for a pursuit."""
        return list(self.db.evidence_packages.find({"pursuit_id": pursuit_id}))

    def update_evidence_package(self, evidence_id: str, updates: Dict) -> bool:
        """v2.9: Update an evidence package."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.evidence_packages.update_one(
            {"evidence_id": evidence_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    # =========================================================================
    # v3.0.1: TIM - TIME ALLOCATIONS OPERATIONS
    # =========================================================================

    def create_time_allocation(self, allocation_record: Dict) -> str:
        """
        v3.0.1: Create a time allocation for a pursuit.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "allocation_id" not in allocation_record:
            allocation_record["allocation_id"] = str(uuid.uuid4())
        allocation_record["created_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        allocation_record["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.time_allocations.insert_one(allocation_record)
        return allocation_record["allocation_id"]

    def get_time_allocation(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.1: Get time allocation for a pursuit."""
        return self.db.time_allocations.find_one({"pursuit_id": pursuit_id})

    def update_time_allocation(self, pursuit_id: str, updates: Dict) -> bool:
        """v3.0.1: Update time allocation for a pursuit."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        result = self.db.time_allocations.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_time_allocation(self, pursuit_id: str) -> bool:
        """v3.0.1: Delete time allocation for a pursuit."""
        result = self.db.time_allocations.delete_one({"pursuit_id": pursuit_id})
        return result.deleted_count > 0 if hasattr(result, 'deleted_count') else False

    # =========================================================================
    # v3.0.1: TIM - TEMPORAL EVENTS OPERATIONS
    # =========================================================================

    def log_temporal_event(self, event_record: Dict) -> str:
        """
        v3.0.1: Log a temporal event in IKF-compatible format.
        All timestamps use ISO 8601 format: '2026-02-13T14:30:00Z'
        """
        if "event_id" not in event_record:
            event_record["event_id"] = str(uuid.uuid4())
        if "timestamp" not in event_record:
            event_record["timestamp"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.temporal_events.insert_one(event_record)
        return event_record["event_id"]

    def get_temporal_events(self, pursuit_id: str, event_type: str = None,
                            start_date: str = None, end_date: str = None,
                            limit: int = 100) -> List[Dict]:
        """
        v3.0.1: Query temporal events with optional filters.
        Timestamps should be ISO 8601 format strings.
        """
        query = {"pursuit_id": pursuit_id}
        if event_type:
            query["event_type"] = event_type
        if start_date:
            query["timestamp"] = query.get("timestamp", {})
            query["timestamp"]["$gte"] = start_date
        if end_date:
            if "timestamp" not in query:
                query["timestamp"] = {}
            query["timestamp"]["$lte"] = end_date

        return list(
            self.db.temporal_events.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )

    def get_recent_events(self, pursuit_id: str, limit: int = 50) -> List[Dict]:
        """v3.0.1: Get most recent temporal events for a pursuit."""
        return list(
            self.db.temporal_events.find({"pursuit_id": pursuit_id})
            .sort("timestamp", -1)
            .limit(limit)
        )

    def count_events_by_type(self, pursuit_id: str, event_type: str,
                              since: str = None) -> int:
        """v3.0.1: Count events of a specific type for velocity calculation."""
        query = {"pursuit_id": pursuit_id, "event_type": event_type}
        if since:
            query["timestamp"] = {"$gte": since}
        return len(list(self.db.temporal_events.find(query)))

    # =========================================================================
    # v3.0.1: TIM - VELOCITY METRICS OPERATIONS
    # =========================================================================

    def save_velocity_metric(self, metric_record: Dict) -> str:
        """v3.0.1: Save a velocity calculation."""
        if "metric_id" not in metric_record:
            metric_record["metric_id"] = str(uuid.uuid4())
        metric_record["calculated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.velocity_metrics.insert_one(metric_record)
        return metric_record["metric_id"]

    def get_latest_velocity(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.1: Get the most recent velocity calculation for a pursuit."""
        return self.db.velocity_metrics.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("calculated_at", -1)]
        )

    def get_velocity_history(self, pursuit_id: str, limit: int = 30) -> List[Dict]:
        """v3.0.1: Get velocity history for trend analysis."""
        return list(
            self.db.velocity_metrics.find({"pursuit_id": pursuit_id})
            .sort("calculated_at", -1)
            .limit(limit)
        )

    # =========================================================================
    # v3.0.1: TIM - PHASE TRANSITIONS OPERATIONS
    # =========================================================================

    def record_phase_transition(self, transition_record: Dict) -> str:
        """v3.0.1: Record a phase transition event."""
        if "transition_id" not in transition_record:
            transition_record["transition_id"] = str(uuid.uuid4())
        transition_record["transitioned_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.phase_transitions.insert_one(transition_record)
        return transition_record["transition_id"]

    def get_phase_history(self, pursuit_id: str) -> List[Dict]:
        """v3.0.1: Get chronological phase transition history."""
        return list(
            self.db.phase_transitions.find({"pursuit_id": pursuit_id})
            .sort("transitioned_at", 1)
        )

    def get_current_phase_record(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.1: Get the most recent (current) phase record."""
        return self.db.phase_transitions.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("transitioned_at", -1)]
        )

    def get_phase_duration(self, pursuit_id: str, phase: str) -> Optional[Dict]:
        """v3.0.1: Get duration spent in a specific phase."""
        history = self.get_phase_history(pursuit_id)
        for i, record in enumerate(history):
            if record.get("to_phase") == phase:
                start = record.get("transitioned_at")
                end = None
                if i + 1 < len(history):
                    end = history[i + 1].get("transitioned_at")
                return {
                    "phase": phase,
                    "started_at": start,
                    "ended_at": end,
                    "is_current": end is None
                }
        return None

    # =========================================================================
    # v3.9: MILESTONE OPERATIONS
    # =========================================================================

    def get_milestones(self, pursuit_id: str, status: str = None,
                       limit: int = 50) -> List[Dict]:
        """
        v3.9: Get milestones for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            status: Optional filter by status (pending, at_risk, completed, missed)
            limit: Maximum milestones to return

        Returns:
            List of milestones sorted by target_date ascending
        """
        query = {"pursuit_id": pursuit_id}
        if status:
            query["status"] = status

        results = list(
            self.db.pursuit_milestones.find(query, {"_id": 0})
            .sort("target_date", 1)
            .limit(limit)
        )
        return results

    def update_milestone_status(self, milestone_id: str, status: str,
                                 metadata: Dict = None) -> bool:
        """
        v3.9: Update a milestone's status.

        Args:
            milestone_id: Milestone ID
            status: New status (pending, at_risk, completed, missed)
            metadata: Optional additional metadata

        Returns:
            True if updated, False otherwise
        """
        update = {
            "$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat() + 'Z'
            }
        }
        if metadata:
            update["$set"]["status_metadata"] = metadata

        result = self.db.pursuit_milestones.update_one(
            {"milestone_id": milestone_id},
            update
        )
        return result.modified_count > 0

    def update_milestone(self, milestone_id: str, updates: Dict) -> bool:
        """
        v3.9: Update milestone fields.

        Args:
            milestone_id: Milestone ID
            updates: Dict of fields to update

        Returns:
            True if updated, False otherwise
        """
        updates["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        result = self.db.pursuit_milestones.update_one(
            {"milestone_id": milestone_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_milestone(self, milestone_id: str) -> bool:
        """
        v3.9: Delete a milestone.

        Args:
            milestone_id: Milestone ID

        Returns:
            True if deleted, False otherwise
        """
        result = self.db.pursuit_milestones.delete_one(
            {"milestone_id": milestone_id}
        )
        return result.deleted_count > 0

    # =========================================================================
    # v3.0.2: HEALTH SCORES OPERATIONS
    # =========================================================================

    def save_health_score(self, health_record: Dict) -> str:
        """
        v3.0.2: Save a health score calculation.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "score_id" not in health_record:
            health_record["score_id"] = str(uuid.uuid4())
        health_record["calculated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.health_scores.insert_one(health_record)
        return health_record["score_id"]

    def get_latest_health_score(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.2: Get the most recent health score for a pursuit."""
        return self.db.health_scores.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("calculated_at", -1)]
        )

    def get_health_score_history(self, pursuit_id: str, days: int = 30,
                                  limit: int = 100) -> List[Dict]:
        """v3.0.2: Get health score history for trend analysis."""
        return list(
            self.db.health_scores.find({"pursuit_id": pursuit_id})
            .sort("calculated_at", -1)
            .limit(limit)
        )

    def get_health_scores_by_zone(self, pursuit_id: str, zone: str) -> List[Dict]:
        """v3.0.2: Get health scores filtered by zone."""
        return list(
            self.db.health_scores.find({
                "pursuit_id": pursuit_id,
                "zone": zone
            }).sort("calculated_at", -1)
        )

    def get_crisis_triggered_scores(self, pursuit_id: str) -> List[Dict]:
        """v3.0.2: Get health scores where crisis was triggered."""
        return list(
            self.db.health_scores.find({
                "pursuit_id": pursuit_id,
                "crisis_triggered": True
            }).sort("calculated_at", -1)
        )

    # =========================================================================
    # v3.0.2: VALIDATION EXPERIMENTS OPERATIONS
    # =========================================================================

    def create_validation_experiment(self, experiment_record: Dict) -> str:
        """
        v3.0.2: Create a validation experiment.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "experiment_id" not in experiment_record:
            experiment_record["experiment_id"] = str(uuid.uuid4())
        experiment_record["created_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        experiment_record["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        experiment_record["status"] = experiment_record.get("status", "DESIGNED")
        self.db.validation_experiments.insert_one(experiment_record)
        return experiment_record["experiment_id"]

    def get_validation_experiment(self, experiment_id: str) -> Optional[Dict]:
        """v3.0.2: Get a validation experiment by ID."""
        return self.db.validation_experiments.find_one({"experiment_id": experiment_id})

    def get_pursuit_experiments(self, pursuit_id: str,
                                 status: str = None) -> List[Dict]:
        """v3.0.2: Get all experiments for a pursuit, optionally filtered by status."""
        query = {"pursuit_id": pursuit_id}
        if status:
            query["status"] = status
        return list(self.db.validation_experiments.find(query).sort("created_at", -1))

    def get_risk_experiments(self, risk_id: str) -> List[Dict]:
        """v3.0.2: Get all experiments for a specific risk."""
        return list(self.db.validation_experiments.find({"risk_id": risk_id}))

    def update_validation_experiment(self, experiment_id: str, updates: Dict) -> bool:
        """v3.0.2: Update a validation experiment."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        result = self.db.validation_experiments.update_one(
            {"experiment_id": experiment_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def start_experiment(self, experiment_id: str) -> bool:
        """v3.0.2: Mark an experiment as in progress."""
        return self.update_validation_experiment(experiment_id, {
            "status": "IN_PROGRESS",
            "start_date": datetime.now(timezone.utc).isoformat() + 'Z'
        })

    def complete_experiment(self, experiment_id: str, results: Dict = None) -> bool:
        """v3.0.2: Mark an experiment as complete."""
        updates = {
            "status": "COMPLETE",
            "completion_date": datetime.now(timezone.utc).isoformat() + 'Z'
        }
        if results:
            updates["results"] = results
        return self.update_validation_experiment(experiment_id, updates)

    def abandon_experiment(self, experiment_id: str, reason: str = None) -> bool:
        """v3.0.2: Mark an experiment as abandoned."""
        updates = {"status": "ABANDONED"}
        if reason:
            updates["abandon_reason"] = reason
        return self.update_validation_experiment(experiment_id, updates)

    def get_active_experiments(self, pursuit_id: str) -> List[Dict]:
        """v3.0.2: Get experiments that are designed or in progress."""
        return list(self.db.validation_experiments.find({
            "pursuit_id": pursuit_id,
            "status": {"$in": ["DESIGNED", "IN_PROGRESS"]}
        }))

    def get_completed_experiments(self, pursuit_id: str) -> List[Dict]:
        """v3.0.2: Get completed experiments."""
        return self.get_pursuit_experiments(pursuit_id, status="COMPLETE")

    # =========================================================================
    # v3.0.2: RISK DETECTIONS OPERATIONS
    # =========================================================================

    def save_risk_detection(self, detection_record: Dict) -> str:
        """
        v3.0.2: Save a risk detection result.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "detection_id" not in detection_record:
            detection_record["detection_id"] = str(uuid.uuid4())
        detection_record["detected_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.risk_detections.insert_one(detection_record)
        return detection_record["detection_id"]

    def get_latest_risk_detection(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.2: Get the most recent risk detection for a pursuit."""
        return self.db.risk_detections.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("detected_at", -1)]
        )

    def get_risk_detection_history(self, pursuit_id: str,
                                    limit: int = 30) -> List[Dict]:
        """v3.0.2: Get risk detection history."""
        return list(
            self.db.risk_detections.find({"pursuit_id": pursuit_id})
            .sort("detected_at", -1)
            .limit(limit)
        )

    def get_high_risk_detections(self, pursuit_id: str) -> List[Dict]:
        """v3.0.2: Get detections with HIGH or CRITICAL risk levels."""
        return list(
            self.db.risk_detections.find({
                "pursuit_id": pursuit_id,
                "overall_risk_level": {"$in": ["HIGH", "CRITICAL"]}
            }).sort("detected_at", -1)
        )

    # =========================================================================
    # v3.0.2: EXTENDED EVIDENCE PACKAGES OPERATIONS
    # =========================================================================

    def update_evidence_verdict(self, evidence_id: str, verdict: str,
                                 recommendation: str, confidence: float,
                                 rigor_score: float) -> bool:
        """
        v3.0.2: Update evidence package with three-zone assessment verdict.

        Args:
            evidence_id: Evidence package ID
            verdict: GREEN | YELLOW | RED
            recommendation: Advisory recommendation text
            confidence: Confidence in verdict (0-1)
            rigor_score: Quality of evidence (0-1)
        """
        return self.update_evidence_package(evidence_id, {
            "verdict": verdict,
            "recommendation": recommendation,
            "confidence": confidence,
            "rigor_score": rigor_score,
            "assessed_at": datetime.now(timezone.utc).isoformat() + 'Z'
        })

    def record_innovator_decision(self, evidence_id: str, decision: str,
                                   rationale: str = None,
                                   monitoring_plan: str = None) -> bool:
        """
        v3.0.2: Record innovator's decision after evidence assessment.

        Args:
            evidence_id: Evidence package ID
            decision: ACCEPTED | OVERRIDE_PROCEED | PIVOTED
            rationale: Required for OVERRIDE_PROCEED
            monitoring_plan: Optional plan for monitoring the risk
        """
        updates = {
            "innovator_decision": decision,
            "decision_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }
        if rationale:
            updates["decision_rationale"] = rationale
        if monitoring_plan:
            updates["monitoring_plan"] = monitoring_plan
        return self.update_evidence_package(evidence_id, updates)

    def get_evidence_by_verdict(self, pursuit_id: str, verdict: str) -> List[Dict]:
        """v3.0.2: Get evidence packages filtered by verdict."""
        return list(self.db.evidence_packages.find({
            "pursuit_id": pursuit_id,
            "verdict": verdict
        }))

    def get_override_evidence(self, pursuit_id: str) -> List[Dict]:
        """v3.0.2: Get evidence where innovator overrode recommendation."""
        return list(self.db.evidence_packages.find({
            "pursuit_id": pursuit_id,
            "innovator_decision": "OVERRIDE_PROCEED"
        }))

    # =========================================================================
    # v3.0.2: EXTENDED PURSUIT RVE STATUS OPERATIONS
    # =========================================================================

    def update_pursuit_rve_status(self, pursuit_id: str, rve_status: Dict) -> bool:
        """
        v3.0.2: Update pursuit with full RVE status.

        Args:
            pursuit_id: Pursuit ID
            rve_status: {
                "enabled": bool,
                "total_risks_identified": int,
                "risks_validated": int,
                "risks_green": int,
                "risks_yellow": int,
                "risks_red": int,
                "risks_unmitigated_proceeding": int,
                "pending_experiments": [ObjectId],
                "active_experiments": [ObjectId],
                "completed_experiments": [ObjectId],
                "last_validation_update": ISODate
            }
        """
        rve_status["last_validation_update"] = datetime.now(timezone.utc).isoformat() + 'Z'
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "rve_status": rve_status,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def get_pursuit_rve_status(self, pursuit_id: str) -> Optional[Dict]:
        """v3.0.2: Get RVE status for a pursuit."""
        pursuit = self.get_pursuit(pursuit_id)
        if not pursuit:
            return None
        return pursuit.get("rve_status", {
            "enabled": False,
            "total_risks_identified": 0,
            "risks_validated": 0,
            "risks_green": 0,
            "risks_yellow": 0,
            "risks_red": 0,
            "risks_unmitigated_proceeding": 0,
            "pending_experiments": [],
            "active_experiments": [],
            "completed_experiments": [],
            "last_validation_update": None
        })

    def increment_rve_zone_count(self, pursuit_id: str, zone: str) -> bool:
        """v3.0.2: Increment a zone count in RVE status."""
        field = f"rve_status.risks_{zone.lower()}"
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$inc": {field: 1},
                "$set": {
                    "rve_status.last_validation_update": datetime.now(timezone.utc).isoformat() + 'Z',
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    # =========================================================================
    # v3.0.3: PORTFOLIO ANALYTICS OPERATIONS
    # =========================================================================

    def save_portfolio_analytics(self, analytics_record: Dict) -> str:
        """
        v3.0.3: Save a portfolio analytics snapshot.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "snapshot_id" not in analytics_record:
            analytics_record["snapshot_id"] = str(uuid.uuid4())
        analytics_record["calculated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        self.db.portfolio_analytics.insert_one(analytics_record)
        return analytics_record["snapshot_id"]

    def get_latest_portfolio_analytics(self, user_id: str) -> Optional[Dict]:
        """v3.0.3: Get the most recent portfolio analytics for a user."""
        return self.db.portfolio_analytics.find_one(
            {"user_id": user_id},
            sort=[("calculated_at", -1)]
        )

    def get_portfolio_analytics_history(self, user_id: str,
                                         limit: int = 30) -> List[Dict]:
        """v3.0.3: Get portfolio analytics history for trend analysis."""
        return list(
            self.db.portfolio_analytics.find({"user_id": user_id})
            .sort("calculated_at", -1)
            .limit(limit)
        )

    def get_portfolio_analytics_by_date_range(self, user_id: str,
                                               start_date: str,
                                               end_date: str) -> List[Dict]:
        """v3.0.3: Get portfolio analytics within a date range."""
        return list(
            self.db.portfolio_analytics.find({
                "user_id": user_id,
                "calculated_at": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }).sort("calculated_at", -1)
        )

    # =========================================================================
    # v3.0.3: IKF CONTRIBUTIONS OPERATIONS
    # =========================================================================

    def create_ikf_contribution(self, contribution_record: Dict) -> str:
        """
        v3.0.3: Create an IKF contribution package.
        All timestamps use ISO 8601 format for IKF compatibility.
        """
        if "contribution_id" not in contribution_record:
            contribution_record["contribution_id"] = str(uuid.uuid4())
        contribution_record["created_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        contribution_record["status"] = "DRAFT"  # Always starts as DRAFT
        contribution_record["transmission_status"] = "NOT_SENT"  # Until v3.2
        self.db.ikf_contributions.insert_one(contribution_record)
        return contribution_record["contribution_id"]

    def get_ikf_contribution(self, contribution_id: str) -> Optional[Dict]:
        """v3.0.3: Get an IKF contribution by ID."""
        return self.db.ikf_contributions.find_one({"contribution_id": contribution_id})

    def get_user_ikf_contributions(self, user_id: str,
                                    status: str = None) -> List[Dict]:
        """v3.0.3: Get all IKF contributions for a user, optionally filtered by status."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return list(self.db.ikf_contributions.find(query).sort("created_at", -1))

    def get_pursuit_ikf_contributions(self, pursuit_id: str) -> List[Dict]:
        """v3.0.3: Get all IKF contributions for a pursuit."""
        return list(self.db.ikf_contributions.find({"pursuit_id": pursuit_id}))

    def get_pending_ikf_reviews(self, user_id: str) -> List[Dict]:
        """v3.0.3: Get IKF contributions awaiting review (DRAFT status)."""
        return self.get_user_ikf_contributions(user_id, status="DRAFT")

    def update_ikf_contribution(self, contribution_id: str, updates: Dict) -> bool:
        """v3.0.3: Update an IKF contribution."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat() + 'Z'
        result = self.db.ikf_contributions.update_one(
            {"contribution_id": contribution_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def approve_ikf_contribution(self, contribution_id: str,
                                  reviewer_id: str,
                                  review_notes: str = None) -> bool:
        """
        v3.0.3: Approve an IKF contribution for federation.
        Transitions status: DRAFT → REVIEWED → IKF_READY.
        """
        updates = {
            "status": "IKF_READY",
            "reviewed_by": reviewer_id,
            "approved_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }
        if review_notes:
            updates["review_notes"] = review_notes
        return self.update_ikf_contribution(contribution_id, updates)

    def reject_ikf_contribution(self, contribution_id: str,
                                 reviewer_id: str,
                                 rejection_reason: str) -> bool:
        """v3.0.3: Reject an IKF contribution."""
        return self.update_ikf_contribution(contribution_id, {
            "status": "REJECTED",
            "reviewed_by": reviewer_id,
            "rejection_reason": rejection_reason,
            "rejected_at": datetime.now(timezone.utc).isoformat() + 'Z'
        })

    def get_ikf_ready_contributions(self, user_id: str) -> List[Dict]:
        """v3.0.3: Get contributions ready for IKF federation."""
        return self.get_user_ikf_contributions(user_id, status="IKF_READY")

    def get_ikf_contribution_stats(self, user_id: str) -> Dict:
        """v3.0.3: Get IKF contribution statistics for a user."""
        all_contributions = self.get_user_ikf_contributions(user_id)
        stats = {
            "total": len(all_contributions),
            "draft": 0,
            "reviewed": 0,
            "ikf_ready": 0,
            "rejected": 0,
            "by_package_type": {}
        }
        for contrib in all_contributions:
            status = contrib.get("status", "DRAFT").lower()
            if status in stats:
                stats[status] += 1
            pkg_type = contrib.get("package_type", "unknown")
            stats["by_package_type"][pkg_type] = stats["by_package_type"].get(pkg_type, 0) + 1
        return stats

    # =========================================================================
    # v3.0.3: PORTFOLIO PRIORITY OPERATIONS
    # =========================================================================

    def update_pursuit_portfolio_priority(self, pursuit_id: str,
                                           priority: float) -> bool:
        """
        v3.0.3: Update pursuit portfolio priority (1.0-3.0 range).
        Used in weighted portfolio health calculation.
        """
        priority = max(1.0, min(3.0, priority))  # Clamp to valid range
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "portfolio_priority": priority,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def get_pursuit_portfolio_priority(self, pursuit_id: str) -> float:
        """v3.0.3: Get pursuit portfolio priority (default 1.0)."""
        pursuit = self.get_pursuit(pursuit_id)
        if not pursuit:
            return 1.0
        return pursuit.get("portfolio_priority", 1.0)

    def update_pursuit_ikf_status(self, pursuit_id: str, status: str) -> bool:
        """v3.0.3: Update pursuit IKF contribution status."""
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "ikf_contribution_status": status,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def update_pursuit_effectiveness_metrics(self, pursuit_id: str,
                                              metrics: Dict) -> bool:
        """v3.0.3: Update pursuit-level effectiveness metrics."""
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "effectiveness_metrics": metrics,
                "effectiveness_calculated_at": datetime.now(timezone.utc).isoformat() + 'Z',
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return result.modified_count > 0

    def get_user_active_pursuits_with_health(self, user_id: str) -> List[Dict]:
        """v3.0.3: Get all active pursuits with their latest health scores."""
        pursuits = self.get_user_pursuits(user_id, status="active")
        for pursuit in pursuits:
            health = self.get_latest_health_score(pursuit["pursuit_id"])
            pursuit["latest_health"] = health
        return pursuits

    # =========================================================================
    # v3.7.1: EMS PROCESS OBSERVATION ENGINE OPERATIONS
    # =========================================================================

    def create_observation(self, observation: Dict) -> str:
        """
        v3.7.1: Create a new process observation record.

        Args:
            observation: Observation document with pursuit_id, innovator_id,
                        observation_type, timestamp, sequence_number, details,
                        context, signal_weight

        Returns:
            The inserted observation ID
        """
        observation["created_at"] = datetime.now(timezone.utc)
        result = self.db.process_observations.insert_one(observation)
        return str(result.inserted_id)

    def get_observations_for_pursuit(
        self,
        pursuit_id: str,
        min_weight: float = 0.0,
        exclude_coaching: bool = False,
        observation_type: str = None
    ) -> List[Dict]:
        """
        v3.7.1: Retrieve all observations for a pursuit, ordered by sequence.

        Args:
            pursuit_id: The pursuit to get observations for
            min_weight: Minimum signal weight threshold (0.0-1.0)
            exclude_coaching: If True, exclude COACHING_INTERACTION observations
            observation_type: Filter to specific observation type

        Returns:
            List of observation documents ordered by sequence_number
        """
        query = {
            "pursuit_id": pursuit_id,
            "signal_weight": {"$gte": min_weight}
        }
        if exclude_coaching:
            query["observation_type"] = {"$ne": "COACHING_INTERACTION"}
        elif observation_type:
            query["observation_type"] = observation_type

        cursor = self.db.process_observations.find(query)
        return list(cursor.sort("sequence_number", 1))

    def get_observations_for_innovator(
        self,
        innovator_id: str,
        min_weight: float = 0.0
    ) -> List[Dict]:
        """
        v3.7.1: Retrieve all observations across all ad-hoc pursuits for an innovator.
        Used by Pattern Inference to find cross-pursuit patterns.

        Args:
            innovator_id: The innovator's ID
            min_weight: Minimum signal weight threshold

        Returns:
            List of observations ordered by pursuit_id, then sequence_number
        """
        cursor = self.db.process_observations.find({
            "innovator_id": innovator_id,
            "signal_weight": {"$gte": min_weight}
        })
        return list(cursor.sort([("pursuit_id", 1), ("sequence_number", 1)]))

    def get_observation_count(self, pursuit_id: str) -> int:
        """v3.7.1: Get total observation count for a pursuit."""
        return self.db.process_observations.count_documents({"pursuit_id": pursuit_id})

    def get_latest_observation(self, pursuit_id: str) -> Optional[Dict]:
        """v3.7.1: Get the most recent observation for a pursuit."""
        return self.db.process_observations.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("sequence_number", -1)]
        )

    def get_latest_non_temporal_observation(self, pursuit_id: str) -> Optional[Dict]:
        """
        v3.7.1: Get the most recent non-temporal-pattern observation.
        Used for temporal gap calculation.
        """
        return self.db.process_observations.find_one(
            {"pursuit_id": pursuit_id, "observation_type": {"$ne": "TEMPORAL_PATTERN"}},
            sort=[("timestamp", -1)]
        )

    def update_pursuit_adhoc_metadata(
        self,
        pursuit_id: str,
        metadata_updates: Dict
    ) -> bool:
        """
        v3.7.1: Update ad-hoc pursuit metadata fields.

        Args:
            pursuit_id: The pursuit to update
            metadata_updates: Dict of fields to update within adhoc_metadata

        Returns:
            True if update was successful
        """
        update_dict = {
            f"adhoc_metadata.{key}": value
            for key, value in metadata_updates.items()
        }
        update_dict["updated_at"] = datetime.now(timezone.utc)

        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": update_dict}
        )
        return result.modified_count > 0

    def increment_observation_count(self, pursuit_id: str) -> bool:
        """v3.7.1: Increment the observation count on a pursuit."""
        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$inc": {"adhoc_metadata.observation_count": 1}}
        )
        return result.modified_count > 0

    def get_adhoc_pursuit_count(self, innovator_id: str) -> int:
        """
        v3.7.1: Count completed ad-hoc pursuits for an innovator.
        Used for synthesis eligibility check.
        """
        return self.db.pursuits.count_documents({
            "user_id": innovator_id,
            "archetype": "ad_hoc",
            "adhoc_metadata.observation_status": {"$in": ["COMPLETED", "ACTIVE"]}
        })

    def get_synthesis_eligible_pursuits(self, innovator_id: str) -> List[Dict]:
        """
        v3.7.1: Get all ad-hoc pursuits that can contribute to synthesis.
        """
        cursor = self.db.pursuits.find({
            "user_id": innovator_id,
            "archetype": "ad_hoc",
            "adhoc_metadata.observation_status": "COMPLETED"
        })
        return list(cursor.sort("created_at", -1))

    def update_observation_status(
        self,
        pursuit_id: str,
        status: str
    ) -> bool:
        """
        v3.7.1: Update the observation status for an ad-hoc pursuit.

        Args:
            pursuit_id: The pursuit to update
            status: One of ACTIVE, PAUSED, COMPLETED, ABANDONED

        Returns:
            True if update was successful
        """
        update_data = {
            "adhoc_metadata.observation_status": status,
            "updated_at": datetime.now(timezone.utc)
        }

        if status == "COMPLETED":
            update_data["adhoc_metadata.observation_ended_at"] = datetime.now(timezone.utc)

        result = self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    # =========================================================================
    # v3.7.2: EMS PATTERN INFERENCE ENGINE OPERATIONS
    # =========================================================================

    def store_inference_result(
        self,
        innovator_id: str,
        inference_result: Dict
    ) -> str:
        """
        v3.7.2: Store a pattern inference result.

        Args:
            innovator_id: The innovator this inference is for
            inference_result: Full inference result from PatternInferenceEngine

        Returns:
            The inserted result ID
        """
        record = {
            "innovator_id": innovator_id,
            "inference_result": inference_result,
            "created_at": datetime.now(timezone.utc),
            "inference_timestamp": inference_result.get("inference_timestamp"),
            "pursuit_count": inference_result.get("pursuit_count", 0),
            "synthesis_ready": inference_result.get("synthesis_ready", False),
            "confidence_overall": inference_result.get("confidence", {}).get("overall", 0),
        }
        result = self.db.inference_results.insert_one(record)
        return str(result.inserted_id)

    def get_latest_inference_result(self, innovator_id: str) -> Optional[Dict]:
        """
        v3.7.2: Get the most recent inference result for an innovator.

        Returns:
            The inference_result dict or None if no results exist
        """
        record = self.db.inference_results.find_one(
            {"innovator_id": innovator_id},
            sort=[("created_at", -1)]
        )
        if record:
            return record.get("inference_result")
        return None

    def get_inference_history(
        self,
        innovator_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        v3.7.2: Get inference result history for an innovator.

        Returns:
            List of inference results, most recent first
        """
        cursor = self.db.inference_results.find({"innovator_id": innovator_id})
        results = list(cursor.sort("created_at", -1).limit(limit))
        return [r.get("inference_result", {}) for r in results]

    def store_generated_archetype(
        self,
        innovator_id: str,
        archetype_result: Dict
    ) -> str:
        """
        v3.7.2: Store a generated ADL archetype.

        Args:
            innovator_id: The innovator this archetype is for
            archetype_result: Full ADL generation result from ADLGenerator

        Returns:
            The inserted archetype ID
        """
        archetype = archetype_result.get("archetype", {})
        record = {
            "innovator_id": innovator_id,
            "archetype_id": archetype_result.get("archetype_id"),
            "archetype_result": archetype_result,
            "archetype_name": archetype.get("name") if archetype else None,
            "adl_version": archetype_result.get("adl_version"),
            "confidence_level": archetype.get("confidence_level", 0) if archetype else 0,
            "created_at": datetime.now(timezone.utc),
            "generated_at": archetype_result.get("generated_at"),
            "is_active": True,
        }
        result = self.db.generated_archetypes.insert_one(record)
        return str(result.inserted_id)

    def get_latest_archetype(self, innovator_id: str) -> Optional[Dict]:
        """
        v3.7.2: Get the most recent generated archetype for an innovator.

        Returns:
            The archetype_result dict or None if no archetypes exist
        """
        record = self.db.generated_archetypes.find_one(
            {"innovator_id": innovator_id, "is_active": True},
            sort=[("created_at", -1)]
        )
        if record:
            return record.get("archetype_result")
        return None

    def get_archetype_by_id(self, archetype_id: str) -> Optional[Dict]:
        """
        v3.7.2: Get an archetype by its archetype_id.

        Returns:
            The archetype_result dict or None if not found
        """
        record = self.db.generated_archetypes.find_one({"archetype_id": archetype_id})
        if record:
            return record.get("archetype_result")
        return None

    def deactivate_archetype(self, archetype_id: str) -> bool:
        """
        v3.7.2: Mark an archetype as inactive (superseded by newer version).

        Returns:
            True if update was successful
        """
        result = self.db.generated_archetypes.update_one(
            {"archetype_id": archetype_id},
            {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    def get_innovator_archetypes(
        self,
        innovator_id: str,
        include_inactive: bool = False
    ) -> List[Dict]:
        """
        v3.7.2: Get all archetypes for an innovator.

        Args:
            innovator_id: The innovator's ID
            include_inactive: If True, include deactivated archetypes

        Returns:
            List of archetype results, most recent first
        """
        query = {"innovator_id": innovator_id}
        if not include_inactive:
            query["is_active"] = True

        cursor = self.db.generated_archetypes.find(query)
        results = list(cursor.sort("created_at", -1))
        return [r.get("archetype_result", {}) for r in results]

    # =========================================================================
    # v3.7.3: EMS REVIEW SESSION OPERATIONS
    # =========================================================================

    def create_review_session(
        self,
        innovator_id: str,
        inference_result_id: str,
        original_draft: Dict
    ) -> str:
        """
        v3.7.3: Create a new review session for methodology validation.

        Args:
            innovator_id: The innovator's ID
            inference_result_id: Reference to the inference result being reviewed
            original_draft: The draft archetype as it was at session start

        Returns:
            The created session's ID as string
        """
        now = datetime.now(timezone.utc)
        doc = {
            "innovator_id": innovator_id,
            "inference_result_id": inference_result_id,
            "status": "INITIATED",
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "original_draft": original_draft,
            "refined_archetype": original_draft.copy(),  # Start with draft
            "coaching_exchanges": [],
            "refinements": [],
            "methodology_name": None,
            "methodology_description": None,
            "key_principles": [],
            "visibility": "PERSONAL",  # Default visibility
            "publish_approved": False,
            "publish_timestamp": None,
            "published_archetype_id": None,
        }
        result = self.db.review_sessions.insert_one(doc)
        return str(result.inserted_id)

    def get_review_session(self, session_id: str) -> Optional[Dict]:
        """
        v3.7.3: Get a review session by ID.
        """
        try:
            from bson import ObjectId
            result = self.db.review_sessions.find_one({"_id": ObjectId(session_id)})
        except Exception:
            result = self.db.review_sessions.find_one({"_id": session_id})

        if result:
            result["_id"] = str(result["_id"])
        return result

    def get_latest_review_session(self, innovator_id: str) -> Optional[Dict]:
        """
        v3.7.3: Get the most recent review session for an innovator.
        """
        result = self.db.review_sessions.find_one(
            {"innovator_id": innovator_id},
            sort=[("created_at", -1)]
        )
        if result:
            result["_id"] = str(result["_id"])
        return result

    def get_active_review_session(self, innovator_id: str) -> Optional[Dict]:
        """
        v3.7.3: Get the active (non-completed) review session for an innovator.
        """
        result = self.db.review_sessions.find_one(
            {
                "innovator_id": innovator_id,
                "status": {"$in": ["INITIATED", "IN_PROGRESS"]}
            },
            sort=[("created_at", -1)]
        )
        if result:
            result["_id"] = str(result["_id"])
        return result

    def update_review_session_status(
        self,
        session_id: str,
        status: str,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """
        v3.7.3: Update review session status.

        Args:
            session_id: The session ID
            status: New status (INITIATED | IN_PROGRESS | APPROVED | REJECTED | ABANDONED)
            completed_at: Completion timestamp (set automatically for terminal states)
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "status": status,
                "updated_at": now,
            }
        }

        # Set completed_at for terminal states
        if status in ("APPROVED", "REJECTED", "ABANDONED"):
            update["$set"]["completed_at"] = completed_at or now

        result = self.db.review_sessions.update_one({"_id": oid}, update)
        return result.modified_count > 0

    def add_coaching_exchange(
        self,
        session_id: str,
        role: str,
        content: str,
        context: str = "",
        phase_reference: str = ""
    ) -> bool:
        """
        v3.7.3: Add a coaching exchange to the review session.

        Args:
            session_id: The session ID
            role: "coach" or "innovator"
            content: The message content
            context: Which aspect of methodology being discussed
            phase_reference: Which phase being discussed, if applicable
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        now = datetime.now(timezone.utc)
        exchange = {
            "timestamp": now,
            "role": role,
            "content": content,
            "context": context,
            "phase_reference": phase_reference,
        }

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$push": {"coaching_exchanges": exchange},
                "$set": {"updated_at": now, "status": "IN_PROGRESS"}
            }
        )
        return result.modified_count > 0

    def add_refinement(
        self,
        session_id: str,
        action: str,
        target: str,
        before: str,
        after: str,
        innovator_rationale: str = ""
    ) -> bool:
        """
        v3.7.3: Add a refinement to the review session audit trail.

        Args:
            session_id: The session ID
            action: Refinement action type
            target: What was modified
            before: Previous value
            after: New value
            innovator_rationale: Why the change was made
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        now = datetime.now(timezone.utc)
        refinement = {
            "timestamp": now,
            "action": action,
            "target": target,
            "before": before,
            "after": after,
            "innovator_rationale": innovator_rationale,
        }

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$push": {"refinements": refinement},
                "$set": {"updated_at": now}
            }
        )
        return result.modified_count > 0

    def update_refined_archetype(
        self,
        session_id: str,
        refined_archetype: Dict
    ) -> bool:
        """
        v3.7.3: Update the refined archetype in a review session.
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$set": {
                    "refined_archetype": refined_archetype,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def set_methodology_details(
        self,
        session_id: str,
        name: str = None,
        description: str = None,
        key_principles: List[str] = None,
        visibility: str = None
    ) -> bool:
        """
        v3.7.3: Set methodology naming and visibility details.
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        updates = {"updated_at": datetime.now(timezone.utc)}
        if name is not None:
            updates["methodology_name"] = name
        if description is not None:
            updates["methodology_description"] = description
        if key_principles is not None:
            updates["key_principles"] = key_principles
        if visibility is not None:
            updates["visibility"] = visibility

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {"$set": updates}
        )
        return result.modified_count > 0

    def approve_publication(
        self,
        session_id: str,
        published_archetype_id: str
    ) -> bool:
        """
        v3.7.3: Mark review session as approved and link to published archetype.
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        now = datetime.now(timezone.utc)
        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "APPROVED",
                    "publish_approved": True,
                    "publish_timestamp": now,
                    "published_archetype_id": published_archetype_id,
                    "completed_at": now,
                    "updated_at": now,
                }
            }
        )
        return result.modified_count > 0

    def get_review_history(
        self,
        innovator_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        v3.7.3: Get review session history for an innovator.
        """
        cursor = self.db.review_sessions.find(
            {"innovator_id": innovator_id}
        ).sort("created_at", -1).limit(limit)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def get_inferred_archetypes(
        self,
        innovator_id: str,
        status: str = None
    ) -> List[Dict]:
        """
        v3.7.3: Get inferred archetypes for an innovator.

        Args:
            innovator_id: The innovator's ID
            status: Optional status filter (INFERRED, REVIEWED, PUBLISHED)

        Returns:
            List of inferred archetype documents
        """
        query = {"innovator_id": innovator_id}
        if status:
            query["status"] = status

        cursor = self.db.generated_archetypes.find(query).sort("generated_at", -1)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Flatten archetype_result for easier access
            if "archetype_result" in doc:
                result = doc["archetype_result"]
                doc["archetype_id"] = result.get("archetype_id", doc.get("archetype_id"))
                doc["confidence"] = result.get("archetype", {}).get("confidence_level", 0.5)
                doc["inferred_phases"] = result.get("archetype", {}).get("phases", [])
                doc["inferred_transitions"] = result.get("archetype", {}).get("transitions", [])
                doc["inferred_activities"] = []
                for phase in doc["inferred_phases"]:
                    doc["inferred_activities"].extend(phase.get("activities", []))
                doc["inferred_tools"] = result.get("archetype", {}).get("tools", [])
                doc["inferred_at"] = result.get("generated_at", doc.get("generated_at"))
                doc["similar_archetypes"] = result.get("synthesis_metadata", {}).get("similar_archetypes", [])
            results.append(doc)
        return results

    def get_inferred_archetype(
        self,
        archetype_id: str
    ) -> Optional[Dict]:
        """
        v3.7.3: Get a single inferred archetype by ID.

        Args:
            archetype_id: The archetype ID

        Returns:
            The inferred archetype document or None
        """
        doc = self.db.generated_archetypes.find_one({"archetype_id": archetype_id})
        if not doc:
            return None

        doc["_id"] = str(doc["_id"])
        # Flatten archetype_result for easier access
        if "archetype_result" in doc:
            result = doc["archetype_result"]
            doc["archetype_id"] = result.get("archetype_id", doc.get("archetype_id"))
            doc["confidence"] = result.get("archetype", {}).get("confidence_level", 0.5)
            doc["inferred_phases"] = result.get("archetype", {}).get("phases", [])
            doc["inferred_transitions"] = result.get("archetype", {}).get("transitions", [])
            doc["inferred_activities"] = []
            for phase in doc["inferred_phases"]:
                doc["inferred_activities"].extend(phase.get("activities", []))
            doc["inferred_tools"] = result.get("archetype", {}).get("tools", [])
            doc["inferred_at"] = result.get("generated_at", doc.get("generated_at"))
            doc["pursuit_ids"] = result.get("source", {}).get("pursuit_ids", [])
            doc["similar_archetypes"] = result.get("synthesis_metadata", {}).get("similar_archetypes", [])
        return doc

    def update_review_session_stage(
        self,
        session_id: str,
        stage: str
    ) -> bool:
        """
        v3.7.3: Update the current review stage.

        Args:
            session_id: The session ID
            stage: The new stage (REVIEWING_PHASES, REVIEWING_TRANSITIONS, etc.)
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$set": {
                    "review_stage": stage,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    def update_review_session_phase_index(
        self,
        session_id: str,
        phase_index: int
    ) -> bool:
        """
        v3.7.3: Update the current phase index in review.

        Args:
            session_id: The session ID
            phase_index: The current phase being reviewed
        """
        try:
            from bson import ObjectId
            oid = ObjectId(session_id)
        except Exception:
            oid = session_id

        result = self.db.review_sessions.update_one(
            {"_id": oid},
            {
                "$set": {
                    "current_phase_index": phase_index,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0


class InMemoryDB:
    """
    Pure in-memory database fallback when mongomock is not available.
    Mimics MongoDB interface for basic operations.
    """

    def __init__(self):
        self._collections = {name: InMemoryCollection() for name in COLLECTIONS}

    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if name in self._collections:
            return self._collections[name]
        raise AttributeError(f"Collection '{name}' not found")

    def list_collection_names(self):
        return list(self._collections.keys())

    def create_collection(self, name):
        if name not in self._collections:
            self._collections[name] = InMemoryCollection()


class InMemoryCollection:
    """In-memory collection that mimics MongoDB collection interface."""

    def __init__(self):
        self._documents = []

    def insert_one(self, doc):
        doc = dict(doc)
        if '_id' not in doc:
            doc['_id'] = str(uuid.uuid4())
        self._documents.append(doc)
        return type('Result', (), {'inserted_id': doc['_id']})()

    def find_one(self, query=None, sort=None):
        results = list(self._find(query))
        if sort:
            # Handle sort parameter (list of tuples)
            for key, direction in reversed(sort):
                results.sort(key=lambda x: x.get(key, ''), reverse=(direction == -1))
        return results[0] if results else None

    def find(self, query=None):
        return InMemoryCursor(list(self._find(query)))

    def _find(self, query=None):
        if query is None:
            return iter(self._documents)
        for doc in self._documents:
            if self._matches(doc, query):
                yield doc

    def _matches(self, doc, query):
        """Check if document matches query. v2.5: Enhanced operator support."""
        for key, value in query.items():
            # Handle nested key paths like "problem_context.domain"
            doc_value = self._get_nested(doc, key)

            # v2.5: Handle query operators
            if isinstance(value, dict):
                if "$ne" in value:
                    if doc_value == value["$ne"]:
                        return False
                    continue
                if "$in" in value:
                    # Value must be in the list
                    # Also handles case where doc_value is a list (any match)
                    target_list = value["$in"]
                    if isinstance(doc_value, list):
                        if not any(v in target_list for v in doc_value):
                            return False
                    elif doc_value not in target_list:
                        return False
                    continue
                if "$gte" in value:
                    if doc_value is None or doc_value < value["$gte"]:
                        return False
                    continue
                if "$gt" in value:
                    if doc_value is None or doc_value <= value["$gt"]:
                        return False
                    continue
                if "$lte" in value:
                    if doc_value is None or doc_value > value["$lte"]:
                        return False
                    continue
                if "$lt" in value:
                    if doc_value is None or doc_value >= value["$lt"]:
                        return False
                    continue

            # Simple equality check
            if doc_value != value:
                return False
        return True

    def _get_nested(self, doc, key):
        """Get a nested key value like 'problem_context.domain'."""
        if '.' not in key:
            return doc.get(key)

        parts = key.split('.')
        current = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def update_one(self, query, update, upsert=False, sort=None):
        doc = self.find_one(query, sort=sort)
        if doc:
            if '$set' in update:
                for key, value in update['$set'].items():
                    self._set_nested(doc, key, value)
            if '$push' in update:
                for key, value in update['$push'].items():
                    if key not in doc:
                        doc[key] = []
                    doc[key].append(value)
            return type('Result', (), {'modified_count': 1, 'acknowledged': True})()
        elif upsert:
            new_doc = dict(query)
            if '$set' in update:
                new_doc.update(update['$set'])
            self.insert_one(new_doc)
            return type('Result', (), {'modified_count': 0, 'upserted_id': new_doc.get('_id'), 'acknowledged': True})()
        return type('Result', (), {'modified_count': 0, 'acknowledged': True})()

    def _set_nested(self, doc, key, value):
        """Set a nested key like 'vision_elements.problem_statement'."""
        parts = key.split('.')
        current = doc
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value


class InMemoryCursor:
    """Cursor for in-memory collection results."""

    def __init__(self, documents):
        self._documents = documents

    def sort(self, key, direction=1):
        self._documents.sort(key=lambda x: x.get(key, ''), reverse=(direction == -1))
        return self

    def limit(self, n):
        self._documents = self._documents[:n]
        return self

    def __iter__(self):
        return iter(self._documents)

    def __list__(self):
        return self._documents


# Global database instance
db = Database()
