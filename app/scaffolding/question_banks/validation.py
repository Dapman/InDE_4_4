"""
InDE MVP v2.3 - Validation Question Bank

Use when: Medium uncertainty, problem understood, testing solution fit
Style: Evidence-focused, assumption-testing, iteration-oriented

This bank is the default and is selected when:
- Maturity state is "hypothesis" with moderate uncertainty
- User understands the problem but is testing solutions
- No specific context triggers other banks

Questions help the innovator test assumptions and gather evidence.
"""

QUESTIONS = {
    "CRITICAL_GAP": {
        # Vision Elements
        "problem_statement": [
            "What evidence do you have that this problem exists?",
            "How did you confirm this is a real problem for people?",
            "What have you heard directly from people experiencing this?"
        ],
        "target_user": [
            "Have you talked to potential users? What did they say?",
            "How specific can you get about who has this problem?",
            "What distinguishes someone who needs this from someone who doesn't?"
        ],
        "current_situation": [
            "What alternatives have you seen people actually use?",
            "How much effort do people put into the current workarounds?",
            "What's the cost of the status quo for them?"
        ],
        "pain_points": [
            "Which pain point would users pay to solve first?",
            "How do users prioritize this problem vs others they have?",
            "What's the trigger that makes this pain acute?"
        ],
        "solution_concept": [
            "What's the simplest version of this you could test?",
            "How might you validate this approach quickly?",
            "What's the core capability that makes everything else possible?"
        ],
        "value_proposition": [
            "How would you test if people actually value this?",
            "What would prove the value proposition?",
            "How could you measure the value delivered?"
        ],
        "differentiation": [
            "How will users compare this to alternatives?",
            "What would make someone switch to this?",
            "How defensible is your differentiation?"
        ],
        "success_criteria": [
            "How will you know if this is working?",
            "What data would convince you this is the right solution?",
            "What's the smallest signal that would validate this idea?"
        ],

        # Fear Elements
        "capability_fears": [
            "What's the biggest technical risk we should validate first?",
            "What capability would you want to prove before going further?",
            "What could you build to test the hardest part?"
        ],
        "market_fears": [
            "How could you test if there's real demand for this?",
            "What would early adopters tell you about market potential?",
            "What signal would indicate the market is ready?"
        ],
        "resource_fears": [
            "What's the leanest way to test this idea?",
            "How could you validate this with the resources you have now?",
            "What would a minimal viable test look like?"
        ],

        # Hypothesis Elements
        "assumption_statement": [
            "What's your riskiest assumption right now?",
            "What must be true for this to work?",
            "If one thing turned out to be false, what would kill this idea?"
        ],
        "testable_prediction": [
            "What specific outcome would confirm this assumption?",
            "What would you expect to see if this works?",
            "How would user behavior change if you're right?"
        ],
        "test_method": [
            "What's the fastest way to learn if this works?",
            "How could you test this in the next week?",
            "What's the cheapest experiment you could run?"
        ],
        "success_metric": [
            "What metric would tell you this is working?",
            "What number would make you confident to proceed?",
            "How would you measure progress?"
        ],
        "failure_criteria": [
            "What result would tell you to try something different?",
            "At what point would you pivot?",
            "What would make you abandon this approach?"
        ],
        "learning_plan": [
            "What will you do with the results of this test?",
            "How will this experiment inform your next steps?",
            "What decisions will this data help you make?"
        ]
    },

    "FEAR_OPPORTUNITY": {
        "general": [
            "That's worth examining. How could you test if that concern is valid?",
            "What evidence would help you understand if that's a real risk?",
            "Is there a small experiment that could address that worry?"
        ],
        "risk_assessment": [
            "What's the probability of that actually happening?",
            "What's the impact if it does happen?",
            "What could you do to mitigate that risk?"
        ]
    },

    "READY_TO_FORMALIZE": {
        "vision": [
            "You've gathered good evidence. Ready to document what you've learned?",
            "Sounds like you have a validated picture. Want to capture it formally?",
            "Would it help to crystallize your validated understanding?"
        ],
        "fears": [
            "You've tested several concerns. Ready to document the real risks?",
            "Want to capture what you've learned about these risks?",
            "Would it help to prioritize these based on what you've found?"
        ],
        "hypothesis": [
            "You've got a testable idea. Want to formalize it as a hypothesis?",
            "Ready to write down exactly what you're predicting?",
            "Would a formal hypothesis help guide your experiment?"
        ]
    },

    "NATURAL_TRANSITION": {
        "vision_to_fears": [
            "Now that we've validated the core idea, what risks should we examine?",
            "What could prevent this from working that we should test?",
            "What are the main unknowns that could derail this?"
        ],
        "fears_to_hypothesis": [
            "Based on these risks, what's the most important thing to test first?",
            "What experiment would give you the most confidence?",
            "What's the quickest way to reduce uncertainty?"
        ]
    }
}

COACHING_STYLE = {
    "tone": "pragmatic, evidence-oriented, focused on learning",
    "emphasis": [
        "testability",
        "quick experiments",
        "user feedback",
        "data-driven decisions",
        "iteration"
    ],
    "avoid": [
        "premature scaling",
        "perfect solution thinking",
        "analysis paralysis",
        "untested assumptions"
    ],
    "approach": "Help them learn quickly through small, cheap experiments"
}
