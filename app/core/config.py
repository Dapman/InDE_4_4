"""
InDE MVP v3.4 - Configuration
Innovation Development Environment - "Enterprise Intelligence & Coaching Convergence"

v3.4 transforms InDE into an enterprise-grade innovation intelligence system with:
- Org-Level Portfolio Dashboard: Aggregate analytics across all org pursuits
- Coaching Convergence Protocol: Four-phase model (Exploration→Consolidation→Commitment→Handoff)
- IDTFS: Innovator Discovery & Team Formation Service with 6-pillar assessment
- Advanced RBAC & Governance: Custom roles, policy-based access control
- Methodology Expansion: Design Thinking + Stage-Gate archetypes
- SOC 2 Audit Infrastructure: Immutable audit log with event correlation

NEW IN v3.4:
- Org-Level Portfolio Dashboard: 7-panel enterprise intelligence view
- Coaching Convergence Protocol: Signal detection, criteria evaluation, outcome capture
- IDTFS: Six-pillar expertise assessment for intelligent team formation
- Advanced RBAC: Custom role definitions, policy-based access control
- Methodology Archetypes: Design Thinking + Stage-Gate with coaching configs
- SOC 2 Audit Pipeline: Immutable audit events via Redis Streams
- Convergence-Aware ODICM: Coaching adapts to convergence phase
- Org Intelligence Context: Org-level patterns in coaching prompts

Building on v3.3 Team Innovation & Shared Pursuits:
- Organization Entity Model: Users belong to organizations with role-based access
- Shared Pursuit Workspaces: Team collaboration with owner/editor/viewer roles
- Team Scaffolding Engine: Element attribution, gap analysis, expertise matching
- Activity Streams & Notifications: Redis-powered real-time collaboration events
- Team-Aware ODICM: Collaborative coaching with privacy boundaries
- Organization-Scoped IKF: Three-tier knowledge hierarchy (personal → org → federated)
- RBAC Middleware: Two-level authorization (org role + pursuit role)
- Practice Pursuit Support: 50% maturity weighting, IKF federation exclusion

Building on v3.2 Federation Foundation:
- Docker Compose Deployment: 5-container architecture (app, db, llm-gateway, events, ikf)
- FastAPI Backend: API-first server with organization and teams endpoints
- Redis Streams Event Bus: Consumer groups and dead letter queue
- IKF Container: Federation protocol (simulation mode)

Building on v3.0.3 Analytics & Synthesis:
- Portfolio Intelligence Engine: Cross-pursuit analytics with weighted health
- Cross-Pursuit Comparator: Benchmarking with percentile rankings
- Innovation Effectiveness Scorecard: 7 organizational metrics
- SILR Temporal Enrichment: 8 visualization types in reports
- IKF Contribution Preparation: 4-stage generalization with human review

Building on v3.0.2 Intelligence Layer:
- Pursuit Health Monitor: Real-time health scoring (0-100) with 5 health zones
- Temporal Pattern Intelligence: Enriched IML pattern matching with temporal signals
- Predictive Guidance Engine: Forward-looking predictions based on historical patterns
- Full RVE: Experiment-driven decision support system
- Temporal Risk Detection: Short/medium/long-term risk identification

Building on previous versions (v3.0.1 - v2.5):
- Time Allocation Engine, Velocity Tracker, Phase Manager
- Report Distribution, Pursuit Sharing, Stakeholder Response Capture
- Living Snapshot Reports, Portfolio Analytics Reports
- Terminal State Detection, Retrospective Orchestrator
- Pattern Engine, Advanced Scaffolding, Adaptive Interventions
"""

import os

# =============================================================================
# VERSION INFORMATION
# =============================================================================
VERSION = "4.4.0"
VERSION_NAME = "The Learning Engine"
VERSION_DATE = "March 2026"

# =============================================================================
# API CONFIGURATION (v3.1: Routes through LLM Gateway)
# =============================================================================
# Legacy direct API key - kept for backward compatibility
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# v3.1: LLM Gateway URL (used inside Docker network)
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8080")

# =============================================================================
# AUTHENTICATION CONFIGURATION (v3.1 NEW)
# =============================================================================
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# =============================================================================
# ADMIN CONFIGURATION (v3.14 NEW)
# =============================================================================
# Email address for the admin user - automatically assigned admin role on startup
# and on registration. Leave empty to disable auto-assignment.
INDE_ADMIN_EMAIL = os.getenv("INDE_ADMIN_EMAIL", "")

# =============================================================================
# DEMO MODE (v4.2 NEW)
# =============================================================================
# Controls availability of the Demo User account.
# ACTIVE:   Demo login is available — users can try InDE without registering.
# INACTIVE: Demo login is disabled — users must register or sign in.
# Set to INACTIVE for production beta testing to track real user participation.
DEMO_MODE = os.getenv("DEMO_MODE", "ACTIVE").upper()
DEMO_MODE_ACTIVE = DEMO_MODE == "ACTIVE"

# =============================================================================
# RATE LIMITING CONFIGURATION (v3.15 NEW)
# =============================================================================
# Per-user coaching rate limit (requests per 60-second sliding window)
INDE_COACHING_RATE_LIMIT = int(os.getenv("INDE_COACHING_RATE_LIMIT", "30"))

# Per-IP authentication rate limit (attempts per window)
INDE_AUTH_RATE_LIMIT = int(os.getenv("INDE_AUTH_RATE_LIMIT", "10"))

# Authentication rate limit window duration (seconds)
INDE_AUTH_RATE_LIMIT_WINDOW = int(os.getenv("INDE_AUTH_RATE_LIMIT_WINDOW", "300"))

# =============================================================================
# DATABASE CONFIGURATION (v3.1: Supports Docker Compose)
# =============================================================================
# MONGO_URI is the Docker Compose name, MONGODB_URI is the legacy name
MONGODB_URI = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "inde")

# Use MongoDB by default, fall back to in-memory only if MongoDB unavailable
# Set USE_MONGOMOCK=True via environment variable to force demo mode
USE_MONGOMOCK = os.getenv("USE_MONGOMOCK", "").lower() in ("true", "1", "yes")

# 56 Core Collections (v3.7.3: added review_sessions for EMS Review Interface)
COLLECTIONS = [
    "users",
    "pursuits",
    "scaffolding_states",
    "artifacts",
    "conversation_history",
    "intervention_history",
    "patterns",
    "system_config",
    "user_engagement_metrics",      # v2.5: Track user engagement for adaptive cooldowns
    "pattern_effectiveness",        # v2.5: Track pattern application outcomes
    "stakeholder_feedback",         # v2.6: Track stakeholder feedback and support
    # v2.7: Terminal Intelligence collections
    "retrospectives",               # Terminal state learning capture
    "learning_patterns",            # Proto-patterns extracted from retros
    "fear_resolutions",             # Track which fears materialized
    "retrospective_conversations",  # Retro dialogue history
    "terminal_reports",             # SILR and other generated reports
    "outcome_artifacts",            # Competitive intel, success patterns, etc.
    # v2.8: Report Intelligence collections
    "living_snapshot_reports",      # Progress reports for active pursuits
    "portfolio_analytics_reports",  # Cross-pursuit analytics reports
    "report_templates",             # Custom and system report templates
    # v2.9: Social Intelligence collections
    "report_distributions",         # Track report email/link distribution
    "shared_pursuits",              # Shareable pursuit links and access analytics
    "stakeholder_responses",        # Feedback from shared pursuit views
    "artifact_comments",            # Comments on artifacts for collaboration
    # v2.9: RVE Lite collections
    "risk_definitions",             # Fear-to-risk conversions
    "evidence_packages",            # Validation evidence for risks
    # v3.0.1: Temporal Intelligence Module (TIM) collections
    "time_allocations",             # Phase-level time distribution
    "temporal_events",              # Event stream with ISO 8601 timestamps
    "velocity_metrics",             # Progress velocity tracking
    "phase_transitions",            # Phase change history
    # v3.0.2: Intelligence Layer collections
    "health_scores",                # Pursuit health score history
    "validation_experiments",       # Full RVE experiment tracking
    "risk_detections",              # Temporal risk detection results
    # v3.0.3: Analytics & Synthesis collections
    "portfolio_analytics",          # Portfolio-level analytics snapshots
    "ikf_contributions",            # IKF-ready contribution packages
    # v3.1: Platform Foundation collections
    "sessions",                     # JWT session tracking with refresh tokens
    "maturity_events",              # Behavioral events for maturity calculation
    "crisis_sessions",              # Crisis mode records and interventions
    "gii_profiles",                 # Global Innovator Identifier records
    "domain_events",                # Persistent event log for audit and v3.2 migration
    "coaching_sessions",            # Coaching session tracking with user association
    # v3.2: Pending state collections for request persistence
    "pending_artifacts",            # Pending artifact generation requests
    "pending_regenerations",        # Pending artifact regeneration requests
    "pending_terminal_confirmations",  # Pending terminal state confirmations
    # v3.4: Enterprise Intelligence collections (NEW)
    "audit_events",                 # Immutable audit log (append-only, SOC 2 ready)
    "convergence_sessions",         # Convergence state per coaching session
    "innovator_profiles",           # IDTFS external profile + availability
    "vouching_records",             # IDTFS directional endorsements
    "formation_recommendations",    # IDTFS discovery results + outcomes
    "composition_patterns",         # IML/IKF team configuration patterns
    "custom_roles",                 # Organization-defined roles
    "access_policies",              # Organization-wide policy configuration
    # v3.7.1: EMS Process Observation Engine collections
    "process_observations",         # Behavioral observations during ad-hoc pursuits
    # v3.7.2: EMS Pattern Inference Engine collections
    "inference_results",            # Pattern inference results per innovator
    "generated_archetypes",         # ADL-generated methodology archetypes
    # v3.7.3: EMS Innovator Review Interface collections (NEW)
    "review_sessions",              # Coaching-assisted methodology review sessions
]

# =============================================================================
# SCAFFOLDING CONFIGURATION
# =============================================================================

# The 20 Critical Elements organized by artifact type (v2.2 baseline)
CRITICAL_ELEMENTS = {
    # Vision Elements (8)
    "vision": [
        "problem_statement",      # What problem exists?
        "target_user",            # Who has this problem?
        "current_situation",      # How do they deal with it now?
        "pain_points",            # What's painful about current state?
        "solution_concept",       # What's the proposed solution?
        "value_proposition",      # Why would anyone want this?
        "differentiation",        # What makes this different?
        "success_criteria"        # How do we know if it works?
    ],

    # Fear Elements (6)
    "fears": [
        "capability_fears",       # Can we build this?
        "market_fears",           # Will anyone want this?
        "resource_fears",         # Do we have what we need?
        "timing_fears",           # Is now the right time?
        "competition_fears",      # What about competitors?
        "personal_fears"          # What am I personally worried about?
    ],

    # Hypothesis Elements (6)
    "hypothesis": [
        "assumption_statement",   # What are we assuming?
        "testable_prediction",    # What do we predict will happen?
        "test_method",            # How can we test this?
        "success_metric",         # How do we measure success?
        "failure_criteria",       # When do we admit we're wrong?
        "learning_plan"           # What do we do with results?
    ]
}

# v2.3: Important Tier Elements (20 additional elements)
IMPORTANT_ELEMENTS = {
    # Vision Enhancement (5)
    "vision_enhanced": [
        "alternative_solutions",      # What else have people tried?
        "success_metrics",            # How will we measure success?
        "timeline_expectations",      # When do we need this?
        "resource_requirements",      # What will this take to build?
        "key_assumptions"             # What must be true for this to work?
    ],

    # User Understanding Enhancement (4)
    "user_enhanced": [
        "user_behaviors",             # How do users currently behave?
        "user_context",               # Where/when does this problem occur?
        "user_segment_size",          # How many people have this problem?
        "willingness_to_pay"          # Will users pay? How much?
    ],

    # Solution Enhancement (4)
    "solution_enhanced": [
        "technical_feasibility",      # Can we actually build this?
        "regulatory_constraints",     # Legal/compliance issues?
        "partnerships_needed",        # Who do we need to work with?
        "distribution_channel"        # How do we reach users?
    ],

    # Fear/Risk Enhancement (3)
    "risk_enhanced": [
        "technical_risks",            # What could go wrong technically?
        "market_risks",               # What if market doesn't want this?
        "resource_risks"              # What if we run out of time/money?
    ],

    # Learning Enhancement (4)
    "learning_enhanced": [
        "stakeholder_feedback",       # What have stakeholders said?
        "competitive_analysis",       # What do competitors offer?
        "early_signals",              # Any early validation data?
        "pivot_indicators"            # What would make us change course?
    ]
}

# =============================================================================
# v2.5: IMPORTANT ELEMENTS (20 additional elements for richer tracking)
# =============================================================================
# These elements enhance pattern matching and artifact quality but are not
# required for basic artifact generation (unlike CRITICAL_ELEMENTS).
V25_IMPORTANT_ELEMENTS = [
    "competitive_landscape",      # Who else is solving this
    "business_model",             # How will this make money
    "cost_structure",             # What will this cost to build/run
    "revenue_model",              # How will revenue be generated
    "go_to_market",               # How will users discover this
    "partnerships",               # Who needs to collaborate
    "regulatory_concerns",        # Legal/compliance issues
    "technical_feasibility",      # Can this be built
    "resource_requirements",      # What resources are needed
    "team_capabilities",          # What skills exist/needed
    "market_timing",              # Is now the right time
    "adoption_barriers",          # What prevents user adoption
    "switching_costs",            # How hard to change from current
    "network_effects",            # Does value increase with users
    "scalability_constraints",    # What limits growth
    "exit_strategy",              # How might this end/pivot
    "stakeholder_alignment",      # Who supports/opposes this
    "cultural_fit",               # Does this match org culture
    "risk_tolerance",             # How much uncertainty acceptable
    "early_validation"            # What early signals exist
]

# v2.3: Teleological Dimensions (8 elements for methodology inference)
TELEOLOGICAL_DIMENSIONS = [
    "purpose_type",               # problem-solving, opportunity-creation, compliance, process-improvement
    "beneficiary",                # end-users, market, organization, society
    "uncertainty_level",          # 0.0-1.0 confidence score (how much is unknown)
    "value_creation_mode",        # efficiency, experience, safety, knowledge
    "resource_context",           # time/capital/expertise constraints
    "org_context",                # startup, enterprise, public-sector, academic
    "innovation_type",            # incremental, architectural, radical, disruptive
    "maturity_state"              # spark, hypothesis, validated, scaling
]

# v2.3: Keyword indicators for teleological extraction
TELEOLOGICAL_INDICATORS = {
    "purpose_type": {
        "problem_solving": ["problem", "pain", "struggle", "difficulty", "challenge", "issue", "broken", "frustrating"],
        "opportunity_creation": ["opportunity", "market", "could", "potential", "gap", "white space", "new market"],
        "compliance": ["regulation", "requirement", "must", "mandate", "compliance", "legal", "policy", "law"],
        "process_improvement": ["inefficient", "optimize", "improve", "streamline", "faster", "better", "automate"]
    },
    "beneficiary": {
        "end_users": ["users", "customers", "people", "patients", "students", "children", "consumers", "individuals"],
        "market": ["buyers", "companies", "businesses", "enterprises", "clients", "b2b", "organizations"],
        "organization": ["our team", "employees", "internal", "stakeholders", "department", "our company"],
        "society": ["community", "public", "everyone", "society", "citizens", "population", "world"]
    },
    "value_creation_mode": {
        "efficiency": ["faster", "cheaper", "automate", "reduce cost", "save time", "streamline", "optimize"],
        "experience": ["better experience", "easier", "more enjoyable", "delightful", "engaging", "intuitive"],
        "safety": ["safer", "protect", "prevent", "secure", "reduce risk", "avoid danger", "safe"],
        "knowledge": ["learn", "educate", "understand", "discover", "inform", "aware", "insight"]
    },
    "org_context": {
        "startup": ["we're building", "my startup", "founding", "seed", "early stage", "co-founder", "bootstrapping"],
        "enterprise": ["company policy", "corporate", "internal approval", "stakeholders", "division", "enterprise"],
        "public_sector": ["government", "public", "citizens", "policy", "regulation", "agency", "municipal"],
        "academic": ["research", "university", "study", "hypothesis", "experiment", "thesis", "professor"]
    },
    "innovation_type": {
        "incremental": ["improve", "enhance", "better version", "upgrade", "refine", "iteration", "next version"],
        "architectural": ["combine", "integrate", "platform", "ecosystem", "modular", "system of"],
        "radical": ["completely new", "never existed", "revolutionary", "breakthrough", "first ever", "disrupt"],
        "disruptive": ["cheaper alternative", "democratize", "accessible", "lower cost", "simpler"]
    },
    "maturity_state": {
        "spark": ["just thinking", "initial idea", "wondering", "what if", "concept", "brainstorming"],
        "hypothesis": ["believe", "think it will", "assumption", "predict", "expect", "should work"],
        "validated": ["tested", "proven", "customers said", "data shows", "results", "evidence"],
        "scaling": ["growing", "expanding", "more users", "next market", "scale", "growth"]
    }
}

# Readiness threshold for artifact generation (75% completeness)
READINESS_THRESHOLD = 0.75

# Intent detection confidence threshold for auto-creating pursuits
INTENT_CONFIDENCE_THRESHOLD = 0.7

# =============================================================================
# INTERVENTION CONFIGURATION
# =============================================================================

# 10 Moment Types with cooldowns and priorities (v2.7: added TERMINAL_TRANSITION)
MOMENT_TYPES = {
    "CRITICAL_GAP": {
        "priority": 1,
        "cooldown_minutes": 15,
        "description": "Missing essential information that blocks progress"
    },
    "READY_TO_FORMALIZE": {
        "priority": 2,
        "cooldown_minutes": 20,
        "description": "Enough info to create formal artifact"
    },
    "FEAR_OPPORTUNITY": {
        "priority": 3,
        "cooldown_minutes": 30,
        "description": "User expressed worry/concern worth capturing"
    },
    "NATURAL_TRANSITION": {
        "priority": 4,
        "cooldown_minutes": 45,
        "description": "Natural point to shift focus"
    },
    "ARTIFACT_DRIFT": {
        "priority": 3,
        "cooldown_minutes": 30,
        "description": "Artifact is stale due to evolved scaffolding elements"
    },
    # v2.5: New intervention types for Pattern Intelligence
    "PATTERN_RELEVANT": {
        "priority": 3,
        "cooldown_minutes": 25,
        "description": "v2.5: Historical pattern matches current context"
    },
    "CROSS_PURSUIT_INSIGHT": {
        "priority": 3,
        "cooldown_minutes": 35,
        "description": "v2.5: Connection between user's own pursuits detected"
    },
    "METHODOLOGY_GUIDANCE": {
        "priority": 4,
        "cooldown_minutes": 40,
        "description": "v2.5: Natural phase transition point detected"
    },
    # v2.6: Stakeholder engagement prompt
    "STAKEHOLDER_ENGAGEMENT_PROMPT": {
        "priority": 3,
        "cooldown_minutes": 99999,  # Only prompt once per trigger
        "description": "v2.6: Prompt to capture stakeholder feedback at transitions"
    },
    # v2.7: Terminal state transition
    "TERMINAL_TRANSITION": {
        "priority": 1,  # Highest priority when detected
        "cooldown_minutes": 99999,  # Only once per pursuit
        "description": "v2.7: Detected terminal state, initiate retrospective"
    }
}

# Shorthand cooldowns dict for easy access (v2.7: added terminal transition)
COOLDOWNS = {
    "CRITICAL_GAP": 15,
    "READY_TO_FORMALIZE": 20,
    "FEAR_OPPORTUNITY": 30,
    "NATURAL_TRANSITION": 45,
    "ARTIFACT_DRIFT": 30,
    # v2.5: New cooldowns
    "PATTERN_RELEVANT": 25,
    "CROSS_PURSUIT_INSIGHT": 35,
    "METHODOLOGY_GUIDANCE": 40,
    # v2.6: Stakeholder prompt (once per trigger)
    "STAKEHOLDER_ENGAGEMENT_PROMPT": 99999,
    # v2.7: Terminal transition (once per pursuit)
    "TERMINAL_TRANSITION": 99999
}

# =============================================================================
# v2.4: LIFECYCLE MANAGEMENT CONFIGURATION
# =============================================================================

LIFECYCLE_CONFIG = {
    "enable_drift_detection": True,
    "drift_check_frequency": "every_turn",  # or "periodic"
    "change_thresholds": {
        "MINOR": 0.15,      # <15% of elements changed
        "MODERATE": 0.35,   # 15-35% changed
        "MAJOR": 0.35       # >35% changed (pivot-level)
    },
    "critical_elements": [
        "problem_statement",
        "solution_concept",
        "target_user",
        "value_proposition"
    ],
    "preserve_old_versions": True,
    "max_version_history": 10  # Keep last 10 versions
}

# UI Configuration for v2.5
UI_CONFIG = {
    "enable_enter_to_send": True,
    "auto_select_new_pursuits": True,
    "show_pursuit_status": True,
    "dropdown_refresh_mode": "automatic"  # vs "manual"
}

# =============================================================================
# v2.5: PATTERN ENGINE CONFIGURATION
# =============================================================================
PATTERN_ENGINE_CONFIG = {
    "enable_pattern_matching": True,
    "matching_mode": "semantic",              # "semantic" | "keyword" | "hybrid"
    "relevance_threshold": 0.70,              # Minimum relevance to surface pattern
    "effectiveness_threshold": 0.50,          # Minimum success rate to recommend
    "max_patterns_per_turn": 3,               # Limit patterns surfaced per turn
    "cross_pursuit_window_days": 180,         # How far back to look for connections
    "proto_pattern_promotion_threshold": 3,   # Applications before validation
    "enable_cross_pursuit_insights": True,
    "pattern_cache_ttl_seconds": 300          # Cache pattern results for 5 minutes
}

# =============================================================================
# v2.5: ADVANCED ELEMENT TRACKING CONFIGURATION
# =============================================================================
ELEMENT_TRACKING_CONFIG = {
    "track_critical_elements": True,          # 20 critical elements (required)
    "track_important_elements": True,         # 20 important elements (enhances quality)
    "confidence_threshold_critical": 0.60,    # Minimum confidence for critical
    "confidence_threshold_important": 0.50,   # Minimum confidence for important
    "track_extraction_method": True,          # Track how element was extracted
    "track_update_history": True              # Track when elements change
}

# =============================================================================
# v2.5: ADAPTIVE INTERVENTION CONFIGURATION
# =============================================================================
ADAPTIVE_CONFIG = {
    "enable_adaptive_cooldowns": True,
    "engagement_calculation_window_hours": 2,  # Rolling window for engagement calc
    "high_engagement_threshold": 0.70,         # Score above this = high engagement
    "low_engagement_threshold": 0.40,          # Score below this = low engagement
    "high_engagement_multiplier": 0.6,         # Intervene more frequently
    "low_engagement_multiplier": 1.5,          # Intervene less frequently
    "track_intervention_quality": True,
    "min_messages_for_engagement": 3           # Min messages before calculating
}

# =============================================================================
# v2.6: STAKEHOLDER FEEDBACK CONFIGURATION
# =============================================================================
STAKEHOLDER_CONFIG = {
    "enable_stakeholder_tracking": True,
    "prompt_at_transitions": True,
    "enforcement_mode": "advisory",  # Never blocks transitions
    "prompt_frequency": "once_per_trigger",
    "support_threshold_warning": 0.50,  # Warn if <50% support
    "support_threshold_strong": 0.70,   # Indicate strong foundation
    "max_concerns_displayed": 5,
    "enable_pattern_learning": True
}

# State transitions that trigger stakeholder prompt
STAKEHOLDER_PROMPT_TRIGGERS = [
    ("PROBLEM_VALIDATION", "SOLUTION_REFINEMENT"),
    ("SOLUTION_REFINEMENT", "BUILDING"),
    ("before_pitch", None)  # Special trigger before pitch phase
]

# Support level enum values
SUPPORT_LEVELS = [
    "supportive",
    "conditional",
    "neutral",
    "opposed",
    "unclear"
]

# Stakeholder feedback templates
STAKEHOLDER_TEMPLATES = {
    "minimal": {
        "fields": ["stakeholder_name", "role", "support_level", "concerns", "resources_offered"],
        "required": ["stakeholder_name", "role", "support_level"]
    },
    "extended": {
        "fields": ["all"],
        "required": ["stakeholder_name", "role", "support_level"]
    }
}

# =============================================================================
# v2.7: TERMINAL STATE CONFIGURATION
# =============================================================================

# Terminal States (6 only - NO SUSPENDED states)
TERMINAL_STATES = [
    "COMPLETED.SUCCESSFUL",
    "COMPLETED.VALIDATED_NOT_PURSUED",
    "TERMINATED.INVALIDATED",
    "TERMINATED.PIVOTED",
    "TERMINATED.ABANDONED",
    "TERMINATED.OBE"
]

# Suspended States (NOT terminal - do not trigger retrospectives)
SUSPENDED_STATES = [
    "SUSPENDED.RESOURCE_CONSTRAINED",
    "SUSPENDED.MARKET_TIMING",
    "SUSPENDED.DEPENDENCY_BLOCKED"
]

# Pursuit States (all valid states)
PURSUIT_STATES = ["ACTIVE"] + TERMINAL_STATES + SUSPENDED_STATES

# Retrospective System Configuration (v2.8: Added early exit capability)
RETROSPECTIVE_CONFIG = {
    "enable_terminal_detection": True,
    "detection_confidence_threshold": 0.70,  # Higher for accuracy
    "inactivity_threshold_days": {
        "early_stage": 45,      # More patient in early stages
        "mid_stage": 30,
        "late_stage": 21
    },
    "completion_threshold": 0.70,  # 70% of prompts answered = complete
    "quality_threshold": 0.60,
    "max_prompts_per_retro": 8,
    "allow_pause_resume": True,
    # v2.8: Retrospective Flexibility
    "allow_early_exit": True,               # Allow exiting before all questions
    "min_questions_for_partial": 3,         # Minimum for partial completion
    "partial_completion_threshold": 0.40,   # 40% minimum for partial
    "enable_resume": True,                  # Can pause and resume later
    "gentle_completion_prompts": True       # Suggest completing later
}

# =============================================================================
# v2.8: LIVING SNAPSHOT REPORT CONFIGURATION
# =============================================================================
LIVING_SNAPSHOT_CONFIG = {
    "enable_snapshot_reports": True,
    "default_template": "silr-light",
    "auto_populate_threshold": 0.85,
    "projection_enabled": True,         # Show future sections as "Planned"
    "formats": ["markdown", "pdf"]
}

# =============================================================================
# v2.8: PORTFOLIO ANALYTICS CONFIGURATION
# =============================================================================
PORTFOLIO_ANALYTICS_CONFIG = {
    "enable_portfolio_reports": True,
    "default_analysis": "comprehensive",
    "min_pursuits_for_analytics": 3,    # Need at least 3 pursuits
    "enable_visualizations": True,
    "chart_format": "png"
}

# =============================================================================
# v2.8: REPORT TEMPLATES CONFIGURATION
# =============================================================================
REPORT_TEMPLATES_CONFIG = {
    "system_templates": [
        "silr-standard",
        "silr-light",
        "academic",
        "commercial",
        "internal",
        "investor",
        "grant"
    ],
    "allow_custom_templates": True,
    "max_custom_templates_per_user": 10
}

# =============================================================================
# v2.8: REPORT REVIEW WORKFLOW CONFIGURATION
# =============================================================================
REPORT_REVIEW_CONFIG = {
    "enable_review_workflow": True,
    "require_approval_for_external": True,  # External distribution requires approval
    "enable_comments": True,
    "enable_version_control": True,
    "max_versions_stored": 5
}

# =============================================================================
# v2.8: VISUALIZATION CONFIGURATION
# =============================================================================
VISUALIZATION_CONFIG = {
    "enable_charts": True,
    "chart_library": "matplotlib",      # or "plotly" for interactive
    "default_dpi": 300,
    "color_scheme": "professional",     # professional, vibrant, monochrome
    "include_in_reports": True
}

# =============================================================================
# v2.8: REPORT SCHEDULING CONFIGURATION
# =============================================================================
REPORT_SCHEDULING_CONFIG = {
    "enable_scheduled_reports": True,
    "frequencies": ["weekly", "monthly", "quarterly"],
    "max_scheduled_reports_per_user": 5,
    "auto_delivery_enabled": True
}

# Report Generation Config
REPORT_CONFIG = {
    "default_template": "silr-standard",
    "auto_generate_on_terminal": True,
    "formats": ["markdown"],  # pdf optional with pandoc
    "auto_populate_threshold": 0.95
}

# Outcome-Specific Artifacts Config
OUTCOME_ARTIFACTS = {
    "TERMINATED.OBE": ["competitive_intelligence", "resurrection_analysis"],
    "COMPLETED.SUCCESSFUL": ["success_pattern", "replication_guide"],
    "TERMINATED.INVALIDATED": ["anti_pattern", "validation_evidence"],
    "TERMINATED.PIVOTED": ["carry_forward_analysis"],
    "TERMINATED.ABANDONED": ["salvage_assessment"],
    "COMPLETED.VALIDATED_NOT_PURSUED": ["strategic_rationale"]
}

# Terminal State Detection Prompt
TERMINAL_DETECTION_PROMPT = """Analyze this message for signals that an innovation pursuit has reached a TERMINAL endpoint.

CONTEXT:
Pursuit: {pursuit_name}
Recent activity: {activity_count} messages in last 7 days

USER MESSAGE: "{message}"

CLASSIFY into ONE of these categories (be CONSERVATIVE - prefer ACTIVE if uncertain):

TERMINAL STATES (definitive endpoints):
1. COMPLETED.SUCCESSFUL - Innovation achieved objectives, launched/deployed
2. COMPLETED.VALIDATED_NOT_PURSUED - Validated concept but strategically chose not to proceed
3. TERMINATED.INVALIDATED - Core hypothesis disproven through validation/testing
4. TERMINATED.PIVOTED - Original pursuit ended, pivoting to new direction
5. TERMINATED.ABANDONED - External factors forced termination (resources, org changes)
6. TERMINATED.OBE - Overtaken By Events (competitor launched, regulations changed, market shifted)

NOT TERMINAL:
7. ACTIVE - Pursuit is ongoing, including if paused/suspended with intent to resume

CRITICAL: SUSPENDED states (awaiting resources, timing, dependencies) are NOT terminal - classify as ACTIVE.

Respond with JSON:
{{
    "state": "TERMINATED.INVALIDATED" | "COMPLETED.SUCCESSFUL" | "ACTIVE" | etc.,
    "confidence": 0.0-1.0,
    "evidence": "specific phrase from user message that indicates this state",
    "reasoning": "brief explanation of classification"
}}

Be conservative - only suggest terminal states when confident (>0.70)."""

# Retrospective Token Budget
RETROSPECTIVE_TOKEN_BUDGET = {
    "system_prompt": 1800,
    "retrospective_context": 2000,
    "conversation_history": 2500,
    "pursuit_context": 1000,
    "pattern_suggestions": 1500,
    "user_message": 500,
    "response_generation": 1700,
    "total_max": 12000
}

# =============================================================================
# TOKEN BUDGET (per turn) - v2.7: Added retrospective context
# =============================================================================
TOKEN_BUDGET = {
    "system_prompt": 1500,        # Base coaching instructions
    "scaffolding_context": 2000,  # v2.5: Increased for 40 elements
    "pattern_context": 2000,      # v2.5: Pattern matching context
    "stakeholder_context": 500,   # v2.6: NEW - Stakeholder support landscape
    "conversation_history": 3000, # Last 10 turns
    "lifecycle_context": 1000,    # v2.5: Artifact lifecycle state
    "user_message": 500,          # Current user input
    "response_budget": 2000,      # v2.5: Increased for richer responses
    "total_max": 12500            # v2.6: Increased from 12k for stakeholder context
}
# Total: ~12,500 tokens per turn (increased from v2.5's ~12,000)

# =============================================================================
# UI CONFIGURATION
# =============================================================================
GRADIO_HOST = "127.0.0.1"
GRADIO_PORT = 7860
GRADIO_THEME = "soft"

# =============================================================================
# LLM PROMPTS
# =============================================================================

INTENT_DETECTION_PROMPT = """Analyze this message for innovation intent. Does the user want to create, build, design, or develop something new?

Look for patterns like:
- "I want to create/build/design/develop..."
- "What if we made..."
- "I'm thinking about a product/service/solution..."
- Problem statements: "The problem with X is..."
- Opportunity statements: "There's a need for..."

User message: {user_message}

Respond in JSON only:
{{
    "has_intent": true or false,
    "confidence": 0.0-1.0,
    "suggested_title": "brief descriptive title for the pursuit",
    "problem_hint": "what problem they mentioned or null",
    "solution_hint": "what solution they hinted at or null"
}}"""

ELEMENT_EXTRACTION_PROMPT = """Extract innovation elements from this conversation turn.

Current pursuit: {pursuit_title}
Elements already captured: {existing_elements}

Critical elements to look for:
VISION ELEMENTS:
- problem_statement: What problem exists?
- target_user: Who has this problem?
- current_situation: How do they deal with it now?
- pain_points: What's painful about current state?
- solution_concept: What's the proposed solution?
- value_proposition: Why would anyone want this?
- differentiation: What makes this different?
- success_criteria: How do we know if it works?

FEAR ELEMENTS:
- capability_fears: Can we build this?
- market_fears: Will anyone want this?
- resource_fears: Do we have what we need?
- timing_fears: Is now the right time?
- competition_fears: What about competitors?
- personal_fears: What am I personally worried about?

HYPOTHESIS ELEMENTS:
- assumption_statement: What are we assuming?
- testable_prediction: What do we predict will happen?
- test_method: How can we test this?
- success_metric: How do we measure success?
- failure_criteria: When do we admit we're wrong?
- learning_plan: What do we do with results?

Conversation turn: {conversation_turn}

Respond in JSON with any NEW elements found. Only include elements you're confident about (confidence > 0.6).
{{
    "vision": {{"element_name": {{"text": "extracted text", "confidence": 0.8}}, ...}},
    "fears": {{"element_name": {{"text": "extracted text", "confidence": 0.7}}, ...}},
    "hypothesis": {{"element_name": {{"text": "extracted text", "confidence": 0.9}}, ...}}
}}"""

ARTIFACT_GENERATION_PROMPT = """Generate a formal {artifact_type} artifact from these elements:

{elements_json}

Use this template format:

{template}

IMPORTANT: Wrap the entire artifact in markers like this:
[ARTIFACT:{artifact_type}]
... your artifact content here ...
[/ARTIFACT]

Write clearly and concisely. This will be shown to the innovator as a formal document they can share with partners or investors."""

COACHING_RESPONSE_PROMPT = """You are an innovation coach having a natural conversation with an innovator.

Current pursuit: {pursuit_title}
Scaffolding completeness - Vision: {vision_completeness}%, Fears: {fear_completeness}%, Hypothesis: {hypothesis_completeness}%

{intervention_instruction}

Conversation so far:
{conversation_history}

User just said: {user_message}

Respond naturally as a supportive innovation coach. Keep responses conversational and under 150 words unless generating an artifact. {additional_guidance}"""

# Artifact Templates
VISION_TEMPLATE = """# Vision: {title}

## Problem
{problem_statement}

## Target User
{target_user}

## Current Situation
{current_situation}

## Pain Points
{pain_points}

## Solution Concept
{solution_concept}

## Value Proposition
{value_proposition}

## Differentiation
{differentiation}

## Success Criteria
{success_criteria}"""

FEARS_TEMPLATE = """# Fears & Concerns: {title}

## Capability Concerns
{capability_fears}

## Market Concerns
{market_fears}

## Resource Concerns
{resource_fears}

## Timing Concerns
{timing_fears}

## Competition Concerns
{competition_fears}

## Personal Concerns
{personal_fears}"""

HYPOTHESIS_TEMPLATE = """# Key Hypothesis: {title}

## Core Assumption
{assumption_statement}

## Testable Prediction
{testable_prediction}

## Test Method
{test_method}

## Success Metric
{success_metric}

## Failure Criteria
{failure_criteria}

## Learning Plan
{learning_plan}"""

# =============================================================================
# v2.5: PATTERN MATCHING PROMPTS
# =============================================================================

PATTERN_MATCHING_PROMPT = """Analyze this pursuit context and find relevant historical patterns.

Current pursuit context:
- Problem: {problem_statement}
- Solution: {solution_concept}
- Domain: {domain}
- Stage: {stage}
- Key challenges: {key_challenges}

Available patterns:
{patterns_json}

Return the top 3 most relevant patterns with relevance scores. Consider:
1. Problem similarity (domain, type of challenge)
2. Solution approach alignment
3. Stage appropriateness
4. Historical effectiveness

Respond in JSON only:
{{
    "relevant_patterns": [
        {{
            "pattern_id": "uuid",
            "relevance_score": 0.0-1.0,
            "relevance_reason": "brief explanation of why relevant",
            "suggested_application": "how this pattern could help"
        }}
    ]
}}"""

CROSS_PURSUIT_PROMPT = """Analyze these pursuits from the same user and find meaningful connections.

Current pursuit:
{current_pursuit}

Other pursuits:
{other_pursuits}

Look for:
1. Similar assumptions or fears across pursuits
2. Patterns in problem-solving approaches
3. Learnings from completed pursuits that apply here
4. Potential resource or knowledge sharing opportunities

Respond in JSON only:
{{
    "insights": [
        {{
            "insight_type": "similar_assumption|shared_fear|applicable_learning|resource_synergy",
            "related_pursuit_id": "uuid",
            "insight": "brief description of the connection",
            "suggested_action": "what the user might do with this insight",
            "confidence": 0.0-1.0
        }}
    ]
}}"""

PROTO_PATTERN_EXTRACTION_PROMPT = """Extract a learnable pattern from this completed pursuit.

Pursuit summary:
- Title: {title}
- Problem: {problem_statement}
- Solution: {solution_concept}
- Domain: {domain}
- Outcome: {outcome}
- Key learnings: {learnings}
- Timeline: {timeline}

Create a proto-pattern that could help future innovators facing similar challenges.

Respond in JSON only:
{{
    "pattern_name": "concise name for pattern",
    "problem_context": {{
        "domain": ["applicable domains"],
        "problem_type": ["types of problems this addresses"],
        "innovation_stage": ["stages where applicable"]
    }},
    "solution_approach": "description of the approach that worked",
    "key_insight": "the core learning that others should know",
    "success_factors": ["what made this work"],
    "failure_risks": ["what to watch out for"],
    "applicability_score": 0.0-1.0
}}"""

# =============================================================================
# v2.7: SURVEY DATA INGESTION CONFIGURATION
# =============================================================================
SURVEY_CONFIG = {
    "max_file_size_mb": 5,
    "supported_formats": [".csv", ".xlsx", ".xls", ".txt", ".md"],
    "column_mappings": {
        # Maps various column names to standard field names
        "name": ["name", "respondent", "stakeholder", "participant", "person", "who"],
        "role": ["role", "title", "position", "job_title", "job", "function"],
        "support": ["support", "rating", "score", "satisfaction", "level", "opinion"],
        "concerns": ["concerns", "feedback", "comments", "issues", "problems", "worries"],
        "organization": ["organization", "company", "org", "employer", "firm", "business"]
    },
    "support_level_mapping": {
        # Map numeric scores to support levels
        5: "supportive",
        4: "supportive",
        3: "neutral",
        2: "opposed",
        1: "opposed"
    },
    "text_support_mapping": {
        # Map text responses to support levels
        "strongly agree": "supportive",
        "agree": "supportive",
        "neutral": "neutral",
        "disagree": "opposed",
        "strongly disagree": "opposed",
        "yes": "supportive",
        "no": "opposed",
        "maybe": "conditional"
    }
}

# Prompt for extracting insights from survey data
SURVEY_INSIGHT_PROMPT = """Analyze these survey results for an innovation pursuit.

PURSUIT CONTEXT:
- Title: {pursuit_title}
- Vision Summary: {vision_summary}

SURVEY DATA:
{survey_data}

Extract insights in these categories:

1. KEY THEMES: Common patterns across responses
2. VISION VALIDATION: Signals that support or challenge the vision
3. FEARS/CONCERNS: Issues that should inform the "fears" scaffolding
4. HYPOTHESIS REFINEMENTS: Suggestions for testing assumptions
5. SUPPORT DISTRIBUTION: Summary of stakeholder sentiment

Respond in JSON only:
{{
    "themes": ["theme1", "theme2", ...],
    "vision_validations": [
        {{"signal": "description", "strength": "strong|moderate|weak", "source_count": N}}
    ],
    "fears_insights": [
        {{"concern": "description", "frequency": N, "severity": "high|medium|low"}}
    ],
    "hypothesis_refinements": [
        {{"suggestion": "description", "based_on": "evidence from survey"}}
    ],
    "support_summary": {{
        "supportive_count": N,
        "conditional_count": N,
        "neutral_count": N,
        "opposed_count": N,
        "key_conditions": ["condition1", ...],
        "overall_sentiment": "positive|mixed|negative"
    }}
}}"""

# =============================================================================
# v2.9: REPORT DISTRIBUTION CONFIGURATION
# =============================================================================
DISTRIBUTION_CONFIG = {
    "enable_email_distribution": True,
    "enable_share_links": True,
    "smtp_host": os.getenv("SMTP_HOST", "localhost"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "smtp_from_email": os.getenv("SMTP_FROM", "inde@example.com"),
    "smtp_from_name": os.getenv("SMTP_FROM_NAME", "InDE Innovation Platform"),
    "share_link_base_url": os.getenv("SHARE_LINK_BASE_URL", "http://localhost:7860"),
    "default_share_expiry_days": 7,
    "max_share_expiry_days": 365,
    "track_email_opens": True,
    "track_downloads": True
}

# Email templates
EMAIL_TEMPLATES = {
    "professional": {
        "subject": "Innovation Report: {pursuit_title}",
        "greeting": "Hello {recipient_name},",
        "body": "Please find attached the latest report for the innovation pursuit: {pursuit_title}.",
        "cta_text": "View Full Report"
    },
    "casual": {
        "subject": "{pursuit_title} - Update for you",
        "greeting": "Hi {recipient_name}!",
        "body": "Here's an update on {pursuit_title}. Check out the attached report for details.",
        "cta_text": "See What's New"
    },
    "investor": {
        "subject": "Investment Update: {pursuit_title}",
        "greeting": "Dear {recipient_name},",
        "body": "Attached is the latest investor report for {pursuit_title}. This report includes key metrics, progress updates, and risk assessments.",
        "cta_text": "Review Full Report"
    }
}

# =============================================================================
# v2.9: PURSUIT SHARING CONFIGURATION
# =============================================================================
SHARING_CONFIG = {
    "enable_sharing": True,
    "default_privacy_level": "unlisted",  # public, unlisted, private
    "share_token_length": 32,
    "allow_password_protection": True,
    "track_analytics": True,
    "viral_cta_enabled": True,
    "viral_cta_text": "Create your own innovation pursuit",
    "show_social_proof": True,
    "social_proof_min_users": 100  # Minimum users before showing count
}

# Privacy levels
PRIVACY_LEVELS = ["public", "unlisted", "private"]

# Sections visible in public pursuit view
PUBLIC_VIEW_SECTIONS = [
    "vision",
    "fears",
    "hypotheses",
    "progress_timeline",
    "risk_validation"
]

# =============================================================================
# v2.9: STAKEHOLDER RESPONSE CONFIGURATION
# =============================================================================
STAKEHOLDER_RESPONSE_CONFIG = {
    "enable_response_capture": True,
    "thread_to_conversation": True,
    "notify_innovator": True,
    "enable_innovator_reply": True,
    "response_types": ["excitement", "concern", "question"],
    "question_categories": ["market", "technical", "resource", "timing", "general"]
}

# Feedback widget labels
FEEDBACK_WIDGET_LABELS = {
    "excitement": "This excites me",
    "concern": "This concerns me",
    "question": "I have questions"
}

# =============================================================================
# v2.9: COLLABORATION CONFIGURATION
# =============================================================================
COLLABORATION_CONFIG = {
    "enable_comments": True,
    "enable_mentions": True,
    "enable_activity_feed": True,
    "max_comments_per_artifact": 100,
    "mention_pattern": r"@([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[A-Za-z][A-Za-z0-9_]*)"
}

# Activity types for feed
ACTIVITY_TYPES = [
    "artifact_created",
    "artifact_updated",
    "decision_made",
    "stakeholder_feedback",
    "comment_added",
    "phase_transition",
    "risk_defined",
    "evidence_captured"
]

# =============================================================================
# v2.9: RVE LITE CONFIGURATION
# =============================================================================
RVE_LITE_CONFIG = {
    "enable_fear_to_risk": True,
    "enable_evidence_capture": True,
    "enable_decision_support": True,
    "advisory_only": True,  # No automatic actions - purely advisory
    "allow_override": True,
    "track_overrides": True
}

# Risk categories
RISK_CATEGORIES = ["MARKET", "TECHNICAL", "RESOURCE", "REGULATORY", "TIMING"]

# Risk priorities
RISK_PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# Validation states
VALIDATION_STATES = ["ASSUMPTION", "PARTIALLY_VALIDATED", "VALIDATED"]

# Validation status
VALIDATION_STATUS = ["NOT_STARTED", "IN_PROGRESS", "VALIDATED", "UNMITIGATED"]

# Recommendation types
RECOMMENDATION_TYPES = ["PROCEED", "PIVOT", "INVESTIGATE_FURTHER"]

# Evidence confidence levels
EVIDENCE_CONFIDENCE_LEVELS = {
    "HIGH": {"min_score": 0.7, "description": "Strong evidence, good sample, controlled"},
    "MEDIUM": {"min_score": 0.4, "description": "Some evidence, limited sample, informal"},
    "LOW": {"min_score": 0.0, "description": "Anecdotal, small sample, biased"}
}

# RVE Lite prompts
FEAR_TO_RISK_PROMPT = """Convert this fear into a measurable risk definition.

FEAR ARTIFACT:
{fear_content}

PURSUIT CONTEXT:
- Title: {pursuit_title}
- Vision: {vision_summary}

Guide the innovator to define:
1. Risk Parameter: What specific metric or signal proves this fear is real?
2. Acceptable Threshold: What minimum value indicates the risk is manageable?
3. Category: MARKET, TECHNICAL, RESOURCE, REGULATORY, or TIMING
4. Priority: CRITICAL, HIGH, MEDIUM, or LOW based on impact

Respond with a JSON structure:
{{
    "risk_parameter": "description of what to measure",
    "acceptable_threshold": "minimum acceptable value or condition",
    "category": "MARKET|TECHNICAL|RESOURCE|REGULATORY|TIMING",
    "priority": "CRITICAL|HIGH|MEDIUM|LOW",
    "impact_if_unmitigated": "description of consequences",
    "suggested_validation_method": "how to test this risk"
}}"""

EVIDENCE_ASSESSMENT_PROMPT = """Assess the rigor of this validation evidence.

EVIDENCE:
- Methodology: {methodology}
- Sample Size: {sample_size}
- Results: {results}

RISK BEING VALIDATED:
- Parameter: {risk_parameter}
- Threshold: {acceptable_threshold}

Assess:
1. Sample Adequacy: Is the sample size sufficient?
2. Bias Controls: What controls exist for bias?
3. Confidence Level: HIGH, MEDIUM, or LOW

Respond with JSON:
{{
    "confidence_level": "HIGH|MEDIUM|LOW",
    "confidence_score": 0.0-1.0,
    "sample_adequacy": "assessment of sample size",
    "bias_controls": ["control1", "control2"],
    "recommendation": "interpretation of evidence"
}}"""

DECISION_SUPPORT_PROMPT = """Provide advisory recommendation based on evidence.

RISK:
- Parameter: {risk_parameter}
- Threshold: {acceptable_threshold}
- Category: {category}
- Priority: {priority}

EVIDENCE SUMMARY:
{evidence_summary}

Provide an advisory recommendation:
1. Status: MITIGATED, UNMITIGATED, or UNCERTAIN
2. Recommendation: PROCEED, PIVOT, or INVESTIGATE_FURTHER
3. Confidence in recommendation

IMPORTANT: This is ADVISORY ONLY. The innovator makes all final decisions.

Respond with JSON:
{{
    "status": "MITIGATED|UNMITIGATED|UNCERTAIN",
    "recommendation": "PROCEED|PIVOT|INVESTIGATE_FURTHER",
    "confidence": 0.0-1.0,
    "rationale": "brief explanation",
    "key_considerations": ["consideration1", "consideration2"]
}}"""

# =============================================================================
# v3.0.1: TEMPORAL INTELLIGENCE MODULE (TIM) CONFIGURATION
# =============================================================================
TIM_CONFIG = {
    "enable_temporal_tracking": True,
    "default_buffer_percent": 10,
    "default_pursuit_duration_days": 180,  # 6 months default
    "velocity_window_days": 7,
    "velocity_cache_ttl_seconds": 3600,  # 1 hour cache
    "enable_velocity_projection": True,
    "projection_confidence_window_days": 14
}

# IKF Universal Phase Taxonomy (Innovation Knowledge Fabric compatible)
IKF_PHASES = ["VISION", "DE_RISK", "DEPLOY"]

# Default phase allocations (must sum to 100% minus buffer)
DEFAULT_PHASE_ALLOCATIONS = {
    "VISION": 15,
    "DE_RISK": 35,
    "DEPLOY": 40,
    "BUFFER": 10
}

# Phase status values
PHASE_STATUS = ["NOT_STARTED", "IN_PROGRESS", "COMPLETE"]

# Velocity status thresholds
VELOCITY_THRESHOLDS = {
    "ahead": 1.10,      # >110% of expected pace
    "on_track_high": 1.10,
    "on_track_low": 0.90,
    "behind": 0.90      # <90% of expected pace
}

# Temporal event types (IKF-compatible)
TEMPORAL_EVENT_TYPES = [
    "PURSUIT_START",
    "PHASE_START",
    "ELEMENT_CAPTURED",
    "ARTIFACT_GENERATED",
    "INTERVENTION_TRIGGERED",
    "PHASE_COMPLETE",
    "PURSUIT_COMPLETE",
    "MILESTONE_EXTRACTED",    # v3.9: Auto-extracted from conversation
    "MILESTONE_UPDATED",      # v3.9: User clarified/changed a milestone
    # v3.10: Timeline Integrity event types
    "TIMELINE_CONFLICT",           # TD-001: Milestone conflict detected
    "CONFLICT_RESOLVED",           # TD-001: User chose resolution
    "TIMELINE_INCONSISTENCY",      # TD-002: Allocation/milestone mismatch
    "INCONSISTENCY_RESOLVED",      # TD-002: User chose source of truth
    "RELATIVE_DATE_PROMPTED",      # TD-005: Confirmation prompt shown
    "RELATIVE_DATE_CONFIRMED"      # TD-005: User confirmed resolution
]

# Phase transition triggers
PHASE_TRANSITION_TRIGGERS = ["automatic", "innovator_initiated", "system_recommendation"]

# =============================================================================
# v3.10: TIMELINE INTEGRITY CONFIGURATION
# =============================================================================

# Timeline conflict detection threshold (days)
# Milestone date shifts beyond this trigger user confirmation
TIMELINE_CONFLICT_THRESHOLD_DAYS = int(os.environ.get("TIMELINE_CONFLICT_THRESHOLD_DAYS", "14"))

# Relative date recalculation prompt threshold (days)
# Unconfirmed relative dates older than this get a confirmation prompt
RELATIVE_DATE_PROMPT_THRESHOLD_DAYS = int(os.environ.get("RELATIVE_DATE_PROMPT_THRESHOLD_DAYS", "7"))

# Inconsistency threshold (days) - mismatch below this is treated as noise
TIMELINE_INCONSISTENCY_THRESHOLD_DAYS = 3

# Conflict severity levels
CONFLICT_SEVERITY_NONE = "none"           # No conflict - safe to store
CONFLICT_SEVERITY_MINOR = "minor"         # <14 day shift - store but note in coaching
CONFLICT_SEVERITY_MAJOR = "major"         # >14 day shift - hold pending user confirmation
CONFLICT_SEVERITY_RETROGRADE = "retrograde"  # Past date - treat as completed milestone

# Resolution strategies
RESOLUTION_USER_CONFIRMED = "user_confirmed"
RESOLUTION_USER_REJECTED = "user_rejected"
RESOLUTION_AUTO_MINOR_UPDATE = "auto_minor_update"
RESOLUTION_USER_CHOSE_ALLOCATION = "user_chose_allocation"
RESOLUTION_USER_CHOSE_MILESTONE = "user_chose_milestone"

# Relative date resolution methods
RELATIVE_RESOLUTION_QUARTER_END = "quarter_end"
RELATIVE_RESOLUTION_QUARTER_START = "quarter_start"
RELATIVE_RESOLUTION_MONTH_END = "month_end"
RELATIVE_RESOLUTION_WEEK_END = "week_end"
RELATIVE_RESOLUTION_ESTIMATED = "estimated"

# =============================================================================
# v3.9: TIMELINE EXTRACTION CONFIGURATION
# =============================================================================

# Quick patterns to detect date mentions (avoids LLM call if no dates)
DATE_QUICK_PATTERNS = [
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}?,?\s*\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    r"\b(by|before|after|in|within|during)\s+(?:the\s+)?(?:end\s+of\s+)?(?:month\s+of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)",
    r"\bq[1-4]\s+\d{4}\b",
    r"\b(next|this)\s+(week|month|quarter|year)\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s*,?\s*\d{4}\b",
]

# Milestone type categories
MILESTONE_TYPES = [
    "phase_end",       # End of an IKF phase
    "deliverable",     # Specific deliverable completion
    "external",        # External event (conference, demo)
    "release",         # Product/feature release
    "validation",      # Test/validation milestone
    "funding",         # Funding-related deadline
    "team",            # Team-related milestone
    "other"
]

# LLM prompt for timeline/milestone extraction
TIMELINE_EXTRACTION_PROMPT = """Extract timeline information from this conversation turn.

Current pursuit: {pursuit_title}
Existing milestones: {existing_milestones}
Today's date: {today_date}

Extract TWO types of information:

1. PROJECT START DATE: When the user says they "started", "began", "kicked off" the project
   - Only extract if explicitly mentioned (e.g., "started on February 25th")
   - This is NOT a milestone - it's metadata about when the project began

2. MILESTONES: Future target dates for deliverables, releases, etc.
   - Look for: "by March", "release on May 1", "complete by", "due on", "deadline is"
   - These are FUTURE targets, not past events

IMPORTANT - Milestone types:
- "release" = product launch, initial release, go-live, ship date, "be complete by"
- "validation" = testing, QA, user testing, beta
- "deliverable" = design complete, prototype ready, feature done
- "phase_end" = end of a phase (Vision, De-Risk, Deploy)
- "external" = conferences, demos, investor meetings

For month-only dates like "March 2026", use the last day of the month (e.g., "2026-03-31").

Conversation turn:
{conversation_turn}

Respond ONLY with valid JSON:
{{
    "project_start_date": "YYYY-MM-DD or null if not mentioned",
    "project_end_date": "YYYY-MM-DD or null if not mentioned (overall completion/release date)",
    "milestones": [
        {{
            "title": "brief milestone name (3-6 words)",
            "description": "fuller context from conversation",
            "target_date": "YYYY-MM-DD or null if only relative",
            "date_expression": "original text mentioning the date",
            "date_precision": "exact|month|quarter|relative",
            "milestone_type": "phase_end|deliverable|external|release|validation|funding|team|other",
            "phase": "VISION|DE_RISK|DEPLOY|null",
            "confidence": 0.8
        }}
    ]
}}"""

# =============================================================================
# v3.0.2: INTELLIGENCE LAYER CONFIGURATION
# =============================================================================

# Health Monitor Configuration
HEALTH_MONITOR_CONFIG = {
    "enable_health_monitoring": True,
    "calculation_trigger_events": ["element_capture", "phase_transition", "session_start", "experiment_complete"],
    "health_score_cache_ttl_seconds": 300,  # 5 minutes
    "crisis_mode_enabled": True,
    "crisis_duration_threshold_days": 7,
    "wellness_suggestion_cooldown_seconds": 120
}

# Health Zone Definitions
HEALTH_ZONES = {
    "THRIVING": {"min": 80, "max": 100, "label": "Thriving", "color": "green"},
    "HEALTHY": {"min": 60, "max": 79, "label": "Healthy", "color": "light_green"},
    "ATTENTION": {"min": 40, "max": 59, "label": "Needs Attention", "color": "yellow"},
    "AT_RISK": {"min": 20, "max": 39, "label": "At Risk", "color": "orange"},
    "CRITICAL": {"min": 0, "max": 19, "label": "Critical", "color": "red"}
}

# Health Score Component Weights
HEALTH_SCORE_WEIGHTS = {
    "velocity_health": 0.30,      # Is progress pace on track?
    "element_coverage": 0.25,     # Are critical elements being captured?
    "phase_timing": 0.20,         # Is phase duration within allocation?
    "engagement_rhythm": 0.15,    # Is the innovator consistently active?
    "risk_posture": 0.10          # Are identified risks being addressed?
}

# Zone-Specific Coaching Guidelines
ZONE_COACHING_GUIDELINES = {
    "THRIVING": {
        "tone": "celebratory, forward-looking",
        "intervention_style": "light touch - encourage stretch goals"
    },
    "HEALTHY": {
        "tone": "supportive, confirmatory",
        "intervention_style": "standard coaching cadence"
    },
    "ATTENTION": {
        "tone": "gently probing, curious",
        "intervention_style": "ask about blockers, suggest retrospective"
    },
    "AT_RISK": {
        "tone": "direct but empathetic",
        "intervention_style": "surface specific risks, recommend action"
    },
    "CRITICAL": {
        "tone": "honest, urgent but not panic",
        "intervention_style": "suggest crisis mode, present options clearly"
    }
}

# Temporal Pattern Intelligence Configuration
TEMPORAL_PATTERN_CONFIG = {
    "enable_temporal_enrichment": True,
    "temporal_weight_in_matching": 0.20,  # 20% of total relevance score
    "antipattern_detection_enabled": True,
    "phase_benchmark_enabled": True,
    "velocity_correlation_enabled": True
}

# Updated Pattern Matching Weights (v3.0.2)
PATTERN_MATCHING_WEIGHTS = {
    "domain_match": 0.28,       # Was 35%
    "methodology_match": 0.20,  # Was 25%
    "tag_overlap": 0.20,        # Was 25%
    "phase_relevance": 0.12,    # Was 15%
    "temporal_similarity": 0.20  # NEW
}

# Temporal Anti-patterns
TEMPORAL_ANTIPATTERNS = [
    "VISION_STALL",         # >30% of total time in VISION phase
    "VELOCITY_COLLAPSE",    # >50% velocity drop over 2-week window
    "PHASE_SKIP",           # Moved to DEPLOY without adequate DE_RISK time
    "BUFFER_EXHAUSTION",    # Buffer consumed before 60% completion
    "ELEMENT_DROUGHT"       # No new elements captured in >10 days
]

# Predictive Guidance Configuration
PREDICTIVE_GUIDANCE_CONFIG = {
    "enable_predictions": True,
    "max_predictions_per_invocation": 3,
    "min_confidence_threshold": 0.60,
    "high_confidence_threshold": 0.75,
    "prediction_cache_ttl_seconds": 600  # 10 minutes
}

# Prediction Types
PREDICTION_TYPES = [
    "PHASE_CHALLENGE",      # "Teams typically struggle with [X] at this phase"
    "UPCOMING_RISK",        # "Based on velocity trajectory, [risk] likely in [timeframe]"
    "OPPORTUNITY_WINDOW",   # "Similar pursuits that [action] at this point had [outcome]"
    "STALL_WARNING",        # "Pursuits with this velocity pattern often stall in [N] days"
    "METHODOLOGY_HINT"      # "This is a good moment to [methodology-specific action]"
]

# Full RVE Configuration (upgraded from RVE Lite)
RVE_CONFIG = {
    "enable_experiment_wizard": True,
    "enable_three_zone_assessment": True,
    "enable_override_capture": True,
    "advisory_only": True,  # CRITICAL: No auto-termination, purely advisory
    "allow_override": True,
    "track_overrides": True,
    "default_confidence_threshold": 0.80
}

# RVE Experiment Templates by Methodology
RVE_EXPERIMENT_TEMPLATES = {
    "LEAN_STARTUP": [
        "landing_page_test",
        "concierge_mvp",
        "smoke_test",
        "wizard_of_oz",
        "split_test"
    ],
    "DESIGN_THINKING": [
        "user_interview_series",
        "prototype_test",
        "observation_study",
        "co_creation_session",
        "diary_study"
    ],
    "STAGE_GATE": [
        "technical_feasibility",
        "market_assessment",
        "financial_analysis",
        "competitive_scan",
        "regulatory_review"
    ]
}

# RVE Three-Zone Assessment
RVE_ZONES = {
    "GREEN": {
        "label": "Risk Mitigated",
        "emoji": "green_circle",
        "description": "Evidence demonstrates risk is manageable",
        "typical_confidence": (0.80, 1.0),
        "recommendation": "Proceed with confidence"
    },
    "YELLOW": {
        "label": "Risk Uncertain",
        "emoji": "yellow_circle",
        "description": "Evidence inconclusive or mixed",
        "typical_confidence": (0.40, 0.80),
        "recommendations": [
            "Refine experiment and re-test",
            "Proceed with enhanced monitoring",
            "Pivot approach"
        ]
    },
    "RED": {
        "label": "Risk Unmitigated",
        "emoji": "red_circle",
        "description": "Evidence demonstrates risk cannot be adequately mitigated",
        "typical_confidence": (0.80, 1.0),
        "recommendations": [
            "Consider termination",
            "Fundamental pivot required",
            "Acknowledge risk and proceed with explicit justification"
        ]
    }
}

# Experiment Status Values
EXPERIMENT_STATUS = ["DESIGNED", "IN_PROGRESS", "COMPLETE", "ABANDONED"]

# Temporal Risk Detection Configuration
RISK_DETECTION_CONFIG = {
    "enable_risk_detection": True,
    "short_term_horizon_days": 14,
    "medium_term_horizon_days": 60,
    "detection_frequency": "on_significant_event",  # Not every keystroke
    "max_risk_alerts_per_session": 2
}

# Risk Severity Levels
RISK_SEVERITY = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Overall Risk Levels
OVERALL_RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

# New Moment Types for Intelligence Layer (v3.0.2)
INTELLIGENCE_MOMENT_TYPES = {
    "HEALTH_WARNING": {
        "description": "Health score dropped below threshold",
        "cooldown_seconds": 60,
        "priority": "HIGH",
        "trigger": "health_score < 40 AND previous_score >= 40"
    },
    "PREDICTIVE_INSIGHT": {
        "description": "High-confidence prediction ready to surface",
        "cooldown_seconds": 45,
        "priority": "MEDIUM",
        "trigger": "prediction.confidence > 0.75 AND not_yet_surfaced"
    },
    "RISK_ESCALATION": {
        "description": "Risk level increased across detection cycle",
        "cooldown_seconds": 90,
        "priority": "HIGH",
        "trigger": "risk_level_increased AND new_risks_detected"
    },
    "EXPERIMENT_COMPLETE": {
        "description": "Validation experiment has results ready for assessment",
        "cooldown_seconds": 0,  # Always surface immediately
        "priority": "HIGH",
        "trigger": "experiment.status == COMPLETE AND not_assessed"
    },
    "RVE_ACTIVATION_PROMPT": {
        "description": "Prompt innovator to design experiment for unvalidated risk",
        "cooldown_seconds": 120,
        "priority": "LOW",
        "trigger": "risk.validation_status == NOT_STARTED AND risk.priority >= HIGH"
    },
    # v3.0.3: Portfolio-level insight moment
    "PORTFOLIO_INSIGHT": {
        "description": "Portfolio-level insight ready to surface (cross-pursuit patterns, health alerts)",
        "cooldown_seconds": 120,
        "priority": "MEDIUM",
        "trigger": "portfolio_insight_available AND multi_pursuit_context"
    }
}

# v3.0.3: Portfolio moment type configuration
PORTFOLIO_MOMENT_TYPE = {
    "type": "PORTFOLIO_INSIGHT",
    "cooldown_minutes": 2,  # 120 seconds
    "priority": 4,  # MEDIUM priority
    "triggers": [
        "portfolio_health_changed",
        "cross_pursuit_pattern_detected",
        "velocity_anomaly_detected",
        "ikf_contribution_ready"
    ]
}

# GPU Acceleration Configuration
GPU_CONFIG = {
    "enable_gpu_acceleration": True,
    "device_preference": "cuda",  # cuda | cpu
    "batch_similarity_threshold": 100,  # Use GPU when patterns > 100
    "embedding_batch_size": 64
}

# =============================================================================
# v3.0.3: PORTFOLIO INTELLIGENCE CONFIGURATION
# =============================================================================
PORTFOLIO_INTELLIGENCE_CONFIG = {
    "enable_portfolio_analytics": True,
    "recalculate_on_session_start": True,
    "recalculate_on_pursuit_change": True,
    "max_recommendations": 3,
    "cache_ttl_seconds": 300
}

# Phase weights for portfolio health calculation
PORTFOLIO_PHASE_WEIGHTS = {
    "VISION": 1.0,
    "CONCEPT": 1.0,
    "DE_RISK": 1.2,
    "DEPLOY": 1.5
}

# Portfolio health zones (same as pursuit health but for portfolio)
PORTFOLIO_HEALTH_ZONES = {
    "THRIVING": {"min": 80, "max": 100, "color": "#22C55E"},
    "HEALTHY": {"min": 60, "max": 79, "color": "#3B82F6"},
    "ATTENTION": {"min": 40, "max": 59, "color": "#F59E0B"},
    "AT_RISK": {"min": 20, "max": 39, "color": "#F97316"},
    "CRITICAL": {"min": 0, "max": 19, "color": "#EF4444"}
}

# Cross-pursuit pattern types
PORTFOLIO_PATTERN_TYPES = [
    "SHARED_RISK",
    "COMMON_BLOCKER",
    "SYNERGY",
    "VELOCITY_CORRELATION"
]

# =============================================================================
# v3.0.3: EFFECTIVENESS SCORECARD CONFIGURATION
# =============================================================================
EFFECTIVENESS_METRICS = {
    "learning_velocity_trend": {
        "description": "Rate of change in time-to-insight across sequential pursuits",
        "unit": "ratio",
        "good_threshold": 1.0,  # Improving if > 1.0
        "min_pursuits_required": 3
    },
    "prediction_accuracy": {
        "description": "% of predictive guidance matching actual outcomes",
        "unit": "percentage",
        "good_threshold": 0.70,
        "min_predictions_required": 10
    },
    "risk_validation_roi": {
        "description": "Ratio of validated risks to total risks, weighted by severity",
        "unit": "ratio",
        "good_threshold": 0.60,
        "min_risks_required": 5
    },
    "pattern_application_success": {
        "description": "Outcomes when IML patterns were applied vs ignored",
        "unit": "percentage",
        "good_threshold": 0.65,
        "min_patterns_required": 5
    },
    "fear_resolution_rate": {
        "description": "% of fears resolved before pursuit completion",
        "unit": "percentage",
        "good_threshold": 0.70,
        "min_fears_required": 10
    },
    "retrospective_completeness": {
        "description": "Average completion of retrospective prompts",
        "unit": "percentage",
        "good_threshold": 0.80,
        "min_retrospectives_required": 2
    },
    "time_to_decision": {
        "description": "Average time from risk identification to RVE verdict",
        "unit": "days",
        "good_threshold": 14,  # Lower is better
        "min_experiments_required": 5
    }
}

# =============================================================================
# v3.0.3: IKF CONTRIBUTION CONFIGURATION
# =============================================================================
IKF_CONTRIBUTION_CONFIG = {
    "enable_ikf_preparation": True,
    "require_human_review": True,  # MANDATORY - never auto-approve
    "max_pending_contributions": 10,
    "generalization_level_default": 3
}

# IKF package types (v3.2 naming with backwards compatibility)
IKF_PACKAGE_TYPES = [
    "temporal_benchmark",
    "pattern_contribution",  # v3.2 name
    "pattern",               # v3.0.3 backwards compatibility
    "risk_intelligence",
    "effectiveness_metrics", # v3.2 name
    "effectiveness",         # v3.0.3 backwards compatibility
    "retrospective_wisdom",  # v3.2 name
    "retrospective"          # v3.0.3 backwards compatibility
]

# IKF contribution status flow (v3.2 adds federation statuses)
IKF_CONTRIBUTION_STATUS = [
    "DRAFT",
    "REVIEWED",
    "IKF_READY",
    "REJECTED",
    "PENDING",           # v3.2: Queued for federation
    "SUBMITTED",         # v3.2: Submitted to federation
    "RETRY_PENDING",     # v3.2: Awaiting retry
    "SUBMISSION_FAILED"  # v3.2: Max retries exceeded
]

# Entity abstraction patterns for generalization
IKF_ENTITY_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}",
    "url": r"https?://[^\s<>\"{}|\\^`\[\]]+",
    "money": r"\$[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|EUR|GBP)"
}

# Metric normalization ranges
IKF_METRIC_RANGES = {
    "revenue": [(0, 1e6, "<$1M"), (1e6, 1e7, "$1M-$10M"), (1e7, 1e8, "$10M-$100M"), (1e8, float('inf'), ">$100M")],
    "employees": [(0, 10, "<10"), (10, 50, "10-50"), (50, 200, "50-200"), (200, 1000, "200-1000"), (1000, float('inf'), ">1000")],
    "days": [(0, 7, "<1 week"), (7, 30, "1-4 weeks"), (30, 90, "1-3 months"), (90, 365, "3-12 months"), (365, float('inf'), ">1 year")]
}

# =============================================================================
# v3.0.3: ANALYTICS VISUALIZATION CONFIGURATION
# =============================================================================
INDE_COLORS = {
    "THRIVING": "#22C55E",
    "HEALTHY": "#3B82F6",
    "ATTENTION": "#F59E0B",
    "AT_RISK": "#F97316",
    "CRITICAL": "#EF4444",
    "PORTFOLIO_AVG": "#6366F1",
    "CONFIDENCE_BAND": "#A5B4FC",
    "GRID": "#F1F5F9",
    "PASS": "#22C55E",
    "GREY": "#F59E0B",
    "FAIL": "#EF4444",
    "PRIMARY": "#6366F1",
    "SECONDARY": "#8B5CF6"
}

# Visualization types for SILR enrichment
SILR_VISUALIZATION_TYPES = [
    "timeline_journey",
    "velocity_curve",
    "health_trend",
    "risk_horizon_map",
    "rve_outcomes_donut",
    "portfolio_heatmap",
    "prediction_gauge",
    "learning_sparkline"
]

# Report enrichment configuration
SILR_ENRICHMENT_CONFIG = {
    "enable_temporal_enrichment": True,
    "include_visualizations": True,
    "visualization_dpi": 100,
    "max_data_points_per_chart": 50
}

# New moment type for portfolio insights
PORTFOLIO_MOMENT_TYPE = {
    "PORTFOLIO_INSIGHT": {
        "description": "Cross-pursuit pattern or insight ready to surface",
        "cooldown_seconds": 120,
        "priority": "MEDIUM",
        "trigger": "cross_pursuit_pattern_detected AND relevant_to_current"
    }
}

# =============================================================================
# v3.1: INNOVATOR MATURITY MODEL CONFIGURATION
# =============================================================================
MATURITY_CONFIG = {
    "enable_maturity_tracking": True,
    "recalculate_on_element_capture": True,
    "recalculate_on_pursuit_complete": True,
    "recalculate_on_experiment_complete": True
}

# Maturity Levels (never regress once achieved)
MATURITY_LEVELS = ["NOVICE", "COMPETENT", "PROFICIENT", "EXPERT"]

# Level Thresholds
MATURITY_LEVEL_THRESHOLDS = {
    "COMPETENT": {"min_score": 40, "min_pursuits": 2},
    "PROFICIENT": {"min_score": 55, "min_pursuits": 5},
    "EXPERT": {"min_score": 70, "min_pursuits": 9}
}

# Dimension Weights for composite score
MATURITY_DIMENSION_WEIGHTS = {
    "discovery_competence": 0.20,
    "validation_rigor": 0.25,
    "reflective_practice": 0.15,
    "velocity_management": 0.15,
    "risk_awareness": 0.15,
    "knowledge_contribution": 0.10
}

# Maturity-adaptive coaching styles
MATURITY_COACHING_STYLES = {
    "NOVICE": {
        "mode": "NURTURING",
        "intervention_frequency": "high",
        "explain_why": True,
        "encouragement_level": "high"
    },
    "COMPETENT": {
        "mode": "GUIDING",
        "intervention_frequency": "moderate",
        "explain_why": False,
        "encouragement_level": "moderate"
    },
    "PROFICIENT": {
        "mode": "CHALLENGING",
        "intervention_frequency": "low",
        "explain_why": False,
        "encouragement_level": "low"
    },
    "EXPERT": {
        "mode": "PEER_DIALOGUE",
        "intervention_frequency": "minimal",
        "explain_why": False,
        "encouragement_level": "minimal"
    }
}

# =============================================================================
# v3.1: ENHANCED CRISIS MODE CONFIGURATION
# =============================================================================
CRISIS_CONFIG = {
    "enable_crisis_mode": True,
    "auto_trigger_on_critical_health": True,
    "auto_trigger_on_velocity_collapse": True,
    "max_active_crises_per_pursuit": 1
}

# 7 Crisis Types
CRISIS_TYPES = {
    "COMPETITOR_THREAT": {"default_urgency": "URGENT", "intervention_depth": "FULL"},
    "RESOURCE_EXHAUSTION": {"default_urgency": "CRITICAL", "intervention_depth": "FULL"},
    "HYPOTHESIS_INVALIDATION": {"default_urgency": "URGENT", "intervention_depth": "FULL"},
    "SPONSOR_LOSS": {"default_urgency": "CRITICAL", "intervention_depth": "FULL"},
    "VELOCITY_COLLAPSE": {"default_urgency": "STANDARD", "intervention_depth": "MODERATE"},
    "PATTERN_MATCH": {"default_urgency": "STANDARD", "intervention_depth": "MODERATE"},
    "MANUAL": {"default_urgency": "STANDARD", "intervention_depth": "FULL"}
}

# Crisis Urgency Levels
CRISIS_URGENCY_LEVELS = ["STANDARD", "URGENT", "CRITICAL"]

# Crisis Intervention Phases
CRISIS_PHASES = [
    "IMMEDIATE_TRIAGE",      # 0-5 min
    "DIAGNOSTIC_DEEP_DIVE",  # 5-15 min
    "OPTIONS_GENERATION",    # 15-30 min
    "DECISION_SUPPORT",      # 30-45 min
    "POST_CRISIS_MONITORING" # 45-60 min
]

# =============================================================================
# v3.1: GII FOUNDATION CONFIGURATION
# =============================================================================
GII_CONFIG = {
    "enable_gii": True,
    "default_region": "NA",
    "require_explicit_binding": True,
    "publication_boundary_enforcement": "strict"
}

# Storage Election Options
STORAGE_ELECTIONS = ["FULL_PARTICIPATION", "ORG_VISIBLE", "PRIVATE"]

# Working State Types (blocked from publication)
WORKING_STATE_TYPES = [
    "raw_conversation",
    "fear_inventory_draft",
    "working_artifact_draft",
    "coaching_internal_note",
    "crisis_session_raw"
]

# =============================================================================
# v3.1: DOMAIN EVENT CONFIGURATION
# =============================================================================
EVENT_CONFIG = {
    "enable_event_persistence": True,
    "enable_event_dispatch": True,
    "max_handlers_per_event": 10,
    "log_all_events": True
}

# =============================================================================
# v3.2: REDIS EVENT BUS CONFIGURATION
# =============================================================================
REDIS_CONFIG = {
    "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
    "stream_prefix": os.getenv("REDIS_STREAM_PREFIX", "inde:events:"),
    "consumer_group": os.getenv("EVENT_CONSUMER_GROUP", "inde-app-consumers"),
    "fallback_mode": os.getenv("EVENT_BUS_FALLBACK", "memory"),
    "stream_maxlen": 10000,
    "consumer_block_ms": 5000,
    "reclaim_timeout_ms": 30000
}

# Redis Streams for different event categories (v3.4: added discovery, convergence, audit)
REDIS_STREAMS = [
    "pursuit",
    "coaching",
    "element",
    "health",
    "rve",
    "maturity",
    "crisis",
    "ikf",
    "retrospective",
    # v3.3: Team collaboration streams
    "team",
    "activity",
    # v3.4: Enterprise intelligence streams (NEW)
    "discovery",      # IDTFS discovery and formation events
    "convergence",    # Coaching convergence events
    "audit",          # SOC 2 audit events
    # v3.7.1: EMS stream (NEW)
    "ems",            # EMS Process Observation events
]

# =============================================================================
# v3.2: IKF SERVICE CONFIGURATION
# =============================================================================
IKF_SERVICE_CONFIG = {
    "url": os.getenv("IKF_SERVICE_URL", "http://localhost:8090"),
    "service_token": os.getenv("SERVICE_TOKEN", ""),
    "processing_mode": os.getenv("IKF_PROCESSING_MODE", "local"),
    "auto_prepare": os.getenv("IKF_AUTO_PREPARE", "true").lower() == "true",
    "max_pending_reviews": int(os.getenv("IKF_MAX_PENDING_REVIEWS", "3")),
    "consumer_group": os.getenv("IKF_CONSUMER_GROUP", "ikf-pipeline")
}

# v3.5: FEDERATION CONFIGURATION
# Configuration for connecting to external IKF federation hubs
FEDERATION_CONFIG = {
    "hub_url": os.getenv("IKF_HUB_URL", ""),
    "api_key": os.getenv("IKF_API_KEY", ""),
    "node_type": os.getenv("IKF_NODE_TYPE", "FULL"),  # CONTRIBUTOR, CONSUMER, FULL
    "connectivity_mode": os.getenv("IKF_CONNECTIVITY_MODE", "OFFLINE"),  # DIRECT, PEER, OFFLINE
    "heartbeat_interval_seconds": int(os.getenv("IKF_HEARTBEAT_INTERVAL", "300")),
    "sync_interval_seconds": int(os.getenv("IKF_SYNC_INTERVAL", "3600")),
    "max_retry_attempts": int(os.getenv("IKF_MAX_RETRIES", "3")),
    "package_expiry_days": int(os.getenv("IKF_PACKAGE_EXPIRY_DAYS", "90")),
}

# v3.2 Collections (new in this version)
V32_COLLECTIONS = [
    "event_dead_letters",     # Failed event processing queue
    "ikf_contribution_queue", # IKF contribution preparation queue
    "pattern_cache"           # Local IKF pattern cache
]

# =============================================================================
# v3.3: ORGANIZATION & TEAM CONFIGURATION
# =============================================================================
ORG_ROLES = ["admin", "member", "viewer"]

PURSUIT_ROLES = ["owner", "editor", "viewer"]

PURSUIT_ROLE_PERMISSIONS = {
    "owner": {
        "can_edit": True,
        "can_delete": True,
        "can_manage_team": True,
        "can_generate_reports": True,
        "can_coach": True,
        "can_contribute_elements": True,
        "can_view": True,
    },
    "editor": {
        "can_edit": True,
        "can_delete": False,
        "can_manage_team": False,
        "can_generate_reports": True,
        "can_coach": True,
        "can_contribute_elements": True,
        "can_view": True,
    },
    "viewer": {
        "can_edit": False,
        "can_delete": False,
        "can_manage_team": False,
        "can_generate_reports": False,
        "can_coach": False,
        "can_contribute_elements": False,
        "can_view": True,
    },
}

# =============================================================================
# v3.4: CONVERGENCE PROTOCOL CONFIGURATION
# =============================================================================
CONVERGENCE_CONFIG = {
    "threshold": float(os.getenv("CONVERGENCE_THRESHOLD", "0.7")),
    "signal_weights": {
        "repetition": 0.25,           # Semantic similarity between recent messages
        "decision_language": 0.30,    # "I think we should...", "My decision is..."
        "summary_requests": 0.15,     # Innovator asks coach to summarize, recap
        "satisfaction": 0.15,         # Positive affirmation, closure language
        "time_investment": 0.15,      # Session duration relative to expected
    },
    "context_token_budget": 800,      # Tokens allocated for convergence context
}

# Convergence phases
CONVERGENCE_PHASES = ["EXPLORING", "CONSOLIDATING", "COMMITTED", "HANDED_OFF"]

# Outcome types that can be captured during convergence
CONVERGENCE_OUTCOME_TYPES = ["DECISION", "INSIGHT", "HYPOTHESIS", "COMMITMENT", "REFINEMENT"]

# Criteria types for transition evaluation
CONVERGENCE_CRITERIA_TYPES = [
    "ARTIFACT_EXISTS",      # Required artifact has been created
    "ARTIFACT_COMPLETE",    # Artifact passes schema validation
    "VALIDATION",           # Experiment executed with outcomes
    "COACH_CHECKPOINT",     # Coach confirms readiness to proceed
    "TIME_INVESTMENT",      # Minimum time threshold met
    "CUSTOM",               # Archetype-specific criteria
]

# Criteria enforcement philosophies
CRITERIA_ENFORCEMENT = {
    "strict": "All criteria must be satisfied. No progression without gate approval.",
    "advisory": "Criteria recommended. Coach warns but allows override with rationale.",
    "suggestive": "Criteria are guidance. Iteration back is expected/encouraged.",
    "emergent": "Criteria discovered during progression. No predefined gates.",
}

# =============================================================================
# v3.4: IDTFS CONFIGURATION (Innovator Discovery & Team Formation Service)
# =============================================================================
IDTFS_CONFIG = {
    "max_candidates": int(os.getenv("IDTFS_MAX_CANDIDATES", "20")),
    "unavailable_hard_exclude": os.getenv("IDTFS_UNAVAILABLE_HARD_EXCLUDE", "true").lower() == "true",
    "pillar_weights": {
        "p1_behavioral_expertise": 0.20,    # InDE-derived from maturity, contribution history
        "p2_professional_profile": 0.15,    # External: career, domain tags, credentials
        "p3_vouching": 0.15,                # Directional endorsements from peers
        "p4_availability": 0.0,             # Binary filter (UNAVAILABLE = excluded)
        "p5_composition_patterns": 0.25,    # IML/IKF team composition intelligence
        "p6_expertise_type": 0.25,          # Domain vs process capability matching
    },
    "staleness_threshold_days": 90,         # Profile considered stale after this
    "coaching_token_budget": 500,           # Tokens for IDTFS coaching intervention
}

# Availability statuses
AVAILABILITY_STATUSES = ["AVAILABLE", "SELECTIVE", "UNAVAILABLE"]

# =============================================================================
# v3.4: ORG PORTFOLIO DASHBOARD CONFIGURATION
# =============================================================================
ORG_PORTFOLIO_CONFIG = {
    "cache_ttl_seconds": int(os.getenv("ORG_PORTFOLIO_CACHE_TTL", "300")),
    "recalculate_on_pursuit_change": True,
    "max_pursuits_for_realtime": 200,       # Above this, use pre-computed aggregates
    "org_context_token_budget": 700,        # Tokens for org intelligence in coaching
}

# The 7 dashboard panels
ORG_PORTFOLIO_PANELS = [
    "innovation_health_overview",
    "pursuit_phase_distribution",
    "methodology_effectiveness",
    "team_composition_analytics",
    "maturity_distribution",
    "knowledge_contribution_pipeline",
    "at_risk_pursuit_alerts",
]

# =============================================================================
# v3.4: ADVANCED RBAC CONFIGURATION
# =============================================================================
DEFINED_PERMISSIONS = [
    "can_create_pursuits",
    "can_invite_members",
    "can_manage_org_settings",
    "can_review_ikf_contributions",
    "can_view_portfolio_dashboard",
    "can_manage_audit_logs",
    "can_manage_roles",
    "can_manage_retention_policies",
    "can_discover_members",
]

# Built-in roles with their permissions
BUILTIN_ROLE_PERMISSIONS = {
    "admin": DEFINED_PERMISSIONS,  # All permissions
    "member": ["can_create_pursuits", "can_discover_members", "can_invite_members"],
    "viewer": [],  # Read-only org access
}

# =============================================================================
# v3.4: AUDIT PIPELINE CONFIGURATION
# =============================================================================
AUDIT_CONFIG = {
    "retention_days": int(os.getenv("AUDIT_RETENTION_DAYS", "365")),
    "stream_batch_size": int(os.getenv("AUDIT_STREAM_BATCH_SIZE", "100")),
    "async_timeout_ms": 50,                 # Max time for async audit publish
    "enable_correlation": True,             # Track multi-event operation correlation
}

# Audit event types
AUDIT_EVENT_TYPES = [
    "AUTH_LOGIN",
    "AUTH_LOGOUT",
    "AUTH_FAILED",
    "RESOURCE_ACCESS",
    "RESOURCE_CREATE",
    "RESOURCE_UPDATE",
    "RESOURCE_DELETE",
    "PERMISSION_CHANGE",
    "POLICY_CHANGE",
    "CONFIG_CHANGE",
    "DATA_EXPORT",
    "ADMIN_ACTION",
]

# Audit event outcomes
AUDIT_OUTCOMES = ["SUCCESS", "FAILURE", "DENIED"]

# =============================================================================
# v3.4: METHODOLOGY ARCHETYPES CONFIGURATION
# =============================================================================
METHODOLOGY_ARCHETYPES = [
    "lean_startup",     # "Does this work?"
    "design_thinking",  # "Does anyone want this?"
    "stage_gate",       # "Can we build this responsibly?"
    "triz",             # "How do we solve the impossible?" (v3.6.1)
    "blue_ocean",       # "Are we in the right ocean?" (v3.6.1)
    "ad_hoc",           # "What does my best work look like?" (v3.7.1 - Freeform)
    "emergent",         # Synthesized from ad-hoc patterns
]

# Default archetype for backward compatibility
DEFAULT_METHODOLOGY_ARCHETYPE = "lean_startup"

# Methodology coaching language styles
METHODOLOGY_COACHING_STYLES = {
    "lean_startup": {
        "language_style": "experiment_focused",
        "framing": "hypothesis_driven",
        "backward_iteration": "pivot_is_progress",
    },
    "design_thinking": {
        "language_style": "empathy_oriented",
        "framing": "human_centered",
        "backward_iteration": "feature_not_failure",
    },
    "stage_gate": {
        "language_style": "governance_aware",
        "framing": "gate_criteria_explicit",
        "backward_iteration": "requires_gate_approval",
    },
    "adhoc": {
        "language_style": "flexible",
        "framing": "innovator_led",
        "backward_iteration": "open",
    },
    "emergent": {
        "language_style": "discovery_oriented",
        "framing": "pattern_recognition",
        "backward_iteration": "natural_flow",
    },
}

# =============================================================================
# v3.4: TOKEN BUDGET UPDATE (Extended for enterprise context)
# =============================================================================
TOKEN_BUDGET_V34 = {
    "system_prompt": 1800,                  # +300 for convergence + IDTFS patterns
    "scaffolding_context": 1500,            # Unchanged
    "conversation_history": 3000,           # Unchanged
    "team_context": 1500,                   # Unchanged from v3.3
    "convergence_context": 800,             # NEW: Convergence state, criteria, readiness
    "org_intelligence_context": 700,        # NEW: Org-level patterns for coaching
    "user_response_generation": 2200,       # Unchanged
    "total_max": 11500,                     # +1500 from v3.3 (10,000)
}

# v3.4 Redis Consumer Groups
V34_CONSUMER_GROUPS = [
    "audit-persistence-consumer",           # Reads audit events, persists to MongoDB
    "convergence-analytics-consumer",       # Tracks convergence patterns
    "discovery-activity-consumer",          # Feeds IDTFS events to activity streams
]

# =============================================================================
# v3.7.1: EMS PROCESS OBSERVATION ENGINE CONFIGURATION
# =============================================================================
EMS_CONFIG = {
    "observation_enabled": True,
    "significant_gap_hours": 24,          # Time gaps > this are recorded as temporal patterns
    "synthesis_threshold_pursuits": 3,     # Minimum ad-hoc pursuits before synthesis offered
    "high_confidence_threshold": 5,        # Pursuits for high-confidence synthesis
    "synthesis_trigger_on_completion": True,
    "synthesis_trigger_on_threshold": True,
    "synthesis_trigger_manual": True,
}

# EMS Observation Types with default signal weights
EMS_OBSERVATION_TYPES = {
    "ARTIFACT_CREATED": {"weight": 0.8, "description": "Artifact creation"},
    "TOOL_INVOKED": {"weight": 0.7, "description": "Tool invocation"},
    "DECISION_MADE": {"weight": 0.9, "description": "Explicit decision point"},
    "TEMPORAL_PATTERN": {"weight": 0.5, "description": "Time gap pattern"},
    "COACHING_INTERACTION": {"weight": 0.3, "description": "Coaching (external influence)"},
    "ELEMENT_CAPTURED": {"weight": 0.7, "description": "Innovation element captured"},
    "RISK_VALIDATION": {"weight": 0.8, "description": "RVE experiment"},
}

# EMS Observation Status values
EMS_OBSERVATION_STATUS = ["ACTIVE", "PAUSED", "COMPLETED", "ABANDONED"]

# EMS Synthesis Eligibility levels
EMS_SYNTHESIS_ELIGIBILITY = ["NOT_ENOUGH_DATA", "ELIGIBLE", "HIGH_CONFIDENCE"]

# Ad-Hoc pursuit coaching configuration
ADHOC_COACHING_CONFIG = {
    "mode": "NON_DIRECTIVE",
    "proactive_triggers_enabled": False,
    "socratic_questioning_enabled": False,
    "convergence_detection_enabled": False,
    "methodology_vocabulary_visible": False,
    "available_on_request": True,
    "tag_interactions_as_influence": True,
    "per_turn_token_budget": 12500,  # Less than archetype-guided pursuits
}

# EMS Redis consumer group
EMS_CONSUMER_GROUP = "ems-observer"

# EMS event stream
EMS_EVENT_STREAM = "inde:events:ems"

# =============================================================================
# DEMO MODE CONFIGURATION
# =============================================================================
DEMO_USER_ID = "demo_user"
DEMO_USER_NAME = "Demo Innovator"
LEGACY_USER_EMAIL = "legacy@inde.local"
LEGACY_USER_NAME = "Legacy System User"
