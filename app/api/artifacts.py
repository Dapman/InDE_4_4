"""
InDE v3.15 - Artifacts API Routes
CRUD operations for formal artifacts (Vision, Fears, Hypothesis documents).
v3.15: Added Getting Started checklist integration.
v3.14: Added onboarding metrics instrumentation.
v3.7.4.4: Added file upload support for data files.
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid
import base64
import os
import logging

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel

from auth.middleware import get_current_user
from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
from api.user_discovery import update_checklist_item_async

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed file types for upload
ALLOWED_EXTENSIONS = {'.csv', '.json', '.xlsx', '.xls', '.txt', '.md', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class CreateArtifactRequest(BaseModel):
    pursuit_id: str
    artifact_type: str  # "vision", "fears", "hypothesis"
    title: str
    content: str


class UpdateArtifactRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class ArtifactResponse(BaseModel):
    artifact_id: str
    pursuit_id: str
    artifact_type: str
    title: str
    content: str
    version: int
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=ArtifactResponse)
async def create_artifact(
    request: Request,
    data: CreateArtifactRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a new artifact for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    artifact_id = str(uuid.uuid4())
    artifact = {
        "artifact_id": artifact_id,
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"],
        "artifact_type": data.artifact_type,
        "title": data.title,
        "content": data.content,
        "version": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    db.db.artifacts.insert_one(artifact)

    # Add to pursuit's artifact list
    db.db.pursuits.update_one(
        {"pursuit_id": data.pursuit_id},
        {
            "$push": {"artifact_ids": artifact_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    # v3.14: Record onboarding metrics for vision and fears artifacts
    try:
        metrics_service = OnboardingMetricsService(db)
        if data.artifact_type == "vision":
            await metrics_service.record_criterion_met(user["user_id"], "vision_artifact_created")
            await metrics_service.record_screen_reached(user["user_id"], 3)
        elif data.artifact_type == "fears":
            await metrics_service.record_criterion_met(user["user_id"], "fear_identified")
            await metrics_service.record_screen_reached(user["user_id"], 4)
    except Exception as e:
        logger.warning(f"Onboarding metrics recording failed: {e}")

    # v3.15: Update Getting Started checklist
    try:
        if data.artifact_type == "vision":
            await update_checklist_item_async(user["user_id"], "vision_created")
        elif data.artifact_type == "fears":
            await update_checklist_item_async(user["user_id"], "fear_identified")
        # Any artifact counts as first artifact generated
        await update_checklist_item_async(user["user_id"], "first_artifact_generated")
    except Exception as e:
        logger.warning(f"Discovery checklist update failed: {e}")

    return ArtifactResponse(**{k: v for k, v in artifact.items() if k != "_id"})


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    request: Request,
    artifact_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get an artifact by ID.
    """
    db = request.app.state.db

    artifact = db.db.artifacts.find_one({
        "artifact_id": artifact_id,
        "user_id": user["user_id"]
    })

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(**{k: v for k, v in artifact.items() if k != "_id"})


@router.get("/pursuit/{pursuit_id}")
async def list_pursuit_artifacts(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    List all artifacts for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    artifacts = list(db.db.artifacts.find(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    ).sort("created_at", -1))

    return {"pursuit_id": pursuit_id, "artifacts": artifacts}


@router.patch("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    request: Request,
    artifact_id: str,
    data: UpdateArtifactRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update an artifact (creates new version).
    """
    db = request.app.state.db

    artifact = db.db.artifacts.find_one({
        "artifact_id": artifact_id,
        "user_id": user["user_id"]
    })

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    updates = {"updated_at": datetime.now(timezone.utc)}
    if data.title is not None:
        updates["title"] = data.title
    if data.content is not None:
        updates["content"] = data.content
        updates["version"] = artifact.get("version", 1) + 1

    db.db.artifacts.update_one(
        {"artifact_id": artifact_id},
        {"$set": updates}
    )

    updated = db.db.artifacts.find_one({"artifact_id": artifact_id})

    return ArtifactResponse(**{k: v for k, v in updated.items() if k != "_id"})


@router.delete("/{artifact_id}")
async def delete_artifact(
    request: Request,
    artifact_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete an artifact.
    """
    db = request.app.state.db

    artifact = db.db.artifacts.find_one({
        "artifact_id": artifact_id,
        "user_id": user["user_id"]
    })

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Remove from pursuit
    db.db.pursuits.update_one(
        {"pursuit_id": artifact["pursuit_id"]},
        {"$pull": {"artifact_ids": artifact_id}}
    )

    # Delete artifact
    db.db.artifacts.delete_one({"artifact_id": artifact_id})

    return {"message": "Artifact deleted successfully"}


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    pursuit_id: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """
    Upload a data file as an artifact.
    Supports: CSV, JSON, Excel, TXT, MD, PDF files up to 10MB.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Validate file extension
    filename = file.filename or "uploaded_file"
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Determine artifact type based on extension
    artifact_type_map = {
        '.csv': 'data_file',
        '.json': 'data_file',
        '.xlsx': 'data_file',
        '.xls': 'data_file',
        '.txt': 'document',
        '.md': 'document',
        '.pdf': 'document',
    }
    artifact_type = artifact_type_map.get(ext, 'data_file')

    # For text files, store content directly; for binary, store base64
    if ext in {'.txt', '.md', '.csv'}:
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError:
            file_content = base64.b64encode(content).decode('ascii')
    else:
        file_content = base64.b64encode(content).decode('ascii')

    artifact_id = str(uuid.uuid4())
    artifact = {
        "artifact_id": artifact_id,
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"],
        "artifact_type": artifact_type,
        "title": filename,
        "content": file_content,
        "file_name": filename,
        "file_extension": ext,
        "file_size": len(content),
        "is_binary": ext not in {'.txt', '.md', '.csv'},
        "version": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    db.db.artifacts.insert_one(artifact)

    # Add to pursuit's artifact list
    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {
            "$push": {"artifact_ids": artifact_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    return {
        "artifact_id": artifact_id,
        "pursuit_id": pursuit_id,
        "artifact_type": artifact_type,
        "title": filename,
        "file_name": filename,
        "file_size": len(content),
        "version": 1,
        "created_at": artifact["created_at"].isoformat()
    }
