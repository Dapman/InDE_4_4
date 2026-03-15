"""
InDE MVP v2.9 - Pursuit Sharer
Enable viral growth through shareable pursuit links.

Features:
- Generate shareable URLs with privacy levels
- Read-only public pursuit views
- Access analytics tracking
- Viral CTAs for new user acquisition
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from config import SHARING_CONFIG, PRIVACY_LEVELS, PUBLIC_VIEW_SECTIONS


class PursuitSharer:
    """
    Enable viral growth through shareable pursuit links.

    Creates shareable URLs with configurable privacy levels and
    tracks access analytics for viral growth measurement.
    """

    def __init__(self, db):
        """
        Initialize the pursuit sharer.

        Args:
            db: Database instance
        """
        self.db = db
        self.config = SHARING_CONFIG

    def generate_share_link(self, pursuit_id: str, user_id: str,
                           privacy_level: str = None,
                           expiry_days: int = None,
                           allowed_viewers: List[str] = None) -> Dict:
        """
        Create shareable URL for pursuit.

        Args:
            pursuit_id: ID of pursuit to share
            user_id: ID of user creating the share
            privacy_level: public, unlisted, or private (default from config)
            expiry_days: Days until link expires (None for permanent)
            allowed_viewers: List of user IDs for private links

        Returns:
            Dict with share URL and metadata
        """
        # Validate pursuit exists
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError(f"Pursuit not found: {pursuit_id}")

        # Check if user owns this pursuit
        if pursuit.get("user_id") != user_id:
            raise ValueError("Cannot share pursuit you don't own")

        # Set defaults
        if privacy_level is None:
            privacy_level = self.config.get("default_privacy_level", "unlisted")

        if privacy_level not in PRIVACY_LEVELS:
            raise ValueError(f"Invalid privacy level: {privacy_level}")

        # Generate secure token
        token_length = self.config.get("share_token_length", 32)
        share_token = secrets.token_urlsafe(token_length)

        # Calculate expiry
        expires_at = None
        if expiry_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

        # Create shared pursuit record
        shared_record = {
            "pursuit_id": pursuit_id,
            "share_token": share_token,
            "privacy_level": privacy_level,
            "created_by": user_id,
            "expires_at": expires_at,
            "allowed_viewers": allowed_viewers or []
        }

        share_id = self.db.create_shared_pursuit(shared_record)

        # Generate URL
        base_url = self.config.get("share_link_base_url", "http://localhost:7860")
        share_url = f"{base_url}/pursuit/{share_token}"

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="share_link_created",
            description=f"Created {privacy_level} share link",
            metadata={"share_id": share_id, "privacy_level": privacy_level}
        )

        return {
            "share_id": share_id,
            "share_url": share_url,
            "share_token": share_token,
            "privacy_level": privacy_level,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_permanent": expires_at is None
        }

    def revoke_share_link(self, share_token: str, user_id: str) -> bool:
        """
        Disable a share link.

        Args:
            share_token: Token of the share link to revoke
            user_id: ID of user requesting revocation

        Returns:
            True if revoked successfully
        """
        shared = self.db.get_shared_pursuit_by_token(share_token)
        if not shared:
            return False

        # Verify ownership
        if shared.get("created_by") != user_id:
            raise ValueError("Cannot revoke share link you didn't create")

        success = self.db.revoke_share_link(share_token)

        if success:
            # Log activity
            self.db.log_activity(
                pursuit_id=shared.get("pursuit_id"),
                activity_type="share_link_revoked",
                description="Share link revoked",
                metadata={"share_token": share_token[:8] + "..."}
            )

        return success

    def get_public_view_data(self, share_token: str,
                             viewer_info: Dict = None) -> Optional[Dict]:
        """
        Fetch pursuit data for read-only display.

        Args:
            share_token: Token from share URL
            viewer_info: Optional info about viewer for analytics

        Returns:
            Dict with sanitized pursuit data or None if invalid
        """
        # Validate token
        shared = self.db.get_shared_pursuit_by_token(share_token)
        if not shared:
            return None

        # Check if active
        if not shared.get("is_active", True):
            return None

        # Check expiry
        expires_at = shared.get("expires_at")
        if expires_at and datetime.now(timezone.utc) > expires_at:
            return None

        # Check privacy level for private links
        privacy_level = shared.get("privacy_level", "unlisted")
        if privacy_level == "private":
            viewer_id = viewer_info.get("user_id") if viewer_info else None
            allowed = shared.get("allowed_viewers", [])
            if viewer_id not in allowed:
                return None

        # Get pursuit data
        pursuit_id = shared.get("pursuit_id")
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Track access
        self.track_access(share_token, viewer_info)

        # Get scaffolding state for elements
        scaffolding = self.db.get_scaffolding_state(pursuit_id)

        # Get artifacts
        artifacts = self.db.get_pursuit_artifacts(pursuit_id)

        # Get risk definitions if any
        risks = self.db.get_pursuit_risks(pursuit_id)

        # Get activity feed
        activity_feed = self.db.get_activity_feed(pursuit_id, limit=20)

        # Build sanitized view data
        view_data = {
            "pursuit_id": pursuit_id,
            "title": pursuit.get("title"),
            "created_at": pursuit.get("created_at"),
            "status": pursuit.get("status", "active"),
            "state": pursuit.get("state", "ACTIVE"),
            "privacy_level": privacy_level,
            "sections": {}
        }

        # Vision section
        if "vision" in PUBLIC_VIEW_SECTIONS:
            vision_artifact = next(
                (a for a in artifacts if a.get("type") == "vision"),
                None
            )
            view_data["sections"]["vision"] = {
                "artifact": vision_artifact.get("content") if vision_artifact else None,
                "elements": self._sanitize_elements(
                    scaffolding.get("vision_elements", {}) if scaffolding else {}
                )
            }

        # Fears section
        if "fears" in PUBLIC_VIEW_SECTIONS:
            fear_artifact = next(
                (a for a in artifacts if a.get("type") == "fears"),
                None
            )
            view_data["sections"]["fears"] = {
                "artifact": fear_artifact.get("content") if fear_artifact else None,
                "elements": self._sanitize_elements(
                    scaffolding.get("fear_elements", {}) if scaffolding else {}
                )
            }

        # Hypotheses section
        if "hypotheses" in PUBLIC_VIEW_SECTIONS:
            hypothesis_artifact = next(
                (a for a in artifacts if a.get("type") == "hypothesis"),
                None
            )
            view_data["sections"]["hypotheses"] = {
                "artifact": hypothesis_artifact.get("content") if hypothesis_artifact else None,
                "elements": self._sanitize_elements(
                    scaffolding.get("hypothesis_elements", {}) if scaffolding else {}
                )
            }

        # Progress timeline
        if "progress_timeline" in PUBLIC_VIEW_SECTIONS:
            view_data["sections"]["progress_timeline"] = self._build_progress_timeline(
                activity_feed, artifacts
            )

        # Risk validation (RVE Lite)
        if "risk_validation" in PUBLIC_VIEW_SECTIONS and risks:
            view_data["sections"]["risk_validation"] = [
                {
                    "risk_parameter": r.get("risk_parameter"),
                    "category": r.get("risk_category"),
                    "priority": r.get("validation_priority"),
                    "status": r.get("validation_status"),
                    "evidence_count": len(r.get("linked_evidence", []))
                }
                for r in risks
            ]

        # Add viral CTA if enabled
        if self.config.get("viral_cta_enabled", True):
            view_data["viral_cta"] = {
                "text": self.config.get("viral_cta_text", "Create your own innovation pursuit"),
                "url": self.config.get("share_link_base_url", "") + "/signup"
            }

        # Add social proof if enabled
        if self.config.get("show_social_proof", True):
            view_data["social_proof"] = self._get_social_proof()

        # Get access analytics for share owner
        view_data["analytics"] = shared.get("access_analytics", {})

        return view_data

    def _sanitize_elements(self, elements: Dict) -> Dict:
        """Remove internal metadata from elements for public view."""
        sanitized = {}
        for key, value in elements.items():
            if value and isinstance(value, dict):
                text = value.get("text")
                if text:
                    sanitized[key] = text
        return sanitized

    def _build_progress_timeline(self, activity_feed: List[Dict],
                                  artifacts: List[Dict]) -> List[Dict]:
        """Build a progress timeline from activity and artifacts."""
        timeline = []

        # Add artifact creation events
        for artifact in artifacts:
            timeline.append({
                "timestamp": artifact.get("created_at"),
                "type": "artifact_created",
                "description": f"{artifact.get('type', 'Unknown').title()} artifact created",
                "version": artifact.get("version", 1)
            })

        # Add selected activity events
        interesting_types = [
            "decision_made", "phase_transition", "risk_defined",
            "evidence_captured", "stakeholder_feedback"
        ]
        for activity in activity_feed:
            if activity.get("activity_type") in interesting_types:
                timeline.append({
                    "timestamp": activity.get("timestamp"),
                    "type": activity.get("activity_type"),
                    "description": activity.get("description")
                })

        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)

        return timeline[:20]  # Limit to 20 items

    def _get_social_proof(self) -> Dict:
        """Get social proof statistics."""
        min_users = self.config.get("social_proof_min_users", 100)

        # Count total users (simplified)
        try:
            user_count = len(list(self.db.db.users.find()))
            if user_count < min_users:
                return None

            return {
                "user_count": user_count,
                "message": f"Join {user_count:,} innovators using InDE"
            }
        except Exception:
            return None

    def track_access(self, share_token: str, viewer_info: Dict = None) -> bool:
        """
        Record access analytics.

        Args:
            share_token: Token of the share link
            viewer_info: Optional info about viewer

        Returns:
            True if tracked successfully
        """
        # Increment view count
        self.db.increment_share_analytics(share_token, "total_views")

        # Track unique visitors (simplified - would use cookies/fingerprinting)
        if viewer_info and viewer_info.get("is_new_visitor"):
            self.db.increment_share_analytics(share_token, "unique_visitors")

        return True

    def track_section_view(self, share_token: str, section: str) -> bool:
        """
        Track which sections are viewed.

        Args:
            share_token: Token of the share link
            section: Section name (vision, fears, etc.)

        Returns:
            True if tracked successfully
        """
        self.db.increment_share_analytics(share_token, f"sections_viewed.{section}")
        return True

    def track_referral_signup(self, share_token: str) -> bool:
        """
        Track when a viewer signs up (viral conversion).

        Args:
            share_token: Token of the referring share link

        Returns:
            True if tracked successfully
        """
        self.db.increment_share_analytics(share_token, "referral_signups")
        return True

    def get_share_analytics(self, pursuit_id: str = None,
                            user_id: str = None) -> Dict:
        """
        Get analytics for share links.

        Args:
            pursuit_id: Optional filter by pursuit
            user_id: Optional filter by creator

        Returns:
            Dict with analytics summary
        """
        query = {}
        if pursuit_id:
            query["pursuit_id"] = pursuit_id
        if user_id:
            query["created_by"] = user_id

        shares = list(self.db.db.shared_pursuits.find(query))

        analytics = {
            "total_shares": len(shares),
            "active_shares": sum(1 for s in shares if s.get("is_active", True)),
            "by_privacy": {
                "public": 0,
                "unlisted": 0,
                "private": 0
            },
            "total_views": 0,
            "unique_visitors": 0,
            "referral_signups": 0,
            "viral_coefficient": 0.0
        }

        for share in shares:
            privacy = share.get("privacy_level", "unlisted")
            if privacy in analytics["by_privacy"]:
                analytics["by_privacy"][privacy] += 1

            access = share.get("access_analytics", {})
            analytics["total_views"] += access.get("total_views", 0)
            analytics["unique_visitors"] += access.get("unique_visitors", 0)
            analytics["referral_signups"] += access.get("referral_signups", 0)

        # Calculate viral coefficient
        if analytics["unique_visitors"] > 0:
            analytics["viral_coefficient"] = (
                analytics["referral_signups"] / analytics["unique_visitors"]
            )

        return analytics

    def get_user_shares(self, user_id: str) -> List[Dict]:
        """
        Get all shares created by a user.

        Args:
            user_id: User ID

        Returns:
            List of share records with analytics
        """
        shares = list(self.db.db.shared_pursuits.find({"created_by": user_id}))

        result = []
        for share in shares:
            pursuit = self.db.get_pursuit(share.get("pursuit_id"))
            result.append({
                "share_id": share.get("share_id"),
                "share_token": share.get("share_token"),
                "pursuit_title": pursuit.get("title") if pursuit else "Unknown",
                "privacy_level": share.get("privacy_level"),
                "is_active": share.get("is_active", True),
                "created_at": share.get("created_at"),
                "expires_at": share.get("expires_at"),
                "analytics": share.get("access_analytics", {})
            })

        return result
