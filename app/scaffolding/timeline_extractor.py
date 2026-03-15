"""
InDE MVP v3.10 - Timeline Extractor

Automatically extracts dates, deadlines, and milestones from user conversation.
Uses hybrid approach: regex quick patterns + LLM semantic extraction.

Extracted milestones are stored as temporal events for timeline visualization.
Milestones are extracted invisibly as the user talks - they never see
explicit date tracking or timeline terminology.

v3.9 Features:
- Quick pattern detection to avoid unnecessary LLM calls
- LLM-based semantic extraction for context understanding
- Supports multiple date formats and precision levels
- Duplicate detection to avoid re-extracting same milestones

v3.10 Features (Timeline Integrity):
- TD-001: Conflict detection before milestone storage
- TD-001: Milestone versioning with supersession tracking
- TD-005: Relative date context preservation
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from config import (
    DATE_QUICK_PATTERNS,
    MILESTONE_TYPES,
    TIMELINE_EXTRACTION_PROMPT,
    RESOLUTION_AUTO_MINOR_UPDATE
)
from .conflict_resolver import TemporalConflictResolver, ConflictSeverity


class TimelineExtractor:
    """
    Extracts timeline information from conversation.
    Milestones are extracted invisibly as user talks.
    """

    def __init__(self, llm_interface, database):
        """
        Initialize TimelineExtractor.

        Args:
            llm_interface: LLMInterface instance for Claude API calls
            database: Database instance for persistence
        """
        self.llm = llm_interface
        self.db = database
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in DATE_QUICK_PATTERNS
        ]
        # v3.10: Conflict resolver for milestone date conflicts
        self.conflict_resolver = TemporalConflictResolver(database)

    def extract_milestones(self, conversation_turn: str, pursuit_id: str,
                            user_id: str = None) -> List[Dict]:
        """
        Extract milestones/deadlines from conversation turn.

        Args:
            conversation_turn: The user's message text
            pursuit_id: ID of the current pursuit
            user_id: ID of the user (v3.11: for created_by_user_id tracking)

        Returns:
            List of milestone dicts with:
            - milestone_id, title, target_date, date_precision, milestone_type, confidence
        """
        print(f"[TimelineExtractor] Processing: {conversation_turn[:50]}...")

        # Quick pattern check - avoid LLM if no date mentions
        has_date_mention = self._quick_pattern_check(conversation_turn)
        if not has_date_mention:
            print("[TimelineExtractor] No date patterns detected, skipping LLM")
            return []

        print("[TimelineExtractor] Date pattern detected, proceeding with LLM extraction")

        # Get pursuit context
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            print(f"[TimelineExtractor] No pursuit found for ID: {pursuit_id}")
            return []

        # Get existing milestones to avoid duplicates
        existing = self._get_existing_milestones_summary(pursuit_id)

        # LLM extraction - returns dict with milestones, project_start_date, project_end_date
        try:
            extraction_result = self._llm_extract_milestones(
                conversation_turn,
                pursuit.get("title", "Unknown"),
                existing
            )
            extracted_milestones = extraction_result.get("milestones", [])
            project_start_date = extraction_result.get("project_start_date")
            project_end_date = extraction_result.get("project_end_date")

            print(f"[TimelineExtractor] LLM extracted {len(extracted_milestones)} milestones")
            if project_start_date:
                print(f"[TimelineExtractor] Project start date: {project_start_date}")
            if project_end_date:
                print(f"[TimelineExtractor] Project end date: {project_end_date}")

        except Exception as e:
            print(f"[TimelineExtractor] LLM extraction failed: {e}")
            return []

        # Update timeline with project dates (even if no milestones)
        if project_start_date or project_end_date:
            self._update_project_dates(pursuit_id, project_start_date, project_end_date)

        # Filter duplicates and store milestones with conflict detection
        stored_milestones = []
        pending_conflicts = []

        for milestone in extracted_milestones:
            # Check for duplicate
            if self._is_duplicate(pursuit_id, milestone):
                print(f"[TimelineExtractor] Skipping duplicate: {milestone.get('title')}")
                continue

            # v3.10: Check for conflicts before storing
            conflict_result = self.conflict_resolver.check(milestone, pursuit_id)

            if conflict_result.severity == ConflictSeverity.RETROGRADE:
                # Past date - store as completed milestone
                milestone["status"] = "completed"
                milestone_id = self._store_milestone(pursuit_id, milestone, user_id)
                milestone["milestone_id"] = milestone_id
                stored_milestones.append(milestone)
                print(f"[TimelineExtractor] Stored retrograde milestone as completed: {milestone.get('title')}")

            elif conflict_result.severity == ConflictSeverity.MAJOR:
                # Major conflict - hold pending user confirmation
                pending_conflicts.append({
                    "milestone": milestone,
                    "conflict_result": conflict_result
                })
                print(f"[TimelineExtractor] Major conflict detected for: {milestone.get('title')}")

            elif conflict_result.severity == ConflictSeverity.MINOR:
                # Minor conflict - supersede old milestone automatically
                if conflict_result.existing_milestone_id:
                    new_doc = self.conflict_resolver.supersede_milestone(
                        old_id=conflict_result.existing_milestone_id,
                        new_milestone_doc={
                            "pursuit_id": pursuit_id,
                            "created_by_user_id": user_id,  # v3.11: TD-014
                            **milestone
                        },
                        resolution_strategy=RESOLUTION_AUTO_MINOR_UPDATE
                    )
                    milestone["milestone_id"] = new_doc["milestone_id"]
                    milestone["coaching_note"] = conflict_result.coaching_prompt
                else:
                    milestone_id = self._store_milestone(pursuit_id, milestone, user_id)
                    milestone["milestone_id"] = milestone_id
                stored_milestones.append(milestone)
                print(f"[TimelineExtractor] Stored with minor conflict note: {milestone.get('title')}")

            else:
                # No conflict - store normally
                milestone_id = self._store_milestone(pursuit_id, milestone, user_id)
                milestone["milestone_id"] = milestone_id
                stored_milestones.append(milestone)

        if stored_milestones:
            print(f"[TimelineExtractor] Stored {len(stored_milestones)} new milestones")

            # v3.9: Update time allocation if release milestone detected
            self._update_timeline_from_milestones(pursuit_id, stored_milestones)

        # Return both stored milestones and pending conflicts
        return {
            "stored": stored_milestones,
            "pending_conflicts": pending_conflicts
        }

    def _quick_pattern_check(self, message: str) -> bool:
        """
        Quick regex check for date mentions.
        Avoids expensive LLM calls if no dates present.
        """
        for pattern in self._compiled_patterns:
            if pattern.search(message):
                return True
        return False

    def _get_existing_milestones_summary(self, pursuit_id: str) -> str:
        """Get summary of existing milestones for context."""
        try:
            milestones = self.db.get_milestones(pursuit_id, limit=20)
            if not milestones:
                return "No milestones recorded yet."

            summaries = []
            for m in milestones:
                date_str = m.get("target_date", m.get("date_expression", "unknown date"))
                summaries.append(f"- {m.get('title')}: {date_str}")

            return "\n".join(summaries)
        except Exception as e:
            print(f"[TimelineExtractor] Failed to get existing milestones: {e}")
            return "No milestones recorded yet."

    def _llm_extract_milestones(self, conversation_turn: str,
                                 pursuit_title: str, existing_milestones: str) -> Dict:
        """
        Use LLM to extract timeline info from the conversation turn.

        Returns:
            Dict with keys: milestones (list), project_start_date, project_end_date
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        prompt = TIMELINE_EXTRACTION_PROMPT.format(
            pursuit_title=pursuit_title,
            existing_milestones=existing_milestones,
            today_date=today,
            conversation_turn=conversation_turn
        )

        response = self.llm.call_llm(
            prompt=prompt,
            max_tokens=800,
            system="You are a timeline extractor. Respond only with valid JSON."
        )

        # Parse JSON response
        try:
            json_text = response.strip()
            # Clean markdown code blocks if present
            if json_text.startswith("```"):
                json_text = re.sub(r"```json?\s*", "", json_text)
                json_text = re.sub(r"```\s*$", "", json_text)

            result = json.loads(json_text)

            # Extract project dates
            project_start = result.get("project_start_date")
            project_end = result.get("project_end_date")

            milestones = result.get("milestones", [])
            if not isinstance(milestones, list):
                milestones = []

            # Validate and normalize each milestone
            valid_milestones = []
            for m in milestones:
                if self._validate_milestone(m):
                    normalized = self._normalize_milestone(m)
                    valid_milestones.append(normalized)

            return {
                "milestones": valid_milestones,
                "project_start_date": project_start,
                "project_end_date": project_end
            }

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[TimelineExtractor] Failed to parse LLM response: {e}")
            print(f"[TimelineExtractor] Raw response: {response[:200]}")
            return {"milestones": [], "project_start_date": None, "project_end_date": None}

    def _validate_milestone(self, milestone: Dict) -> bool:
        """Validate milestone has required fields and sufficient confidence."""
        if not isinstance(milestone, dict):
            return False

        # Must have title
        if not milestone.get("title"):
            return False

        # Must have date info (either target_date or date_expression)
        if not milestone.get("target_date") and not milestone.get("date_expression"):
            return False

        # Check confidence threshold
        confidence = milestone.get("confidence", 0)
        if confidence < 0.6:
            return False

        return True

    def _normalize_milestone(self, milestone: Dict) -> Dict:
        """Normalize milestone data structure."""
        # Ensure milestone_type is valid
        m_type = milestone.get("milestone_type", "other")
        if m_type not in MILESTONE_TYPES:
            m_type = "other"

        # Normalize date_precision
        precision = milestone.get("date_precision", "exact")
        if precision not in ["exact", "month", "quarter", "relative"]:
            precision = "exact" if milestone.get("target_date") else "relative"

        # Normalize phase
        phase = milestone.get("phase")
        if phase and phase not in ["VISION", "DE_RISK", "DEPLOY"]:
            phase = None

        return {
            "title": milestone.get("title", "")[:100],  # Limit title length
            "description": milestone.get("description", "")[:500],  # Limit description
            "target_date": milestone.get("target_date"),
            "date_expression": milestone.get("date_expression", ""),
            "date_precision": precision,
            "milestone_type": m_type,
            "phase": phase,
            "confidence": min(1.0, max(0.0, float(milestone.get("confidence", 0.7))))
        }

    def _is_duplicate(self, pursuit_id: str, milestone: Dict) -> bool:
        """Check if a similar milestone already exists."""
        try:
            existing = self.db.get_milestones(pursuit_id, limit=50)
            if not existing:
                return False

            new_title = milestone.get("title", "").lower().strip()
            new_date = milestone.get("target_date")

            for m in existing:
                existing_title = m.get("title", "").lower().strip()
                existing_date = m.get("target_date")

                # Check for similar title (fuzzy match)
                if self._titles_similar(new_title, existing_title):
                    # If dates are close or same, it's a duplicate
                    if new_date and existing_date:
                        if new_date == existing_date:
                            return True
                    elif not new_date and not existing_date:
                        # Both relative - check date_expression
                        if milestone.get("date_expression") == m.get("date_expression"):
                            return True

            return False
        except Exception:
            return False

    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be duplicates."""
        # Simple word overlap check
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0
        return similarity > 0.6

    def _store_milestone(self, pursuit_id: str, milestone: Dict,
                          user_id: str = None) -> str:
        """Store milestone to database.

        Args:
            pursuit_id: ID of the pursuit
            milestone: Milestone data dict
            user_id: ID of the user creating the milestone (v3.11: TD-014)
        """
        milestone_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat() + "Z"

        # Determine if this is a relative date requiring confirmation
        date_precision = milestone.get("date_precision", "exact")
        requires_recalculation = date_precision == "relative"

        record = {
            "milestone_id": milestone_id,
            "pursuit_id": pursuit_id,
            "title": milestone.get("title"),
            "description": milestone.get("description"),
            "target_date": milestone.get("target_date"),
            "date_expression": milestone.get("date_expression"),
            "date_precision": date_precision,
            "milestone_type": milestone.get("milestone_type"),
            "phase": milestone.get("phase"),
            "confidence": milestone.get("confidence"),
            "source": "conversation",
            "extracted_at": now,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            # v3.10: TD-001 Versioning fields
            "milestone_version": 1,
            "supersedes_milestone_id": None,
            "is_superseded": False,
            "conflict_resolution_strategy": None,
            # v3.10: TD-005 Relative date context fields
            "relative_resolution_method": milestone.get("relative_resolution_method"),
            "requires_recalculation": requires_recalculation,
            "recalculation_prompted_at": None,
            # v3.11: TD-014 Permission tracking
            "created_by_user_id": user_id
        }

        self.db.db.pursuit_milestones.insert_one(record)
        print(f"[TimelineExtractor] Stored milestone: {milestone_id} - {milestone.get('title')}")

        return milestone_id

    def get_milestones(self, pursuit_id: str, status: str = None) -> List[Dict]:
        """
        Get milestones for a pursuit.

        Args:
            pursuit_id: ID of the pursuit
            status: Optional filter by status (pending, at_risk, completed, missed)

        Returns:
            List of milestone dicts
        """
        return self.db.get_milestones(pursuit_id, status=status)

    def update_milestone_status(self, milestone_id: str, status: str,
                                 metadata: Dict = None) -> bool:
        """
        Update a milestone's status.

        Args:
            milestone_id: ID of the milestone
            status: New status (pending, at_risk, completed, missed)
            metadata: Optional additional metadata

        Returns:
            True if updated, False otherwise
        """
        return self.db.update_milestone_status(milestone_id, status, metadata)

    def _update_project_dates(self, pursuit_id: str, start_date: str = None,
                               end_date: str = None) -> None:
        """
        Update time allocation with project start and/or end dates.

        Args:
            pursuit_id: Pursuit ID
            start_date: Project start date (YYYY-MM-DD)
            end_date: Project end/completion date (YYYY-MM-DD)
        """
        if not start_date and not end_date:
            return

        print(f"[TimelineExtractor] Updating project dates - start: {start_date}, end: {end_date}")

        # Format dates to ISO 8601
        if start_date and "T" not in start_date:
            start_date = f"{start_date}T00:00:00Z"
        if end_date and "T" not in end_date:
            end_date = f"{end_date}T23:59:59Z"

        # Get existing allocation
        allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})
        now = datetime.now(timezone.utc).isoformat() + "Z"

        if allocation:
            # Update existing allocation
            updates = {"updated_at": now, "timeline_source": "conversation"}

            if start_date:
                updates["start_date"] = start_date
                updates["started_at"] = start_date  # Also set started_at for compatibility

            if end_date:
                updates["target_end"] = end_date
                updates["end_date"] = end_date  # Also set end_date for compatibility

            # Recalculate total_days if both dates are now known
            final_start = start_date or allocation.get("start_date") or allocation.get("started_at")
            final_end = end_date or allocation.get("target_end") or allocation.get("end_date")

            if final_start and final_end:
                try:
                    start_dt = datetime.fromisoformat(str(final_start).replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(str(final_end).replace("Z", "+00:00"))
                    new_total_days = (end_dt - start_dt).days
                    if new_total_days > 0:
                        updates["total_days"] = new_total_days
                        print(f"[TimelineExtractor] Calculated total_days: {new_total_days}")
                except (ValueError, TypeError) as e:
                    print(f"[TimelineExtractor] Date calculation error: {e}")

            self.db.db.time_allocations.update_one(
                {"pursuit_id": pursuit_id},
                {"$set": updates}
            )
            print(f"[TimelineExtractor] Updated allocation with project dates")

        else:
            # Create new allocation with these dates
            pursuit = self.db.get_pursuit(pursuit_id)
            default_start = pursuit.get("created_at") if pursuit else now

            final_start = start_date or default_start
            final_end = end_date

            # Calculate total_days
            total_days = 90  # Default
            if final_start and final_end:
                try:
                    start_dt = datetime.fromisoformat(str(final_start).replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(str(final_end).replace("Z", "+00:00"))
                    new_total_days = (end_dt - start_dt).days
                    if new_total_days > 0:
                        total_days = new_total_days
                except (ValueError, TypeError):
                    pass

            new_allocation = {
                "pursuit_id": pursuit_id,
                "start_date": final_start,
                "started_at": final_start,
                "target_end": final_end,
                "end_date": final_end,
                "total_days": total_days,
                "phases": {
                    "VISION": {"percent": 15, "days": int(total_days * 0.15), "status": "NOT_STARTED"},
                    "DE_RISK": {"percent": 35, "days": int(total_days * 0.35), "status": "NOT_STARTED"},
                    "DEPLOY": {"percent": 40, "days": int(total_days * 0.40), "status": "NOT_STARTED"},
                    "BUFFER": {"percent": 10, "days": int(total_days * 0.10)}
                },
                "created_at": now,
                "updated_at": now,
                "timeline_source": "conversation",
                # v3.10: TD-002 - Track if target_end is computed from milestone
                "is_computed": False,
                "computed_source_milestone_id": None
            }
            self.db.db.time_allocations.insert_one(new_allocation)
            print(f"[TimelineExtractor] Created new allocation with project dates")

    def _update_timeline_from_milestones(self, pursuit_id: str,
                                          milestones: List[Dict]) -> None:
        """
        Update time allocation based on extracted milestones.

        When a "release" type milestone is detected with an exact date,
        update the timeline's target_end date to match.
        """
        # Find release milestone with exact date
        release_milestone = None
        for m in milestones:
            m_type = m.get("milestone_type", "")
            precision = m.get("date_precision", "")
            target_date = m.get("target_date")

            # Prioritize release milestones with exact dates
            if m_type == "release" and target_date:
                release_milestone = m
                break
            # Fall back to any milestone with high confidence and exact date
            elif target_date and precision == "exact" and m.get("confidence", 0) >= 0.8:
                if not release_milestone:
                    release_milestone = m

        if not release_milestone:
            print("[TimelineExtractor] No release milestone to update timeline")
            return

        target_date = release_milestone.get("target_date")
        if not target_date:
            return

        # Ensure ISO format with time component
        if "T" not in target_date:
            target_date = f"{target_date}T23:59:59Z"
        if not target_date.endswith("Z") and "+" not in target_date:
            target_date += "Z"

        print(f"[TimelineExtractor] Updating timeline target_end to: {target_date}")

        # Get existing allocation
        allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})

        if allocation:
            # Update existing allocation with target_end
            now = datetime.now(timezone.utc).isoformat() + "Z"

            # Calculate new total_days if we have a start date
            start_date = allocation.get("start_date") or allocation.get("created_at")
            total_days = allocation.get("total_days", 90)

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(str(start_date).replace("Z", "+00:00"))
                    target_dt = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                    new_total_days = (target_dt - start_dt).days
                    if new_total_days > 0:
                        total_days = new_total_days
                except (ValueError, TypeError) as e:
                    print(f"[TimelineExtractor] Date calculation error: {e}")

            self.db.db.time_allocations.update_one(
                {"pursuit_id": pursuit_id},
                {"$set": {
                    "target_end": target_date,
                    "total_days": total_days,
                    "updated_at": now,
                    "timeline_source": "conversation"
                }}
            )
            print(f"[TimelineExtractor] Updated allocation with target_end and total_days={total_days}")
        else:
            # Create new allocation with target_end
            pursuit = self.db.get_pursuit(pursuit_id)
            start_date = pursuit.get("created_at") if pursuit else datetime.now(timezone.utc).isoformat() + "Z"

            # Calculate total_days from start to target
            total_days = 90  # Default
            try:
                start_dt = datetime.fromisoformat(str(start_date).replace("Z", "+00:00"))
                target_dt = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
                new_total_days = (target_dt - start_dt).days
                if new_total_days > 0:
                    total_days = new_total_days
            except (ValueError, TypeError):
                pass

            now = datetime.now(timezone.utc).isoformat() + "Z"
            new_allocation = {
                "pursuit_id": pursuit_id,
                "start_date": start_date,
                "target_end": target_date,
                "total_days": total_days,
                "phases": {
                    "VISION": {"percent": 15, "days": int(total_days * 0.15), "status": "NOT_STARTED"},
                    "DE_RISK": {"percent": 35, "days": int(total_days * 0.35), "status": "NOT_STARTED"},
                    "DEPLOY": {"percent": 40, "days": int(total_days * 0.40), "status": "NOT_STARTED"},
                    "BUFFER": {"percent": 10, "days": int(total_days * 0.10)}
                },
                "created_at": now,
                "updated_at": now,
                "timeline_source": "conversation"
            }
            self.db.db.time_allocations.insert_one(new_allocation)
            print(f"[TimelineExtractor] Created new allocation with target_end={target_date}")
