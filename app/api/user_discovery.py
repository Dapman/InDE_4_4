"""
InDE MVP v3.15 - User Discovery State API
Guided Discovery Layer for first-time users.

Endpoints:
- GET /api/v1/user/discovery - Get discovery state for current user
- POST /api/v1/user/discovery/dismiss - Dismiss a hint
- POST /api/v1/user/discovery/reset - Reset all dismissed hints
- POST /api/v1/user/discovery/checklist/{item_key}/complete - Mark checklist item complete
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from core.database import db
from auth.middleware import get_current_user

logger = logging.getLogger("inde.api.user_discovery")

router = APIRouter(prefix="/api/v1/user/discovery", tags=["user-discovery"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DiscoveryStateResponse(BaseModel):
    """Discovery state for guided first-time user experience."""
    checklist_complete: bool = False
    dismissed_hints: List[str] = []
    checklist_items: Dict[str, bool] = {}


class DismissHintRequest(BaseModel):
    """Request to dismiss a hint."""
    hint_id: str


class ChecklistUpdateResponse(BaseModel):
    """Response after updating checklist item."""
    item_key: str
    completed: bool
    checklist_complete: bool


# =============================================================================
# DEFAULT DISCOVERY STATE
# =============================================================================

DEFAULT_CHECKLIST_ITEMS = {
    "vision_created": False,
    "fear_identified": False,
    "methodology_selected": False,
    "coaching_conversation_started": False,
    "first_artifact_generated": False,
}


def get_default_discovery_state() -> Dict[str, Any]:
    """Return default discovery state for new users."""
    return {
        "checklist_complete": False,
        "dismissed_hints": [],
        "checklist_items": DEFAULT_CHECKLIST_ITEMS.copy(),
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_discovery_state(user_doc: Dict) -> Dict:
    """Ensure user document has discovery state, returning defaults if missing."""
    discovery = user_doc.get("discovery")
    if not discovery:
        return get_default_discovery_state()

    # Ensure all checklist items exist (forward compatibility)
    checklist = discovery.get("checklist_items", {})
    for key in DEFAULT_CHECKLIST_ITEMS:
        if key not in checklist:
            checklist[key] = False
    discovery["checklist_items"] = checklist

    return {
        "checklist_complete": discovery.get("checklist_complete", False),
        "dismissed_hints": discovery.get("dismissed_hints", []),
        "checklist_items": checklist,
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=DiscoveryStateResponse)
async def get_discovery_state(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Returns the user's discovery state for the active pursuit.

    The discovery state tracks:
    - Checklist completion (Getting Started items)
    - Dismissed hints (per-zone hint cards)
    - Overall completion status
    """
    user_id = user.get("user_id")

    # Get user document to read discovery state
    user_doc = db.db.users.find_one({"user_id": user_id})
    if not user_doc:
        # User not found, return defaults
        return DiscoveryStateResponse(**get_default_discovery_state())

    state = ensure_discovery_state(user_doc)
    return DiscoveryStateResponse(**state)


@router.post("/dismiss")
async def dismiss_hint(
    request: Request,
    body: DismissHintRequest,
    user: dict = Depends(get_current_user)
):
    """
    Marks a hint as dismissed. Persisted in user document.

    Dismissed hints never reappear for this user unless they reset.
    """
    user_id = user.get("user_id")

    # Add hint_id to dismissed_hints array (avoid duplicates)
    result = db.db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"discovery.dismissed_hints": body.hint_id}}
    )

    if result.matched_count == 0:
        # User document doesn't exist yet, create discovery state
        db.db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "discovery": {
                        "checklist_complete": False,
                        "dismissed_hints": [body.hint_id],
                        "checklist_items": DEFAULT_CHECKLIST_ITEMS.copy(),
                    }
                }
            },
            upsert=True
        )

    logger.info(f"User {user_id} dismissed hint: {body.hint_id}")

    return {"status": "dismissed", "hint_id": body.hint_id}


@router.post("/reset")
async def reset_discovery(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Resets all dismissed hints (available from user preferences).

    Does not reset checklist completion status.
    """
    user_id = user.get("user_id")

    result = db.db.users.update_one(
        {"user_id": user_id},
        {"$set": {"discovery.dismissed_hints": []}}
    )

    logger.info(f"User {user_id} reset dismissed hints")

    return {"status": "reset", "dismissed_hints": []}


@router.post("/checklist/{item_key}/complete", response_model=ChecklistUpdateResponse)
async def mark_checklist_item(
    request: Request,
    item_key: str,
    user: dict = Depends(get_current_user)
):
    """
    Marks a Getting Started checklist item complete.

    Also checks if all items are now complete and updates checklist_complete flag.
    """
    user_id = user.get("user_id")

    # Validate item_key
    valid_keys = list(DEFAULT_CHECKLIST_ITEMS.keys())
    if item_key not in valid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid checklist item. Must be one of: {valid_keys}"
        )

    # Update the specific checklist item
    db.db.users.update_one(
        {"user_id": user_id},
        {"$set": {f"discovery.checklist_items.{item_key}": True}},
        upsert=True
    )

    # Check if all items are now complete
    user_doc = db.db.users.find_one({"user_id": user_id})
    checklist_items = user_doc.get("discovery", {}).get("checklist_items", {})

    # Merge with defaults to ensure all keys exist
    for key in DEFAULT_CHECKLIST_ITEMS:
        if key not in checklist_items:
            checklist_items[key] = False

    all_complete = all(checklist_items.values())

    if all_complete:
        db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"discovery.checklist_complete": True}}
        )
        logger.info(f"User {user_id} completed all Getting Started items")

    return ChecklistUpdateResponse(
        item_key=item_key,
        completed=True,
        checklist_complete=all_complete
    )


# =============================================================================
# HELPER: Non-blocking checklist update (for use by other modules)
# =============================================================================

async def update_checklist_item_async(user_id: str, item_key: str):
    """
    Non-blocking update of a checklist item.

    Called by other modules when events occur that should mark checklist items.
    Never throws - failures are logged and ignored.
    """
    try:
        db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {f"discovery.checklist_items.{item_key}": True}},
            upsert=True
        )

        # Check completion
        user_doc = db.db.users.find_one({"user_id": user_id}, {"discovery.checklist_items": 1})
        if user_doc:
            items = user_doc.get("discovery", {}).get("checklist_items", {})
            # Merge with defaults
            for key in DEFAULT_CHECKLIST_ITEMS:
                if key not in items:
                    items[key] = False

            if all(items.values()):
                db.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"discovery.checklist_complete": True}}
                )
    except Exception as e:
        logger.warning(f"Checklist update failed for {user_id}/{item_key}: {e}")


def update_checklist_item_sync(user_id: str, item_key: str):
    """
    Synchronous version of checklist update.

    For use in synchronous contexts (e.g., scaffolding engine).
    """
    try:
        db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {f"discovery.checklist_items.{item_key}": True}},
            upsert=True
        )

        # Check completion
        user_doc = db.db.users.find_one({"user_id": user_id}, {"discovery.checklist_items": 1})
        if user_doc:
            items = user_doc.get("discovery", {}).get("checklist_items", {})
            for key in DEFAULT_CHECKLIST_ITEMS:
                if key not in items:
                    items[key] = False

            if all(items.values()):
                db.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"discovery.checklist_complete": True}}
                )
    except Exception as e:
        logger.warning(f"Checklist update failed for {user_id}/{item_key}: {e}")
