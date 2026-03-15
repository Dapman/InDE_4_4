"""
InDE v3.3 - Team Events Schema Migration
Adds activity_events collection and team event indexes.

Run with: python -m migrations.v33_team_events_schema
"""

import os
import sys
from datetime import datetime, timezone

# Add app directory to path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inde.migration.v33")


# v3.3 Team Event Types
TEAM_EVENT_TYPES = [
    "team.member.added",
    "team.member.departed",
    "team.role.changed",
    "team.gap.identified",
    "team.milestone.reached",
    "org.created",
    "org.member.joined",
]

ACTIVITY_EVENT_TYPES = [
    "element.contributed",
    "artifact.created",
    "session.started",
    "session.completed",
    "state.changed",
    "member.joined",
    "member.departed",
    "mention.created",
    "risk.evidence.submitted",
    "convergence.detected",
    "report.generated",
]


def _safe_create_index(collection, keys, **kwargs):
    """Create index, ignoring if equivalent index already exists."""
    try:
        return collection.create_index(keys, **kwargs)
    except OperationFailure as e:
        if e.code == 85:  # IndexOptionsConflict
            logger.info(f"Index already exists (equivalent): {kwargs.get('name', keys)}")
            return None
        raise


def run_migration():
    """Run v3.3 team events schema migration."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("MONGODB_DB", "inde")

    logger.info(f"Connecting to MongoDB: {mongo_uri}")
    client = MongoClient(mongo_uri)
    db = client[db_name]

    try:
        # 1. Create organizations collection and indexes
        _create_organizations_indexes(db)

        # 2. Create memberships collection and indexes
        _create_memberships_indexes(db)

        # 3. Create activity_events collection and indexes
        _create_activity_events_indexes(db)

        # 4. Add team fields to pursuits collection
        _extend_pursuits_schema(db)

        # 5. Add team event types to system config
        _register_event_types(db)

        logger.info("v3.3 Team events schema migration completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()


def _create_organizations_indexes(db):
    """Create indexes for organizations collection."""
    logger.info("Creating organizations indexes...")

    # Unique slug lookup
    _safe_create_index(
        db.organizations,
        [("slug", ASCENDING)],
        name="idx_slug_unique",
        unique=True
    )

    # Creator lookup
    _safe_create_index(
        db.organizations,
        [("created_by", ASCENDING)],
        name="idx_created_by"
    )

    # Status filter
    _safe_create_index(
        db.organizations,
        [("status", ASCENDING)],
        name="idx_status"
    )

    logger.info("Created organizations indexes")


def _create_memberships_indexes(db):
    """Create indexes for memberships collection."""
    logger.info("Creating memberships indexes...")

    # Unique user-org combination
    _safe_create_index(
        db.memberships,
        [("user_id", ASCENDING), ("org_id", ASCENDING)],
        name="idx_user_org_unique",
        unique=True
    )

    # Org members lookup (by status)
    _safe_create_index(
        db.memberships,
        [("org_id", ASCENDING), ("status", ASCENDING)],
        name="idx_org_status"
    )

    # User orgs lookup (by status)
    _safe_create_index(
        db.memberships,
        [("user_id", ASCENDING), ("status", ASCENDING)],
        name="idx_user_status"
    )

    # Role-based queries
    _safe_create_index(
        db.memberships,
        [("org_id", ASCENDING), ("role", ASCENDING)],
        name="idx_org_role"
    )

    logger.info("Created memberships indexes")


def _create_activity_events_indexes(db):
    """Create indexes for activity_events collection."""
    logger.info("Creating activity_events indexes...")

    # Primary lookup by event_id
    _safe_create_index(
        db.activity_events,
        [("event_id", ASCENDING)],
        name="idx_event_id",
        unique=True
    )

    # Pursuit activity timeline
    _safe_create_index(
        db.activity_events,
        [("pursuit_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_pursuit_timeline"
    )

    # Org activity timeline
    _safe_create_index(
        db.activity_events,
        [("org_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_org_timeline"
    )

    # Actor activity
    _safe_create_index(
        db.activity_events,
        [("actor_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_actor_timeline"
    )

    # Event type queries
    _safe_create_index(
        db.activity_events,
        [("event_type", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_event_type_timeline"
    )

    # Mentions lookup (for notifications)
    _safe_create_index(
        db.activity_events,
        [("payload.mentions", ASCENDING)],
        name="idx_mentions"
    )

    # Unread notifications
    _safe_create_index(
        db.activity_events,
        [("payload.mentions", ASCENDING), ("read_by", ASCENDING)],
        name="idx_unread_mentions"
    )

    # TTL index for automatic cleanup (90 days)
    _safe_create_index(
        db.activity_events,
        [("ttl_expiry", ASCENDING)],
        name="idx_ttl_expiry",
        expireAfterSeconds=0  # Honor ttl_expiry field value
    )

    logger.info("Created activity_events indexes (8 indexes)")


def _extend_pursuits_schema(db):
    """Add v3.3 team fields to existing pursuits."""
    logger.info("Extending pursuits schema with team fields...")

    # Add org_id field to pursuits that don't have it
    result = db.pursuits.update_many(
        {"org_id": {"$exists": False}},
        {"$set": {"org_id": None}}
    )
    logger.info(f"Added org_id to {result.modified_count} pursuits")

    # Add is_practice field
    result = db.pursuits.update_many(
        {"is_practice": {"$exists": False}},
        {"$set": {"is_practice": False}}
    )
    logger.info(f"Added is_practice to {result.modified_count} pursuits")

    # Add sharing field
    result = db.pursuits.update_many(
        {"sharing": {"$exists": False}},
        {"$set": {
            "sharing": {
                "is_shared": False,
                "team_members": [],
                "invite_tokens": []
            }
        }}
    )
    logger.info(f"Added sharing to {result.modified_count} pursuits")

    # Add team_scaffolding field
    result = db.pursuits.update_many(
        {"team_scaffolding": {"$exists": False}},
        {"$set": {
            "team_scaffolding": {
                "element_attribution": {},
                "team_completeness": 0.0,
                "member_contributions": {},
                "gap_analysis": {}
            }
        }}
    )
    logger.info(f"Added team_scaffolding to {result.modified_count} pursuits")

    # Add fear_sharing field
    result = db.pursuits.update_many(
        {"fear_sharing": {"$exists": False}},
        {"$set": {"fear_sharing": {}}}
    )
    logger.info(f"Added fear_sharing to {result.modified_count} pursuits")

    # Create pursuit org_id index
    _safe_create_index(
        db.pursuits,
        [("org_id", ASCENDING)],
        name="idx_org_id"
    )

    # Create pursuit team_members index
    _safe_create_index(
        db.pursuits,
        [("sharing.team_members.user_id", ASCENDING)],
        name="idx_team_members_user_id"
    )

    logger.info("Extended pursuits schema")


def _register_event_types(db):
    """Register v3.3 event types in system config."""
    logger.info("Registering v3.3 event types...")

    # Store event type registry
    db.system_config.update_one(
        {"key": "event_types_v33"},
        {"$set": {
            "value": {
                "team_events": TEAM_EVENT_TYPES,
                "activity_events": ACTIVITY_EVENT_TYPES,
                "registered_at": datetime.now(timezone.utc)
            }
        }},
        upsert=True
    )

    logger.info(f"Registered {len(TEAM_EVENT_TYPES)} team events and {len(ACTIVITY_EVENT_TYPES)} activity events")


def verify_migration(db_name: str = "inde"):
    """Verify v3.3 migration completed successfully."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client[db_name]

    try:
        # Check organizations indexes
        org_indexes = list(db.organizations.list_indexes())
        if len(org_indexes) < 3:
            logger.warning("organizations missing indexes")
            return False

        # Check memberships indexes
        mem_indexes = list(db.memberships.list_indexes())
        if len(mem_indexes) < 4:
            logger.warning("memberships missing indexes")
            return False

        # Check activity_events indexes
        ae_indexes = list(db.activity_events.list_indexes())
        if len(ae_indexes) < 7:
            logger.warning("activity_events missing indexes")
            return False

        # Check pursuit schema extensions
        sample_pursuit = db.pursuits.find_one({})
        if sample_pursuit:
            required_fields = ["org_id", "is_practice", "sharing", "team_scaffolding", "fear_sharing"]
            for field in required_fields:
                if field not in sample_pursuit:
                    logger.warning(f"Pursuits missing {field} field")
                    return False

        # Check event types registered
        config = db.system_config.find_one({"key": "event_types_v33"})
        if not config:
            logger.warning("Event types not registered")
            return False

        logger.info("v3.3 Migration verification passed")
        return True

    finally:
        client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="InDE v3.3 Team Events Schema Migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration only")
    parser.add_argument("--db", default="inde", help="Database name")
    args = parser.parse_args()

    if args.verify:
        success = verify_migration(args.db)
        sys.exit(0 if success else 1)
    else:
        run_migration()
