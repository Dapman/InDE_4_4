"""
v3.6.1 Migration: Methodology Expansion & Scenario Intelligence

Creates:
1. triz_inventive_principles collection (40 principles reference)
2. scenario_artifacts collection
3. Indexes for methodology effectiveness queries
4. Extends pursuit schema with triz_state, blue_ocean_state, scenario_state

This migration also seeds the 40 TRIZ inventive principles if not present.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger("inde.migrations.v3_6_1")


MIGRATION_VERSION = "3.6.1"
MIGRATION_NAME = "methodology_scenario"


async def migrate(db) -> Dict[str, Any]:
    """
    Run the v3.6.1 migration.

    Args:
        db: MongoDB database instance

    Returns:
        Migration result dict
    """
    results = {
        "version": MIGRATION_VERSION,
        "name": MIGRATION_NAME,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "collections_created": [],
        "indexes_created": [],
        "data_seeded": [],
        "errors": [],
    }

    try:
        # 1. Create TRIZ inventive principles collection
        await _create_triz_principles_collection(db, results)

        # 2. Create scenario artifacts collection
        await _create_scenario_artifacts_collection(db, results)

        # 3. Create methodology effectiveness index
        await _create_methodology_indexes(db, results)

        # 4. Seed TRIZ inventive principles
        await _seed_triz_principles(db, results)

        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["success"] = True
        logger.info(f"v3.6.1 migration completed successfully: {results}")

    except Exception as e:
        results["errors"].append(str(e))
        results["success"] = False
        logger.error(f"v3.6.1 migration failed: {e}")

    return results


async def _create_triz_principles_collection(db, results: Dict):
    """Create the TRIZ inventive principles reference collection."""
    collection_name = "triz_inventive_principles"

    existing = await db.list_collection_names()
    if collection_name not in existing:
        await db.create_collection(collection_name)
        results["collections_created"].append(collection_name)
        logger.info(f"Created collection: {collection_name}")

    # Create indexes
    await db[collection_name].create_index("number", unique=True)
    results["indexes_created"].append(f"{collection_name}.number (unique)")

    await db[collection_name].create_index("name")
    results["indexes_created"].append(f"{collection_name}.name")


async def _create_scenario_artifacts_collection(db, results: Dict):
    """Create the scenario artifacts collection."""
    collection_name = "scenario_artifacts"

    existing = await db.list_collection_names()
    if collection_name not in existing:
        await db.create_collection(collection_name)
        results["collections_created"].append(collection_name)
        logger.info(f"Created collection: {collection_name}")

    # Create indexes
    await db[collection_name].create_index("pursuit_id")
    results["indexes_created"].append(f"{collection_name}.pursuit_id")

    await db[collection_name].create_index("trigger")
    results["indexes_created"].append(f"{collection_name}.trigger")

    await db[collection_name].create_index("created_at")
    results["indexes_created"].append(f"{collection_name}.created_at")

    # Compound index for scenario decision analysis
    await db[collection_name].create_index(
        [("decision.chosen_scenario", 1), ("trigger", 1)],
        name="scenario_decision_analysis"
    )
    results["indexes_created"].append(f"{collection_name}.scenario_decision_analysis (compound)")


async def _create_methodology_indexes(db, results: Dict):
    """Create indexes for methodology effectiveness queries."""
    collection_name = "pursuits"

    # Methodology effectiveness index for 5-archetype benchmarking
    await db[collection_name].create_index(
        [("methodology", 1), ("outcome", 1), ("completed_at", -1)],
        name="methodology_effectiveness_v3_6_1"
    )
    results["indexes_created"].append(f"{collection_name}.methodology_effectiveness_v3_6_1 (compound)")

    # TRIZ state index
    await db[collection_name].create_index(
        [("triz_state.active_contradiction.improving_parameter", 1)],
        name="triz_contradiction_lookup",
        sparse=True
    )
    results["indexes_created"].append(f"{collection_name}.triz_contradiction_lookup (sparse)")

    # Blue Ocean state index
    await db[collection_name].create_index(
        [("blue_ocean_state.non_customer_tier", 1)],
        name="blue_ocean_non_customer_lookup",
        sparse=True
    )
    results["indexes_created"].append(f"{collection_name}.blue_ocean_non_customer_lookup (sparse)")


async def _seed_triz_principles(db, results: Dict):
    """Seed the 40 TRIZ inventive principles if not present."""
    collection_name = "triz_inventive_principles"

    # Check if already seeded
    count = await db[collection_name].count_documents({})
    if count >= 40:
        logger.info("TRIZ principles already seeded, skipping")
        return

    # Import principles from the methodology module
    try:
        import sys
        import os

        # Add app to path if needed
        app_path = os.path.join(os.path.dirname(__file__), "..", "..", "app")
        if app_path not in sys.path:
            sys.path.insert(0, app_path)

        from methodology.triz.inventive_principles import INVENTIVE_PRINCIPLES

        # Insert principles
        if count == 0:
            await db[collection_name].insert_many(INVENTIVE_PRINCIPLES)
            results["data_seeded"].append(f"40 TRIZ inventive principles")
            logger.info(f"Seeded {len(INVENTIVE_PRINCIPLES)} TRIZ inventive principles")
        else:
            # Insert any missing principles
            for principle in INVENTIVE_PRINCIPLES:
                existing = await db[collection_name].find_one({"number": principle["number"]})
                if not existing:
                    await db[collection_name].insert_one(principle)
            results["data_seeded"].append("TRIZ principles (incremental)")

    except ImportError as e:
        logger.warning(f"Could not import TRIZ principles for seeding: {e}")
        results["errors"].append(f"TRIZ principles import failed: {e}")


async def rollback(db) -> Dict[str, Any]:
    """
    Rollback the v3.6.1 migration.

    Args:
        db: MongoDB database instance

    Returns:
        Rollback result dict
    """
    results = {
        "version": MIGRATION_VERSION,
        "action": "rollback",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "collections_dropped": [],
        "indexes_dropped": [],
        "errors": [],
    }

    try:
        # Drop scenario artifacts collection
        await db.drop_collection("scenario_artifacts")
        results["collections_dropped"].append("scenario_artifacts")

        # Drop TRIZ principles collection
        await db.drop_collection("triz_inventive_principles")
        results["collections_dropped"].append("triz_inventive_principles")

        # Drop indexes (these will also be dropped with collection drops)
        # but handle any indexes on existing collections
        try:
            await db.pursuits.drop_index("methodology_effectiveness_v3_6_1")
            results["indexes_dropped"].append("pursuits.methodology_effectiveness_v3_6_1")
        except Exception:
            pass

        try:
            await db.pursuits.drop_index("triz_contradiction_lookup")
            results["indexes_dropped"].append("pursuits.triz_contradiction_lookup")
        except Exception:
            pass

        try:
            await db.pursuits.drop_index("blue_ocean_non_customer_lookup")
            results["indexes_dropped"].append("pursuits.blue_ocean_non_customer_lookup")
        except Exception:
            pass

        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["success"] = True
        logger.info(f"v3.6.1 rollback completed: {results}")

    except Exception as e:
        results["errors"].append(str(e))
        results["success"] = False
        logger.error(f"v3.6.1 rollback failed: {e}")

    return results


def get_migration_info() -> Dict[str, Any]:
    """Get information about this migration."""
    return {
        "version": MIGRATION_VERSION,
        "name": MIGRATION_NAME,
        "description": "Methodology Expansion & Scenario Intelligence",
        "new_collections": [
            "triz_inventive_principles",
            "scenario_artifacts",
        ],
        "new_indexes": [
            "triz_inventive_principles.number (unique)",
            "scenario_artifacts.pursuit_id",
            "scenario_artifacts.trigger",
            "scenario_artifacts.created_at",
            "scenario_artifacts.scenario_decision_analysis",
            "pursuits.methodology_effectiveness_v3_6_1",
            "pursuits.triz_contradiction_lookup",
            "pursuits.blue_ocean_non_customer_lookup",
        ],
        "seed_data": [
            "40 TRIZ inventive principles",
        ],
        "dependencies": ["005_v3_6_0_biomimicry"],
    }
