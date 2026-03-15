"""
InDE v3.5.0 - Initial Migration

Creates indexes and updates schema for v3.5.0 changes:
- Adds schema_version field to ikf_contributions
- Creates indexes for efficient federation queries
- Updates any legacy documents missing required fields
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from migrate import Migration


class V350InitialMigration(Migration):
    """v3.5.0 Initial Migration - Schema versioning and indexes."""

    version = "001"
    name = "v3_5_0_initial"
    description = "Add schema versioning and federation indexes"

    def up(self, db) -> bool:
        """Apply migration."""
        print()

        # 1. Add schema_version to existing IKF contributions
        result = db.ikf_contributions.update_many(
            {"schema_version": {"$exists": False}},
            {"$set": {"schema_version": "3.4.0"}}  # Mark legacy as 3.4.0
        )
        print(f"  - Updated {result.modified_count} IKF contributions with schema_version")

        # 2. Create indexes for federation queries
        indexes_created = 0

        # IKF contributions - status + created_at for dashboard queries
        try:
            db.ikf_contributions.create_index(
                [("status", 1), ("created_at", -1)],
                name="idx_status_created"
            )
            indexes_created += 1
        except Exception as e:
            print(f"  - Warning: Could not create idx_status_created: {e}")

        # IKF contributions - user_id + package_type for rate limiting
        try:
            db.ikf_contributions.create_index(
                [("user_id", 1), ("package_type", 1), ("auto_triggered", 1)],
                name="idx_user_package_auto"
            )
            indexes_created += 1
        except Exception as e:
            print(f"  - Warning: Could not create idx_user_package_auto: {e}")

        # IKF contributions - federation_status for sync
        try:
            db.ikf_contributions.create_index(
                [("federation_status", 1)],
                name="idx_federation_status"
            )
            indexes_created += 1
        except Exception as e:
            print(f"  - Warning: Could not create idx_federation_status: {e}")

        # Pursuits - org_id for portfolio queries
        try:
            db.pursuits.create_index(
                [("org_id", 1), ("status", 1)],
                name="idx_org_status"
            )
            indexes_created += 1
        except Exception as e:
            print(f"  - Warning: Could not create idx_org_status: {e}")

        # Audit events - compound index for queries
        try:
            db.audit_events.create_index(
                [("timestamp", -1), ("event_type", 1)],
                name="idx_timestamp_type"
            )
            indexes_created += 1
        except Exception as e:
            print(f"  - Warning: Could not create idx_timestamp_type: {e}")

        print(f"  - Created {indexes_created} indexes")

        # 3. Add version tracking document
        db._schema_version.update_one(
            {"_id": "current"},
            {"$set": {
                "version": "3.5.0",
                "migration": "001",
                "updated_at": __import__("datetime").datetime.now(timezone.utc)
            }},
            upsert=True
        )
        print("  - Updated schema version to 3.5.0")

        return True

    def down(self, db) -> bool:
        """Rollback migration."""
        print()

        # 1. Remove schema_version from contributions marked as 3.4.0
        result = db.ikf_contributions.update_many(
            {"schema_version": "3.4.0"},
            {"$unset": {"schema_version": ""}}
        )
        print(f"  - Removed schema_version from {result.modified_count} documents")

        # 2. Drop created indexes
        indexes_dropped = 0
        for idx_name in ["idx_status_created", "idx_user_package_auto",
                         "idx_federation_status", "idx_org_status", "idx_timestamp_type"]:
            try:
                # Try each collection that might have the index
                for coll_name in ["ikf_contributions", "pursuits", "audit_events"]:
                    try:
                        db[coll_name].drop_index(idx_name)
                        indexes_dropped += 1
                    except:
                        pass
            except Exception:
                pass

        print(f"  - Dropped {indexes_dropped} indexes")

        # 3. Revert version tracking
        db._schema_version.update_one(
            {"_id": "current"},
            {"$set": {
                "version": "3.4.0",
                "migration": "000",
                "updated_at": __import__("datetime").datetime.now(timezone.utc)
            }}
        )
        print("  - Reverted schema version to 3.4.0")

        return True
