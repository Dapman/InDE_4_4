"""
Migration 007: v3.7.0 Display Labels & UI Remediation
InDE MVP v3.7.0 - IKF UI Remediation & Display Label Registry

This migration introduces no database schema changes.
It serves as a documentation marker and verification checkpoint.

Purpose:
- Verify Display Label Registry is importable
- Verify Response Transform Middleware is functional
- Document the version marker

All remediations are in code, not data. Existing contributions
in the database do not change; the transforms are applied at
read-time by the API layer.
"""

from datetime import datetime, timezone
import logging

MIGRATION_VERSION = "3.7.0"
MIGRATION_DATE = "2026-02-19"
MIGRATION_NAME = "Display Labels & UI Remediation"

logger = logging.getLogger("inde.migration.007")


def check_prerequisites() -> bool:
    """Verify v3.6.1 baseline is present."""
    try:
        from app.core.config import VERSION
        major_minor = ".".join(VERSION.split(".")[:2])
        # Allow 3.6.x or 3.7.x
        return major_minor in ("3.6", "3.7")
    except ImportError:
        return False


def run_migration(db) -> dict:
    """
    Execute the migration.

    For v3.7.0, this only verifies the new modules are importable
    and functional. No database changes are made.
    """
    results = {
        "version": MIGRATION_VERSION,
        "name": MIGRATION_NAME,
        "status": "pending",
        "checks": [],
        "errors": []
    }

    # Check 1: Display Labels importable
    try:
        from app.shared.display_labels import DisplayLabels
        label = DisplayLabels.get("contribution_status", "IKF_READY")
        if label != "IKF_READY":  # Should be translated
            results["checks"].append({
                "name": "Display Labels Registry",
                "status": "pass",
                "detail": f"Registry loads with {DisplayLabels.get_total_label_count()} labels"
            })
        else:
            results["checks"].append({
                "name": "Display Labels Registry",
                "status": "fail",
                "detail": "Labels not translated correctly"
            })
            results["errors"].append("DisplayLabels translation not working")
    except Exception as e:
        results["checks"].append({
            "name": "Display Labels Registry",
            "status": "fail",
            "detail": str(e)
        })
        results["errors"].append(f"DisplayLabels import failed: {e}")

    # Check 2: Response Transform importable
    try:
        from app.middleware.response_transform import ResponseTransformMiddleware
        test_data = {"contribution_id": "test-id", "status": "IKF_READY"}
        transformed = ResponseTransformMiddleware.transform(test_data)
        if "contribution_id" not in transformed:
            results["checks"].append({
                "name": "Response Transform Middleware",
                "status": "pass",
                "detail": "Transform strips internal IDs correctly"
            })
        else:
            results["checks"].append({
                "name": "Response Transform Middleware",
                "status": "fail",
                "detail": "Transform not stripping internal IDs"
            })
            results["errors"].append("ResponseTransformMiddleware not stripping IDs")
    except Exception as e:
        results["checks"].append({
            "name": "Response Transform Middleware",
            "status": "fail",
            "detail": str(e)
        })
        results["errors"].append(f"ResponseTransformMiddleware import failed: {e}")

    # Check 3: Verify API integration
    try:
        from app.api.ikf import ResponseTransformMiddleware as IKFTransform
        results["checks"].append({
            "name": "IKF API Integration",
            "status": "pass",
            "detail": "IKF API routes import transform middleware"
        })
    except Exception as e:
        results["checks"].append({
            "name": "IKF API Integration",
            "status": "fail",
            "detail": str(e)
        })
        results["errors"].append(f"IKF API integration failed: {e}")

    # Determine overall status
    if results["errors"]:
        results["status"] = "failed"
    else:
        results["status"] = "complete"
        # Record migration completion
        if db is not None:
            try:
                db.migrations.update_one(
                    {"version": MIGRATION_VERSION},
                    {"$set": {
                        "version": MIGRATION_VERSION,
                        "name": MIGRATION_NAME,
                        "completed_at": datetime.now(timezone.utc),
                        "status": "complete"
                    }},
                    upsert=True
                )
            except Exception:
                pass  # Migration tracking is optional

    logger.info(f"Migration {MIGRATION_VERSION} complete: {results['status']}")
    return results


def rollback(db) -> dict:
    """
    Rollback is not applicable for this migration.
    The changes are code-only, not data.
    """
    return {
        "version": MIGRATION_VERSION,
        "status": "not_applicable",
        "detail": "v3.7.0 changes are code-only; no data rollback needed"
    }


if __name__ == "__main__":
    # Run migration in standalone mode
    import sys
    sys.path.insert(0, "../..")

    if check_prerequisites():
        print(f"Running migration {MIGRATION_VERSION}: {MIGRATION_NAME}")
        result = run_migration(None)
        print(f"Status: {result['status']}")
        for check in result["checks"]:
            status_icon = "✓" if check["status"] == "pass" else "✗"
            print(f"  {status_icon} {check['name']}: {check['detail']}")
    else:
        print("Prerequisites not met. Ensure v3.6.1 baseline is installed.")
