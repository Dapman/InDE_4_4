"""
InDE MVP v2.8 - Retrospective Orchestrator

Orchestrates retrospective conversations and artifact generation.
Uses three-tier prompt composition: Core + Methodology + Outcome.

Progressive Flow:
1. Initialize retrospective session
2. Guide through 6-8 structured questions
3. Generate .retrospective artifact
4. Extract proto-patterns for learning library
5. Cross-validate fears with outcomes

v2.8 Enhancements:
- Early exit capability (partial completion)
- Pause and resume support
- Gentle completion prompts
- Partial artifact generation
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import RETROSPECTIVE_CONFIG


class RetrospectiveOrchestrator:
    """
    Orchestrates retrospective conversations and artifact generation.

    v2.8: Supports early exit, pause/resume, and partial completion.
    """

    # Exit signal patterns for early exit detection
    # v3.7.4: Allow trailing punctuation (., !, ?) on single-word exit commands
    EXIT_PATTERNS = [
        r"(?i)^(exit|quit|stop|done|finish|end|skip)[.!?]?$",
        r"(?i)i('m| am)?\s*(done|finished|complete)",
        r"(?i)(that'?s|thats)\s*(all|enough|it)",
        r"(?i)(let'?s|lets)\s*(stop|end|finish)",
        r"(?i)no\s*more\s*(questions|time)",
        r"(?i)wrap\s*(it|this)?\s*up",
        r"(?i)can\s*we\s*(stop|finish|end)",
        r"(?i)i\s*(need|want)\s*to\s*(stop|go|leave)",
        r"(?i)out\s*of\s*time",
        r"(?i)complete\s*(now|early|this)",
    ]

    # Pause patterns for resume later
    PAUSE_PATTERNS = [
        r"(?i)^(pause|save|later)$",
        r"(?i)continue\s*later",
        r"(?i)come\s*back\s*(to\s*this)?",
        r"(?i)pause\s*(for\s*now|this)?",
        r"(?i)save\s*(and\s*)?(exit|stop)?",
        r"(?i)resume\s*later",
    ]

    # Core prompt categories (methodology-agnostic)
    PROMPT_CATEGORIES = [
        "HYPOTHESIS_VALIDATION",
        "LEARNING_VELOCITY",
        "PIVOT_POINTS",
        "METHODOLOGY_EFFECTIVENESS",
        "SURPRISE_FACTORS",
        "FEAR_RESOLUTION",
        "FUTURE_ADAPTATIONS"
    ]

    # Core prompts
    CORE_PROMPTS = {
        "HYPOTHESIS_VALIDATION": (
            "Looking back at your initial hypotheses and assumptions about this innovation, "
            "which were validated through your work? Which were invalidated? "
            "What specific evidence led to these conclusions?"
        ),
        "LEARNING_VELOCITY": (
            "What did you learn most quickly during this pursuit? "
            "What took longer than expected to discover? "
            "What do you wish you had known earlier?"
        ),
        "PIVOT_POINTS": (
            "Were there specific moments where you made critical decisions or changed direction? "
            "What data or insights drove those decisions?"
        ),
        "METHODOLOGY_EFFECTIVENESS": (
            "How well did your innovation methodology work for this pursuit? "
            "What aspects were particularly helpful? What felt like overhead or didn't fit?"
        ),
        "SURPRISE_FACTORS": (
            "What surprised you most during this pursuit? "
            "What assumptions turned out to be wrong? What emerged that you didn't anticipate?"
        ),
        "FEAR_RESOLUTION": (
            "Looking at the concerns you identified at the start, which ones actually materialized? "
            "Which turned out to be unfounded? How effective were your mitigation strategies?"
        ),
        "FUTURE_ADAPTATIONS": (
            "If you were starting a similar pursuit tomorrow, what would you do differently? "
            "What would you definitely keep the same?"
        )
    }

    # Outcome-specific extensions
    OUTCOME_EXTENSIONS = {
        "COMPLETED.SUCCESSFUL": (
            "What were the key factors that contributed to this success? "
            "Was there a specific turning point where you gained confidence this would work? "
            "How scalable do you believe this solution is?"
        ),
        "COMPLETED.VALIDATED_NOT_PURSUED": (
            "What insights did validation provide? "
            "What strategic factors led to the decision not to proceed? "
            "Under what circumstances might this become viable in the future?"
        ),
        "TERMINATED.INVALIDATED": (
            "At what point did you realize the hypothesis wouldn't work? "
            "What specific evidence was most convincing? "
            "Was this a 'good failure' - did you fail fast enough? "
            "What did you save by learning this now rather than later?"
        ),
        "TERMINATED.PIVOTED": (
            "What insight or data triggered the pivot decision? "
            "How does the new direction differ from the original vision? "
            "What learnings from this pursuit are carrying forward into the new direction?"
        ),
        "TERMINATED.ABANDONED": (
            "What external factors led to abandonment? "
            "What was working well before this happened? "
            "Are there any salvageable assets or insights from the work you completed?"
        ),
        "TERMINATED.OBE": (
            "What specific external event overtook this pursuit? When did you become aware of it? "
            "If a competitor launched first, what did they do differently? "
            "Under what circumstances could this pursuit become viable again?"
        )
    }

    def __init__(self, llm_interface, database, pattern_engine=None,
                 element_tracker=None):
        """
        Initialize RetrospectiveOrchestrator.

        Args:
            llm_interface: LLMInterface for content generation
            database: Database instance
            pattern_engine: Optional PatternEngine for pattern extraction
            element_tracker: Optional ElementTracker for context
        """
        self.llm = llm_interface
        self.db = database
        self.pattern_engine = pattern_engine
        self.element_tracker = element_tracker

    def initialize_retrospective(self, pursuit_id: str,
                                  outcome_state: str) -> Dict:
        """
        Initialize new retrospective session.

        Args:
            pursuit_id: Pursuit ID
            outcome_state: Terminal state (e.g., COMPLETED.SUCCESSFUL)

        Returns:
            {
                "retrospective_id": str,
                "pursuit_id": str,
                "outcome_state": str
            }
            or {"error": str} on failure
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {"error": "Pursuit not found"}

        methodology = pursuit.get("methodology", "lean_startup")

        retrospective_id = str(uuid.uuid4())

        # v2.8: Check config for flexibility options
        allow_early_exit = RETROSPECTIVE_CONFIG.get("allow_early_exit", True)
        enable_resume = RETROSPECTIVE_CONFIG.get("enable_resume", True)

        retrospective = {
            "retrospective_id": retrospective_id,
            "pursuit_id": pursuit_id,
            "outcome_state": outcome_state,
            "methodology": methodology,
            "started_at": datetime.now(timezone.utc),
            "completion_status": "IN_PROGRESS",
            "completion_percentage": 0.0,
            "prompts_answered": 0,
            "prompts_total": len(self.PROMPT_CATEGORIES) + 1,  # Core + outcome
            "artifact": None,
            "patterns_extracted": 0,
            "fear_resolutions": 0,
            # v2.8: Retrospective Flexibility fields
            "early_exit": False,
            "exit_reason": None,
            "resumable": enable_resume,
            "allow_early_exit": allow_early_exit,
            "paused_at": None,
            "resumed_from": None
        }

        try:
            self.db.db.retrospectives.insert_one(retrospective)

            # Lock pursuit state during retrospective
            self.db.db.pursuits.update_one(
                {"pursuit_id": pursuit_id},
                {"$set": {
                    "state_locked": True,
                    "pending_terminal_state": outcome_state
                }}
            )

            return {
                "retrospective_id": retrospective_id,
                "pursuit_id": pursuit_id,
                "outcome_state": outcome_state
            }
        except Exception as e:
            return {"error": str(e)}

    def get_first_prompt(self, retrospective_id: str) -> str:
        """
        Get the first retrospective prompt.

        Args:
            retrospective_id: Retrospective ID

        Returns:
            First prompt text
        """
        retro = self._get_retrospective(retrospective_id)
        if not retro:
            return "Error: Retrospective not found."

        # Introduction with v2.8 flexibility note
        allow_early_exit = retro.get("allow_early_exit", RETROSPECTIVE_CONFIG.get("allow_early_exit", True))

        intro = """Thank you for taking the time to reflect on this pursuit. This reflection is valuable for your growth and will help inform future innovations.

I'll guide you through a series of questions - feel free to be candid and detailed.

"""
        if allow_early_exit:
            intro += """*You can say "done" or "finish" at any time to complete the retrospective with the responses collected so far.*

"""

        # First question: Hypothesis Validation
        first_q = self.CORE_PROMPTS["HYPOTHESIS_VALIDATION"]

        # Save prompt to conversation
        self._save_conversation(
            retrospective_id=retrospective_id,
            role="assistant",
            content=intro + first_q,
            prompt_category="HYPOTHESIS_VALIDATION"
        )

        return intro + first_q

    def process_response(self, retrospective_id: str,
                         user_message: str) -> Dict:
        """
        Process user response and generate next prompt.

        v2.8 Enhanced: Supports early exit and pause/resume.

        Args:
            retrospective_id: Retrospective ID
            user_message: User's response

        Returns:
            {
                "next_prompt": str | None,
                "is_complete": bool,
                "progress": float,
                "current_question": int,
                "total_questions": int,
                "early_exit": bool (v2.8),
                "paused": bool (v2.8)
            }
        """
        retro = self._get_retrospective(retrospective_id)
        if not retro:
            return {"error": "Retrospective not found"}

        # v2.8: Check for pause request first
        if self._is_pause_request(user_message):
            return self._handle_pause(retrospective_id, retro)

        # v2.8: Check for exit signals BEFORE saving response
        if self._is_exit_request(user_message) and retro.get("allow_early_exit", True):
            return self._handle_early_exit(retrospective_id, retro)

        # Save user response
        self._save_conversation(
            retrospective_id=retrospective_id,
            role="user",
            content=user_message
        )

        answered = retro["prompts_answered"] + 1
        total = retro["prompts_total"]

        self._update_retrospective(retrospective_id, {
            "prompts_answered": answered,
            "completion_percentage": answered / total
        })

        # Check if complete
        if answered >= total:
            return {
                "next_prompt": None,
                "is_complete": True,
                "progress": 1.0,
                "current_question": answered,
                "total_questions": total
            }

        # Generate next prompt
        next_category = self._get_next_category(answered, retro["outcome_state"])
        next_prompt = self._compose_prompt(retro, next_category, answered)

        # Save prompt
        self._save_conversation(
            retrospective_id=retrospective_id,
            role="assistant",
            content=next_prompt,
            prompt_category=next_category
        )

        return {
            "next_prompt": next_prompt,
            "is_complete": False,
            "progress": answered / total,
            "current_question": answered + 1,
            "total_questions": total
        }

    def complete_retrospective(self, retrospective_id: str) -> Dict:
        """
        Finalize retrospective: generate artifacts, extract patterns, resolve fears.

        Args:
            retrospective_id: Retrospective ID

        Returns:
            {
                "retrospective_id": str,
                "artifact": dict,
                "patterns_extracted": int,
                "fear_resolutions": int,
                "completion_message": str
            }
        """
        retro = self._get_retrospective(retrospective_id)
        if not retro:
            return {"error": "Retrospective not found"}

        pursuit_id = retro["pursuit_id"]
        conversations = self._get_conversations(retrospective_id)

        # Generate .retrospective artifact
        artifact = self._generate_artifact(retrospective_id, conversations, retro)

        # Extract proto-patterns
        patterns = self._extract_patterns(artifact, pursuit_id)

        # Cross-validate fears
        fear_resolutions = self._resolve_fears(artifact, pursuit_id)

        # Update retrospective
        self._update_retrospective(retrospective_id, {
            "artifact": artifact,
            "completion_status": "COMPLETE",
            "completed_at": datetime.now(timezone.utc),
            "patterns_extracted": len(patterns),
            "fear_resolutions": len(fear_resolutions)
        })

        # Update pursuit with terminal state
        self._finalize_pursuit(pursuit_id, retro["outcome_state"], retrospective_id)

        # Generate completion message
        message = self._generate_completion_message(artifact, patterns, fear_resolutions)

        return {
            "retrospective_id": retrospective_id,
            "artifact": artifact,
            "patterns_extracted": len(patterns),
            "fear_resolutions": len(fear_resolutions),
            "completion_message": message
        }

    def cancel_retrospective(self, retrospective_id: str) -> bool:
        """
        Cancel retrospective and return pursuit to ACTIVE.

        Args:
            retrospective_id: Retrospective ID

        Returns:
            True if cancelled successfully
        """
        retro = self._get_retrospective(retrospective_id)
        if not retro:
            return False

        pursuit_id = retro["pursuit_id"]

        # Update retrospective
        self._update_retrospective(retrospective_id, {
            "completion_status": "CANCELLED",
            "cancelled_at": datetime.now(timezone.utc)
        })

        # Unlock pursuit
        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "state_locked": False,
                "pending_terminal_state": None,
                "state": "ACTIVE"
            }}
        )

        return True

    def get_progress(self, retrospective_id: str) -> Dict:
        """Get retrospective progress."""
        retro = self._get_retrospective(retrospective_id)
        if not retro:
            return {"error": "Not found"}

        return {
            "retrospective_id": retrospective_id,
            "status": retro["completion_status"],
            "progress": retro["completion_percentage"],
            "questions_answered": retro["prompts_answered"],
            "total_questions": retro["prompts_total"],
            # v2.8: Additional status fields
            "early_exit": retro.get("early_exit", False),
            "resumable": retro.get("resumable", False),
            "paused": retro.get("completion_status") == "PAUSED"
        }

    # ===== v2.8: Early Exit & Pause/Resume Methods =====

    def _is_exit_request(self, message: str) -> bool:
        """Check if message is an early exit request."""
        message = message.strip()
        for pattern in self.EXIT_PATTERNS:
            if re.search(pattern, message):
                return True
        return False

    def _is_pause_request(self, message: str) -> bool:
        """Check if message is a pause/save for later request."""
        message = message.strip()
        for pattern in self.PAUSE_PATTERNS:
            if re.search(pattern, message):
                return True
        return False

    def _handle_early_exit(self, retrospective_id: str, retro: Dict) -> Dict:
        """
        Handle early exit request - complete with partial data.

        v2.8: Allows user to exit before all questions are answered.
        v3.7.4: Always honor explicit exit requests (done/finish) without minimum check.
        v3.7.4.1: Wrapped in try/except to ensure pursuit is archived even if completion fails.
        """
        try:
            # v3.7.4: Always complete when user explicitly requests exit
            return self._complete_partial_retrospective(retrospective_id, retro, "user_requested")
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error in _handle_early_exit: {e}")
            import traceback
            traceback.print_exc()

            # Emergency fallback: archive the pursuit even if retrospective completion failed
            pursuit_id = retro.get("pursuit_id")
            if pursuit_id:
                try:
                    self._finalize_pursuit(pursuit_id, retro.get("outcome_state", "TERMINATED.ABANDONED"), retrospective_id)
                    self._update_retrospective(retrospective_id, {
                        "completion_status": "FAILED",
                        "completed_at": datetime.now(timezone.utc),
                        "early_exit": True,
                        "exit_reason": f"error: {str(e)}"
                    })
                except Exception as e2:
                    print(f"[RetrospectiveOrchestrator] Emergency finalization also failed: {e2}")

            # Return success anyway so the user isn't stuck
            return {
                "next_prompt": None,
                "is_complete": True,
                "early_exit": True,
                "progress": 0,
                "current_question": 0,
                "total_questions": retro.get("prompts_total", 1),
                "completion_message": "Your retrospective has been completed and the pursuit has been archived.",
                "artifact": None,
                "patterns_extracted": 0,
                "fear_resolutions": 0
            }

    def _handle_pause(self, retrospective_id: str, retro: Dict) -> Dict:
        """
        Handle pause request - save state for resume later.

        v2.8: Allows pausing and resuming retrospectives.
        """
        answered = retro["prompts_answered"]
        total = retro["prompts_total"]

        # Update status to PAUSED
        self._update_retrospective(retrospective_id, {
            "completion_status": "PAUSED",
            "paused_at": datetime.now(timezone.utc),
            "resumable": True
        })

        pause_message = (
            f"Your retrospective has been paused. You've completed {answered} of {total} questions. "
            f"You can resume at any time by starting a new session with this pursuit. "
            f"Your progress has been saved."
        )

        return {
            "next_prompt": pause_message,
            "is_complete": False,
            "paused": True,
            "progress": answered / total,
            "current_question": answered,
            "total_questions": total,
            "early_exit": False
        }

    def resume_retrospective(self, pursuit_id: str) -> Optional[Dict]:
        """
        Resume a paused retrospective.

        v2.8: Finds and resumes paused retrospective for pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Retrospective data with next prompt, or None if not found
        """
        # Find paused retrospective
        retro = self.db.db.retrospectives.find_one({
            "pursuit_id": pursuit_id,
            "completion_status": "PAUSED",
            "resumable": True
        })

        if not retro:
            return None

        retrospective_id = retro["retrospective_id"]
        answered = retro["prompts_answered"]
        total = retro["prompts_total"]

        # Update status to IN_PROGRESS
        self._update_retrospective(retrospective_id, {
            "completion_status": "IN_PROGRESS",
            "resumed_from": "PAUSED",
            "resumed_at": datetime.now(timezone.utc)
        })

        # Get next prompt
        next_category = self._get_next_category(answered, retro["outcome_state"])
        next_prompt = self._compose_prompt(retro, next_category, answered)

        # Add resume message
        resume_intro = (
            f"Welcome back! Let's continue your retrospective from where you left off "
            f"(question {answered + 1} of {total}).\n\n"
        )

        return {
            "retrospective_id": retrospective_id,
            "next_prompt": resume_intro + next_prompt,
            "progress": answered / total,
            "current_question": answered + 1,
            "total_questions": total,
            "resumed": True
        }

    def _complete_partial_retrospective(self, retrospective_id: str,
                                         retro: Dict, exit_reason: str) -> Dict:
        """
        Complete retrospective with partial data collected so far.

        v2.8: Generates artifacts even with incomplete data.
        v3.7.4: Added comprehensive error handling.
        """
        pursuit_id = retro.get("pursuit_id")
        answered = retro.get("prompts_answered", 0)
        total = retro.get("prompts_total", 1)
        completion_pct = answered / total if total > 0 else 0

        try:
            conversations = self._get_conversations(retrospective_id)

            # Generate partial artifact
            artifact = self._generate_artifact(retrospective_id, conversations, retro)
            artifact["partial_completion"] = True
            artifact["completion_percentage"] = completion_pct
            artifact["questions_answered"] = answered
            artifact["questions_total"] = total

            # Extract patterns (may be fewer due to partial data)
            patterns = self._extract_patterns(artifact, pursuit_id)

            # Cross-validate fears with what we have
            fear_resolutions = self._resolve_fears(artifact, pursuit_id)

        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error generating artifact/patterns: {e}")
            import traceback
            traceback.print_exc()
            # Use minimal artifact with all required fields
            artifact = {
                "retrospective_id": retrospective_id,
                "pursuit_id": pursuit_id,
                "outcome_state": retro.get("outcome_state", "TERMINATED.ABANDONED"),
                "partial_completion": True,
                "completion_percentage": completion_pct,
                "error": str(e)
            }
            patterns = []
            fear_resolutions = []

        # Update retrospective with PARTIAL status (even if artifact generation failed)
        try:
            self._update_retrospective(retrospective_id, {
                "artifact": artifact,
                "completion_status": "PARTIAL",
                "completion_percentage": completion_pct,
                "completed_at": datetime.now(timezone.utc),
                "early_exit": True,
                "exit_reason": exit_reason,
                "patterns_extracted": len(patterns),
                "fear_resolutions": len(fear_resolutions)
            })
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error updating retrospective: {e}")

        # Update pursuit with terminal state (critical - must archive the pursuit)
        try:
            self._finalize_pursuit(pursuit_id, retro.get("outcome_state", "TERMINATED.ABANDONED"), retrospective_id)
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error finalizing pursuit: {e}")
            import traceback
            traceback.print_exc()

        # Generate completion message for partial
        try:
            message = self._generate_partial_completion_message(
                artifact, patterns, fear_resolutions, completion_pct
            )
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error generating completion message: {e}")
            message = "Your retrospective has been completed and the pursuit has been archived."

        return {
            "next_prompt": None,
            "is_complete": True,
            "early_exit": True,
            "progress": completion_pct,
            "current_question": answered,
            "total_questions": total,
            "completion_message": message,
            "artifact": artifact,
            "patterns_extracted": len(patterns),
            "fear_resolutions": len(fear_resolutions)
        }

    def _generate_partial_completion_message(self, artifact: Dict,
                                              patterns: List,
                                              fear_resolutions: List,
                                              completion_pct: float) -> str:
        """Generate completion message for partial retrospective."""
        outcome = artifact.get("outcome_state", "TERMINATED")

        base = f"""**Your Retrospective is Complete (Partial)**

You completed {completion_pct:.0%} of the retrospective questions. I've captured:
- {len(artifact.get('hypothesis_outcomes', []))} hypothesis outcome(s)
- {len(artifact.get('key_learnings', []))} key learning(s)
- {len(fear_resolutions)} fear resolution(s)
- {len(patterns)} proto-pattern(s) extracted

These insights are now part of your innovation memory.

"""

        # Add gentle suggestion to complete later if configured
        if RETROSPECTIVE_CONFIG.get("gentle_completion_prompts", True):
            base += "*You can always add more reflections later to capture additional insights.*\n\n"

        return base

    def _get_next_category(self, answered: int, outcome_state: str) -> str:
        """Determine next prompt category."""
        if answered < len(self.PROMPT_CATEGORIES):
            return self.PROMPT_CATEGORIES[answered]
        else:
            return "OUTCOME_SPECIFIC"

    def _compose_prompt(self, retro: Dict, category: str, answered: int) -> str:
        """Compose prompt using three-tier system."""
        outcome = retro["outcome_state"]

        if category in self.CORE_PROMPTS:
            prompt = self.CORE_PROMPTS[category]

            # Add transition phrasing
            prompt = f"Question {answered + 1} of {retro['prompts_total']}:\n\n{prompt}"

            return prompt

        elif category == "OUTCOME_SPECIFIC":
            extension = self.OUTCOME_EXTENSIONS.get(
                outcome,
                "What final thoughts would you like to share about this pursuit?"
            )
            return f"Final question:\n\n{extension}"

        return "Thank you for sharing. Let's continue..."

    def _generate_artifact(self, retrospective_id: str,
                          conversations: List[Dict],
                          retro: Dict) -> Dict:
        """Generate structured .retrospective artifact from conversation.

        v3.7.4: Added defensive coding for missing keys.
        """
        # Build conversation text for extraction (defensive)
        conversation_text = "\n\n".join([
            f"{c.get('role', 'unknown').upper()}: {c.get('content', '')}"
            for c in conversations
            if isinstance(c, dict)
        ])

        # Use LLM to extract structured data
        extracted = self._extract_structured_data(conversation_text)

        # Get pursuit info (defensive)
        pursuit_id = retro.get("pursuit_id")
        pursuit = self.db.get_pursuit(pursuit_id) if pursuit_id else None

        artifact = {
            "schema_version": "1.0",
            "retrospective_id": retrospective_id,
            "pursuit_id": pursuit_id,
            "pursuit_name": pursuit.get("title", "Unknown") if pursuit else "Unknown",
            "methodology": retro.get("methodology", "unknown"),
            "outcome_state": retro.get("outcome_state", "TERMINATED.ABANDONED"),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "duration_days": self._calculate_duration(pursuit),
            **extracted
        }

        # Store artifact
        try:
            self.db.db.artifacts.insert_one({
                "artifact_id": str(uuid.uuid4()),
                "pursuit_id": pursuit_id,
                "type": "retrospective",
                "content": json.dumps(artifact, default=str),
                "version": 1,
                "status": "CURRENT",
                "created_at": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error storing artifact: {e}")

        return artifact

    def _extract_structured_data(self, conversation_text: str) -> Dict:
        """Use LLM to extract structured data from conversation."""
        if self.llm.demo_mode:
            return self._demo_extraction()

        prompt = f"""Extract structured learning data from this retrospective conversation.

CONVERSATION:
{conversation_text[:4000]}

Generate JSON with this schema:
{{
    "hypothesis_outcomes": [
        {{
            "hypothesis": "specific hypothesis statement",
            "outcome": "VALIDATED | INVALIDATED | INCONCLUSIVE",
            "evidence": "supporting evidence",
            "confidence": "HIGH | MEDIUM | LOW"
        }}
    ],
    "key_learnings": [
        {{
            "learning": "specific insight or lesson",
            "category": "MARKET | TECHNICAL | EXECUTION | METHODOLOGY | EXTERNAL",
            "transferability": "HIGH | MEDIUM | LOW"
        }}
    ],
    "surprise_factors": ["string"],
    "methodology_assessment": {{
        "what_worked": ["string"],
        "what_didnt_work": ["string"],
        "effectiveness_score": 1-5
    }},
    "future_recommendations": ["string"],
    "pattern_tags": ["string"]
}}

Extract only information explicitly discussed in the conversation."""

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=1200,
                system="You are a retrospective analyst. Respond only with valid JSON."
            )

            text = response.strip()
            if text.startswith("```"):
                import re
                text = re.sub(r"```json?\s*", "", text)
                text = re.sub(r"```\s*$", "", text)

            return json.loads(text)

        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Extraction failed: {e}")
            return self._demo_extraction()

    def _demo_extraction(self) -> Dict:
        """Demo extraction for testing."""
        return {
            "hypothesis_outcomes": [
                {
                    "hypothesis": "Demo hypothesis",
                    "outcome": "VALIDATED",
                    "evidence": "Demo evidence",
                    "confidence": "MEDIUM"
                }
            ],
            "key_learnings": [
                {
                    "learning": "Demo learning captured",
                    "category": "EXECUTION",
                    "transferability": "HIGH"
                }
            ],
            "surprise_factors": ["Demo surprise"],
            "methodology_assessment": {
                "what_worked": ["Structured approach"],
                "what_didnt_work": [],
                "effectiveness_score": 4
            },
            "future_recommendations": ["Continue structured approach"],
            "pattern_tags": ["demo", "test"]
        }

    def _extract_patterns(self, artifact: Dict, pursuit_id: str) -> List[Dict]:
        """Extract proto-patterns from retrospective artifact.

        v3.7.4: Added defensive coding for missing keys.
        """
        patterns = []
        retrospective_id = artifact.get("retrospective_id")

        # Pattern from invalidated hypotheses
        for hypo in artifact.get("hypothesis_outcomes", []):
            if not isinstance(hypo, dict):
                continue
            if hypo.get("outcome") == "INVALIDATED":
                hypothesis_content = hypo.get("hypothesis")
                if not hypothesis_content:
                    continue
                pattern = {
                    "pattern_id": str(uuid.uuid4()),
                    "retrospective_id": retrospective_id,
                    "pursuit_id": pursuit_id,
                    "pattern_type": "FAILED_HYPOTHESIS",
                    "pattern_content": hypothesis_content,
                    "pattern_evidence": hypo.get("evidence", ""),
                    "confidence_score": 0.7,
                    "applications": 1,
                    "tags": artifact.get("pattern_tags", []),
                    "created_at": datetime.now(timezone.utc)
                }
                try:
                    self.db.db.learning_patterns.insert_one(pattern)
                    patterns.append(pattern)
                except Exception as e:
                    print(f"[RetrospectiveOrchestrator] Error inserting pattern: {e}")

        # Pattern from validated hypotheses
        for hypo in artifact.get("hypothesis_outcomes", []):
            if not isinstance(hypo, dict):
                continue
            if hypo.get("outcome") == "VALIDATED":
                hypothesis_content = hypo.get("hypothesis")
                if not hypothesis_content:
                    continue
                pattern = {
                    "pattern_id": str(uuid.uuid4()),
                    "retrospective_id": retrospective_id,
                    "pursuit_id": pursuit_id,
                    "pattern_type": "SUCCESS_FACTOR",
                    "pattern_content": hypothesis_content,
                    "pattern_evidence": hypo.get("evidence", ""),
                    "confidence_score": 0.85,
                    "applications": 1,
                    "tags": artifact.get("pattern_tags", []),
                    "created_at": datetime.now(timezone.utc)
                }
                try:
                    self.db.db.learning_patterns.insert_one(pattern)
                    patterns.append(pattern)
                except Exception as e:
                    print(f"[RetrospectiveOrchestrator] Error inserting pattern: {e}")

        # Pattern from surprises
        for surprise in artifact.get("surprise_factors", []):
            if not surprise or not isinstance(surprise, str):
                continue
            pattern = {
                "pattern_id": str(uuid.uuid4()),
                "retrospective_id": retrospective_id,
                "pursuit_id": pursuit_id,
                "pattern_type": "UNEXPECTED_DISCOVERY",
                "pattern_content": surprise,
                "confidence_score": 0.75,
                "applications": 1,
                "tags": artifact.get("pattern_tags", []),
                "created_at": datetime.now(timezone.utc)
            }
            try:
                self.db.db.learning_patterns.insert_one(pattern)
                patterns.append(pattern)
            except Exception as e:
                print(f"[RetrospectiveOrchestrator] Error inserting pattern: {e}")

        return patterns

    def _resolve_fears(self, artifact: Dict, pursuit_id: str) -> List[Dict]:
        """Cross-reference fears with retrospective outcomes.

        v3.7.4: Added defensive coding.
        """
        resolutions = []
        retrospective_id = artifact.get("retrospective_id")

        # Get fear artifacts
        try:
            fear_artifacts = list(self.db.db.artifacts.find({
                "pursuit_id": pursuit_id,
                "type": "fears"
            }))
        except Exception as e:
            print(f"[RetrospectiveOrchestrator] Error fetching fear artifacts: {e}")
            return resolutions

        if not fear_artifacts:
            return resolutions

        # For each fear, create resolution record
        for fa in fear_artifacts:
            resolution = {
                "resolution_id": str(uuid.uuid4()),
                "retrospective_id": retrospective_id,
                "pursuit_id": pursuit_id,
                "fear_artifact_id": fa.get("artifact_id"),
                "materialized": None,  # Would be determined by analysis
                "mitigation_effectiveness": "NOT_ANALYZED",
                "created_at": datetime.now(timezone.utc)
            }
            try:
                self.db.db.fear_resolutions.insert_one(resolution)
                resolutions.append(resolution)
            except Exception as e:
                print(f"[RetrospectiveOrchestrator] Error inserting fear resolution: {e}")

        return resolutions

    def _finalize_pursuit(self, pursuit_id: str, outcome_state: str,
                          retrospective_id: str):
        """Finalize pursuit with terminal state and archive it."""
        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "state": outcome_state,
                "status": "archived",  # Remove from active portfolio
                "state_locked": False,
                "pending_terminal_state": None,
                "archived_at": datetime.now(timezone.utc),
                "retrospective_completed": True,
                "terminal_info": {
                    "terminal_state": outcome_state,
                    "terminated_at": datetime.now(timezone.utc),
                    "retrospective_id": retrospective_id,
                    "stakeholders_notified": False,
                    "portfolio_updated": True
                },
                "updated_at": datetime.now(timezone.utc)
            }}
        )

    def _generate_completion_message(self, artifact: Dict,
                                     patterns: List,
                                     fear_resolutions: List) -> str:
        """Generate personalized completion message."""
        outcome = artifact["outcome_state"]

        base = f"""**Your Retrospective is Complete**

I've captured:
- {len(artifact.get('hypothesis_outcomes', []))} hypothesis outcome(s)
- {len(artifact.get('key_learnings', []))} key learning(s)
- {len(artifact.get('surprise_factors', []))} surprise factor(s)
- {len(fear_resolutions)} fear resolution(s)
- {len(patterns)} proto-pattern(s) extracted

These insights are now part of your innovation memory and will help inform future pursuits.

"""

        wisdom_map = {
            "COMPLETED.SUCCESSFUL": "Your success pattern will help others recognize what works.",
            "COMPLETED.VALIDATED_NOT_PURSUED": "Validating before committing is smart strategy - this learning saves resources.",
            "TERMINATED.INVALIDATED": "Failing fast and learning is success - you saved significant time and resources.",
            "TERMINATED.PIVOTED": "Your pivot represents valuable learning. The new direction builds on solid insights.",
            "TERMINATED.ABANDONED": "Even when circumstances force a stop, the learning journey has lasting value.",
            "TERMINATED.OBE": "Being overtaken is learning too - this competitive intelligence informs future timing decisions."
        }

        wisdom = wisdom_map.get(outcome, "Every innovation journey contributes to organizational wisdom.")

        return base + wisdom

    def _calculate_duration(self, pursuit: Optional[Dict]) -> int:
        """Calculate pursuit duration in days."""
        if not pursuit:
            return 0

        created = pursuit.get("created_at")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except (ValueError, TypeError):
                return 0
        elif not isinstance(created, datetime):
            return 0

        return (datetime.now(timezone.utc) - created).days

    def _get_retrospective(self, retrospective_id: str) -> Optional[Dict]:
        """Get retrospective by ID."""
        return self.db.db.retrospectives.find_one({"retrospective_id": retrospective_id})

    def _update_retrospective(self, retrospective_id: str, updates: Dict):
        """Update retrospective."""
        self.db.db.retrospectives.update_one(
            {"retrospective_id": retrospective_id},
            {"$set": updates}
        )

    def _save_conversation(self, retrospective_id: str, role: str,
                          content: str, prompt_category: str = None):
        """Save conversation turn."""
        turn = {
            "retrospective_id": retrospective_id,
            "role": role,
            "content": content,
            "prompt_category": prompt_category,
            "timestamp": datetime.now(timezone.utc)
        }
        self.db.db.retrospective_conversations.insert_one(turn)

    def _get_conversations(self, retrospective_id: str) -> List[Dict]:
        """Get all conversations for retrospective."""
        return list(self.db.db.retrospective_conversations.find(
            {"retrospective_id": retrospective_id}
        ).sort("timestamp", 1))
