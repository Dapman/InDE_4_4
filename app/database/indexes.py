"""
InDE MongoDB Index Definitions
Centralized index management — called at application startup.
All operations are idempotent: safe to call on every startup.

v3.11: TD-015 — Milestone Query Performance Indexes
v3.12: Account Trust — Password reset tokens and user deletion indexes
v3.13: Experience Polish — Pursuit archive index, conversation text search
"""

import logging

logger = logging.getLogger(__name__)


async def create_all_indexes(db) -> None:
    """
    Create all MongoDB indexes for the InDE application.
    Uses background=True to avoid blocking startup on large collections.
    Safe to call multiple times — MongoDB ignores already-existing identical indexes.

    Args:
        db: Database instance (expects db.db for raw pymongo/motor access)
    """

    logger.info("Creating/verifying MongoDB indexes...")

    # Get the raw database connection
    raw_db = db.db if hasattr(db, 'db') else db

    # ── pursuit_milestones collection ──────────────────────────────────────
    # Note: Collection is named 'pursuit_milestones' in InDE, not just 'milestones'

    # Primary query pattern: all milestones for a pursuit ordered by date
    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_date"
    )

    # Filter by status within a pursuit (e.g., "show pending milestones")
    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("status", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_status_date"
    )

    # Filter by type within a pursuit (e.g., "find release milestones")
    # Used heavily by TemporalConflictResolver and TimelineConsistencyValidator
    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("milestone_type", 1)],
        background=True,
        name="milestones_pursuit_type"
    )

    # Filter active (non-superseded) milestones — critical for v3.10 versioning
    # Without this index, conflict resolution queries scan the full collection
    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("is_superseded", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_superseded_date"
    )

    # ── temporal_events collection ─────────────────────────────────────────

    # Query events for a pursuit in chronological order
    raw_db.temporal_events.create_index(
        [("pursuit_id", 1), ("created_at", -1)],
        background=True,
        name="temporal_events_pursuit_created"
    )

    # Query by event type (e.g., find all CONFLICT_RESOLVED events for a pursuit)
    raw_db.temporal_events.create_index(
        [("pursuit_id", 1), ("event_type", 1), ("created_at", -1)],
        background=True,
        name="temporal_events_pursuit_type_created"
    )

    # ── time_allocations collection ────────────────────────────────────────

    # Primary lookup: one allocation per pursuit
    raw_db.time_allocations.create_index(
        [("pursuit_id", 1)],
        unique=True,
        background=True,
        name="time_allocations_pursuit_unique"
    )

    # ── v3.12: password_reset_tokens collection ────────────────────────────

    # Lookup by token hash (primary query pattern)
    raw_db.password_reset_tokens.create_index(
        [("token_hash", 1)],
        background=True,
        name="prt_token_hash"
    )

    # TTL index — auto-deletes expired tokens (expires_at must be a Date type)
    # Note: MongoDB TTL requires the field to be a Date/datetime, not ISO string
    raw_db.password_reset_tokens.create_index(
        [("expires_at", 1)],
        background=True,
        expireAfterSeconds=0,
        name="prt_expires_ttl"
    )

    # User's tokens lookup
    raw_db.password_reset_tokens.create_index(
        [("user_id", 1), ("used", 1)],
        background=True,
        name="prt_user_used"
    )

    # ── v3.12: users collection additions ──────────────────────────────────

    # Query deactivated accounts for deletion job
    raw_db.users.create_index(
        [("status", 1), ("deletion_scheduled_for", 1)],
        background=True,
        name="users_status_deletion_scheduled"
    )

    # ── v3.13: pursuits collection — archive index ─────────────────────────

    # Efficient filtered queries: active vs archived pursuits for a user
    raw_db.pursuits.create_index(
        [("user_id", 1), ("is_archived", 1), ("updated_at", -1)],
        background=True,
        name="pursuits_user_archived_updated"
    )

    # ── v3.13: conversation_history collection — full-text search ──────────

    # Check if text index already exists before creating
    # MongoDB allows only ONE text index per collection
    existing_indexes = raw_db.conversation_history.index_information()
    has_text_index = any(
        "text" in str(idx.get("key", {}))
        for idx in existing_indexes.values()
    )

    if not has_text_index:
        raw_db.conversation_history.create_index(
            [("content", "text")],
            background=True,
            name="conversation_history_content_text",
            default_language="english"
        )

    # Compound index for scoped search (pursuit + time ordering)
    raw_db.conversation_history.create_index(
        [("pursuit_id", 1), ("timestamp", -1)],
        background=True,
        name="conversation_history_pursuit_timestamp"
    )

    logger.info("MongoDB indexes verified successfully.")


def create_all_indexes_sync(db) -> None:
    """
    Synchronous version of create_all_indexes for non-async contexts.

    Args:
        db: Database instance (expects db.db for raw pymongo access)
    """

    logger.info("Creating/verifying MongoDB indexes (sync)...")

    # Get the raw database connection
    raw_db = db.db if hasattr(db, 'db') else db

    # ── pursuit_milestones collection ──────────────────────────────────────

    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_date"
    )

    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("status", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_status_date"
    )

    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("milestone_type", 1)],
        background=True,
        name="milestones_pursuit_type"
    )

    raw_db.pursuit_milestones.create_index(
        [("pursuit_id", 1), ("is_superseded", 1), ("target_date", 1)],
        background=True,
        name="milestones_pursuit_superseded_date"
    )

    # ── temporal_events collection ─────────────────────────────────────────

    raw_db.temporal_events.create_index(
        [("pursuit_id", 1), ("created_at", -1)],
        background=True,
        name="temporal_events_pursuit_created"
    )

    raw_db.temporal_events.create_index(
        [("pursuit_id", 1), ("event_type", 1), ("created_at", -1)],
        background=True,
        name="temporal_events_pursuit_type_created"
    )

    # ── time_allocations collection ────────────────────────────────────────

    raw_db.time_allocations.create_index(
        [("pursuit_id", 1)],
        unique=True,
        background=True,
        name="time_allocations_pursuit_unique"
    )

    # ── v3.12: password_reset_tokens collection ────────────────────────────

    raw_db.password_reset_tokens.create_index(
        [("token_hash", 1)],
        background=True,
        name="prt_token_hash"
    )

    raw_db.password_reset_tokens.create_index(
        [("expires_at", 1)],
        background=True,
        expireAfterSeconds=0,
        name="prt_expires_ttl"
    )

    raw_db.password_reset_tokens.create_index(
        [("user_id", 1), ("used", 1)],
        background=True,
        name="prt_user_used"
    )

    # ── v3.12: users collection additions ──────────────────────────────────

    raw_db.users.create_index(
        [("status", 1), ("deletion_scheduled_for", 1)],
        background=True,
        name="users_status_deletion_scheduled"
    )

    # ── v3.13: pursuits collection — archive index ─────────────────────────

    raw_db.pursuits.create_index(
        [("user_id", 1), ("is_archived", 1), ("updated_at", -1)],
        background=True,
        name="pursuits_user_archived_updated"
    )

    # ── v3.13: conversation_history collection — full-text search ──────────

    existing_indexes = raw_db.conversation_history.index_information()
    has_text_index = any(
        "text" in str(idx.get("key", {}))
        for idx in existing_indexes.values()
    )

    if not has_text_index:
        raw_db.conversation_history.create_index(
            [("content", "text")],
            background=True,
            name="conversation_history_content_text",
            default_language="english"
        )

    raw_db.conversation_history.create_index(
        [("pursuit_id", 1), ("timestamp", -1)],
        background=True,
        name="conversation_history_pursuit_timestamp"
    )

    logger.info("MongoDB indexes verified successfully (sync).")
