"""
v3.10 Timeline Integrity Migration
Adds default values for new milestone and time_allocation fields.

TD-001: Milestone versioning fields
TD-002: Time allocation is_computed flag
TD-005: Relative date context fields

IDEMPOTENT: Safe to run multiple times.
"""

from datetime import datetime, timezone
from typing import Any, Dict


async def run(db) -> Dict[str, Any]:
    """
    Called at app startup before accepting requests.

    Adds v3.10 schema fields to existing documents:
    - milestones: milestone_version, supersedes_milestone_id, is_superseded,
                  conflict_resolution_strategy, relative_resolution_method,
                  requires_recalculation, recalculation_prompted_at
    - time_allocations: is_computed, computed_source_milestone_id

    Args:
        db: Motor/pymongo database instance

    Returns:
        Migration result dict with counts
    """
    results = {
        "migration": "v310_timeline_integrity",
        "run_at": datetime.now(timezone.utc).isoformat() + "Z",
        "idempotent": True,
        "milestones_updated": 0,
        "time_allocations_updated": 0
    }

    # Migrate milestones collection (pursuit_milestones)
    milestones_result = await db.pursuit_milestones.update_many(
        {"milestone_version": {"$exists": False}},
        {"$set": {
            # TD-001: Versioning fields
            "milestone_version": 1,
            "supersedes_milestone_id": None,
            "is_superseded": False,
            "conflict_resolution_strategy": None,
            # TD-005: Relative date context fields
            "relative_resolution_method": None,
            "requires_recalculation": False,
            "recalculation_prompted_at": None
        }}
    )
    results["milestones_updated"] = milestones_result.modified_count

    # Migrate time_allocations collection
    allocations_result = await db.time_allocations.update_many(
        {"is_computed": {"$exists": False}},
        {"$set": {
            # TD-002: Computed flag
            "is_computed": False,
            "computed_source_milestone_id": None
        }}
    )
    results["time_allocations_updated"] = allocations_result.modified_count

    # Log migration completion
    await db.migration_log.insert_one({
        "migration": "v310_timeline_integrity",
        "run_at": results["run_at"],
        "idempotent": True,
        "milestones_updated": results["milestones_updated"],
        "time_allocations_updated": results["time_allocations_updated"]
    })

    return results


def run_sync(db) -> Dict[str, Any]:
    """
    Synchronous version for non-async contexts.

    Args:
        db: pymongo database instance (not Motor)

    Returns:
        Migration result dict with counts
    """
    results = {
        "migration": "v310_timeline_integrity",
        "run_at": datetime.now(timezone.utc).isoformat() + "Z",
        "idempotent": True,
        "milestones_updated": 0,
        "time_allocations_updated": 0
    }

    # Migrate milestones collection (pursuit_milestones)
    milestones_result = db.pursuit_milestones.update_many(
        {"milestone_version": {"$exists": False}},
        {"$set": {
            # TD-001: Versioning fields
            "milestone_version": 1,
            "supersedes_milestone_id": None,
            "is_superseded": False,
            "conflict_resolution_strategy": None,
            # TD-005: Relative date context fields
            "relative_resolution_method": None,
            "requires_recalculation": False,
            "recalculation_prompted_at": None
        }}
    )
    results["milestones_updated"] = milestones_result.modified_count

    # Migrate time_allocations collection
    allocations_result = db.time_allocations.update_many(
        {"is_computed": {"$exists": False}},
        {"$set": {
            # TD-002: Computed flag
            "is_computed": False,
            "computed_source_milestone_id": None
        }}
    )
    results["time_allocations_updated"] = allocations_result.modified_count

    # Log migration completion
    db.migration_log.insert_one({
        "migration": "v310_timeline_integrity",
        "run_at": results["run_at"],
        "idempotent": True,
        "milestones_updated": results["milestones_updated"],
        "time_allocations_updated": results["time_allocations_updated"]
    })

    return results
