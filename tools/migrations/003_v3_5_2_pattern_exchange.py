"""
Migration 003: v3.5.2 Pattern Exchange Infrastructure

Creates:
- ikf_federation_patterns collection with indexes
- ikf_pattern_rejections collection (audit trail)
- ikf_contribution_outbox collection with indexes
- Indexes for incremental sync queries

Audit Findings Addressed:
- 3.1: Pattern import mechanism (collection ready)
- 3.2: Local federation pattern cache
- 3.3: Pattern versioning/deduplication (content_hash index)
- 3.4: Incremental sync support (timestamp indexes)
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger("inde.migration.003")

MIGRATION_ID = "003_v3_5_2_pattern_exchange"
VERSION = "3.5.2"
DESCRIPTION = "Bidirectional pattern exchange infrastructure"


def up(db):
    """Apply migration - create collections and indexes."""
    results = {
        "collections_created": 0,
        "indexes_created": 0,
        "sync_state_initialized": False
    }

    # =========================================================================
    # ikf_federation_patterns - The inbound pattern cache
    # =========================================================================

    # Unique pattern ID (prevents duplicate imports)
    try:
        db.ikf_federation_patterns.create_index("pattern_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index pattern_id may already exist: {e}")

    # Content hash for deduplication (Finding 3.3)
    try:
        db.ikf_federation_patterns.create_index("content_hash")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index content_hash may already exist: {e}")

    # Status for filtering active patterns
    try:
        db.ikf_federation_patterns.create_index("status")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index status may already exist: {e}")

    # Pattern type for coaching queries
    try:
        db.ikf_federation_patterns.create_index("type")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index type may already exist: {e}")

    # Compound index for coaching context queries
    try:
        db.ikf_federation_patterns.create_index([
            ("status", 1),
            ("type", 1),
            ("confidence", -1)
        ])
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Compound coaching index may already exist: {e}")

    # Received timestamp for sync ordering and eviction
    try:
        db.ikf_federation_patterns.create_index("received_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index received_at may already exist: {e}")

    # Industry applicability for cross-pollination
    try:
        db.ikf_federation_patterns.create_index([
            ("applicability.industries", 1)
        ])
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index applicability.industries may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_federation_patterns indexes")

    # =========================================================================
    # ikf_pattern_rejections - Audit trail for rejected patterns
    # =========================================================================

    try:
        db.ikf_pattern_rejections.create_index("rejected_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index rejected_at may already exist: {e}")

    try:
        db.ikf_pattern_rejections.create_index("pattern_id")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index pattern_id may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_pattern_rejections indexes")

    # =========================================================================
    # ikf_contribution_outbox - Guaranteed delivery queue
    # =========================================================================

    try:
        db.ikf_contribution_outbox.create_index("contribution_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index contribution_id may already exist: {e}")

    # Compound index for outbox worker polling
    try:
        db.ikf_contribution_outbox.create_index([
            ("status", 1),
            ("next_attempt_after", 1)
        ])
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Compound outbox worker index may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_contribution_outbox indexes")

    # =========================================================================
    # Incremental sync state tracking
    # =========================================================================

    db.ikf_federation_state.update_one(
        {"type": "sync"},
        {"$setOnInsert": {
            "type": "sync",
            "last_sync_timestamp": None,
            "last_sync_patterns_received": 0,
            "total_patterns_received": 0,
            "total_contributions_submitted": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["sync_state_initialized"] = True
    logger.info("Initialized sync state tracking")

    # Record migration
    db.migrations.insert_one({
        "migration_id": MIGRATION_ID,
        "version": VERSION,
        "description": DESCRIPTION,
        "applied_at": datetime.now(timezone.utc),
        "results": results
    })

    logger.info(f"Migration {MIGRATION_ID} complete: {results}")
    return results


def down(db):
    """Rollback migration - drop collections."""
    db.ikf_federation_patterns.drop()
    db.ikf_pattern_rejections.drop()
    db.ikf_contribution_outbox.drop()

    db.ikf_federation_state.delete_one({"type": "sync"})
    db.migrations.delete_one({"migration_id": MIGRATION_ID})

    logger.info(f"Migration {MIGRATION_ID} rolled back")
    return {"rolled_back": True}


def is_applied(db) -> bool:
    """Check if this migration has been applied."""
    return db.migrations.find_one({"migration_id": MIGRATION_ID}) is not None


if __name__ == "__main__":
    # For standalone testing
    from pymongo import MongoClient
    import os

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/inde")
    client = MongoClient(mongo_uri)
    db = client.get_database()

    if not is_applied(db):
        print(f"Applying migration: {MIGRATION_ID}")
        result = up(db)
        print(f"Result: {result}")
    else:
        print(f"Migration {MIGRATION_ID} already applied")

    client.close()
