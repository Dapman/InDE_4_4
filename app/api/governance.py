"""
InDE MVP v3.4 - Governance API Routes
Advanced RBAC, custom roles, and access policy management.

Endpoints:
- GET /orgs/{org_id}/roles - List all roles (built-in + custom)
- POST /orgs/{org_id}/roles - Create custom role
- PUT /orgs/{org_id}/roles/{role_name} - Update custom role
- DELETE /orgs/{org_id}/roles/{role_name} - Delete custom role
- GET /orgs/{org_id}/access-policy - Get access policy
- PUT /orgs/{org_id}/access-policy - Update access policy
- GET /orgs/{org_id}/permissions - Get available permissions

All governance endpoints require admin role.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from core.database import db
from middleware.rbac import (
    require_permission, get_org_roles, create_custom_role,
    update_custom_role, check_user_has_permission
)
from core.config import DEFINED_PERMISSIONS, BUILTIN_ROLE_PERMISSIONS

logger = logging.getLogger("inde.api.governance")

router = APIRouter(prefix="/orgs/{org_id}", tags=["governance"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateRoleRequest(BaseModel):
    """Request to create a custom role."""
    name: str = Field(..., min_length=2, max_length=50,
                      description="Role name (must be unique within org)")
    description: str = Field(..., max_length=500,
                             description="Role description")
    permissions: List[str] = Field(..., min_items=0,
                                   description="List of permissions from DEFINED_PERMISSIONS")


class UpdateRoleRequest(BaseModel):
    """Request to update a custom role."""
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = Field(None)


class AccessPolicyUpdate(BaseModel):
    """Request to update access policy."""
    portfolio_dashboard_access: Optional[List[str]] = Field(
        None,
        description="Roles that can access portfolio dashboard"
    )
    discovery_permissions: Optional[Dict[str, Any]] = Field(
        None,
        description="Discovery permission settings"
    )
    audit_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Audit configuration"
    )
    methodology_preferences: Optional[List[str]] = Field(
        None,
        description="Enabled methodology archetypes"
    )
    data_retention: Optional[Dict[str, Any]] = Field(
        None,
        description="Data retention settings"
    )


class RoleResponse(BaseModel):
    """Role details response."""
    name: str
    description: str
    permissions: List[str]
    is_system: bool
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class PermissionInfo(BaseModel):
    """Permission information."""
    name: str
    description: str
    category: str


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(org_id: str, current_user: Dict = Depends(get_current_user)) -> Dict:
    """Verify user has admin permission for the organization."""
    user_id = current_user.get("user_id")
    if not check_user_has_permission(user_id, org_id, "can_manage_roles"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    return current_user


# =============================================================================
# ROLES ENDPOINTS
# =============================================================================

@router.get("/roles", response_model=List[RoleResponse])
async def list_org_roles(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all roles for an organization.

    Returns both built-in roles (admin, member, viewer) and custom roles.
    Requires org membership.
    """
    # Verify membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    roles = get_org_roles(org_id)
    return [RoleResponse(
        name=r["name"],
        description=r.get("description", ""),
        permissions=r.get("permissions", []),
        is_system=r.get("is_system", False),
        created_by=r.get("created_by"),
        created_at=r.get("created_at")
    ) for r in roles]


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_org_role(
    org_id: str,
    request: CreateRoleRequest,
    current_user: Dict = Depends(require_admin)
):
    """
    Create a custom role for the organization.

    Role name must be unique within the organization.
    Requires can_manage_roles permission.
    """
    try:
        role = create_custom_role(
            org_id=org_id,
            name=request.name,
            description=request.description,
            permissions=request.permissions,
            created_by=current_user["user_id"]
        )
        logger.info(f"Custom role created: {request.name} in org {org_id}")
        return RoleResponse(
            name=role["name"],
            description=role["description"],
            permissions=role["permissions"],
            is_system=role["is_system"],
            created_by=role["created_by"],
            created_at=role["created_at"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/roles/{role_name}", response_model=RoleResponse)
async def update_org_role(
    org_id: str,
    role_name: str,
    request: UpdateRoleRequest,
    current_user: Dict = Depends(require_admin)
):
    """
    Update a custom role's permissions or description.

    System roles (admin, member, viewer) cannot be modified.
    Requires can_manage_roles permission.
    """
    try:
        role = update_custom_role(
            org_id=org_id,
            role_name=role_name,
            permissions=request.permissions,
            description=request.description
        )
        if not role:
            raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

        logger.info(f"Custom role updated: {role_name} in org {org_id}")
        return RoleResponse(
            name=role["name"],
            description=role["description"],
            permissions=role["permissions"],
            is_system=role["is_system"],
            created_by=role.get("created_by"),
            created_at=role.get("created_at")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_name}", status_code=204)
async def delete_org_role(
    org_id: str,
    role_name: str,
    current_user: Dict = Depends(require_admin)
):
    """
    Delete a custom role.

    System roles cannot be deleted.
    Requires can_manage_roles permission.
    """
    # Check if system role
    if role_name in BUILTIN_ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")

    # Check if role exists
    role = db.get_custom_role(org_id, role_name)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

    # Delete role
    success = db.delete_custom_role(org_id, role_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete role")

    logger.info(f"Custom role deleted: {role_name} from org {org_id}")


# =============================================================================
# ACCESS POLICY ENDPOINTS
# =============================================================================

@router.get("/access-policy")
async def get_access_policy(
    org_id: str,
    current_user: Dict = Depends(require_admin)
):
    """
    Get the access policy for the organization.

    Requires admin permission.
    """
    policy = db.get_access_policy(org_id)
    if not policy:
        # Return default policy structure
        return {
            "org_id": org_id,
            "portfolio_dashboard_access": ["admin"],
            "discovery_permissions": {
                "who_can_discover": ["admin", "member"],
                "availability_default": "SELECTIVE"
            },
            "audit_config": {
                "retention_days": 365,
                "export_allowed_roles": ["admin"]
            },
            "methodology_preferences": ["lean_startup", "design_thinking", "stage_gate"],
            "data_retention": {
                "pursuit_retention_days": None,
                "coaching_session_retention_days": None,
                "activity_event_retention_days": 365
            }
        }
    return policy


@router.put("/access-policy")
async def update_access_policy(
    org_id: str,
    request: AccessPolicyUpdate,
    current_user: Dict = Depends(require_admin)
):
    """
    Update the access policy for the organization.

    Only provided fields are updated; others remain unchanged.
    Requires can_manage_org_settings permission.
    """
    # Check additional permission for policy changes
    if not check_user_has_permission(current_user["user_id"], org_id, "can_manage_org_settings"):
        raise HTTPException(status_code=403, detail="Settings management permission required")

    # Build update dict from non-None fields
    updates = {}
    if request.portfolio_dashboard_access is not None:
        updates["portfolio_dashboard_access"] = request.portfolio_dashboard_access
    if request.discovery_permissions is not None:
        updates["discovery_permissions"] = request.discovery_permissions
    if request.audit_config is not None:
        updates["audit_config"] = request.audit_config
    if request.methodology_preferences is not None:
        updates["methodology_preferences"] = request.methodology_preferences
    if request.data_retention is not None:
        updates["data_retention"] = request.data_retention

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Check if policy exists
    existing = db.get_access_policy(org_id)
    if existing:
        success = db.update_access_policy(org_id, updates)
    else:
        # Create new policy with defaults
        db.create_access_policy(org_id, updates)
        success = True

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update access policy")

    logger.info(f"Access policy updated for org {org_id}")
    return db.get_access_policy(org_id)


# =============================================================================
# PERMISSIONS ENDPOINTS
# =============================================================================

@router.get("/permissions", response_model=List[PermissionInfo])
async def get_available_permissions(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get list of all available permissions for custom role creation.

    Returns permission names with descriptions and categories.
    """
    # Permission descriptions and categories
    permission_details = {
        "can_create_pursuits": {
            "description": "Create new innovation pursuits",
            "category": "pursuits"
        },
        "can_invite_members": {
            "description": "Invite users to the organization",
            "category": "membership"
        },
        "can_manage_org_settings": {
            "description": "Modify organization settings and policies",
            "category": "admin"
        },
        "can_review_ikf_contributions": {
            "description": "Review and approve IKF contributions",
            "category": "knowledge"
        },
        "can_view_portfolio_dashboard": {
            "description": "Access organization portfolio dashboard",
            "category": "analytics"
        },
        "can_manage_audit_logs": {
            "description": "View and export audit logs",
            "category": "admin"
        },
        "can_manage_roles": {
            "description": "Create and modify custom roles",
            "category": "admin"
        },
        "can_manage_retention_policies": {
            "description": "Configure data retention settings",
            "category": "admin"
        },
        "can_discover_members": {
            "description": "Use IDTFS to discover organization members",
            "category": "discovery"
        },
    }

    return [
        PermissionInfo(
            name=perm,
            description=permission_details.get(perm, {}).get("description", ""),
            category=permission_details.get(perm, {}).get("category", "general")
        )
        for perm in DEFINED_PERMISSIONS
    ]


# =============================================================================
# USER ROLE ASSIGNMENT (for completeness)
# =============================================================================

class AssignRoleRequest(BaseModel):
    """Request to assign a role to a user."""
    user_id: str
    role: str


@router.post("/members/{user_id}/role")
async def assign_member_role(
    org_id: str,
    user_id: str,
    request: AssignRoleRequest,
    current_user: Dict = Depends(require_admin)
):
    """
    Assign a role to an organization member.

    Role can be a built-in role or a custom role defined for this org.
    Requires admin permission.
    """
    # Verify the role exists
    if request.role not in BUILTIN_ROLE_PERMISSIONS:
        custom_role = db.get_custom_role(org_id, request.role)
        if not custom_role:
            raise HTTPException(status_code=400, detail=f"Role '{request.role}' not found")

    # Update membership
    membership = db.get_user_membership_in_org(user_id, org_id)
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this organization")

    # Update the role
    success = db.update_membership_role(user_id, org_id, request.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update role")

    logger.info(f"Role '{request.role}' assigned to user {user_id} in org {org_id}")
    return {"message": f"Role '{request.role}' assigned successfully"}
