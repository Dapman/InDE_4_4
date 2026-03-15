"""
InDE v3.1 - Reports API Routes
Report generation and distribution.
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user

router = APIRouter()


class CreateReportRequest(BaseModel):
    pursuit_id: str
    report_type: str  # "living_snapshot", "terminal", "portfolio"
    template: Optional[str] = "silr-standard"


class ReportResponse(BaseModel):
    report_id: str
    pursuit_id: Optional[str]
    report_type: str
    template: str
    status: str
    content: Optional[str]
    created_at: datetime


@router.post("", response_model=ReportResponse)
async def create_report(
    request: Request,
    data: CreateReportRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a new report for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    report_id = str(uuid.uuid4())
    report = {
        "report_id": report_id,
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"],
        "report_type": data.report_type,
        "template": data.template,
        "status": "generating",
        "content": None,
        "created_at": datetime.now(timezone.utc)
    }

    # Store in appropriate collection based on type
    if data.report_type == "living_snapshot":
        db.db.living_snapshot_reports.insert_one(report)
    elif data.report_type == "terminal":
        db.db.terminal_reports.insert_one(report)
    else:
        db.db.portfolio_analytics_reports.insert_one(report)

    # Placeholder: In full implementation, trigger async report generation
    report["status"] = "draft"
    report["content"] = f"# Report for {pursuit['title']}\n\nReport generation placeholder."

    return ReportResponse(**{k: v for k, v in report.items() if k != "_id"})


@router.get("/{report_id}")
async def get_report(
    request: Request,
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a report by ID.
    """
    db = request.app.state.db

    # Check all report collections
    for collection in ["living_snapshot_reports", "terminal_reports", "portfolio_analytics_reports"]:
        report = db.db[collection].find_one({
            "report_id": report_id,
            "user_id": user["user_id"]
        })
        if report:
            if "_id" in report:
                del report["_id"]
            return report

    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/pursuit/{pursuit_id}")
async def list_pursuit_reports(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    List all reports for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    reports = []

    for collection in ["living_snapshot_reports", "terminal_reports"]:
        docs = list(db.db[collection].find(
            {"pursuit_id": pursuit_id},
            {"_id": 0}
        ).sort("created_at", -1))
        reports.extend(docs)

    return {"pursuit_id": pursuit_id, "reports": reports}
