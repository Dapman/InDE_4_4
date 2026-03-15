"""
InDE EMS v3.7.3 - Innovator Review Interface

Coaching-assisted methodology validation interface. The review interface is a
coaching conversation, not a static form. It guides the innovator through:

1. Phase-by-phase review - Validate inferred phases
2. Transition review - Confirm flow and iteration loops
3. Tool and artifact review - Identify essential tools
4. Comparison view - Compare against similar archetypes
5. Naming and description - Define methodology identity
6. Apply refinements - Transform draft into publishable archetype

The coach (ODICM in review mode) helps the innovator articulate principles,
validate inferences, and refine the methodology to match their actual practice.
"""

import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import re

logger = logging.getLogger("inde.ems.review_interface")


# =============================================================================
# REVIEW COACHING CONTEXT
# =============================================================================

REVIEW_COACHING_CONTEXT = """
You are helping an innovator review a methodology that was discovered from
their behavior across {pursuit_count} freeform pursuits. The Pattern Inference
Engine identified {phase_count} phases with {confidence_tier} overall confidence.

Your role in this review session:
- Present each inferred phase clearly, with its confidence level
- Ask the innovator to confirm, correct, or remove each element
- Help them articulate WHY they do things in this order
- Capture key principles they express
- Suggest names based on their descriptions
- Be honest about low-confidence elements — "This pattern appeared in
  some of your pursuits but not all. Is it part of your process, or
  was it situational?"

DO NOT:
- Assume the inference is correct — it's a hypothesis the innovator must validate
- Push the innovator to accept elements they don't recognize
- Reference methodology frameworks by name unless the innovator does first
- Skip low-confidence elements — they may be the most interesting discoveries

The draft archetype structure:
{draft_archetype_summary}
"""


# =============================================================================
# REVIEW SESSION MANAGER
# =============================================================================

class ReviewSessionManager:
    """
    Manages the methodology review session flow.

    The review progresses through phases:
    1. INITIATED - Session created, draft loaded
    2. REVIEWING_PHASES - Going through each phase
    3. REVIEWING_TRANSITIONS - Validating phase transitions
    4. REVIEWING_TOOLS - Confirming essential tools
    5. COMPARING - Comparing to similar archetypes
    6. NAMING - Setting name, description, principles
    7. FINALIZING - Applying refinements
    8. APPROVED/REJECTED/ABANDONED - Terminal states
    """

    REVIEW_STAGES = [
        "INITIATED",
        "REVIEWING_PHASES",
        "REVIEWING_TRANSITIONS",
        "REVIEWING_TOOLS",
        "COMPARING",
        "NAMING",
        "FINALIZING",
    ]

    def __init__(self, db=None, llm=None):
        """
        Args:
            db: Database instance. If None, uses singleton.
            llm: LLM interface for coaching conversations (optional)
        """
        if db is None:
            from core.database import db as singleton_db
            db = singleton_db
        self.db = db
        self.llm = llm

    def start_review_session(
        self,
        innovator_id: str,
        inference_result_id: str,
        draft_archetype: Dict
    ) -> Dict:
        """
        Start a new review session.

        Args:
            innovator_id: The innovator's ID
            inference_result_id: ID of the inference result being reviewed
            draft_archetype: The synthesized archetype to review

        Returns:
            Session info with initial coaching message
        """
        # Create the review session
        session_id = self.db.create_review_session(
            innovator_id=innovator_id,
            inference_result_id=inference_result_id,
            original_draft=draft_archetype
        )

        # Generate initial coaching context
        context = self._build_review_context(draft_archetype)

        # Generate opening message
        opening_message = self._generate_opening_message(draft_archetype, context)

        # Record the opening exchange
        self.db.add_coaching_exchange(
            session_id=session_id,
            role="coach",
            content=opening_message,
            context="session_opening",
            phase_reference=""
        )

        logger.info(f"Started review session {session_id} for innovator {innovator_id}")

        return {
            "session_id": session_id,
            "status": "INITIATED",
            "review_stage": "REVIEWING_PHASES",
            "current_phase_index": 0,
            "coaching_message": opening_message,
            "context": context,
        }

    def _build_review_context(self, draft_archetype: Dict) -> Dict:
        """Build context information for the review session."""
        phases = draft_archetype.get("archetype", {}).get("phases", [])
        confidence = draft_archetype.get("source", {}).get("confidence", 0)
        pursuit_count = draft_archetype.get("source", {}).get("pursuit_count", 0)

        # Determine confidence tier
        if confidence >= 0.8:
            confidence_tier = "high"
        elif confidence >= 0.6:
            confidence_tier = "moderate"
        else:
            confidence_tier = "low"

        # Summarize the draft archetype
        phase_summary = []
        for i, phase in enumerate(phases):
            phase_summary.append({
                "index": i,
                "name": phase.get("name", f"Phase {i+1}"),
                "activities": phase.get("activities", [])[:5],
                "universal_state": phase.get("universal_state", "UNKNOWN"),
            })

        return {
            "pursuit_count": pursuit_count,
            "phase_count": len(phases),
            "confidence_tier": confidence_tier,
            "confidence_score": confidence,
            "phases": phase_summary,
            "has_transitions": bool(draft_archetype.get("archetype", {}).get("transitions", [])),
        }

    def _generate_opening_message(self, draft_archetype: Dict, context: Dict) -> str:
        """Generate the opening coaching message."""
        phase_count = context["phase_count"]
        pursuit_count = context["pursuit_count"]
        confidence_tier = context["confidence_tier"]

        message = (
            f"I've analyzed your work across {pursuit_count} pursuits and discovered "
            f"what looks like a {phase_count}-phase process that you naturally follow. "
        )

        if confidence_tier == "high":
            message += (
                "I'm quite confident about this pattern - it appeared consistently "
                "across most of your pursuits. "
            )
        elif confidence_tier == "moderate":
            message += (
                "I have moderate confidence in this pattern - some elements were "
                "very consistent, others appeared in some pursuits but not all. "
            )
        else:
            message += (
                "I should be upfront: my confidence in this pattern is lower than I'd like. "
                "Some elements may be situational rather than core to your process. "
            )

        message += (
            "\n\nLet's walk through each phase together. For each one, I'll explain "
            "what I observed, and you tell me if it matches how you think about "
            "your process. Feel free to rename phases, add or remove activities, "
            "or tell me when I've got it wrong.\n\n"
            "**Ready to start with the first phase?**"
        )

        return message

    def process_innovator_response(
        self,
        session_id: str,
        innovator_message: str,
        current_stage: str,
        current_phase_index: int = 0
    ) -> Dict:
        """
        Process an innovator's response and generate the next coaching message.

        Args:
            session_id: The review session ID
            innovator_message: The innovator's response
            current_stage: Current review stage
            current_phase_index: Current phase being reviewed (if in REVIEWING_PHASES)

        Returns:
            Next coaching message and updated state
        """
        # Record the innovator's message
        self.db.add_coaching_exchange(
            session_id=session_id,
            role="innovator",
            content=innovator_message,
            context=current_stage,
            phase_reference=str(current_phase_index) if current_stage == "REVIEWING_PHASES" else ""
        )

        # Get session data
        session = self.db.get_review_session(session_id)
        if not session:
            return {"error": "Session not found"}

        draft = session.get("refined_archetype", session.get("original_draft", {}))
        phases = draft.get("archetype", {}).get("phases", [])

        # Process based on current stage
        if current_stage == "REVIEWING_PHASES":
            return self._process_phase_review(
                session_id, session, innovator_message, current_phase_index, phases
            )
        elif current_stage == "REVIEWING_TRANSITIONS":
            return self._process_transition_review(session_id, session, innovator_message)
        elif current_stage == "REVIEWING_TOOLS":
            return self._process_tool_review(session_id, session, innovator_message)
        elif current_stage == "COMPARING":
            return self._process_comparison_review(session_id, session, innovator_message)
        elif current_stage == "NAMING":
            return self._process_naming(session_id, session, innovator_message)
        elif current_stage == "FINALIZING":
            return self._process_finalization(session_id, session, innovator_message)
        else:
            return {
                "coaching_message": "I'm not sure where we are in the review. Let's restart from the phases.",
                "next_stage": "REVIEWING_PHASES",
                "current_phase_index": 0,
            }

    def _process_phase_review(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str,
        current_phase_index: int,
        phases: List[Dict]
    ) -> Dict:
        """Process a phase review response."""
        # Check for refinement actions in the response
        refinements = self._extract_refinements(innovator_message, current_phase_index, phases)

        # Record any refinements
        for refinement in refinements:
            self.db.add_refinement(
                session_id=session_id,
                action=refinement["action"],
                target=refinement["target"],
                before=refinement.get("before", ""),
                after=refinement.get("after", ""),
                innovator_rationale=refinement.get("rationale", "")
            )

        # Move to next phase or next stage
        if current_phase_index + 1 < len(phases):
            next_phase = phases[current_phase_index + 1]
            next_message = self._generate_phase_presentation(
                next_phase, current_phase_index + 1, len(phases)
            )

            # Record coach message
            self.db.add_coaching_exchange(
                session_id=session_id,
                role="coach",
                content=next_message,
                context="phase_review",
                phase_reference=str(current_phase_index + 1)
            )

            return {
                "coaching_message": next_message,
                "next_stage": "REVIEWING_PHASES",
                "current_phase_index": current_phase_index + 1,
                "refinements_applied": len(refinements),
            }
        else:
            # Done with phases, move to transitions
            transition_message = self._generate_transition_opening(session)

            self.db.add_coaching_exchange(
                session_id=session_id,
                role="coach",
                content=transition_message,
                context="transition_review",
                phase_reference=""
            )

            return {
                "coaching_message": transition_message,
                "next_stage": "REVIEWING_TRANSITIONS",
                "current_phase_index": 0,
                "refinements_applied": len(refinements),
            }

    def _generate_phase_presentation(
        self,
        phase: Dict,
        phase_index: int,
        total_phases: int
    ) -> str:
        """Generate the presentation message for a phase."""
        phase_name = phase.get("name", f"Phase {phase_index + 1}")
        activities = phase.get("activities", [])
        frequency = phase.get("frequency", 0)

        # Determine confidence language
        if frequency >= 0.8:
            confidence_text = "This appeared in most of your pursuits"
        elif frequency >= 0.5:
            confidence_text = "This appeared in about half of your pursuits"
        else:
            confidence_text = "This appeared in some of your pursuits, so I'm less certain about it"

        activities_text = ", ".join(activities[:5]) if activities else "various activities"

        message = (
            f"**Phase {phase_index + 1} of {total_phases}: \"{phase_name}\"**\n\n"
            f"I noticed you tend to focus on: {activities_text}.\n"
            f"{confidence_text}.\n\n"
            f"Does this match how you think about this part of your process? "
            f"Would you call it something different?"
        )

        return message

    def _generate_transition_opening(self, session: Dict) -> str:
        """Generate the opening message for transition review."""
        draft = session.get("refined_archetype", session.get("original_draft", {}))
        transitions = draft.get("archetype", {}).get("transitions", [])

        if not transitions:
            return (
                "Now let's look at how you move between phases. I didn't detect "
                "any specific triggers for your transitions - it seems like you "
                "move naturally from one phase to the next based on feel rather "
                "than specific criteria. Is that accurate?"
            )

        return (
            f"Now let's look at how you move between phases. I identified "
            f"{len(transitions)} typical transitions in your process. "
            f"For each one, I want to understand: is this a deliberate "
            f"checkpoint, or does it just happen naturally?"
        )

    def _process_transition_review(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str
    ) -> Dict:
        """Process a transition review response."""
        # For now, move to tool review after one exchange
        tool_message = self._generate_tool_review_opening(session)

        self.db.add_coaching_exchange(
            session_id=session_id,
            role="coach",
            content=tool_message,
            context="tool_review",
            phase_reference=""
        )

        return {
            "coaching_message": tool_message,
            "next_stage": "REVIEWING_TOOLS",
            "current_phase_index": 0,
        }

    def _generate_tool_review_opening(self, session: Dict) -> str:
        """Generate the opening message for tool review."""
        draft = session.get("refined_archetype", session.get("original_draft", {}))
        tools = draft.get("archetype", {}).get("tools", [])

        if not tools:
            return (
                "I noticed you used various InDE tools during your pursuits. "
                "Are there any specific tools that you consider essential to your process? "
                "For example, do you always start by telling your story, "
                "or always validate with experiments?"
            )

        tool_list = ", ".join(tools[:5])
        return (
            f"I noticed you frequently used these tools: {tool_list}. "
            f"Do you consider all of these essential to your process, "
            f"or are some optional depending on the situation?"
        )

    def _process_tool_review(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str
    ) -> Dict:
        """Process a tool review response."""
        # Move to comparison view
        comparison_message = self._generate_comparison_view(session)

        self.db.add_coaching_exchange(
            session_id=session_id,
            role="coach",
            content=comparison_message,
            context="comparison",
            phase_reference=""
        )

        return {
            "coaching_message": comparison_message,
            "next_stage": "COMPARING",
            "current_phase_index": 0,
        }

    def _generate_comparison_view(self, session: Dict) -> str:
        """Generate the comparison view message."""
        draft = session.get("original_draft", {})
        synthesis_metadata = draft.get("synthesis_metadata", {})
        similar_archetypes = synthesis_metadata.get("similar_archetypes", [])

        if not similar_archetypes:
            return (
                "Interestingly, your process doesn't closely match any of our "
                "existing methodology frameworks. This suggests you've developed "
                "a genuinely unique approach. That's valuable!\n\n"
                "**Let's move on to naming your methodology.**"
            )

        top_similar = similar_archetypes[0] if similar_archetypes else {}
        archetype_name = top_similar.get("display_name", "an existing methodology")
        similarity = top_similar.get("similarity", 0)

        if similarity > 0.7:
            comparison_text = (
                f"Your process has significant similarities to {archetype_name} - "
                f"about {int(similarity * 100)}% overlap. This is common and doesn't "
                f"diminish your approach. Many effective methodologies build on "
                f"established patterns while adding unique elements."
            )
        elif similarity > 0.5:
            comparison_text = (
                f"Your process has some similarities to {archetype_name}, "
                f"but with meaningful differences. You've adapted and personalized "
                f"the approach in ways that work for you."
            )
        else:
            comparison_text = (
                f"Your process is quite distinct from existing methodologies. "
                f"While there's a slight resemblance to {archetype_name}, "
                f"you've developed a largely unique approach."
            )

        return (
            f"{comparison_text}\n\n"
            f"**Now let's give your methodology a name and description.**"
        )

    def _process_comparison_review(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str
    ) -> Dict:
        """Process a comparison review response."""
        # Move to naming stage
        naming_message = self._generate_naming_prompt(session)

        self.db.add_coaching_exchange(
            session_id=session_id,
            role="coach",
            content=naming_message,
            context="naming",
            phase_reference=""
        )

        return {
            "coaching_message": naming_message,
            "next_stage": "NAMING",
            "current_phase_index": 0,
        }

    def _generate_naming_prompt(self, session: Dict) -> str:
        """Generate the naming prompt."""
        # Extract key themes from the review
        exchanges = session.get("coaching_exchanges", [])
        refinements = session.get("refinements", [])

        # Suggest names based on themes
        suggestions = self._generate_name_suggestions(session)

        suggestion_text = ""
        if suggestions:
            suggestion_text = f"\n\nSome ideas based on our discussion: {', '.join(suggestions)}"

        return (
            f"Now that we've reviewed your process, let's give it a name. "
            f"What captures the essence of how you approach innovation?{suggestion_text}\n\n"
            f"You can also write a brief description (1-3 sentences) and list "
            f"any key principles that guide your process."
        )

    def _generate_name_suggestions(self, session: Dict) -> List[str]:
        """Generate name suggestions based on the review."""
        # This would ideally use LLM to generate contextual suggestions
        # For now, return generic placeholders
        return [
            "The Discovery Loop",
            "Rapid Insight Framework",
            "Iterative Validation Method",
        ]

    def _process_naming(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str
    ) -> Dict:
        """Process naming input from the innovator."""
        # Extract name, description, principles from the message
        name = self._extract_methodology_name(innovator_message)
        description = self._extract_description(innovator_message)
        principles = self._extract_principles(innovator_message)

        # Update session with naming details
        self.db.set_methodology_details(
            session_id=session_id,
            name=name,
            description=description,
            key_principles=principles
        )

        # Generate finalization message
        finalization_message = (
            f"Great! Your methodology will be called **\"{name}\"**.\n\n"
            f"Here's a summary of what we've captured:\n"
            f"- **Name:** {name}\n"
            f"- **Description:** {description or '(to be completed)'}\n"
            f"- **Key Principles:** {', '.join(principles) if principles else '(none specified)'}\n\n"
            f"Are you ready to finalize and publish this methodology? "
            f"Once published, you'll be able to select it for future pursuits."
        )

        self.db.add_coaching_exchange(
            session_id=session_id,
            role="coach",
            content=finalization_message,
            context="finalization",
            phase_reference=""
        )

        return {
            "coaching_message": finalization_message,
            "next_stage": "FINALIZING",
            "current_phase_index": 0,
            "methodology_name": name,
            "methodology_description": description,
            "key_principles": principles,
        }

    def _extract_methodology_name(self, message: str) -> str:
        """Extract methodology name from innovator's message."""
        # Look for quoted text or "call it" patterns
        quoted = re.findall(r'"([^"]+)"', message)
        if quoted:
            return quoted[0]

        # Look for "call it X" patterns
        call_it = re.search(r'call it\s+([A-Za-z][A-Za-z\s]+)', message, re.IGNORECASE)
        if call_it:
            return call_it.group(1).strip()

        # Default to first capitalized phrase
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', message)
        if capitalized:
            return capitalized[0]

        return "My Innovation Process"

    def _extract_description(self, message: str) -> str:
        """Extract description from innovator's message."""
        # Look for description-like sentences
        sentences = message.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 30 and len(sentence.strip()) < 200:
                # Likely a description if it's a medium-length sentence
                if any(word in sentence.lower() for word in ['approach', 'process', 'method', 'way', 'how']):
                    return sentence.strip() + '.'

        return ""

    def _extract_principles(self, message: str) -> List[str]:
        """Extract key principles from innovator's message."""
        principles = []

        # Look for numbered lists
        numbered = re.findall(r'\d+[.)]\s*([^\n.]+)', message)
        if numbered:
            principles.extend([p.strip() for p in numbered[:5]])

        # Look for "principle" mentions
        principle_mentions = re.findall(r'principle[:\s]+([^\n.]+)', message, re.IGNORECASE)
        if principle_mentions:
            principles.extend([p.strip() for p in principle_mentions])

        return principles[:5]  # Limit to 5 principles

    def _process_finalization(
        self,
        session_id: str,
        session: Dict,
        innovator_message: str
    ) -> Dict:
        """Process finalization decision."""
        message_lower = innovator_message.lower()

        if any(word in message_lower for word in ['yes', 'publish', 'finalize', 'approve', 'ready', 'do it']):
            # Innovator approved
            return self._finalize_and_approve(session_id, session)
        elif any(word in message_lower for word in ['no', 'cancel', 'reject', 'stop', 'wait']):
            # Innovator rejected or wants to wait
            reject_message = (
                "No problem! Your methodology draft is saved and you can return "
                "to complete the review whenever you're ready. Just let me know "
                "when you'd like to continue."
            )

            self.db.update_review_session_status(session_id, "ABANDONED")

            return {
                "coaching_message": reject_message,
                "next_stage": "ABANDONED",
                "current_phase_index": 0,
            }
        else:
            # Ask for clarification
            return {
                "coaching_message": (
                    "I want to make sure I understand - are you ready to publish "
                    "this methodology, or would you like to make more changes first?"
                ),
                "next_stage": "FINALIZING",
                "current_phase_index": 0,
            }

    def _finalize_and_approve(self, session_id: str, session: Dict) -> Dict:
        """Finalize and approve the methodology."""
        # Apply all refinements to create the final archetype
        draft = session.get("original_draft", {})
        refinements = session.get("refinements", [])
        naming = {
            "methodology_name": session.get("methodology_name", "My Process"),
            "methodology_description": session.get("methodology_description", ""),
            "key_principles": session.get("key_principles", []),
        }

        try:
            refined = apply_refinements(draft, refinements, naming)

            # Update the session with refined archetype
            self.db.update_refined_archetype(session_id, refined)

            # Update status to approved
            self.db.update_review_session_status(session_id, "APPROVED")

            return {
                "coaching_message": (
                    f"Congratulations! Your methodology **\"{naming['methodology_name']}\"** "
                    f"has been approved and is ready to publish. You can now select it "
                    f"as your methodology for future pursuits.\n\n"
                    f"Would you like to make it visible to your team, organization, "
                    f"or keep it personal for now?"
                ),
                "next_stage": "APPROVED",
                "current_phase_index": 0,
                "refined_archetype": refined,
            }
        except ValueError as e:
            return {
                "coaching_message": (
                    f"I encountered an issue finalizing your methodology: {str(e)}. "
                    f"Let's review the changes and try again."
                ),
                "next_stage": "REVIEWING_PHASES",
                "current_phase_index": 0,
                "error": str(e),
            }

    # =========================================================================
    # CONVENIENCE METHODS FOR UI INTEGRATION
    # =========================================================================

    def start_review(
        self,
        innovator_id: str,
        inferred_archetype_id: str
    ) -> Dict:
        """
        Convenience method to start a review from an inferred archetype ID.

        Args:
            innovator_id: The innovator's ID
            inferred_archetype_id: ID of the inferred archetype to review

        Returns:
            Session info with initial coaching message
        """
        # Get the inferred archetype
        inferred = self.db.get_inferred_archetype(inferred_archetype_id)
        if not inferred:
            return {"error": f"Inferred archetype {inferred_archetype_id} not found"}

        # Build a draft archetype from the inference
        draft_archetype = {
            "archetype": {
                "id": inferred_archetype_id,
                "name": "Discovered Process",
                "draft": True,
                "phases": inferred.get("inferred_phases", []),
                "transitions": inferred.get("inferred_transitions", []),
                "tools": inferred.get("inferred_tools", []),
            },
            "source": {
                "type": "EMERGENT",
                "inference_result_id": inferred_archetype_id,
                "confidence": inferred.get("confidence", 0.5),
                "pursuit_count": len(inferred.get("pursuit_ids", [])),
            },
            "synthesis_metadata": {
                "similar_archetypes": inferred.get("similar_archetypes", []),
            },
            "scaffolding_config": {},
        }

        result = self.start_review_session(
            innovator_id=innovator_id,
            inference_result_id=inferred_archetype_id,
            draft_archetype=draft_archetype
        )

        # Rename for UI consistency
        if "coaching_message" in result:
            result["coach_message"] = result.pop("coaching_message")

        return result

    def process_response(
        self,
        session_id: str,
        innovator_message: str
    ) -> Dict:
        """
        Convenience method to process an innovator response.

        Automatically retrieves current stage from the session.

        Args:
            session_id: The review session ID
            innovator_message: The innovator's response

        Returns:
            Next coaching message and updated state
        """
        # Get session to find current stage
        session = self.db.get_review_session(session_id)
        if not session:
            return {"error": "Session not found"}

        current_stage = session.get("review_stage", "REVIEWING_PHASES")
        current_phase_index = session.get("current_phase_index", 0)

        result = self.process_innovator_response(
            session_id=session_id,
            innovator_message=innovator_message,
            current_stage=current_stage,
            current_phase_index=current_phase_index
        )

        # Update session stage
        if "next_stage" in result:
            self.db.update_review_session_stage(session_id, result["next_stage"])

        # Update phase index
        if "current_phase_index" in result:
            self.db.update_review_session_phase_index(session_id, result["current_phase_index"])

        # Rename for UI consistency
        if "coaching_message" in result:
            result["coach_response"] = result.pop("coaching_message")

        # Include refinements applied
        if "refinements_applied" in result:
            result["refinements_applied"] = [
                {"action": "applied_refinement"}
                for _ in range(result["refinements_applied"])
            ] if isinstance(result["refinements_applied"], int) else result["refinements_applied"]

        return result

    def set_methodology_name(self, session_id: str, name: str) -> bool:
        """Set the methodology name for a review session."""
        return self.db.set_methodology_details(
            session_id=session_id,
            name=name
        )

    def set_visibility(self, session_id: str, visibility: str) -> bool:
        """Set the visibility level for the reviewed methodology."""
        session = self.db.get_review_session(session_id)
        if not session:
            return False

        # Store visibility in session for publisher to use
        session["requested_visibility"] = visibility
        # Update in DB (implementation depends on database method)
        return True

    def approve_publication(self, session_id: str) -> Dict:
        """Approve the methodology for publication."""
        session = self.db.get_review_session(session_id)
        if not session:
            return {"error": "Session not found"}

        if session.get("status") == "APPROVED":
            return {"status": "already_approved"}

        # Finalize
        result = self._finalize_and_approve(session_id, session)

        return result

    def reject_review(self, session_id: str) -> Dict:
        """Reject the review and abandon the pattern."""
        session = self.db.get_review_session(session_id)
        if not session:
            return {"error": "Session not found"}

        self.db.update_review_session_status(session_id, "REJECTED")

        return {"status": "rejected"}

    def _extract_refinements(
        self,
        message: str,
        phase_index: int,
        phases: List[Dict]
    ) -> List[Dict]:
        """Extract refinement actions from innovator's message."""
        refinements = []
        message_lower = message.lower()

        # Look for rename patterns
        rename_match = re.search(r'(?:call it|rename it to|name it)\s*["\']?([^"\']+)["\']?', message, re.IGNORECASE)
        if rename_match:
            old_name = phases[phase_index].get("name", f"Phase {phase_index + 1}") if phase_index < len(phases) else ""
            refinements.append({
                "action": "RENAMED_PHASE",
                "target": f"phase_{phase_index}",
                "before": old_name,
                "after": rename_match.group(1).strip(),
                "rationale": "User requested rename",
            })

        # Look for removal patterns
        if any(phrase in message_lower for phrase in ['remove', 'delete', 'don\'t include', 'skip']):
            refinements.append({
                "action": "REMOVED_ACTIVITY",
                "target": f"phase_{phase_index}",
                "before": "activity",
                "after": "",
                "rationale": "User requested removal",
            })

        return refinements


# =============================================================================
# REFINEMENT APPLICATION
# =============================================================================

def apply_refinements(
    draft_archetype: Dict,
    refinements: List[Dict],
    naming: Dict
) -> Dict:
    """
    Apply innovator refinements to the draft archetype.

    Produces the 'refined_archetype' that will be published.
    Runs validate_adl_compatibility() after refinements.

    Args:
        draft_archetype: The original draft archetype
        refinements: List of refinement actions from the review session
        naming: Naming details (name, description, principles)

    Returns:
        The refined archetype ready for publication
    """
    from ems.adl_generator import validate_adl_compatibility

    refined = deepcopy(draft_archetype)

    # Get the archetype section
    archetype = refined.get("archetype", {})
    phases = archetype.get("phases", [])

    for refinement in refinements:
        action = refinement.get("action", "")
        target = refinement.get("target", "")

        if action == "RENAMED_PHASE":
            # Find phase by index and rename
            try:
                phase_idx = int(target.replace("phase_", ""))
                if 0 <= phase_idx < len(phases):
                    phases[phase_idx]["name"] = refinement.get("after", phases[phase_idx]["name"])
            except (ValueError, IndexError):
                pass

        elif action == "REORDERED":
            # Reorder phases based on new order
            # target contains new order as comma-separated indices
            try:
                new_order = [int(i) for i in target.split(",")]
                phases[:] = [phases[i] for i in new_order if 0 <= i < len(phases)]
            except (ValueError, IndexError):
                pass

        elif action == "ADDED_ACTIVITY":
            # Add activity to specified phase
            try:
                phase_idx = int(target.replace("phase_", ""))
                if 0 <= phase_idx < len(phases):
                    activity = refinement.get("after", "")
                    if activity and "activities" in phases[phase_idx]:
                        phases[phase_idx]["activities"].append(activity)
            except (ValueError, IndexError):
                pass

        elif action == "REMOVED_ACTIVITY":
            # Remove activity from specified phase
            try:
                phase_idx = int(target.replace("phase_", ""))
                activity = refinement.get("before", "")
                if 0 <= phase_idx < len(phases) and activity:
                    activities = phases[phase_idx].get("activities", [])
                    if activity in activities:
                        activities.remove(activity)
            except (ValueError, IndexError):
                pass

        elif action == "MARKED_OPTIONAL":
            # Move activity to optional list
            try:
                phase_idx = int(target.replace("phase_", ""))
                if 0 <= phase_idx < len(phases):
                    if "optional_activities" not in phases[phase_idx]:
                        phases[phase_idx]["optional_activities"] = []
                    phases[phase_idx]["optional_activities"].append(refinement.get("after", ""))
            except (ValueError, IndexError):
                pass

        elif action == "MARKED_REQUIRED":
            # Move activity from optional to required
            try:
                phase_idx = int(target.replace("phase_", ""))
                activity = refinement.get("after", "")
                if 0 <= phase_idx < len(phases) and activity:
                    optional = phases[phase_idx].get("optional_activities", [])
                    if activity in optional:
                        optional.remove(activity)
                    if "activities" not in phases[phase_idx]:
                        phases[phase_idx]["activities"] = []
                    phases[phase_idx]["activities"].append(activity)
            except (ValueError, IndexError):
                pass

        elif action == "ADDED_PRINCIPLE":
            # Add principle to coaching config
            principle = refinement.get("after", "")
            if principle:
                coaching_config = refined.get("scaffolding_config", {})
                if "key_principles" not in coaching_config:
                    coaching_config["key_principles"] = []
                coaching_config["key_principles"].append(principle)
                refined["scaffolding_config"] = coaching_config

        elif action == "MERGED_PHASES":
            # Combine two phases into one
            try:
                indices = [int(i) for i in target.split(",")]
                if len(indices) >= 2 and all(0 <= i < len(phases) for i in indices):
                    merged = deepcopy(phases[indices[0]])
                    for idx in indices[1:]:
                        merged["activities"].extend(phases[idx].get("activities", []))
                    phases[indices[0]] = merged
                    # Remove merged phases (in reverse order to preserve indices)
                    for idx in sorted(indices[1:], reverse=True):
                        phases.pop(idx)
            except (ValueError, IndexError):
                pass

        elif action == "SPLIT_PHASE":
            # Split one phase into two
            try:
                phase_idx = int(target.replace("phase_", ""))
                if 0 <= phase_idx < len(phases):
                    original = phases[phase_idx]
                    activities = original.get("activities", [])
                    mid = len(activities) // 2

                    # Create two new phases
                    phase1 = deepcopy(original)
                    phase1["activities"] = activities[:mid]
                    phase1["name"] = original["name"] + " (Part 1)"

                    phase2 = deepcopy(original)
                    phase2["activities"] = activities[mid:]
                    phase2["name"] = original["name"] + " (Part 2)"

                    phases[phase_idx] = phase1
                    phases.insert(phase_idx + 1, phase2)
            except (ValueError, IndexError):
                pass

    # Update archetype with refined phases
    archetype["phases"] = phases

    # Apply naming
    methodology_name = naming.get("methodology_name", "My Process")
    archetype["id"] = slugify(methodology_name)
    archetype["name"] = methodology_name

    description = naming.get("methodology_description", "")
    if description:
        archetype["description"] = description

    # Add key principles to coaching config
    key_principles = naming.get("key_principles", [])
    if key_principles:
        scaffolding_config = refined.get("scaffolding_config", {})
        scaffolding_config["key_principles"] = key_principles
        refined["scaffolding_config"] = scaffolding_config

    # Remove draft flag
    archetype["draft"] = False

    # Update refined archetype
    refined["archetype"] = archetype

    # Validate the archetype content (not the nested structure)
    validation = validate_adl_compatibility(archetype)
    if not validation["valid"]:
        raise ValueError(f"Refined archetype is invalid: {validation['errors']}")

    return refined


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and special chars with underscores
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '_', slug)
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    return slug


# =============================================================================
# SINGLETON
# =============================================================================

_review_manager_instance = None


def get_review_session_manager() -> ReviewSessionManager:
    """Get or create the ReviewSessionManager singleton."""
    global _review_manager_instance
    if _review_manager_instance is None:
        _review_manager_instance = ReviewSessionManager()
    return _review_manager_instance
