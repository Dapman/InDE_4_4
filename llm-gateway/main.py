"""
InDE v3.9 - LLM Gateway Service
Provides unified LLM access with rate limiting, provider abstraction, and automatic failover.

v3.9 "Air-Gapped Intelligence" Features:
- Provider Registry: Configuration-driven provider chain with automatic failover
- Ollama Support: Local LLM for air-gapped deployments
- Quality Tier Awareness: Prompts calibrated based on model capability
- Failover Events: Logged and emitted for operator visibility

Endpoints:
- POST /generate: Generate LLM response (legacy, uses provider registry)
- POST /llm/chat: New chat endpoint with full provider metadata
- GET /health: Health check with provider status
- GET /llm/health: Detailed provider registry health
- GET /api/v1/providers: Provider chain status for admin panel
- GET /rate-limit: Current rate limit status
- GET /api/v1/validate-key: Validate configured API key
- POST /api/v1/configure: Runtime API key configuration (BYOK)
"""

import os
import time
import json
import logging
import httpx
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List
from collections import defaultdict
from contextlib import asynccontextmanager

# Load .env file from parent directory (project root)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[LLM Gateway] Loaded .env from {env_path}")
except ImportError:
    pass  # dotenv not installed, rely on system env vars

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from provider_registry import get_registry, initialize_providers
from providers.base_provider import ChatRequest, ChatResponse, QualityTier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm-gateway")

# Rate limiting config
MAX_TOKENS_PER_MINUTE = int(os.getenv("MAX_TOKENS_PER_MINUTE", "100000"))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")

# Mutable config for runtime updates (BYOK support)
_config = {
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "api_key_validated": False,
    "available_models": []
}

# For backwards compatibility
def get_api_key() -> str:
    """Get the current API key."""
    return _config["anthropic_api_key"]

# Rate limit tracking
rate_limit_buckets: Dict[str, Dict] = defaultdict(lambda: {
    "tokens_used": 0,
    "window_start": time.time()
})


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting InDE LLM Gateway v3.9.0")

    # Initialize provider registry
    initialize_providers()

    # Log provider chain
    registry = get_registry()
    providers = registry.get_providers()
    logger.info(f"Provider chain: {[p.name for p in providers]}")

    yield

    logger.info("LLM Gateway shutdown")


app = FastAPI(
    title="InDE LLM Gateway",
    description="LLM provider abstraction with rate limiting, failover, and BYOK support",
    version="3.10.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1000
    model: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = False


class GenerateResponse(BaseModel):
    content: str
    model: str
    tokens_used: int
    provider: str
    quality_tier: Optional[str] = None
    failover: bool = False


class LLMChatRequest(BaseModel):
    """Full chat request with message history."""
    messages: List[dict]
    system_prompt: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False
    user_id: Optional[str] = None
    preferred_provider: Optional[str] = "auto"  # 'auto', 'cloud', or 'local'


class ValidateKeyResponse(BaseModel):
    valid: bool
    models_available: List[str]
    error: Optional[str] = None


class ConfigureRequest(BaseModel):
    anthropic_api_key: str


class ConfigureResponse(BaseModel):
    success: bool
    message: str
    api_key_configured: bool


# =============================================================================
# Utility Functions
# =============================================================================

def detect_gpu() -> Dict:
    """Detect available GPU resources."""
    gpu_info = {
        "cuda_available": False,
        "device_count": 0,
        "devices": []
    }

    try:
        import torch
        gpu_info["cuda_available"] = torch.cuda.is_available()
        if gpu_info["cuda_available"]:
            gpu_info["device_count"] = torch.cuda.device_count()
            for i in range(gpu_info["device_count"]):
                gpu_info["devices"].append({
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_total": torch.cuda.get_device_properties(i).total_memory
                })
    except ImportError:
        pass

    return gpu_info


def check_rate_limit(user_id: str, tokens_requested: int) -> bool:
    """Check if request is within rate limits."""
    bucket = rate_limit_buckets[user_id]
    current_time = time.time()

    if current_time - bucket["window_start"] > 60:
        bucket["tokens_used"] = 0
        bucket["window_start"] = current_time

    if bucket["tokens_used"] + tokens_requested > MAX_TOKENS_PER_MINUTE:
        return False

    return True


def record_usage(user_id: str, tokens_used: int):
    """Record token usage for rate limiting."""
    bucket = rate_limit_buckets[user_id]
    bucket["tokens_used"] += tokens_used


# =============================================================================
# Core Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    registry = get_registry()
    primary = await registry.get_primary()

    return {
        "service": "InDE LLM Gateway",
        "version": "3.9.0",
        "status": "running",
        "active_provider": primary.name if primary else None,
        "api_key_configured": bool(get_api_key())
    }


@app.get("/health")
async def health_check():
    """Basic health check with provider status."""
    gpu_info = detect_gpu()
    registry = get_registry()
    primary = await registry.get_primary()

    return {
        "status": "healthy" if primary else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_provider": primary.name if primary else None,
        "gpu": gpu_info,
        "anthropic_configured": bool(get_api_key()),
        "api_key_configured": bool(get_api_key()),
        "api_key_validated": _config["api_key_validated"],
        "default_model": DEFAULT_MODEL
    }


@app.get("/llm/health")
async def llm_health():
    """Detailed LLM provider registry health."""
    registry = get_registry()
    return await registry.health_check()


@app.get("/rate-limit")
async def get_rate_limit_status(user_id: str = "default"):
    """Get current rate limit status for a user."""
    bucket = rate_limit_buckets[user_id]
    current_time = time.time()

    if current_time - bucket["window_start"] > 60:
        remaining = MAX_TOKENS_PER_MINUTE
        reset_in = 60
    else:
        remaining = MAX_TOKENS_PER_MINUTE - bucket["tokens_used"]
        reset_in = 60 - (current_time - bucket["window_start"])

    return {
        "max_tokens_per_minute": MAX_TOKENS_PER_MINUTE,
        "tokens_remaining": remaining,
        "reset_in_seconds": int(reset_in)
    }


# =============================================================================
# Provider Status Endpoints (v3.9)
# =============================================================================

@app.get("/api/v1/providers")
async def get_providers_status():
    """
    Detailed provider information for admin panel.
    Shows chain order, availability, quality tiers, and failover history.
    """
    registry = get_registry()
    providers = registry.get_providers()
    statuses = await registry.get_all_status()

    return {
        "chain": [p.name for p in providers],
        "providers": [
            {
                **status.dict(),
                "priority": i + 1
            }
            for i, status in enumerate(statuses)
        ],
        "failover_history": registry.get_failover_history(limit=50)
    }


@app.get("/api/v1/providers/failover-events")
async def get_failover_events(limit: int = 50):
    """
    Get recent failover events from the provider registry.

    Args:
        limit: Maximum number of events to return (default 50)

    Returns:
        List of failover events with timestamps and provider info.
    """
    registry = get_registry()
    events = registry.get_failover_history(limit=limit)

    return {
        "events": events,
        "count": len(events),
        "stream": "inde:events:llm-failover"
    }


@app.get("/api/v1/providers/quality-tier")
async def get_current_quality_tier():
    """
    Get the quality tier of the currently active provider.

    Returns:
        Current quality tier info for prompt calibration.
    """
    registry = get_registry()
    primary = await registry.get_primary()

    if not primary:
        return {
            "tier": "basic",
            "provider": None,
            "status": "no_providers_available"
        }

    status = await primary.get_status()
    return {
        "tier": status.quality_tier.value,
        "provider": primary.name,
        "status": "available"
    }


# =============================================================================
# LLM Chat Endpoints (v3.9)
# =============================================================================

@app.post("/llm/chat")
async def llm_chat(request: LLMChatRequest):
    """
    Chat endpoint using provider registry with preference-aware selection.

    Supports user preference for 'cloud' (premium), 'local' (cost-free), or 'auto'.
    Returns response with provider metadata for ODICM prompt calibration.
    """
    user_id = request.user_id or "default"
    registry = get_registry()

    # Check rate limit
    estimated_tokens = sum(len(str(m.get("content", "")).split()) for m in request.messages) * 2 + request.max_tokens
    if not check_rate_limit(user_id, estimated_tokens):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making more requests."
        )

    try:
        # Get provider based on user preference (with automatic fallback)
        preference = request.preferred_provider or "auto"
        provider, did_fallback = await registry.get_provider_by_preference(preference)
        status = await provider.get_status()

        # Track if we're not using the preferred provider
        did_failover = did_fallback

        # Build chat request
        chat_req = ChatRequest(
            messages=request.messages,
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            user_id=user_id
        )

        if request.stream:
            # Streaming response
            async def stream_with_metadata():
                # Emit provider info as first SSE event
                provider_info = {
                    "type": "provider_info",
                    "provider": provider.name,
                    "quality_tier": status.quality_tier,
                    "failover": did_failover,
                    "model": status.current_model
                }
                yield f"data: {json.dumps(provider_info)}\n\n"

                # Stream content
                async for chunk in provider.stream_chat(chat_req):
                    yield chunk

            return StreamingResponse(
                stream_with_metadata(),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            response = await provider.chat(chat_req)

            # Record usage
            tokens_used = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
            record_usage(user_id, tokens_used)

            return {
                "content": response.content,
                "provider": response.provider,
                "quality_tier": response.quality_tier,
                "model": response.model,
                "failover": did_failover,
                "usage": response.usage
            }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")


# =============================================================================
# Legacy Generate Endpoint (Backward Compatibility)
# =============================================================================

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate LLM response (legacy endpoint).

    Uses provider registry with automatic failover.
    For new integrations, use /llm/chat instead.
    """
    user_id = request.user_id or "default"
    registry = get_registry()

    # Check rate limit
    estimated_tokens = len(request.prompt.split()) * 2 + request.max_tokens
    if not check_rate_limit(user_id, estimated_tokens):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making more requests."
        )

    try:
        # Get provider with failover
        provider, did_failover = await registry.get_provider_with_failover()
        status = await provider.get_status()

        # Build chat request from legacy format
        chat_req = ChatRequest(
            messages=[{"role": "user", "content": request.prompt}],
            system_prompt=request.system,
            max_tokens=request.max_tokens,
            temperature=0.7,
            stream=False,
            user_id=user_id
        )

        response = await provider.chat(chat_req)

        # Record usage
        tokens_used = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
        record_usage(user_id, tokens_used)

        return GenerateResponse(
            content=response.content,
            model=response.model,
            tokens_used=tokens_used,
            provider=response.provider,
            quality_tier=response.quality_tier,
            failover=did_failover
        )

    except RuntimeError as e:
        # No providers available - use demo fallback
        logger.warning(f"No providers available: {e}")
        response = _demo_response(request.prompt)
        tokens_used = len(response.split())
        record_usage(user_id, tokens_used)

        return GenerateResponse(
            content=response,
            model="demo",
            tokens_used=tokens_used,
            provider="demo",
            quality_tier="basic",
            failover=True
        )


def _demo_response(prompt: str) -> str:
    """Generate demo response when no LLM available."""
    prompt_lower = prompt.lower()

    if "innovation" in prompt_lower or "idea" in prompt_lower:
        return "That's an interesting concept. Tell me more about the problem you're trying to solve and who would benefit from your solution."

    if "fear" in prompt_lower or "concern" in prompt_lower:
        return "Those concerns are valid and worth exploring. What's the worst-case scenario you're imagining, and what would need to be true to mitigate that risk?"

    if "hypothesis" in prompt_lower or "test" in prompt_lower:
        return "Testing assumptions early is crucial. What's the smallest experiment you could run to validate or invalidate this hypothesis?"

    return "I understand. Can you tell me more about what you're thinking?"


# =============================================================================
# BYOK (Bring Your Own Key) API Key Management
# =============================================================================

async def validate_anthropic_key(api_key: str) -> tuple[bool, List[str], Optional[str]]:
    """
    Validate an Anthropic API key by making a minimal API call.
    Returns: (is_valid, available_models, error_message)
    """
    if not api_key:
        return False, [], "No API key provided"

    if not api_key.startswith("sk-ant-"):
        return False, [], "Invalid API key format. Anthropic keys start with sk-ant-"

    models = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022"
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )

            if response.status_code == 200:
                return True, models, None
            elif response.status_code == 401:
                return False, [], "Invalid API key"
            elif response.status_code == 404:
                return True, models, None
            elif response.status_code == 403:
                return False, [], "API key does not have access to this resource"
            elif response.status_code == 429:
                return True, models, None
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"API returned status {response.status_code}")
                return False, [], error_msg

    except httpx.TimeoutException:
        logger.warning("Timeout validating API key, assuming valid based on format")
        return True, models, None
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return False, [], str(e)


@app.get("/api/v1/validate-key", response_model=ValidateKeyResponse)
async def validate_key():
    """Validate the currently configured Anthropic API key."""
    api_key = get_api_key()

    if not api_key:
        return ValidateKeyResponse(
            valid=False,
            models_available=[],
            error="No API key configured"
        )

    is_valid, models, error = await validate_anthropic_key(api_key)

    _config["api_key_validated"] = is_valid
    _config["available_models"] = models if is_valid else []

    return ValidateKeyResponse(
        valid=is_valid,
        models_available=models if is_valid else [],
        error=error
    )


@app.post("/api/v1/validate-key", response_model=ValidateKeyResponse)
async def validate_provided_key(request: ConfigureRequest):
    """Validate a provided API key without configuring it."""
    api_key = request.anthropic_api_key

    if not api_key:
        return ValidateKeyResponse(
            valid=False,
            models_available=[],
            error="No API key provided"
        )

    is_valid, models, error = await validate_anthropic_key(api_key)

    return ValidateKeyResponse(
        valid=is_valid,
        models_available=models if is_valid else [],
        error=error
    )


@app.post("/api/v1/configure", response_model=ConfigureResponse)
async def configure_api_key(request: ConfigureRequest):
    """
    Configure the Anthropic API key at runtime (BYOK).
    Also updates the Claude provider in the registry.
    """
    api_key = request.anthropic_api_key

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    if not api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format. Anthropic keys start with sk-ant-"
        )

    is_valid, models, error = await validate_anthropic_key(api_key)

    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid API key: {error}")

    # Update runtime config
    _config["anthropic_api_key"] = api_key
    _config["api_key_validated"] = True
    _config["available_models"] = models

    # Update Claude provider in registry if present
    registry = get_registry()
    for provider in registry.get_providers():
        if provider.name == "anthropic":
            provider.update_api_key(api_key)
            break

    logger.info("API key configured successfully via BYOK")

    return ConfigureResponse(
        success=True,
        message="API key configured successfully",
        api_key_configured=True
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
