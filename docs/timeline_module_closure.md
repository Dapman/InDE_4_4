# Timeline Module — Closure Decision Record

**Date:** March 2026
**Decision Maker:** InDE Project (Yul Williams)
**Status:** FINAL

## Summary

The timeline enhancement workstream is closed as of v3.11.0. The timeline module is complete at its current capability level.

## What Was Built

| Version | Capability |
|---------|-----------|
| v3.9 | Conversational timeline extraction — milestones inferred from coaching conversation |
| v3.10 | Data integrity — conflict resolution, allocation sync, relative date handling |
| v3.11 | Housekeeping — query performance indexes, team permission enforcement |

## The Governing Principle

**InDE's mission:** Frictionless, methodology-invisible innovation coaching.

**The line:** InDE captures timeline information because it reveals innovator intent and commitment. InDE does not manage timelines.

Timeline extraction exists to make coaching smarter — not to turn InDE into a project management tool. Every feature request that crosses from "coaching insight" to "project scheduling" is out of scope.

## What Was Retired and Why

The following TD items from the InDE Timeline Extraction Technical Debt Specification (v1.0, March 3, 2026) were considered and formally retired. They are not deferred to a future version — they are out of scope for InDE's mission.

### TD-003: Missing Milestone Detection & Suggestion

**Description:** Detect when an innovator's milestone coverage is incomplete relative to their phase goals and suggest additional milestones.

**Why Retired:** This is project scheduling, not coaching. InDE does not manage innovators' work breakdown structures. Suggesting milestones creates the expectation that InDE is a timeline management tool. Innovators should set their own milestones naturally through conversation.

### TD-004: Timeline Compression Risk Detection

**Description:** Detect when milestones are clustered too closely or when the timeline is compressed relative to scope.

**Why Retired:** Risk scoring based on milestone density is project management. This feature would require InDE to make judgments about what constitutes "too much work" — a subjective call that varies by innovator, domain, and context. This belongs in a PM tool, not a coaching session.

### TD-007: Milestone Dependency Tracking

**Description:** Allow milestones to declare dependencies on other milestones and visualize the critical path.

**Why Retired:** Critical path analysis is explicitly out of InDE's coaching scope. Dependency tracking turns milestones into a formal task graph, which is project management. InDE captures milestones as signals, not as nodes in a scheduling network.

### TD-008: Timeline Branching / Scenario Planning

**Description:** Allow innovators to create "what if" timeline scenarios and compare outcomes.

**Why Retired:** Scenario planning at the milestone level is project management. InDE's role is to coach innovators through their actual timeline, not to model hypothetical alternatives. Scenario analysis belongs in specialized planning tools.

### TD-009: External Calendar Integration

**Description:** Sync milestones with Google Calendar, Outlook, or other external calendar systems.

**Why Retired:** Stakeholder calendar management is outside InDE's domain. Calendar sync creates expectations of reminders, notifications, and schedule coordination — all of which are project management functions. InDE is not a calendar app.

### TD-010: Conditional Milestone Completion Evidence

**Description:** Require evidence (files, links, or attestations) before a milestone can be marked complete.

**Why Retired:** Evidence management belongs in portfolio/compliance tools, not coaching. This feature would introduce friction into the coaching flow and create audit-trail expectations that conflict with InDE's lightweight approach.

### TD-011: Timeline-Aware Scaffolding Modulation

**Description:** Adjust coaching tone and urgency based on proximity to milestone dates.

**Why Retired:** Deadline-urgency-based coaching tone shifts reduce coaching quality. InDE's scaffolding responds to innovation state (where the innovator is in their methodology), not calendar pressure. Adding "you have 3 days left!" urgency undermines the psychological safety of the coaching relationship.

### TD-012: Release Milestone → RVE Integration

**Description:** Automatically trigger Reality Validation Exercises when release milestones approach.

**Why Retired:** RVE is already triggered by conversation context. Calendar-triggered RVE is redundant and mechanical. The coaching engine should invite RVE when the innovator's conversation signals readiness, not when a date approaches.

### TD-013: Timeline Estimation Accuracy Tracking

**Description:** Track how accurately innovators estimate their milestone dates over time and surface patterns.

**Why Retired:** Historical accuracy tracking is a performance management feature, not a coaching feature. Showing innovators "you're usually 20% late" creates judgment and defensiveness rather than coaching safety.

### TD-016: Natural Language Milestone Update Interface

**Description:** Parse conversational statements like "push the launch back a week" as milestone updates.

**Why Retired:** Ambiguity risk in coaching context. The conversation is already the interface — innovators naturally mention dates when they want to. Adding explicit "update detection" creates ambiguity about what constitutes an update vs. a hypothetical statement. The v3.10 conflict detection system handles genuine date changes; we don't need to parse every casual mention as an edit command.

## What Was Deferred (Not Retired)

### TD-006: Milestone Classification Accuracy Tracking

**Status:** Parked (not retired)

**Description:** Track LLM accuracy in classifying milestone types and use correction signals for fine-tuning.

**Rationale:** This is a system improvement that could be revisited when there is a sufficient corpus of user corrections to learn from. It is not fundamentally in conflict with InDE's coaching mission — it's just not worth building until there's data to act on.

## What Comes Next

With the timeline workstream closed, InDE development returns focus to the core coaching and innovator experience. See the active roadmap for next priorities.

---

*InDE MVP v3.11.0 "Timeline Housekeeping & Closure"*
*Closure Record Version: 1.0 — March 2026*
*© 2024–2026 Yul Williams | InDEVerse, Incorporated*
