"""
InDE MVP v2.9 - Artifact Comments
Enable commenting on artifacts for async collaboration.

Features:
- Add comments to vision, fear, hypothesis artifacts
- Resolve comments when addressed
- Track comment threads
"""

from datetime import datetime
from typing import Dict, List, Optional

from config import COLLABORATION_CONFIG


class ArtifactComments:
    """
    Manage comments on artifacts for collaboration.

    Allows stakeholders and team members to comment on
    vision, fear, and hypothesis artifacts.
    """

    def __init__(self, db):
        """
        Initialize the comments handler.

        Args:
            db: Database instance
        """
        self.db = db
        self.config = COLLABORATION_CONFIG

    def add_comment(self, artifact_id: str, pursuit_id: str,
                   commenter_id: str = None, commenter_email: str = None,
                   commenter_name: str = None, comment_text: str = "") -> str:
        """
        Add comment to artifact.

        Args:
            artifact_id: ID of the artifact to comment on
            pursuit_id: ID of the pursuit (for activity logging)
            commenter_id: Optional user ID if InDE user
            commenter_email: Email of commenter
            commenter_name: Display name of commenter
            comment_text: The comment text

        Returns:
            comment_id of created comment
        """
        if not self.config.get("enable_comments", True):
            raise ValueError("Comments are disabled")

        if not comment_text.strip():
            raise ValueError("Comment text is required")

        # Check max comments limit
        existing = self.db.get_artifact_comments(artifact_id)
        max_comments = self.config.get("max_comments_per_artifact", 100)
        if len(existing) >= max_comments:
            raise ValueError(f"Maximum comments ({max_comments}) reached for this artifact")

        comment_record = {
            "artifact_id": artifact_id,
            "pursuit_id": pursuit_id,
            "commenter_id": commenter_id,
            "commenter_email": commenter_email,
            "commenter_name": commenter_name or "Anonymous",
            "comment_text": comment_text
        }

        comment_id = self.db.create_artifact_comment(comment_record)

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="comment_added",
            description=f"{commenter_name or 'Someone'} commented on artifact",
            metadata={
                "comment_id": comment_id,
                "artifact_id": artifact_id,
                "commenter_name": commenter_name
            }
        )

        # Notify artifact owner
        self._notify_owner(pursuit_id, artifact_id, commenter_name, comment_text)

        return comment_id

    def resolve_comment(self, comment_id: str, resolver_id: str) -> bool:
        """
        Mark comment as resolved.

        Args:
            comment_id: ID of comment to resolve
            resolver_id: ID of user resolving the comment

        Returns:
            True if resolved successfully
        """
        comment = self.db.get_artifact_comment(comment_id)
        if not comment:
            return False

        # Verify resolver owns the pursuit
        pursuit_id = comment.get("pursuit_id")
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit or pursuit.get("user_id") != resolver_id:
            raise ValueError("Only the pursuit owner can resolve comments")

        success = self.db.resolve_artifact_comment(comment_id, resolver_id)

        if success:
            # Log activity
            self.db.log_activity(
                pursuit_id=pursuit_id,
                activity_type="comment_resolved",
                description=f"Resolved comment from {comment.get('commenter_name', 'someone')}",
                metadata={"comment_id": comment_id}
            )

        return success

    def get_artifact_comments(self, artifact_id: str,
                              include_resolved: bool = True) -> List[Dict]:
        """
        Retrieve all comments for artifact.

        Args:
            artifact_id: ID of the artifact
            include_resolved: Whether to include resolved comments

        Returns:
            List of comments with metadata
        """
        comments = self.db.get_artifact_comments(artifact_id)

        if not include_resolved:
            comments = [c for c in comments if not c.get("resolved")]

        return [self._format_comment(c) for c in comments]

    def get_pursuit_comments(self, pursuit_id: str,
                             include_resolved: bool = True) -> List[Dict]:
        """
        Get all comments for a pursuit across all artifacts.

        Args:
            pursuit_id: ID of the pursuit
            include_resolved: Whether to include resolved comments

        Returns:
            List of comments grouped by artifact
        """
        comments = self.db.get_pursuit_comments(pursuit_id)

        if not include_resolved:
            comments = [c for c in comments if not c.get("resolved")]

        # Group by artifact
        by_artifact = {}
        for comment in comments:
            artifact_id = comment.get("artifact_id")
            if artifact_id not in by_artifact:
                by_artifact[artifact_id] = []
            by_artifact[artifact_id].append(self._format_comment(comment))

        return by_artifact

    def get_unresolved_count(self, pursuit_id: str) -> int:
        """
        Get count of unresolved comments for a pursuit.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            Count of unresolved comments
        """
        comments = self.db.get_pursuit_comments(pursuit_id)
        return sum(1 for c in comments if not c.get("resolved"))

    def _format_comment(self, comment: Dict) -> Dict:
        """Format comment for display."""
        return {
            "comment_id": comment.get("comment_id"),
            "commenter_name": comment.get("commenter_name", "Anonymous"),
            "commenter_email": comment.get("commenter_email"),
            "comment_text": comment.get("comment_text"),
            "created_at": comment.get("created_at"),
            "resolved": comment.get("resolved", False),
            "resolved_by": comment.get("resolved_by"),
            "resolved_at": comment.get("resolved_at")
        }

    def _notify_owner(self, pursuit_id: str, artifact_id: str,
                      commenter_name: str, comment_text: str) -> None:
        """Notify pursuit owner of new comment."""
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return

        user_id = pursuit.get("user_id")
        user = self.db.get_user(user_id)
        if not user:
            return

        # In production, would send email
        print(
            f"[Notification] New comment on {pursuit.get('title')} "
            f"from {commenter_name}: {comment_text[:50]}..."
        )

    def get_comment_summary(self, pursuit_id: str) -> Dict:
        """
        Get comment summary for pursuit.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            Dict with comment statistics
        """
        comments = self.db.get_pursuit_comments(pursuit_id)

        summary = {
            "total": len(comments),
            "unresolved": sum(1 for c in comments if not c.get("resolved")),
            "resolved": sum(1 for c in comments if c.get("resolved")),
            "by_artifact": {},
            "recent_comments": []
        }

        # Count by artifact
        for comment in comments:
            artifact_id = comment.get("artifact_id")
            if artifact_id not in summary["by_artifact"]:
                summary["by_artifact"][artifact_id] = {"total": 0, "unresolved": 0}
            summary["by_artifact"][artifact_id]["total"] += 1
            if not comment.get("resolved"):
                summary["by_artifact"][artifact_id]["unresolved"] += 1

        # Recent comments (last 5)
        recent = sorted(comments, key=lambda c: c.get("created_at", ""), reverse=True)[:5]
        summary["recent_comments"] = [
            {
                "commenter_name": c.get("commenter_name"),
                "comment_text": c.get("comment_text", "")[:100],
                "created_at": c.get("created_at"),
                "resolved": c.get("resolved", False)
            }
            for c in recent
        ]

        return summary
