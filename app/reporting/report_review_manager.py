"""
InDE MVP v2.8 - Report Review Manager

Manages report review, editing, commenting, and approval workflow.
Supports the full lifecycle: Draft -> Review -> Edit -> Approve -> Finalize

Key Features:
- Start and manage review process
- Add comments/annotations to sections
- Edit section content with version tracking
- Approval workflow
- Version control for reports
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import REPORT_REVIEW_CONFIG


class ReportReviewManager:
    """
    Manages report review, editing, commenting, and approval workflow.
    """

    # Review statuses
    STATUS_DRAFT = "DRAFT"
    STATUS_IN_REVIEW = "IN_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_FINALIZED = "FINALIZED"
    STATUS_REJECTED = "REJECTED"

    def __init__(self, database):
        self.db = database

    def start_review(self, report_id: str, reviewer_id: str) -> Dict:
        """
        Begin review process for a report.

        Args:
            report_id: Report to review
            reviewer_id: User starting the review

        Returns:
            {
                "report_id": str,
                "review_status": str,
                "editable_sections": list
            }
        """
        report = self._get_report(report_id)

        if not report:
            raise ValueError(f"Report {report_id} not found")

        current_status = report.get("review_status", self.STATUS_DRAFT)
        if current_status == self.STATUS_FINALIZED:
            raise ValueError("Cannot review a finalized report. Create a new version first.")

        # Update status to IN_REVIEW
        self.db.update_report(report_id, {
            "review_status": self.STATUS_IN_REVIEW,
            "reviewed_by": reviewer_id,
            "review_started_at": datetime.now(timezone.utc)
        })

        editable_sections = self._get_editable_sections(report)

        return {
            "report_id": report_id,
            "review_status": self.STATUS_IN_REVIEW,
            "reviewer_id": reviewer_id,
            "editable_sections": editable_sections,
            "current_comments": len(report.get("comments", [])),
            "current_edits": len(report.get("edits", []))
        }

    def add_comment(
        self,
        report_id: str,
        section_id: str,
        text: str,
        created_by: str,
        comment_type: str = "note"  # "note", "question", "suggestion", "issue"
    ) -> Dict:
        """
        Add comment/annotation to report section.

        Args:
            report_id: Report ID
            section_id: Section to comment on
            text: Comment text
            created_by: User creating comment
            comment_type: Type of comment

        Returns:
            Comment record
        """
        if not REPORT_REVIEW_CONFIG.get("enable_comments", True):
            raise ValueError("Comments are disabled in configuration")

        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        comment = {
            "comment_id": str(uuid.uuid4()),
            "section_id": section_id,
            "text": text,
            "comment_type": comment_type,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
            "resolved": False,
            "resolved_by": None,
            "resolved_at": None
        }

        # Add to report's comments list
        comments = report.get("comments", [])
        comments.append(comment)

        self.db.update_report(report_id, {"comments": comments})

        return comment

    def resolve_comment(
        self,
        report_id: str,
        comment_id: str,
        resolved_by: str
    ) -> Dict:
        """
        Mark a comment as resolved.

        Args:
            report_id: Report ID
            comment_id: Comment to resolve
            resolved_by: User resolving

        Returns:
            Updated comment
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        comments = report.get("comments", [])
        updated_comment = None

        for comment in comments:
            if comment["comment_id"] == comment_id:
                comment["resolved"] = True
                comment["resolved_by"] = resolved_by
                comment["resolved_at"] = datetime.now(timezone.utc)
                updated_comment = comment
                break

        if not updated_comment:
            raise ValueError(f"Comment {comment_id} not found")

        self.db.update_report(report_id, {"comments": comments})

        return updated_comment

    def get_comments(
        self,
        report_id: str,
        section_id: str = None,
        include_resolved: bool = True
    ) -> List[Dict]:
        """
        Get comments for a report.

        Args:
            report_id: Report ID
            section_id: Optional filter by section
            include_resolved: Include resolved comments

        Returns:
            List of comments
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        comments = report.get("comments", [])

        # Apply filters
        if section_id:
            comments = [c for c in comments if c["section_id"] == section_id]

        if not include_resolved:
            comments = [c for c in comments if not c["resolved"]]

        return comments

    def edit_section(
        self,
        report_id: str,
        section_id: str,
        new_content: str,
        edited_by: str,
        edit_reason: str = None
    ) -> Dict:
        """
        Edit report section content.

        Args:
            report_id: Report ID
            section_id: Section to edit
            new_content: New content for section
            edited_by: User making edit
            edit_reason: Optional reason for edit

        Returns:
            Edit record
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Check if finalized
        if report.get("review_status") == self.STATUS_FINALIZED:
            raise ValueError("Cannot edit a finalized report. Create a new version first.")

        # Get original content
        content = report.get("content", {})
        original_content = content.get(section_id, {})

        # Create edit record
        edit = {
            "edit_id": str(uuid.uuid4()),
            "section_id": section_id,
            "original_content": original_content,
            "edited_content": new_content,
            "edited_by": edited_by,
            "edited_at": datetime.now(timezone.utc),
            "edit_reason": edit_reason
        }

        # Add to edits list
        edits = report.get("edits", [])
        edits.append(edit)

        # Update report content
        content[section_id] = new_content

        self.db.update_report(report_id, {
            "content": content,
            "edits": edits,
            "updated_at": datetime.now(timezone.utc)
        })

        return edit

    def revert_edit(
        self,
        report_id: str,
        edit_id: str,
        reverted_by: str
    ) -> Dict:
        """
        Revert a specific edit.

        Args:
            report_id: Report ID
            edit_id: Edit to revert
            reverted_by: User reverting

        Returns:
            Revert record
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        edits = report.get("edits", [])
        edit_to_revert = None

        for edit in edits:
            if edit.get("edit_id") == edit_id:
                edit_to_revert = edit
                break

        if not edit_to_revert:
            raise ValueError(f"Edit {edit_id} not found")

        # Restore original content
        section_id = edit_to_revert["section_id"]
        original_content = edit_to_revert["original_content"]

        content = report.get("content", {})
        content[section_id] = original_content

        # Create revert record
        revert = {
            "edit_id": str(uuid.uuid4()),
            "section_id": section_id,
            "original_content": edit_to_revert["edited_content"],
            "edited_content": original_content,
            "edited_by": reverted_by,
            "edited_at": datetime.now(timezone.utc),
            "edit_reason": f"Reverted edit {edit_id}"
        }

        edits.append(revert)

        self.db.update_report(report_id, {
            "content": content,
            "edits": edits,
            "updated_at": datetime.now(timezone.utc)
        })

        return revert

    def approve_report(
        self,
        report_id: str,
        approved_by: str,
        approval_notes: str = None
    ) -> Dict:
        """
        Approve report for finalization.

        Args:
            report_id: Report to approve
            approved_by: User approving
            approval_notes: Optional notes

        Returns:
            Approval record
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Check for unresolved comments
        unresolved = [c for c in report.get("comments", []) if not c["resolved"]]
        if unresolved and REPORT_REVIEW_CONFIG.get("require_resolved_comments", False):
            raise ValueError(f"Cannot approve with {len(unresolved)} unresolved comments")

        # Update status
        self.db.update_report(report_id, {
            "review_status": self.STATUS_APPROVED,
            "approved_by": approved_by,
            "approval_date": datetime.now(timezone.utc),
            "approval_notes": approval_notes
        })

        return {
            "report_id": report_id,
            "review_status": self.STATUS_APPROVED,
            "approved_by": approved_by,
            "approval_date": datetime.now(timezone.utc).isoformat()
        }

    def reject_report(
        self,
        report_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> Dict:
        """
        Reject report and return to draft status.

        Args:
            report_id: Report to reject
            rejected_by: User rejecting
            rejection_reason: Reason for rejection

        Returns:
            Rejection record
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Update status back to draft
        self.db.update_report(report_id, {
            "review_status": self.STATUS_DRAFT,
            "rejected_by": rejected_by,
            "rejection_date": datetime.now(timezone.utc),
            "rejection_reason": rejection_reason
        })

        return {
            "report_id": report_id,
            "review_status": self.STATUS_DRAFT,
            "rejected_by": rejected_by,
            "rejection_reason": rejection_reason
        }

    def finalize_report(self, report_id: str, finalized_by: str = None) -> Dict:
        """
        Finalize report (make immutable).

        Args:
            report_id: Report to finalize
            finalized_by: User finalizing

        Returns:
            Finalization record
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        current_status = report.get("review_status", self.STATUS_DRAFT)

        # Must be approved first (unless we're allowing direct finalization)
        if current_status != self.STATUS_APPROVED:
            if REPORT_REVIEW_CONFIG.get("require_approval_for_external", True):
                raise ValueError("Report must be approved before finalization")

        self.db.update_report(report_id, {
            "review_status": self.STATUS_FINALIZED,
            "finalized_at": datetime.now(timezone.utc),
            "finalized_by": finalized_by
        })

        return {
            "report_id": report_id,
            "review_status": self.STATUS_FINALIZED,
            "finalized_at": datetime.now(timezone.utc).isoformat()
        }

    def create_new_version(self, report_id: str, created_by: str = None) -> str:
        """
        Create new version of report for further edits.

        Args:
            report_id: Original report ID
            created_by: User creating version

        Returns:
            New report ID
        """
        if not REPORT_REVIEW_CONFIG.get("enable_version_control", True):
            raise ValueError("Version control is disabled")

        original = self._get_report(report_id)
        if not original:
            raise ValueError(f"Report {report_id} not found")

        # Check version limit
        max_versions = REPORT_REVIEW_CONFIG.get("max_versions_stored", 5)
        previous_versions = original.get("previous_versions", [])
        if len(previous_versions) >= max_versions:
            # Could clean up old versions here
            pass

        # Create new version
        new_report_id = str(uuid.uuid4())
        new_version = {
            "report_id": new_report_id,
            "version": original.get("version", 1) + 1,
            "previous_versions": previous_versions + [report_id],
            "review_status": self.STATUS_DRAFT,
            "created_at": datetime.now(timezone.utc),
            "created_by": created_by,
            # Copy content and metadata
            "report_type": original.get("report_type"),
            "pursuit_id": original.get("pursuit_id"),
            "template_id": original.get("template_id"),
            "content": original.get("content", {}),
            "metadata": original.get("metadata", {}),
            # Reset review data
            "comments": [],
            "edits": [],
            "reviewed_by": None,
            "approved_by": None
        }

        self.db.create_report(new_version)

        return new_report_id

    def get_version_history(self, report_id: str) -> List[Dict]:
        """
        Get version history for a report.

        Args:
            report_id: Current report ID

        Returns:
            List of version summaries
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        history = []
        previous_versions = report.get("previous_versions", [])

        for prev_id in previous_versions:
            prev_report = self._get_report(prev_id)
            if prev_report:
                history.append({
                    "report_id": prev_id,
                    "version": prev_report.get("version", 1),
                    "created_at": prev_report.get("created_at"),
                    "finalized_at": prev_report.get("finalized_at"),
                    "review_status": prev_report.get("review_status")
                })

        # Add current version
        history.append({
            "report_id": report_id,
            "version": report.get("version", 1),
            "created_at": report.get("created_at"),
            "finalized_at": report.get("finalized_at"),
            "review_status": report.get("review_status"),
            "current": True
        })

        return history

    def get_review_summary(self, report_id: str) -> Dict:
        """
        Get summary of review activity.

        Args:
            report_id: Report ID

        Returns:
            Review summary
        """
        report = self._get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        comments = report.get("comments", [])
        edits = report.get("edits", [])

        unresolved_comments = [c for c in comments if not c["resolved"]]
        resolved_comments = [c for c in comments if c["resolved"]]

        return {
            "report_id": report_id,
            "review_status": report.get("review_status", self.STATUS_DRAFT),
            "version": report.get("version", 1),
            "total_comments": len(comments),
            "unresolved_comments": len(unresolved_comments),
            "resolved_comments": len(resolved_comments),
            "total_edits": len(edits),
            "reviewed_by": report.get("reviewed_by"),
            "review_started_at": report.get("review_started_at"),
            "approved_by": report.get("approved_by"),
            "approval_date": report.get("approval_date"),
            "finalized_at": report.get("finalized_at")
        }

    def _get_report(self, report_id: str) -> Optional[Dict]:
        """Get report from any collection."""
        # Try different report types
        report = self.db.get_report(report_id) if hasattr(self.db, 'get_report') else None

        if not report:
            # Try specific collections
            if hasattr(self.db, 'get_terminal_report'):
                report = self.db.get_terminal_report(report_id)

            if not report and hasattr(self.db, 'get_living_snapshot_report'):
                report = self.db.get_living_snapshot_report(report_id)

            if not report and hasattr(self.db, 'get_portfolio_analytics_report'):
                report = self.db.get_portfolio_analytics_report(report_id)

        return report

    def _get_editable_sections(self, report: Dict) -> List[Dict]:
        """
        Get list of sections that can be edited.

        Args:
            report: Report data

        Returns:
            List of editable section info
        """
        content = report.get("content", {})
        template_id = report.get("template_id")

        editable = []
        for section_id, section_data in content.items():
            # Check if section allows editing based on template
            auto_populated = False
            if isinstance(section_data, dict):
                auto_populated = section_data.get("auto_populated", True)

            editable.append({
                "section_id": section_id,
                "auto_populated": auto_populated,
                "current_content": section_data if isinstance(section_data, str) else section_data.get("data", {})
            })

        return editable
