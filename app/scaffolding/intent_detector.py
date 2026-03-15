"""
InDE MVP v2.2 - Intent Detector

Automatically detect when the innovator is expressing innovation intent
and create pursuits invisibly - no "Do you want to start a pursuit?" prompts.

Patterns that indicate innovation intent:
- "I want to create/build/design/develop..."
- "What if we made..."
- "I'm thinking about a product/service/solution..."
- Problem statements: "The problem with X is..."
- Opportunity statements: "There's a need for..."
"""

import json
import re
from typing import Dict, Optional

from config import INTENT_CONFIDENCE_THRESHOLD, INTENT_DETECTION_PROMPT


class IntentDetector:
    """
    Detects innovation intent from natural conversation and auto-creates pursuits.
    """

    # Quick pattern matching for obvious innovation intent (before LLM call)
    QUICK_PATTERNS = [
        r"i want to (create|build|design|develop|make|start)",
        r"i'm (thinking about|working on|planning) (a|an|the)",
        r"what if (we|i|you) (made|created|built|designed)",
        r"(there's|there is) (a need|an opportunity|a gap)",
        r"the problem (with|is)",
        r"i have (an idea|a concept|a vision)",
        r"my idea is",
        r"i'm trying to solve",
    ]

    def __init__(self, llm_interface, database):
        """
        Initialize IntentDetector.

        Args:
            llm_interface: LLMInterface instance for Claude API calls
            database: Database instance for persistence
        """
        self.llm = llm_interface
        self.db = database
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.QUICK_PATTERNS]

    def analyze_message(self, user_message: str, user_id: str) -> Dict:
        """
        Analyze user message for innovation intent.

        Args:
            user_message: The user's message text
            user_id: User ID for pursuit creation

        Returns:
            {
                "has_intent": bool,
                "confidence": float,  # 0.0-1.0
                "suggested_title": str,
                "problem_hint": str or None,
                "solution_hint": str or None,
                "create_pursuit": bool  # Auto-create if confidence > threshold
            }
        """
        # Quick check first - if no obvious patterns, might still have intent
        has_quick_match = self._quick_pattern_check(user_message)

        # Use LLM for full intent analysis
        try:
            result = self._llm_intent_analysis(user_message)
        except Exception as e:
            print(f"[IntentDetector] LLM analysis failed: {e}")
            # Fallback to quick pattern result
            if has_quick_match:
                result = {
                    "has_intent": True,
                    "confidence": 0.6,
                    "suggested_title": self._extract_title_heuristic(user_message),
                    "problem_hint": None,
                    "solution_hint": None
                }
            else:
                result = {
                    "has_intent": False,
                    "confidence": 0.0,
                    "suggested_title": None,
                    "problem_hint": None,
                    "solution_hint": None
                }

        # Determine if we should auto-create pursuit
        result["create_pursuit"] = (
            result["has_intent"] and
            result["confidence"] >= INTENT_CONFIDENCE_THRESHOLD
        )

        return result

    def create_pursuit_silently(self, intent_data: Dict, user_id: str) -> str:
        """
        Create pursuit without asking user confirmation.

        Args:
            intent_data: Result from analyze_message
            user_id: User ID

        Returns:
            pursuit_id of the created pursuit
        """
        title = intent_data.get("suggested_title") or "New Innovation Pursuit"

        # Create pursuit in database
        pursuit = self.db.create_pursuit(user_id, title)
        pursuit_id = pursuit["pursuit_id"]

        print(f"[IntentDetector] Auto-created pursuit: '{title}' ({pursuit_id})")

        # If we have initial hints, pre-populate scaffolding
        if intent_data.get("problem_hint"):
            self.db.update_scaffolding_element(
                pursuit_id, "vision", "problem_statement",
                intent_data["problem_hint"], 0.6
            )

        if intent_data.get("solution_hint"):
            self.db.update_scaffolding_element(
                pursuit_id, "vision", "solution_concept",
                intent_data["solution_hint"], 0.6
            )

        return pursuit_id

    def _quick_pattern_check(self, message: str) -> bool:
        """Quick regex check for obvious innovation patterns."""
        for pattern in self._compiled_patterns:
            if pattern.search(message):
                return True
        return False

    def _llm_intent_analysis(self, user_message: str) -> Dict:
        """Use LLM to analyze message for innovation intent."""
        prompt = INTENT_DETECTION_PROMPT.format(user_message=user_message)

        response = self.llm.call_llm(
            prompt=prompt,
            max_tokens=300,
            system="You are an intent analyzer. Respond only with valid JSON."
        )

        # Parse JSON response
        try:
            # Clean response - extract JSON if wrapped in markdown
            json_text = response.strip()
            if json_text.startswith("```"):
                json_text = re.sub(r"```json?\s*", "", json_text)
                json_text = re.sub(r"```\s*$", "", json_text)

            result = json.loads(json_text)

            return {
                "has_intent": result.get("has_intent", False),
                "confidence": float(result.get("confidence", 0.0)),
                "suggested_title": result.get("suggested_title"),
                "problem_hint": result.get("problem_hint"),
                "solution_hint": result.get("solution_hint")
            }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[IntentDetector] Failed to parse LLM response: {e}")
            # Fallback
            return {
                "has_intent": False,
                "confidence": 0.0,
                "suggested_title": None,
                "problem_hint": None,
                "solution_hint": None
            }

    def _extract_title_heuristic(self, message: str) -> str:
        """Extract a title from message using simple heuristics."""
        # Look for quoted names
        quoted = re.search(r'"([^"]+)"', message)
        if quoted:
            return quoted.group(1)

        # Look for "called X" or "named X"
        named = re.search(r"called\s+([A-Z][a-zA-Z\s]+)", message)
        if named:
            return named.group(1).strip()

        # Take first sentence, clean up
        first_sentence = message.split('.')[0]
        if len(first_sentence) < 50:
            return first_sentence

        # Default
        return "New Innovation Pursuit"
