#!/usr/bin/env python3
"""
InDE MVP v3.9 - Application Launcher
Innovation Development Environment - "Commercial Launch Infrastructure"

Usage:
    python run_inde.py          # Launch GUI (default)
    python run_inde.py --gui    # Launch GUI explicitly
    python run_inde.py --cli    # Launch CLI mode
    python run_inde.py --test   # Run test scenario

Features (v3.0.2 - Intelligence Layer):
- Health Monitor: Real-time pursuit health scoring (0-100) with 5 zones
- Temporal Pattern Intelligence: Enriched IML pattern matching with temporal signals
- Predictive Guidance Engine: Forward-looking predictions
- Full RVE: Experiment wizard, three-zone assessment, override capture
- Temporal Risk Detection: Short/medium/long-term risk identification
- Health badge in UI header showing zone and score

Features (maintained from v3.0.1 - Temporal Foundation):
- Temporal Intelligence Module (TIM): Phase-based timeline management
- Time Allocation Engine: Percentage-based phase distribution
- Velocity Tracker: Progress pace monitoring (elements/week)
- Temporal Event Logger: IKF-compatible event stream
- Phase Manager: Automatic phase transition detection
- Timeline Panel: Visual progress tracking in UI
- All timestamps use ISO 8601 format for IKF compatibility

Features (maintained from v2.9):
- Report Distribution: Email distribution, shareable links, batch distribution
- Pursuit Sharing: Public/unlisted/private shareable views with viral CTAs
- Stakeholder Response Capture: Feedback widgets, conversation threading
- Basic Collaboration: Comments, @mentions, activity feeds

Features (maintained from v2.8):
- Report Intelligence: Living Snapshot and Portfolio Analytics reports
- Template Selection: Choose report format (SILR-Light, Investor, etc.)
- Retrospective Flexibility: Early exit and pause/resume support

Features (maintained from v2.7):
- Terminal State Detection: Automatic detection of pursuit conclusions
- Retrospective Orchestrator: Guided end-of-pursuit conversations
- Terminal Reports (SILR): Standardized Innovation Lifecycle Reports
- Portfolio Manager: Track terminal state distribution and learning
- Learning Insights: Historical pattern analysis and proactive guidance

Features (maintained from v2.6):
- Stakeholder Feedback Capture: Quick form, conversational, and batch input
- Support Landscape Analysis: Aggregate stakeholder support intelligence

Features (maintained from v2.5):
- Pattern Intelligence: IML integration for historical pattern matching
- Adaptive Interventions: Engagement-based cooldown adjustment
- 40-element tracking (20 critical + 20 important)
- Cross-pursuit insights: Surface connections between user's pursuits
- All coaching remains invisible - users never see methodology
"""

import sys
import argparse

# Add app directory to path for imports
sys.path.insert(0, './app')

from config import VERSION, VERSION_NAME, USE_MONGOMOCK, GRADIO_HOST, GRADIO_PORT


def print_banner():
    """Print startup banner."""
    print(f"""
    +==============================================================+
    |                                                              |
    |     InDE - Innovation Development Environment                |
    |     Version {VERSION} "{VERSION_NAME}"                    |
    |                                                              |
    |     "If the innovator can see the scaffolding, we failed."   |
    |                                                              |
    +==============================================================+
    """)


def init_engine():
    """Initialize the scaffolding engine with database and LLM."""
    from core.database import db
    from core.llm_interface import LLMInterface
    from scaffolding.engine import ScaffoldingEngine

    llm = LLMInterface()
    engine = ScaffoldingEngine(db, llm)

    return engine


def run_gui():
    """Launch the Gradio GUI."""
    print_banner()
    print(f"[InDE] Starting GUI mode...")
    print(f"[InDE] Demo mode: {USE_MONGOMOCK}")

    engine = init_engine()

    from ui.chat_interface import launch_interface
    print(f"[InDE] Launching interface at http://{GRADIO_HOST}:{GRADIO_PORT}")
    launch_interface(engine)


def run_cli():
    """Run CLI mode for testing."""
    print_banner()
    print("[InDE] Starting CLI mode...")
    print("[InDE] Type 'quit' or 'exit' to end the session.")
    print("[InDE] Type 'status' to see current pursuit status.")
    print("[InDE] Type 'artifacts' to see generated artifacts.")
    print("[InDE] Type 'portfolio' to see portfolio summary.")
    print("[InDE] Type 'insights' to see learning insights.")
    print("[InDE] Type 'velocity' to see progress velocity (v3.0.1).")
    print("[InDE] Type 'timeline' to see timeline events (v3.0.1).")
    print("[InDE] Type 'health' to see pursuit health score (v3.0.2).")
    print("[InDE] Type 'risks' to see risk detection (v3.0.2).")
    print("[InDE] Type 'predictions' to see predictions (v3.0.2).")
    print("-" * 60)

    engine = init_engine()
    current_pursuit_id = None

    while True:
        try:
            # v2.7: Show retrospective mode indicator
            prompt = "\nYou: "
            if current_pursuit_id and engine.is_in_retrospective_mode(current_pursuit_id):
                progress = engine.get_retrospective_progress(current_pursuit_id)
                prompt = f"\n[RETROSPECTIVE {progress}%] You: "

            user_input = input(prompt).strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit']:
                print("\n[InDE] Goodbye! Keep innovating!")
                break

            if user_input.lower() == 'status':
                if current_pursuit_id:
                    context = engine._get_pursuit_context(current_pursuit_id)
                    completeness = context.get("completeness", {})
                    pursuit = engine.db.get_pursuit(current_pursuit_id)
                    state = pursuit.get("state", "ACTIVE") if pursuit else "ACTIVE"
                    print(f"\n[Status] Pursuit: {context.get('title')}")
                    print(f"  State: {state}")
                    print(f"  Vision: {int(completeness.get('vision', 0) * 100)}%")
                    print(f"  Fears: {int(completeness.get('fears', 0) * 100)}%")
                    print(f"  Hypothesis: {int(completeness.get('hypothesis', 0) * 100)}%")
                    if engine.is_in_retrospective_mode(current_pursuit_id):
                        print(f"  [IN RETROSPECTIVE MODE]")
                else:
                    print("\n[Status] No active pursuit. Start by describing an idea.")
                continue

            if user_input.lower() == 'artifacts':
                if current_pursuit_id:
                    artifacts = engine.get_pursuit_artifacts(current_pursuit_id)
                    if artifacts:
                        for a in artifacts:
                            print(f"\n=== {a['type'].upper()} ===")
                            print(a['content'])
                    else:
                        print("\n[Artifacts] No artifacts generated yet.")
                else:
                    print("\n[Artifacts] No active pursuit.")
                continue

            # v2.7: Portfolio command
            if user_input.lower() == 'portfolio':
                summary = engine.get_portfolio_summary()
                print(f"\n[Portfolio Summary]")
                print(f"  Total Pursuits: {summary.get('total_pursuits', 0)}")
                print(f"  Active: {summary.get('active_count', 0)}")
                print(f"  Completed: {summary.get('completed_count', 0)}")
                print(f"  Terminated: {summary.get('terminated_count', 0)}")
                print(f"  Patterns Learned: {summary.get('patterns_extracted', 0)}")
                print(f"  Success Rate: {summary.get('completion_rate', 0) * 100:.0f}%")
                continue

            # v2.7: Insights command
            if user_input.lower() == 'insights':
                insights = engine.get_learning_insights()
                if insights.get("insights"):
                    print(f"\n[Learning Insights]")
                    for insight in insights.get("insights", [])[:5]:
                        print(f"  - {insight.get('insight', 'Unknown')}")
                    if insights.get("recommendations"):
                        print(f"\n[Recommendations]")
                        for rec in insights.get("recommendations", [])[:3]:
                            print(f"  - {rec}")
                else:
                    print("\n[Insights] Need more pursuit history to generate insights.")
                continue

            # v3.0.1: Velocity command (TIM)
            if user_input.lower() == 'velocity':
                if current_pursuit_id:
                    velocity = engine.get_velocity_summary(current_pursuit_id)
                    if velocity and velocity.get("current"):
                        current = velocity["current"]
                        print(f"\n[Velocity Summary]")
                        print(f"  Pace: {current.get('elements_per_week', 0):.1f} elements/week")
                        print(f"  Expected: {current.get('expected_velocity', 0):.1f} elements/week")
                        print(f"  Status: {current.get('status', 'unknown')}")
                        print(f"  Trend: {current.get('trend', 'unknown')}")

                        projection = velocity.get("projection", {})
                        if projection.get("projected_date"):
                            print(f"\n[Completion Projection]")
                            print(f"  Target: {projection.get('target_date', '')[:10]}")
                            print(f"  Projected: {projection.get('projected_date', '')[:10]}")
                            days_diff = projection.get("days_ahead_behind", 0)
                            if days_diff > 0:
                                print(f"  Status: {days_diff} days ahead")
                            elif days_diff < 0:
                                print(f"  Status: {abs(days_diff)} days behind")
                            else:
                                print(f"  Status: On target")
                    else:
                        print("\n[Velocity] Not enough data yet.")
                else:
                    print("\n[Velocity] No active pursuit.")
                continue

            # v3.0.1: Timeline command (TIM)
            if user_input.lower() == 'timeline':
                if current_pursuit_id:
                    events = engine.get_timeline_events(current_pursuit_id, limit=10)
                    if events:
                        print(f"\n[Recent Timeline Events]")
                        for event in events:
                            ts = event.get("timestamp", "")[:16].replace("T", " ")
                            etype = event.get("event_type", "").replace("_", " ").title()
                            phase = event.get("phase", "")
                            print(f"  {ts} | {etype} ({phase})")
                    else:
                        print("\n[Timeline] No events yet.")

                    # Show phase summary
                    phase_summary = engine.get_phase_summary(current_pursuit_id)
                    if phase_summary:
                        print(f"\n[Phase Status] Current: {phase_summary.get('current_phase', 'VISION')}")
                else:
                    print("\n[Timeline] No active pursuit.")
                continue

            # v3.0.2: Health command (Intelligence Layer)
            if user_input.lower() == 'health':
                if current_pursuit_id:
                    health = engine.get_health_score(current_pursuit_id)
                    if health and not health.get("error"):
                        print(f"\n[Health Summary]")
                        print(f"  Score: {health.get('health_score', 50):.0f}/100")
                        print(f"  Zone: {health.get('zone', 'UNKNOWN')}")

                        components = health.get("components", {})
                        if components:
                            print(f"\n[Component Scores]")
                            for comp, score in components.items():
                                label = comp.replace("_", " ").title()
                                print(f"  {label}: {score:.0f}%")

                        if health.get("crisis_triggered"):
                            print(f"\n  [CRISIS MODE TRIGGERED]")

                        # Show trend
                        trend = engine.get_health_trend(current_pursuit_id)
                        if trend:
                            print(f"\n[Trend] {trend.get('trend', 'stable').title()} ({trend.get('change', 0):+.0f} pts)")
                    else:
                        print("\n[Health] Could not calculate health score.")
                else:
                    print("\n[Health] No active pursuit.")
                continue

            # v3.0.2: Risks command (Intelligence Layer)
            if user_input.lower() == 'risks':
                if current_pursuit_id:
                    detection = engine.get_risk_detection(current_pursuit_id)
                    if detection and not detection.get("detection_disabled"):
                        print(f"\n[Risk Detection]")
                        print(f"  Overall Level: {detection.get('overall_risk_level', 'UNKNOWN')}")
                        print(f"  Total Risks: {detection.get('risk_count', 0)}")

                        top_risks = detection.get("top_risks", [])
                        if top_risks:
                            print(f"\n[Top Risks]")
                            for risk in top_risks[:3]:
                                severity = risk.get("severity", "?")
                                title = risk.get("title", "Unknown")
                                print(f"  [{severity}] {title}")

                        recs = detection.get("recommendations", [])
                        if recs:
                            print(f"\n[Recommendations]")
                            for rec in recs[:3]:
                                print(f"  - {rec}")
                    else:
                        print("\n[Risks] Risk detection not available.")
                else:
                    print("\n[Risks] No active pursuit.")
                continue

            # v3.0.2: Predictions command (Intelligence Layer)
            if user_input.lower() == 'predictions':
                if current_pursuit_id:
                    predictions = engine.get_predictions(current_pursuit_id)
                    if predictions:
                        print(f"\n[Predictions] ({len(predictions)} found)")
                        for pred in predictions[:3]:
                            ptype = pred.get("type", "").replace("_", " ").title()
                            conf = pred.get("confidence", 0) * 100
                            title = pred.get("title", "Unknown")
                            desc = pred.get("description", "")[:80]
                            print(f"\n  [{ptype}] ({conf:.0f}% conf)")
                            print(f"  {title}")
                            print(f"  {desc}...")
                    else:
                        print("\n[Predictions] No predictions available yet.")
                else:
                    print("\n[Predictions] No active pursuit.")
                continue

            # Process message
            result = engine.process_message(
                message=user_input,
                current_pursuit_id=current_pursuit_id
            )

            response = result.get("response", "")
            new_pursuit_id = result.get("pursuit_id")
            pursuit_title = result.get("pursuit_title")

            # v2.7: Check retrospective mode
            retrospective_mode = result.get("retrospective_mode", False)
            if retrospective_mode:
                progress = result.get("retrospective_progress", 0)
                print(f"\n[RETROSPECTIVE MODE - {progress}% complete]")

            # Update current pursuit
            if new_pursuit_id and new_pursuit_id != current_pursuit_id:
                current_pursuit_id = new_pursuit_id
                print(f"\n[InDE] Working on: {pursuit_title}")

            print(f"\nCoach: {response}")

            # Show artifact if generated
            if result.get("artifact_content"):
                print("\n" + "=" * 60)
                print(result["artifact_content"])
                print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n[InDE] Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] {e}")


def run_test():
    """Run the Danger Doll test scenario."""
    print_banner()
    print("[InDE] Running Danger Doll test scenario...")
    print("-" * 60)

    engine = init_engine()

    # Test messages from the Danger Doll scenario
    test_messages = [
        'I want to design a new toy called "Danger Doll" to detect and warn children of hazards like smoke or gas.',
        "Probably ages 3-8. Young enough that a doll is appealing, old enough to understand and respond to warnings.",
        "My sister's house had a carbon monoxide leak last year. Her smoke detectors worked but her 4-year-old didn't understand the urgency. She kept playing until my sister physically carried her out.",
        "Honestly? I'm not an engineer. I don't know if the sensor technology could even fit in a doll. And what if it malfunctions?",
        "Yes, that would be great."  # Accept vision generation
    ]

    current_pursuit_id = None

    for i, message in enumerate(test_messages, 1):
        print(f"\n[Test {i}] User: {message}")

        result = engine.process_message(
            message=message,
            current_pursuit_id=current_pursuit_id
        )

        response = result.get("response", "")
        new_pursuit_id = result.get("pursuit_id")
        pursuit_title = result.get("pursuit_title")
        intervention = result.get("intervention_made")

        if new_pursuit_id and new_pursuit_id != current_pursuit_id:
            current_pursuit_id = new_pursuit_id
            print(f"[System] Auto-created pursuit: {pursuit_title}")

        print(f"[Test {i}] Coach: {response}")

        if intervention:
            print(f"[System] Intervention: {intervention}")

        if result.get("artifact_content"):
            print(f"\n[System] Artifact Generated:")
            print("=" * 40)
            print(result["artifact_content"][:500] + "..." if len(result.get("artifact_content", "")) > 500 else result["artifact_content"])
            print("=" * 40)

        # Show completeness after each turn
        if current_pursuit_id:
            context = engine._get_pursuit_context(current_pursuit_id)
            comp = context.get("completeness", {})
            print(f"[Status] Vision: {int(comp.get('vision', 0) * 100)}%, Fears: {int(comp.get('fears', 0) * 100)}%")

    print("\n" + "-" * 60)
    print("[InDE] Test scenario complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=f"InDE v{VERSION} - Innovation Development Environment"
    )
    parser.add_argument(
        '--gui', action='store_true',
        help='Launch GUI mode (default)'
    )
    parser.add_argument(
        '--cli', action='store_true',
        help='Launch CLI mode'
    )
    parser.add_argument(
        '--test', action='store_true',
        help='Run Danger Doll test scenario'
    )

    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.cli:
        run_cli()
    else:
        # Default to GUI
        run_gui()


if __name__ == "__main__":
    main()
