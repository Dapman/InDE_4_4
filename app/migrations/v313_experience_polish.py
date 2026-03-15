"""
v3.13 Experience Polish Migration
Adds archive fields to all existing pursuits.
IDEMPOTENT: Only updates documents missing the new fields.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run(db) -> dict:
    """
    Add is_archived and archived_at fields to existing pursuits.

    Args:
        db: Database instance (expects db.db for raw pymongo access)

    Returns:
        dict with migration results
    """
    raw_db = db.db if hasattr(db, 'db') else db

    # Update pursuits missing the is_archived field
    result = raw_db.pursuits.update_many(
        {"is_archived": {"$exists": False}},
        {"$set": {
            "is_archived": False,
            "archived_at": None,
        }}
    )
    count = result.modified_count

    logger.info(f"v3.13 migration: added archive fields to {count} pursuits.")

    # Log the migration
    raw_db.migration_log.insert_one({
        "migration": "v3_13_experience_polish",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "pursuits_updated": count,
        "idempotent": True
    })

    return {"pursuits_updated": count}


def run_sync(db) -> dict:
    """
    Synchronous version for non-async contexts.
    """
    raw_db = db.db if hasattr(db, 'db') else db

    result = raw_db.pursuits.update_many(
        {"is_archived": {"$exists": False}},
        {"$set": {
            "is_archived": False,
            "archived_at": None,
        }}
    )
    count = result.modified_count

    logger.info(f"v3.13 migration (sync): added archive fields to {count} pursuits.")

    raw_db.migration_log.insert_one({
        "migration": "v3_13_experience_polish",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "pursuits_updated": count,
        "idempotent": True
    })

    return {"pursuits_updated": count}
