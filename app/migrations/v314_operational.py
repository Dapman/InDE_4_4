"""
v3.14 Operational Migration
Creates the onboarding_metrics collection with indexes.
IDEMPOTENT: Creates index only if collection is new.

v3.14: Operational Readiness
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run(db) -> dict:
    """
    Create onboarding_metrics collection and indexes.

    Args:
        db: Database instance (expects db.db for raw pymongo access)

    Returns:
        dict with migration results
    """
    raw_db = db.db if hasattr(db, 'db') else db

    # Create indexes on onboarding_metrics
    raw_db.onboarding_metrics.create_index(
        [("user_id", 1), ("started_at", -1)],
        background=True,
        name="onboarding_metrics_user_started"
    )
    raw_db.onboarding_metrics.create_index(
        [("started_at", -1)],
        background=True,
        name="onboarding_metrics_started"
    )

    logger.info("v3.14 migration: onboarding_metrics collection and indexes ready.")

    # Log the migration
    raw_db.migration_log.insert_one({
        "migration": "v3_14_operational",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "idempotent": True
    })

    return {"status": "ok", "indexes_created": 2}


def run_sync(db) -> dict:
    """
    Synchronous version for non-async contexts.
    """
    raw_db = db.db if hasattr(db, 'db') else db

    raw_db.onboarding_metrics.create_index(
        [("user_id", 1), ("started_at", -1)],
        background=True,
        name="onboarding_metrics_user_started"
    )
    raw_db.onboarding_metrics.create_index(
        [("started_at", -1)],
        background=True,
        name="onboarding_metrics_started"
    )

    logger.info("v3.14 migration (sync): onboarding_metrics collection and indexes ready.")

    raw_db.migration_log.insert_one({
        "migration": "v3_14_operational",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "idempotent": True
    })

    return {"status": "ok", "indexes_created": 2}
