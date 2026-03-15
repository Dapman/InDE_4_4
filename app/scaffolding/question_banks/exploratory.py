"""
InDE MVP v2.3 - Exploratory Question Bank

Use when: High uncertainty, early-stage pursuit, unclear problem/solution
Style: Open-ended, discovery-focused, user-centric

This bank is selected when:
- Maturity state is "spark" or "hypothesis"
- Uncertainty level > 0.5
- User is still discovering the problem space

Questions help the innovator explore and understand before committing to solutions.
"""

QUESTIONS = {
    "CRITICAL_GAP": {
        # Vision Elements
        "problem_statement": [
            "What made you first notice this problem?",
            "How do you know this is a problem worth solving?",
            "What happens when people encounter this issue today?",
            "Can you tell me about a specific moment when you saw this problem in action?"
        ],
        "target_user": [
            "I'm curious about who experiences this problem most acutely. Have you talked to anyone about it?",
            "When you picture someone using this, who comes to mind?",
            "Who have you observed dealing with this challenge?",
            "Is there a specific person or group you had in mind when you thought of this?"
        ],
        "current_situation": [
            "How are people handling this now?",
            "What workarounds have you seen people create?",
            "What's the current 'good enough' solution?",
            "What do people do today when they face this problem?"
        ],
        "pain_points": [
            "What's the most frustrating part of the current approach?",
            "What would change if this problem disappeared tomorrow?",
            "How much time/money/effort does this problem cost people?",
            "What emotions come up when people deal with this?"
        ],
        "solution_concept": [
            "What sparked this particular approach in your mind?",
            "How did you arrive at this solution idea?",
            "What would the ideal outcome look like for someone using this?",
            "If you had a magic wand, what would this solution do?"
        ],
        "value_proposition": [
            "What would make someone stop what they're doing now and try this instead?",
            "Why would this be worth someone's attention?",
            "What's the 'aha moment' when someone first experiences this?",
            "How would someone describe the benefit in their own words?"
        ],
        "differentiation": [
            "What have you seen others try that didn't quite work?",
            "What's different about your angle on this?",
            "Why hasn't someone solved this already?",
            "What insight do you have that others might be missing?"
        ],
        "success_criteria": [
            "How would you know if this was actually helping people?",
            "What would success look like for the first few users?",
            "What change would you hope to see?",
            "What would make you feel this was worthwhile?"
        ],

        # Fear Elements
        "capability_fears": [
            "What parts of this feel most uncertain to build?",
            "What skills or knowledge would help the most here?",
            "What's the biggest unknown in making this real?"
        ],
        "market_fears": [
            "What would need to be true for people to actually want this?",
            "How might people react differently than you expect?",
            "What would make this a 'nice to have' vs a 'must have'?"
        ],

        # Hypothesis Elements
        "assumption_statement": [
            "What's the biggest leap of faith in your thinking?",
            "What would need to be true for this to work?",
            "What are you assuming about how people behave?"
        ],
        "testable_prediction": [
            "If your assumption is right, what would we observe?",
            "What would be the first sign that this is working?",
            "How would people's behavior change if this works?"
        ]
    },

    "FEAR_OPPORTUNITY": {
        "general": [
            "That's an interesting concern. What made you think of that?",
            "I appreciate you sharing that worry. Can you tell me more about it?",
            "What would need to happen for that fear to come true?",
            "What's the scenario you're picturing when that worry comes up?"
        ],
        "user_adoption": [
            "What might prevent people from trying this?",
            "What behavior change would this require from users?",
            "How would someone discover this even exists?"
        ],
        "value_clarity": [
            "If someone asked 'why should I care?', what would you say?",
            "What's the one thing this does that nothing else can?",
            "How would you explain this to someone in 20 seconds?"
        ]
    },

    "READY_TO_FORMALIZE": {
        "vision": [
            "You've shared a lot about this. Would it help to capture the key points?",
            "It sounds like you have a clear picture forming. Want to document it?",
            "Would it be useful to write down what we've uncovered so far?"
        ],
        "fears": [
            "You've identified several concerns. Want to organize them?",
            "It might help to list these worries so we can address them systematically.",
            "Would capturing these concerns make them easier to work through?"
        ],
        "hypothesis": [
            "You've got some clear assumptions. Want to turn them into something testable?",
            "It sounds like there's a hypothesis here worth writing down.",
            "Would it help to formalize what you're predicting?"
        ]
    },

    "NATURAL_TRANSITION": {
        "vision_to_fears": [
            "Now that we have a clearer picture of what you're building, what concerns come to mind?",
            "With this vision in mind, what keeps you up at night about it?",
            "What obstacles do you see between here and making this real?"
        ],
        "fears_to_hypothesis": [
            "Given these concerns, what's the riskiest assumption we should test first?",
            "What's one thing we could learn that would reduce your biggest worry?",
            "If you could get one question answered, what would it be?"
        ]
    }
}

COACHING_STYLE = {
    "tone": "curious, open-ended, hypothesis-generating",
    "emphasis": [
        "user understanding",
        "problem validation",
        "assumption surfacing",
        "empathy for the problem space"
    ],
    "avoid": [
        "methodology jargon",
        "process terminology",
        "framework references",
        "premature solutions",
        "rushing to action"
    ],
    "approach": "Help them discover and articulate what they're really trying to do"
}
