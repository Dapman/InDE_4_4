"""
InDE MVP v2.3 - Scaling Question Bank

Use when: Low uncertainty, validated solution, growth phase
Style: Strategic, growth-focused, optimization-oriented

This bank is selected when:
- Maturity state is "validated" or "scaling"
- Uncertainty level < 0.3
- User has validated core assumptions and is ready to grow

Questions help the innovator scale efficiently and sustain growth.
"""

QUESTIONS = {
    "CRITICAL_GAP": {
        # Vision Elements
        "problem_statement": [
            "How does the problem look different at scale?",
            "Are there adjacent problems you could solve for these users?",
            "How does the problem vary across different user segments?"
        ],
        "target_user": [
            "Who's the next segment you want to reach?",
            "What defines your ideal customer profile at this stage?",
            "How are expansion users different from early adopters?"
        ],
        "current_situation": [
            "How has the competitive landscape evolved?",
            "What new alternatives have emerged since you started?",
            "How are market dynamics changing?"
        ],
        "pain_points": [
            "What new pain points emerge as users rely on you more?",
            "What would make current users use this more frequently?",
            "What's limiting deeper engagement?"
        ],
        "solution_concept": [
            "What features would drive the most growth?",
            "How might the solution evolve for enterprise/mass market?",
            "What's the next major capability to add?"
        ],
        "value_proposition": [
            "How do you articulate value differently at scale?",
            "What's driving referrals and word of mouth?",
            "How do you communicate value to new segments?"
        ],
        "differentiation": [
            "How sustainable is your competitive advantage?",
            "What moats are you building?",
            "How do you stay ahead as others catch up?"
        ],
        "success_criteria": [
            "What metrics matter most at this stage?",
            "How do you measure healthy growth?",
            "What leading indicators predict long-term success?"
        ],

        # Fear Elements
        "capability_fears": [
            "What breaks first as you scale?",
            "Where are the bottlenecks in your current approach?",
            "What capabilities need to scale differently?"
        ],
        "market_fears": [
            "What could cause growth to plateau?",
            "How might market conditions change?",
            "What competitive threats are emerging?"
        ],
        "resource_fears": [
            "What resources constrain your growth?",
            "How will you fund continued expansion?",
            "What talent gaps need to be filled?"
        ],

        # Hypothesis Elements
        "assumption_statement": [
            "What assumptions are you making about scalability?",
            "What's different about reaching the next 10x users?",
            "What do you believe about this market that others don't?"
        ],
        "testable_prediction": [
            "What growth rate are you targeting and why?",
            "How will unit economics change at scale?",
            "What efficiency gains do you expect?"
        ],
        "test_method": [
            "How are you testing new growth channels?",
            "What experiments inform your expansion strategy?",
            "How do you validate product-market fit in new segments?"
        ],
        "success_metric": [
            "What metrics define sustainable growth?",
            "How do you balance growth with profitability?",
            "What's your north star metric?"
        ]
    },

    "FEAR_OPPORTUNITY": {
        "general": [
            "How might that concern evolve as you scale?",
            "What systems could help manage that at scale?",
            "How do others at your stage handle this challenge?"
        ],
        "growth_risks": [
            "What would cause growth to stall?",
            "How do you prevent growing too fast to sustain?",
            "What quality trade-offs are you making for growth?"
        ]
    },

    "READY_TO_FORMALIZE": {
        "vision": [
            "Your scaled vision is taking shape. Ready to document it?",
            "Want to capture your growth-stage vision formally?",
            "Would it help to articulate where you're heading at scale?"
        ],
        "fears": [
            "You've identified scaling risks. Ready to document mitigation plans?",
            "Want to formalize your risk management approach?",
            "Would capturing these help prioritize what to address first?"
        ],
        "hypothesis": [
            "You have growth hypotheses. Want to formalize them for testing?",
            "Ready to document your expansion assumptions?",
            "Would structured hypotheses help guide your growth experiments?"
        ]
    },

    "NATURAL_TRANSITION": {
        "vision_to_fears": [
            "With this growth vision, what scaling challenges concern you?",
            "What risks become more significant at scale?",
            "What could derail your growth trajectory?"
        ],
        "fears_to_hypothesis": [
            "Given these scaling risks, what should we test first?",
            "What growth experiment would reduce the most uncertainty?",
            "What's the highest-leverage thing to learn right now?"
        ]
    }
}

COACHING_STYLE = {
    "tone": "strategic, growth-focused, optimization-oriented",
    "emphasis": [
        "metrics and KPIs",
        "repeatability and efficiency",
        "sustainable growth",
        "competitive positioning",
        "operational excellence"
    ],
    "avoid": [
        "over-experimentation",
        "unnecessary pivots",
        "startup theater",
        "growth at any cost"
    ],
    "approach": "Help them scale efficiently while maintaining what works"
}
