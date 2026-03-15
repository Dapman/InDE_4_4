"""
Bridge Question Library

Pursuit-context-aware bridge questions for each artifact transition.
Each bridge crosses a module boundary without naming the boundary.

Library structure:
    BRIDGE_LIBRARY[completed_artifact][momentum_tier] → list of templates

Templates use {placeholder} syntax for pursuit-context injection.
Available placeholders (all optional with graceful fallback):
    {idea_domain}    — The domain of the pursuit (e.g., "healthcare", "education")
    {idea_summary}   — Brief summary of the core idea concept
    {user_name}      — Innovator's first name or display name
    {persona}        — Primary user/stakeholder mentioned in vision

Design rules:
    - Every bridge MUST end with a question mark
    - No methodology terminology of any kind
    - No module names (Fear Extraction, Risk Validation, etc.)
    - HIGH tier: advances the substance — assumes strong engagement
    - MEDIUM tier: sustaining — keeps energy without demanding a leap
    - LOW tier: re-grounding — reconnects with the idea's core appeal
    - CRITICAL tier: reconnection — the simplest possible re-entry
"""

BRIDGE_LIBRARY = {

    # ─── VISION → FEAR/PROTECTION ────────────────────────────────────────
    "vision": {
        "HIGH": [
            "Your story is coming into focus — you've described something real. "
            "Here's what I'm wondering: if this idea were in front of someone who "
            "could fund it tomorrow, what's the one thing they'd push back on?",

            "You've given this idea a real shape. Now I'm curious — what's the "
            "part of it that still feels most uncertain to you, even after "
            "everything you've described?",

            "What you've built here is genuinely compelling. Let me ask you this: "
            "if everything went wrong, where would it go wrong first?",

            "The idea is landing well. One thing I keep coming back to — "
            "what would have to be true about {idea_domain} for this to "
            "actually work the way you're imagining?",
        ],
        "MEDIUM": [
            "You've described something that clearly matters to you. I'm curious "
            "about one thing — what's the part of this you're most confident about, "
            "and what's the part you're least sure of?",

            "Your idea is taking shape. What's the biggest assumption hiding "
            "inside what you've described — the thing you're pretty sure is true "
            "but haven't tested yet?",

            "That's a meaningful problem you've put your finger on. "
            "What would make someone say 'this will never work'?",
        ],
        "LOW": [
            "Before we go further — what drew you to this idea in the first place? "
            "What is it about this problem that made you say 'someone needs to "
            "fix this'?",

            "Let me ask a simpler question: of everything you've described, "
            "what's the part you find most interesting?",

            "What's the thing about {idea_domain} that you know better than "
            "most people — the insight that made you think this was worth pursuing?",
        ],
        "CRITICAL": [
            "Tell me something — what's the moment you first noticed this problem?",
            "What made you want to work on this?",
            "Who is the person this idea would help the most?",
        ],
    },

    # ─── FEAR/PROTECTION → VALIDATION/TESTING ────────────────────────────
    "fear": {
        "HIGH": [
            "You've identified what matters most to protect. Of everything we just "
            "talked about, which risk would be most valuable to get some real-world "
            "evidence on — something you could actually find out in the next few weeks?",

            "Good — you can see the risks clearly now. If you could ask one person "
            "who has this problem a single question this week, what would it be?",

            "You've named what could go wrong. Here's the sharper question: which "
            "of those things is most likely to actually happen — and how would you "
            "find out for sure?",

            "The risks are visible. Now — what's the fastest way to find out "
            "whether the biggest one is actually a problem in {idea_domain}, "
            "or whether you've been worrying about the wrong thing?",
        ],
        "MEDIUM": [
            "You've looked at what could go wrong. Here's a useful question: "
            "if you talked to three people who have this problem tomorrow, "
            "what would you most want to know from them?",

            "You've been honest about the challenges. What's the one thing "
            "you'd need to learn — or the one conversation you'd need to have "
            "— to feel more confident about moving forward?",

            "That was real work. What's still an open question for you about "
            "whether this idea will actually work?",
        ],
        "LOW": [
            "Let's step back for a second. Of all the concerns you just named, "
            "which one do you actually think is solvable?",

            "Here's an easier question: who is the person you'd most want to "
            "talk to about this idea — someone who would give you an honest "
            "reaction?",

            "What would make you feel better about this idea — not certain, "
            "just a little more confident it's worth pursuing?",
        ],
        "CRITICAL": [
            "What's one thing about this idea that you do feel good about?",
            "If you had to describe this idea in one sentence to a friend, "
            "what would you say?",
            "What would need to happen for you to feel like this idea is "
            "worth another conversation?",
        ],
    },

    # ─── VALIDATION/TESTING → DEVELOPMENT ───────────────────────────────
    "validation": {
        "HIGH": [
            "You've done real work testing your assumptions. Based on what you've "
            "learned, what feels most ready to move forward — and what still has "
            "an open question attached to it?",

            "The evidence is pointing somewhere. What does it tell you about "
            "what to build first — the simplest version of this that would let "
            "you learn something real?",

            "You've stress-tested the idea and it held. Here's the next question: "
            "who is the first person you'd want to put something tangible in "
            "front of, and what would you show them?",
        ],
        "MEDIUM": [
            "You've tested some of the assumptions. What are you most confident "
            "about now that you weren't before — and what still feels uncertain?",

            "Based on what you've learned so far, what would the next version "
            "of this idea look like — even just in concept?",

            "Where does the evidence point? What would you do differently "
            "knowing what you know now?",
        ],
        "LOW": [
            "What's the most useful thing you've learned from everything we've "
            "worked through so far?",

            "Let me ask this differently: if you were explaining this idea to "
            "someone new, how would you describe it now compared to when you started?",

            "What feels more real about this idea than when we started?",
        ],
        "CRITICAL": [
            "What has stayed the same about this idea through everything we've discussed?",
            "What's one thing you're still excited about?",
        ],
    },

    # ─── GENERIC FALLBACK (any artifact, any tier) ───────────────────────
    "_fallback": {
        "HIGH": [
            "You've made real progress here. What's the next thing you find "
            "yourself genuinely wondering about?",
        ],
        "MEDIUM": [
            "That's a solid foundation. What feels like the most natural "
            "next question to sit with?",
        ],
        "LOW": [
            "Let's pause for a second. What's the most interesting part of "
            "what we've covered so far?",
        ],
        "CRITICAL": [
            "What about this idea still matters to you?",
        ],
    },
}
