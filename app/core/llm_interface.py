"""
InDE MVP v3.9 - LLM Interface "Air-Gapped Intelligence"

Manages all LLM calls with token budget tracking.
Supports multiple providers through LLM Gateway with automatic failover.

v3.9 Enhancement: Provider-agnostic architecture
- Routes through LLM Gateway for provider selection and failover
- Quality tier-aware prompt calibration (PREMIUM/STANDARD/BASIC)
- Ollama local model support for air-gapped deployments
- Graceful degradation with capability-appropriate coaching

v3.1 Enhancement: Maturity-informed coaching
- Coaching style adapts to innovator maturity level (NOVICE → EXPERT)
- Crisis mode integration with phase-specific guidance
- Maturity events emitted for dimension scoring

v3.0.3 Enhancement: Portfolio-informed coaching
- Portfolio context included in system prompt when multiple pursuits exist
- Cross-pursuit insights surface naturally in conversation
- Effectiveness metrics inform coaching recommendations
- IKF contribution guidance integrated into coaching flow

v3.0.2 Enhancement: Health-informed coaching
- Uses health zone context to adjust coaching tone
- Zone-specific intervention styles per ZONE_COACHING_GUIDELINES
- Surfaces predictions and risk alerts naturally in coaching
- Maintains advisory-only approach - no auto-termination

v2.3 Enhancement: Teleological-informed coaching
- Uses teleological context to select coaching style
- Incorporates selected questions from appropriate question bank
- Maintains natural conversation while invisibly applying methodology

Token Budget (per turn - adjusted per quality tier):
PREMIUM tier (Claude):
- system_prompt: 3000
- context: 8000
- response_budget: 4096

STANDARD tier (70B+ local):
- system_prompt: 1500
- context: 4000
- response_budget: 2048

BASIC tier (7B-13B local):
- system_prompt: 800
- context: 2000
- response_budget: 1024
"""

import re
import logging
import time
from typing import Dict, List, Optional

import httpx

# v3.15: Import retry utilities for LLM resilience
from functools import wraps

from core.config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, TOKEN_BUDGET,
    COACHING_RESPONSE_PROMPT, USE_MONGOMOCK,
    ZONE_COACHING_GUIDELINES, MATURITY_COACHING_STYLES,
    LLM_GATEWAY_URL
)
from coaching.prompt_calibration import (
    calibrate_system_prompt,
    get_max_response_tokens,
    get_context_budget,
    get_quality_tier,
    set_quality_tier,
    QualityTier
)

logger = logging.getLogger("inde.core.llm_interface")


# =============================================================================
# v3.15: Retry Configuration for LLM Resilience
# =============================================================================
LLM_RETRY_MAX_ATTEMPTS = 3
LLM_RETRY_INITIAL_DELAY = 2.0  # seconds
LLM_RETRY_MULTIPLIER = 2.0  # exponential backoff

# v3.15: User-friendly error messages
LLM_ERROR_MESSAGES = {
    "timeout": "The coaching service took too long to respond. Please try again.",
    "connection": "Unable to connect to the coaching service. Please check your connection and try again.",
    "rate_limit": "The coaching service is busy. Please wait a moment and try again.",
    "server_error": "The coaching service encountered an issue. Our team has been notified.",
    "unknown": "Something unexpected happened. Please try again.",
}


def _get_user_friendly_error(error: Exception) -> str:
    """Convert exceptions to user-friendly error messages."""
    error_str = str(error).lower()

    if isinstance(error, httpx.TimeoutException):
        return LLM_ERROR_MESSAGES["timeout"]
    elif isinstance(error, httpx.ConnectError):
        return LLM_ERROR_MESSAGES["connection"]
    elif "429" in error_str or "rate" in error_str:
        return LLM_ERROR_MESSAGES["rate_limit"]
    elif "500" in error_str or "502" in error_str or "503" in error_str:
        return LLM_ERROR_MESSAGES["server_error"]
    else:
        return LLM_ERROR_MESSAGES["unknown"]


class LLMInterface:
    """
    Manages all Claude API calls with token budget tracking.
    Falls back to demo responses when no API key available.
    """

    # Base system prompt for coaching conversations
    COACHING_SYSTEM_PROMPT = """You are an innovation coach having a natural conversation with an innovator.

Your style:
- Be warm, supportive, and genuinely curious about their idea
- Ask probing questions that help them think deeper
- Celebrate their insights and progress
- Keep responses conversational (under 150 words unless generating an artifact)
- Never use jargon like "scaffolding" or "artifact" - just have a natural conversation
- Guide them toward clarity without being prescriptive

Remember: You're helping them discover their own insights, not telling them what to do."""

    def __init__(self, api_key: str = None, use_gateway: bool = True):
        """
        Initialize LLM Interface.

        v3.9: Supports both direct Anthropic calls and LLM Gateway routing.
        Gateway mode enables automatic failover to local models (Ollama).

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            use_gateway: If True, route through LLM Gateway (default for v3.9)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = CLAUDE_MODEL
        self.demo_mode = False  # Try to use real API by default
        self.client = None
        self.use_gateway = use_gateway
        self._gateway_url = LLM_GATEWAY_URL
        self._http_client: Optional[httpx.Client] = None

        if not self.api_key and not self.use_gateway:
            logger.info("No API key provided, using demo mode")
            self.demo_mode = True
        elif USE_MONGOMOCK:
            # Only use demo mode if explicitly requested via USE_MONGOMOCK env var
            logger.info("Demo mode enabled via config, using demo responses")
            self.demo_mode = True
        elif self.use_gateway:
            # v3.9: Use LLM Gateway for provider selection
            logger.info(f"Initialized with LLM Gateway at {self._gateway_url}")
            self._http_client = httpx.Client(timeout=120.0)
        else:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Initialized with direct Claude API (model: {self.model})")
            except ImportError:
                logger.warning("anthropic package not installed, using demo mode")
                self.demo_mode = True
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.demo_mode = True

        if self.demo_mode:
            logger.info("Running in demo mode (pre-defined responses)")

    def call_llm(self, prompt: str, max_tokens: int = 500,
                 system: str = None, pursuit_context: Dict = None) -> str:
        """
        Make a call to the LLM.

        v3.9: Routes through LLM Gateway with automatic calibration.

        Args:
            prompt: The user/task prompt
            max_tokens: Maximum response tokens
            system: System prompt (optional)
            pursuit_context: Optional pursuit context for calibration

        Returns:
            Response text
        """
        if self.demo_mode:
            return self._demo_response(prompt)

        # v3.9: Get current quality tier and apply calibration
        quality_tier = get_quality_tier().value
        system_prompt = system or self.COACHING_SYSTEM_PROMPT

        # Apply calibration based on quality tier
        calibrated_system = calibrate_system_prompt(
            system_prompt,
            quality_tier,
            pursuit_context
        )

        # Adjust max_tokens based on tier
        tier_max_tokens = get_max_response_tokens(quality_tier)
        adjusted_max_tokens = min(max_tokens, tier_max_tokens)

        if self.use_gateway:
            return self._call_gateway(prompt, adjusted_max_tokens, calibrated_system)

        try:
            messages = [{"role": "user", "content": prompt}]

            response = self.client.messages.create(
                model=self.model,
                max_tokens=adjusted_max_tokens,
                system=calibrated_system,
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return self._demo_response(prompt)

    def _call_gateway(
        self,
        prompt: str,
        max_tokens: int,
        system: str,
        preferred_provider: str = "auto"
    ) -> str:
        """
        v3.9: Call the LLM Gateway for provider-agnostic routing.
        v3.15: Added retry logic with exponential backoff.

        Args:
            prompt: User prompt
            max_tokens: Maximum response tokens
            system: Calibrated system prompt
            preferred_provider: User's provider preference ('auto', 'cloud', 'local')

        Returns:
            Response text

        Raises:
            LLMTimeoutError: If all retry attempts timeout (for frontend handling)
        """
        last_error = None
        delay = LLM_RETRY_INITIAL_DELAY

        for attempt in range(1, LLM_RETRY_MAX_ATTEMPTS + 1):
            try:
                response = self._http_client.post(
                    f"{self._gateway_url}/llm/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "system_prompt": system,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "preferred_provider": preferred_provider
                    },
                    timeout=90.0  # v3.15: Explicit 90-second timeout
                )
                response.raise_for_status()
                data = response.json()

                # Update quality tier from gateway response
                if "quality_tier" in data:
                    set_quality_tier(data["quality_tier"])
                    logger.debug(f"Quality tier updated to: {data['quality_tier']}")

                return data.get("content", "")

            except httpx.ConnectError as e:
                logger.warning(f"LLM Gateway not reachable at {self._gateway_url} (attempt {attempt})")
                last_error = e
                # Don't retry connection errors - fall through to demo mode
                break

            except httpx.TimeoutException as e:
                logger.warning(f"Gateway call timed out (attempt {attempt}/{LLM_RETRY_MAX_ATTEMPTS})")
                last_error = e
                if attempt < LLM_RETRY_MAX_ATTEMPTS:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= LLM_RETRY_MULTIPLIER

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited - retry with backoff
                    logger.warning(f"Gateway rate limited (attempt {attempt}/{LLM_RETRY_MAX_ATTEMPTS})")
                    last_error = e
                    if attempt < LLM_RETRY_MAX_ATTEMPTS:
                        retry_after = int(e.response.headers.get("Retry-After", delay))
                        time.sleep(retry_after)
                        delay *= LLM_RETRY_MULTIPLIER
                elif e.response.status_code >= 500:
                    # Server error - retry with backoff
                    logger.warning(f"Gateway server error {e.response.status_code} (attempt {attempt})")
                    last_error = e
                    if attempt < LLM_RETRY_MAX_ATTEMPTS:
                        time.sleep(delay)
                        delay *= LLM_RETRY_MULTIPLIER
                else:
                    # Client error - don't retry
                    logger.error(f"Gateway client error: {e}")
                    last_error = e
                    break

            except Exception as e:
                logger.error(f"Gateway call failed unexpectedly: {e}")
                last_error = e
                break

        # All retries exhausted or non-retryable error
        logger.error(f"Gateway call failed after {LLM_RETRY_MAX_ATTEMPTS} attempts: {last_error}")

        # v3.15: Return user-friendly error message in a structured format
        # that the coaching endpoint can detect and handle
        error_msg = _get_user_friendly_error(last_error) if last_error else LLM_ERROR_MESSAGES["unknown"]
        return f"[COACHING_ERROR]{error_msg}"

    def generate_coaching_response(self, user_message: str,
                                   conversation_history: List[Dict],
                                   pursuit_context: Dict,
                                   intervention: Dict = None,
                                   teleological_context: Dict = None,
                                   selected_question: str = None,
                                   health_context: Dict = None,
                                   portfolio_context: Dict = None,
                                   maturity_context: Dict = None,
                                   crisis_context: Dict = None,
                                   ikf_context: Dict = None,
                                   momentum_context: Dict = None,
                                   preferred_provider: str = "auto") -> str:
        """
        Generate coaching response with optional intervention.

        v3.1 Enhancement: Adapts coaching style to innovator maturity level.
        Crisis mode overrides normal coaching when active.

        v3.0.3 Enhancement: Includes portfolio context when multiple pursuits exist.
        Surfaces cross-pursuit insights and effectiveness guidance naturally.

        v3.0.2 Enhancement: Uses health zone context to adjust coaching tone
        per ZONE_COACHING_GUIDELINES. Surfaces predictions and risks naturally.

        v2.3 Enhancement: Uses teleological context to inform coaching style
        and incorporates questions from the appropriate question bank.

        Args:
            user_message: Current user message
            conversation_history: Recent conversation turns
            pursuit_context: Current pursuit state including completeness
            intervention: Optional intervention to weave in
            teleological_context: v2.3 - Teleological assessment with question bank
            selected_question: v2.3 - Specific question from question bank
            health_context: v3.0.2 - Health zone context with coaching guidelines
            portfolio_context: v3.0.3 - Portfolio analytics context (optional)
            maturity_context: v3.1 - Innovator maturity level and coaching style
            crisis_context: v3.1 - Active crisis mode info (optional)
            ikf_context: v3.5.2 - IKF contribution context (optional)
            momentum_context: v4.1 - MME momentum state (optional)

        Returns:
            Coaching response text
        """
        if self.demo_mode:
            return self._demo_coaching_response(user_message, pursuit_context, intervention, health_context, portfolio_context, maturity_context, crisis_context)

        # Build conversation history string
        history_str = self._format_conversation_history(conversation_history)

        # Build intervention instruction
        intervention_instruction = ""
        additional_guidance = ""

        if intervention:
            moment_type = intervention.get("type", "")
            suggestion = intervention.get("suggestion", "")

            if moment_type == "READY_TO_FORMALIZE":
                intervention_instruction = f"The user has shared enough information to create a formal document. Naturally offer: {suggestion}"
                additional_guidance = "If they agree, you'll generate the artifact in your next response."

            elif moment_type == "CRITICAL_GAP":
                intervention_instruction = f"There's important information missing. Naturally work in this question: {suggestion}"
                additional_guidance = "Don't make it feel like an interrogation - weave it into the conversation."

            elif moment_type == "FEAR_OPPORTUNITY":
                intervention_instruction = f"The user expressed a concern. Acknowledge it and explore: {suggestion}"
                additional_guidance = "Be empathetic and help them articulate their concerns."

            elif moment_type == "NATURAL_TRANSITION":
                intervention_instruction = f"It's a good time to shift focus. Suggest: {suggestion}"
                additional_guidance = "Make the transition feel natural, not forced."

        # v2.3: Add teleological coaching guidance
        teleological_guidance = ""
        if teleological_context:
            coaching_style = teleological_context.get("coaching_style", {})
            if coaching_style:
                tone = coaching_style.get("tone", "")
                emphasis = coaching_style.get("emphasis", [])
                avoid = coaching_style.get("avoid", [])

                teleological_guidance = f"""
Coaching style for this conversation:
- Tone: {tone}
- Emphasize: {', '.join(emphasis[:3]) if emphasis else 'user understanding'}
- Avoid: {', '.join(avoid[:3]) if avoid else 'methodology jargon'}
"""

        # v2.3: Add selected question as guidance
        question_guidance = ""
        if selected_question:
            question_guidance = f"""
Use this question as inspiration for your response (do NOT quote it verbatim):
"{selected_question}"

Adapt this naturally to the conversation flow.
"""

        # v3.0.2: Add health zone coaching guidance
        health_zone_guidance = ""
        if health_context:
            zone = health_context.get("zone", "HEALTHY")
            health_score = health_context.get("health_score", 50)
            guidelines = ZONE_COACHING_GUIDELINES.get(zone, {})
            tone = guidelines.get("tone", "supportive")
            intervention_style = guidelines.get("intervention_style", "standard coaching")

            health_zone_guidance = f"""
Health-informed coaching guidance (pursuit health score: {health_score}/100, zone: {zone}):
- Tone: {tone}
- Intervention style: {intervention_style}
"""
            # Add zone-specific instructions
            if zone == "CRITICAL":
                health_zone_guidance += """
- Be honest but not alarmist - present options clearly
- Focus on immediate actionable steps
- Suggest examining what's blocking progress
"""
            elif zone == "AT_RISK":
                health_zone_guidance += """
- Be direct but empathetic about challenges
- Surface specific risks observed
- Recommend concrete action items
"""
            elif zone == "ATTENTION":
                health_zone_guidance += """
- Ask gently about potential blockers
- Probe for obstacles without judgment
- Consider suggesting a brief retrospective
"""
            elif zone == "THRIVING":
                health_zone_guidance += """
- Celebrate their momentum
- Encourage stretch goals
- Keep interventions light
"""

            # Add prediction context if available
            prediction = health_context.get("top_prediction")
            if prediction:
                pred_type = prediction.get("type", "")
                pred_desc = prediction.get("description", "")
                health_zone_guidance += f"""
Consider naturally weaving in this insight:
{pred_desc}
"""

            # Add risk alert if critical
            top_risk = health_context.get("top_risk")
            if top_risk and top_risk.get("severity") in ["HIGH", "CRITICAL"]:
                risk_desc = top_risk.get("description", "")
                health_zone_guidance += f"""
There's a significant risk to be aware of: {risk_desc}
Surface this naturally if relevant to the conversation.
"""

        # v3.0.3: Add portfolio context guidance
        portfolio_guidance = ""
        if portfolio_context and portfolio_context.get("pursuit_count", 0) > 1:
            portfolio_health = portfolio_context.get("portfolio_health", 50)
            portfolio_zone = portfolio_context.get("portfolio_zone", "HEALTHY")
            pursuit_count = portfolio_context.get("pursuit_count", 0)

            portfolio_guidance = f"""
Portfolio context (innovator has {pursuit_count} active pursuits):
- Portfolio health: {portfolio_health}/100 ({portfolio_zone})
"""
            # Add cross-pursuit insights if available
            cross_insights = portfolio_context.get("cross_pursuit_insights", [])
            if cross_insights:
                top_insight = cross_insights[0] if isinstance(cross_insights, list) else cross_insights
                if isinstance(top_insight, dict):
                    insight_text = top_insight.get("insight", "")
                    if insight_text:
                        portfolio_guidance += f"- Cross-pursuit insight: {insight_text[:100]}...\n"

            # Add velocity comparison if relevant
            velocity_context = portfolio_context.get("velocity_context")
            if velocity_context:
                current_velocity = velocity_context.get("current_pursuit_velocity", 0)
                portfolio_avg = velocity_context.get("portfolio_average", 0)
                if current_velocity > 0 and portfolio_avg > 0:
                    if current_velocity < portfolio_avg * 0.7:
                        portfolio_guidance += f"- This pursuit's velocity ({current_velocity:.1f}/wk) is below portfolio average ({portfolio_avg:.1f}/wk)\n"
                    elif current_velocity > portfolio_avg * 1.3:
                        portfolio_guidance += f"- This pursuit is progressing faster than average\n"

            # Add recommendations if available
            recommendations = portfolio_context.get("recommendations", [])
            if recommendations:
                top_rec = recommendations[0] if isinstance(recommendations, list) else recommendations
                if isinstance(top_rec, dict):
                    rec_text = top_rec.get("recommendation", "")
                    if rec_text:
                        portfolio_guidance += f"- Consider: {rec_text[:100]}...\n"

            portfolio_guidance += """
When relevant, naturally reference connections to other pursuits or portfolio-level insights.
Never use jargon like 'portfolio analytics' or 'cross-pursuit' - keep it conversational.
"""

        # v3.1: Add maturity-informed coaching guidance
        maturity_guidance = ""
        if maturity_context:
            maturity_level = maturity_context.get("maturity_level", "NOVICE")
            coaching_style = MATURITY_COACHING_STYLES.get(maturity_level, MATURITY_COACHING_STYLES["NOVICE"])

            maturity_guidance = f"""
Maturity-informed coaching (innovator is at {maturity_level} level):
- Mode: {coaching_style.get('mode', 'NURTURING')}
- Intervention frequency: {coaching_style.get('intervention_frequency', 'high')}
"""
            if coaching_style.get("explain_why"):
                maturity_guidance += "- Explain the reasoning behind suggestions\n"
            if coaching_style.get("encouragement_level") == "high":
                maturity_guidance += "- Provide frequent encouragement and validation\n"
            elif coaching_style.get("encouragement_level") == "minimal":
                maturity_guidance += "- Treat them as a peer; minimal hand-holding needed\n"

        # v3.1: Add crisis mode guidance if active
        crisis_guidance = ""
        if crisis_context and crisis_context.get("active"):
            crisis_type = crisis_context.get("crisis_type", "MANUAL")
            current_phase = crisis_context.get("current_phase", "IMMEDIATE_TRIAGE")
            urgency = crisis_context.get("urgency", "STANDARD")

            crisis_guidance = f"""
CRISIS MODE ACTIVE - {crisis_type} (Urgency: {urgency})
Current phase: {current_phase}

Focus your coaching on crisis resolution:
"""
            if current_phase == "IMMEDIATE_TRIAGE":
                crisis_guidance += """- Help stabilize the situation
- Assess immediate impacts
- Identify who needs to know
"""
            elif current_phase == "DIAGNOSTIC_DEEP_DIVE":
                crisis_guidance += """- Explore root causes
- Challenge assumptions that led here
- Surface underlying issues
"""
            elif current_phase == "OPTIONS_GENERATION":
                crisis_guidance += """- Help brainstorm response options
- Consider multiple approaches
- Evaluate feasibility
"""
            elif current_phase == "DECISION_SUPPORT":
                crisis_guidance += """- Help evaluate options
- Support decision-making
- Define success criteria
"""
            elif current_phase == "POST_CRISIS_MONITORING":
                crisis_guidance += """- Check on resolution progress
- Capture lessons learned
- Update early warning systems
"""

        # v3.5.2: Add IKF contribution context guidance
        ikf_guidance = ""
        if ikf_context:
            contribution_mode = ikf_context.get("contribution_mode", "PASSIVE")
            current_archetype = ikf_context.get("current_archetype")
            federation_status = ikf_context.get("federation_status", "NOT_CONNECTED")

            if contribution_mode == "ACTIVE" and current_archetype:
                ikf_guidance = f"""
IKF Context (Innovation Knowledge Fabric):
- Active contribution mode with {current_archetype} archetype
- Consider how insights from this pursuit might benefit other innovators
"""
            elif federation_status == "CONNECTED":
                ikf_guidance = """
IKF Context: Connected to federation - relevant cross-organizational insights available.
"""

        # v4.1: Add momentum context guidance (MME)
        momentum_guidance = ""
        if momentum_context:
            coaching_guidance = momentum_context.get("coaching_guidance", "")
            turn_count = momentum_context.get("turn_count", 0)
            bridge_delivered = momentum_context.get("bridge_delivered", False)

            if coaching_guidance:
                momentum_guidance = f"""
[COACHING TONE GUIDANCE — INTERNAL — DO NOT REPEAT TO INNOVATOR]
{coaching_guidance}

Turn count this session: {turn_count}
Bridge already delivered this session: {bridge_delivered}
[END COACHING TONE GUIDANCE]
"""

        # Get completeness values
        completeness = pursuit_context.get("completeness", {})

        # Build the prompt
        prompt = COACHING_RESPONSE_PROMPT.format(
            pursuit_title=pursuit_context.get("title", "Your Innovation"),
            vision_completeness=int(completeness.get("vision", 0) * 100),
            fear_completeness=int(completeness.get("fears", 0) * 100),
            hypothesis_completeness=int(completeness.get("hypothesis", 0) * 100),
            intervention_instruction=intervention_instruction,
            conversation_history=history_str,
            user_message=user_message,
            additional_guidance=momentum_guidance + additional_guidance + teleological_guidance + question_guidance + health_zone_guidance + portfolio_guidance + maturity_guidance + crisis_guidance + ikf_guidance
        )

        # v3.9: Apply quality tier-aware calibration
        quality_tier = get_quality_tier().value
        calibrated_system = calibrate_system_prompt(
            self.COACHING_SYSTEM_PROMPT,
            quality_tier,
            pursuit_context
        )

        # Adjust max_tokens based on tier
        tier_max_tokens = get_max_response_tokens(quality_tier)
        adjusted_max_tokens = min(TOKEN_BUDGET["response_budget"], tier_max_tokens)

        # v3.9: Route through gateway if enabled (with user's provider preference)
        if self.use_gateway:
            return self._call_gateway(prompt, adjusted_max_tokens, calibrated_system, preferred_provider)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=adjusted_max_tokens,
                system=calibrated_system,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Coaching response failed: {e}")
            return self._demo_coaching_response(user_message, pursuit_context, intervention)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt."""
        if not history:
            return "(This is the start of the conversation)"

        formatted = []
        for turn in history[-5:]:  # Last 5 turns
            role = turn.get("role", "user")
            content = turn.get("content", "")
            prefix = "User" if role == "user" else "Coach"
            formatted.append(f"{prefix}: {content}")

        return "\n".join(formatted)

    def _demo_response(self, prompt: str) -> str:
        """Generate demo response when no API available."""
        # Check what kind of prompt this is
        prompt_lower = prompt.lower()

        if "innovation intent" in prompt_lower or "has_intent" in prompt_lower:
            # Intent detection prompt - extract user message portion
            user_msg = prompt
            if "User message:" in prompt:
                # Extract just the user message, not the JSON template that follows
                after_marker = prompt.split("User message:")[-1]
                # Stop at "Respond" which starts the JSON template
                if "Respond" in after_marker:
                    user_msg = after_marker.split("Respond")[0].strip()
                else:
                    user_msg = after_marker.strip()

            user_msg_lower = user_msg.lower()

            if any(word in user_msg_lower for word in ["create", "build", "design", "develop", "make", "want to"]):
                # Try to extract a title
                title = "New Innovation Concept"

                # Look for quoted names like "Danger Doll"
                quoted = re.search(r'"([^"]+)"', user_msg)
                if quoted:
                    name = quoted.group(1)
                    # Add context if it's just a product name
                    if len(name.split()) <= 3:
                        title = f"{name} Innovation"
                    else:
                        title = name
                elif "called" in user_msg_lower:
                    match = re.search(r'called\s+["\']?([A-Za-z][A-Za-z\s]+)', user_msg, re.IGNORECASE)
                    if match:
                        title = match.group(1).split(' to ')[0].strip() + " Innovation"

                # Extract problem/solution hints
                problem_hint = None
                solution_hint = None

                if "detect" in prompt_lower or "warn" in prompt_lower:
                    solution_hint = "Detection and warning system"
                if "hazard" in prompt_lower or "smoke" in prompt_lower or "gas" in prompt_lower:
                    problem_hint = "Safety hazard detection for children"
                if "toy" in prompt_lower or "doll" in prompt_lower:
                    solution_hint = "Safety toy with sensors"

                problem_json = f'"{problem_hint}"' if problem_hint else "null"
                solution_json = f'"{solution_hint}"' if solution_hint else "null"
                return f'{{"has_intent": true, "confidence": 0.9, "suggested_title": "{title}", "problem_hint": {problem_json}, "solution_hint": {solution_json}}}'

            return '{"has_intent": false, "confidence": 0.2, "suggested_title": null, "problem_hint": null, "solution_hint": null}'

        elif "extract" in prompt_lower and "element" in prompt_lower:
            # Element extraction prompt - try to extract some elements
            elements = {"vision": {}, "fears": {}, "hypothesis": {}}

            # Check for vision elements in the conversation turn
            turn_text = prompt.split("Conversation turn:")[-1] if "Conversation turn:" in prompt else prompt
            # Also clean up any JSON template that might follow
            if "Respond in JSON" in turn_text:
                turn_text = turn_text.split("Respond in JSON")[0]
            turn_text_lower = turn_text.lower()

            print(f"[DemoResponse] Element extraction from: {turn_text[:100]}...")

            # Age/target user detection
            if re.search(r'ages?\s*\d', turn_text, re.IGNORECASE) or "children" in turn_text_lower or "kids" in turn_text_lower:
                age_match = re.search(r'ages?\s*(\d+[-\s]?\d*)', turn_text, re.IGNORECASE)
                if age_match:
                    elements["vision"]["target_user"] = {"text": f"Children ages {age_match.group(1)}", "confidence": 0.85}
                    print(f"[DemoResponse] Extracted target_user: Children ages {age_match.group(1)}")
                elif "children" in turn_text_lower:
                    elements["vision"]["target_user"] = {"text": "Children", "confidence": 0.7}
                    print(f"[DemoResponse] Extracted target_user: Children")

            # Solution concept detection (from initial idea)
            if "toy" in turn_text_lower or "doll" in turn_text_lower:
                if "detect" in turn_text_lower or "warn" in turn_text_lower or "sensor" in turn_text_lower:
                    elements["vision"]["solution_concept"] = {"text": "A toy/doll with sensors to detect and warn children of hazards", "confidence": 0.85}
                    print(f"[DemoResponse] Extracted solution_concept")

            # Problem detection
            if "problem" in turn_text_lower or "leak" in turn_text_lower or "didn't understand" in turn_text_lower:
                elements["vision"]["problem_statement"] = {"text": "Children don't respond appropriately to safety alarms", "confidence": 0.8}
                print(f"[DemoResponse] Extracted problem_statement")

            # Pain point detection
            if "didn't understand" in turn_text_lower or "kept playing" in turn_text_lower:
                elements["vision"]["pain_points"] = {"text": "Young children ignore or don't understand traditional safety alarms", "confidence": 0.85}
                elements["vision"]["current_situation"] = {"text": "Traditional smoke/CO detectors alert adults but not children effectively", "confidence": 0.8}
                print(f"[DemoResponse] Extracted pain_points and current_situation")

            # Personal story / origin / differentiation
            if "sister" in turn_text_lower or ("my" in turn_text_lower and ("house" in turn_text_lower or "family" in turn_text_lower)):
                elements["vision"]["differentiation"] = {"text": "Personal experience-driven design focused on child engagement", "confidence": 0.7}
                print(f"[DemoResponse] Extracted differentiation")

            # Fear detection
            if "not an engineer" in turn_text_lower or "don't know" in turn_text_lower or "not sure" in turn_text_lower:
                elements["fears"]["capability_fears"] = {"text": "Lack of engineering expertise for sensor technology", "confidence": 0.85}
                print(f"[DemoResponse] Extracted capability_fears")
            if "malfunction" in turn_text_lower or "what if" in turn_text_lower or "fail" in turn_text_lower:
                elements["fears"]["market_fears"] = {"text": "Product liability if device fails during emergency", "confidence": 0.8}
                print(f"[DemoResponse] Extracted market_fears")

            # Count what we extracted
            extracted_count = sum(len(v) for v in elements.values())
            print(f"[DemoResponse] Total elements extracted: {extracted_count}")

            # Convert to proper JSON
            import json
            return json.dumps(elements)

        elif "polish" in prompt_lower or "artifact" in prompt_lower:
            # Artifact generation/polish prompt
            if "Current content:" in prompt:
                return prompt.split("Current content:")[-1].split("Available elements:")[0].strip()
            return prompt

        else:
            # Generic response
            return "I understand. Tell me more about your idea."

    def _demo_coaching_response(self, user_message: str,
                                 pursuit_context: Dict,
                                 intervention: Dict = None,
                                 health_context: Dict = None,
                                 portfolio_context: Dict = None,
                                 maturity_context: Dict = None,
                                 crisis_context: Dict = None) -> str:
        """
        Generate demo coaching response.

        v3.1: Uses maturity and crisis context when available.
        v3.0.3: Uses portfolio context when available.
        v3.0.2: Uses health context to adjust tone in demo mode.
        """
        title = pursuit_context.get("title", "your idea")
        completeness = pursuit_context.get("completeness", {})
        vision_pct = int(completeness.get("vision", 0) * 100)
        fears_pct = int(completeness.get("fears", 0) * 100)

        # v3.1: Check for crisis mode first - takes precedence
        if crisis_context and crisis_context.get("active"):
            crisis_type = crisis_context.get("crisis_type", "situation")
            current_phase = crisis_context.get("current_phase", "IMMEDIATE_TRIAGE")

            if current_phase == "IMMEDIATE_TRIAGE":
                return f"Let's pause and assess what's happening. Can you tell me what triggered this {crisis_type.lower().replace('_', ' ')} situation? What's the most immediate concern?"
            elif current_phase == "DIAGNOSTIC_DEEP_DIVE":
                return "Now let's dig deeper. What assumptions or decisions led to this point? Were there any warning signs we might have missed?"
            elif current_phase == "OPTIONS_GENERATION":
                return "Let's brainstorm options. What are at least three different ways we could respond to this? Don't filter yet - let's get ideas on the table."
            elif current_phase == "DECISION_SUPPORT":
                return "Looking at our options, which one best addresses the root cause? What resources would we need, and how would we know if it's working?"
            else:
                return "How is the resolution progressing? What would you do differently next time, and what should we add to our early warning system?"

        # v3.1: Get maturity level for tone adjustment
        maturity_level = "NOVICE"
        if maturity_context:
            maturity_level = maturity_context.get("maturity_level", "NOVICE")

        # v3.0.2: Get health zone for tone adjustment
        health_zone = "HEALTHY"
        health_score = 50
        if health_context:
            health_zone = health_context.get("zone", "HEALTHY")
            health_score = health_context.get("health_score", 50)

        # v3.0.3: Check for portfolio insights
        if portfolio_context and portfolio_context.get("pursuit_count", 0) > 1:
            msg_lower = user_message.lower()

            # Handle portfolio-related queries
            if any(word in msg_lower for word in ["portfolio", "other projects", "other pursuits", "all my"]):
                pursuit_count = portfolio_context.get("pursuit_count", 0)
                portfolio_zone = portfolio_context.get("portfolio_zone", "HEALTHY")
                return f"Looking across your {pursuit_count} active pursuits, your portfolio is in the {portfolio_zone} zone. Would you like to explore how they connect or compare?"

            # Handle comparison requests
            if any(word in msg_lower for word in ["compare", "versus", "vs", "difference"]):
                return f"I can help you compare aspects of your pursuits. What specifically would you like to compare - progress pace, risks, or approach?"

        msg_lower = user_message.lower()

        # v3.0.2: Zone-specific urgent responses
        if health_zone == "CRITICAL" and health_score < 20:
            return f"I notice {title} has been facing some challenges. I want to be direct with you - it might help to step back and examine what's blocking progress. What's really going on? What would help you move forward?"

        if health_zone == "AT_RISK" and health_score < 40:
            return f"I've been thinking about {title}. Things seem a bit stuck lately. What's getting in the way? Sometimes talking through the obstacles helps clarify the path forward."

        # Check for affirmative responses (user accepting artifact generation)
        affirmative_words = ["yes", "sure", "ok", "please", "yeah", "yep", "go ahead", "sounds good"]
        if any(word in msg_lower for word in affirmative_words):
            if intervention and intervention.get("type") == "READY_TO_FORMALIZE":
                # v4.0: Use momentum bridge language instead of session-close
                return f"Great! Let me draft that for you. Here's your vision statement for {title}:\n\n[Vision artifact would be generated here in full mode]\n\nYour story is taking shape. I'm curious — what's the part of this idea that still feels most uncertain to you?"

        # Handle interventions
        if intervention:
            moment_type = intervention.get("type", "")

            if moment_type == "READY_TO_FORMALIZE":
                return f"We've covered a lot of ground on {title}. Would it be helpful if I drafted a formal vision statement that captures everything we've discussed? That way you'd have a clear document to share with others."

            elif moment_type == "CRITICAL_GAP":
                return intervention.get("suggestion", "Tell me more about who would use this.")

            elif moment_type == "FEAR_OPPORTUNITY":
                return "That sounds like an important concern. Tell me more about what worries you there - what's the worst case you're imagining?"

            elif moment_type == "NATURAL_TRANSITION":
                return intervention.get("suggestion", "Now that we've captured your vision, what concerns do you have about making this real?")

        # Context-aware responses based on message content
        if "age" in msg_lower or re.search(r'\d+[-\s]?\d*', msg_lower):
            return f"That age range makes sense for {title}. At that stage, kids can understand warnings but might not take traditional alarms seriously. What made you think of this concept?"

        if "sister" in msg_lower or "brother" in msg_lower or "family" in msg_lower or "personal" in msg_lower:
            return "That's a powerful origin story - personal experience often drives the best innovations. Given how meaningful this is to you, what concerns do you have about bringing it to life?"

        if "engineer" in msg_lower or "don't know" in msg_lower or "not sure" in msg_lower:
            return "Those are valid concerns, and it's good you're thinking about them early. The technical challenges are real, but your insight into the problem is what matters most right now. What else worries you about this?"

        if "malfunction" in msg_lower or "fail" in msg_lower or "liability" in msg_lower:
            return "Product safety is critical for any device meant for children. That's exactly the kind of thinking that will make this product trustworthy. Are there other risks on your mind?"

        # Default responses based on progress
        if vision_pct < 25:
            return f"That's a fascinating concept - {title}. I'm curious about the age range you're thinking about. Are we talking toddlers, elementary school kids, or a wider range?"

        elif vision_pct < 50:
            return "I'm getting a clearer picture. What made you think of this idea? Was there a specific incident or gap you noticed?"

        elif vision_pct < 75:
            if fears_pct < 25:
                return f"We've covered good ground on the vision for {title}. What concerns do you have about making this real? What worries you most?"
            return "We're building a solid foundation. What would success look like for this in 6-12 months?"

        else:
            # v2.5 FIX: Only offer drafting when READY_TO_FORMALIZE is the actual intervention
            # Otherwise, the intervention system offers it and we don't want duplicate offers
            if fears_pct < 50:
                return f"Your vision for {title} is really taking shape. What worries you most about making this happen? What could go wrong?"
            return f"You've built a solid foundation for {title}. Is there anything else you'd like to explore or clarify?"

    # =========================================================================
    # v3.9: Quality Tier Utilities
    # =========================================================================

    def get_current_quality_tier(self) -> str:
        """
        v3.9: Get the current quality tier.

        Returns:
            Quality tier string: 'premium', 'standard', or 'basic'
        """
        return get_quality_tier().value

    def get_quality_indicator(self) -> Optional[Dict]:
        """
        v3.9: Get quality indicator info for UI display.

        Returns None for premium tier (no indicator needed).
        For other tiers, returns dict with message and tier info.
        """
        from coaching.prompt_calibration import (
            should_show_quality_indicator,
            get_quality_indicator_message
        )

        tier = get_quality_tier().value
        if not should_show_quality_indicator(tier):
            return None

        return {
            "show": True,
            "tier": tier,
            "message": get_quality_indicator_message(tier)
        }

    def close(self):
        """
        v3.9: Clean up resources.

        Call this when the interface is no longer needed.
        """
        if self._http_client:
            self._http_client.close()
            self._http_client = None
