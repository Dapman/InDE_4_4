"""
Migration 005: v3.6.0 Biomimicry Pattern Database

Creates:
1. biomimicry_patterns collection with compound indexes
2. biomimicry_matches collection for analytics
3. Seeds 40+ curated biological strategies across 8 categories

v3.6.0 Features:
- LLM-assisted function extraction for biological parallel detection
- Conversational coaching integration (not wizard-like)
- Methodology-adaptive guidance (Lean Startup / Design Thinking / Stage-Gate)
- Innovator response tracking with effectiveness feedback loop
- IKF federation of biomimicry application patterns (bidirectional)
- TRIZ inventive principle cross-references pre-populated for v3.6.1
"""

from datetime import datetime, timezone
import logging
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger("inde.migration.005")

MIGRATION_ID = "005_v3_6_0_biomimicry"
VERSION = "3.6.0"
DESCRIPTION = "Biomimicry pattern database with 40+ curated biological strategies"


def up(db):
    """Apply migration - create collections, indexes, and seed data."""
    results = {
        "collections_created": 0,
        "indexes_created": 0,
        "patterns_seeded": 0,
        "state_initialized": []
    }

    # =========================================================================
    # biomimicry_patterns collection
    # =========================================================================

    # Category index for filtering by biological category
    try:
        db.biomimicry_patterns.create_index("category")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index category may already exist: {e}")

    # Functions index for matching extracted functions
    try:
        db.biomimicry_patterns.create_index("functions")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index functions may already exist: {e}")

    # Applicable domains index for domain-based filtering
    try:
        db.biomimicry_patterns.create_index("applicable_domains")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index applicable_domains may already exist: {e}")

    # Source index for filtering by origin (curated/federation/org)
    try:
        db.biomimicry_patterns.create_index("source")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index source may already exist: {e}")

    # Compound index for function + domain queries
    try:
        db.biomimicry_patterns.create_index(
            [("functions", 1), ("applicable_domains", 1)],
            name="function_domain_compound"
        )
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Compound index may already exist: {e}")

    # Effectiveness sorting index
    try:
        db.biomimicry_patterns.create_index(
            [("acceptance_rate", -1), ("match_count", -1)],
            name="effectiveness_sort"
        )
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Effectiveness sort index may already exist: {e}")

    # Pattern ID unique index
    try:
        db.biomimicry_patterns.create_index("pattern_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Pattern ID index may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created biomimicry_patterns indexes")

    # =========================================================================
    # biomimicry_matches collection
    # =========================================================================

    # Pursuit index for finding all matches for a pursuit
    try:
        db.biomimicry_matches.create_index("pursuit_id")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index pursuit_id may already exist: {e}")

    # Pattern index for analytics on pattern effectiveness
    try:
        db.biomimicry_matches.create_index("pattern_id")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index pattern_id may already exist: {e}")

    # Response index for filtering by innovator response
    try:
        db.biomimicry_matches.create_index("innovator_response")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index innovator_response may already exist: {e}")

    # Timestamp index for chronological queries
    try:
        db.biomimicry_matches.create_index("created_at")
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Index created_at may already exist: {e}")

    # Match ID unique index
    try:
        db.biomimicry_matches.create_index("match_id", unique=True)
        results["indexes_created"] += 1
    except Exception as e:
        logger.warning(f"Match ID index may already exist: {e}")

    results["collections_created"] += 1
    logger.info("Created biomimicry_matches indexes")

    # =========================================================================
    # Seed patterns
    # =========================================================================

    try:
        from ikf_service.data.biomimicry_seed_patterns import SEED_PATTERNS
    except ImportError:
        try:
            from data.biomimicry_seed_patterns import SEED_PATTERNS
        except ImportError:
            # Direct import for standalone execution
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "biomimicry_seed_patterns",
                os.path.join(os.path.dirname(__file__), "..", "..", "ikf-service", "data", "biomimicry_seed_patterns.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            SEED_PATTERNS = module.SEED_PATTERNS

    existing_count = db.biomimicry_patterns.count_documents({})
    if existing_count == 0:
        # Add timestamps to seed patterns
        now = datetime.now(timezone.utc)
        for pattern in SEED_PATTERNS:
            pattern["created_at"] = now
            pattern["updated_at"] = now
            pattern["match_count"] = 0
            pattern["acceptance_rate"] = 0.0
            pattern["feedback_scores"] = []

        db.biomimicry_patterns.insert_many(SEED_PATTERNS)
        results["patterns_seeded"] = len(SEED_PATTERNS)
        logger.info(f"Seeded {len(SEED_PATTERNS)} biomimicry patterns")
    else:
        logger.info(f"Skipping seed - {existing_count} patterns already exist")

    # =========================================================================
    # Initialize biomimicry state
    # =========================================================================

    db.ikf_federation_state.update_one(
        {"type": "biomimicry"},
        {"$setOnInsert": {
            "type": "biomimicry",
            "last_analysis_timestamp": None,
            "total_matches": 0,
            "total_acceptances": 0,
            "federation_contributions": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    results["state_initialized"].append("biomimicry")
    logger.info("Initialized biomimicry state")

    # =========================================================================
    # Record migration
    # =========================================================================

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
    db.biomimicry_patterns.drop()
    db.biomimicry_matches.drop()

    db.ikf_federation_state.delete_one({"type": "biomimicry"})
    db.migrations.delete_one({"migration_id": MIGRATION_ID})

    logger.info(f"Migration {MIGRATION_ID} rolled back")
    return {"rolled_back": True}


def is_applied(db) -> bool:
    """Check if this migration has been applied."""
    return db.migrations.find_one({"migration_id": MIGRATION_ID}) is not None


def verify(db) -> dict:
    """Verify migration integrity."""
    from models.biomimicry import BiomimicryCategory

    results = {"valid": True, "issues": []}

    # Check total count
    total = db.biomimicry_patterns.count_documents({})
    if total < 40:
        results["valid"] = False
        results["issues"].append(f"Only {total} patterns (need >= 40)")

    # Check each category has >= 5
    for category in BiomimicryCategory:
        count = db.biomimicry_patterns.count_documents({"category": category.value})
        if count < 5:
            results["valid"] = False
            results["issues"].append(f"Category {category.value} has {count} patterns (need >= 5)")

    # Check TRIZ coverage
    with_triz = db.biomimicry_patterns.count_documents({"triz_connections": {"$ne": []}})
    coverage = with_triz / total if total > 0 else 0
    if coverage < 0.55:
        results["issues"].append(f"TRIZ coverage {coverage:.0%} (recommended >= 55%)")

    # Check indexes
    indexes = db.biomimicry_patterns.index_information()
    required_indexes = ["function_domain_compound", "effectiveness_sort"]
    for idx in required_indexes:
        if idx not in indexes:
            results["valid"] = False
            results["issues"].append(f"Missing index: {idx}")

    results["total_patterns"] = total
    results["triz_coverage"] = f"{coverage:.0%}"

    return results


if __name__ == "__main__":
    # For standalone testing
    from pymongo import MongoClient

    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/inde")
    client = MongoClient(mongo_uri)
    db = client.get_database()

    if not is_applied(db):
        print(f"Applying migration: {MIGRATION_ID}")
        result = up(db)
        print(f"Result: {result}")

        # Verify
        verification = verify(db)
        print(f"Verification: {verification}")
    else:
        print(f"Migration {MIGRATION_ID} already applied")

        # Show verification
        verification = verify(db)
        print(f"Verification: {verification}")

    client.close()
