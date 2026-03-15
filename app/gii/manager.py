"""
InDE v3.16 - Global Innovator Identifier (GII) Manager
GII binding and publication boundary enforcement.

GII Format (GII Portability Protocol v1.0):
  GII-[REGION]-[INDIVIDUAL_HASH]-[CHECK]
  Example: GII-US-8D4E9F2A1B3C4E5F-A7F3

Components:
  REGION          Two-letter code (US, EU, AP, etc.)
  INDIVIDUAL_HASH 16-character hex hash — derived from user_id + timestamp + UUID
  CHECK           4-character checksum for validation

v3.16: Auto-assignment at registration, PROVISIONAL state issuance
v3.1: Original implementation with 12-char format

Storage Elections:
- FULL_PARTICIPATION: All IKF-eligible data can be contributed
- ORG_VISIBLE: Only visible within organization
- PRIVATE: Never shared externally

Publication Boundary:
Working states (raw conversations, drafts, coaching notes) are NEVER
published regardless of storage election.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import hashlib
import uuid
import secrets
import logging

from core.config import (
    GII_CONFIG,
    STORAGE_ELECTIONS,
    WORKING_STATE_TYPES
)

logger = logging.getLogger("inde.gii")


class GIIManager:
    """
    Manages Global Innovator Identifiers and publication boundaries.
    """

    def __init__(self, db):
        """
        Initialize GII manager with database access.

        Args:
            db: Database instance
        """
        self.db = db

    def generate_gii(self, region: str = None, user_id: str = None) -> str:
        """
        Generate a new Global Innovator Identifier (v3.16 format).

        Args:
            region: Region code (US, EU, AP, etc.)
            user_id: Optional user ID for hash input

        Returns:
            New GII string in format GII-[REGION]-[16_CHAR_HASH]-[4_CHAR_CHECK]
        """
        region = (region or GII_CONFIG.get("default_region", "US")).upper()

        # Generate 16-character individual hash
        hash_input = f"{user_id or ''}:{datetime.now(timezone.utc).isoformat()}:{secrets.token_hex(16)}"
        individual_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16].upper()

        # 4-character check digits
        check_input = f"{region}:{individual_hash}"
        check = hashlib.md5(check_input.encode()).hexdigest()[:4].upper()

        return f"GII-{region}-{individual_hash}-{check}"

    def issue_provisional(self, user_id: str, region_code: str = "US") -> str:
        """
        Issue a PROVISIONAL GII at registration.
        Called once, immediately, during user account creation.

        v3.16: New method for auto-assignment at registration.

        Args:
            user_id: The user's ID
            region_code: Two-letter region code

        Returns:
            The generated GII string
        """
        # Generate GII
        gii_id = self.generate_gii(region_code, user_id)

        # Create GII profile with PROVISIONAL state
        profile = {
            "gii_id": gii_id,
            "user_id": str(user_id),
            "state": "PROVISIONAL",
            "region": region_code.upper(),
            "storage_election": "FULL_PARTICIPATION",
            "organization_id": None,
            "verification_level": "UNVERIFIED",
            "binding_type": "INDIVIDUAL",
            "binding_org_id": None,
            "binding_history": [],
            "reputation_score": 0.0,
            "contribution_count": 0,
            "issued_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "privacy_settings": {
                "allow_public_profile": False,
                "allow_ikf_contribution": True,
                "allow_anonymized_patterns": True
            }
        }

        self.db.db.gii_profiles.insert_one(profile)

        # Update user record
        self.db.db.users.update_one(
            {"_id": user_id} if not isinstance(user_id, str) else {"user_id": user_id},
            {"$set": {"gii_id": gii_id, "gii_state": "PROVISIONAL"}}
        )

        logger.info(f"PROVISIONAL GII issued: {gii_id} for user {user_id}")

        return gii_id

    def bind_gii(
        self,
        user_id: str,
        gii_id: Optional[str] = None,
        region: str = None
    ) -> Dict:
        """
        Bind a GII to a user.

        Args:
            user_id: User to bind GII to
            gii_id: Optional existing GII (for migration)
            region: Region for new GII generation

        Returns:
            GII profile
        """
        # Check if user already has GII
        existing = self.db.db.gii_profiles.find_one({"user_id": user_id})
        if existing:
            raise ValueError("User already has a GII bound")

        # Generate or validate GII
        if gii_id:
            # Validate format
            if not self._validate_gii_format(gii_id):
                raise ValueError(f"Invalid GII format: {gii_id}")

            # Check uniqueness
            duplicate = self.db.db.gii_profiles.find_one({"gii_id": gii_id})
            if duplicate:
                raise ValueError(f"GII already in use: {gii_id}")
        else:
            gii_id = self.generate_gii(region)

        # Create GII profile
        profile = {
            "gii_id": gii_id,
            "user_id": user_id,
            "region": region or GII_CONFIG.get("default_region", "NA"),
            "bound_at": datetime.now(timezone.utc),
            "storage_election": "FULL_PARTICIPATION",
            "organization_id": None,
            "privacy_settings": {
                "allow_public_profile": False,
                "allow_ikf_contribution": True,
                "allow_anonymized_patterns": True
            }
        }

        self.db.db.gii_profiles.insert_one(profile)

        # Update user record
        self.db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"gii_id": gii_id}}
        )

        logger.info(f"GII bound: {gii_id} to user {user_id}")

        return profile

    def _validate_gii_format(self, gii_id: str) -> bool:
        """
        Validate GII format. Supports both v3.1 (12-char) and v3.16 (16-char + check) formats.

        Args:
            gii_id: GII string to validate

        Returns:
            True if valid format
        """
        if not gii_id:
            return False

        parts = gii_id.split("-")

        # v3.16 format: GII-REGION-16CHAR_HASH-4CHAR_CHECK (4 parts)
        if len(parts) == 4:
            prefix, region, identifier, check = parts
            if prefix != "GII":
                return False
            if len(region) < 2 or len(region) > 5:
                return False
            if len(identifier) != 16:
                return False
            if len(check) != 4:
                return False
            return True

        # v3.1 format: GII-REGION-12CHAR_ID (3 parts)
        if len(parts) == 3:
            prefix, region, identifier = parts
            if prefix != "GII":
                return False
            if len(region) < 2 or len(region) > 5:
                return False
            if len(identifier) != 12:
                return False
            return True

        return False

    def get_storage_election(self, pursuit_id: str) -> str:
        """
        Get storage election for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Storage election string
        """
        pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})
        if not pursuit:
            return "PRIVATE"

        return pursuit.get("storage_election", "FULL_PARTICIPATION")

    def update_storage_election(
        self,
        pursuit_id: str,
        user_id: str,
        election: str
    ) -> bool:
        """
        Update storage election for a pursuit.

        Args:
            pursuit_id: Pursuit ID
            user_id: User ID (for verification)
            election: New storage election

        Returns:
            True if updated successfully
        """
        if election not in STORAGE_ELECTIONS:
            raise ValueError(f"Invalid storage election: {election}")

        # Verify ownership
        pursuit = self.db.db.pursuits.find_one({
            "pursuit_id": pursuit_id,
            "user_id": user_id
        })

        if not pursuit:
            raise ValueError("Pursuit not found or not owned by user")

        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "storage_election": election,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        return True

    def is_publishable(self, data_type: str, pursuit_id: str) -> bool:
        """
        Check if data is publishable based on type and storage election.

        Args:
            data_type: Type of data (e.g., "artifact", "raw_conversation")
            pursuit_id: Pursuit ID

        Returns:
            True if data can be published to IKF
        """
        # Working states are NEVER publishable
        if data_type in WORKING_STATE_TYPES:
            return False

        # Check storage election
        election = self.get_storage_election(pursuit_id)

        if election == "PRIVATE":
            return False

        if election == "ORG_VISIBLE":
            # Only org-internal publication allowed
            # For v3.1, we don't have org-level IKF, so return False
            return False

        # FULL_PARTICIPATION allows publication
        return True

    def get_publishable_data_types(self, pursuit_id: str) -> List[str]:
        """
        Get list of data types that can be published for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of publishable data types
        """
        election = self.get_storage_election(pursuit_id)

        if election == "PRIVATE":
            return []

        # Publishable types (excluding working states)
        all_types = [
            "artifact",
            "retrospective_summary",
            "learning_pattern",
            "experiment_result",
            "risk_resolution",
            "outcome_summary",
            "velocity_benchmark"
        ]

        if election == "ORG_VISIBLE":
            # Subset for org-only
            return ["artifact", "retrospective_summary"]

        return all_types

    def prepare_for_ikf(self, data: Dict, data_type: str) -> Optional[Dict]:
        """
        Prepare data for IKF contribution by removing PII and working state.

        Args:
            data: Raw data dict
            data_type: Type of data

        Returns:
            Sanitized data ready for IKF, or None if not publishable
        """
        if data_type in WORKING_STATE_TYPES:
            return None

        # Remove PII fields
        pii_fields = [
            "user_id",
            "user_email",
            "user_name",
            "stakeholder_names",
            "ip_address",
            "session_id"
        ]

        sanitized = data.copy()

        for field in pii_fields:
            if field in sanitized:
                del sanitized[field]

        # Add GII reference if available
        if "gii_id" not in sanitized:
            # Could look up GII from user_id in original data
            pass

        # Add publication metadata
        sanitized["_ikf_metadata"] = {
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "data_type": data_type,
            "schema_version": "3.5.0"
        }

        return sanitized
