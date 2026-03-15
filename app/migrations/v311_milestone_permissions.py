"""
v3.11 Milestone Permissions Migration
Backfills created_by_user_id on all existing milestones.
Strategy: look up each milestone's pursuit, find the pursuit creator, assign.

IDEMPOTENT: Only updates milestones where created_by_user_id is None.

TD-014: Team Pursuit Milestone Permissions
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run(db) -> dict:
    """
    Called at app startup before accepting requests.

    Args:
        db: Database instance

    Returns:
        dict with migration stats
    """

    logger.info("v3.11 migration: checking for milestones needing created_by_user_id backfill...")

    # Find all milestones missing created_by_user_id
    milestones_to_update = list(db.db.pursuit_milestones.find(
        {"created_by_user_id": None}
    ).limit(10000))

    if not milestones_to_update:
        logger.info("v3.11 migration: no milestones to backfill.")
        return {"migrated": 0}

    logger.info(f"v3.11 migration: found {len(milestones_to_update)} milestones to backfill")

    # Build a pursuit_id → owner_id lookup
    pursuit_ids = list(set(m.get("pursuit_id") for m in milestones_to_update if m.get("pursuit_id")))
    pursuits = list(db.db.pursuits.find(
        {"pursuit_id": {"$in": pursuit_ids}},
        {"pursuit_id": 1, "created_by": 1, "owner_id": 1, "user_id": 1}
    ))

    # Build lookup map - try created_by, owner_id, user_id in order
    owner_map = {}
    for p in pursuits:
        pid = p.get("pursuit_id")
        owner = p.get("created_by") or p.get("owner_id") or p.get("user_id")
        if pid and owner:
            owner_map[pid] = str(owner)

    # Bulk update
    updated = 0
    for m in milestones_to_update:
        pid = m.get("pursuit_id")
        owner_id = owner_map.get(pid)
        if owner_id:
            db.db.pursuit_milestones.update_one(
                {"_id": m["_id"]},
                {"$set": {
                    "created_by_user_id": owner_id,
                    "updated_at": datetime.now(timezone.utc).isoformat() + "Z"
                }}
            )
            updated += 1

    logger.info(f"v3.11 migration: backfilled created_by_user_id on {updated} milestones.")

    # Log migration completion
    db.db.migration_log.insert_one({
        "migration": "v3_11_milestone_permissions",
        "run_at": datetime.now(timezone.utc).isoformat() + "Z",
        "milestones_updated": updated,
        "idempotent": True
    })

    return {"migrated": updated}
