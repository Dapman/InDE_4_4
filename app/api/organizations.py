"""
InDE v3.3 - Organizations API Routes
Handles organization lifecycle, membership, and invitations.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from auth.middleware import get_current_user

router = APIRouter()


# ===========================================================================
# REQUEST/RESPONSE MODELS
# ===========================================================================

class OrgSettingsRequest(BaseModel):
    default_pursuit_visibility: Optional[str] = "org_private"
    ikf_sharing_level: Optional[str] = "ORG_ONLY"
    max_members: Optional[int] = None
    methodology_preferences: Optional[List[str]] = None
    coaching_intensity_default: Optional[str] = "balanced"


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    settings: Optional[OrgSettingsRequest] = None


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[OrgSettingsRequest] = None
    status: Optional[str] = None


class OrgStatsResponse(BaseModel):
    total_members: int
    total_pursuits: int
    active_pursuits: int
    total_patterns_contributed: int


class OrgResponse(BaseModel):
    org_id: str
    name: str
    slug: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    settings: dict
    stats: OrgStatsResponse
    user_role: Optional[str] = None


class InviteMemberRequest(BaseModel):
    user_id: str
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class MemberPermissionsResponse(BaseModel):
    can_create_pursuits: bool
    can_invite_members: bool
    can_manage_org_settings: bool
    can_review_ikf_contributions: bool


class MemberResponse(BaseModel):
    membership_id: str
    org_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: str
    status: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    permissions: MemberPermissionsResponse


class CreateInviteRequest(BaseModel):
    role: str = Field(default="member", pattern="^(member|viewer)$")
    expires_in_days: int = Field(default=7, ge=1, le=30)
    max_uses: int = Field(default=1, ge=1, le=100)


class InviteResponse(BaseModel):
    token: str
    org_id: str
    role: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    max_uses: int
    current_uses: int


class RedeemInviteRequest(BaseModel):
    token: str


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")


# ===========================================================================
# ORGANIZATION ENDPOINTS
# ===========================================================================

@router.post("", response_model=OrgResponse, status_code=201)
async def create_organization(
    request: Request,
    data: CreateOrgRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new organization.

    The creating user becomes the admin.
    """
    # Import service here to avoid circular imports
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService
    from organizations.models import OrganizationCreate, OrganizationSettings

    service = OrganizationService()
    user_id = current_user["user_id"]

    # Build settings if provided
    settings = None
    if data.settings:
        settings = OrganizationSettings(**data.settings.model_dump())

    org_data = OrganizationCreate(
        name=data.name,
        description=data.description or "",
        settings=settings
    )

    try:
        org = await service.create_organization(user_id, org_data)
        return org
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[OrgResponse])
async def list_my_organizations(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """List all organizations the current user belongs to."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()
    return await service.list_user_organizations(current_user["user_id"])


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get organization details. Must be a member."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()
    org = await service.get_organization(org_id, current_user["user_id"])

    if not org:
        raise HTTPException(
            status_code=404,
            detail="Organization not found or you are not a member"
        )
    return org


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_organization(
    org_id: str,
    data: UpdateOrgRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update organization settings. Admin only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService
    from organizations.models import OrganizationUpdate, OrganizationSettings

    service = OrganizationService()

    # Build update model
    settings = None
    if data.settings:
        settings = OrganizationSettings(**data.settings.model_dump())

    updates = OrganizationUpdate(
        name=data.name,
        description=data.description,
        settings=settings,
        status=data.status
    )

    try:
        org = await service.update_organization(org_id, current_user["user_id"], updates)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================================================
# MEMBERSHIP ENDPOINTS
# ===========================================================================

@router.get("/{org_id}/members", response_model=List[MemberResponse])
async def list_members(
    org_id: str,
    status: str = "active",
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """List organization members."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()

    try:
        return await service.get_org_members(org_id, current_user["user_id"], status)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=201)
async def invite_member(
    org_id: str,
    data: InviteMemberRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Invite a user to the organization by user_id.

    Requires invite permission.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService
    from organizations.models import MembershipCreate

    service = OrganizationService()

    invite_data = MembershipCreate(
        user_id=data.user_id,
        role=data.role
    )

    try:
        return await service.invite_member(org_id, current_user["user_id"], invite_data)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{org_id}/accept")
async def accept_invitation(
    org_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Accept a pending organization invitation."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()

    try:
        membership = await service.accept_invitation(current_user["user_id"], org_id)
        return {"status": "accepted", "membership": membership}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{org_id}/members/{user_id}/role", response_model=MemberResponse)
async def change_member_role(
    org_id: str,
    user_id: str,
    data: ChangeRoleRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Change a member's role. Admin only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()

    try:
        return await service.update_member_role(
            org_id, current_user["user_id"], user_id, data.role
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}/members/{user_id}", status_code=204)
async def remove_member(
    org_id: str,
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a member from the organization.

    Admin can remove anyone. Members can remove themselves.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.service import OrganizationService

    service = OrganizationService()

    try:
        await service.remove_member(org_id, current_user["user_id"], user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================================================
# INVITE TOKEN ENDPOINTS
# ===========================================================================

@router.post("/{org_id}/invites", response_model=InviteResponse, status_code=201)
async def create_invite_token(
    org_id: str,
    data: CreateInviteRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a shareable invite token.

    Tokens can grant member or viewer role (not admin).
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.invite import InviteService
    from organizations.models import InviteCreate

    service = InviteService()

    invite_data = InviteCreate(
        role=data.role,
        expires_in_days=data.expires_in_days,
        max_uses=data.max_uses
    )

    try:
        return service.generate_token(org_id, current_user["user_id"], invite_data)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{org_id}/invites", response_model=List[InviteResponse])
async def list_invite_tokens(
    org_id: str,
    include_expired: bool = False,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """List active invite tokens. Admin only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.invite import InviteService

    service = InviteService()

    try:
        return service.list_org_tokens(org_id, current_user["user_id"], include_expired)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{org_id}/invites/{token}", status_code=204)
async def revoke_invite_token(
    org_id: str,
    token: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Revoke an invite token. Admin only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.invite import InviteService

    service = InviteService()

    try:
        service.revoke_token(token, current_user["user_id"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===========================================================================
# TOKEN REDEMPTION (Public-ish endpoint)
# ===========================================================================

@router.get("/join/{token}")
async def preview_invite(token: str, request: Request):
    """
    Preview organization from invite token (no auth required).

    Returns basic org info for the join page.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.invite import InviteService

    service = InviteService()
    info = service.get_org_from_token(token)

    if not info:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    return info


@router.post("/join/{token}")
async def redeem_invite(
    token: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Redeem an invite token to join an organization.

    Creates a pending membership that must be accepted.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from organizations.invite import InviteService

    service = InviteService()

    try:
        result = service.redeem_token(token, current_user["user_id"])
        return {"status": "redeemed", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
