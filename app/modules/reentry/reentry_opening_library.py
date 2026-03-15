"""
Re-Entry Opening Library

Tone-differentiated opening turn templates organized by:
  - Gap duration tier (how long since the last session)
  - Momentum tier at exit (HIGH/MEDIUM/LOW/CRITICAL from last snapshot)

Templates use {placeholder} syntax for pursuit-context injection:
  {idea_summary}     Brief summary of the core idea
  {idea_domain}      Domain/industry of the pursuit
  {persona}          Primary stakeholder/user from vision artifact
  {last_artifact}    The artifact most recently active at exit
                     (expressed in innovator vocabulary, not module name)
  {user_name}        First name of the innovator
  {gap_natural}      Natural-language gap description ("a couple of days",
                     "about a week", "this morning")

All templates MUST:
  - End with a question mark
  - Contain no methodology terminology
  - Sound like a coach who was thinking about the innovator's idea
    between sessions, not a system that retrieved a record
"""

# Gap duration tiers
# SHORT:  < 4 hours  (same day, brief break)
# MEDIUM: 4h – 48h  (overnight to a couple of days)
# LONG:   48h – 7d  (several days)
# EXTENDED: > 7d    (a week or more)

REENTRY_OPENINGS = {

    # ── HIGH MOMENTUM EXIT ─────────────────────────────────────────────
    # Innovator left with strong engagement. Coach continues the energy.
    "HIGH": {
        "SHORT": [
            "Welcome back. I've been thinking about what you said — "
            "where did you want to go next with {idea_summary}?",

            "You left in a good place. What's been on your mind since "
            "we last talked?",

            "Good timing. I had a question forming about {idea_domain} "
            "that I think you'll find interesting — but first, where "
            "were you headed when you stepped away?",
        ],
        "MEDIUM": [
            "Good to have you back. {gap_natural}, I've been sitting "
            "with something from our last conversation about "
            "{idea_summary} — what's been on your mind?",

            "Welcome back. You left with real momentum last time. "
            "What's happened with {idea_summary} since then?",

            "I'm glad you're back. Last time we were getting somewhere "
            "interesting. What's the first thing you want to pick back "
            "up on?",
        ],
        "LONG": [
            "You're back — and I'm genuinely curious. It's been "
            "{gap_natural}. What happened with {idea_summary} "
            "in the meantime?",

            "Welcome back, {user_name}. {gap_natural} is long enough "
            "for things to shift. What's changed about how you're "
            "thinking about {idea_summary}?",

            "Good to see you again. {gap_natural} away — "
            "has anything happened with {idea_domain} that's "
            "relevant to where we were?",
        ],
        "EXTENDED": [
            "It's been {gap_natural} — and I want to hear what "
            "happened. Did {idea_summary} keep moving, or did "
            "life get in the way?",

            "Welcome back. {gap_natural} is a meaningful gap. "
            "Before we pick up where we left off — what's the "
            "current state of {idea_summary} from your perspective?",

            "You're back after {gap_natural}. Let's not assume "
            "everything is where we left it — what's most "
            "important for me to know right now about {idea_summary}?",
        ],
    },

    # ── MEDIUM MOMENTUM EXIT ───────────────────────────────────────────
    # Innovator left with moderate engagement. Coach sustains without
    # demanding a leap.
    "MEDIUM": {
        "SHORT": [
            "Welcome back. What's the thing about {idea_summary} "
            "that stayed with you while you were away?",

            "Good to have you back. Where's your head at with "
            "{idea_summary} right now?",

            "Welcome back. What feels most alive about "
            "{idea_summary} today?",
        ],
        "MEDIUM": [
            "Good to have you back, {user_name}. It's been "
            "{gap_natural}. What's been sitting with you about "
            "{idea_summary}?",

            "Welcome back. Before we dive in — what's one thing "
            "that came to mind about {idea_summary} while "
            "you were away?",

            "It's good to see you. {gap_natural} away from "
            "{idea_summary} — what feels different, if anything?",
        ],
        "LONG": [
            "Welcome back. {gap_natural} is enough time for "
            "things to become clearer — or murkier. Where does "
            "{idea_summary} stand for you right now?",

            "Good to have you back. It's been {gap_natural}. "
            "What's the most honest answer you'd give right now "
            "to the question: how do you feel about {idea_summary}?",

            "You're back after {gap_natural}. Let's start fresh — "
            "what's the part of {idea_summary} you're most "
            "curious about right now?",
        ],
        "EXTENDED": [
            "It's been {gap_natural}, {user_name}. I want to "
            "start simply: what's still compelling about "
            "{idea_summary} for you?",

            "Welcome back after {gap_natural}. A lot can happen "
            "in that time. What's the most important update to "
            "{idea_summary} that I should know about?",

            "It's been {gap_natural}. Before we pick up any "
            "threads, I'd like to know: what made you come back "
            "to {idea_summary} today?",
        ],
    },

    # ── LOW MOMENTUM EXIT ──────────────────────────────────────────────
    # Innovator left with flagging energy. Coach re-grounds — reconnects
    # with the idea's core before advancing anything.
    "LOW": {
        "SHORT": [
            "Welcome back. No pressure to pick up where we left "
            "off — let me ask you something simpler. What's the "
            "part of {idea_summary} that you actually find "
            "most interesting?",

            "Good to have you back. Let's slow down for a moment. "
            "What drew you to {idea_summary} in the first place?",

            "Welcome back. I want to start with an easy question: "
            "if you described {idea_summary} to a friend over "
            "dinner tonight, what would you say?",
        ],
        "MEDIUM": [
            "Welcome back, {user_name}. It's been {gap_natural}. "
            "Let's not worry about where we were — what feels "
            "most true about {idea_summary} to you right now?",

            "Good to have you back. {gap_natural} away — "
            "sometimes that helps things settle. What's the "
            "clearest thing you know about {idea_summary} today?",

            "Welcome back. I want to start somewhere simple: "
            "what's the one thing about {idea_domain} that you "
            "understand better than most people?",
        ],
        "LONG": [
            "It's been {gap_natural}. Let's not rush. "
            "What still matters to you about {idea_summary}?",

            "Welcome back after {gap_natural}. I'd like to "
            "reconnect before we do anything else. "
            "What's the problem that {idea_summary} is trying "
            "to solve, in your own words — right now?",

            "Good to see you again. {gap_natural} away. "
            "Sometimes the gap helps. What feels clearer about "
            "{idea_summary} now than it did before?",
        ],
        "EXTENDED": [
            "It's been {gap_natural}, {user_name}. "
            "Let's start with the most important question: "
            "is {idea_summary} still something you want to "
            "work on?",

            "Welcome back after {gap_natural}. No assumptions. "
            "What does {idea_summary} mean to you right now?",

            "It's been {gap_natural}. Before anything else — "
            "what brought you back today?",
        ],
    },

    # ── CRITICAL MOMENTUM EXIT ────────────────────────────────────────
    # Innovator left with very low energy — possible disengagement risk.
    # Coach asks the simplest possible question that reconnects with
    # the idea's core value without any pressure.
    "CRITICAL": {
        "SHORT": [
            "Welcome back. Just one question to start: "
            "what's the most interesting part of {idea_summary}?",

            "Good to have you. Let's keep it simple — "
            "what made you want to work on {idea_summary}?",

            "Welcome back. What's one thing about "
            "{idea_summary} that still excites you?",
        ],
        "MEDIUM": [
            "Good to have you back, {user_name}. "
            "It's been {gap_natural}. What's still interesting "
            "to you about {idea_summary}?",

            "Welcome back. No pressure to jump in anywhere specific. "
            "What's the first thing about {idea_summary} "
            "that comes to mind?",

            "It's good to see you after {gap_natural}. "
            "What's one thing about {idea_domain} that you've "
            "been thinking about?",
        ],
        "LONG": [
            "It's been {gap_natural}. I just have one question: "
            "what still matters to you about {idea_summary}?",

            "Welcome back after {gap_natural}. "
            "What made you come back today?",

            "Good to see you again. {gap_natural} is a long time. "
            "What's the thing about {idea_summary} that kept "
            "coming back to you?",
        ],
        "EXTENDED": [
            "It's been {gap_natural}, {user_name}. "
            "I'm glad you're back. What's still alive about "
            "{idea_summary} for you?",

            "Welcome back after {gap_natural}. "
            "Let's start with the simplest question: "
            "why does {idea_summary} matter?",

            "It's been {gap_natural}. No agenda — "
            "what brought you back to {idea_summary} today?",
        ],
    },

    # ── FIRST RETURN (no prior momentum snapshot) ─────────────────────
    # User returns but no v4.1 snapshot exists — graceful fallback.
    # Warm, curious, no assumptions.
    "_no_snapshot": {
        "SHORT": [
            "Welcome back. What's on your mind about "
            "{idea_summary}?",
        ],
        "MEDIUM": [
            "Good to have you back. It's been {gap_natural}. "
            "What's the most interesting thing about "
            "{idea_summary} to you right now?",
        ],
        "LONG": [
            "Welcome back after {gap_natural}. "
            "What's changed about how you're thinking about "
            "{idea_summary}?",
        ],
        "EXTENDED": [
            "It's been {gap_natural}. Welcome back. "
            "What brought you back to {idea_summary} today?",
        ],
    },
}
