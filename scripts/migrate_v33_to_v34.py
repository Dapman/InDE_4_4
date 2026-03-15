"""
InDE MVP v3.4 Migration Script
Migrates v3.3 schema to v3.4 "Enterprise Intelligence & Coaching Convergence"

This script is IDEMPOTENT - safe to re-execute multiple times.

v3.4 Schema Additions:
1. audit_events - Immutable audit log (SOC 2 ready)
2. convergence_sessions - Convergence state per coaching session
3. innovator_profiles - IDTFS external profile + availability
4. vouching_records - IDTFS directional endorsements
5. formation_recommendations - IDTFS discovery results
6. composition_patterns - IML/IKF team configuration patterns
7. custom_roles - Organization-defined roles
8. access_policies - Organization-wide policy configuration

Schema Extensions:
- coaching_sessions: +convergence_state, +convergence_initiated_at, +outcomes_captured, +methodology_archetype
- pursuits: +methodology_archetype, +criteria_enforcement, +transition_history

Usage:
    python scripts/migrate_v33_to_v34.py [--dry-run] [--mongo-uri URI]
"""

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import CollectionInvalid, OperationFailure
except ImportError:
    print("ERROR: pymongo is required. Install with: pip install pymongo")
    sys.exit(1)


# Default connection settings
DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_DATABASE = "inde"

# v3.4 New Collections
V34_COLLECTIONS = [
    "audit_events",
    "convergence_sessions",
    "innovator_profiles",
    "vouching_records",
    "formation_recommendations",
    "composition_patterns",
    "custom_roles",
    "access_policies",
]

# Built-in roles (seeded for each organization)
BUILTIN_ROLES = [
    {
        "name": "admin",
        "description": "Full organization management access",
        "permissions": [
            "can_create_pursuits",
            "can_invite_members",
            "can_manage_org_settings",
            "can_review_ikf_contributions",
            "can_view_portfolio_dashboard",
            "can_manage_audit_logs",
            "can_manage_roles",
            "can_manage_retention_policies",
            "can_discover_members",
        ],
        "is_system": True,
    },
    {
        "name": "member",
        "description": "Standard organization member",
        "permissions": [
            "can_create_pursuits",
            "can_discover_members",
            "can_invite_members",
        ],
        "is_system": True,
    },
    {
        "name": "viewer",
        "description": "Read-only organization access",
        "permissions": [],
        "is_system": True,
    },
]

# Default access policy for organizations
DEFAULT_ACCESS_POLICY = {
    "portfolio_dashboard_access": ["admin"],
    "discovery_permissions": {
        "who_can_discover": ["admin", "member"],
        "availability_default": "SELECTIVE",
    },
    "audit_config": {
        "retention_days": 365,
        "export_allowed_roles": ["admin"],
    },
    "methodology_preferences": ["lean_startup", "design_thinking", "stage_gate"],
    "data_retention": {
        "pursuit_retention_days": None,  # Indefinite
        "coaching_session_retention_days": None,
        "activity_event_retention_days": 365,
    },
}


def log(msg: str, dry_run: bool = False):
    """Log a message with timestamp."""
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{datetime.now().isoformat()} {prefix}{msg}")


def create_collections(db, dry_run: bool = False):
    """Step 1: Create 8 new collections."""
    log("Step 1: Creating new collections...", dry_run)

    existing = db.list_collection_names()
    created = 0

    for collection in V34_COLLECTIONS:
        if collection in existing:
            log(f"  Collection '{collection}' already exists, skipping", dry_run)
        else:
            if not dry_run:
                db.create_collection(collection)
            log(f"  Created collection: {collection}", dry_run)
            created += 1

    log(f"Step 1 complete: {created} collections created", dry_run)
    return created


def create_indexes(db, dry_run: bool = False):
    """Step 2: Create all indexes with background=True."""
    log("Step 2: Creating indexes...", dry_run)

    indexes_created = 0

    # audit_events indexes
    audit_indexes = [
        ([("timestamp", DESCENDING)], {"name": "timestamp_ttl"}),
        ([("event_type", ASCENDING), ("timestamp", DESCENDING)], {"name": "event_type_time"}),
        ([("actor_id", ASCENDING), ("timestamp", DESCENDING)], {"name": "actor_time"}),
        ([("org_id", ASCENDING), ("timestamp", DESCENDING)], {"name": "org_time"}),
        ([("resource_type", ASCENDING), ("resource_id", ASCENDING)], {"name": "resource"}),
        ([("correlation_id", ASCENDING)], {"name": "correlation"}),
    ]

    for keys, opts in audit_indexes:
        if not dry_run:
            db.audit_events.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(audit_indexes)} indexes on audit_events", dry_run)

    # convergence_sessions indexes
    conv_indexes = [
        ([("session_id", ASCENDING)], {"name": "session_id", "unique": True}),
        ([("pursuit_id", ASCENDING), ("initiated_at", DESCENDING)], {"name": "pursuit_time"}),
        ([("user_id", ASCENDING), ("initiated_at", DESCENDING)], {"name": "user_time"}),
    ]

    for keys, opts in conv_indexes:
        if not dry_run:
            db.convergence_sessions.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(conv_indexes)} indexes on convergence_sessions", dry_run)

    # innovator_profiles indexes
    profile_indexes = [
        ([("user_id", ASCENDING), ("org_id", ASCENDING)], {"name": "user_org", "unique": True}),
        ([("org_id", ASCENDING), ("availability", ASCENDING)], {"name": "org_availability"}),
    ]

    for keys, opts in profile_indexes:
        if not dry_run:
            db.innovator_profiles.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(profile_indexes)} indexes on innovator_profiles", dry_run)

    # vouching_records indexes
    vouch_indexes = [
        ([("voucher_id", ASCENDING), ("vouched_id", ASCENDING), ("org_id", ASCENDING)], {"name": "vouch_pair"}),
        ([("vouched_id", ASCENDING), ("org_id", ASCENDING), ("is_active", ASCENDING)], {"name": "vouched_active"}),
    ]

    for keys, opts in vouch_indexes:
        if not dry_run:
            db.vouching_records.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(vouch_indexes)} indexes on vouching_records", dry_run)

    # formation_recommendations indexes
    formation_indexes = [
        ([("pursuit_id", ASCENDING), ("created_at", DESCENDING)], {"name": "pursuit_time"}),
        ([("org_id", ASCENDING), ("created_at", DESCENDING)], {"name": "org_time"}),
    ]

    for keys, opts in formation_indexes:
        if not dry_run:
            db.formation_recommendations.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(formation_indexes)} indexes on formation_recommendations", dry_run)

    # composition_patterns indexes
    comp_indexes = [
        ([("domain_tags", ASCENDING), ("phase_applicability", ASCENDING)], {"name": "domain_phase"}),
        ([("org_id", ASCENDING)], {"name": "org"}),
    ]

    for keys, opts in comp_indexes:
        if not dry_run:
            db.composition_patterns.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(comp_indexes)} indexes on composition_patterns", dry_run)

    # custom_roles indexes
    role_indexes = [
        ([("org_id", ASCENDING), ("name", ASCENDING)], {"name": "org_name", "unique": True}),
    ]

    for keys, opts in role_indexes:
        if not dry_run:
            db.custom_roles.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(role_indexes)} indexes on custom_roles", dry_run)

    # access_policies indexes
    policy_indexes = [
        ([("org_id", ASCENDING)], {"name": "org", "unique": True}),
    ]

    for keys, opts in policy_indexes:
        if not dry_run:
            db.access_policies.create_index(keys, background=True, **opts)
        indexes_created += 1
    log(f"  Created {len(policy_indexes)} indexes on access_policies", dry_run)

    log(f"Step 2 complete: {indexes_created} indexes created", dry_run)
    return indexes_created


def seed_builtin_roles(db, dry_run: bool = False):
    """Step 3: Seed built-in roles for each existing organization."""
    log("Step 3: Seeding built-in roles for organizations...", dry_run)

    orgs = list(db.organizations.find({}, {"_id": 1}))
    roles_created = 0

    for org in orgs:
        org_id = org["_id"]

        for role in BUILTIN_ROLES:
            existing = db.custom_roles.find_one({"org_id": org_id, "name": role["name"]})
            if existing:
                continue

            role_doc = {
                "org_id": org_id,
                "name": role["name"],
                "description": role["description"],
                "permissions": role["permissions"],
                "is_system": role["is_system"],
                "created_by": None,  # System-created
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            if not dry_run:
                db.custom_roles.insert_one(role_doc)
            roles_created += 1

    log(f"Step 3 complete: {roles_created} built-in roles seeded for {len(orgs)} organizations", dry_run)
    return roles_created


def seed_access_policies(db, dry_run: bool = False):
    """Step 4: Seed default access_policies for each existing organization."""
    log("Step 4: Seeding default access policies...", dry_run)

    orgs = list(db.organizations.find({}, {"_id": 1}))
    policies_created = 0

    for org in orgs:
        org_id = org["_id"]

        existing = db.access_policies.find_one({"org_id": org_id})
        if existing:
            log(f"  Access policy for org {org_id} already exists, skipping", dry_run)
            continue

        policy_doc = {
            "org_id": org_id,
            **DEFAULT_ACCESS_POLICY,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        if not dry_run:
            db.access_policies.insert_one(policy_doc)
        policies_created += 1

    log(f"Step 4 complete: {policies_created} access policies seeded", dry_run)
    return policies_created


def extend_coaching_sessions(db, dry_run: bool = False):
    """Step 5: Extend coaching_sessions with convergence fields."""
    log("Step 5: Extending coaching_sessions schema...", dry_run)

    update_fields = {
        "$set": {
            "convergence_state": None,
            "convergence_initiated_at": None,
            "outcomes_captured": 0,
            "methodology_archetype": None,
        }
    }

    # Only update documents that don't have convergence_state field
    filter_query = {"convergence_state": {"$exists": False}}

    if not dry_run:
        result = db.coaching_sessions.update_many(filter_query, update_fields)
        modified = result.modified_count
    else:
        modified = db.coaching_sessions.count_documents(filter_query)

    log(f"Step 5 complete: {modified} coaching sessions extended", dry_run)
    return modified


def extend_pursuits(db, dry_run: bool = False):
    """Step 6: Extend pursuits with methodology fields."""
    log("Step 6: Extending pursuits schema...", dry_run)

    # Only update documents that don't have methodology_archetype field
    filter_query = {"methodology_archetype": {"$exists": False}}

    update_fields = {
        "$set": {
            "methodology_archetype": "lean_startup",  # Backward compatibility default
            "criteria_enforcement": "advisory",
            "transition_history": [],
        }
    }

    if not dry_run:
        result = db.pursuits.update_many(filter_query, update_fields)
        modified = result.modified_count
    else:
        modified = db.pursuits.count_documents(filter_query)

    log(f"Step 6 complete: {modified} pursuits extended", dry_run)
    return modified


def create_innovator_profiles(db, dry_run: bool = False):
    """Step 7: Create default innovator_profiles for existing org members."""
    log("Step 7: Creating default innovator profiles...", dry_run)

    memberships = list(db.memberships.find({"status": "active"}, {"user_id": 1, "org_id": 1}))
    profiles_created = 0

    for membership in memberships:
        user_id = membership["user_id"]
        org_id = membership["org_id"]

        existing = db.innovator_profiles.find_one({"user_id": user_id, "org_id": org_id})
        if existing:
            continue

        profile_doc = {
            "user_id": user_id,
            "org_id": org_id,
            "availability": "SELECTIVE",  # Default
            "interest_profile": {
                "domain_areas": [],
                "preferred_phases": [],
                "team_size_preference": None,
                "weekly_capacity_hours": None,
            },
            "professional_background": {
                "domain_expertise_tags": [],
                "career_summary": None,
                "credential_indicators": [],
                "corporate_directory_link": None,
            },
            "profile_completeness": 0.0,
            "last_availability_update": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        if not dry_run:
            db.innovator_profiles.insert_one(profile_doc)
        profiles_created += 1

    log(f"Step 7 complete: {profiles_created} innovator profiles created", dry_run)
    return profiles_created


def verify_migration(db, dry_run: bool = False):
    """Step 8: Verify v3.3 features still work with extended schemas."""
    log("Step 8: Verifying migration...", dry_run)

    errors = []

    # Check all v3.4 collections exist
    existing = db.list_collection_names()
    for collection in V34_COLLECTIONS:
        if collection not in existing:
            errors.append(f"Missing collection: {collection}")

    # Check sample pursuit has new fields
    sample_pursuit = db.pursuits.find_one()
    if sample_pursuit:
        if "methodology_archetype" not in sample_pursuit:
            errors.append("Pursuit missing methodology_archetype field")
        if "criteria_enforcement" not in sample_pursuit:
            errors.append("Pursuit missing criteria_enforcement field")

    # Check sample coaching session has new fields
    sample_session = db.coaching_sessions.find_one()
    if sample_session:
        if "convergence_state" not in sample_session:
            errors.append("Coaching session missing convergence_state field")

    if errors:
        for error in errors:
            log(f"  ERROR: {error}", dry_run)
        log(f"Step 8 FAILED: {len(errors)} errors found", dry_run)
        return False

    log("Step 8 complete: Migration verified successfully", dry_run)
    return True


def run_migration(mongo_uri: str, database: str, dry_run: bool = False):
    """Execute the full 8-step migration."""
    log(f"Starting v3.3 -> v3.4 migration on {database}", dry_run)
    log(f"MongoDB URI: {mongo_uri}", dry_run)

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        db = client[database]
    except Exception as e:
        log(f"ERROR: Failed to connect to MongoDB: {e}")
        return False

    # Execute migration steps
    create_collections(db, dry_run)
    create_indexes(db, dry_run)
    seed_builtin_roles(db, dry_run)
    seed_access_policies(db, dry_run)
    extend_coaching_sessions(db, dry_run)
    extend_pursuits(db, dry_run)
    create_innovator_profiles(db, dry_run)
    success = verify_migration(db, dry_run)

    if success:
        log("Migration completed successfully!", dry_run)
    else:
        log("Migration completed with errors", dry_run)

    client.close()
    return success


def main():
    parser = argparse.ArgumentParser(description="Migrate InDE v3.3 to v3.4")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--mongo-uri", default=DEFAULT_MONGO_URI, help="MongoDB connection URI")
    parser.add_argument("--database", default=DEFAULT_DATABASE, help="Database name")

    args = parser.parse_args()

    success = run_migration(args.mongo_uri, args.database, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
