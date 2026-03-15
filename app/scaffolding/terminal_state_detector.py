"""
InDE MVP v2.7 - Terminal State Detector

Detects when pursuits reach terminal states using multi-signal analysis.
CRITICAL: Does NOT trigger on SUSPENDED states - only the 6 terminal states.

Terminal States:
1. COMPLETED.SUCCESSFUL - Innovation achieved objectives
2. COMPLETED.VALIDATED_NOT_PURSUED - Validated but strategically not pursued
3. TERMINATED.INVALIDATED - Core hypothesis disproven
4. TERMINATED.PIVOTED - Pivoting to new direction
5. TERMINATED.ABANDONED - External factors forced termination
6. TERMINATED.OBE - Overtaken By Events
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from config import (
    TERMINAL_STATES, SUSPENDED_STATES, RETROSPECTIVE_CONFIG,
    TERMINAL_DETECTION_PROMPT
)


class TerminalStateDetector:
    """
    Detects when pursuits reach terminal states.
    CRITICAL: Does NOT trigger on SUSPENDED states.
    """

    # Explicit terminal phrases by state
    # v2.7.1: Added more conversational phrases for easier triggering
    EXPLICIT_PATTERNS = {
        "COMPLETED.SUCCESSFUL": [
            r"\b(launched|deployed|shipped|released|went live|in production)\b",
            r"\b(successfully completed|achieved|accomplished)\b",
            r"\b(met (all |our )?goals?|hit (all |our )?targets?)\b",
            # v2.7.1: More conversational phrases
            r"\bthis (pursuit|project|idea) is (complete|done|finished|successful)\b",
            r"\bmark (this |it )?(as )?(complete|done|finished|successful)\b",
            r"\bwe('ve| have) (completed|finished|succeeded|done it)\b",
            r"\bit('s| is) (complete|done|finished|a success)\b",
            r"\bcompleted? this pursuit\b",
            r"\bthis (one |pursuit |project )?(is |was )?a success\b",
        ],
        "COMPLETED.VALIDATED_NOT_PURSUED": [
            r"\b(validated but|proven but|works but).*(not (going to |gonna )?(proceed|continue|pursue))\b",
            r"\b(strategically (decided|chose) not to)\b",
            r"\b(validated|confirmed).*(won't|will not|aren't going to) (pursue|continue)\b",
            # v2.7.1: More conversational phrases
            r"\b(validated|proved|confirmed) but (not pursuing|won't pursue|decided against)\b",
            r"\bit works but (we're not|I'm not|not going to) (pursue|continue)\b",
        ],
        "TERMINATED.INVALIDATED": [
            r"\b(invalidated|disproven|hypothesis (was |is )wrong)\b",
            r"\b(customers? (don't|didn't|won't) (want|need|buy))\b",
            r"\b(testing (showed|proved|confirmed) (it )?(doesn't|won't) work)\b",
            r"\b(failed (the |our )?validation)\b",
            # v2.7.1: More conversational phrases
            r"\bthis (idea |pursuit |hypothesis )?(didn't|doesn't|won't) work\b",
            r"\bit('s| is| was) (invalidated|disproven|wrong)\b",
            r"\bthe (hypothesis|assumption|idea) (was |is )wrong\b",
        ],
        "TERMINATED.PIVOTED": [
            r"\b(pivoting|pivot to|changing direction|new direction)\b",
            r"\b(going (to |a )different (way|direction|approach))\b",
            r"\b(abandoning (this|the original) (and|to) (try|pursue))\b",
            # v2.7.1: More conversational phrases
            r"\bpivot(ing|ed)? (to|from) (this|a new|another)\b",
            r"\bchanging (direction|approach|strategy)\b",
            r"\bgoing (in )?a (different|new) direction\b",
        ],
        "TERMINATED.ABANDONED": [
            r"\b(abandon(ing|ed)?|giving up|stopping|quit(ting)?)\b",
            r"\b(can't continue|unable to continue|forced to stop)\b",
            r"\b(lost (funding|resources|support))\b",
            r"\b(decided (not to|to stop))\b",
            # v2.7.1: More conversational phrases
            r"\bmark (this |it )?(as )?(abandoned|terminated|stopped|dead)\b",
            r"\bthis (pursuit|project|idea) is (abandoned|dead|terminated|stopped)\b",
            r"\b(stopping|ending|terminating) this (pursuit|project)\b",
            r"\bnot (going to |gonna )?(continue|pursue) this\b",
            r"\blet('s| us) (stop|end|abandon|terminate) this\b",
            r"\bclose (out )?this pursuit\b",
            r"\bI('m| am) (stopping|abandoning|quitting|ending) this\b",
            # v3.7.4: Explicit "I want to abandon" patterns
            r"\bi want to abandon\b",
            r"\bwant to (abandon|stop|quit|end|terminate) (this|the|my) (pursuit|project|idea)\b",
            r"\bi('d| would) like to (abandon|stop|quit|end|terminate)\b",
            r"\bcan we (abandon|stop|quit|end|terminate) this\b",
            r"\bplease (abandon|stop|quit|end|terminate) this\b",
        ],
        "TERMINATED.OBE": [
            r"\b(competitor (launched|beat us|got there first))\b",
            r"\b(market (changed|shifted|disappeared))\b",
            r"\b(regulations? (changed|prevent|block))\b",
            # v4.0 FIX: "overtaken by" requires context (events/circumstances/competitor)
            r"\b(overtaken by (events|circumstances|competition|competitors))\b",
            r"\bbeaten to market\b",
            r"\b(someone else (already|just) (did|launched|built) (it|this))\b",
            # v2.7.1: More conversational phrases
            # v4.0 FIX: Require pursuit/idea/project context to avoid false positives
            r"\b(circumstances|situation) (have |has )?(changed|shifted)\b",
            r"\b(this |the )?(pursuit|idea|project|concept) is no longer (relevant|needed|viable)\b",
            r"\bevents made this (obsolete|irrelevant|unnecessary)\b",
            # v4.0: Explicit OBE phrases
            r"\b(world|things|everything) (has |have )?(moved on|changed)\b",
        ]
    }

    # Phrases that indicate NOT terminal (suspended or just pausing)
    SUSPENSION_PATTERNS = [
        r"\b(on hold|paused|pausing|waiting)\b",
        r"\b(until (Q\d|next (month|quarter|year)|budget|funding))\b",
        r"\b(when (we get|resources|time|budget))\b",
        r"\b(temporarily (stopped|paused))\b",
        r"\b(will resume|coming back to|picking (this )?up later)\b"
    ]

    # v4.4 FIX: Phrases where "pivot" means focus shift, not pursuit direction change
    # These patterns indicate forward progress, not terminal states
    PIVOT_FALSE_POSITIVE_PATTERNS = [
        # Attention/focus pivot (shifting mental focus, not pursuit direction)
        r"\b(attention|focus|thinking|mind|effort) (needs to |should |must |will )?(pivot|shift|turn|move)\b",
        r"\bpivot (my |our )?(attention|focus|thinking|effort)\b",
        # Phase transition language (what -> how, idea -> execution)
        r"\bpivot to (how|the how|execution|building|implementation|next)\b",
        r"\b(now|next) .{0,20}pivot to (how|building|making|creating)\b",
        # Forward progress indicators with pivot
        r"\b(settled|decided|clear) .{0,30}pivot\b",
        r"\bpivot .{0,20}(next step|next phase|implementation)\b",
        # v4.4.1: User corrections - CRITICAL: these must prevent re-triggering
        # When user clarifies they are NOT pivoting, don't re-detect as pivot
        r"\b(not|am not|i'm not|i am not|isn't|wasn't|aren't|don't|didn't) (actually )?(pivot|pivoting)\b",
        r"\bnot pivoting\b",
        r"\bwasn't pivoting\b",
        r"\bdidn't (mean to |intend to )?(pivot|change direction)\b",
        r"\b(poor|bad|wrong) (choice of |)words\b",
        r"\bthat's not what (i|I) meant\b",
        r"\bmisunderst(ood|anding)\b",
        r"\blet me clarify\b",
        r"\bto clarify\b",
        r"\b(i|I) (simply |just )?(meant|mean)\b",
        r"\bstill (working on|pursuing|committed to)\b",
        r"\bnot (done|finished|stopping|abandoning|ending|changing direction)\b",
    ]

    # Phrases that suggest the message might be about ending/concluding
    # Used as a gate before expensive semantic analysis
    # v2.7.1: Added more conversational triggers
    TERMINAL_HINT_PATTERNS = [
        r"\b(done|finished|complete[d]?|ended|over|wrapped up)\b",
        r"\b(closing|concluding|ending|stopping|terminating)\b",
        r"\b(failed|didn't work|won't work|killed|scrapped)\b",
        r"\b(pivot|pivoting|changing direction|new direction)\b",
        r"\b(abandon|gave up|giving up|quit|quitting)\b",
        r"\b(launched|shipped|deployed|released|went live)\b",
        r"\b(competitor|beaten|overtaken|too late)\b",
        r"\b(validated but|proved but|works but).*(not|won't)\b",
        # v2.7.1: More conversational triggers
        r"\bmark.*(complete|done|finished|abandoned|success)\b",
        r"\bthis (pursuit|project|idea) is\b",
        r"\bclose (out )?this\b",
        r"\bretrospec\b",  # "retrospective", "retrospect"
        r"\bcapture (learnings?|lessons?|what we learned)\b",
        r"\bwhat (did )?(we|I) learn\b",
        r"\blet'?s (end|stop|finish|complete|close)\b",
        # v3.7.4: Explicit "want to abandon" triggers
        r"\bwant to (abandon|stop|quit|end|terminate)\b",
        r"\bcan we (abandon|stop|quit|end|terminate)\b",
        r"\bplease (abandon|stop|quit|end|terminate)\b",
    ]

    def __init__(self, llm_interface, database, element_tracker=None):
        """
        Initialize TerminalStateDetector.

        Args:
            llm_interface: LLMInterface for semantic analysis
            database: Database instance
            element_tracker: Optional ElementTracker for context
        """
        self.llm = llm_interface
        self.db = database
        self.element_tracker = element_tracker

        # Compile regex patterns
        self._explicit_patterns = {}
        for state, patterns in self.EXPLICIT_PATTERNS.items():
            self._explicit_patterns[state] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        self._suspension_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SUSPENSION_PATTERNS
        ]

        # v4.4 FIX: Compile pivot false positive patterns
        self._pivot_false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PIVOT_FALSE_POSITIVE_PATTERNS
        ]

        # v2.7 FIX: Compile terminal hint patterns for gating semantic analysis
        self._terminal_hint_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.TERMINAL_HINT_PATTERNS
        ]

        # v2.7 FIX: Cache for recent terminal checks to avoid repeat LLM calls
        # Structure: {pursuit_id: {"result": dict, "message_hash": str, "timestamp": datetime}}
        self._detection_cache = {}
        self._cache_ttl_seconds = 300  # 5 minute cache TTL

    def detect_terminal_intent(self, message: str, pursuit_id: str,
                                skip_semantic: bool = False) -> Dict:
        """
        Analyze message for terminal state signals.

        Args:
            message: User's message
            pursuit_id: Pursuit ID
            skip_semantic: If True, skip expensive semantic LLM analysis (v2.7 fix)

        Returns:
            {
                "state": "TERMINATED.INVALIDATED" | "COMPLETED.SUCCESSFUL" | "ACTIVE",
                "confidence": 0.0-1.0,
                "evidence": "quote from message",
                "trigger_type": "explicit" | "semantic" | "inactivity"
            }
        """
        # First check for suspension patterns - these are NOT terminal
        if self._is_suspension_signal(message):
            return {
                "state": "ACTIVE",
                "confidence": 0.90,
                "evidence": "Suspension signal detected",
                "trigger_type": "suspension"
            }

        # v4.4 FIX: Check for pivot false positives (attention/focus shifts, not pursuit pivots)
        if self._is_pivot_false_positive(message):
            return {
                "state": "ACTIVE",
                "confidence": 0.95,
                "evidence": "Pivot language indicates focus shift, not pursuit direction change",
                "trigger_type": "pivot_false_positive"
            }

        # Check for explicit terminal patterns
        explicit_result = self._check_explicit_patterns(message)
        if explicit_result["state"] != "ACTIVE":
            return explicit_result

        # v2.7 FIX: Skip semantic analysis if caller requested it
        if skip_semantic:
            return {
                "state": "ACTIVE",
                "confidence": 1.0,
                "evidence": "",
                "trigger_type": "none"
            }

        # v2.7 FIX: Only use LLM semantic analysis if message hints at terminal state
        # This gates the expensive LLM call to avoid 3-5 second delays on every message
        if not self.llm.demo_mode and self._might_be_terminal(message):
            # Check cache first to avoid repeat LLM calls
            cached = self._get_cached_result(pursuit_id, message)
            if cached:
                return cached

            semantic_result = self._semantic_analysis(message, pursuit_id)
            if semantic_result["confidence"] >= RETROSPECTIVE_CONFIG["detection_confidence_threshold"]:
                # Cache the result
                self._cache_result(pursuit_id, message, semantic_result)
                return semantic_result

        # No terminal signal detected
        return {
            "state": "ACTIVE",
            "confidence": 1.0,
            "evidence": "",
            "trigger_type": "none"
        }

    def _might_be_terminal(self, message: str) -> bool:
        """
        v2.7 FIX: Quick check if message might be about ending/concluding.

        Used as a gate before expensive semantic LLM analysis.
        Only returns True if message contains terminal-related language.
        """
        for pattern in self._terminal_hint_patterns:
            if pattern.search(message):
                return True
        return False

    def _get_cached_result(self, pursuit_id: str, message: str) -> Optional[Dict]:
        """
        v2.7 FIX: Get cached terminal detection result if available and fresh.
        """
        if pursuit_id not in self._detection_cache:
            return None

        cached = self._detection_cache[pursuit_id]

        # Check if cache is still valid (within TTL)
        age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
        if age > self._cache_ttl_seconds:
            del self._detection_cache[pursuit_id]
            return None

        # Check if it's for the same message (or similar)
        # Use simple hash comparison
        message_hash = hash(message.lower().strip()[:100])
        if cached["message_hash"] == message_hash:
            return cached["result"]

        return None

    def _cache_result(self, pursuit_id: str, message: str, result: Dict) -> None:
        """
        v2.7 FIX: Cache terminal detection result.
        """
        self._detection_cache[pursuit_id] = {
            "result": result,
            "message_hash": hash(message.lower().strip()[:100]),
            "timestamp": datetime.now(timezone.utc)
        }

    def detect_pursuit_abandonment(self, pursuit_id: str) -> Dict:
        """
        Detect abandonment through inactivity patterns.
        More conservative - requires high confidence.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            {
                "likely_abandoned": bool,
                "confidence": float,
                "days_inactive": int,
                "last_activity_type": str
            }
        """
        # Get last activity
        last_activity = self._get_last_activity(pursuit_id)

        if not last_activity:
            return {"likely_abandoned": False, "confidence": 0.0, "days_inactive": 0}

        days_inactive = (datetime.now(timezone.utc) - last_activity["timestamp"]).days

        # Get pursuit phase to determine threshold
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {"likely_abandoned": False, "confidence": 0.0, "days_inactive": 0}

        phase = self._determine_phase(pursuit_id)
        thresholds = RETROSPECTIVE_CONFIG["inactivity_threshold_days"]
        threshold = thresholds.get(phase, 30)

        # Only suggest abandonment if WELL beyond threshold (1.5x multiplier)
        if days_inactive > (threshold * 1.5):
            confidence = min(0.85, (days_inactive / threshold) * 0.4)
            return {
                "likely_abandoned": True,
                "confidence": confidence,
                "days_inactive": days_inactive,
                "last_activity_type": last_activity.get("type", "message")
            }

        return {
            "likely_abandoned": False,
            "confidence": 0.0,
            "days_inactive": days_inactive,
            "last_activity_type": last_activity.get("type", "message")
        }

    def should_trigger_retrospective(self, pursuit_id: str,
                                      current_message: str) -> Dict:
        """
        Multi-signal fusion for retrospective triggering.

        Args:
            pursuit_id: Pursuit ID
            current_message: Current user message

        Returns:
            {
                "should_trigger": bool,
                "suggested_state": str,
                "confidence": float,
                "trigger_reason": str,
                "mode": "mandatory" | "suggested"
            }
        """
        # Check if pursuit already terminal
        pursuit = self.db.get_pursuit(pursuit_id)
        if pursuit and pursuit.get("state") in TERMINAL_STATES:
            return {
                "should_trigger": False,
                "suggested_state": pursuit.get("state"),
                "confidence": 1.0,
                "trigger_reason": "Already terminal",
                "mode": None
            }

        # Signal 1: Message content analysis
        semantic_signal = self.detect_terminal_intent(current_message, pursuit_id)

        # Signal 2: Inactivity pattern (only if no explicit signal)
        inactivity_signal = {"likely_abandoned": False, "confidence": 0.0}
        if semantic_signal["state"] == "ACTIVE":
            inactivity_signal = self.detect_pursuit_abandonment(pursuit_id)

        # Fusion logic
        if semantic_signal["state"] != "ACTIVE":
            mode = "mandatory" if semantic_signal["confidence"] > 0.85 else "suggested"
            return {
                "should_trigger": True,
                "suggested_state": semantic_signal["state"],
                "confidence": semantic_signal["confidence"],
                "trigger_reason": f"Detected: {semantic_signal['evidence']}",
                "mode": mode
            }

        elif inactivity_signal["likely_abandoned"]:
            return {
                "should_trigger": True,
                "suggested_state": "TERMINATED.ABANDONED",
                "confidence": inactivity_signal["confidence"],
                "trigger_reason": f"Inactive for {inactivity_signal['days_inactive']} days",
                "mode": "suggested"
            }

        else:
            return {
                "should_trigger": False,
                "suggested_state": "ACTIVE",
                "confidence": 1.0,
                "trigger_reason": "Pursuit is active",
                "mode": None
            }

    def _is_suspension_signal(self, message: str) -> bool:
        """Check if message indicates suspension (NOT terminal)."""
        for pattern in self._suspension_patterns:
            if pattern.search(message):
                return True
        return False

    def _is_pivot_false_positive(self, message: str) -> bool:
        """
        v4.4 FIX: Check if 'pivot' in message is a false positive.

        Detects when 'pivot' is used to mean shifting attention/focus
        (forward progress) rather than changing pursuit direction (terminal).

        Examples of false positives this catches:
        - "my attention needs to pivot to how to build it"
        - "now I need to pivot my focus to execution"
        - "settled on what, now pivot to how"
        """
        # Only check if message contains pivot-related words
        if not re.search(r'\bpivot', message, re.IGNORECASE):
            return False

        for pattern in self._pivot_false_positive_patterns:
            if pattern.search(message):
                return True
        return False

    def _check_explicit_patterns(self, message: str) -> Dict:
        """Check for explicit terminal state patterns."""
        best_match = {
            "state": "ACTIVE",
            "confidence": 0.0,
            "evidence": "",
            "trigger_type": "none"
        }

        for state, patterns in self._explicit_patterns.items():
            for pattern in patterns:
                match = pattern.search(message)
                if match:
                    # Explicit pattern = high confidence
                    confidence = 0.85
                    if best_match["confidence"] < confidence:
                        best_match = {
                            "state": state,
                            "confidence": confidence,
                            "evidence": match.group(0),
                            "trigger_type": "explicit"
                        }

        return best_match

    def _semantic_analysis(self, message: str, pursuit_id: str) -> Dict:
        """Use LLM for semantic terminal state detection."""
        pursuit = self.db.get_pursuit(pursuit_id)
        pursuit_name = pursuit.get("title", "Unknown") if pursuit else "Unknown"

        # Get recent activity count
        history = self.db.get_conversation_history(pursuit_id, limit=10)
        activity_count = len(history)

        prompt = TERMINAL_DETECTION_PROMPT.format(
            pursuit_name=pursuit_name,
            activity_count=activity_count,
            message=message
        )

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=400,
                system="You are a terminal state detector. Respond only with valid JSON."
            )

            result = self._parse_json_response(response)

            return {
                "state": result.get("state", "ACTIVE"),
                "confidence": result.get("confidence", 0.0),
                "evidence": result.get("evidence", ""),
                "trigger_type": "semantic"
            }

        except Exception as e:
            print(f"[TerminalDetector] Semantic analysis failed: {e}")
            return {
                "state": "ACTIVE",
                "confidence": 0.0,
                "evidence": "",
                "trigger_type": "error"
            }

    def _get_last_activity(self, pursuit_id: str) -> Optional[Dict]:
        """Get last activity for pursuit."""
        history = self.db.get_conversation_history(pursuit_id, limit=1)
        if history:
            turn = history[0]
            timestamp = turn.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except (ValueError, TypeError):
                    timestamp = datetime.now(timezone.utc)
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)

            # Ensure timezone-aware
            if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            return {
                "timestamp": timestamp,
                "type": "message"
            }
        return None

    def _determine_phase(self, pursuit_id: str) -> str:
        """Determine pursuit phase for inactivity threshold."""
        if not self.element_tracker:
            return "mid_stage"

        completeness = self.element_tracker.get_completeness(pursuit_id)
        vision = completeness.get("vision", 0)
        fears = completeness.get("fears", 0)
        hypothesis = completeness.get("hypothesis", 0)

        avg_completeness = (vision + fears + hypothesis) / 3

        if avg_completeness < 0.25:
            return "early_stage"
        elif avg_completeness < 0.60:
            return "mid_stage"
        else:
            return "late_stage"

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response."""
        text = response.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            text = re.sub(r"```json?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)

        return json.loads(text)

    def generate_transition_offer(self, suggested_state: str,
                                  confidence: float,
                                  trigger_reason: str) -> str:
        """
        Generate natural language offer to transition to retrospective.

        Args:
            suggested_state: Suggested terminal state
            confidence: Detection confidence
            trigger_reason: Why this was detected

        Returns:
            Offer message string
        """
        state_descriptions = {
            "COMPLETED.SUCCESSFUL": "successfully completed this pursuit",
            "COMPLETED.VALIDATED_NOT_PURSUED": "validated this concept but decided not to pursue it further",
            "TERMINATED.INVALIDATED": "discovered this hypothesis doesn't hold up",
            "TERMINATED.PIVOTED": "decided to pivot in a new direction",
            "TERMINATED.ABANDONED": "had to stop working on this",
            "TERMINATED.OBE": "been overtaken by external events"
        }

        description = state_descriptions.get(
            suggested_state,
            "reached a conclusion with this pursuit"
        )

        base_offer = f"""It sounds like you've {description}.

Before we close this chapter, would you like to do a brief retrospective? Taking 5-10 minutes to reflect can help:

- Capture valuable learnings for future pursuits
- Document what worked and what didn't
- Build organizational knowledge that helps everyone

Would you like to proceed with a retrospective?"""

        if confidence < 0.80:
            base_offer = f"""I'm sensing that you might have {description}. Is that correct?

If so, I'd recommend taking a few minutes for a retrospective to capture what you've learned.

Would you like to proceed, or should we continue working on this pursuit?"""

        return base_offer
