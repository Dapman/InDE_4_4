"""
Pursuit Archive Service
Moves pursuits in and out of the archived view.
Archiving is non-destructive — all data fully preserved.

v3.13: Innovator Experience Polish
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PursuitArchiveService:
    """
    Manages pursuit archiving and restoration.

    Archiving is a workspace organization feature:
    - Moves a pursuit out of the active view
    - All data is fully preserved
    - Easily reversible with restore

    This is different from the existing "abandon → archive" workflow,
    which involves retrospectives and permanent status change.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    def archive_pursuit(self, pursuit_id: str, user_id: str) -> dict:
        """
        Archive a pursuit. Removes it from the active workspace view.

        Authorization: user must own the pursuit.
        Idempotent: archiving an already-archived pursuit is a no-op.

        Args:
            pursuit_id: The pursuit to archive
            user_id: The user performing the action

        Returns:
            {"success": bool, "pursuit_id": str, "archived_at": str}

        Raises:
            HTTPException: 404 if pursuit not found, 403 if not authorized
        """
        pursuit = self._get_authorized_pursuit(pursuit_id, user_id)

        if pursuit.get("is_archived"):
            return {
                "success": True,
                "pursuit_id": pursuit_id,
                "archived_at": pursuit.get("archived_at"),
                "already_archived": True
            }

        archived_at = datetime.now(timezone.utc).isoformat()

        self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "is_archived": True,
                "archived_at": archived_at,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        logger.info(f"Pursuit {pursuit_id} archived by user {user_id}.")
        return {
            "success": True,
            "pursuit_id": pursuit_id,
            "archived_at": archived_at,
            "already_archived": False
        }

    def restore_pursuit(self, pursuit_id: str, user_id: str) -> dict:
        """
        Restore an archived pursuit to the active workspace.

        Authorization: user must own the pursuit.
        Idempotent: restoring an active pursuit is a no-op.

        Args:
            pursuit_id: The pursuit to restore
            user_id: The user performing the action

        Returns:
            {"success": bool, "pursuit_id": str}

        Raises:
            HTTPException: 404 if pursuit not found, 403 if not authorized
        """
        pursuit = self._get_authorized_pursuit(pursuit_id, user_id)

        if not pursuit.get("is_archived"):
            return {
                "success": True,
                "pursuit_id": pursuit_id,
                "already_active": True
            }

        self.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "is_archived": False,
                "archived_at": None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        logger.info(f"Pursuit {pursuit_id} restored by user {user_id}.")
        return {
            "success": True,
            "pursuit_id": pursuit_id,
            "already_active": False
        }

    def get_archived_pursuits(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Return paginated list of archived pursuits for a user.
        Ordered by archived_at descending (most recently archived first).

        Args:
            user_id: The user whose archived pursuits to fetch
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            {
                "total": int,
                "pursuits": list,
                "limit": int,
                "offset": int
            }
        """
        total = self.db.pursuits.count_documents({
            "user_id": user_id,
            "is_archived": True
        })

        pursuits = list(self.db.pursuits.find(
            {"user_id": user_id, "is_archived": True},
            # Return summary fields only — not full content
            {
                "pursuit_id": 1,
                "title": 1,
                "description": 1,
                "status": 1,
                "methodology_archetype": 1,
                "archived_at": 1,
                "created_at": 1,
                "updated_at": 1,
                "health_score": 1,
                "health_zone": 1,
                "_id": 0
            }
        ).sort("archived_at", -1).skip(offset).limit(limit))

        return {
            "total": total,
            "pursuits": pursuits,
            "limit": limit,
            "offset": offset
        }

    def _get_authorized_pursuit(self, pursuit_id: str, user_id: str) -> dict:
        """
        Fetch pursuit and verify ownership.

        Args:
            pursuit_id: The pursuit to fetch
            user_id: The user who should own it

        Returns:
            The pursuit document

        Raises:
            HTTPException: 404 if not found, 403 if not authorized
        """
        pursuit = self.db.pursuits.find_one({"pursuit_id": pursuit_id})

        if not pursuit:
            raise HTTPException(status_code=404, detail="Pursuit not found")

        if str(pursuit.get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to modify this pursuit"
            )

        return pursuit
