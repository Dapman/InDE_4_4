"""
InDE MVP v4.4.0 - Pivot False Positive Detection Tests

Tests for the v4.4 fix that prevents false positive "pivot" detection
when the user means shifting attention/focus rather than changing pursuit direction.

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
import re


class TestPivotFalsePositivePatterns:
    """Tests for pivot false positive pattern matching."""

    # v4.4 FIX: Patterns that indicate "pivot" means focus shift, not pursuit change
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
    ]

    # Actual pivot patterns (should still trigger terminal state)
    REAL_PIVOT_PATTERNS = [
        r"\b(pivoting|pivot to|changing direction|new direction)\b",
        r"\b(going (to |a |in a )different (way|direction|approach))\b",
    ]

    def setup_method(self):
        """Compile patterns for testing."""
        self._pivot_false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PIVOT_FALSE_POSITIVE_PATTERNS
        ]
        self._real_pivot_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.REAL_PIVOT_PATTERNS
        ]

    def _is_pivot_false_positive(self, message: str) -> bool:
        """Check if pivot in message is a false positive."""
        if not re.search(r'\bpivot', message, re.IGNORECASE):
            return False
        for pattern in self._pivot_false_positive_patterns:
            if pattern.search(message):
                return True
        return False

    def _matches_real_pivot(self, message: str) -> bool:
        """Check if message matches real pivot patterns."""
        for pattern in self._real_pivot_patterns:
            if pattern.search(message):
                return True
        return False

    def test_attention_pivot_is_false_positive(self):
        """'attention needs to pivot' should be detected as false positive."""
        message = "I am settled on what to build. Now my attention needs to pivot to how to build it."
        assert self._is_pivot_false_positive(message) is True

    def test_focus_pivot_is_false_positive(self):
        """'pivot my focus' should be detected as false positive."""
        message = "Time to pivot my focus to the implementation details."
        assert self._is_pivot_false_positive(message) is True

    def test_pivot_to_how_is_false_positive(self):
        """'pivot to how' should be detected as false positive."""
        message = "Now I need to pivot to how we actually build this."
        assert self._is_pivot_false_positive(message) is True

    def test_pivot_to_execution_is_false_positive(self):
        """'pivot to execution' should be detected as false positive."""
        message = "With the design done, let's pivot to execution."
        assert self._is_pivot_false_positive(message) is True

    def test_settled_then_pivot_is_false_positive(self):
        """'settled on X, pivot to Y' should be detected as false positive."""
        message = "I'm settled on the approach, now pivot to building."
        assert self._is_pivot_false_positive(message) is True

    def test_thinking_pivot_is_false_positive(self):
        """'thinking needs to pivot' should be detected as false positive."""
        message = "My thinking needs to pivot from ideation to implementation."
        assert self._is_pivot_false_positive(message) is True

    def test_effort_pivot_is_false_positive(self):
        """'effort should pivot' should be detected as false positive."""
        message = "Our effort should pivot to the technical architecture now."
        assert self._is_pivot_false_positive(message) is True

    def test_pivot_to_next_step_is_false_positive(self):
        """'pivot to next step' should be detected as false positive."""
        message = "Now we pivot to the next step in our plan."
        assert self._is_pivot_false_positive(message) is True

    # Tests for real pivots (should NOT be false positives)

    def test_changing_direction_not_false_positive(self):
        """'changing direction entirely' should NOT be a false positive."""
        message = "We're changing direction entirely on this pursuit."
        assert self._is_pivot_false_positive(message) is False
        assert self._matches_real_pivot(message) is True

    def test_going_different_direction_not_false_positive(self):
        """'going in a different direction' should NOT be a false positive."""
        message = "After the validation results, we're going in a different direction."
        assert self._is_pivot_false_positive(message) is False
        assert self._matches_real_pivot(message) is True

    def test_pivoting_to_new_approach_not_false_positive(self):
        """'pivoting to a completely different approach' should NOT be false positive."""
        message = "This idea isn't working. I'm pivoting to a completely different approach."
        # This matches the real pivot pattern but should be checked if it's also a false positive
        # It's not a false positive because it doesn't match false positive patterns
        assert self._is_pivot_false_positive(message) is False
        assert self._matches_real_pivot(message) is True

    def test_new_direction_not_false_positive(self):
        """'new direction' should NOT be a false positive."""
        message = "I think we need to go in a new direction with this idea."
        assert self._is_pivot_false_positive(message) is False
        assert self._matches_real_pivot(message) is True

    def test_no_pivot_word_not_false_positive(self):
        """Message without 'pivot' should return False."""
        message = "I'm ready to start building the prototype."
        assert self._is_pivot_false_positive(message) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
