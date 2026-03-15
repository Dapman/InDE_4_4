"""
Migration 004: v3.5.3 Global Benchmarking & Cross-Org Intelligence

Creates:
- ikf_benchmarks collection (cached benchmark data from IKF)
- ikf_trust_relationships collection (bilateral trust network)
- ikf_reputation collection (org/innovator reputation cache)
- ikf_introduction_requests collection (mediated introduction tracking)
- Indexes for all new collections

v3.5.3 Features:
- Global Benchmarking Engine for anonymized comparative analytics
- Trust Network & Reputation management
- Cross-Organization IDTFS for federated talent discovery
- WebSocket real-time event delivery

Audit Findings Addressed:
- 1.2: Benchmark integration for coaching context
- 4.2: Trust relationship prerequisites for cross-org features
- 4.3: Reputation-based eligibility checks
- 5.4: Cross-org IDTFS with privacy enforcement
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger("inde.migration.004")

MIGRATION_ID = "004_v3_5_3_global_benchmarking"
VERSION = "3.5.3"
DESCRIPTION = "Global benchmarking, trust network, reputation, cross-org IDTFS"


def up(db):
    """Apply migration - create collections and indexes."""
    results = {
        "collections_created": 0,
        "indexes_created": 0,
        "state_initialized": []
    }

    # =========================================================================
    # ikf_benchmarks - Cached benchmark data from IKF
    # =========================================================================

    # Unique benchmark key (scope + timeframe + metric)
    try:
        db.ikf_benchmarks.create_index(
            [("scope", 1), ("timeframe", 1), ("metric_type", 1)],
            unique=True
        )
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Benchmark unique index may already exist: {e}")

    # For querying by scope (industry, methodology, size)
    try:
        db.ikf_benchmarks.create_index("scope")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index scope may already exist: {e}")

    # For cache freshness checks
    try:
        db.ikf_benchmarks.create_index("fetched_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index fetched_at may already exist: {e}")

    # For stale data cleanup
    try:
        db.ikf_benchmarks.create_index("stale", expireAfterSeconds=86400)  # TTL 24h
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"TTL index stale may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_benchmarks indexes")

    # =========================================================================
    # ikf_trust_relationships - Bilateral trust network cache
    # =========================================================================

    # Unique relationship ID
    try:
        db.ikf_trust_relationships.create_index("relationship_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index relationship_id may already exist: {e}")

    # For querying by partner org
    try:
        db.ikf_trust_relationships.create_index("partner_org_id")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index partner_org_id may already exist: {e}")

    # For filtering by status (ACTIVE, PROPOSED, REVOKED, EXPIRED)
    try:
        db.ikf_trust_relationships.create_index("status")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index status may already exist: {e}")

    # Compound index for active trust queries
    try:
        db.ikf_trust_relationships.create_index([
            ("partner_org_id", 1),
            ("status", 1)
        ])
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Compound trust index may already exist: {e}")

    # For expiration checks
    try:
        db.ikf_trust_relationships.create_index("expires_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index expires_at may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_trust_relationships indexes")

    # =========================================================================
    # ikf_reputation - Org/innovator reputation cache
    # =========================================================================

    # Unique entity (type + id)
    try:
        db.ikf_reputation.create_index(
            [("entity_type", 1), ("entity_id", 1)],
            unique=True
        )
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Reputation unique index may already exist: {e}")

    # For cache freshness
    try:
        db.ikf_reputation.create_index("updated_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index updated_at may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_reputation indexes")

    # =========================================================================
    # ikf_introduction_requests - Mediated introduction tracking
    # =========================================================================

    # Unique introduction ID
    try:
        db.ikf_introduction_requests.create_index("introduction_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index introduction_id may already exist: {e}")

    # For querying by target GII
    try:
        db.ikf_introduction_requests.create_index("target_gii")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index target_gii may already exist: {e}")

    # For filtering by status
    try:
        db.ikf_introduction_requests.create_index("status")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index status may already exist: {e}")

    # For user's introduction history
    try:
        db.ikf_introduction_requests.create_index([
            ("requested_by", 1),
            ("requested_at", -1)
        ])
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Compound introduction history index may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created ikf_introduction_requests indexes")

    # =========================================================================
    # Initialize benchmark sync state
    # =========================================================================

    db.ikf_federation_state.update_one(
        {"type": "benchmark_sync"},
        {"$setOnInsert": {
            "type": "benchmark_sync",
            "last_sync_timestamp": None,
            "industry_benchmarks_cached": 0,
            "methodology_benchmarks_cached": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["state_initialized"].append("benchmark_sync")
    logger.info("Initialized benchmark sync state")

    # =========================================================================
    # Initialize trust network state
    # =========================================================================

    db.ikf_federation_state.update_one(
        {"type": "trust_network"},
        {"$setOnInsert": {
            "type": "trust_network",
            "last_sync_timestamp": None,
            "active_trust_count": 0,
            "pending_request_count": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["state_initialized"].append("trust_network")
    logger.info("Initialized trust network state")

    # =========================================================================
    # Initialize reputation state
    # =========================================================================

    db.ikf_federation_state.update_one(
        {"type": "reputation"},
        {"$setOnInsert": {
            "type": "reputation",
            "last_sync_timestamp": None,
            "org_reputation_score": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["state_initialized"].append("reputation")
    logger.info("Initialized reputation state")

    # =========================================================================
    # Organization settings for cross-org discovery
    # =========================================================================

    db.organization_settings.update_one(
        {},
        {"$setOnInsert": {
            "cross_org_discovery_enabled": True,
            "cross_org_sharing_level": "INDUSTRY",
            "benchmark_opt_in": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["state_initialized"].append("organization_settings")
    logger.info("Initialized organization settings")

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
    """Rollback migration - drop collections and state."""
    db.ikf_benchmarks.drop()
    db.ikf_trust_relationships.drop()
    db.ikf_reputation.drop()
    db.ikf_introduction_requests.drop()

    db.ikf_federation_state.delete_one({"type": "benchmark_sync"})
    db.ikf_federation_state.delete_one({"type": "trust_network"})
    db.ikf_federation_state.delete_one({"type": "reputation"})
    db.organization_settings.delete_one({})

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
