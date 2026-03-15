"""
InDE v3.2 - Event Schema Migration
Migrates existing data to support Redis Streams event architecture.

Run with: python -m migrations.v32_event_schema
"""

import os
import sys
from datetime import datetime

# Add app directory to path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inde.migration.v32")


def _safe_create_index(collection, keys, **kwargs):
    """Create index, ignoring if equivalent index already exists."""
    try:
        return collection.create_index(keys, **kwargs)
    except OperationFailure as e:
        if e.code == 85:  # IndexOptionsConflict
            logger.info(f"Index already exists (equivalent): {kwargs.get('name', keys)}")
            return None
        raise


def run_migration():
    """Run v3.2 event schema migration."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB", "inde")

    logger.info(f"Connecting to MongoDB: {mongo_uri}")
    client = MongoClient(mongo_uri)
    db = client[db_name]

    try:
        # 1. Add correlation_id to existing domain_events
        _migrate_domain_events(db)

        # 2. Create event_dead_letters collection and indexes
        _create_dead_letter_indexes(db)

        # 3. Create temporal_events collection and indexes
        _create_temporal_events_indexes(db)

        # 4. Create event audit indexes
        _create_event_audit_indexes(db)

        logger.info("v3.2 Event schema migration completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()


def _migrate_domain_events(db):
    """Add correlation_id and source_module to existing domain_events."""
    logger.info("Migrating domain_events collection...")

    # Count events without correlation_id
    count = db.domain_events.count_documents({"correlation_id": {"$exists": False}})
    logger.info(f"Found {count} events without correlation_id")

    if count > 0:
        # Add correlation_id to existing events (use event_id as fallback)
        result = db.domain_events.update_many(
            {"correlation_id": {"$exists": False}},
            [
                {
                    "$set": {
                        "correlation_id": {"$toString": "$event_id"},
                        "source_module": "legacy"
                    }
                }
            ]
        )
        logger.info(f"Updated {result.modified_count} domain_events with correlation_id")

    # Create correlation_id index
    _safe_create_index(
        db.domain_events,
        [("correlation_id", ASCENDING)],
        name="idx_correlation_id"
    )
    logger.info("Created correlation_id index on domain_events")


def _create_dead_letter_indexes(db):
    """Create indexes for event_dead_letters collection."""
    logger.info("Creating event_dead_letters indexes...")

    # Primary lookup by event_id
    _safe_create_index(
        db.event_dead_letters,
        [("event_id", ASCENDING)],
        name="idx_event_id",
        unique=True
    )

    # Query by consumer group
    _safe_create_index(
        db.event_dead_letters,
        [("consumer_group", ASCENDING), ("failed_at", DESCENDING)],
        name="idx_consumer_group_failed_at"
    )

    # Query by stream
    _safe_create_index(
        db.event_dead_letters,
        [("stream", ASCENDING), ("failed_at", DESCENDING)],
        name="idx_stream_failed_at"
    )

    # TTL index for automatic cleanup (90 days)
    _safe_create_index(
        db.event_dead_letters,
        [("failed_at", ASCENDING)],
        name="idx_failed_at_ttl",
        expireAfterSeconds=90 * 24 * 60 * 60  # 90 days
    )

    logger.info("Created event_dead_letters indexes")


def _create_temporal_events_indexes(db):
    """Create indexes for temporal_events collection."""
    logger.info("Creating temporal_events indexes...")

    # Primary lookup by event_id
    _safe_create_index(
        db.temporal_events,
        [("event_id", ASCENDING)],
        name="idx_event_id",
        unique=True
    )

    # Timeline queries by pursuit
    _safe_create_index(
        db.temporal_events,
        [("pursuit_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_pursuit_timeline"
    )

    # Timeline queries by user
    _safe_create_index(
        db.temporal_events,
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_user_timeline"
    )

    # Query by event type
    _safe_create_index(
        db.temporal_events,
        [("event_type", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_event_type_timeline"
    )

    # TTL index for automatic cleanup (1 year)
    _safe_create_index(
        db.temporal_events,
        [("logged_at", ASCENDING)],
        name="idx_logged_at_ttl",
        expireAfterSeconds=365 * 24 * 60 * 60  # 1 year
    )

    logger.info("Created temporal_events indexes")


def _create_event_audit_indexes(db):
    """Create additional audit indexes for domain_events."""
    logger.info("Creating event audit indexes...")

    # Replay support: find events since timestamp
    _safe_create_index(
        db.domain_events,
        [("timestamp", ASCENDING)],
        name="idx_timestamp_asc"
    )

    # Replay by pursuit
    _safe_create_index(
        db.domain_events,
        [("pursuit_id", ASCENDING), ("timestamp", ASCENDING)],
        name="idx_pursuit_timestamp_asc"
    )

    # Source module queries
    _safe_create_index(
        db.domain_events,
        [("source_module", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_source_module_timeline"
    )

    logger.info("Created event audit indexes")


def verify_migration(db_name: str = "inde"):
    """Verify migration completed successfully."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client[db_name]

    try:
        # Check domain_events correlation_id
        without_corr = db.domain_events.count_documents({"correlation_id": {"$exists": False}})
        if without_corr > 0:
            logger.warning(f"{without_corr} domain_events still missing correlation_id")
            return False

        # Check dead letter indexes
        dl_indexes = list(db.event_dead_letters.list_indexes())
        if len(dl_indexes) < 4:
            logger.warning("event_dead_letters missing indexes")
            return False

        # Check temporal events indexes
        te_indexes = list(db.temporal_events.list_indexes())
        if len(te_indexes) < 4:
            logger.warning("temporal_events missing indexes")
            return False

        logger.info("Migration verification passed")
        return True

    finally:
        client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="InDE v3.2 Event Schema Migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration only")
    parser.add_argument("--db", default="inde", help="Database name")
    args = parser.parse_args()

    if args.verify:
        success = verify_migration(args.db)
        sys.exit(0 if success else 1)
    else:
        run_migration()
