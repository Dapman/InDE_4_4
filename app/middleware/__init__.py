"""
InDE MVP v3.8 - Middleware Module
Two-level authorization, license validation, and request processing.

RBAC Model:
- Level 1: Organization role (admin | member | viewer)
- Level 2: Pursuit role (owner | editor | viewer)

v3.8: License Validation:
- First-run detection for setup wizard
- License status checking and caching
- Read-only mode enforcement during grace period expiration

Authorization flows:
- Org-level actions: Check org membership + org role permissions
- Pursuit actions: Check pursuit team membership + pursuit role permissions
- Cross-pursuit actions: Check org membership for all involved pursuits
"""

from middleware.rbac import (
    RBACMiddleware,
    check_org_permission,
    check_pursuit_permission,
    require_org_admin,
    require_org_member,
    require_pursuit_access,
    require_pursuit_edit,
    get_user_org_context,
    get_user_pursuit_context,
)

# v3.8: License validation middleware
from middleware.license import (
    LicenseMiddleware,
    get_license_status,
    is_first_run,
    is_read_only_mode,
    require_write_access,
)

__all__ = [
    # RBAC
    "RBACMiddleware",
    "check_org_permission",
    "check_pursuit_permission",
    "require_org_admin",
    "require_org_member",
    "require_pursuit_access",
    "require_pursuit_edit",
    "get_user_org_context",
    "get_user_pursuit_context",
    # v3.8: License
    "LicenseMiddleware",
    "get_license_status",
    "is_first_run",
    "is_read_only_mode",
    "require_write_access",
]
