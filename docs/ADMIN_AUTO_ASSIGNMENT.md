# Admin Auto-Assignment Feature

**InDE Version:** 3.14.0 "Operational Readiness"
**Feature Added:** March 2026
**Related Feature:** Diagnostics Panel (admin-only)

---

## Overview

InDE v3.14 introduces automatic admin role assignment via environment variable configuration. This eliminates the need for manual MongoDB commands to designate administrators in self-hosted deployments.

---

## Configuration

### Environment Variable

```env
INDE_ADMIN_EMAIL=admin@yourcompany.com
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INDE_ADMIN_EMAIL` | No | (empty) | Email address for automatic admin role assignment. Leave empty to disable. |

### Location

The variable should be set in one of:
- `.env` (development)
- `deployment/.env` (production)
- Docker environment variables

---

## Behavior

### On Application Startup

When the InDE application starts:

1. Checks if `INDE_ADMIN_EMAIL` is configured (non-empty)
2. If a user with that email exists in the database:
   - Sets their `role` field to `"admin"`
   - Logs: `"Admin role assigned to {email}"`
3. If no matching user exists:
   - No action taken (user hasn't registered yet)
   - Admin role will be assigned when they register

### On User Registration

When a new user registers:

1. Checks if `INDE_ADMIN_EMAIL` is configured
2. Compares registration email (case-insensitive) to `INDE_ADMIN_EMAIL`
3. If match:
   - Sets `role: "admin"` in user document
   - Logs: `"Auto-assigning admin role to {email}"`
4. If no match:
   - Sets `role: "user"` (default)

---

## Implementation Details

### Files Modified

| File | Change |
|------|--------|
| `app/core/config.py` | Added `INDE_ADMIN_EMAIL` configuration variable |
| `app/main.py` | Added startup logic to assign admin role to existing users |
| `app/api/auth.py` | Added registration logic to auto-assign admin role |
| `.env` | Added `INDE_ADMIN_EMAIL` section with documentation |
| `.env.example` | Added `INDE_ADMIN_EMAIL` template with documentation |
| `deployment/.env.template` | Updated with admin email configuration |

### Code: Configuration (config.py)

```python
# =============================================================================
# ADMIN CONFIGURATION (v3.14 NEW)
# =============================================================================
# Email address for the admin user - automatically assigned admin role on startup
# and on registration. Leave empty to disable auto-assignment.
INDE_ADMIN_EMAIL = os.getenv("INDE_ADMIN_EMAIL", "")
```

### Code: Startup Assignment (main.py)

```python
# v3.14: Auto-assign admin role from INDE_ADMIN_EMAIL
if INDE_ADMIN_EMAIL:
    try:
        result = db.db.users.update_one(
            {"email": INDE_ADMIN_EMAIL.lower()},
            {"$set": {"role": "admin"}}
        )
        if result.modified_count > 0:
            logger.info(f"Admin role assigned to {INDE_ADMIN_EMAIL}")
        elif result.matched_count > 0:
            logger.debug(f"Admin role already set for {INDE_ADMIN_EMAIL}")
    except Exception as e:
        logger.warning(f"Admin role assignment skipped: {e}")
```

### Code: Registration Assignment (auth.py)

```python
# v3.14: Auto-assign admin role if email matches INDE_ADMIN_EMAIL
is_admin = (
    INDE_ADMIN_EMAIL and
    data.email.lower() == INDE_ADMIN_EMAIL.lower()
)
if is_admin:
    logger.info(f"Auto-assigning admin role to {data.email}")

user = {
    # ... other fields ...
    "role": "admin" if is_admin else "user",  # v3.14: Admin auto-assignment
}
```

---

## Admin Capabilities

Users with `role: "admin"` can access:

| Feature | Route | Description |
|---------|-------|-------------|
| Diagnostics Panel | `/diagnostics` | System health monitoring dashboard |
| Diagnostics API | `GET /api/system/diagnostics` | Full diagnostics data |
| Onboarding Stats | `GET /api/system/diagnostics/onboarding` | Onboarding funnel metrics |
| Error Log | `GET /api/system/diagnostics/errors` | Recent application errors |
| LLM Providers | `GET /api/system/llm/providers` | Provider chain status |

---

## User Schema Change

The `users` collection now includes a `role` field:

```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "admin" | "user",
  // ... other fields
}
```

| Role | Description |
|------|-------------|
| `"admin"` | Full access including diagnostics panel |
| `"user"` | Standard innovator access (default) |

---

## Deployment Scenarios

### Scenario 1: New Deployment

1. Set `INDE_ADMIN_EMAIL=admin@company.com` in `.env`
2. Start InDE
3. Admin registers with `admin@company.com`
4. Admin role is automatically assigned

### Scenario 2: Existing Deployment

1. User `admin@company.com` already exists with `role: "user"`
2. Set `INDE_ADMIN_EMAIL=admin@company.com` in `.env`
3. Restart InDE
4. Startup assigns `role: "admin"` to existing user

### Scenario 3: Change Admin

1. Change `INDE_ADMIN_EMAIL` to new email in `.env`
2. Restart InDE
3. New admin gets role assigned
4. **Note:** Previous admin retains admin role (not automatically revoked)

---

## Security Considerations

1. **Environment Variable Security**: `INDE_ADMIN_EMAIL` should be protected like other secrets
2. **Case Insensitive**: Email comparison is case-insensitive (`Admin@Co.com` matches `admin@co.com`)
3. **No Auto-Revoke**: Changing `INDE_ADMIN_EMAIL` does not revoke previous admin's role
4. **Single Admin**: Only one email can be auto-assigned; additional admins require manual DB update

---

## Manual Admin Assignment (Alternative)

For deployments not using `INDE_ADMIN_EMAIL`, admin role can still be assigned manually:

```javascript
// MongoDB shell
db.users.updateOne(
  { email: "admin@example.com" },
  { $set: { role: "admin" } }
)
```

```bash
# Via Docker
docker exec -it inde-db mongosh inde_db --eval \
  'db.users.updateOne({email:"admin@example.com"},{$set:{role:"admin"}})'
```

---

## Related Documentation

- `CHANGELOG.md` - v3.14.0 release notes
- `ONBOARDING_AUDIT.md` - Onboarding metrics documentation
- `deployment/DEPLOYMENT.md` - Production deployment guide

---

*Document created for InDE v3.14.0 "Operational Readiness"*
