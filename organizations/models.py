"""
InDE MVP v3.3 - Organization Models
Pydantic models for organization and membership entities.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re


class OrganizationSettings(BaseModel):
    """Organization-level settings."""
    default_pursuit_visibility: str = Field(
        default="org_private",
        description="Default visibility for new pursuits: org_private | team_only | public"
    )
    ikf_sharing_level: str = Field(
        default="ORG_ONLY",
        description="IKF contribution sharing: NONE | ORG_ONLY | FEDERATED"
    )
    max_members: Optional[int] = Field(
        default=None,
        description="Maximum number of members (null = unlimited)"
    )
    methodology_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred innovation methodologies/archetypes"
    )
    coaching_intensity_default: str = Field(
        default="balanced",
        description="Default coaching intensity: comprehensive | balanced | light"
    )


class OrganizationStats(BaseModel):
    """Organization statistics."""
    total_members: int = Field(default=1, ge=0)
    total_pursuits: int = Field(default=0, ge=0)
    active_pursuits: int = Field(default=0, ge=0)
    total_patterns_contributed: int = Field(default=0, ge=0)


class OrganizationCreate(BaseModel):
    """Request model for creating an organization."""
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Organization display name"
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Organization description"
    )
    settings: Optional[OrganizationSettings] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Organization name cannot be empty')
        return v.strip()


class OrganizationUpdate(BaseModel):
    """Request model for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[OrganizationSettings] = None
    status: Optional[str] = Field(
        None,
        description="Organization status: CREATED | ACTIVE | SUSPENDED | ARCHIVED"
    )

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v and v not in ["CREATED", "ACTIVE", "SUSPENDED", "ARCHIVED"]:
            raise ValueError('Invalid status. Must be CREATED, ACTIVE, SUSPENDED, or ARCHIVED')
        return v


class Organization(BaseModel):
    """Complete organization entity."""
    org_id: str
    name: str
    slug: str
    description: str = ""
    created_by: str
    created_at: datetime
    updated_at: datetime
    status: str = "CREATED"
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)
    stats: OrganizationStats = Field(default_factory=OrganizationStats)

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Response model for organization endpoints."""
    org_id: str
    name: str
    slug: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    settings: OrganizationSettings
    stats: OrganizationStats
    user_role: Optional[str] = None  # Populated based on requesting user

    class Config:
        from_attributes = True


class MemberPermissions(BaseModel):
    """Member permissions within an organization."""
    can_create_pursuits: bool = True
    can_invite_members: bool = False
    can_manage_org_settings: bool = False
    can_review_ikf_contributions: bool = False


class MembershipCreate(BaseModel):
    """Request model for creating a membership (inviting a user)."""
    user_id: str = Field(..., description="User ID to invite")
    role: str = Field(
        default="member",
        description="Role: admin | member | viewer"
    )
    permissions: Optional[MemberPermissions] = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ["admin", "member", "viewer"]:
            raise ValueError('Role must be admin, member, or viewer')
        return v


class Membership(BaseModel):
    """Complete membership entity."""
    membership_id: str
    org_id: str
    user_id: str
    role: str
    invited_by: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    status: str = "pending"
    permissions: MemberPermissions = Field(default_factory=MemberPermissions)

    class Config:
        from_attributes = True


class MembershipResponse(BaseModel):
    """Response model for membership endpoints."""
    membership_id: str
    org_id: str
    user_id: str
    role: str
    status: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    permissions: MemberPermissions
    # User details populated from user lookup
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class InviteCreate(BaseModel):
    """Request model for generating an invite token."""
    role: str = Field(
        default="member",
        description="Role for invited user: member | viewer (not admin)"
    )
    expires_in_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Token expiration in days (1-30)"
    )
    max_uses: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of times token can be used"
    )

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        # Token-based invites cannot grant admin role
        if v not in ["member", "viewer"]:
            raise ValueError('Token-based invites can only grant member or viewer role')
        return v


class InviteResponse(BaseModel):
    """Response model for invite token generation."""
    token: str
    org_id: str
    role: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    max_uses: int
    current_uses: int = 0


class InviteToken(BaseModel):
    """Complete invite token entity."""
    token: str
    org_id: str
    role: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    max_uses: int = 1
    current_uses: int = 0
    used_by: List[str] = Field(default_factory=list)
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


def generate_slug(name: str) -> str:
    """
    Generate a URL-safe slug from an organization name.

    Examples:
        "Nexus Dynamics" -> "nexus-dynamics"
        "My Company!" -> "my-company"
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = name.lower().strip()
    # Remove special characters except hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace multiple spaces/hyphens with single hyphen
    slug = re.sub(r'[\s-]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug
