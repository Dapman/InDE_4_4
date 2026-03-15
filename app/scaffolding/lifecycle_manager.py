"""
InDE MVP v2.4 - Artifact Lifecycle Manager

Manages artifact versioning and regeneration. Detects when artifacts
become stale as the pursuit evolves and offers regeneration at appropriate moments.

Key Responsibilities:
1. Detect when scaffolding elements change after artifact generation
2. Classify change severity (MINOR, MODERATE, MAJOR)
3. Suggest regeneration at appropriate moments
4. Create versioned artifacts (v1, v2, v3...)
5. Preserve learning history (old versions stay in IML)

The lifecycle manager enables artifacts to evolve naturally with the pursuit
while preserving the history of how thinking evolved.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import CRITICAL_ELEMENTS


class ArtifactLifecycleManager:
    """
    Manages artifact versioning and regeneration.

    Detects when artifacts become stale due to scaffolding element changes
    and facilitates natural artifact evolution through versioning.
    """

    # Change severity thresholds
    SEVERITY_THRESHOLDS = {
        "MINOR": 0.15,      # <15% of elements changed
        "MODERATE": 0.35,   # 15-35% changed
        "MAJOR": 0.35       # >35% changed (pivot-level)
    }

    # Critical elements that trigger MAJOR if changed
    CRITICAL_CHANGE_ELEMENTS = [
        "problem_statement",
        "solution_concept",
        "target_user",
        "value_proposition"
    ]

    def __init__(self, database, element_tracker):
        """
        Initialize ArtifactLifecycleManager.

        Args:
            database: Database instance for artifact persistence
            element_tracker: ElementTracker instance for current state
        """
        self.db = database
        self.element_tracker = element_tracker

    def detect_artifact_drift(self, pursuit_id: str) -> List[Dict]:
        """
        Check all artifacts for this pursuit to detect staleness.

        Compares the elements used to generate each artifact against
        the current scaffolding state to detect meaningful changes.

        Args:
            pursuit_id: ID of the pursuit to check

        Returns:
            List of drift detections, e.g.:
            [
                {
                    "artifact_id": "uuid",
                    "artifact_type": "vision",
                    "version": 1,
                    "change_severity": "MODERATE",
                    "changed_elements": ["solution_concept", "value_proposition"],
                    "change_description": "Solution evolved from individual to enterprise focus",
                    "should_suggest_regen": True
                }
            ]
        """
        print(f"[LifecycleManager] Detecting drift for pursuit: {pursuit_id}")

        # Get all current artifacts for this pursuit (only CURRENT status)
        artifacts = self.db.get_pursuit_artifacts(pursuit_id)
        current_artifacts = [
            a for a in artifacts
            if a.get("status", "CURRENT") == "CURRENT"
        ]

        if not current_artifacts:
            return []

        drifts = []

        for artifact in current_artifacts:
            artifact_type = artifact.get("type", "vision")

            # Get elements that were used to generate this artifact
            generated_from = artifact.get("generated_from", {})
            generation_elements = generated_from.get("elements_used", {})

            # If elements_used is a list (old format), skip detailed comparison
            if isinstance(generation_elements, list):
                # Convert to dict format for comparison
                generation_elements = {elem: {"text": ""} for elem in generation_elements}

            # Get current scaffolding elements for this artifact type
            current_elements = self.db.get_present_elements(pursuit_id, artifact_type)

            # Compare elements
            changes = self._compare_elements(
                generation_elements,
                current_elements,
                artifact_type
            )

            if changes["has_changes"]:
                severity = self._classify_severity(
                    changes["changed_elements"],
                    artifact_type
                )

                drift = {
                    "artifact_id": artifact.get("artifact_id"),
                    "artifact_type": artifact_type,
                    "version": artifact.get("version", 1),
                    "change_severity": severity,
                    "changed_elements": changes["changed_elements"],
                    "change_description": changes["description"],
                    "should_suggest_regen": severity in ["MODERATE", "MAJOR"]
                }
                drifts.append(drift)

                print(f"[LifecycleManager] Detected {severity} drift in {artifact_type}: "
                      f"{changes['changed_elements']}")

        return drifts

    def _compare_elements(self, old_elements: Dict, new_elements: Dict,
                          artifact_type: str) -> Dict:
        """
        Compare two element sets to detect changes.

        Args:
            old_elements: Elements at artifact generation time
            new_elements: Current elements
            artifact_type: Type of artifact (vision, fears, hypothesis)

        Returns:
            {
                "has_changes": bool,
                "changed_elements": [element_names],
                "new_elements": [newly added element names],
                "description": "human readable change summary"
            }
        """
        changed = []
        new_additions = []

        # Get all possible elements for this artifact type
        all_elements = CRITICAL_ELEMENTS.get(artifact_type, [])

        for element_name in all_elements:
            old_value = old_elements.get(element_name, {})
            new_value = new_elements.get(element_name, "")

            # Handle different data formats
            old_text = ""
            if isinstance(old_value, dict):
                old_text = old_value.get("text", "")
            elif isinstance(old_value, str):
                old_text = old_value

            new_text = new_value if isinstance(new_value, str) else ""

            # Check for new element (didn't exist before, exists now)
            if not old_text and new_text:
                new_additions.append(element_name)

            # Check for meaningful change (both exist but different)
            elif old_text and new_text and old_text != new_text:
                if self._is_significant_change(old_text, new_text):
                    changed.append(element_name)

        # Combine changed and new for total drift
        all_changes = changed + new_additions

        # Generate human-readable description
        description = self._generate_change_description(
            old_elements, new_elements, changed, new_additions
        )

        return {
            "has_changes": len(all_changes) > 0,
            "changed_elements": all_changes,
            "new_elements": new_additions,
            "description": description
        }

    def _is_significant_change(self, old_text: str, new_text: str) -> bool:
        """
        Check if text change is significant (>20% different).

        Uses word-level comparison to determine if the change
        is meaningful or just minor wording tweaks.

        Args:
            old_text: Previous element text
            new_text: Current element text

        Returns:
            True if change is significant (>20% different)
        """
        if not old_text and not new_text:
            return False
        if not old_text or not new_text:
            return True

        # Simple word-level diff
        old_words = set(old_text.lower().split())
        new_words = set(new_text.lower().split())

        if not old_words:
            return True

        common = old_words.intersection(new_words)
        similarity = len(common) / max(len(old_words), len(new_words))

        return similarity < 0.8  # 20% difference threshold

    def _classify_severity(self, changed_elements: List[str],
                           artifact_type: str) -> str:
        """
        Classify change severity.

        Args:
            changed_elements: List of element names that changed
            artifact_type: Type of artifact

        Returns:
            "MINOR" | "MODERATE" | "MAJOR"
        """
        if not changed_elements:
            return "MINOR"

        # Check if critical element changed
        critical_changed = any(
            elem in self.CRITICAL_CHANGE_ELEMENTS
            for elem in changed_elements
        )

        if critical_changed:
            return "MAJOR"

        # Calculate percentage of elements changed
        total_elements = len(CRITICAL_ELEMENTS.get(artifact_type, []))
        if total_elements == 0:
            return "MINOR"

        change_ratio = len(changed_elements) / total_elements

        if change_ratio < self.SEVERITY_THRESHOLDS["MINOR"]:
            return "MINOR"
        elif change_ratio < self.SEVERITY_THRESHOLDS["MODERATE"]:
            return "MODERATE"
        else:
            return "MAJOR"

    def _generate_change_description(self, old_elements: Dict, new_elements: Dict,
                                      changed: List[str], new_additions: List[str]) -> str:
        """
        Generate human-readable description of what changed.

        Args:
            old_elements: Previous element state
            new_elements: Current element state
            changed: List of changed element names
            new_additions: List of newly added element names

        Returns:
            Human-readable description string
        """
        if not changed and not new_additions:
            return "No significant changes"

        descriptions = []

        # Focus on most important changes first
        if "problem_statement" in changed:
            descriptions.append("your problem definition evolved")

        if "solution_concept" in changed:
            old_solution = old_elements.get("solution_concept", {})
            old_text = old_solution.get("text", "")[:40] if isinstance(old_solution, dict) else str(old_solution)[:40]
            new_text = new_elements.get("solution_concept", "")[:40]
            if old_text and new_text:
                descriptions.append(f"solution evolved from '{old_text}...' to '{new_text}...'")
            else:
                descriptions.append("your solution approach changed")

        if "target_user" in changed:
            descriptions.append("target user segment changed")

        if "value_proposition" in changed:
            descriptions.append("value proposition refined")

        # Handle new additions
        if new_additions:
            if len(new_additions) <= 2:
                descriptions.append(f"added {', '.join(new_additions)}")
            else:
                descriptions.append(f"added {len(new_additions)} new elements")

        # Handle remaining changes
        remaining = [c for c in changed if c not in
                     ["problem_statement", "solution_concept", "target_user", "value_proposition"]]
        if remaining and not descriptions:
            descriptions.append(f"updated {', '.join(remaining[:3])}")

        return "; ".join(descriptions) if descriptions else "Multiple elements refined"

    def regenerate_artifact(self, artifact_id: str, artifact_generator) -> Optional[Dict]:
        """
        Create new version of artifact with current scaffolding state.

        Workflow:
        1. Get old artifact
        2. Generate new artifact with current elements
        3. Increment version number
        4. Link to parent artifact
        5. Mark old artifact as superseded
        6. Return new artifact

        Args:
            artifact_id: ID of artifact to regenerate
            artifact_generator: ArtifactGenerator instance

        Returns:
            {
                "artifact_id": "new_uuid",
                "version": 2,
                "parent_artifact_id": "old_uuid",
                "type": "vision",
                "content": "...",
                "changes_summary": "Updated 3 elements..."
            }
            or None if regeneration failed
        """
        print(f"[LifecycleManager] Regenerating artifact: {artifact_id}")

        # Get old artifact
        old_artifact = self.db.get_artifact(artifact_id)
        if not old_artifact:
            print(f"[LifecycleManager] Artifact not found: {artifact_id}")
            return None

        pursuit_id = old_artifact.get("pursuit_id")
        artifact_type = old_artifact.get("type")
        old_version = old_artifact.get("version", 1)

        # Generate new artifact
        new_artifact = artifact_generator.generate_artifact(
            pursuit_id=pursuit_id,
            artifact_type=artifact_type,
            method="regeneration"
        )

        if not new_artifact:
            print(f"[LifecycleManager] Failed to generate new artifact")
            return None

        # The artifact_generator already stored the artifact
        # We need to update its versioning metadata
        new_artifact_id = new_artifact.get("artifact_id")

        # Update new artifact with versioning info
        version_updates = {
            "version": old_version + 1,
            "parent_artifact_id": artifact_id,
            "status": "CURRENT"
        }
        self.db.update_artifact(new_artifact_id, version_updates)

        # Mark old artifact as superseded
        self.db.update_artifact(artifact_id, {
            "status": "SUPERSEDED",
            "superseded_at": datetime.now(timezone.utc),
            "superseded_by": new_artifact_id
        })

        print(f"[LifecycleManager] Created {artifact_type} v{old_version + 1} "
              f"(superseded v{old_version})")

        return {
            "artifact_id": new_artifact_id,
            "version": old_version + 1,
            "parent_artifact_id": artifact_id,
            "type": artifact_type,
            "content": new_artifact.get("content", ""),
            "changes_summary": f"Updated to v{old_version + 1} reflecting latest pursuit evolution"
        }

    def get_artifact_history(self, pursuit_id: str, artifact_type: str) -> List[Dict]:
        """
        Get version history for an artifact type.

        Args:
            pursuit_id: Pursuit ID
            artifact_type: Type of artifact (vision, fears, hypothesis)

        Returns:
            List of artifact versions, newest first
        """
        all_artifacts = self.db.get_pursuit_artifacts(pursuit_id, artifact_type)

        # Sort by version descending
        sorted_artifacts = sorted(
            all_artifacts,
            key=lambda a: a.get("version", 1),
            reverse=True
        )

        return [
            {
                "artifact_id": a.get("artifact_id"),
                "version": a.get("version", 1),
                "status": a.get("status", "CURRENT"),
                "created_at": a.get("created_at"),
                "superseded_at": a.get("superseded_at"),
                "parent_artifact_id": a.get("parent_artifact_id")
            }
            for a in sorted_artifacts
        ]

    def generate_drift_suggestion(self, drift: Dict) -> str:
        """
        Generate natural coaching suggestion for artifact drift.

        Args:
            drift: Drift detection dict from detect_artifact_drift()

        Returns:
            Natural language suggestion for the user
        """
        artifact_type = drift.get("artifact_type", "vision").title()
        severity = drift.get("change_severity", "MODERATE")
        description = drift.get("change_description", "your thinking has evolved")
        version = drift.get("version", 1)

        if severity == "MAJOR":
            return (
                f"I notice your thinking has evolved significantly - {description}. "
                f"Your {artifact_type} Statement was created before this shift. "
                f"Would you like me to create an updated version (v{version + 1}) "
                f"reflecting this new direction?"
            )
        elif severity == "MODERATE":
            return (
                f"I see we've refined some key elements - {description}. "
                f"Want me to update your {artifact_type} Statement to reflect "
                f"these changes? I'll preserve the original as v{version} "
                f"so you can see how your thinking evolved."
            )
        else:
            return (
                f"Some details in your {artifact_type} have evolved. "
                f"Let me know if you'd like an updated version!"
            )
