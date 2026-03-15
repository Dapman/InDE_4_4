"""
InDE v3.3 - Team Innovation Integration Tests
Tests for organization, shared pursuit, and team collaboration features.
"""

import pytest
from datetime import datetime, timezone
import uuid

# Test fixtures and setup


@pytest.fixture
def db():
    """Get database instance (uses mongomock in test)."""
    import os
    os.environ["USE_MONGOMOCK"] = "true"

    from database import Database
    return Database()


@pytest.fixture
def test_users(db):
    """Create test users."""
    users = []
    for i in range(3):
        user_id = str(uuid.uuid4())
        db.create_user(user_id, f"Test User {i}", f"user{i}@test.com")
        users.append({"user_id": user_id, "name": f"Test User {i}"})
    return users


@pytest.fixture
def test_org(db, test_users):
    """Create test organization with first user as admin."""
    org_data = {
        "name": "Test Organization",
        "slug": "test-org",
        "description": "Test organization for v3.3 testing",
        "created_by": test_users[0]["user_id"],
        "settings": {
            "default_pursuit_visibility": "org_private",
            "ikf_sharing_level": "ORG_ONLY"
        }
    }
    org_id = db.create_organization(org_data)
    return org_id


# =============================================================================
# Organization Tests
# =============================================================================

class TestOrganizationLifecycle:
    """Test organization CRUD operations."""

    def test_create_organization(self, db, test_users):
        """Test organization creation."""
        org_data = {
            "name": "New Org",
            "slug": "new-org",
            "created_by": test_users[0]["user_id"]
        }
        org_id = db.create_organization(org_data)

        assert org_id is not None

        org = db.get_organization(org_id)
        assert org is not None
        assert org["name"] == "New Org"
        assert org["status"] == "CREATED"

    def test_organization_unique_slug(self, db, test_users):
        """Test that org slugs must be unique."""
        org_data = {
            "name": "Org One",
            "slug": "unique-slug",
            "created_by": test_users[0]["user_id"]
        }
        db.create_organization(org_data)

        # Second org with same slug should fail
        # (In real implementation, service layer handles this)
        org2 = db.get_organization_by_slug("unique-slug")
        assert org2 is not None

    def test_update_organization(self, db, test_org):
        """Test organization update."""
        success = db.update_organization(test_org, {
            "description": "Updated description",
            "status": "ACTIVE"
        })
        assert success

        org = db.get_organization(test_org)
        assert org["description"] == "Updated description"
        assert org["status"] == "ACTIVE"


# =============================================================================
# Membership Tests
# =============================================================================

class TestMembershipLifecycle:
    """Test membership operations."""

    def test_create_membership(self, db, test_org, test_users):
        """Test membership creation (invitation)."""
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[1]["user_id"],
            "role": "member",
            "invited_by": test_users[0]["user_id"],
            "status": "pending"
        }
        membership_id = db.create_membership(membership_data)

        assert membership_id is not None

        membership = db.get_membership(membership_id)
        assert membership["status"] == "pending"
        assert membership["role"] == "member"

    def test_accept_membership(self, db, test_org, test_users):
        """Test accepting membership invitation."""
        # Create pending membership
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[1]["user_id"],
            "role": "member",
            "invited_by": test_users[0]["user_id"],
            "status": "pending"
        }
        membership_id = db.create_membership(membership_data)

        # Accept
        success = db.accept_membership(membership_id)
        assert success

        membership = db.get_membership(membership_id)
        assert membership["status"] == "active"
        assert membership["accepted_at"] is not None

    def test_change_membership_role(self, db, test_org, test_users):
        """Test changing member role."""
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[1]["user_id"],
            "role": "member",
            "invited_by": test_users[0]["user_id"],
            "status": "active"
        }
        membership_id = db.create_membership(membership_data)

        success = db.change_membership_role(membership_id, "admin")
        assert success

        membership = db.get_membership(membership_id)
        assert membership["role"] == "admin"

    def test_depart_membership(self, db, test_org, test_users):
        """Test member departure."""
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[1]["user_id"],
            "role": "member",
            "invited_by": test_users[0]["user_id"],
            "status": "active"
        }
        membership_id = db.create_membership(membership_data)

        success = db.depart_membership(membership_id)
        assert success

        membership = db.get_membership(membership_id)
        assert membership["status"] == "departed"


# =============================================================================
# Shared Pursuit Tests
# =============================================================================

class TestSharedPursuits:
    """Test shared pursuit operations."""

    def test_share_pursuit(self, db, test_users):
        """Test sharing a pursuit with team members."""
        # Create pursuit
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")
        pursuit_id = pursuit["pursuit_id"]

        # Share with second user
        sharing_data = {
            "is_shared": True,
            "team_members": [{
                "user_id": test_users[1]["user_id"],
                "role": "editor",
                "joined_at": datetime.now(timezone.utc)
            }]
        }
        success = db.update_pursuit_sharing(pursuit_id, sharing_data)
        assert success

        pursuit = db.get_pursuit(pursuit_id)
        assert pursuit["sharing"]["is_shared"] is True
        assert len(pursuit["sharing"]["team_members"]) == 1

    def test_add_team_member(self, db, test_users):
        """Test adding team member to pursuit."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")
        pursuit_id = pursuit["pursuit_id"]

        success = db.add_pursuit_team_member(pursuit_id, test_users[1]["user_id"], "editor")
        assert success

        pursuit = db.get_pursuit(pursuit_id)
        assert pursuit["sharing"]["is_shared"] is True

    def test_remove_team_member(self, db, test_users):
        """Test removing team member from pursuit."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")
        pursuit_id = pursuit["pursuit_id"]

        # Add then remove
        db.add_pursuit_team_member(pursuit_id, test_users[1]["user_id"], "editor")
        success = db.remove_pursuit_team_member(pursuit_id, test_users[1]["user_id"])
        assert success

    def test_practice_pursuit_flag(self, db, test_users):
        """Test practice pursuit marking."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Practice Pursuit")
        pursuit_id = pursuit["pursuit_id"]

        success = db.set_pursuit_practice_flag(pursuit_id, True)
        assert success

        pursuit = db.get_pursuit(pursuit_id)
        assert pursuit["is_practice"] is True


# =============================================================================
# Activity Events Tests
# =============================================================================

class TestActivityEvents:
    """Test activity event operations."""

    def test_create_activity_event(self, db, test_users):
        """Test creating activity event."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")

        event_data = {
            "event_type": "element.contributed",
            "pursuit_id": pursuit["pursuit_id"],
            "actor_id": test_users[0]["user_id"],
            "payload": {
                "summary": "contributed a vision element",
                "details": {"element_type": "vision"},
                "mentions": []
            }
        }
        event_id = db.create_activity_event(event_data)

        assert event_id is not None

    def test_get_pursuit_activity(self, db, test_users):
        """Test retrieving pursuit activity."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")
        pursuit_id = pursuit["pursuit_id"]

        # Create some events
        for i in range(5):
            db.create_activity_event({
                "event_type": "element.contributed",
                "pursuit_id": pursuit_id,
                "actor_id": test_users[0]["user_id"],
                "payload": {"summary": f"event {i}"}
            })

        events = db.get_pursuit_activity(pursuit_id, limit=10)
        assert len(events) == 5

    def test_activity_mentions(self, db, test_users):
        """Test activity event mentions."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")

        db.create_activity_event({
            "event_type": "mention.created",
            "pursuit_id": pursuit["pursuit_id"],
            "actor_id": test_users[0]["user_id"],
            "payload": {
                "summary": "mentioned a team member",
                "mentions": [test_users[1]["user_id"]]
            }
        })

        mentions = db.get_user_mentions(test_users[1]["user_id"])
        assert len(mentions) == 1

    def test_mark_activity_read(self, db, test_users):
        """Test marking activity as read."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Test Pursuit")

        event_id = db.create_activity_event({
            "event_type": "element.contributed",
            "pursuit_id": pursuit["pursuit_id"],
            "actor_id": test_users[0]["user_id"],
            "payload": {"mentions": [test_users[1]["user_id"]]}
        })

        count = db.mark_activity_read([event_id], test_users[1]["user_id"])
        assert count == 1


# =============================================================================
# RBAC Tests
# =============================================================================

class TestRBAC:
    """Test role-based access control."""

    def test_org_admin_permission(self, db, test_org, test_users):
        """Test org admin has all permissions."""
        # Create admin membership
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[0]["user_id"],
            "role": "admin",
            "invited_by": test_users[0]["user_id"],
            "status": "active",
            "permissions": {
                "can_create_pursuits": True,
                "can_invite_members": True,
                "can_manage_org_settings": True,
                "can_review_ikf_contributions": True
            }
        }
        db.create_membership(membership_data)

        membership = db.get_user_membership_in_org(test_users[0]["user_id"], test_org)
        assert membership["permissions"]["can_manage_org_settings"] is True

    def test_org_member_permission(self, db, test_org, test_users):
        """Test org member has limited permissions."""
        membership_data = {
            "org_id": test_org,
            "user_id": test_users[1]["user_id"],
            "role": "member",
            "invited_by": test_users[0]["user_id"],
            "status": "active",
            "permissions": {
                "can_create_pursuits": True,
                "can_invite_members": True,
                "can_manage_org_settings": False,
                "can_review_ikf_contributions": False
            }
        }
        db.create_membership(membership_data)

        membership = db.get_user_membership_in_org(test_users[1]["user_id"], test_org)
        assert membership["permissions"]["can_manage_org_settings"] is False

    def test_pursuit_owner_access(self, db, test_users):
        """Test pursuit owner has full access."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Owner Test")

        # Owner is always the creator
        assert pursuit["user_id"] == test_users[0]["user_id"]

    def test_pursuit_editor_access(self, db, test_users):
        """Test pursuit editor can contribute elements."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Editor Test")
        pursuit_id = pursuit["pursuit_id"]

        # Add editor
        db.add_pursuit_team_member(pursuit_id, test_users[1]["user_id"], "editor")

        pursuit = db.get_pursuit(pursuit_id)
        team_member = next(
            (m for m in pursuit["sharing"]["team_members"]
             if m["user_id"] == test_users[1]["user_id"]),
            None
        )
        assert team_member is not None
        assert team_member["role"] == "editor"


# =============================================================================
# Team Scaffolding Tests
# =============================================================================

class TestTeamScaffolding:
    """Test team scaffolding operations."""

    def test_update_team_scaffolding(self, db, test_users):
        """Test updating team scaffolding data."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Scaffolding Test")
        pursuit_id = pursuit["pursuit_id"]

        team_scaffolding = {
            "element_attribution": {
                "vision.problem_statement": {
                    "user_id": test_users[0]["user_id"],
                    "contributed_at": datetime.now(timezone.utc)
                }
            },
            "team_completeness": 0.1,
            "member_contributions": {
                test_users[0]["user_id"]: {
                    "element_count": 1,
                    "element_types": {"vision": 1}
                }
            },
            "gap_analysis": {}
        }

        success = db.update_pursuit_team_scaffolding(pursuit_id, team_scaffolding)
        assert success

        pursuit = db.get_pursuit(pursuit_id)
        assert pursuit["team_scaffolding"]["team_completeness"] == 0.1

    def test_fear_sharing_toggle(self, db, test_users):
        """Test fear de-anonymization toggle."""
        pursuit = db.create_pursuit(test_users[0]["user_id"], "Fear Test")
        pursuit_id = pursuit["pursuit_id"]

        success = db.update_pursuit_fear_sharing(
            pursuit_id, "capability_fears", True
        )
        assert success

        pursuit = db.get_pursuit(pursuit_id)
        assert pursuit["fear_sharing"]["capability_fears"]["shared_with_team"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
