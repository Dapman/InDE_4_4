"""
InDE EMS v3.7.3 - Archetype Publisher

Commits innovator-approved methodologies to the Archetype Repository.
The published archetype becomes a selectable methodology for future
pursuits - functionally identical to hand-authored archetypes.

Publication pipeline:
1. Validate the refined archetype (ADL compatibility)
2. Assign version 1.0 designation
3. Generate attribution metadata
4. Apply visibility settings
5. Register in the Archetype Repository
6. Register Display Labels for the new archetype
7. Emit publication event
8. Optionally prepare for IKF sharing

Visibility Levels:
- PERSONAL: Only the creator can see and use
- TEAM: Visible to team members (shared pursuits)
- ORGANIZATION: Visible to organization members
- IKF_SHARED: Federated to the Innovation Knowledge Fabric
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

logger = logging.getLogger("inde.ems.publisher")


class ArchetypePublisher:
    """
    Publishes EMS-discovered methodologies to the archetype repository.

    The published archetype becomes selectable for future pursuits,
    functionally identical to hand-authored archetypes like Lean Startup.
    """

    VISIBILITY_LEVELS = ["PERSONAL", "TEAM", "ORGANIZATION", "IKF_SHARED"]

    def __init__(self, db=None, archetype_registry=None, display_labels=None, ikf_service=None):
        """
        Args:
            db: Database instance. If None, uses singleton.
            archetype_registry: Optional archetype registry for registration
            display_labels: Optional display labels registry
            ikf_service: Optional IKF service for federation
        """
        if db is None:
            from core.database import db as singleton_db
            db = singleton_db
        self.db = db
        self.archetype_registry = archetype_registry
        self.display_labels = display_labels
        self.ikf_service = ikf_service

    def publish(self, review_session: Dict, innovator: Dict) -> Dict:
        """
        Publish a reviewed and approved archetype to the repository.

        Args:
            review_session: Completed review session with refined_archetype
            innovator: Innovator profile for attribution

        Returns:
            Published archetype document with repository ID
        """
        refined = review_session.get("refined_archetype", {})

        # Step 1: Final validation
        validation = self._validate_for_publication(refined)
        if not validation["valid"]:
            raise ValueError(f"Cannot publish: {validation['errors']}")

        # Step 2: Version designation
        versioned = self._assign_version(refined, innovator)

        # Step 3: Attribution metadata
        versioned["attribution"] = self._generate_attribution(innovator, review_session)

        # Step 4: Visibility settings
        versioned["visibility"] = review_session.get("visibility", "PERSONAL")

        # Step 5: Provenance finalization
        provenance = versioned.get("provenance", {})
        provenance["published_at"] = datetime.now(timezone.utc).isoformat()
        provenance["review_session_id"] = str(review_session.get("_id", ""))
        provenance["refinement_count"] = len(review_session.get("refinements", []))
        versioned["provenance"] = provenance

        # Step 6: Remove draft flag, mark as published
        versioned["draft"] = False
        versioned["published"] = True

        # Step 7: Persist to published_archetypes collection
        # Store in the same collection as generated archetypes but with published flag
        archetype_doc = {
            "innovator_id": str(innovator.get("_id", innovator.get("innovator_id", ""))),
            "archetype_result": versioned,
            "is_active": True,
            "published": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        result = self.db.db.generated_archetypes.insert_one(archetype_doc)
        versioned["_id"] = str(result.inserted_id)

        # Step 8: Register in Archetype Repository (if available)
        if self.archetype_registry:
            self._register_in_repository(versioned)

        # Step 9: Register Display Labels (if available)
        if self.display_labels:
            self._register_display_labels(versioned)

        # Step 10: Update review session
        self._update_review_session(review_session, result.inserted_id)

        # Step 11: Update inference result if available
        if review_session.get("inference_result_id"):
            self._update_inference_result(review_session["inference_result_id"])

        logger.info(
            f"Archetype published: '{versioned.get('display_name', versioned.get('name', 'Unknown'))}' "
            f"by innovator {innovator.get('display_name', 'unknown')} "
            f"(visibility: {versioned['visibility']})"
        )

        return versioned

    def _validate_for_publication(self, archetype: Dict) -> Dict:
        """Final validation before publication."""
        from ems.adl_generator import validate_adl_compatibility

        # Get the archetype content (may be nested)
        arch_content = archetype.get("archetype", archetype)

        validation = validate_adl_compatibility(archetype)

        # Additional publication-specific checks
        errors = validation.get("errors", [])

        display_name = arch_content.get("display_name") or arch_content.get("name")
        if not display_name:
            errors.append("Methodology must have a name")
            validation["valid"] = False

        description = arch_content.get("description")
        if not description:
            errors.append("Methodology must have a description")
            validation["valid"] = False

        phases = arch_content.get("phases", [])
        if not phases:
            errors.append("Methodology must have at least one phase")
            validation["valid"] = False

        validation["errors"] = errors
        return validation

    def _assign_version(self, archetype: Dict, innovator: Dict) -> Dict:
        """
        Assign version designation.

        First publication = 1.0
        Re-publication after evolution = increment minor version
        """
        arch_content = archetype.get("archetype", archetype)
        arch_name = arch_content.get("name", "unnamed")
        innovator_id = str(innovator.get("_id", innovator.get("innovator_id", "")))

        # Check for existing versions
        existing = self.db.db.generated_archetypes.find_one(
            {
                "archetype_result.archetype.name": arch_name,
                "innovator_id": innovator_id,
                "published": True,
            },
            sort=[("archetype_result.version.major", -1), ("archetype_result.version.minor", -1)]
        )

        if existing:
            existing_result = existing.get("archetype_result", {})
            prev_version = existing_result.get("version", {})
            prev_major = prev_version.get("major", 1) if isinstance(prev_version, dict) else 1
            prev_minor = prev_version.get("minor", 0) if isinstance(prev_version, dict) else 0
            archetype["version"] = {"major": prev_major, "minor": prev_minor + 1}
        else:
            archetype["version"] = {"major": 1, "minor": 0}

        archetype["version_string"] = f"{archetype['version']['major']}.{archetype['version']['minor']}"

        return archetype

    def _generate_attribution(self, innovator: Dict, review_session: Dict) -> Dict:
        """Generate attribution metadata crediting the innovator."""
        original_draft = review_session.get("original_draft", {})
        provenance = original_draft.get("provenance", original_draft.get("source", {}))

        created_at = review_session.get("created_at")
        if isinstance(created_at, datetime):
            discovery_date = created_at.isoformat()
        else:
            discovery_date = str(created_at) if created_at else datetime.now(timezone.utc).isoformat()

        return {
            "innovator_id": str(innovator.get("_id", innovator.get("innovator_id", ""))),
            "innovator_display_name": innovator.get("display_name", innovator.get("username", "Anonymous Innovator")),
            "source_pursuit_count": provenance.get("source_pursuit_count", provenance.get("pursuit_count", 0)),
            "discovery_date": discovery_date,
            "review_date": datetime.now(timezone.utc).isoformat(),
            "methodology_origin": "emergent",  # vs "authored" for hand-authored
        }

    def _update_review_session(self, review_session: Dict, archetype_id) -> None:
        """Update review session with publication details."""
        try:
            from bson import ObjectId
            session_oid = ObjectId(review_session.get("_id")) if review_session.get("_id") else None
        except Exception:
            session_oid = review_session.get("_id")

        if session_oid:
            now = datetime.now(timezone.utc)
            self.db.db.review_sessions.update_one(
                {"_id": session_oid},
                {"$set": {
                    "status": "APPROVED",
                    "publish_approved": True,
                    "publish_timestamp": now,
                    "published_archetype_id": str(archetype_id),
                    "completed_at": now,
                    "updated_at": now,
                }}
            )

    def _update_inference_result(self, inference_result_id: str) -> None:
        """Update inference result with publication status."""
        try:
            from bson import ObjectId
            result_oid = ObjectId(inference_result_id)
        except Exception:
            result_oid = inference_result_id

        self.db.db.inference_results.update_one(
            {"_id": result_oid},
            {"$set": {
                "innovator_reviewed": True,
                "published": True,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

    def _register_in_repository(self, archetype: Dict) -> None:
        """
        Register the published archetype in the Archetype Repository
        so it appears in the methodology selection interface.
        """
        arch_content = archetype.get("archetype", archetype)

        registry_entry = {
            "name": arch_content.get("name", "unnamed"),
            "display_name": arch_content.get("display_name", arch_content.get("name", "Unnamed")),
            "description": arch_content.get("description", ""),
            "source": "EMS",
            "version": archetype.get("version_string", "1.0"),
            "visibility": archetype.get("visibility", "PERSONAL"),
            "archetype_definition": archetype,
        }

        try:
            self.archetype_registry.register_archetype(registry_entry)
            logger.info(f"Archetype '{registry_entry['display_name']}' registered in repository")
        except Exception as e:
            logger.warning(f"Could not register archetype in repository: {e}")

    def _register_display_labels(self, archetype: Dict) -> None:
        """
        Register Display Labels for the new methodology's name
        so it can be translated in the UI.
        """
        arch_content = archetype.get("archetype", archetype)
        name = arch_content.get("name", "unnamed")
        display_name = arch_content.get("display_name", name)

        try:
            self.display_labels.register(
                category="methodology_archetype",
                key=name,
                display_value=display_name,
                icon="sparkles",
                description=arch_content.get("description", "")
            )
            logger.info(f"Display label registered for '{display_name}'")
        except Exception as e:
            logger.warning(f"Could not register display label: {e}")

    # =========================================================================
    # VISIBILITY MANAGEMENT
    # =========================================================================

    def update_visibility(self, archetype_id: str, new_visibility: str, innovator_id: str) -> bool:
        """
        Update the visibility of a published archetype.
        Only the creator can change visibility.
        Abstract Sovereignty: the innovator always controls sharing.

        Args:
            archetype_id: The archetype document ID
            new_visibility: New visibility level
            innovator_id: ID of the innovator making the request

        Returns:
            True if update was successful
        """
        try:
            from bson import ObjectId
            oid = ObjectId(archetype_id)
        except Exception:
            oid = archetype_id

        archetype_doc = self.db.db.generated_archetypes.find_one({"_id": oid})
        if not archetype_doc:
            raise ValueError("Archetype not found")

        archetype = archetype_doc.get("archetype_result", {})
        attribution = archetype.get("attribution", {})

        if str(attribution.get("innovator_id", "")) != str(innovator_id):
            raise PermissionError("Only the creator can change visibility")

        if new_visibility not in self.VISIBILITY_LEVELS:
            raise ValueError(f"Invalid visibility: {new_visibility}. Must be one of {self.VISIBILITY_LEVELS}")

        self.db.db.generated_archetypes.update_one(
            {"_id": oid},
            {"$set": {
                "archetype_result.visibility": new_visibility,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

        # If upgrading to IKF_SHARED, prepare for federation
        if new_visibility == "IKF_SHARED" and self.ikf_service:
            self._prepare_ikf_contribution(archetype)

        logger.info(f"Archetype visibility updated to {new_visibility}")
        return True

    # =========================================================================
    # IKF INTEGRATION
    # =========================================================================

    def _prepare_ikf_contribution(self, archetype: Dict) -> None:
        """
        Prepare an emergent methodology for IKF sharing.

        The archetype passes through the IKF generalization pipeline
        before federation, ensuring no proprietary information crosses
        organizational boundaries.
        """
        if not self.ikf_service:
            logger.warning("IKF service not available - skipping federation prep")
            return

        # Generalize the archetype for sharing
        generalized = self._generalize_for_ikf(archetype)

        arch_content = archetype.get("archetype", archetype)
        provenance = archetype.get("provenance", {})
        attribution = archetype.get("attribution", {})

        try:
            self.ikf_service.prepare_contribution({
                "package_type": "methodology_archetype",
                "content": generalized,
                "source_innovator_gii": attribution.get("innovator_id"),
                "visibility": "IKF_SHARED",
                "metadata": {
                    "phase_count": len(arch_content.get("phases", [])),
                    "confidence": provenance.get("confidence", {}).get("overall", 0),
                    "version": archetype.get("version_string", "1.0"),
                }
            })
            logger.info(f"Archetype prepared for IKF contribution")
        except Exception as e:
            logger.warning(f"Could not prepare IKF contribution: {e}")

    def _generalize_for_ikf(self, archetype: Dict) -> Dict:
        """
        Strip organization-specific details from the archetype
        before IKF contribution.

        Preserves: phase structure, activities, transition criteria, coaching config
        Removes: innovator name, pursuit IDs, organization references
        """
        arch_content = archetype.get("archetype", archetype)
        provenance = archetype.get("provenance", {})

        generalized = {
            "name": arch_content.get("name"),
            "display_name": arch_content.get("display_name"),
            "description": arch_content.get("description"),
            "transition_philosophy": arch_content.get("transition_philosophy"),
            "criteria_enforcement": arch_content.get("criteria_enforcement"),
            "backward_iteration": arch_content.get("backward_iteration"),
            "phases": arch_content.get("phases", []),
            "coaching_config": arch_content.get("coaching_config", {}),
            "provenance": {
                "source": "EMS",
                "version": archetype.get("version_string"),
                "confidence": provenance.get("confidence", {}),
                "source_pursuit_count": provenance.get("source_pursuit_count"),
                # Stripped: innovator_id, pursuit_ids, review_session_id
            }
        }

        return generalized

    # =========================================================================
    # EVOLUTION TRACKING
    # =========================================================================

    def check_evolution_opportunity(self, archetype_id: str, innovator_id: str) -> Dict:
        """
        Check if new pursuit data suggests the methodology should evolve.

        Called after pursuits using the published archetype are completed.
        If new patterns diverge from the published archetype, suggest
        a re-analysis and version increment.

        Args:
            archetype_id: The published archetype ID
            innovator_id: The innovator's ID

        Returns:
            Dict with eligibility status and reason
        """
        try:
            from bson import ObjectId
            oid = ObjectId(archetype_id)
        except Exception:
            oid = archetype_id

        archetype_doc = self.db.db.generated_archetypes.find_one({"_id": oid})
        if not archetype_doc:
            return {"eligible": False, "reason": "Archetype not found"}

        archetype = archetype_doc.get("archetype_result", {})
        arch_content = archetype.get("archetype", archetype)
        arch_name = arch_content.get("name", "")
        provenance = archetype.get("provenance", {})

        # Count pursuits using this archetype since publication
        published_at = provenance.get("published_at")
        query = {
            "methodology_archetype": arch_name,
            "owner_id": innovator_id,
            "current_state": {"$in": ["COMPLETED", "TERMINATED", "completed", "terminated"]}
        }

        if published_at:
            try:
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                query["created_at"] = {"$gte": pub_date}
            except Exception:
                pass

        pursuits_since = self.db.db.pursuits.count_documents(query)

        if pursuits_since < 3:
            return {
                "eligible": False,
                "reason": f"Not enough pursuits since publication ({pursuits_since}/3 required)",
                "pursuits_since_publication": pursuits_since,
                "required_pursuits": 3,
            }

        # TODO: Run pattern inference on new pursuits and compare to published archetype
        # For now, just indicate eligibility based on pursuit count

        return {
            "eligible": True,
            "reason": f"New pursuit data available ({pursuits_since} pursuits since publication)",
            "pursuits_since_publication": pursuits_since,
            "suggestion": "Consider re-analyzing to discover methodology evolution",
        }

    # =========================================================================
    # ARCHETYPE RETRIEVAL
    # =========================================================================

    def get_innovator_archetypes(self, innovator_id: str) -> list:
        """
        Get all archetypes published by a specific innovator.

        This is the primary method for the UI to list "My Methodologies".

        Args:
            innovator_id: The innovator's ID

        Returns:
            List of archetype documents with key fields flattened
        """
        cursor = self.db.db.generated_archetypes.find({
            "innovator_id": innovator_id,
            "published": True,
            "is_active": True,
        }).sort("created_at", -1)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Flatten key fields for UI convenience
            result = doc.get("archetype_result", {})
            arch_content = result.get("archetype", result)
            doc["archetype_id"] = doc["_id"]
            doc["methodology_name"] = arch_content.get("display_name", arch_content.get("name", "Unnamed"))
            doc["visibility"] = result.get("visibility", "PERSONAL")
            doc["version"] = result.get("version", {}).get("minor", 0) + 1 if isinstance(result.get("version"), dict) else 1
            doc["created_at"] = doc.get("created_at")
            results.append(doc)

        return results

    def get_published_archetypes(
        self,
        innovator_id: str,
        include_team: bool = False,
        include_org: bool = False
    ) -> list:
        """
        Get published archetypes visible to an innovator.

        Args:
            innovator_id: The innovator's ID
            include_team: Include team-visible archetypes
            include_org: Include organization-visible archetypes

        Returns:
            List of published archetype documents
        """
        visibility_levels = ["PERSONAL"]
        if include_team:
            visibility_levels.append("TEAM")
        if include_org:
            visibility_levels.append("ORGANIZATION")

        # Always include IKF_SHARED
        visibility_levels.append("IKF_SHARED")

        query = {
            "published": True,
            "$or": [
                {"innovator_id": innovator_id},
                {"archetype_result.visibility": {"$in": visibility_levels}}
            ]
        }

        cursor = self.db.db.generated_archetypes.find(query).sort("created_at", -1)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        return results

    def get_archetype_for_pursuit(self, archetype_name: str, innovator_id: str) -> Optional[Dict]:
        """
        Get a published archetype by name for use in a new pursuit.

        Args:
            archetype_name: The archetype's name/id
            innovator_id: The innovator creating the pursuit

        Returns:
            The archetype definition if accessible, None otherwise
        """
        # First check for innovator's own archetypes
        archetype_doc = self.db.db.generated_archetypes.find_one({
            "archetype_result.archetype.name": archetype_name,
            "innovator_id": innovator_id,
            "published": True,
            "is_active": True,
        })

        if archetype_doc:
            return archetype_doc.get("archetype_result")

        # Check for shared archetypes
        archetype_doc = self.db.db.generated_archetypes.find_one({
            "archetype_result.archetype.name": archetype_name,
            "published": True,
            "is_active": True,
            "archetype_result.visibility": {"$in": ["TEAM", "ORGANIZATION", "IKF_SHARED"]},
        })

        if archetype_doc:
            return archetype_doc.get("archetype_result")

        return None


# =============================================================================
# SINGLETON
# =============================================================================

_publisher_instance = None


def get_archetype_publisher() -> ArchetypePublisher:
    """Get or create the ArchetypePublisher singleton."""
    global _publisher_instance
    if _publisher_instance is None:
        _publisher_instance = ArchetypePublisher()
    return _publisher_instance
