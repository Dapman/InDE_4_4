"""
Display Label Registry
InDE MVP v3.7.2 - EMS Pattern Inference Engine & ADL Generator

Centralized mapping of internal identifiers, enum codes, state machine states,
and database field names to human-readable labels for innovator-facing display.

Design philosophy: The innovator should NEVER see engineering vocabulary.
Every value that appears on screen must answer a question the innovator
would naturally ask, in language they would naturally use.

Usage:
    from app.shared.display_labels import DisplayLabels

    label = DisplayLabels.get("package_type", "temporal_benchmark")
    # Returns: "Timing & Velocity Benchmark"

    label = DisplayLabels.get("contribution_status", "IKF_READY")
    # Returns: "Ready to Share"
"""

import logging

logger = logging.getLogger("inde.display_labels")


class DisplayLabels:
    """
    Centralized registry for all internal-to-display label translations.

    Categories are registered statically. New modules (e.g., EMS in v3.7.1+)
    add their categories by extending the _REGISTRY dict.

    Each category maps internal values to a dict containing:
    - label: The human-readable display string
    - icon: Optional emoji or icon identifier for UI rendering
    - description: Optional longer description for tooltips/help text
    """

    _REGISTRY = {
        # === IKF Contribution Package Types ===
        "package_type": {
            "temporal_benchmark": {
                "label": "Timing & Velocity Benchmark",
                "icon": "⏱️",
                "description": "How your pursuit's timing compares to similar innovations"
            },
            "pattern_contribution": {
                "label": "Innovation Pattern",
                "icon": "🔍",
                "description": "A reusable insight from your innovation experience"
            },
            "pattern": {
                "label": "Innovation Pattern",
                "icon": "🔍",
                "description": "A reusable insight from your innovation experience"
            },
            "risk_intelligence": {
                "label": "Risk Methodology Insight",
                "icon": "⚡",
                "description": "Risk validation approach that could help other innovators"
            },
            "effectiveness": {
                "label": "Effectiveness Metrics",
                "icon": "📊",
                "description": "How effective different approaches were in your pursuit"
            },
            "effectiveness_metrics": {
                "label": "Effectiveness Metrics",
                "icon": "📊",
                "description": "How effective different approaches were in your pursuit"
            },
            "retrospective_wisdom": {
                "label": "Retrospective Learning",
                "icon": "💡",
                "description": "Key lessons captured from your pursuit reflection"
            },
            "retrospective": {
                "label": "Retrospective Learning",
                "icon": "💡",
                "description": "Key lessons captured from your pursuit reflection"
            }
        },

        # === Contribution Lifecycle Status ===
        "contribution_status": {
            "DRAFT": {
                "label": "Needs Your Review",
                "icon": "📝",
                "description": "This contribution is ready for you to review before sharing"
            },
            "REVIEWED": {
                "label": "Approved",
                "icon": "✅",
                "description": "You've approved this contribution"
            },
            "IKF_READY": {
                "label": "Ready to Share",
                "icon": "🚀",
                "description": "Approved and ready to share with the Innovation Network"
            },
            "REJECTED": {
                "label": "Declined",
                "icon": "↩️",
                "description": "You chose not to share this contribution"
            },
            "PENDING": {
                "label": "Queued",
                "icon": "⏳",
                "description": "Queued for sharing with the Innovation Network"
            },
            "SUBMITTED": {
                "label": "Submitted",
                "icon": "📤",
                "description": "Submitted to the Innovation Network"
            },
            "RETRY_PENDING": {
                "label": "Retrying",
                "icon": "🔄",
                "description": "Awaiting retry for sharing"
            },
            "SUBMISSION_FAILED": {
                "label": "Sharing Failed",
                "icon": "⚠️",
                "description": "Unable to share after multiple attempts"
            }
        },

        # === Transmission Status ===
        "transmission_status": {
            "NOT_SENT": {
                "label": "Pending",
                "icon": "⏳",
                "description": "Waiting to be shared"
            },
            "QUEUED": {
                "label": "Queued for Sharing",
                "icon": "📤",
                "description": "In the queue to be shared with the Innovation Network"
            },
            "TRANSMITTED": {
                "label": "Shared with Network",
                "icon": "🌐",
                "description": "Successfully shared with the Innovation Network"
            },
            "ACKNOWLEDGED": {
                "label": "Received by Network",
                "icon": "✓",
                "description": "The Innovation Network has confirmed receipt"
            }
        },

        # === Federation Connection State ===
        "federation_state": {
            "DISCONNECTED": {
                "label": "Local Only",
                "icon": "🔒",
                "description": "Working locally — not connected to the Innovation Network"
            },
            "CONNECTING": {
                "label": "Connecting to Network...",
                "icon": "🔄",
                "description": "Establishing connection to the Innovation Network"
            },
            "CONNECTED": {
                "label": "Connected to Innovation Network",
                "icon": "🌐",
                "description": "Live connection to the Innovation Network"
            },
            "HALF_OPEN": {
                "label": "Reconnecting...",
                "icon": "🔄",
                "description": "Re-establishing connection after a brief interruption"
            },
            "OFFLINE": {
                "label": "Local Only",
                "icon": "🔒",
                "description": "Working locally — Innovation Network features unavailable"
            }
        },

        # === Sharing Level Preferences ===
        "sharing_level": {
            "AGGRESSIVE": {
                "label": "Maximum Sharing",
                "icon": "📡",
                "description": "Prepare contributions whenever possible — maximize your impact on the Innovation Network"
            },
            "MODERATE": {
                "label": "Balanced",
                "icon": "⚖️",
                "description": "Contribute when pursuits complete or major milestones are reached"
            },
            "CONSERVATIVE": {
                "label": "Selective",
                "icon": "🎯",
                "description": "Only contribute on your manual request"
            },
            "NONE": {
                "label": "Private",
                "icon": "🔒",
                "description": "Never auto-prepare contributions"
            }
        },

        # === Methodology Archetype Display Names ===
        "methodology_archetype": {
            "lean_startup": {
                "label": "Lean Startup",
                "icon": "🚀",
                "description": "Rapid hypothesis testing and validated learning"
            },
            "design_thinking": {
                "label": "Design Thinking",
                "icon": "🎨",
                "description": "Human-centered iterative design"
            },
            "stage_gate": {
                "label": "Stage-Gate",
                "icon": "🚪",
                "description": "Structured phase-gate decision process"
            },
            "triz": {
                "label": "TRIZ",
                "icon": "🔧",
                "description": "Systematic inventive problem solving"
            },
            "blue_ocean": {
                "label": "Blue Ocean Strategy",
                "icon": "🌊",
                "description": "Value innovation and uncontested market creation"
            },
            "adhoc": {
                "label": "Freeform",
                "icon": "✨",
                "description": "Work without a predefined methodology — InDE observes and learns from your approach"
            },
            "ad_hoc": {
                "label": "Freeform",
                "icon": "✨",
                "description": "Work without a predefined methodology — InDE observes and learns from your approach"
            },
            "emergent": {
                "label": "Emergent",
                "icon": "🌱",
                "description": "Methodology emerges from your innovation patterns"
            }
        },

        # === Generalization Level (for IKF contribution privacy) ===
        "generalization_level": {
            1: {
                "label": "Lightly Anonymized",
                "icon": "🔓",
                "description": "Basic personal details removed; pursuit context preserved"
            },
            2: {
                "label": "Moderately Generalized",
                "icon": "🔐",
                "description": "Industry-specific details preserved; organization details removed"
            },
            3: {
                "label": "Fully Generalized",
                "icon": "🔒",
                "description": "Abstract patterns only; no identifying context"
            },
            4: {
                "label": "Maximally Abstract",
                "icon": "🛡️",
                "description": "Universal principles only; all contextual detail removed"
            },
            # String versions for flexibility
            "1": {
                "label": "Lightly Anonymized",
                "icon": "🔓",
                "description": "Basic personal details removed; pursuit context preserved"
            },
            "2": {
                "label": "Moderately Generalized",
                "icon": "🔐",
                "description": "Industry-specific details preserved; organization details removed"
            },
            "3": {
                "label": "Fully Generalized",
                "icon": "🔒",
                "description": "Abstract patterns only; no identifying context"
            },
            "4": {
                "label": "Maximally Abstract",
                "icon": "🛡️",
                "description": "Universal principles only; all contextual detail removed"
            }
        },

        # === Scenario Detection Triggers ===
        "scenario_trigger": {
            "fork_language": {
                "label": "Detected during a decision point in your conversation",
                "icon": "🔀"
            },
            "phase_transition": {
                "label": "Triggered by your phase transition",
                "icon": "➡️"
            },
            "rve_ambiguity": {
                "label": "Prompted by ambiguous risk validation results",
                "icon": "⚠️"
            }
        },

        # === PII Scan Confidence (traffic light) ===
        "pii_confidence": {
            "green": {
                "label": "No personal information detected",
                "icon": "🟢",
                "description": "This contribution appears safe to share"
            },
            "yellow": {
                "label": "Some information may need review",
                "icon": "🟡",
                "description": "A few items were flagged — please review before sharing"
            },
            "red": {
                "label": "Personal information detected — review required before sharing",
                "icon": "🔴",
                "description": "Specific personal details were found that should be removed"
            }
        },

        # === Pattern Source Badge ===
        "pattern_source": {
            "local": {
                "label": "From Your Experience",
                "icon": "📌"
            },
            "ikf": {
                "label": "From Innovation Network",
                "icon": "🌐"
            },
            "IKF_GLOBAL": {
                "label": "From Innovation Network",
                "icon": "🌐"
            },
            "LOCAL": {
                "label": "From Your Experience",
                "icon": "📌"
            }
        },

        # === Health Zones ===
        "health_zone": {
            "THRIVING": {
                "label": "Thriving",
                "icon": "🌟",
                "description": "This pursuit is progressing exceptionally well"
            },
            "HEALTHY": {
                "label": "Healthy",
                "icon": "✅",
                "description": "Good progress on track"
            },
            "ATTENTION": {
                "label": "Needs Attention",
                "icon": "⚠️",
                "description": "Some areas may need focus"
            },
            "AT_RISK": {
                "label": "At Risk",
                "icon": "🚨",
                "description": "Significant challenges detected"
            },
            "CRITICAL": {
                "label": "Critical",
                "icon": "🔴",
                "description": "Immediate attention required"
            }
        },

        # === Pursuit Status ===
        "pursuit_status": {
            "ACTIVE": {
                "label": "Active",
                "icon": "🔄",
                "description": "Currently in progress"
            },
            "COMPLETED.SUCCESSFUL": {
                "label": "Successfully Completed",
                "icon": "🎉",
                "description": "Pursuit achieved its objectives"
            },
            "COMPLETED.VALIDATED_NOT_PURSUED": {
                "label": "Validated but Not Pursued",
                "icon": "✓",
                "description": "Concept validated but strategically not pursued"
            },
            "TERMINATED.INVALIDATED": {
                "label": "Invalidated",
                "icon": "❌",
                "description": "Core hypothesis was disproven"
            },
            "TERMINATED.PIVOTED": {
                "label": "Pivoted",
                "icon": "↪️",
                "description": "Direction changed to new approach"
            },
            "TERMINATED.ABANDONED": {
                "label": "Discontinued",
                "icon": "⏹️",
                "description": "Pursuit was discontinued"
            },
            "TERMINATED.OBE": {
                "label": "Overtaken by Events",
                "icon": "⏩",
                "description": "External factors made pursuit obsolete"
            },
            "SUSPENDED.RESOURCE_CONSTRAINED": {
                "label": "Paused - Awaiting Resources",
                "icon": "⏸️",
                "description": "Temporarily paused due to resource constraints"
            },
            "SUSPENDED.MARKET_TIMING": {
                "label": "Paused - Market Timing",
                "icon": "⏸️",
                "description": "Waiting for better market conditions"
            },
            "SUSPENDED.DEPENDENCY_BLOCKED": {
                "label": "Paused - Blocked",
                "icon": "⏸️",
                "description": "Waiting on external dependencies"
            }
        },

        # === IKF Phase Names ===
        "ikf_phase": {
            "VISION": {
                "label": "Vision",
                "icon": "🎯",
                "description": "Defining the innovation vision and problem space"
            },
            "DE_RISK": {
                "label": "De-Risk",
                "icon": "🛡️",
                "description": "Validating assumptions and mitigating risks"
            },
            "DEPLOY": {
                "label": "Deploy",
                "icon": "🚀",
                "description": "Building and launching the innovation"
            }
        },

        # === Convergence Phases ===
        "convergence_phase": {
            "EXPLORING": {
                "label": "Exploring",
                "icon": "🔍",
                "description": "Gathering information and considering options"
            },
            "CONSOLIDATING": {
                "label": "Consolidating",
                "icon": "📋",
                "description": "Narrowing down to key insights"
            },
            "COMMITTED": {
                "label": "Committed",
                "icon": "✅",
                "description": "Decision made and direction set"
            },
            "HANDED_OFF": {
                "label": "Handed Off",
                "icon": "🤝",
                "description": "Transition complete"
            }
        },

        # === Maturity Levels ===
        "maturity_level": {
            "NOVICE": {
                "label": "Novice Innovator",
                "icon": "🌱",
                "description": "Beginning your innovation journey"
            },
            "COMPETENT": {
                "label": "Competent Innovator",
                "icon": "🌿",
                "description": "Building solid innovation foundations"
            },
            "PROFICIENT": {
                "label": "Proficient Innovator",
                "icon": "🌳",
                "description": "Skilled in innovation practices"
            },
            "EXPERT": {
                "label": "Expert Innovator",
                "icon": "⭐",
                "description": "Master of innovation methodology"
            }
        },

        # =====================================================================
        # v3.7.1: EMS PROCESS OBSERVATION ENGINE CATEGORIES
        # =====================================================================

        # === Observation Status ===
        "observation_status": {
            "ACTIVE": {
                "label": "Observing",
                "icon": "👁️",
                "description": "Silently capturing your process patterns"
            },
            "PAUSED": {
                "label": "Paused",
                "icon": "⏸️",
                "description": "Observation paused — resume anytime"
            },
            "COMPLETED": {
                "label": "Observation Complete",
                "icon": "✅",
                "description": "Process observation finished — ready for synthesis"
            },
            "ABANDONED": {
                "label": "Discontinued",
                "icon": "⏹️",
                "description": "Observation ended without completion"
            }
        },

        # === Observation Types ===
        "observation_type": {
            "ARTIFACT_CREATED": {
                "label": "Created an artifact",
                "icon": "📄",
                "description": "You created a document or deliverable"
            },
            "TOOL_INVOKED": {
                "label": "Used a tool",
                "icon": "🔧",
                "description": "You invoked an InDE capability"
            },
            "DECISION_MADE": {
                "label": "Made a decision",
                "icon": "🔀",
                "description": "You reached a decision point"
            },
            "TEMPORAL_PATTERN": {
                "label": "Time pattern detected",
                "icon": "⏱️",
                "description": "A notable time pattern in your work rhythm"
            },
            "COACHING_INTERACTION": {
                "label": "Asked for guidance",
                "icon": "💬",
                "description": "You requested coaching input"
            },
            "ELEMENT_CAPTURED": {
                "label": "Captured an insight",
                "icon": "💡",
                "description": "You captured an innovation element"
            },
            "RISK_VALIDATION": {
                "label": "Validated a risk",
                "icon": "⚡",
                "description": "You ran a risk validation activity"
            }
        },

        # === Synthesis Eligibility ===
        "synthesis_eligibility": {
            "NOT_ENOUGH_DATA": {
                "label": "Building Your Pattern Library",
                "icon": "📚",
                "description": "A few more freeform pursuits will reveal your natural methodology"
            },
            "ELIGIBLE": {
                "label": "Ready for Synthesis",
                "icon": "🧪",
                "description": "You have enough data — I can help you capture your methodology"
            },
            "HIGH_CONFIDENCE": {
                "label": "High-Confidence Synthesis Available",
                "icon": "🎯",
                "description": "Strong patterns detected across multiple pursuits"
            }
        },

        # === Coaching Mode ===
        "coaching_mode": {
            "NON_DIRECTIVE": {
                "label": "Responsive",
                "icon": "🙋",
                "description": "I'll help when you ask — you lead the way"
            },
            "EXPLORATORY": {
                "label": "Exploratory",
                "icon": "🔍",
                "description": "Open exploration with guiding questions"
            },
            "CONVERGENT": {
                "label": "Convergent",
                "icon": "🎯",
                "description": "Focusing toward decisions and outcomes"
            },
            "DIRECTIVE": {
                "label": "Directive",
                "icon": "➡️",
                "description": "Clear guidance toward specific goals"
            },
            "REFLECTIVE": {
                "label": "Reflective",
                "icon": "🪞",
                "description": "Reflecting on outcomes and learnings"
            }
        },

        # === Artifact Types ===
        # v3.7.1: Added experiment artifact type for data collection sheets
        "artifact_type": {
            "vision": {
                "label": "Vision Statement",
                "icon": "🎯",
                "description": "Your innovation's problem, solution, and value proposition"
            },
            "fears": {
                "label": "Challenges & Concerns",
                "icon": "⚠️",
                "description": "Identified risks and concerns about the innovation"
            },
            "hypothesis": {
                "label": "Key Hypothesis",
                "icon": "🔬",
                "description": "Assumptions to validate and test methods"
            },
            "experiment": {
                "label": "Data Collection Sheet",
                "icon": "📋",
                "description": "A structured form for recording experiment results"
            },
            "evidence": {
                "label": "Validation Evidence",
                "icon": "✅",
                "description": "Evidence captured from validation experiments"
            }
        },

        # =====================================================================
        # v4.4.1: SCAFFOLDING ELEMENT DISPLAY LABELS
        # =====================================================================
        # Maps internal element names to innovator-facing labels.
        # Critical: Avoid innovation methodology jargon (e.g., "fears")

        "scaffolding_elements": {
            # Vision elements
            "problem_statement": {
                "label": "The Problem You're Solving",
                "icon": "🎯",
                "description": "What challenge or opportunity are you addressing?"
            },
            "target_user": {
                "label": "Who You're Helping",
                "icon": "👤",
                "description": "The people who will benefit from your innovation"
            },
            "current_situation": {
                "label": "How Things Work Today",
                "icon": "📍",
                "description": "The current state before your innovation"
            },
            "pain_points": {
                "label": "What's Not Working",
                "icon": "⚡",
                "description": "The specific frustrations or gaps you're addressing"
            },
            "solution_concept": {
                "label": "Your Solution",
                "icon": "💡",
                "description": "How you're going to solve the problem"
            },
            "value_proposition": {
                "label": "Why It Matters",
                "icon": "✨",
                "description": "The value you're creating for your users"
            },
            "differentiation": {
                "label": "What Makes It Different",
                "icon": "🌟",
                "description": "How your approach stands out from alternatives"
            },
            "success_criteria": {
                "label": "How You'll Know It's Working",
                "icon": "📊",
                "description": "Measurable signs of success"
            },
            # Risk/concern elements (formerly "fears")
            "capability_fears": {
                "label": "Can We Build This?",
                "icon": "🔧",
                "description": "Technical and capability concerns"
            },
            "market_fears": {
                "label": "Will People Want This?",
                "icon": "🎯",
                "description": "Market demand and adoption concerns"
            },
            "resource_fears": {
                "label": "Do We Have What We Need?",
                "icon": "📦",
                "description": "Resource availability concerns"
            },
            "timing_fears": {
                "label": "Is the Timing Right?",
                "icon": "⏰",
                "description": "Market timing and readiness concerns"
            },
            "competition_fears": {
                "label": "What About Competitors?",
                "icon": "🏁",
                "description": "Competitive landscape concerns"
            },
            "personal_fears": {
                "label": "Personal Concerns",
                "icon": "💭",
                "description": "Your personal worries about pursuing this"
            },
            # Validation/hypothesis elements
            "assumption_statement": {
                "label": "What You Believe",
                "icon": "💭",
                "description": "The key assumption you're testing"
            },
            "testable_prediction": {
                "label": "What Should Happen",
                "icon": "🎯",
                "description": "A specific, testable prediction"
            },
            "test_method": {
                "label": "How You'll Test It",
                "icon": "🔬",
                "description": "Your approach to validating the assumption"
            },
            "success_metric": {
                "label": "Success Looks Like",
                "icon": "📈",
                "description": "How you'll measure validation success"
            },
            "failure_criteria": {
                "label": "When to Reconsider",
                "icon": "⚠️",
                "description": "Signs that the assumption may be wrong"
            },
            "learning_plan": {
                "label": "What You'll Learn",
                "icon": "📚",
                "description": "The insights you expect to gain"
            },
            # Market elements
            "competitive_landscape": {
                "label": "Competition Overview",
                "icon": "🏁",
                "description": "Who else is solving this problem"
            },
            "business_model": {
                "label": "How It Makes Money",
                "icon": "💰",
                "description": "Your approach to creating and capturing value"
            },
            "revenue_model": {
                "label": "Revenue Approach",
                "icon": "📊",
                "description": "How revenue will be generated"
            },
            "go_to_market": {
                "label": "Getting to Market",
                "icon": "🚀",
                "description": "Your plan for reaching customers"
            },
            "market_timing": {
                "label": "Market Readiness",
                "icon": "⏱️",
                "description": "Why now is the right time"
            },
            "adoption_barriers": {
                "label": "Adoption Challenges",
                "icon": "🚧",
                "description": "What might slow user adoption"
            },
            # Technical elements
            "technical_feasibility": {
                "label": "Technical Feasibility",
                "icon": "⚙️",
                "description": "Can this be built with available technology?"
            },
            "resource_requirements": {
                "label": "What's Needed to Build",
                "icon": "📦",
                "description": "Resources required for development"
            },
            "team_capabilities": {
                "label": "Team Strengths",
                "icon": "👥",
                "description": "What the team brings to the table"
            },
            "scalability_constraints": {
                "label": "Scaling Considerations",
                "icon": "📈",
                "description": "Factors that affect growth"
            },
            "cost_structure": {
                "label": "Cost Structure",
                "icon": "💵",
                "description": "Key cost drivers and economics"
            },
            # Strategy elements
            "risk_tolerance": {
                "label": "Risk Appetite",
                "icon": "⚖️",
                "description": "How much risk you're willing to take"
            },
            "regulatory_concerns": {
                "label": "Regulatory Landscape",
                "icon": "📋",
                "description": "Compliance and regulatory considerations"
            },
            "partnerships": {
                "label": "Key Partnerships",
                "icon": "🤝",
                "description": "Strategic relationships that matter"
            },
            "stakeholder_alignment": {
                "label": "Stakeholder Buy-In",
                "icon": "✅",
                "description": "Who needs to support this and their status"
            },
            "exit_strategy": {
                "label": "Long-Term Plan",
                "icon": "🎯",
                "description": "Where this is heading long-term"
            },
        },

        # =====================================================================
        # v3.7.2: EMS PATTERN INFERENCE ENGINE & ADL GENERATOR CATEGORIES
        # =====================================================================

        # === Inference Algorithm Names ===
        "inference_algorithm": {
            "sequence_mining": {
                "label": "Activity Pattern Discovery",
                "icon": "🔗",
                "description": "Finding recurring sequences in your innovation activities"
            },
            "phase_clustering": {
                "label": "Phase Identification",
                "icon": "📊",
                "description": "Grouping your activities into natural methodology phases"
            },
            "transition_inference": {
                "label": "Transition Detection",
                "icon": "➡️",
                "description": "Understanding what triggers your phase changes"
            },
            "dependency_mapping": {
                "label": "Activity Relationships",
                "icon": "🕸️",
                "description": "Mapping connections between your tools and artifacts"
            }
        },

        # === Discovered Pattern Types ===
        "pattern_type": {
            "sequence": {
                "label": "Activity Sequence",
                "icon": "🔗",
                "description": "A recurring pattern of activities you perform"
            },
            "phase": {
                "label": "Methodology Phase",
                "icon": "📋",
                "description": "A distinct stage in your innovation process"
            },
            "transition": {
                "label": "Phase Transition",
                "icon": "➡️",
                "description": "How you move between methodology phases"
            },
            "dependency": {
                "label": "Activity Connection",
                "icon": "🔀",
                "description": "A relationship between tools or artifacts"
            }
        },

        # === Confidence Scoring Dimensions ===
        "confidence_dimension": {
            "sample_size": {
                "label": "Data Volume",
                "icon": "📚",
                "description": "Based on the number of pursuits analyzed"
            },
            "consistency": {
                "label": "Pattern Consistency",
                "icon": "🎯",
                "description": "How reliably the pattern appears across pursuits"
            },
            "outcome_association": {
                "label": "Success Correlation",
                "icon": "📈",
                "description": "How strongly the pattern relates to successful outcomes"
            },
            "distinctiveness": {
                "label": "Uniqueness",
                "icon": "✨",
                "description": "How distinctive this pattern is to your approach"
            }
        },

        # === Archetype Origin ===
        "archetype_origin": {
            "prescribed": {
                "label": "Established Methodology",
                "icon": "📖",
                "description": "A well-known innovation methodology"
            },
            "synthesized": {
                "label": "Your Emergent Methodology",
                "icon": "🧬",
                "description": "Discovered from your natural innovation patterns"
            },
            "hybrid": {
                "label": "Adapted Methodology",
                "icon": "🔄",
                "description": "A methodology adapted from your practices"
            }
        },

        # === ADL Synthesis Status ===
        "adl_status": {
            "insufficient_data": {
                "label": "Gathering Patterns",
                "icon": "📊",
                "description": "More pursuits needed to synthesize your methodology"
            },
            "ready": {
                "label": "Ready to Synthesize",
                "icon": "🧪",
                "description": "Enough patterns detected to create your methodology"
            },
            "synthesizing": {
                "label": "Creating Your Methodology",
                "icon": "⚙️",
                "description": "Analyzing patterns and building your methodology"
            },
            "complete": {
                "label": "Methodology Created",
                "icon": "✅",
                "description": "Your emergent methodology has been captured"
            },
            "failed": {
                "label": "Synthesis Incomplete",
                "icon": "⚠️",
                "description": "Unable to identify consistent patterns"
            }
        },

        # === Confidence Level (overall) ===
        "confidence_level": {
            "low": {
                "label": "Emerging",
                "icon": "🌱",
                "description": "Early patterns detected — continue pursuing to strengthen"
            },
            "moderate": {
                "label": "Forming",
                "icon": "🌿",
                "description": "Solid patterns forming — methodology taking shape"
            },
            "high": {
                "label": "Strong",
                "icon": "🌳",
                "description": "Clear, consistent patterns across your pursuits"
            },
            "very_high": {
                "label": "Definitive",
                "icon": "⭐",
                "description": "Highly distinctive methodology clearly identified"
            }
        },

        # === Dependency Relationship Types ===
        "dependency_type": {
            "enables": {
                "label": "Enables",
                "icon": "→",
                "description": "This activity enables the next"
            },
            "precedes": {
                "label": "Typically Before",
                "icon": "↗️",
                "description": "This activity usually comes before"
            },
            "immediately_precedes": {
                "label": "Directly Before",
                "icon": "➡️",
                "description": "This activity comes directly before"
            },
            "co_occurs": {
                "label": "Often Together",
                "icon": "↔️",
                "description": "These activities often happen together"
            }
        },

        # =====================================================================
        # v3.7.3: EMS REVIEW & PUBLICATION CATEGORIES
        # =====================================================================

        # === Review Session Status ===
        "review_status": {
            "INITIATED": {
                "label": "Review Starting",
                "icon": "clipboard",
                "description": "Beginning your methodology review"
            },
            "IN_PROGRESS": {
                "label": "Reviewing Your Process",
                "icon": "search",
                "description": "Walking through your discovered methodology"
            },
            "APPROVED": {
                "label": "Methodology Approved",
                "icon": "check_circle",
                "description": "Your methodology is ready to publish"
            },
            "REJECTED": {
                "label": "Draft Set Aside",
                "icon": "folder",
                "description": "This draft was set aside — you can try again later"
            },
            "ABANDONED": {
                "label": "Review Paused",
                "icon": "pause",
                "description": "Review paused — continue whenever you're ready"
            }
        },

        # === Refinement Actions (for review audit trail display) ===
        "refinement_action": {
            "RENAMED_PHASE": {
                "label": "Renamed a Phase",
                "icon": "edit",
                "description": "Changed the name of a methodology phase"
            },
            "REORDERED": {
                "label": "Reordered Phases",
                "icon": "swap_vert",
                "description": "Changed the order of phases"
            },
            "ADDED_ACTIVITY": {
                "label": "Added an Activity",
                "icon": "add",
                "description": "Added a new activity to a phase"
            },
            "REMOVED_ACTIVITY": {
                "label": "Removed an Activity",
                "icon": "remove",
                "description": "Removed an activity from a phase"
            },
            "MARKED_OPTIONAL": {
                "label": "Marked as Optional",
                "icon": "help",
                "description": "Made this activity optional rather than required"
            },
            "MARKED_REQUIRED": {
                "label": "Marked as Required",
                "icon": "priority_high",
                "description": "Made this activity required"
            },
            "ADDED_PRINCIPLE": {
                "label": "Added a Principle",
                "icon": "lightbulb",
                "description": "Added a key principle to your methodology"
            },
            "MERGED_PHASES": {
                "label": "Combined Two Phases",
                "icon": "link",
                "description": "Merged two phases into one"
            },
            "SPLIT_PHASE": {
                "label": "Split into Two Phases",
                "icon": "content_cut",
                "description": "Split one phase into two separate phases"
            },
            "REJECTION": {
                "label": "Rejected Methodology",
                "icon": "cancel",
                "description": "Decided not to publish this methodology"
            }
        },

        # === Methodology Visibility Levels ===
        "methodology_visibility": {
            "PERSONAL": {
                "label": "Just for Me",
                "icon": "lock",
                "description": "Only you can see and use this methodology"
            },
            "TEAM": {
                "label": "My Team",
                "icon": "group",
                "description": "Shared with your pursuit team members"
            },
            "ORGANIZATION": {
                "label": "My Organization",
                "icon": "business",
                "description": "Available to everyone in your organization"
            },
            "IKF_SHARED": {
                "label": "Innovation Network",
                "icon": "public",
                "description": "Shared with the global innovation community"
            }
        },

        # === Archetype Version Status ===
        "archetype_version": {
            "CURRENT": {
                "label": "Current Version",
                "icon": "check",
                "description": "This is the latest version of your methodology"
            },
            "SUPERSEDED": {
                "label": "Previous Version",
                "icon": "inventory",
                "description": "A newer version of this methodology exists"
            },
            "EVOLVING": {
                "label": "Update Available",
                "icon": "refresh",
                "description": "New insights suggest your methodology could evolve"
            }
        },

        # ═══════════════════════════════════════════════════════════════════
        # v4.0 MOMENTUM MANAGEMENT — INNOVATOR-FACING LABEL CATEGORIES
        # ═══════════════════════════════════════════════════════════════════
        # Design rule: Every label must pass the Innovator Test.
        # "If I had never heard of innovation methodology, would this label
        # make sense to me in the context of my idea?"
        # ───────────────────────────────────────────────────────────────────

        # === Primary Navigation / Workflow Steps (replaces module names) ===
        "workflow_step": {
            "vision_formulator": {
                "label": "Tell Your Story",
                "icon": "✍️",
                "description": "Articulate what you're building and who it's for",
                "novice_hint": "Start here — describe your idea in your own words"
            },
            "fear_extraction": {
                "label": "Protect Your Idea",
                "icon": "🛡️",
                "description": "Identify what could get in the way — and how to address it",
                "novice_hint": "Every strong idea has risks. Let's find yours before they find you."
            },
            "risk_validation": {
                "label": "Test Your Assumptions",
                "icon": "🔬",
                "description": "Determine what you need to learn before building further",
                "novice_hint": "What do you believe about this idea that might not be true yet?"
            },
            "methodology_selection": {
                "label": None,  # SUPPRESSED for novice — handled invisibly by coach
                "icon": None,
                "description": "Coaching approach selection (handled automatically for most innovators)",
                "novice_hint": None,
                "novice_visible": False  # Key flag — do not render in novice path
            },
            "retrospective": {
                "label": "What Did We Learn?",
                "icon": "💡",
                "description": "Capture the insights from your innovation journey",
                "novice_hint": "Every pursuit — successful or not — has lessons worth keeping."
            },
            "coaching": {
                "label": "Talk to Your Coach",
                "icon": "💬",
                "description": "Continue your coaching conversation",
                "novice_hint": "Your coach is ready when you are."
            },
        },

        # === Artifact Panel Headers ===
        "artifact_panel": {
            "vision": {
                "label": "Your Innovation Story",
                "icon": "📖",
                "description": "The narrative of your idea — who it helps, why it matters"
            },
            "fear": {
                "label": "Risks & Protections",
                "icon": "🛡️",
                "description": "What could get in the way, and how to address it"
            },
            "validation": {
                "label": "What You've Tested",
                "icon": "🔬",
                "description": "Assumptions explored and evidence gathered"
            },
            "coaching_history": {
                "label": "Your Coaching Journey",
                "icon": "💬",
                "description": "A record of your conversations and insights"
            },
            "timeline": {
                "label": "Your Idea Over Time",
                "icon": "📅",
                "description": "Key moments and milestones in your innovation pursuit"
            },
            "retrospective": {
                "label": "Lessons Learned",
                "icon": "💡",
                "description": "What this pursuit taught you"
            },
        },

        # === Pursuit Lifecycle States (innovator-facing display) ===
        # Internal enum values → depth-framing display labels
        "pursuit_state_display": {
            # ACTIVE states — express as depth, not distance
            "INCEPTION": {
                "label": "Just Getting Started",
                "icon": "🌱",
                "description": "Your idea is taking its first shape",
                "color_hint": "green"
            },
            "EXPLORATION": {
                "label": "Deepening Your Idea",
                "icon": "🔍",
                "description": "Learning what you need to know about the problem and the people it affects",
                "color_hint": "blue"
            },
            "VALIDATION": {
                "label": "Testing What You Believe",
                "icon": "🔬",
                "description": "Checking your most important assumptions against reality",
                "color_hint": "purple"
            },
            "DEVELOPMENT": {
                "label": "Building It Out",
                "icon": "🔧",
                "description": "Taking your validated concept forward",
                "color_hint": "amber"
            },
            "DEPLOYMENT": {
                "label": "Getting It Out There",
                "icon": "🚀",
                "description": "Bringing your idea into the world",
                "color_hint": "gold"
            },
            # SUCCESS states
            "COMPLETED.SUCCESSFUL": {
                "label": "Idea Launched",
                "icon": "🎉",
                "description": "This pursuit achieved its goal",
                "color_hint": "green"
            },
            "COMPLETED.PARTIAL": {
                "label": "Partially Achieved",
                "icon": "✅",
                "description": "This pursuit moved forward and captured learning",
                "color_hint": "blue"
            },
            # TERMINAL states — human, non-clinical framing
            "TERMINATED.ABANDONED": {
                "label": "Pursuit Closed",
                "icon": "📁",
                "description": "This pursuit was closed before completion",
                "color_hint": "gray"
            },
            "TERMINATED.BLOCKED": {
                "label": "Blocked — On Hold",
                "icon": "⏸️",
                "description": "External factors prevented this pursuit from continuing",
                "color_hint": "amber"
            },
            "TERMINATED.INFEASIBLE": {
                "label": "Not the Right Path",
                "icon": "🔄",
                "description": "Evidence showed this direction wouldn't work — a valuable finding",
                "color_hint": "blue"
            },
            "TERMINATED.SUPERSEDED": {
                "label": "Replaced by a Better Idea",
                "icon": "⬆️",
                "description": "A stronger approach made this pursuit redundant",
                "color_hint": "purple"
            },
            "TERMINATED.PIVOT": {
                "label": "Pivoted to New Direction",
                "icon": "↪️",
                "description": "Learning from this pursuit created a new path forward",
                "color_hint": "green"
            },
            "SUSPENDED": {
                "label": "Paused",
                "icon": "⏸️",
                "description": "This pursuit is paused and can be resumed",
                "color_hint": "gray"
            },
        },

        # === Onboarding Path Cards ===
        "onboarding_path": {
            "vision_formulator": {
                "label": "Tell Your Story",
                "duration_hint": "About 15–20 minutes",
                "description": "Turn your idea into a clear, compelling narrative — who it helps, why it matters, and what makes it different.",
                "cta": "Start Here →"
            },
            "fear_extraction": {
                "label": "Strengthen Your Idea",
                "duration_hint": "About 10–12 minutes",
                "description": "Every strong idea has risks hiding inside it. We'll find yours — and figure out how to get ahead of them.",
                "cta": "Let's Protect It →"
            },
            "validation": {
                "label": "Test What You Believe",
                "duration_hint": "About 10–15 minutes",
                "description": "There are things you believe about this idea that haven't been tested yet. We'll figure out what to check first.",
                "cta": "Start Testing →"
            },
            # Methodology selection card is REMOVED from novice path entirely
            # Expert and intermediate paths retain it under their own label
            "methodology_expert": {
                "label": "Choose Your Approach",
                "duration_hint": "About 5 minutes",
                "description": "Select the innovation methodology that best fits your pursuit context.",
                "cta": "Configure →"
            },
        },

        # === Role Detection (Onboarding Screen 1) ===
        "innovator_role": {
            "novice": {
                "label": "Exploring an Idea",
                "description": "You have an idea or problem you want to develop — let's figure it out together.",
                "icon": "💡"
            },
            "intermediate": {
                "label": "Leading an Initiative",
                "description": "You're driving an innovation project and want structured support.",
                "icon": "🎯"
            },
            "expert": {
                "label": "Running a Pivot or Portfolio",
                "description": "You've done this before and want full control over your methodology.",
                "icon": "⚡"
            },
            "demo": {
                "label": "Exploring the Platform",
                "description": "Take a guided tour with sample pursuits — no commitment required.",
                "icon": "🗺️"
            },
        },

        # === Depth-Framed Progress Language (replaces % complete / step N of M) ===
        "depth_progress": {
            "idea_forming": {
                "label": "Your idea is taking shape",
                "sublabel": "You've described the problem and who it affects"
            },
            "idea_sharpening": {
                "label": "Your idea is getting sharper",
                "sublabel": "You've articulated the value and started identifying risks"
            },
            "idea_tested": {
                "label": "Your idea is battle-tested",
                "sublabel": "You've explored risks and identified key assumptions to validate"
            },
            "idea_advancing": {
                "label": "Your idea is moving forward",
                "sublabel": "You've validated the core assumptions and are building momentum"
            },
            "idea_ready": {
                "label": "Your idea is ready",
                "sublabel": "You've prepared this idea to go into the world"
            },
        },

        # === Re-Engagement Language (async coaching cadence) ===
        "re_engagement": {
            "bridge_prompt_prefix": {
                "label": "Your idea has been waiting."
            },
            "bridge_cta": {
                "label": "Pick up where you left off →"
            },
            "session_gap_label": {
                "label": "You were last here"
            },
            "return_greeting_high_momentum": {
                "label": "Welcome back. You were on a roll."
            },
            "return_greeting_neutral": {
                "label": "Good to have you back."
            },
            "return_greeting_low_momentum": {
                "label": "Your idea is still here. Let's pick it back up."
            },
        },

        # ═══════════════════════════════════════════════════════════════════════════════
        # v4.3 ADDITIONS — Depth Frame Visual Identity
        # ═══════════════════════════════════════════════════════════════════════════════

        # DEPTH_DIMENSIONS: Innovator-facing names for the five depth dimensions
        "depth_dimensions": {
            "clarity": {
                "label": "How clear is your idea",
            },
            "empathy": {
                "label": "How well you know who you're helping",
            },
            "protection": {
                "label": "How well your idea is protected",
            },
            "evidence": {
                "label": "How much you've tested it",
            },
            "specificity": {
                "label": "How specific and actionable it is",
            },
        },

        # DEPTH_RICHNESS_SIGNALS: Qualitative language for each score tier
        # Used by ArtifactRichnessSignal and DepthDimensionBar
        "depth_richness_signals": {
            "nascent": {
                "label": "Just beginning",
            },
            "emerging": {
                "label": "Taking shape",
            },
            "developing": {
                "label": "Getting stronger",
            },
            "solid": {
                "label": "Well established",
            },
            "rich": {
                "label": "Deeply developed",
            },
        },

        # NAVIGATION_SECTIONS: Goal-language section headers for the Navigator panel
        # Replaces module-named sections (v4.0 language audit Phase 3 completions)
        "navigation_sections": {
            "tell_your_story": {
                "label": "Tell Your Story",
            },
            "protect_your_idea": {
                "label": "Protect Your Idea",
            },
            "test_your_assumptions": {
                "label": "Test Your Assumptions",
            },
            "sharpen_and_refine": {
                "label": "Sharpen and Refine",
            },
            "prepare_to_launch": {
                "label": "Prepare to Launch",
            },
            "your_team": {
                "label": "Your Team",
                "visibility": "team_mode",
            },
            "your_portfolio": {
                "label": "Your Portfolio",
                "visibility": "enterprise_mode",
            },
        },

        # ARTIFACT_RICHNESS_SIGNALS: Per-artifact qualitative labels
        "artifact_richness_signals": {
            "vision": {
                "label": "Your story is taking shape",
            },
            "fear": {
                "label": "Your idea is better protected",
            },
            "hypothesis": {
                "label": "Your thinking is getting sharper",
            },
            "test_plan": {
                "label": "You have a clear test ahead",
            },
            "experiment": {
                "label": "You've learned something real",
            },
            "value_prop": {
                "label": "Your idea is more compelling",
            },
            "risk_assessment": {
                "label": "You see more clearly what to watch for",
            },
            "silr": {
                "label": "A full picture of where you are",
            },
        },

        # TIM_DEPTH_LABELS: Depth-framed milestone labels for novice mode
        "tim_depth_labels": {
            "vision_first": {
                "label": "Your story first took shape",
            },
            "fear_surfaced": {
                "label": "You started protecting your idea",
            },
            "first_hypothesis": {
                "label": "You formed your first real question",
            },
            "first_evidence": {
                "label": "You got your first real answer",
            },
            "idea_sharpened": {
                "label": "Your idea became more specific",
            },
            "ready_to_test": {
                "label": "You were ready to test it in the world",
            },
            "idea_at_launch": {
                "label": "Your idea at its most developed",
            },
        },

        # ONBOARDING_DEPTH_FRAMING: Idea-first copy for the onboarding screens
        "onboarding_depth_framing": {
            "screen_1_title": {
                "label": "What's the idea you're working on?",
            },
            "screen_1_body": {
                "label": "Start by telling us what you're trying to build, solve, or change.",
            },
            "screen_2_title": {
                "label": "Your idea will get sharper as we work together",
            },
            "screen_2_body": {
                "label": "We'll help you understand it more deeply - who it helps, what could go wrong, and how to test it.",
            },
            "screen_3_title": {
                "label": "Everything you build here stays with you",
            },
            "screen_3_body": {
                "label": "Every question you answer and insight you capture makes your idea more defensible.",
            },
            "screen_4_title": {
                "label": "You're in control of the pace",
            },
            "screen_4_body": {
                "label": "Come back when you have something to think through. Your idea will be exactly where you left it.",
            },
            "screen_5_cta": {
                "label": "Start developing my idea",
            },
        },

        # EXPERIENCE_MODE_LABELS: Settings UI copy for the experience toggle
        "experience_mode_labels": {
            "novice": {
                "label": "Show me depth and richness",
                "description": "Progress shown as how rich and specific your idea is becoming.",
            },
            "intermediate": {
                "label": "Show me steps and depth",
                "description": "Combination of depth language and progress milestones.",
            },
            "expert": {
                "label": "Show me phases and detail",
                "description": "Full methodology visibility including phase indicators.",
            },
        },
    }

    @classmethod
    def get(cls, category: str, value, field: str = "label") -> str:
        """
        Get a display label for an internal value.

        Args:
            category: Registry category (e.g., "package_type")
            value: Internal value to translate (e.g., "temporal_benchmark")
            field: Which field to return ("label", "icon", "description")

        Returns:
            Human-readable string, or the original value if no mapping exists.
            NEVER returns None — unknown values pass through unchanged with
            a logged warning for developer attention.
        """
        cat = cls._REGISTRY.get(category)
        if cat is None:
            logger.warning(f"DisplayLabels: Unknown category '{category}'")
            return str(value)

        entry = cat.get(value)
        if entry is None:
            logger.warning(f"DisplayLabels: Unknown value '{value}' in category '{category}'")
            return str(value)

        return entry.get(field, entry.get("label", str(value)))

    @classmethod
    def get_with_icon(cls, category: str, value) -> str:
        """
        Get label with prepended icon: "🚀 Ready to Share"
        """
        icon = cls.get(category, value, "icon")
        label = cls.get(category, value, "label")
        if icon and icon != str(value):
            return f"{icon} {label}"
        return label

    @classmethod
    def get_workflow_step(cls, step_key: str, experience_level: str = "novice") -> dict | None:
        """
        Returns the full workflow step entry for a given internal step key.

        Returns None if the step should not be rendered for the given
        experience level (e.g., methodology_selection for novice users).

        Args:
            step_key: Internal step identifier (e.g., "fear_extraction")
            experience_level: "novice", "intermediate", or "expert"

        Returns:
            dict with label, icon, description, novice_hint
            None if step is suppressed for this experience level
        """
        entry = cls._REGISTRY.get("workflow_step", {}).get(step_key)
        if not entry:
            return None

        # Check visibility flag — novice path suppresses methodology_selection
        if experience_level == "novice" and not entry.get("novice_visible", True):
            return None

        return entry

    @classmethod
    def get_pursuit_state(cls, state: str) -> dict:
        """
        Returns the innovator-facing label for a pursuit lifecycle state.

        Falls back gracefully — never exposes the raw enum value.
        """
        entry = cls._REGISTRY.get("pursuit_state_display", {}).get(state)
        if entry:
            return entry
        # Safe fallback — the raw state must never reach the UI
        return {
            "label": "In Progress",
            "icon": "⚙️",
            "description": "Your pursuit is active",
            "color_hint": "gray"
        }

    @classmethod
    def get_all(cls, category: str) -> dict:
        """
        Get all entries for a category. Used for populating dropdowns,
        filter options, and preference panels.
        """
        return cls._REGISTRY.get(category, {})

    @classmethod
    def register(cls, category: str, value, label: str,
                 icon: str = None, description: str = None):
        """
        Register a new display label at runtime. Used by modules that
        add categories during initialization (e.g., EMS in v3.7.1+).

        This enables extensibility without modifying the core registry file.
        """
        if category not in cls._REGISTRY:
            cls._REGISTRY[category] = {}

        entry = {"label": label}
        if icon:
            entry["icon"] = icon
        if description:
            entry["description"] = description

        cls._REGISTRY[category][value] = entry

    @classmethod
    def pii_confidence_level(cls, score: float) -> str:
        """
        Convert a raw PII confidence float to a traffic light category.

        Args:
            score: Raw PII confidence (0.0-1.0)

        Returns:
            Traffic light category key ("green", "yellow", "red")
        """
        if score >= 0.85:
            return "red"
        elif score >= 0.5:
            return "yellow"
        else:
            return "green"

    @classmethod
    def get_category_count(cls) -> int:
        """Return the number of registered categories."""
        return len(cls._REGISTRY)

    @classmethod
    def get_total_label_count(cls) -> int:
        """Return the total number of registered labels across all categories."""
        return sum(len(v) for v in cls._REGISTRY.values())

    @classmethod
    def get_all_categories(cls) -> dict:
        """
        Return all Display Labels organized by category.

        Used by the frontend to fetch all labels at startup and cache them
        for the session lifetime.

        Returns:
            dict: Nested dict of category -> value -> {label, icon, description}
        """
        return cls._REGISTRY.copy()
