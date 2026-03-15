"""
InDE MVP v3.4 - RBAC Middleware
Advanced role-based access control with custom roles and policy-based governance.

v3.4 Enhancements:
- Custom Role System: Organizations can define custom roles from DEFINED_PERMISSIONS
- Policy-Based Access Control: Organization-wide access_policies configuration
- Permission-based decorators: Check specific permissions instead of role names
- Role caching: Per-session caching with < 15ms overhead target

Authorization Model:
1. Organization Level (org role: admin | member | viewer | custom)
   - Built-in roles: admin, member, viewer (immutable)
   - Custom roles: Composed from DEFINED_PERMISSIONS
   - Policy overrides: access_policies can restrict/extend defaults

2. Pursuit Level (pursuit role: owner | editor | viewer)
   - owner: Full pursuit control, manage team, delete, generate reports
   - editor: Chat with coach, contribute elements, generate reports
   - viewer: View pursuit data and reports only

Access Evaluation Order:
1. User must be authenticated (have valid session/JWT)
2. For org actions: Check user's org membership status and role
3. Resolve role permissions (built-in OR custom from custom_roles collection)
4. Check access_policies for org-level policy overrides
5. For pursuit actions: Check pursuit ownership OR team membership + role
6. Personal pursuits: Creator is always owner, org role doesn't override
"""

from functools import wraps
from typing import Optional, Dict, List, Callable, Any
import logging
import time

from core.database import db
from core.config import (
    ORG_ROLES, PURSUIT_ROLES, PURSUIT_ROLE_PERMISSIONS,
    DEFINED_PERMISSIONS, BUILTIN_ROLE_PERMISSIONS
)

logger = logging.getLogger("inde.middleware.rbac")

# v3.4: Role permission cache (per-session, cleared on role change)
_role_permission_cache: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minute cache


# =============================================================================
# AUTHORIZATION CONTEXT
# =============================================================================

class AuthorizationContext:
    """
    User authorization context for a request.

    Contains user identity, org memberships, and pursuit access.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._org_memberships: Dict[str, Dict] = {}
        self._pursuit_roles: Dict[str, str] = {}
        self._loaded_orgs: set = set()
        self._loaded_pursuits: set = set()

    def load_org_membership(self, org_id: str) -> Optional[Dict]:
        """Load and cache user's membership in an organization."""
        if org_id in self._loaded_orgs:
            return self._org_memberships.get(org_id)

        membership = db.get_user_membership_in_org(self.user_id, org_id)
        self._loaded_orgs.add(org_id)

        if membership and membership.get("status") == "active":
            self._org_memberships[org_id] = membership
            return membership
        return None

    def get_org_role(self, org_id: str) -> Optional[str]:
        """Get user's role in an organization."""
        membership = self.load_org_membership(org_id)
        return membership.get("role") if membership else None

    def get_org_permissions(self, org_id: str) -> Dict:
        """Get user's permissions in an organization."""
        membership = self.load_org_membership(org_id)
        return membership.get("permissions", {}) if membership else {}

    def load_pursuit_role(self, pursuit_id: str) -> Optional[str]:
        """Load and cache user's role in a pursuit."""
        if pursuit_id in self._loaded_pursuits:
            return self._pursuit_roles.get(pursuit_id)

        pursuit = db.get_pursuit(pursuit_id)
        self._loaded_pursuits.add(pursuit_id)

        if not pursuit:
            return None

        # Check if user is the pursuit creator (always owner)
        if pursuit.get("user_id") == self.user_id:
            self._pursuit_roles[pursuit_id] = "owner"
            return "owner"

        # Check team membership in sharing.team_members
        sharing = pursuit.get("sharing", {})
        team_members = sharing.get("team_members", [])

        for member in team_members:
            if member.get("user_id") == self.user_id:
                role = member.get("role", "viewer")
                self._pursuit_roles[pursuit_id] = role
                return role

        # No explicit role found
        return None

    def get_pursuit_role(self, pursuit_id: str) -> Optional[str]:
        """Get user's role in a pursuit."""
        return self.load_pursuit_role(pursuit_id)

    def can_access_pursuit(self, pursuit_id: str) -> bool:
        """Check if user can access a pursuit (any role)."""
        return self.get_pursuit_role(pursuit_id) is not None

    def can_edit_pursuit(self, pursuit_id: str) -> bool:
        """Check if user can edit a pursuit (owner or editor)."""
        role = self.get_pursuit_role(pursuit_id)
        return role in ["owner", "editor"]

    def is_pursuit_owner(self, pursuit_id: str) -> bool:
        """Check if user is the pursuit owner."""
        return self.get_pursuit_role(pursuit_id) == "owner"


def get_user_org_context(user_id: str, org_id: str) -> Optional[Dict]:
    """
    Get user's organization context.

    Returns:
        Dict with org info, user's role, and permissions, or None
    """
    membership = db.get_user_membership_in_org(user_id, org_id)
    if not membership or membership.get("status") != "active":
        return None

    org = db.get_organization(org_id)
    if not org:
        return None

    return {
        "org_id": org_id,
        "org_name": org.get("name"),
        "org_status": org.get("status"),
        "user_role": membership.get("role"),
        "permissions": membership.get("permissions", {}),
        "settings": org.get("settings", {})
    }


def get_user_pursuit_context(user_id: str, pursuit_id: str) -> Optional[Dict]:
    """
    Get user's pursuit context.

    Returns:
        Dict with pursuit info, user's role, and permissions, or None
    """
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        return None

    # Determine role
    role = None
    if pursuit.get("user_id") == user_id:
        role = "owner"
    else:
        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            if member.get("user_id") == user_id:
                role = member.get("role", "viewer")
                break

    if not role:
        return None

    # Get permissions from config
    permissions = PURSUIT_ROLE_PERMISSIONS.get(role, {})

    return {
        "pursuit_id": pursuit_id,
        "pursuit_title": pursuit.get("title"),
        "pursuit_status": pursuit.get("status"),
        "user_role": role,
        "permissions": permissions,
        "is_shared": pursuit.get("sharing", {}).get("is_shared", False),
        "org_id": pursuit.get("org_id")
    }


# =============================================================================
# PERMISSION CHECKERS
# =============================================================================

def check_org_permission(user_id: str, org_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission in an organization.

    Args:
        user_id: User ID
        org_id: Organization ID
        permission: Permission name (e.g., "can_invite_members")

    Returns:
        True if user has permission
    """
    membership = db.get_user_membership_in_org(user_id, org_id)
    if not membership or membership.get("status") != "active":
        return False

    permissions = membership.get("permissions", {})
    return permissions.get(permission, False)


def check_pursuit_permission(user_id: str, pursuit_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission for a pursuit.

    Args:
        user_id: User ID
        pursuit_id: Pursuit ID
        permission: Permission name (e.g., "contribute_elements")

    Returns:
        True if user has permission
    """
    context = get_user_pursuit_context(user_id, pursuit_id)
    if not context:
        return False

    return context.get("permissions", {}).get(permission, False)


# =============================================================================
# DECORATORS FOR ROUTE PROTECTION
# =============================================================================

def require_org_admin(org_id_param: str = "org_id"):
    """
    Decorator requiring org admin role.

    Usage:
        @app.post("/orgs/{org_id}/settings")
        @require_org_admin()
        async def update_org_settings(org_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user_id from current_user or kwargs
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            # Get org_id from kwargs
            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(f"Missing {org_id_param} parameter")

            # Check admin role
            membership = db.get_user_membership_in_org(user_id, org_id)
            if not membership or membership.get("status") != "active":
                raise PermissionError("Not a member of this organization")

            if membership.get("role") != "admin":
                raise PermissionError("Admin role required")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_org_member(org_id_param: str = "org_id"):
    """
    Decorator requiring org membership (any active role).

    Usage:
        @app.get("/orgs/{org_id}/pursuits")
        @require_org_member()
        async def list_org_pursuits(org_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(f"Missing {org_id_param} parameter")

            membership = db.get_user_membership_in_org(user_id, org_id)
            if not membership or membership.get("status") != "active":
                raise PermissionError("Not a member of this organization")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_pursuit_access(pursuit_id_param: str = "pursuit_id"):
    """
    Decorator requiring pursuit access (any role: owner/editor/viewer).

    Usage:
        @app.get("/pursuits/{pursuit_id}")
        @require_pursuit_access()
        async def get_pursuit(pursuit_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            pursuit_id = kwargs.get(pursuit_id_param)
            if not pursuit_id:
                raise ValueError(f"Missing {pursuit_id_param} parameter")

            context = get_user_pursuit_context(user_id, pursuit_id)
            if not context:
                raise PermissionError("No access to this pursuit")

            # Attach context to kwargs for use in handler
            kwargs["pursuit_context"] = context

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_pursuit_edit(pursuit_id_param: str = "pursuit_id"):
    """
    Decorator requiring pursuit edit access (owner or editor).

    Usage:
        @app.post("/pursuits/{pursuit_id}/elements")
        @require_pursuit_edit()
        async def add_element(pursuit_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            pursuit_id = kwargs.get(pursuit_id_param)
            if not pursuit_id:
                raise ValueError(f"Missing {pursuit_id_param} parameter")

            context = get_user_pursuit_context(user_id, pursuit_id)
            if not context:
                raise PermissionError("No access to this pursuit")

            if context.get("user_role") not in ["owner", "editor"]:
                raise PermissionError("Edit access required (owner or editor)")

            kwargs["pursuit_context"] = context

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_pursuit_owner(pursuit_id_param: str = "pursuit_id"):
    """
    Decorator requiring pursuit ownership.

    Usage:
        @app.delete("/pursuits/{pursuit_id}")
        @require_pursuit_owner()
        async def delete_pursuit(pursuit_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            pursuit_id = kwargs.get(pursuit_id_param)
            if not pursuit_id:
                raise ValueError(f"Missing {pursuit_id_param} parameter")

            context = get_user_pursuit_context(user_id, pursuit_id)
            if not context:
                raise PermissionError("No access to this pursuit")

            if context.get("user_role") != "owner":
                raise PermissionError("Owner access required")

            kwargs["pursuit_context"] = context

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# MIDDLEWARE CLASS (for FastAPI)
# =============================================================================

class RBACMiddleware:
    """
    RBAC middleware for FastAPI.

    Adds authorization context to request state for route handlers.
    Works in conjunction with existing auth middleware.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get user from existing auth (should be set by auth middleware)
        user_id = scope.get("state", {}).get("user_id")

        if user_id:
            # Create authorization context
            auth_context = AuthorizationContext(user_id)
            scope.setdefault("state", {})
            scope["state"]["auth_context"] = auth_context

        await self.app(scope, receive, send)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_accessible_pursuits(user_id: str, org_id: str = None) -> List[Dict]:
    """
    Get all pursuits accessible to a user.

    Args:
        user_id: User ID
        org_id: Optional org filter

    Returns:
        List of pursuits with user's role in each
    """
    results = []

    # Get user's own pursuits
    own_pursuits = db.get_user_pursuits(user_id)
    for p in own_pursuits:
        p["user_role"] = "owner"
        if org_id and p.get("org_id") != org_id:
            continue
        results.append(p)

    # Get shared pursuits
    shared = db.get_user_shared_pursuits(user_id)
    for p in shared:
        if p.get("user_id") == user_id:
            continue  # Already counted as owner
        # Find user's role in team_members
        for member in p.get("sharing", {}).get("team_members", []):
            if member.get("user_id") == user_id:
                p["user_role"] = member.get("role", "viewer")
                break
        if org_id and p.get("org_id") != org_id:
            continue
        results.append(p)

    return results


def can_user_access_org_pursuit(user_id: str, pursuit_id: str) -> bool:
    """
    Check if user can access a pursuit through org membership.

    For org-visible pursuits, org members may have implicit view access
    based on org settings.
    """
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        return False

    # Check explicit access first
    if get_user_pursuit_context(user_id, pursuit_id):
        return True

    # Check org-level visibility
    org_id = pursuit.get("org_id")
    if not org_id:
        return False

    membership = db.get_user_membership_in_org(user_id, org_id)
    if not membership or membership.get("status") != "active":
        return False

    # Check org visibility settings
    org = db.get_organization(org_id)
    if not org:
        return False

    visibility = org.get("settings", {}).get("default_pursuit_visibility", "team_only")

    # org_private = visible to all org members
    # team_only = only visible to team members (default in pursuit.sharing)
    if visibility == "org_private":
        return True

    return False


# =============================================================================
# v3.4: CUSTOM ROLE RESOLUTION
# =============================================================================

def get_role_permissions(org_id: str, role_name: str) -> List[str]:
    """
    Resolve permissions for a role (built-in or custom).

    Args:
        org_id: Organization ID
        role_name: Role name (admin, member, viewer, or custom)

    Returns:
        List of permission strings
    """
    # Check cache first
    cache_key = f"{org_id}:{role_name}"
    cached = _role_permission_cache.get(cache_key)
    if cached and time.time() - cached.get("timestamp", 0) < _CACHE_TTL_SECONDS:
        return cached.get("permissions", [])

    # Built-in roles
    if role_name in BUILTIN_ROLE_PERMISSIONS:
        permissions = BUILTIN_ROLE_PERMISSIONS[role_name]
    else:
        # Custom role - lookup from custom_roles collection
        custom_role = db.get_custom_role(org_id, role_name)
        if custom_role:
            permissions = custom_role.get("permissions", [])
        else:
            permissions = []

    # Cache the result
    _role_permission_cache[cache_key] = {
        "permissions": permissions,
        "timestamp": time.time()
    }

    return permissions


def invalidate_role_cache(org_id: str, role_name: str = None):
    """
    Invalidate cached role permissions.

    Args:
        org_id: Organization ID
        role_name: Specific role to invalidate, or None for all org roles
    """
    if role_name:
        cache_key = f"{org_id}:{role_name}"
        _role_permission_cache.pop(cache_key, None)
    else:
        # Invalidate all roles for this org
        keys_to_remove = [k for k in _role_permission_cache if k.startswith(f"{org_id}:")]
        for key in keys_to_remove:
            _role_permission_cache.pop(key, None)


def check_user_has_permission(user_id: str, org_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission in an organization.

    v3.4: Resolves permissions from custom roles and checks policy overrides.

    Args:
        user_id: User ID
        org_id: Organization ID
        permission: Permission name from DEFINED_PERMISSIONS

    Returns:
        True if user has the permission
    """
    # Get user's membership
    membership = db.get_user_membership_in_org(user_id, org_id)
    if not membership or membership.get("status") != "active":
        return False

    role = membership.get("role", "viewer")

    # Resolve role permissions
    permissions = get_role_permissions(org_id, role)

    # Check if permission is granted by role
    if permission not in permissions:
        return False

    # Check policy overrides (access_policies can restrict certain permissions)
    policy = get_access_policy(org_id)
    if policy:
        # Some permissions have policy-level restrictions
        if permission == "can_view_portfolio_dashboard":
            allowed_roles = policy.get("portfolio_dashboard_access", ["admin"])
            if role not in allowed_roles:
                return False

        if permission == "can_discover_members":
            who_can_discover = policy.get("discovery_permissions", {}).get("who_can_discover", ["admin", "member"])
            if role not in who_can_discover:
                return False

    return True


def get_access_policy(org_id: str) -> Optional[Dict]:
    """
    Get access policy for an organization.

    Args:
        org_id: Organization ID

    Returns:
        Access policy dict or None
    """
    return db.get_access_policy(org_id)


# =============================================================================
# v3.4: PERMISSION-BASED DECORATORS
# =============================================================================

def require_permission(permission: str, org_id_param: str = "org_id"):
    """
    Decorator requiring a specific permission in an organization.

    v3.4: Uses custom role resolution and policy evaluation.

    Usage:
        @app.get("/orgs/{org_id}/portfolio")
        @require_permission("can_view_portfolio_dashboard")
        async def get_portfolio(org_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(f"Missing {org_id_param} parameter")

            # Check permission
            if not check_user_has_permission(user_id, org_id, permission):
                raise PermissionError(f"Permission denied: {permission}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[str], org_id_param: str = "org_id"):
    """
    Decorator requiring any one of the specified permissions.

    Usage:
        @app.get("/orgs/{org_id}/audit")
        @require_any_permission(["can_manage_audit_logs", "can_manage_org_settings"])
        async def get_audit(org_id: str, current_user: User):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("current_user", {}).get("user_id")
            if not user_id:
                raise PermissionError("Authentication required")

            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(f"Missing {org_id_param} parameter")

            # Check any permission
            has_any = any(
                check_user_has_permission(user_id, org_id, perm)
                for perm in permissions
            )

            if not has_any:
                raise PermissionError(f"Permission denied: requires one of {permissions}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# v3.4: CUSTOM ROLE MANAGEMENT
# =============================================================================

def create_custom_role(org_id: str, name: str, description: str,
                       permissions: List[str], created_by: str) -> Dict:
    """
    Create a custom role for an organization.

    Args:
        org_id: Organization ID
        name: Role name (must be unique within org)
        description: Role description
        permissions: List of permissions from DEFINED_PERMISSIONS
        created_by: User ID of creator

    Returns:
        Created role document

    Raises:
        ValueError: If role name is reserved or permissions invalid
    """
    # Validate role name
    if name in BUILTIN_ROLE_PERMISSIONS:
        raise ValueError(f"Cannot use reserved role name: {name}")

    # Validate permissions
    invalid_perms = [p for p in permissions if p not in DEFINED_PERMISSIONS]
    if invalid_perms:
        raise ValueError(f"Invalid permissions: {invalid_perms}")

    # Check for duplicate
    existing = db.get_custom_role(org_id, name)
    if existing:
        raise ValueError(f"Role '{name}' already exists in this organization")

    # Create role
    role = db.create_custom_role(
        org_id=org_id,
        name=name,
        description=description,
        permissions=permissions,
        created_by=created_by,
        is_system=False
    )

    # Invalidate cache
    invalidate_role_cache(org_id, name)

    return role


def update_custom_role(org_id: str, role_name: str,
                       permissions: List[str] = None,
                       description: str = None) -> Dict:
    """
    Update a custom role's permissions or description.

    Args:
        org_id: Organization ID
        role_name: Role name
        permissions: New permissions list (optional)
        description: New description (optional)

    Returns:
        Updated role document

    Raises:
        ValueError: If trying to update system role or invalid permissions
    """
    role = db.get_custom_role(org_id, role_name)
    if not role:
        raise ValueError(f"Role '{role_name}' not found")

    if role.get("is_system"):
        raise ValueError("Cannot modify system roles")

    if permissions is not None:
        invalid_perms = [p for p in permissions if p not in DEFINED_PERMISSIONS]
        if invalid_perms:
            raise ValueError(f"Invalid permissions: {invalid_perms}")

    # Update role
    updated = db.update_custom_role(org_id, role_name, permissions, description)

    # Invalidate cache
    invalidate_role_cache(org_id, role_name)

    return updated


def get_org_roles(org_id: str) -> List[Dict]:
    """
    Get all roles for an organization (built-in + custom).

    Args:
        org_id: Organization ID

    Returns:
        List of role documents
    """
    roles = []

    # Add built-in roles
    for role_name, perms in BUILTIN_ROLE_PERMISSIONS.items():
        roles.append({
            "name": role_name,
            "description": f"Built-in {role_name} role",
            "permissions": perms,
            "is_system": True
        })

    # Add custom roles
    custom_roles = db.get_org_custom_roles(org_id)
    roles.extend(custom_roles)

    return roles
