"""
InDE MVP v4.4.0 - Terminal Detection Correction Tests

Tests for the v4.4 fix that allows users to correct false positive
terminal state detection (e.g., when they clarify they didn't mean to pivot).

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
import re


class TestUserCorrectionDetection:
    """Tests for user correction patterns in decline detection."""

    # v4.4: Correction patterns from engine.py _user_declined_formalization
    CORRECTION_PATTERNS = [
        # Direct corrections of pivot/terminal misdetection
        r"\b(not|didn't|don't|wasn't|isn't) (actually )?(pivoting|pivot|changing direction)\b",
        r"\bam not pivoting\b",
        r"\bnot pivoting\b",
        r"\bwasn't pivoting\b",
        r"\bdidn't (mean|intend) (to |)(pivot|change direction)\b",
        r"\b(poor|bad|wrong) (choice of |)words\b",
        r"\bthat's not what I meant\b",
        r"\bI didn't mean (that|it that way)\b",
        r"\bmisunderst(ood|anding)\b",
        r"\blet me clarify\b",
        r"\bto clarify\b",
        r"\bI (simply |just )?meant\b",
        r"\bI was (just |only )?(talking about|referring to)\b",
        # Clarifying forward progress
        r"\b(shifting|shift) (my |our )?(attention|focus)\b",
        r"\b(moving|move) (my |our )?(attention|focus|thinking)\b",
        r"\bnot changing (direction|course)\b",
        r"\bstill (working on|pursuing|committed to)\b",
        r"\b(pursuit|project|idea) is (still )?active\b",
        # Direct rejection of retrospective offer context
        r"^actually\b",
        r"\bI'm not (done|finished|stopping|abandoning|ending)\b",
        r"\bnot (done|finished|stopping|abandoning|ending) (this|the|with)\b",
    ]

    def setup_method(self):
        """Compile patterns for testing."""
        self._correction_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.CORRECTION_PATTERNS
        ]

    def _is_correction(self, message: str) -> bool:
        """Check if message contains a correction pattern."""
        message_lower = message.lower().strip()
        for pattern in self._correction_patterns:
            if pattern.search(message_lower):
                return True
        return False

    # Tests for the exact user message that triggered the issue

    def test_not_pivoting_in_new_direction(self):
        """User explicitly saying they are not pivoting should be detected."""
        message = "Actually, I am not pivoting in a new direction for the pursuit. It was a poor choice of words."
        assert self._is_correction(message) is True

    def test_poor_choice_of_words(self):
        """'poor choice of words' should be detected as correction."""
        message = "That was a poor choice of words on my part."
        assert self._is_correction(message) is True

    def test_simply_meant_focus(self):
        """'I simply meant' should be detected as correction."""
        message = "I simply meant that I must now focus attention on the how."
        assert self._is_correction(message) is True

    # More correction patterns

    def test_not_pivoting(self):
        """'not pivoting' should be detected."""
        message = "I'm not pivoting, just shifting focus."
        assert self._is_correction(message) is True

    def test_wasnt_pivoting(self):
        """'wasn't pivoting' should be detected."""
        message = "I wasn't pivoting the pursuit."
        assert self._is_correction(message) is True

    def test_didnt_mean_to_pivot(self):
        """'didn't mean to pivot' should be detected."""
        message = "I didn't mean to pivot or change direction."
        assert self._is_correction(message) is True

    def test_thats_not_what_i_meant(self):
        """'that's not what I meant' should be detected."""
        message = "That's not what I meant at all."
        assert self._is_correction(message) is True

    def test_let_me_clarify(self):
        """'let me clarify' should be detected."""
        message = "Let me clarify - I'm still working on this pursuit."
        assert self._is_correction(message) is True

    def test_misunderstanding(self):
        """'misunderstanding' should be detected."""
        message = "There seems to be a misunderstanding here."
        assert self._is_correction(message) is True

    def test_shifting_attention(self):
        """'shifting my attention' should be detected."""
        message = "I was just shifting my attention to implementation."
        assert self._is_correction(message) is True

    def test_still_working_on(self):
        """'still working on' should be detected."""
        message = "I'm still working on this idea."
        assert self._is_correction(message) is True

    def test_pursuit_is_active(self):
        """'pursuit is still active' should be detected."""
        message = "This pursuit is still active, I'm not abandoning it."
        assert self._is_correction(message) is True

    def test_im_not_done(self):
        """'I'm not done' should be detected."""
        message = "I'm not done with this pursuit yet."
        assert self._is_correction(message) is True

    def test_actually_at_start(self):
        """'Actually' at start should be detected as correction."""
        message = "Actually, I was just talking about next steps."
        assert self._is_correction(message) is True

    def test_wrong_words(self):
        """'wrong words' should be detected."""
        message = "I used the wrong words there."
        assert self._is_correction(message) is True

    # Negative tests - these should NOT be detected as corrections

    def test_real_pivot_not_correction(self):
        """Real pivot intent should NOT be detected as correction."""
        message = "Yes, I want to pivot to a new direction."
        assert self._is_correction(message) is False

    def test_affirmative_not_correction(self):
        """Simple affirmative should NOT be detected as correction."""
        message = "Yes, let's do the retrospective."
        assert self._is_correction(message) is False

    def test_unrelated_message_not_correction(self):
        """Unrelated message should NOT be detected as correction."""
        message = "I need to think about the market research next."
        assert self._is_correction(message) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
