# Onboarding Completeness Audit Report

**InDE v3.14 "Operational Readiness"**
Generated for: Onboarding Metrics Instrumentation

---

## Overview

This document describes the onboarding funnel metrics instrumentation added in v3.14. The system tracks four completion criteria that indicate a new user has successfully completed the onboarding flow and is ready to engage with the full coaching experience.

---

## Completion Criteria

| Criterion | Description | Trigger Point |
|-----------|-------------|---------------|
| `vision_artifact_created` | User has created a vision artifact | First `artifact_type="vision"` artifact created |
| `fear_identified` | User has identified at least one fear | First `artifact_type="fears"` artifact created |
| `methodology_selected` | User has engaged with methodology guidance | `METHODOLOGY_GUIDANCE` intervention triggered |
| `iml_pattern_engaged` | User has viewed IKF/IML insights | IKF patterns surfaced in coaching context |

---

## Instrumentation Points

### 1. Session Start (Screen 1)
**File:** `app/api/pursuits.py` → `create_pursuit()`
**Line:** ~96-100
**Trigger:** When a new pursuit is created
**Action:** Calls `record_session_start(user_id)` and `record_screen_reached(user_id, 1)`

```python
# v3.14: Record onboarding metrics - session start + screen 1
try:
    metrics_service = OnboardingMetricsService(db)
    await metrics_service.record_session_start(user["user_id"])
    await metrics_service.record_screen_reached(user["user_id"], 1)
except Exception as e:
    logger.warning(f"Onboarding metrics recording failed: {e}")
```

### 2. First Coaching Turn (Screen 2)
**File:** `app/api/coaching.py` → `send_coaching_message()`
**Line:** ~85-95
**Trigger:** First coaching message in a pursuit
**Action:** Calls `record_screen_reached(user_id, 2)`

```python
# v3.14: Check if this is the first coaching message for onboarding tracking
is_first_message = db.db.conversation_history.count_documents({
    "pursuit_id": pursuit_id
}) == 0
...
if is_first_message:
    metrics_service = OnboardingMetricsService(db)
    await metrics_service.record_screen_reached(user["user_id"], 2)
```

### 3. Vision Artifact Created (Screen 3)
**File:** `app/api/artifacts.py` → `create_artifact()`
**Line:** ~82-90
**Trigger:** Artifact created with `artifact_type="vision"`
**Action:** Calls `record_criterion_met(user_id, "vision_artifact_created")` and `record_screen_reached(user_id, 3)`

```python
if data.artifact_type == "vision":
    await metrics_service.record_criterion_met(user["user_id"], "vision_artifact_created")
    await metrics_service.record_screen_reached(user["user_id"], 3)
```

### 4. Fear Identified (Screen 4)
**File:** `app/api/artifacts.py` → `create_artifact()`
**Line:** ~91-94
**Trigger:** Artifact created with `artifact_type="fears"`
**Action:** Calls `record_criterion_met(user_id, "fear_identified")` and `record_screen_reached(user_id, 4)`

```python
elif data.artifact_type == "fears":
    await metrics_service.record_criterion_met(user["user_id"], "fear_identified")
    await metrics_service.record_screen_reached(user["user_id"], 4)
```

### 5. Methodology Selected
**File:** `app/scaffolding/engine.py` → `process_message()` METHODOLOGY_GUIDANCE handler
**Line:** ~1170-1177
**Trigger:** `METHODOLOGY_GUIDANCE` intervention is processed
**Action:** Calls `record_criterion_met_sync(user_id, "methodology_selected")`

```python
# v3.14: Record methodology selection for onboarding metrics
try:
    from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
    metrics = OnboardingMetricsService(self.db)
    metrics.record_criterion_met_sync(user_id, "methodology_selected")
except Exception as om_err:
    _onboarding_logger.warning(f"Methodology selection recording failed: {om_err}")
```

### 6. IML Pattern Engaged
**File:** `app/scaffolding/engine.py` → `process_message()` IKF context builder
**Line:** ~1068-1075
**Trigger:** IKF patterns are successfully surfaced (pattern_count > 0)
**Action:** Calls `record_criterion_met_sync(user_id, "iml_pattern_engaged")`

```python
# v3.14: Record IML pattern engagement for onboarding metrics
if ikf_context.get('pattern_count', 0) > 0:
    try:
        from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
        metrics = OnboardingMetricsService(self.db)
        metrics.record_criterion_met_sync(user_id, "iml_pattern_engaged")
    except Exception as om_err:
        _onboarding_logger.warning(f"IML engagement recording failed: {om_err}")
```

---

## Data Schema

### Collection: `onboarding_metrics`

```json
{
  "_id": ObjectId,
  "user_id": "string",
  "started_at": "ISO 8601 timestamp",
  "completed_at": "ISO 8601 timestamp | null",
  "criteria": {
    "vision_artifact_created": boolean,
    "fear_identified": boolean,
    "methodology_selected": boolean,
    "iml_pattern_engaged": boolean
  },
  "screen_reached": integer (1-5),
  "duration_seconds": integer | null
}
```

### Indexes

Created by migration `v314_operational.py`:

1. **onboarding_metrics_user_started** - Compound index on `(user_id, started_at DESC)`
   - Used for finding user's most recent session

2. **onboarding_metrics_started** - Single index on `started_at DESC`
   - Used for time-range aggregations in funnel stats

---

## Screen Mapping

The "screens" in onboarding metrics are conceptual milestones, not literal UI screens:

| Screen | Milestone |
|--------|-----------|
| 1 | NewPursuitPage - spark entry / pursuit created |
| 2 | First coaching turn received |
| 3 | Vision element captured |
| 4 | Fear element captured |
| 5 | Dashboard ready (all criteria met) |

Screen 5 is implicit - when all four criteria are met, `completed_at` is set.

---

## Funnel Statistics API

The `get_funnel_stats(days=30)` method returns aggregated statistics:

```json
{
  "period_days": 30,
  "total_sessions": 150,
  "completed_sessions": 89,
  "completion_rate": 0.593,
  "criteria_rates": {
    "vision_artifact_created": 0.78,
    "fear_identified": 0.65,
    "methodology_selected": 0.71,
    "iml_pattern_engaged": 0.42
  },
  "average_duration_seconds": 1847,
  "screen_drop_off": {
    "screen_1": 12,
    "screen_2": 18,
    "screen_3": 15,
    "screen_4": 8,
    "screen_5": 8
  }
}
```

---

## Extending the Metrics

### Adding New Criteria

1. Add the new criterion to the `valid_criteria` set in `OnboardingMetricsService.record_criterion_met_sync()`
2. Add the criterion to the default `criteria` dict in `record_session_start_sync()`
3. Add the criterion name to `criteria_names` in `get_funnel_stats_sync()`
4. The schema is forward-compatible - new criteria fields will be added to existing documents on update

**Example: Adding "first_milestone_created"**

```python
# In record_session_start_sync:
"criteria": {
    "vision_artifact_created": False,
    "fear_identified": False,
    "methodology_selected": False,
    "iml_pattern_engaged": False,
    "first_milestone_created": False,  # NEW
}

# In record_criterion_met_sync:
valid_criteria = {
    "vision_artifact_created", "fear_identified",
    "methodology_selected", "iml_pattern_engaged",
    "first_milestone_created",  # NEW
}

# In get_funnel_stats_sync:
criteria_names = [
    "vision_artifact_created", "fear_identified",
    "methodology_selected", "iml_pattern_engaged",
    "first_milestone_created",  # NEW
]
```

### Adding New Screens

1. Update `record_screen_reached_sync()` to accept higher screen numbers
2. Update the `screen_drop_off` loop range in `get_funnel_stats_sync()`
3. Update the Screen Mapping table in this document

### Best Practices

- **Idempotent recording**: All recording methods are idempotent - calling them multiple times with the same criterion has no additional effect
- **Graceful degradation**: All instrumentation points wrap metrics calls in try/except to prevent onboarding from breaking if metrics fail
- **Backward compatibility**: The schema allows new fields without breaking existing records
- **No user-facing impact**: Metrics instrumentation is observational only - it does not alter the onboarding flow behavior

---

## Files Modified in v3.14

| File | Purpose |
|------|---------|
| `app/modules/diagnostics/__init__.py` | Module exports |
| `app/modules/diagnostics/error_buffer.py` | Error buffer (new) |
| `app/modules/diagnostics/onboarding_metrics.py` | Metrics service (new) |
| `app/migrations/v314_operational.py` | Collection/index creation (new) |
| `app/api/pursuits.py` | Session start + screen 1 instrumentation |
| `app/api/artifacts.py` | Vision + fear criterion instrumentation |
| `app/api/coaching.py` | First coaching turn instrumentation |
| `app/scaffolding/engine.py` | Methodology + IML instrumentation |
| `app/main.py` | Migration runner + error buffer integration |

---

## Monitoring Recommendations

1. **Daily funnel review**: Check `completion_rate` and `criteria_rates` daily
2. **Drop-off alerts**: Set alerts if `screen_drop_off.screen_1` exceeds 20% of `total_sessions`
3. **Duration tracking**: Monitor `average_duration_seconds` for UX optimization opportunities
4. **Criteria gaps**: If one criterion has significantly lower rate, investigate the trigger point

---

*This audit report was generated as part of InDE v3.14 "Operational Readiness".*

---

## Remediation Status (v3.15)

**Remediation Date:** March 2026
**Review Status:** Verified

### Current Onboarding Design

InDE v3.7.4 introduced a **simplified conversational approach** to onboarding that differs from the original 5-screen specification. This is an intentional design decision documented in `NewPursuitPage.jsx`:

> "Removed methodology selection wizard. Instead: User describes their innovation idea/spark, Pursuit is created immediately, User enters coaching conversation, InDE detects appropriate methodology through conversational scaffolding."

### Current Flow

| Step | Component | Description | Completion Criterion |
|------|-----------|-------------|---------------------|
| 1 | `NewPursuitPage.jsx` | Spark capture (min 10 chars) | Session starts, screen 1 reached |
| 2 | `PursuitPage.jsx` | First coaching turn | Screen 2 reached |
| 3 | Coaching conversation | Vision artifact created | `vision_artifact_created` |
| 4 | Coaching conversation | Fear identified | `fear_identified` |
| 5 | ODICM scaffolding | Methodology detected | `methodology_selected` |
| 6 | IKF integration | IML pattern surfaced | `iml_pattern_engaged` |

### Instrumentation Verification

All four completion criteria are instrumented correctly:

| Criterion | Location | Status |
|-----------|----------|--------|
| `vision_artifact_created` | `app/api/artifacts.py:82-90` | ✅ Working |
| `fear_identified` | `app/api/artifacts.py:91-94` | ✅ Working |
| `methodology_selected` | `app/scaffolding/engine.py:1170-1177` | ✅ Working |
| `iml_pattern_engaged` | `app/scaffolding/engine.py:1068-1075` | ✅ Working |

### Gap Analysis

The simplified onboarding flow intentionally omits:

| Original Spec Feature | Status | Rationale |
|-----------------------|--------|-----------|
| Role detection cards | Not implemented | Methodology detection through conversation is more natural |
| 500-char limit with specific button states | Replaced with 10-char minimum | Simpler, less restrictive UX |
| IML real-time matching in spark capture | Moved to coaching phase | IML insights surface during conversation |
| Memory Awakening screen | Not implemented | Pioneer/similarity path handled in coaching |
| Explicit methodology selection | Not implemented | Detected via ODICM scaffolding |

### Recommendations for Future Versions

1. **Role Detection (v3.16+)**: Consider adding optional role/persona selection during account setup instead of pursuit creation
2. **IML Spark Matching (v3.16+)**: Could show real-time IML hints as user types spark
3. **Methodology Hints (v3.16+)**: Surface methodology suggestions earlier in coaching based on spark content

### Conclusion

The current simplified onboarding flow is **working as designed**. All completion criteria are properly instrumented and funnel metrics are being collected. The v3.15 Guided Discovery Layer will provide ambient guidance to help first-time users understand the workspace without reverting to the more complex 5-screen wizard approach.
