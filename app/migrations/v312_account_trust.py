"""
v3.12 Account Trust Migration
Adds account status and deletion fields to existing users.

IDEMPOTENT: Only updates documents where new fields are absent.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run(db) -> dict:
    """
    Add v3.12 account trust fields to all existing users.

    New fields:
    - status: "active" | "deactivated" | "deleted"
    - deletion_requested_at: ISO timestamp when deletion initiated
    - deletion_scheduled_for: ISO timestamp = deletion_requested_at + 14 days
    - deletion_cancellation_token: Cryptographic token for cancellation link
    - deleted_at: ISO timestamp when fully deleted

    Args:
        db: Database instance (expects db.db for raw pymongo access)

    Returns:
        dict with migration results
    """
    raw_db = db.db if hasattr(db, 'db') else db

    # Add status and deletion fields to all users missing them
    result = raw_db.users.update_many(
        {"status": {"$exists": False}},
        {"$set": {
            "status": "active",
            "deletion_requested_at": None,
            "deletion_scheduled_for": None,
            "deletion_cancellation_token": None,
            "deleted_at": None,
        }}
    )

    count = result.modified_count
    logger.info(f"v3.12 migration: added account trust fields to {count} users.")

    # Log migration execution
    raw_db.migration_log.insert_one({
        "migration": "v3_12_account_trust",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "users_updated": count,
        "idempotent": True
    })

    return {"migrated_users": count}
