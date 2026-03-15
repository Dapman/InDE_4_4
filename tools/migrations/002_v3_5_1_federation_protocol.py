"""
Migration 002: v3.5.1 Federation Protocol Activation

Adds:
- Index on ikf_federation_state for connection type lookups
- Index on audit_events for federation event queries
- Federation credentials document structure
- Indexes for circuit breaker metrics

Run: python tools/migrate.py up
Rollback: python tools/migrate.py down
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger("inde.migrations")

MIGRATION_ID = "002_v3_5_1_federation_protocol"
VERSION = "3.5.1"
DESCRIPTION = "Federation connection lifecycle + auth infrastructure"


def up(db):
    """
    Apply the v3.5.1 migration.

    Creates indexes for federation state lookups and audit event queries.
    Initializes the federation connection state document.
    """
    results = {
        "indexes_created": 0,
        "documents_initialized": 0,
        "errors": []
    }

    # 1. Index for connection state lookups
    try:
        db.ikf_federation_state.create_index("type", unique=True, name="type_unique")
        results["indexes_created"] += 1
        logger.info("Created index: ikf_federation_state.type")
    except Exception as e:
        if "already exists" not in str(e):
            results["errors"].append(f"ikf_federation_state.type: {e}")
        else:
            logger.info("Index ikf_federation_state.type already exists")

    # 2. Index for federation audit event queries by source
    try:
        db.audit_events.create_index(
            [("source", 1), ("recorded_at", -1)],
            name="source_recorded_at"
        )
        results["indexes_created"] += 1
        logger.info("Created index: audit_events.source_recorded_at")
    except Exception as e:
        if "already exists" not in str(e):
            results["errors"].append(f"audit_events.source_recorded_at: {e}")
        else:
            logger.info("Index audit_events.source_recorded_at already exists")

    # 3. Index for federation audit event queries by event_type
    try:
        db.audit_events.create_index(
            [("event_type", 1), ("recorded_at", -1)],
            name="event_type_recorded_at"
        )
        results["indexes_created"] += 1
        logger.info("Created index: audit_events.event_type_recorded_at")
    except Exception as e:
        if "already exists" not in str(e):
            results["errors"].append(f"audit_events.event_type_recorded_at: {e}")
        else:
            logger.info("Index audit_events.event_type_recorded_at already exists")

    # 4. Index for federation state queries by connection_state
    try:
        db.ikf_federation_state.create_index(
            "connection_state",
            name="connection_state",
            sparse=True
        )
        results["indexes_created"] += 1
        logger.info("Created index: ikf_federation_state.connection_state")
    except Exception as e:
        if "already exists" not in str(e):
            results["errors"].append(f"ikf_federation_state.connection_state: {e}")
        else:
            logger.info("Index ikf_federation_state.connection_state already exists")

    # 5. Ensure federation connection document exists
    try:
        update_result = db.ikf_federation_state.update_one(
            {"type": "connection"},
            {"$setOnInsert": {
                "type": "connection",
                "connection_state": "UNREGISTERED",
                "federation_jwt": None,
                "verification_level": None,
                "assigned_region": None,
                "reconnect_attempt": 0,
                "last_state_change": datetime.now(timezone.utc),
                "version": "3.5.1"
            }},
            upsert=True
        )
        if update_result.upserted_id:
            results["documents_initialized"] += 1
            logger.info("Initialized federation connection document")
        else:
            logger.info("Federation connection document already exists")
    except Exception as e:
        results["errors"].append(f"connection document: {e}")

    # 6. Update schema version
    try:
        db.ikf_schema_version.update_one(
            {"_id": "schema_version"},
            {"$set": {
                "version": "3.5.1",
                "migration": MIGRATION_ID,
                "applied_at": datetime.now(timezone.utc),
                "description": DESCRIPTION
            }},
            upsert=True
        )
        logger.info("Updated schema version to 3.5.1")
    except Exception as e:
        results["errors"].append(f"schema_version: {e}")

    return results


def down(db):
    """
    Rollback the v3.5.1 migration.

    Removes indexes created by this migration.
    Note: Does NOT remove the connection document to preserve state.
    """
    results = {
        "indexes_dropped": 0,
        "errors": []
    }

    # Drop indexes created by this migration
    indexes_to_drop = [
        ("ikf_federation_state", "type_unique"),
        ("ikf_federation_state", "connection_state"),
        ("audit_events", "source_recorded_at"),
        ("audit_events", "event_type_recorded_at"),
    ]

    for collection_name, index_name in indexes_to_drop:
        try:
            collection = db[collection_name]
            collection.drop_index(index_name)
            results["indexes_dropped"] += 1
            logger.info(f"Dropped index: {collection_name}.{index_name}")
        except Exception as e:
            if "not found" not in str(e).lower():
                results["errors"].append(f"{collection_name}.{index_name}: {e}")
            else:
                logger.info(f"Index {collection_name}.{index_name} not found")

    # Revert schema version
    try:
        db.ikf_schema_version.update_one(
            {"_id": "schema_version"},
            {"$set": {
                "version": "3.5.0",
                "migration": "001_v3_5_0_initial",
                "applied_at": datetime.now(timezone.utc),
                "description": "Rolled back from 3.5.1"
            }}
        )
        logger.info("Reverted schema version to 3.5.0")
    except Exception as e:
        results["errors"].append(f"schema_version rollback: {e}")

    results["rolled_back"] = True
    return results


def status(db):
    """
    Check status of this migration.

    Returns information about what has been applied.
    """
    status = {
        "migration_id": MIGRATION_ID,
        "version": VERSION,
        "indexes": {},
        "documents": {}
    }

    # Check indexes
    try:
        fed_state_indexes = list(db.ikf_federation_state.list_indexes())
        status["indexes"]["ikf_federation_state"] = [
            idx["name"] for idx in fed_state_indexes
        ]
    except Exception:
        status["indexes"]["ikf_federation_state"] = "error"

    try:
        audit_indexes = list(db.audit_events.list_indexes())
        status["indexes"]["audit_events"] = [
            idx["name"] for idx in audit_indexes
        ]
    except Exception:
        status["indexes"]["audit_events"] = "error"

    # Check connection document
    try:
        conn_doc = db.ikf_federation_state.find_one({"type": "connection"})
        status["documents"]["connection"] = {
            "exists": bool(conn_doc),
            "state": conn_doc.get("connection_state") if conn_doc else None,
            "version": conn_doc.get("version") if conn_doc else None
        }
    except Exception:
        status["documents"]["connection"] = "error"

    # Check schema version
    try:
        schema_doc = db.ikf_schema_version.find_one({"_id": "schema_version"})
        status["schema_version"] = schema_doc.get("version") if schema_doc else None
    except Exception:
        status["schema_version"] = "error"

    return status
