"""
Publication Boundary Enforcement

Runtime assertions that prevent private data from crossing organizational boundaries.
Any violation is a HARD BLOCK on federation operation.

Boundaries enforced:
1. PERSONAL storage election -> NEVER enters generalization pipeline
2. ORG storage election -> MUST pass through generalization BEFORE federation
3. UNAVAILABLE innovator -> Completely invisible to ALL federation packages
4. Coaching transcripts -> NEVER included in any contribution
5. Individual maturity scores -> NEVER included in any contribution
6. PII -> Caught by entity detector; any remaining PII blocks submission

These checks are redundant with the generalization pipeline by design.
Defense in depth: if generalization fails to catch something, the boundary catches it.

CRITICAL: A single privacy violation blocks the entire v3.5.3 build.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("inde.ikf.publication_boundary")


class PublicationBoundaryError(Exception):
    """
    Raised when a publication boundary violation is detected.

    This exception MUST block federation submission.
    """
    pass


class PublicationBoundary:
    """
    Enforces privacy boundaries on outbound contributions.

    Every contribution MUST pass through this boundary before
    federation submission. Any violation raises PublicationBoundaryError.
    """

    def __init__(self, db):
        """
        Initialize the Publication Boundary.

        Args:
            db: MongoDB database instance
        """
        self._db = db

    def enforce(self, contribution: dict, user_id: str) -> dict:
        """
        Run all publication boundary checks on a contribution.

        Args:
            contribution: The contribution to check
            user_id: The user who owns this contribution

        Returns:
            {"passed": True, "violations": []}

        Raises:
            PublicationBoundaryError: On any violation
        """
        violations = []

        # Check 1: Storage election
        violations.extend(self._check_storage_election(contribution, user_id))

        # Check 2: UNAVAILABLE innovator
        violations.extend(self._check_unavailable(contribution, user_id))

        # Check 3: No coaching transcripts
        violations.extend(self._check_no_transcripts(contribution))

        # Check 4: No individual maturity scores
        violations.extend(self._check_no_maturity_scores(contribution))

        # Check 5: PII scan
        violations.extend(self._check_pii_clear(contribution))

        # Check 6: Generalization applied (for ORG-scoped)
        violations.extend(self._check_generalization_applied(contribution))

        if violations:
            self._log_violations(contribution, violations)
            raise PublicationBoundaryError(
                f"Publication boundary violations: {[v['check'] for v in violations]}"
            )

        # Record clean check in audit trail
        self._db.audit_events.insert_one({
            "event_type": "publication_boundary.passed",
            "contribution_id": contribution.get("contribution_id"),
            "user_id": user_id,
            "checks_passed": 6,
            "timestamp": datetime.now(timezone.utc)
        })

        return {"passed": True, "violations": []}

    def _check_storage_election(self, contribution: dict, user_id: str) -> List[dict]:
        """
        PERSONAL data must NEVER enter the federation pipeline.

        Checks both pursuit-level and user-level storage elections.
        """
        violations = []

        # Check the source pursuit's storage election
        pursuit_id = contribution.get("pursuit_id")
        if pursuit_id:
            pursuit = self._db.pursuits.find_one({"pursuit_id": pursuit_id})
            if pursuit:
                storage = pursuit.get("storage_election", "PERSONAL")
                if storage == "PERSONAL":
                    violations.append({
                        "check": "STORAGE_ELECTION",
                        "severity": "CRITICAL",
                        "detail": f"Pursuit {pursuit_id} has PERSONAL storage - cannot federate"
                    })

        # Also check user-level default
        if user_id:
            user = self._db.users.find_one({"_id": user_id})
            if user:
                default_storage = user.get("default_storage_election", "PERSONAL")
                if default_storage == "PERSONAL" and not contribution.get("explicit_ikf_consent"):
                    violations.append({
                        "check": "USER_DEFAULT_STORAGE",
                        "severity": "WARNING",
                        "detail": "User default is PERSONAL - ensure explicit IKF consent was given"
                    })

        return violations

    def _check_unavailable(self, contribution: dict, user_id: str) -> List[dict]:
        """
        UNAVAILABLE innovators must be completely invisible.

        No data from an UNAVAILABLE user can ever reach federation.
        """
        violations = []

        if user_id:
            user = self._db.users.find_one({"_id": user_id})
            if user:
                availability = user.get("federation_availability", "AVAILABLE")
                if availability == "UNAVAILABLE":
                    violations.append({
                        "check": "UNAVAILABLE_INNOVATOR",
                        "severity": "CRITICAL",
                        "detail": f"User {user_id} is UNAVAILABLE - cannot contribute to federation"
                    })

        return violations

    def _check_no_transcripts(self, contribution: dict) -> List[dict]:
        """
        Coaching transcripts must NEVER appear in contributions.

        Scans for transcript markers that would indicate raw coaching
        conversation data leaked into the contribution.
        """
        violations = []

        # Get all content to scan
        content_sources = [
            contribution.get("generalized_content", {}),
            contribution.get("generalized_data", {}),
            contribution.get("original_data", {})  # Should be empty/null but check anyway
        ]

        content = str(content_sources).lower()

        # Check for transcript markers
        transcript_markers = [
            "coaching_transcript",
            "session_transcript",
            "conversation_log",
            "coach_said",
            "innovator_said",
            "assistant:",
            "user:",
            "<<coaching_session>>",
            "<<conversation>>",
            "raw_transcript",
            "dialogue_history"
        ]

        for marker in transcript_markers:
            if marker.lower() in content:
                violations.append({
                    "check": "TRANSCRIPT_LEAK",
                    "severity": "CRITICAL",
                    "detail": f"Possible transcript content detected: '{marker}'"
                })

        return violations

    def _check_no_maturity_scores(self, contribution: dict) -> List[dict]:
        """
        Individual maturity scores must NEVER appear in contributions.

        These are personal assessment data that cannot be shared.
        """
        violations = []

        content_sources = [
            contribution.get("generalized_content", {}),
            contribution.get("generalized_data", {})
        ]

        content = str(content_sources).lower()

        # Check for maturity score patterns
        maturity_markers = [
            "maturity_score",
            "maturity_level",
            "innovator_maturity",
            "individual_maturity",
            "personal_maturity",
            "user_maturity_score",
            "maturity_assessment",
            "maturity_rating"
        ]

        for marker in maturity_markers:
            if marker.lower() in content:
                violations.append({
                    "check": "MATURITY_SCORE_LEAK",
                    "severity": "CRITICAL",
                    "detail": f"Possible maturity score detected: '{marker}'"
                })

        return violations

    def _check_pii_clear(self, contribution: dict) -> List[dict]:
        """
        Verify PII scan passed with no high-confidence flags remaining.

        High-confidence PII flags indicate likely personally identifiable
        information that wasn't removed during generalization.
        """
        violations = []

        pii_scan = contribution.get("pii_scan", {})
        high_flags = pii_scan.get("high_confidence_flags", [])

        if high_flags:
            violations.append({
                "check": "PII_REMAINING",
                "severity": "CRITICAL",
                "detail": f"PII detected: {len(high_flags)} high-confidence flags - {high_flags[:3]}"
            })

        return violations

    def _check_generalization_applied(self, contribution: dict) -> List[dict]:
        """
        ORG-scoped data must have been generalized before federation.

        Verifies that the generalization level meets the minimum threshold.
        """
        violations = []

        gen_level = contribution.get("generalization_level", 0)
        min_level = contribution.get("min_generalization_level", 1)

        if gen_level < min_level:
            violations.append({
                "check": "INSUFFICIENT_GENERALIZATION",
                "severity": "CRITICAL",
                "detail": f"Generalization level {gen_level} < minimum {min_level}"
            })

        # Also check for missing generalized content
        if not contribution.get("generalized_content") and not contribution.get("generalized_data"):
            violations.append({
                "check": "MISSING_GENERALIZED_CONTENT",
                "severity": "CRITICAL",
                "detail": "No generalized content present - generalization may not have run"
            })

        return violations

    def _log_violations(self, contribution: dict, violations: List[dict]):
        """
        Log violations to audit trail - these are serious events.

        All violations are recorded for security audit and incident response.
        """
        self._db.audit_events.insert_one({
            "event_type": "publication_boundary.VIOLATION",
            "contribution_id": contribution.get("contribution_id"),
            "violations": violations,
            "severity": "CRITICAL",
            "timestamp": datetime.now(timezone.utc)
        })

        for v in violations:
            logger.error(
                f"PUBLICATION BOUNDARY VIOLATION: {v['check']} - {v['detail']}"
            )

    def validate_preview(self, contribution: dict, user_id: str) -> dict:
        """
        Preview validation without blocking.

        Used during contribution preparation to show warnings before final approval.

        Returns:
            {"would_pass": bool, "issues": [...]}
        """
        issues = []

        try:
            issues.extend(self._check_storage_election(contribution, user_id))
        except Exception:
            pass

        try:
            issues.extend(self._check_unavailable(contribution, user_id))
        except Exception:
            pass

        try:
            issues.extend(self._check_no_transcripts(contribution))
        except Exception:
            pass

        try:
            issues.extend(self._check_no_maturity_scores(contribution))
        except Exception:
            pass

        try:
            issues.extend(self._check_pii_clear(contribution))
        except Exception:
            pass

        try:
            issues.extend(self._check_generalization_applied(contribution))
        except Exception:
            pass

        critical_issues = [i for i in issues if i.get("severity") == "CRITICAL"]

        return {
            "would_pass": len(critical_issues) == 0,
            "issues": issues,
            "critical_count": len(critical_issues),
            "warning_count": len([i for i in issues if i.get("severity") == "WARNING"])
        }
