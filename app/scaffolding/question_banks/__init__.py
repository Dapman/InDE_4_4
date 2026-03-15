"""
InDE MVP v2.3 - Question Banks

Goal-oriented question sets for coaching without methodology jargon.

Each question bank provides questions tailored to specific pursuit contexts:
- exploratory: High uncertainty, early-stage discovery
- validation: Testing assumptions and solutions
- scaling: Growth and optimization
- technical: Engineering and compliance focus
- social_impact: Community and society focus

Questions are organized by intervention moment type and missing element.
The ScaffoldingEngine selects questions based on TeleologicalAssessor output.

IMPORTANT: These questions guide the LLM but are NOT shown verbatim to users.
The LLM uses them as inspiration to generate natural coaching responses.
"""

from .exploratory import QUESTIONS as EXPLORATORY_QUESTIONS, COACHING_STYLE as EXPLORATORY_STYLE
from .validation import QUESTIONS as VALIDATION_QUESTIONS, COACHING_STYLE as VALIDATION_STYLE
from .scaling import QUESTIONS as SCALING_QUESTIONS, COACHING_STYLE as SCALING_STYLE
from .technical import QUESTIONS as TECHNICAL_QUESTIONS, COACHING_STYLE as TECHNICAL_STYLE
from .social_impact import QUESTIONS as SOCIAL_IMPACT_QUESTIONS, COACHING_STYLE as SOCIAL_IMPACT_STYLE

# Question bank registry
QUESTION_BANKS = {
    "exploratory": {
        "questions": EXPLORATORY_QUESTIONS,
        "style": EXPLORATORY_STYLE
    },
    "validation": {
        "questions": VALIDATION_QUESTIONS,
        "style": VALIDATION_STYLE
    },
    "scaling": {
        "questions": SCALING_QUESTIONS,
        "style": SCALING_STYLE
    },
    "technical": {
        "questions": TECHNICAL_QUESTIONS,
        "style": TECHNICAL_STYLE
    },
    "social_impact": {
        "questions": SOCIAL_IMPACT_QUESTIONS,
        "style": SOCIAL_IMPACT_STYLE
    }
}


def get_question_bank(bank_name: str) -> dict:
    """Get a question bank by name."""
    return QUESTION_BANKS.get(bank_name, QUESTION_BANKS["validation"])


def get_question_for_moment(bank_name: str, moment_type: str,
                            missing_element: str = None) -> list:
    """
    Get questions for a specific intervention moment.

    Args:
        bank_name: Name of question bank (exploratory, validation, etc.)
        moment_type: Type of intervention (CRITICAL_GAP, FEAR_OPPORTUNITY, etc.)
        missing_element: Specific element that's missing (for CRITICAL_GAP)

    Returns:
        List of question strings
    """
    bank = QUESTION_BANKS.get(bank_name, QUESTION_BANKS["validation"])
    questions = bank["questions"].get(moment_type, {})

    if missing_element and missing_element in questions:
        return questions[missing_element]

    # Return general questions for the moment type if no specific element
    all_questions = []
    for element_questions in questions.values():
        all_questions.extend(element_questions)
    return all_questions[:3]  # Limit to 3 questions
