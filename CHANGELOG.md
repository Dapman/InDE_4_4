# InDE MVP Changelog

## [4.4.1] — 2026-03-17 "Innovation Vitals"

### Series
InDE v4.x — Momentum Management. v4.4.1 adds the Innovation Vitals panel to
Admin Diagnostics, enabling real-time behavioral analysis of beta testers.

### Added
**Innovation Vitals Panel — Admin Diagnostics**
- New "Innovator Vitals" tab as first tab in Diagnostics panel
- Per-user behavioral intelligence aggregation from existing MongoDB collections
- Engagement status classification: ENGAGED, EXPLORING, AT RISK, DORMANT, NEW
- Summary bar with status counts and color indicators
- Sortable table with columns: Innovator, Experience, Pursuits, Phase, Artifacts, Sessions, Status
- Expandable row details: Last Login, Session Duration, Member Since
- Status and experience level filter dropdowns
- Client-side search by name or email
- CSV export of current filtered view
- Auto-refresh every 120 seconds

**Backend Aggregation Endpoint**
- GET /api/system/diagnostics/innovator-vitals (admin-only)
- InnovatorVitalsService class for efficient MongoDB aggregation
- Response envelope with users array, summary counts, and warnings

### Architecture
- New module: app/modules/diagnostics/innovator_vitals.py
- New component: frontend/src/components/admin/InnovatorVitalsTab.jsx
- Zero changes to coaching logic (ODICM, scaffolding, IML, RVE)
- Read-only queries against existing collections

---

## [4.4.0] — 2026-03-XX "The Learning Engine"

### Series
InDE v4.x — Momentum Management. v4.4 closes the intelligence loop opened by the
entire v4.x series: momentum signals accumulated across pursuits become cross-innovator
patterns. The IML learns what keeps innovators moving forward. The coach adapts.

### Added
[filled in at end of build]

### Architecture
- GitHub: https://github.com/Dapman/InDE_4_4
- Deployment: Local development only
- v3.16.0 beta testing continues unaffected
- InDE_4_3 preserved at ~/InDE_4_3 — not modified

---

## [4.2.0] — 2026-03-15 "The Depth Frame"

### Series
InDE v4.x — Momentum Management. v4.2 extends momentum management beyond
session boundaries with depth-framed re-entry and async re-engagement.

### Added
**Momentum-Aware Re-Entry System — app/modules/reentry/**
- Personalized coach opening turns for returning users based on last
  session's momentum state and gap duration
- Depth-framed context assembly from session history
- Re-entry opening library with pursuit-specific templates

**Async Re-Engagement System — app/modules/reengagement/**
- Lightweight outreach (48-72h) for innovators who haven't returned
- Coach-voiced pursuit-specific question delivery
- Re-engagement tracking and analytics

### Changed
- ODICM first-turn detection extended to support re-entry context injection
- Admin diagnostics extended with re-engagement metrics

---

## [4.1.0] — 2026-03-14 "The Momentum Engine"

### Series
InDE v4.x — Momentum Management. v4.1 introduces the Momentum Management
Engine (MME) — the intelligence layer that makes the v4.0 bridge context-aware,
pursuit-specific, and dynamically adaptive to each innovator's conversational
energy.

### Added
**Momentum Management Engine — app/momentum/**

signal_collectors.py:
- MomentumSignals dataclass: 4 dimensions (response_specificity, conversational_lean,
  temporal_commitment, idea_ownership), each 0.0–1.0
- ResponseSpecificityCollector: word count + precision/vagueness pattern scoring
- ConversationalLeanCollector: forward energy vs. closure language detection
- TemporalCommitmentCollector: future action reference detection
- IdeaOwnershipCollector: possessive/active vs. distancing/passive framing
- collect_signals(): unified entry point for all four collectors

momentum_engine.py:
- SessionMomentumState: live per-session state (turn_count, signal_history, composite_score, tier)
- MomentumSnapshot: persistence dataclass for session exit
- MomentumManagementEngine: per-session intelligence module
  - process_turn(): signal extraction + rolling-window composite update
  - Rolling window: 5 turns, recency-discounted (10% discount per position back)
  - Composite weights: specificity 0.30, lean 0.25, commitment 0.25, ownership 0.20
  - Tier thresholds: HIGH >=0.70, MEDIUM >=0.45, LOW >=0.25, CRITICAL >=0.0
  - _build_context(): tier-differentiated coaching guidance for ODICM injection
  - snapshot(): session exit capture

bridge_library.py:
- BRIDGE_LIBRARY: vision x 4 tiers, fear x 4 tiers, validation x 4 tiers, _fallback x 4 tiers
- {idea_domain}, {idea_summary}, {user_name}, {persona} placeholders
- All templates are questions (end with '?') — no methodology terminology

bridge_selector.py:
- BridgeSelector: replaces v4.0 random momentum_bridge_generator()
- Tier-aware selection (HIGH tier -> advance bridges, CRITICAL tier -> reconnection bridges)
- Pursuit context injection with graceful fallback for missing values
- Recently-used deduplication (last 3 bridges)

momentum_persistence.py:
- MomentumPersistence: MongoDB persistence service
- save_snapshot() -> momentum_snapshots collection (90-day TTL index)
- contribute_iml_pattern() -> iml_patterns collection (momentum_trajectory type)
- get_momentum_summary() -> per-pursuit health aggregation

### Changed
**ODICM Turn Pipeline:**
- MME instantiated at session creation, snapshotted at session end
- process_turn() called on every innovator message
- COACHING TONE GUIDANCE block prepended to ODICM system prompt each turn
- Artifact completion bridge upgraded: BridgeSelector replaces random selection
- Bridge now momentum-tier-aware and pursuit-context-parameterized

**Coaching Convergence Protocol:**
- check_convergence() accepts optional momentum_context
- HIGH tier: convergence threshold lowered by 0.05
- LOW tier: threshold raised by 0.08 / CRITICAL: raised by 0.15
- Backward compatible — no change when momentum_context is None

**Admin Telemetry (DiagnosticsAggregator):**
- momentum_health section added: total_sessions, avg_momentum_score,
  tier_distribution, bridge_delivery_rate, bridge_response_rate,
  post_vision_exit_rate (the primary v4.x success metric)

### Architecture
- New collection: momentum_snapshots (90-day TTL, indexed by pursuit_id, gii_id)
- New IML pattern type: momentum_trajectory (written at pursuit terminal states)
- GitHub: https://github.com/Dapman/InDE_4_1 (fresh history from v4.0.0 baseline)
- Deployment: Local development only
- v3.16.0 beta testing continues unaffected on InDEVerse-1
- InDE_4 (v4.0.0) preserved at ~/InDE_4 — not modified

### What Claude Code Must NOT Change
- Display Label Registry and all v4.0 language changes (complete — do not touch)
- Navigation labels, onboarding flow copy (complete from v4.0)
- 5-container Docker architecture
- All v3.16 / v4.0 API contracts
- IKF, federation, GII, RBAC, audit logging
- Any active Digital Ocean configuration or v3.16 deployment

---

## [4.0.0] — 2026-03-14 "The Coherence Build"

### Series
v4.0 begins the Momentum Management series. It is a coherence build —
zero new features, zero functional regression. Only what the innovator
reads changes.

### Changed

- **Display Label Registry Extended** (`app/shared/display_labels.py`)
  - 7 new categories: `workflow_step`, `artifact_panel`, `pursuit_state_display`,
    `onboarding_path`, `innovator_role`, `depth_progress`, `re_engagement`
  - New methods: `get_workflow_step()`, `get_pursuit_state()`
  - Novice suppression for `methodology_selection` step

- **Frontend Navigation Labels** (innovator-facing goal vocabulary)
  - `CoachMessage.jsx`: "Fear Extraction" → "Protecting Your Idea"
  - `ChatHeader.jsx`: All mode labels updated to goal vocabulary
  - `CommandPalette.jsx`: Commands use action-oriented language
  - `ChatInput.jsx`: Placeholders reframed as questions
  - `ScaffoldingPanel.jsx`: "Fears & Risks" → "Risks & Protections"
  - `ArtifactsPanel.jsx`: Group labels use innovator vocabulary
  - `artifactParser.js`, `print.js`: Artifact titles reframed

- **Coaching Language Adapters** (`app/coaching/methodology_archetypes.py`)
  - Added `MOMENTUM_BRIDGES` templates for session close/re-engagement
  - New methods: `get_session_close_message()`, `get_re_engagement_message()`,
    `get_depth_acknowledgment()`

- **Momentum Telemetry** (`app/services/telemetry.py`)
  - 8 new momentum events: `session_opened`, `session_closed`, `re_engaged`,
    `long_gap_return`, `depth_advanced`, `depth_acknowledged`, `bridge_shown`,
    `context_restored`
  - Helper function `track_momentum()` for standardized event properties

### Architecture
- GitHub: InDE_4 repository (fresh history from v3.16.0 baseline)
- Deployment: Local development only — no Digital Ocean in v4.x series
- v3.16.0 beta testing continues unaffected on InDEVerse-1

### Verification
- All modified Python files pass syntax validation
- No "Fear Extraction" or "Vision Formulator" terminology remains in user-facing code
- Display Label Registry: 38 categories, 199 labels registered

---

## v3.16.0 — Production Trust (March 2026)

**Release Date:** 2026-03-08

A production-readiness release focused on establishing trust through secure communications, reliable email delivery, innovator identity, and operational observability.

### Added

- **HTTPS via Let's Encrypt**: Automatic SSL certificate provisioning and renewal
  - Nginx reverse proxy with Certbot integration
  - Auto-renewal cron job for certificates
  - HTTP to HTTPS redirect for all traffic

- **Transactional Email Service**: SendGrid/SMTP integration for reliable email delivery
  - Password reset emails with secure tokens
  - Welcome emails for new user registration
  - Configurable email templates with InDE branding

- **Global Innovator Identifier (GII)**: Automatic assignment at registration
  - Unique GII format: `GII-XXXXXXXX` (8-character alphanumeric)
  - Stored in user profile, displayed in settings
  - Foundation for cross-pursuit analytics

- **Behavioral Telemetry**: GII-keyed event tracking for product analytics
  - Session start/end events with duration
  - Feature usage events (coaching, artifacts, retrospectives)
  - Non-PII event schema with GII correlation

### Fixed

- **Deployment Baseline**: Codified all Digital Ocean deployment fixes
  - WebSocket authentication using `decode_token` (not `verify_token`)
  - UUID generation fallback for non-HTTPS contexts
  - CRLF line ending validation in `.env` files
  - Environment variable persistence across container restarts
  - `.editorconfig` enforcing LF line endings

### Technical Details

- Added `scripts/validate_env.sh` for pre-deployment environment validation
- Added `scripts/migrate_v315_data.sh` for data migration from v3.15
- MongoDB data migration archive support for seamless upgrades

---

## v3.15.0 — First User Ready (March 2026)

**Release Date:** 2026-03-06

A user experience and resilience release focused on ensuring an external user can successfully complete onboarding, understand the workspace without guidance, and have robust coaching sessions even when the LLM has intermittent issues.

### Added

- **Onboarding Gap Remediation**: All CRITICAL and HIGH findings from the v3.14 audit implemented and verified
  - All 5 onboarding screens behave as specified
  - All 4 completion criteria now tracked correctly

- **Guided Discovery Layer**: Lightweight ambient guidance for first-time users
  - `HelpTooltip` components on all 5 workspace zone headers
  - `HintCard` components in empty zones for first-time users
  - `GettingStartedChecklist` widget in workspace sidebar
  - Discovery state persisted in user profile

- **API Rate Limiting**: Per-user and per-IP rate limiting middleware
  - Per-user coaching limit (default 30 requests/minute)
  - Per-IP authentication limit (default 10 attempts/5 minutes)
  - Sliding window implementation, no Redis dependency

- **LLM Resilience**: Retry logic and timeout handling for coaching endpoint
  - 3-attempt retry with exponential backoff (2s → 4s → 8s)
  - 30-second client-side timeout indicator with cancel option
  - Human-readable error messages for all failure scenarios

- **Error Recovery**: React ErrorBoundary wrapping all workspace zones
  - Zone-specific fallback cards with refresh button
  - Frontend errors logged to diagnostics error buffer
  - Global exception handler for user-friendly 500 messages

- **Discovery API Endpoints**:
  - `GET /api/v1/user/discovery` - Returns discovery state
  - `POST /api/v1/user/discovery/dismiss` - Persists hint dismissal
  - `POST /api/v1/user/discovery/reset` - Resets all dismissed hints
  - `POST /api/v1/errors/client` - Receives frontend error reports

### New Environment Variables (all optional with safe defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `INDE_COACHING_RATE_LIMIT` | 30 | Per-user coaching rate limit (requests/minute) |
| `INDE_AUTH_RATE_LIMIT` | 10 | Per-IP auth attempt limit |
| `INDE_AUTH_RATE_LIMIT_WINDOW` | 300 | Auth rate limit window (seconds) |

### New Files

```
app/middleware/
└── rate_limiting.py              # Sliding window rate limiter

app/api/
├── user_discovery.py             # User discovery state API
└── client_errors.py              # Frontend error logging

frontend/src/components/
├── discovery/
│   ├── GettingStartedChecklist.jsx
│   ├── HintCard.jsx
│   └── HelpTooltip.jsx
└── common/
    └── ErrorBoundary.jsx

frontend/src/api/
└── discovery.js                  # Discovery API client
```

### Changed

- Users collection: `discovery` subdocument added (additive, no migration required)
- All coaching endpoint error messages updated to user-friendly language
- Frontend error reports now appear in diagnostics error buffer

---

## v3.14.0 — Operational Readiness (March 2026)

**Release Date:** 2026-03-05

An operational readiness release that adds system health monitoring, onboarding completeness tracking, and backup automation for self-hosted deployments.

### Added

- **In-App Diagnostics Panel**: Admin-only system health dashboard at `/diagnostics`
  - Real-time error counts by severity (ERROR, WARNING, CRITICAL)
  - Onboarding funnel visualization with completion rates
  - System health status monitoring
  - Recent error log table with filtering
  - Auto-refresh every 30 seconds

- **Onboarding Completeness Audit**: Funnel metrics tracking four completion criteria
  - `vision_artifact_created` - First vision artifact
  - `fear_identified` - First fears artifact
  - `methodology_selected` - Methodology guidance engagement
  - `iml_pattern_engaged` - IKF pattern surfaced

- **Error Buffer**: Thread-safe circular buffer for application error events
  - In-memory storage (never persisted)
  - 100-entry capacity
  - Severity-level filtering

- **Backup & Restore Scripts**: MongoDB backup automation
  - `scripts/backup.sh` - Timestamped archive creation with compression
  - `scripts/restore.sh` - Archive restoration with safety prompts
  - Configurable retention (default 30 days)
  - Authentication support

### New Files

```
app/modules/diagnostics/
├── __init__.py
├── error_buffer.py          # Thread-safe error ring buffer
├── aggregator.py            # Health metric aggregation
└── onboarding_metrics.py    # Onboarding funnel service

app/migrations/
└── v314_operational.py      # Collection & index creation

scripts/
├── backup.sh                # MongoDB backup automation
└── restore.sh               # Archive restoration

frontend/src/pages/
└── DiagnosticsPage.jsx      # Admin diagnostics panel

ONBOARDING_AUDIT.md          # Instrumentation documentation
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/diagnostics` | System diagnostics aggregation (admin) |
| GET | `/api/system/diagnostics/onboarding` | Onboarding funnel stats (admin) |
| GET | `/api/system/diagnostics/errors` | Recent error entries (admin) |

### Schema Changes

**New collection: `onboarding_metrics`**
- `user_id`: User identifier
- `started_at`: Session start timestamp
- `completed_at`: Completion timestamp (null if incomplete)
- `criteria`: Object with four boolean completion flags
- `screen_reached`: Integer (1-5) for funnel stage
- `duration_seconds`: Time to completion

**New indexes:**
- `onboarding_metrics_user_started`: (user_id, started_at DESC)
- `onboarding_metrics_started`: (started_at DESC)

### Changed

- Global exception handler now records errors to diagnostics buffer
- LeftSidebar navigation shows Diagnostics link for admin users

### Technical Notes

- Diagnostics panel requires `role: "admin"`
- All instrumentation wrapped in try/catch for graceful degradation
- Migration runs automatically on startup (idempotent)
- No breaking changes to existing APIs

---

## v3.13.0 — Innovator Experience Polish (March 2026)

**Release Date:** 2026-03-05

A workspace quality-of-life release that makes InDE feel like a thoughtfully designed environment. Archiving keeps the workspace clean, search makes history useful, export makes work portable, and notification preferences make the platform respectful of attention.

### Added

- **Pursuit Archiving**: Move any pursuit out of the active workspace while preserving all data. Archived pursuits are stored separately and can be restored at any time.
- **Pursuit Restoration**: Return an archived pursuit to the active workspace with a single action.
- **Archived Pursuits View**: Dedicated list showing all archived pursuits with restore functionality.
- **Coaching Conversation Search**: Full-text search across session history within a pursuit, with 3-turn context window around each match. Uses MongoDB text indexes for performance.
- **Pursuit Export Packaging**: Download a complete pursuit as a ZIP file containing conversations, vision artifacts, fear register, milestone timeline, and export manifest.
- **Notification Preferences**: UI and API for controlling activity feed visibility, mention alerts, state change notifications, contribution alerts, and polling interval.
- **MongoDB Text Index**: Full-text search index on conversation_history collection.
- **Compound Archive Index**: Optimized queries for archived/active pursuit filtering.

### New Files

```
app/
├── modules/
│   ├── pursuit/
│   │   ├── __init__.py
│   │   ├── archive.py          # Archive/restore service
│   │   └── export.py           # ZIP export generation
│   └── search/
│       ├── __init__.py
│       └── conversation_search.py  # Full-text search
└── migrations/
    └── v313_experience_polish.py   # Add archive fields

frontend/src/components/
├── pursuit/
│   ├── ArchiveButton.jsx        # Archive/restore button
│   └── ArchivedPursuitsList.jsx # Archived pursuits panel
├── search/
│   └── ConversationSearch.jsx   # Inline search UI
├── export/
│   └── ExportButton.jsx         # Export download button
└── settings/
    └── NotificationPreferences.jsx  # Notification settings
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pursuits/{id}/archive` | Archive a pursuit |
| POST | `/api/pursuits/{id}/restore` | Restore an archived pursuit |
| GET | `/api/pursuits/archived/list` | List archived pursuits |
| GET | `/api/pursuits/{id}/export` | Download pursuit as ZIP |
| GET | `/api/coaching/{id}/search?q=` | Search conversation history |
| GET | `/api/account/notification-preferences` | Get notification settings |
| PUT | `/api/account/notification-preferences` | Update notification settings |

### Changed

- Active pursuit list queries now exclude archived pursuits by default
- Pursuit model: added `is_archived` (bool, default false) and `archived_at` fields
- List pursuits endpoint accepts `include_archived` query parameter

### Architecture

- Export packages generated on-demand in memory — not persisted server-side
- Conversation search scoped per-pursuit — cross-pursuit search is a future enhancement
- Notification preferences stored within existing user.preferences object — no schema migration required

---

## v3.12.0 — Innovator Trust & Completeness (March 2026)

**Release Date:** 2026-03-05

A trust-building release that delivers essential account management features expected by modern SaaS users: password reset, session management, and GDPR-compliant account deletion with a 14-day cooling-off period.

### Added

- **Password Reset Flow**: Secure, time-limited, single-use tokens with email delivery (graceful degradation when SMTP not configured)
- **Session Management**: View and terminate active sessions from Settings page; see device type, IP address, and login time
- **Account Deletion**: Two-phase deletion with 14-day grace period; email confirmation with cancellation link; GDPR/CCPA compliant data removal
- **Email Service**: SMTP integration for transactional emails with graceful degradation; supports password reset and deletion confirmation
- **Admin Password Reset Link**: Endpoint for self-hosted deployments to generate reset links without SMTP

### New Files

```
app/
├── services/
│   ├── __init__.py
│   └── email_service.py      # SMTP email with graceful degradation
├── modules/
│   └── account/
│       ├── __init__.py
│       ├── deletion.py       # Two-phase account deletion
│       └── password_reset.py # Secure token-based reset
├── api/account.py            # Account management endpoints
└── migrations/
    └── v312_account_trust.py # Add status/deletion fields to users

frontend/src/
├── pages/
│   ├── ForgotPasswordPage.jsx
│   ├── ResetPasswordPage.jsx
│   └── CancelDeletionPage.jsx
└── components/settings/
    ├── SessionManagement.jsx
    ├── PasswordChange.jsx
    └── AccountDeletion.jsx
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/account/forgot-password` | Request password reset email |
| POST | `/api/account/reset-password` | Reset password with token |
| POST | `/api/account/validate-reset-token` | Check token validity |
| GET | `/api/account/password-reset-status` | Check if SMTP configured |
| GET | `/api/account/sessions` | List active sessions |
| DELETE | `/api/account/sessions/{id}` | Terminate specific session |
| DELETE | `/api/account/sessions` | Terminate all sessions |
| PUT | `/api/account/change-password` | Change password (authenticated) |
| POST | `/api/account/request-deletion` | Initiate account deletion |
| GET | `/api/account/cancel-deletion` | Cancel pending deletion |
| GET | `/api/account/deletion-status` | Check deletion status |
| POST | `/api/account/admin/users/{id}/reset-link` | Admin: generate reset link |

### Schema Changes

**users collection:**
- `status`: "active" | "deactivated" | "deleted"
- `deletion_requested_at`: ISO timestamp
- `deletion_scheduled_for`: ISO timestamp (14 days after request)
- `deletion_cancellation_token`: cryptographic token for email link
- `deleted_at`: ISO timestamp when fully deleted

**New collection: `password_reset_tokens`**
- `token_hash`: SHA-256 hash (never store plaintext)
- `user_id`: reference to user
- `expires_at`: datetime with TTL index (auto-delete expired tokens)
- `used`: boolean (single-use enforcement)

### Security Features

- Password reset tokens SHA-256 hashed before storage
- Tokens expire after 60 minutes (configurable)
- Single-use enforcement: tokens invalidated after consumption
- All sessions revoked on password change or reset
- Account deletion requires email confirmation before processing
- 14-day cooling-off period with cancellation option
- Background job processes scheduled deletions hourly

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| SMTP_HOST | - | SMTP server hostname |
| SMTP_PORT | 587 | SMTP server port |
| SMTP_USERNAME | - | SMTP auth username |
| SMTP_PASSWORD | - | SMTP auth password |
| SMTP_FROM_ADDRESS | noreply@indeverse.com | Sender email |
| SMTP_FROM_NAME | InDE Innovation Platform | Sender name |
| SMTP_USE_TLS | true | Use STARTTLS |
| APP_BASE_URL | http://localhost:5173 | Base URL for email links |
| PASSWORD_RESET_TOKEN_EXPIRY_MINUTES | 60 | Token expiry time |
| ACCOUNT_DELETION_COOLING_OFF_DAYS | 14 | Grace period before deletion |

---

## v3.11.0 — Timeline Housekeeping & Closure (March 2026)

**Release Date:** 2026-03-05

A deliberate, scoped housekeeping build that completes and formally closes the timeline module workstream. This release adds performance indexes and team permission enforcement while retiring timeline management features that are outside InDE's coaching scope.

### Added

- **MongoDB Compound Indexes (TD-015)**: Query performance indexes on `pursuit_milestones`, `temporal_events`, and `time_allocations` collections for sustained performance as data grows
- **Team Milestone Permissions (TD-014)**: Only pursuit creators can change milestone dates, types, or delete milestones in team pursuits
- **`created_by_user_id` Field**: New milestone field tracking who created each milestone; backfilled from pursuit ownership for existing records
- **`app/database/indexes.py`**: Centralized index management module, called at startup
- **`app/scaffolding/permissions.py`**: Milestone permission enforcement utilities
- **`GET /timeline/{id}/milestone-permissions`**: New endpoint for UI to check edit permissions

### Changed

- Milestone mutation API routes now enforce creator-only permission for structural changes in team pursuits
- Milestone extraction sets `created_by_user_id` from session context
- Timeline panel shows "Locked" indicator for non-creators in team pursuits
- Inconsistency resolution buttons hidden for non-creators

### Architecture

Timeline enhancement workstream formally closed. The timeline module (v3.9 extraction, v3.10 integrity, v3.11 housekeeping) is complete. The following TD items are retired:

| TD | Description | Retirement Rationale |
|----|-------------|---------------------|
| TD-003 | Missing Milestone Detection | Project scheduling, not coaching |
| TD-004 | Compression Risk Scoring | PM risk management, not coaching |
| TD-007 | Dependency Tracking | Critical path analysis out of scope |
| TD-008 | Timeline Branching/Scenarios | PM scenario planning out of scope |
| TD-009 | Calendar Sync | Stakeholder calendar mgmt out of scope |
| TD-010 | Evidence Collection | Compliance tooling out of scope |
| TD-011 | Scaffolding Modulation by Deadline | Calendar pressure corrupts coaching quality |
| TD-012 | RVE Trigger from Milestones | RVE already triggered by conversation |
| TD-013 | Estimation Accuracy Tracking | Performance management out of scope |
| TD-016 | Natural Language Milestone Updates | Ambiguity risk in coaching context |

**Principle**: InDE captures timeline information because it reveals innovator intent and commitment. InDE does not manage timelines.

### Files Modified

```
app/
├── database/
│   ├── __init__.py         # New module
│   └── indexes.py          # New: index management
├── scaffolding/
│   ├── permissions.py      # New: permission enforcement
│   ├── engine.py           # Pass user_id to extractor
│   └── timeline_extractor.py # Add created_by_user_id
├── api/timeline.py         # Permission checks on mutations
├── main.py                 # Startup index + migration calls
└── migrations/
    └── v311_milestone_permissions.py  # New migration

frontend/
├── src/api/pursuits.js     # getMilestonePermissions API
└── src/components/panels/TimelinePanel.jsx  # Permission-aware UI
```

---

## v3.9.1 — User Provider Selection (February 2026)

**Release Date:** 2026-02-28

Adds user-facing AI provider selection to Settings, allowing users to choose between Cloud (Premium), Local (Cost-Free), or Auto provider routing with transparent cost vs quality tradeoffs.

### AI Provider Preference UI

New Settings section available to all users:

- **Provider Options**: Auto (Recommended), Cloud (Premium), Local (Cost-Free)
- **Cost/Quality Transparency**: Each option shows quality tier and cost indicator
- **Availability Status**: Real-time provider availability display
- **Fallback Warnings**: Notification when preferred provider is unavailable

### Backend Provider Preference Support

- **`get_provider_by_preference()`**: New registry method for preference-aware selection
- **`preferred_provider` Parameter**: Added to LLM Gateway `/llm/chat` endpoint
- **User Preference Storage**: Persisted in `users.preferences.llm_provider`
- **Coaching Integration**: User preference passed through entire coaching flow

### New Endpoints

- **`GET /system/llm/user-providers`**: Returns provider options and user's saved preference
- Accessible to all authenticated users (not admin-only)

### Files Modified

```
llm-gateway/
├── provider_registry.py      # Added get_provider_by_preference()
└── main.py                   # Added preferred_provider to LLMChatRequest

app/
├── api/system.py             # Added /llm/user-providers endpoint
├── api/coaching.py           # Pass user preference to engine
├── core/llm_interface.py     # Pass preferred_provider to gateway
└── scaffolding/engine.py     # Added set/get_llm_preference methods

frontend/
├── src/api/system.js         # Added getUserProviders, updateLlmPreference
└── src/pages/SettingsPage.jsx # Added AI Provider section
```

---

## v3.9.0 — Air-Gapped Intelligence (February 2026)

**Release Date:** 2026-02-28

The Air-Gapped Intelligence release enables InDE to operate without cloud connectivity by supporting local LLM inference via Ollama. Organizations with strict data sovereignty requirements can now run InDE entirely on-premises with no API calls to external services.

### Provider Registry Architecture

New LLM abstraction layer with automatic failover:

- **Provider Chain**: Configuration-driven provider ordering
- **Automatic Failover**: Primary unavailable → next provider in chain
- **Quality Tier Detection**: Automatic classification based on model capabilities
  - PREMIUM: Claude (full ODICM capabilities)
  - STANDARD: 70B+ parameter local models
  - BASIC: 7B-13B parameter local models
- **Failover Event Logging**: Redis Streams integration for observability

### Ollama Integration

Full support for local LLM inference via Ollama:

- **REST API Adapter**: `/api/chat` and `/api/generate` support
- **Model Metadata Detection**: Parameter count, context window, quantization
- **Quality Tier Assignment**: Based on model parameter count
- **Streaming Support**: SSE-compatible streaming for real-time coaching

### ODICM Prompt Calibration Layer

Quality-tier-aware prompt adaptation:

- **Premium Tier**: Full ODICM prompts, 3000 token system prompts
- **Standard Tier**: Compressed prompts, simplified reasoning chains
- **Basic Tier**: Numbered directives, explicit structure, 800 token limit
- **Methodology Keywords Preserved**: Critical coaching concepts maintained

### Docker Compose Deployment Modes

Three deployment configurations:

- **Standard** (`docker-compose.yml`): Claude API (default)
- **Air-Gapped** (`docker-compose.ollama.yml`): Ollama only
- **Hybrid** (`docker-compose.hybrid.yml`): Claude primary, Ollama failover

### Admin Panel Provider Status UI

New settings panel for administrators:

- Provider chain visualization with availability status
- Quality tier badges per provider
- Failover history timeline
- Air-gapped mode indicator

### LLM Gateway Enhancements

- **Provider Status Endpoints**: `/api/v1/providers`, `/api/v1/providers/quality-tier`
- **Failover Events Endpoint**: `/api/v1/providers/failover-events`
- **Environment Configuration**: `LLM_PROVIDER`, `LLM_PROVIDER_CHAIN`, `OLLAMA_MODEL`

### Technical Changes

- Version updated to 3.9.0 in all services
- New modules: `provider_registry.py`, `prompt_calibration.py`
- New provider: `ollama_provider.py`
- 2 new Docker Compose overlays
- Integration tests for provider architecture

### Files Added

```
llm-gateway/
├── provider_registry.py      # Provider chain management
├── providers/
│   ├── base_provider.py      # Abstract provider interface
│   ├── claude_provider.py    # Refactored Claude adapter
│   └── ollama_provider.py    # Ollama REST API adapter
└── tests/
    ├── conftest.py
    └── test_v39_providers.py

app/coaching/
└── prompt_calibration.py     # Quality-tier prompt adaptation

docker-compose.ollama.yml     # Air-gapped deployment
docker-compose.hybrid.yml     # Hybrid failover deployment

tests/
└── test_v39_airgapped.py     # Integration tests
```

### Migration Notes

- Existing v3.8 deployments continue to work unchanged (default: Claude only)
- For air-gapped deployment:
  1. Install Ollama on host system
  2. Pull model: `ollama pull llama3`
  3. Use `docker-compose.ollama.yml` overlay
- For hybrid failover: Use `docker-compose.hybrid.yml` overlay
- No database migrations required

---

## v3.8.0 — Commercial Launch Infrastructure (February 2026)

**Release Date:** 2026-02-27

The Commercial Launch Infrastructure release transforms InDE from an internal prototype into a deployable, licensable product. This release adds enterprise licensing, production deployment tooling, and customer onboarding infrastructure.

### License Validation Service (`inde-license`)

New microservice for license key management and entitlement enforcement:

- **License Key Format**: `INDE-{TIER}-{CUSTOMER_ID}-{CHECKSUM}` with CRC32 validation
- **Three License Tiers**: Professional (PRO), Enterprise (ENT), Federated (FED)
- **Grace Period State Machine**: 30-day tolerance with progressive warnings
  - Days 1-7: GRACE_QUIET (silent grace)
  - Days 8-21: GRACE_VISIBLE (warnings appear)
  - Days 22-30: GRACE_URGENT (prominent warnings)
  - Day 31+: EXPIRED (read-only mode)
- **Seat Counting**: MongoDB-based active user tracking with compliance checks
- **Offline Support**: HMAC-SHA256 signed license files for air-gapped deployments
- **Simulation Mode**: Local development without license.indeverse.com connection
- **FastAPI Endpoints**: `/health`, `/api/v1/validate`, `/api/v1/status`, `/api/v1/activate`, `/api/v1/seats`
- **74 unit tests** covering all license service modules

### Production Deployment Infrastructure

- **`deployment/docker-compose.production.yml`**: 6-service orchestration with:
  - Health checks with startup/interval/timeout configuration
  - Resource limits (CPU, memory) per container
  - Log rotation (10 files, 10MB each)
  - Volume mounts for data persistence
  - Network isolation for security
- **`deployment/.env.template`**: Documented environment configuration
- **`deployment/start.sh`**: Linux/macOS startup script with prereq checks
- **`deployment/start.ps1`**: Windows PowerShell startup script
- **`deployment/DEPLOYMENT.md`**: Comprehensive deployment guide

### First-Run Setup Wizard

6-step React wizard (`/setup`) for customer onboarding:

1. **License Activation**: Enter license key, validate with license service
2. **Organization Setup**: Create organization name and slug
3. **Admin Account**: Create first administrator with email/password
4. **API Key Configuration**: BYOK Anthropic API key entry and validation
5. **System Verification**: Health check for all InDE services
6. **Setup Complete**: Summary and launch button

Components: `SetupWizard.jsx`, `LicenseActivation.jsx`, `OrganizationSetup.jsx`, `AdminAccount.jsx`, `ApiKeyConfig.jsx`, `SystemCheck.jsx`, `SetupComplete.jsx`

### BYOK API Key Management

LLM Gateway enhancements for Bring-Your-Own-Key support:

- **`GET /api/v1/validate-key`**: Test currently configured API key
- **`POST /api/v1/validate-key`**: Test a provided key without configuring
- **`POST /api/v1/configure`**: Runtime key configuration (no restart required)
- API key validation via actual Anthropic API call
- Key stored in memory only (never persisted to disk)
- Health endpoint shows key configuration status

### License Status in Admin Panel

Settings page (`/settings`) enhancements for administrators:

- License status banner with state indicator (Active, Grace, Expired)
- Days remaining counter during grace periods
- License tier and seat usage display
- Enabled features list
- Refresh button for real-time status check

### Backend License Integration

- **`app/middleware/license.py`**: Request filtering middleware
  - Validates license on each request
  - Enforces read-only mode when expired
  - Excludes health/setup endpoints from validation
- **`app/api/system.py`**: Extended with license endpoints
  - `GET /api/system/license`: Full license status
  - `GET /api/system/first-run`: Check if setup wizard needed
  - `POST /api/system/setup-complete`: Mark setup as done

### Technical Changes

- Version updated to 3.8.0 in `app/core/config.py` and `frontend/package.json`
- LLM Gateway version updated to 3.8.0
- Settings page version display updated to 3.8.0
- Main `docker-compose.yml` includes license service

### Files Added

```
license-service/
├── models.py           # Pydantic models for license data
├── config.py           # Service configuration
├── key_generator.py    # License key generation/validation
├── crypto.py           # HMAC-SHA256 signing
├── grace_period.py     # Grace period state machine
├── seat_counter.py     # MongoDB seat counting
├── offline_validator.py # Offline license validation
├── entitlement_manager.py # Core license logic
├── main.py             # FastAPI application
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
└── tests/              # 74 unit tests

deployment/
├── docker-compose.production.yml
├── .env.template
├── start.sh
├── start.ps1
└── DEPLOYMENT.md

frontend/src/pages/setup/
├── SetupWizard.jsx
└── steps/
    ├── index.js
    ├── LicenseActivation.jsx
    ├── OrganizationSetup.jsx
    ├── AdminAccount.jsx
    ├── ApiKeyConfig.jsx
    ├── SystemCheck.jsx
    └── SetupComplete.jsx

app/middleware/
└── license.py
```

### Migration Notes

- Existing v3.7.4 deployments need a license key to continue operating
- Contact InDEVerse sales for license activation
- Setup wizard runs automatically on first deployment
- API key must be configured during setup or via environment variable

---

## v3.7.4.4 - Integration, Polish & Gradio Retirement

**Release Date:** 2026-02-20

### Returning User Experience
- Context detection algorithm: resume pursuit, portfolio overview, welcome screen, expert minimal
- WelcomePage for zero-pursuit users with capability overview cards
- User API module for session state and preferences
- Context-aware routing after authentication

### Adaptive Complexity
- Four UI complexity tiers: guided, standard, streamlined, minimal
- Experience level auto-detection from innovator maturity model
- AdaptiveVisibility component for conditional rendering
- Complexity preferences stored in uiStore with auto-detect toggle

### Backend Cleanup
- **Pydantic v2 migration**: All `class Config` converted to `model_config = ConfigDict(...)`
- **datetime.utcnow() cleanup**: All instances replaced with `datetime.now(timezone.utc)`
- Zero Pydantic deprecation warnings
- Zero deprecated datetime calls

### Gradio Retirement
- Removed Gradio UI files: `chat_interface.py`, `auth_interface.py`, `portfolio_dashboard.py`, `v34_extensions.py`
- Kept `analytics_visualizations.py` (matplotlib-based, used by reports)
- Updated `run_inde.py` to FastAPI-only mode
- FastAPI serves React production build as static files
- Single frontend: React 18 with Vite
- Updated app/ui/__init__.py to export only visualization utilities

### Static File Serving
- React build served from `frontend/dist/` via FastAPI
- Catch-all route for client-side routing (React Router)
- API routes, WebSocket, and docs routes excluded from catch-all
- Development: Vite dev server on port 5173 with proxy to FastAPI

### v3.7.4 UI Overhaul Complete
The Gradio-to-React migration is finished. InDE is now served by a
professional React 18 frontend consuming the unchanged FastAPI backend.
Five sub-builds (v3.7.4.0 through v3.7.4.4) transformed InDE from a
prototyping UI into a production-grade Innovation Development Environment.

### Technical Notes
- Bundle size: 1,001 KB JS, 70 KB CSS
- Context detection runs once after authentication
- Complexity tier affects sidebar default states and tooltip visibility
- Static file serving only active when `frontend/dist/` exists

---

## v3.7.4.3 - Intelligence, Analytics & EMS

**Release Date:** 2026-02-20

### Intelligence Panel (Right Sidebar)
- IML pattern suggestion cards with similarity badges and feedback actions (Apply, Explore, Dismiss)
- Cross-pollination insight cards with domain distance indicators and transfer probability
- Learning velocity metrics with sparkline trend visualization
- Biomimicry insights section (visible on TRIZ pursuits)
- Apply-to-chat action sends pattern context to coaching conversation

### Portfolio Dashboard (Full Page)
- Pursuit grid/list view toggle with filtering by status, methodology, health zone
- Methodology distribution donut chart (CSS-based, no external dependencies)
- Cross-pursuit pattern insights from IML
- Aggregate metric cards: active pursuits, success rate, average health, learning velocity
- Route: `/portfolio` with Briefcase icon in left sidebar

### Organization Portfolio (Full Page, Enterprise)
- Org-level aggregated analytics across all innovators
- Methodology effectiveness comparison chart (grouped bars)
- Innovation pipeline Kanban visualization (Discovery → Development → Validation → Complete)
- Learning velocity trends with industry benchmark comparison
- Team performance breakdown cards
- Route: `/org/portfolio` (visible only for enterprise users)

### IKF Federation Panels (Right Sidebar)
- **Federation Status Panel**: Connection state with human-friendly labels (Display Labels applied)
  - Incoming pattern feed with type badges and confidence indicators
  - Global benchmark comparisons with visual bars
  - Trust network relationships with sharing level indicators
- **Contribution Panel**: Queue management with review interface
  - Side-by-side preview (original vs. generalized) before sharing
  - Approve/Decline workflow with optional notes
  - Contribution history tracking
- All internal identifiers pass through Display Labels — zero schema leakage

### EMS Visual Suite
- **EMS Sidebar Tab**: Observation status indicator, inference ready notifications
- **EMS Page** (`/ems`): Full dashboard with inference results and published archetypes
  - Phase cards with confidence badges (stars: HIGH ★★★, MODERATE ★★☆, LOW ★☆☆)
  - Comparison preview against existing archetypes
  - Published methodology cards with visibility management and evolution checking
- **Review Session Interface** (`/ems/review/:sessionId`): The Crown Jewel
  - Split-screen layout: 60% visual review + 40% coaching chat
  - Draggable phase cards with inline rename (double-click)
  - Interactive activity chips: click to toggle optional/required, × to remove, + to add
  - Process flow visualization (SVG, updates in real-time as phases reorder)
  - Split-screen comparison view against existing archetypes
  - Naming panel with coach-suggested names and principles
  - Visibility selector with descriptive labels (Personal, Team, Organization, InDEVerse)
  - Publish confirmation modal with methodology summary
  - Coaching chat alongside visual review — both paths converge through Review Session API

### New Infrastructure
- 3 API client modules: `intelligence.js`, `portfolio.js`, `federation.js`
- 2 Zustand stores: `intelligenceStore.js`, `emsStore.js`
- 4 new right sidebar tabs: Intelligence, Federation, Contributions, EMS
- 3 new page routes: `/portfolio`, `/org/portfolio`, `/ems/review/:sessionId`
- Left sidebar nav entries: Portfolio, Org Portfolio (enterprise)

### Right Sidebar Tab Count (10 total)
- Scaffolding (v3.7.4.2)
- Artifacts (v3.7.4.2)
- Health (v3.7.4.2)
- Timeline (v3.7.4.2)
- Convergence (v3.7.4.2)
- Team (v3.7.4.2)
- **Intelligence** (v3.7.4.3, NEW)
- **Federation** (v3.7.4.3, NEW)
- **Contributions** (v3.7.4.3, NEW)
- **EMS** (v3.7.4.3, NEW)

### Technical Notes
- Bundle size: 997 KB JS (+86 KB from v3.7.4.2)
- CSS bundle: 70 KB (+2 KB)
- All visualizations use CSS or simple SVG — no heavy charting libraries added
- Display Labels applied throughout new panels — verified zero internal identifier exposure

### Coming in v3.7.4.4
- @Mention autocomplete in chat input
- Full artifact editor pages
- Gradio retirement

---

## v3.7.4.2 - Innovation Workspace Panels

**Release Date:** 2026-02-20

### Right Sidebar Panel System
- Tabbed panel container with adaptive tab visibility
- Notification dots for data changes on inactive tabs
- Panel-to-chat context triggers ("Ask coach" buttons)
- Panel tab persistence across pursuit switches
- Mobile bottom sheet access for panels
- Tablet overlay toggle

### Scaffolding Tracker Panel
- 40-element completion visualization grouped by 6 categories:
  - Vision (6 elements): Problem statement, solution concept, value proposition, target user, desired outcome, current situation
  - Market (7 elements): Competitive landscape, differentiation, business model, revenue model, go-to-market, market timing, adoption barriers
  - Technical (5 elements): Technical feasibility, resource requirements, team capabilities, scalability constraints, cost structure
  - Risk (6 elements): Capability fears, timing fears, market fears, execution fears, risk tolerance, regulatory concerns
  - Validation (6 elements): Hypothesis statement, test plan, key metrics, validation criteria, learning goals, decision criteria
  - Strategy (7 elements): Constraints, assumptions, success metrics, timeline, partnerships, stakeholder alignment, exit strategy
- Overall progress bar with color transitions (red <40%, amber 40-70%, green >70%)
- Click-to-expand element detail with confidence badge, timestamps, attribution
- "Ask coach" button for empty elements to trigger coaching conversation
- Team attribution on shared pursuits

### Artifact Viewer Panel
- Artifacts grouped by type (Vision, Validation, Analysis, Reports, Methodology)
- Inline preview overlay with markdown/JSON rendering
- Version badges and history
- Creation/update timestamps

### Health Dashboard Panel
- Health score gauge with circular progress ring (0-100)
- Zone badge with color coding (Healthy/Caution/At Risk)
- CSS sparkline trend visualization (7-14 days history)
- 5-component breakdown bars (Velocity, Completeness, Engagement, Risk Balance, Time Health)
- Active risk cards with severity indicators and "Discuss" action

### TIM Timeline Panel
- Phase progress bar with proportional segments per phase
- Current phase highlighting with indicator marker
- Planned vs. actual duration comparison with over/under indicators
- Velocity metrics with status badge (Ahead/On Track/Behind)
- Maturity score display with progress bar

### Convergence Indicators Panel
- Phase display with distinct visual treatment:
  - EXPLORING: Blue tint, "Gathering information" guidance
  - CONSOLIDATING: Amber tint, "Narrowing focus" guidance
  - COMMITTED: Green tint, "Moving forward" guidance
- Transition criteria checklist with satisfied/unsatisfied indicators
- "Ready to Move On" action button with confirmation dialog
- Captured outcomes from previous convergence decisions

### Team Panels (Enterprise)
- Sub-tabbed interface: Roster, Activity, Gaps
- Team roster with roles, online status, contribution counts
- Activity stream with polling refresh
- Team gap analysis with coverage visualization
- Contribution balance bars per team member

### Mobile/Tablet Responsive Design
- Mobile (<768px): Bottom action bar with panel icons, bottom sheet panels (70% height)
- Tablet (768-1023px): Toggle overlay for right sidebar
- Desktop (>1024px): Persistent right sidebar

### New Utilities
- `dateUtils.js`: formatDistanceToNow, formatShortDate, formatFullDate, daysUntil, formatDuration
- Extended uiStore with panel state management (activePanelTab, panelNotifications, mobilePanelOpen)

### Technical Notes
- Bundle size: 900 KB JS (+58 KB from v3.7.4.1)
- CSS bundle: 65 KB (+3 KB)
- All panels use React Query with 30-second staleTime and refetchInterval
- No new external dependencies (CSS-only visualizations per spec)

### Coming in v3.7.4.3
- @Mention autocomplete in chat input
- Full artifact editor pages
- Advanced analytics visualizations

---

## v3.7.4.1 - Coaching Experience & Pursuit Management

**Release Date:** 2026-02-20

### Core Coaching Experience

This build delivers the heart of InDE — the real-time streaming coaching conversation. An innovator can now create a pursuit, choose a methodology, and have a coaching conversation through the React frontend.

#### Coaching Chat Interface
- **CoachMessage**: Markdown-rendered coach responses with mode badges
- **InnovatorMessage**: Right-aligned user messages with initials avatar
- **StreamingMessage**: Real-time streaming with blinking cursor indicator
- **MomentNotification**: 6 inline notification types (Teaching, Fear, Readiness, Health Warning, Portfolio, Experiment)
- **ChatHeader**: Mode indicator + health badge + phase display
- **ChatInput**: Auto-growing textarea with Cmd+Enter, mode-aware placeholders
- **ChatContainer**: Full orchestration — WebSocket, history, REST fallback

#### Pursuit Creation Wizard (NewPursuitPage)
- **Step 1**: Spark/problem description input
- **Step 2**: Archetype selection — 6 standard methodologies + emergent archetypes from EMS
  - Lean Startup 🔬, Design Thinking 🎨, Stage-Gate 🏗️, TRIZ 🧩, Blue Ocean 🌊, Freeform ✨
  - Emergent archetypes show ConfidenceBadge + "Discovered from practice" label
- **Step 3**: Optional time & commitment settings
- **Step 4**: Summary review and creation

#### Pursuit Explorer (LeftSidebar)
- React Query integration with 30-second polling
- Active pursuit highlighting with glow effect
- Archetype emojis and health dots per pursuit
- Completed/archived pursuits collapsible section
- Collapsed mode with icon-only view and tooltips

#### Dashboard Enhancement
- Portfolio overview with pursuit cards
- Quick stats: active/completed/total pursuits
- Empty state with onboarding for new users
- Click-to-navigate pursuit cards

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd+K | Open command palette |
| Cmd+1-9 | Switch to pursuit 1-9 |
| Cmd+N | New pursuit creation |
| Cmd+\ | Toggle left sidebar |
| Cmd+] | Toggle right sidebar |

### Command Palette Enhancements
- Dynamic pursuit switching with (current) indicator
- Coaching actions: Vision, Fear Extraction, Retrospective, Experiment
- Fuzzy search across all commands

### Coaching Mode Visual Treatment
- 6 distinct modes: coaching, vision, fear, retrospective, ems_review, crisis
- Top border accent color changes per mode
- Mode badge in chat header
- Crisis mode: red pulse animation

### Responsive Design
- Desktop (≥1024px): Full 5-zone layout
- Tablet (768-1023px): Auto-collapsed sidebar
- Mobile (<768px): Hidden sidebar, wider message bubbles (90%)

### New Dependencies
- `framer-motion`: Message animations and transitions

### Technical Notes
- Bundle size: 842 KB JS (+336 KB from v3.7.4.0 due to framer-motion)
- CSS bundle: 62 KB
- WebSocket streaming with exponential backoff reconnection
- REST fallback when WebSocket unavailable

### Coming in v3.7.4.2
- Innovation Workspace Panels
- Scaffolding tracker panel
- Artifacts preview panel
- Analytics charts

---

## v3.7.4.0 - UI Foundation: React + Design System

**Release Date:** 2026-02-19

### New Frontend Infrastructure

This build establishes the architectural foundation for InDE's modern React frontend. Every subsequent v3.7.4.x build constructs upon this foundation.

#### Core Technologies
- **React 18 + Vite**: Modern build tooling with hot module replacement
- **Tailwind CSS v3**: Utility-first styling with InDE design tokens
- **shadcn/ui**: Component library (Button, Input, Dialog, Command, etc.)
- **Zustand**: Lightweight state management
- **React Query**: Server state and caching
- **React Router v6**: Client-side routing

#### Design System - "InDE Forge"
- Comprehensive color system:
  - InDE brand palette (inde-50 through inde-950)
  - Surface colors for dark/light themes
  - Phase colors (Vision, Pitch, De-Risk, Build, Deploy)
  - Confidence tiers (High, Moderate, Low, Insufficient)
  - Health zones (Thriving, Healthy, Caution, At Risk, Critical)
- Typography: DM Sans (display), Source Sans 3 (body), JetBrains Mono (code)
- Spacing system with sidebar/topbar/statusbar presets
- Animation presets (fade-in, slide-in, shimmer)

#### 5-Zone Layout Shell
- Zone 1: TopBar with logo, pursuit dropdown, search, notifications, theme toggle
- Zone 2: LeftSidebar with pursuit list and navigation (collapsible)
- Zone 3: WorkCanvas with React Router Outlet
- Zone 4: RightSidebar intelligence panel (placeholder)
- Zone 5: StatusBar with connection status, phase, version
- Responsive breakpoints: Desktop (1024px+), Tablet (768px-1023px), Mobile (<768px)

#### API Client Layer
- Axios instance with auth interceptors
- API modules: auth, pursuits, coaching, artifacts, analytics, ems, ikf, system
- WebSocket client for coaching streaming with reconnection
- Display Label hook with infinite cache

#### State Management
- `authStore`: User authentication state
- `pursuitStore`: Active pursuit context and cache
- `uiStore`: Theme, panel states, command palette
- `coachingStore`: Messages, streaming, health

#### Router & Routes
- Protected routes inside AppShell
- Route stubs: Dashboard, Pursuit, Coaching, Artifacts, Analytics, EMS, IKF, Settings
- Functional LoginPage with form and demo login
- 404 NotFoundPage

#### Command Palette (Cmd+K)
- Fuzzy search across pursuits, actions, navigation
- Keyboard shortcuts:
  - Cmd+K: Open command palette
  - Cmd+\: Toggle left sidebar
  - Cmd+]: Toggle right sidebar
  - Escape: Close modals

#### Display Components
- ConfidenceBadge, PhaseBadge, HealthBadge
- DisplayLabel with hook integration
- LoadingSpinner, LoadingOverlay, LoadingPlaceholder

### Backend Additions
- GET /api/system/display-labels endpoint for frontend label caching
- `DisplayLabels.get_all_categories()` method

### Technical Notes
- Gradio remains functional in parallel on port 7860
- React dev server runs on port 5173
- Vite proxy forwards /api and /ws to FastAPI on port 8000
- Dark theme is the default experience

### Coming in v3.7.4.x
- v3.7.4.1: Coaching Chat Experience
- v3.7.4.2: Portfolio Dashboard & Pursuit Workspace
- v3.7.4.3: Intelligence Panels & Analytics
- v3.7.4.4: Final Polish & Gradio Retirement

---

## v3.7.3 - EMS Innovator Review Interface & Archetype Publisher

**Release Date:** 2026-02-19

### New Capabilities

- **Innovator Review Interface**: Coaching-assisted session to validate, refine, and name inferred methodologies
  - Phase-by-phase review with confidence indicators
  - Refinement tools: rename, reorder, add/remove, mark optional/required, merge, split
  - Comparison view against similar existing archetypes
  - Naming, description, and key principles capture

- **Archetype Publisher**: Commits approved methodologies to the Archetype Repository
  - Version 1.0 designation with provenance
  - Attribution metadata crediting the creator
  - Configurable visibility (Personal, Team, Organization, IKF-Shared)
  - Evolution tracking for methodology updates

- **Published Methodology Selection**: Emergent archetypes appear alongside established methodologies

- **IKF Integration**: Emergent methodologies shareable through federation with generalization

- **Distinctiveness Remediation**: True archetype-to-archetype similarity comparison (Audit I fix)

### EMS Pipeline Complete

The full EMS pipeline is now operational:

```
Observe freely -> Infer structure -> Review with innovator -> Publish methodology -> Select for future pursuits
```

### New Infrastructure

- `review_sessions` collection with 3 indexes
- 7 new EMS event types for review and publication workflow
- 13 new API endpoints (9 review + 4 archetype management)
- 25+ new Display Label entries across 4 categories:
  - `review_status`: INITIATED, IN_PROGRESS, APPROVED, REJECTED, ABANDONED
  - `refinement_action`: RENAMED_PHASE, REORDERED, ADDED_ACTIVITY, REMOVED_ACTIVITY, etc.
  - `methodology_visibility`: PERSONAL, TEAM, ORGANIZATION, IKF_SHARED
  - `archetype_version`: CURRENT, SUPERSEDED, EVOLVING

### UI Enhancements

- New "EMS" button in Quick Actions toolbar
- EMS Panel with three tabs:
  - My Methodologies: Published methodologies with visibility indicators
  - Discovered Patterns: Patterns awaiting review with similarity info
  - Review Session: Interactive coaching conversation interface

### API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ems/review/start/{innovator_id}` | POST | Start review session |
| `/api/ems/review/{session_id}/exchange` | POST | Coaching exchange |
| `/api/ems/review/{session_id}/status` | GET | Get review status |
| `/api/ems/review/{session_id}/name` | POST | Set methodology name |
| `/api/ems/review/{session_id}/visibility` | POST | Set visibility |
| `/api/ems/review/{session_id}/approve` | POST | Approve and publish |
| `/api/ems/review/{session_id}/reject` | POST | Reject pattern |
| `/api/ems/review/{session_id}/comparison` | GET | Compare to archetypes |
| `/api/ems/archetypes/mine` | GET | List published |
| `/api/ems/archetypes/{id}/visibility` | PUT | Update visibility |
| `/api/ems/archetypes/{id}/evolution-check` | GET | Check evolution |
| `/api/ems/archetypes/{id}/evolve` | POST | Trigger re-analysis |

### Breaking Changes

None.

### Dependencies

No new external dependencies.

---

## v3.7.2 - EMS Pattern Inference Engine & ADL Generator

**Release Date:** 2025-01-XX

### New Capabilities

- Pattern Inference Engine with 4 algorithms (sequence mining, phase clustering, transition detection, dependency analysis)
- ADL Generator producing full ADL 1.0 archetypes from inferred patterns
- Archetype similarity comparison for distinctiveness assessment

---

## v3.7.1 - EMS Process Observation Engine

**Release Date:** 2025-01-XX

### New Capabilities

- Process Observation Engine for behavior capture
- Observation types: tool invocation, artifact creation, phase transitions, decisions
- Signal weighting for external vs internal activities

---

## v3.7.0 - Display Label Registry

**Release Date:** 2025-01-XX

### New Capabilities

- Unified Display Label Registry for human-readable UI text
- Version-organized label categories
- Icon support for visual indicators
