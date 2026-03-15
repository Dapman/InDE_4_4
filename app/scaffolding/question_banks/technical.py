"""
InDE MVP v2.3 - Technical Question Bank

Use when: Engineering-focused constraints, compliance requirements
Style: Precise, systematic, constraint-aware

This bank is selected when:
- Purpose type is "compliance" or "process_improvement"
- Technical feasibility is a primary concern
- Regulatory or engineering constraints dominate

Questions help the innovator navigate technical and compliance challenges.
"""

QUESTIONS = {
    "CRITICAL_GAP": {
        # Vision Elements
        "problem_statement": [
            "What's the technical root cause of this problem?",
            "What systems or processes are affected?",
            "How is this problem currently measured or monitored?"
        ],
        "target_user": [
            "Who are the stakeholders affected by this technical issue?",
            "Who needs to approve or sign off on changes?",
            "What technical expertise do the users have?"
        ],
        "current_situation": [
            "What's the current technical architecture?",
            "What constraints does the existing system impose?",
            "What technical debt are you working with?"
        ],
        "pain_points": [
            "What's the technical cost of the current approach?",
            "Where are the performance bottlenecks?",
            "What breaks most often?"
        ],
        "solution_concept": [
            "What technical approach are you considering?",
            "How does this fit with existing systems?",
            "What's the implementation complexity?"
        ],
        "value_proposition": [
            "What technical improvements will users notice?",
            "How does this improve reliability or performance?",
            "What operational benefits does this provide?"
        ],
        "differentiation": [
            "What's technically novel about this approach?",
            "How does this compare to standard solutions?",
            "What technical trade-offs are you making?"
        ],
        "success_criteria": [
            "What technical metrics define success?",
            "What performance benchmarks need to be met?",
            "What compliance requirements must be satisfied?"
        ],

        # Fear Elements - Technical Focus
        "capability_fears": [
            "What technical skills are needed that you don't have?",
            "What's the hardest technical challenge here?",
            "What could go wrong during implementation?"
        ],
        "market_fears": [
            "How might technical changes affect user adoption?",
            "What if the technical approach doesn't solve the user problem?",
            "How do users typically respond to technical changes?"
        ],
        "resource_fears": [
            "What technical resources are constrained?",
            "How long will implementation realistically take?",
            "What's the maintenance burden of this approach?"
        ],

        # Technical-Specific Elements
        "technical_feasibility": [
            "What's the most technically risky part of this?",
            "What proof-of-concept could validate feasibility?",
            "What technical assumptions are you making?"
        ],
        "regulatory_constraints": [
            "What compliance requirements apply here?",
            "How do regulations constrain the solution space?",
            "What approvals or certifications are needed?"
        ],
        "technical_risks": [
            "What could cause the system to fail?",
            "What security considerations apply?",
            "What's the blast radius if something goes wrong?"
        ],

        # Hypothesis Elements
        "assumption_statement": [
            "What technical assumptions are you making?",
            "What must the system be capable of for this to work?",
            "What performance characteristics are you assuming?"
        ],
        "testable_prediction": [
            "What technical outcome would validate this approach?",
            "What performance improvement do you expect?",
            "What behavior should change if this works?"
        ],
        "test_method": [
            "How could you test this in a controlled environment?",
            "What's the minimum viable technical test?",
            "How can you validate without production risk?"
        ],
        "success_metric": [
            "What technical metrics will you track?",
            "What performance threshold indicates success?",
            "How will you measure improvement?"
        ],
        "failure_criteria": [
            "What would indicate this technical approach won't work?",
            "At what point would you try a different solution?",
            "What red flags should trigger a reassessment?"
        ]
    },

    "FEAR_OPPORTUNITY": {
        "general": [
            "How could you mitigate that technical risk?",
            "What safety measures could address that concern?",
            "Is there a way to isolate or contain that risk?"
        ],
        "technical_debt": [
            "How does this relate to existing technical debt?",
            "What's the long-term cost of this concern?",
            "How would you prioritize addressing this?"
        ],
        "compliance": [
            "What compliance implications does this have?",
            "How do regulations address this concern?",
            "What documentation or audit trail is needed?"
        ]
    },

    "READY_TO_FORMALIZE": {
        "vision": [
            "The technical requirements are clear. Ready to document them?",
            "Want to create a technical specification?",
            "Would it help to formalize the technical approach?"
        ],
        "fears": [
            "You've identified technical risks. Ready to document mitigation?",
            "Want to create a risk register for this?",
            "Would a formal risk assessment help?"
        ],
        "hypothesis": [
            "You have a technical hypothesis. Ready to design a test?",
            "Want to formalize the technical experiment?",
            "Would a structured test plan help?"
        ]
    },

    "NATURAL_TRANSITION": {
        "vision_to_fears": [
            "With this technical approach, what risks should we consider?",
            "What failure modes are possible?",
            "What security or reliability concerns apply?"
        ],
        "fears_to_hypothesis": [
            "Given these technical risks, what should we validate first?",
            "What's the highest-risk assumption to test?",
            "What proof-of-concept would reduce uncertainty?"
        ]
    }
}

COACHING_STYLE = {
    "tone": "precise, systematic, constraint-aware",
    "emphasis": [
        "feasibility assessment",
        "requirements clarity",
        "risk mitigation",
        "compliance awareness",
        "technical rigor"
    ],
    "avoid": [
        "vague aspirations",
        "ignoring constraints",
        "underestimating complexity",
        "skipping requirements analysis"
    ],
    "approach": "Help them navigate technical and compliance challenges systematically"
}
