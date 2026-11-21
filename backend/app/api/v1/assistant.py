"""FastAPI router for Phase 6 Conversational AI Assistant.

Provides:
- POST /api/v1/assistant/chat: Rate-limited conversational endpoint preserving deterministic guidance
- GET /api/v1/assistant/health: Passive readiness check reporting model & configuration safely
- POST /api/v1/assistant/smoke-test: Protected diagnostic probe for operator verification
"""

import asyncio
import ipaddress
import logging
import secrets
import time
from typing import Dict, List, Optional, Tuple, Union
from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.config import settings
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantHealthResponse,
    AssistantHealthStatus,
    AssistantSmokeTestResponse,
)
from app.services.assistant_service import assistant_service
from app.services.impact_service import impact_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Conversational AI Assistant"])


class InMemoryRateLimiter:
    """Sliding-window process-local in-memory rate limiter using monotonic time.
    
    Architectural Note:
    This rate limiter is process-local and suitable for single-process deployments.
    Multi-worker or distributed deployments require shared state infrastructure (e.g. Redis).
    """

    def __init__(self, max_requests: int, window_seconds: float, max_clients: int = 1000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._records: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, client_key: str) -> Tuple[bool, int]:
        """Check whether the client request is permitted.
        
        Returns:
            Tuple[allowed (bool), retry_after_seconds (int)]
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            # Filter out expired timestamps for this client
            timestamps = self._records.get(client_key, [])
            timestamps = [t for t in timestamps if t > cutoff]

            # Storage hygiene: clean up dead entries if registry exceeds capacity
            if len(self._records) > self.max_clients:
                expired_keys = [k for k, ts in self._records.items() if not ts or ts[-1] <= cutoff]
                for k in expired_keys:
                    self._records.pop(k, None)

            # Check threshold
            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                self._records[client_key] = timestamps
                return False, retry_after

            # Record this valid request
            timestamps.append(now)
            self._records[client_key] = timestamps
            return True, 0

    async def reset(self):
        """Reset internal rate limiter state (primarily for automated testing)."""
        async with self._lock:
            self._records.clear()

    def reset_sync(self):
        """Synchronously reset internal rate limiter state for tests."""
        self._records.clear()


# Application rate limiters
chat_rate_limiter = InMemoryRateLimiter(max_requests=15, window_seconds=60.0)
smoke_test_rate_limiter = InMemoryRateLimiter(max_requests=3, window_seconds=600.0)


def is_ip_trusted(
    ip_obj: Union[ipaddress.IPv4Address, ipaddress.IPv6Address],
    trusted_proxy_configs: List[str]
) -> bool:
    """Check whether a given parsed IP address matches any trusted proxy or network."""
    for item in trusted_proxy_configs:
        try:
            if "/" in item:
                if ip_obj in ipaddress.ip_network(item, strict=False):
                    return True
            else:
                if ip_obj == ipaddress.ip_address(item):
                    return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request) -> str:
    """Safely resolve client IP address using right-to-left verification of X-Forwarded-For.
    
    Security Specification:
    1. Direct peer IP (request.client.host) is trusted by default.
    2. X-Forwarded-For is ONLY inspected if direct peer IP is explicitly listed in settings.TRUSTED_PROXY_IPS.
    3. Every IP in the chain is validated using Python's ipaddress module.
    4. The chain is walked strictly right-to-left, skipping trusted proxy addresses.
    5. The first untrusted address encountered from the right is selected as the genuine client IP.
    6. Malicious client-supplied leading X-Forwarded-For entries are never reached or trusted.
    7. Any malformed, invalid, or unparseable IP in the chain triggers a safe fallback to direct connection IP.
    """
    direct_ip_str = request.client.host if request.client else "127.0.0.1"

    trusted_proxy_configs = getattr(settings, "TRUSTED_PROXY_IPS", [])
    if not trusted_proxy_configs:
        return direct_ip_str

    try:
        direct_ip_obj = ipaddress.ip_address(direct_ip_str)
    except ValueError:
        return direct_ip_str

    # Only inspect X-Forwarded-For if the direct peer is an explicitly trusted proxy
    if not is_ip_trusted(direct_ip_obj, trusted_proxy_configs):
        return direct_ip_str

    forwarded_header = request.headers.get("X-Forwarded-For")
    if not forwarded_header or not forwarded_header.strip():
        return direct_ip_str

    parts = [p.strip() for p in forwarded_header.split(",") if p.strip()]
    if not parts:
        return direct_ip_str

    # Walk forwarding chain right-to-left
    for part in reversed(parts):
        try:
            part_ip_obj = ipaddress.ip_address(part)
        except ValueError:
            # Malformed entry in forwarding chain: abort and safely fall back to direct_ip
            logger.warning("Malformed IP in X-Forwarded-For chain: %s. Falling back to direct connection IP.", part)
            return direct_ip_str

        if not is_ip_trusted(part_ip_obj, trusted_proxy_configs):
            # First untrusted address from the right is the genuine client IP
            return str(part_ip_obj)

    # If all entries in the chain were trusted proxies, return direct_ip_str
    return direct_ip_str


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Consult the conversational family air assistant",
    description="Provides grounded, multi-lingual explanations backed by deterministic CPCB/NCDC health advisories. Rate-limited to 15 req/min.",
)
async def chat_assistant(
    request: AssistantChatRequest,
    raw_request: Request,
    response: Response,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID", description="Optional impact session bearer token"),
) -> AssistantChatResponse:
    """Conversational assistant endpoint."""
    client_ip = get_client_ip(raw_request)

    # 1. Enforce process-local rate limiting (15 requests per 60 seconds)
    allowed, retry_after = await chat_rate_limiter.check(client_ip)
    if not allowed:
        logger.warning("Chat rate limit exceeded", extra={"client_ip": client_ip, "retry_after": retry_after})
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 15 requests per 60 seconds. Please wait before retrying.",
            headers={"Retry-After": str(retry_after)},
        )

    # 2. Support X-Session-ID strictly where impact context is requested and validated
    validated_session_id: Optional[str] = None
    if request.context_inputs.include_impact_summary:
        if x_session_id:
            try:
                impact_service.get_session_summary(x_session_id)
                validated_session_id = x_session_id
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active impact tracking session not found or expired. Please create a new session.",
                )
        # If include_impact_summary is True but no header provided, proceed with validated_session_id=None

    # 3. Process chat with authoritative guidance preservation
    try:
        return await assistant_service.process_chat(
            request=request,
            session_id=validated_session_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in assistant chat handler: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the assistant response.",
        )


@router.get(
    "/health",
    response_model=AssistantHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Passive assistant readiness check",
    description="Reports model identifier and whether the Gemini API key is configured. Consumes zero tokens; makes zero outbound requests.",
)
def get_assistant_health() -> AssistantHealthResponse:
    """Passive readiness check for the assistant generative layer."""
    configured_model = settings.GEMINI_MODEL or "gemini-3.8-flash"
    api_key_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    health_status = (
        AssistantHealthStatus.READY if api_key_configured else AssistantHealthStatus.API_KEY_MISSING
    )

    return AssistantHealthResponse(
        status=health_status,
        configured_model=configured_model,
        api_key_configured=api_key_configured,
    )


@router.post(
    "/smoke-test",
    response_model=AssistantSmokeTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Controlled operator diagnostic probe",
    description="Performs an authenticated minimal test request against Google Gemini. Requires separate X-Operator-Token. Strictly rate-limited to 3 req/10min.",
)
async def operator_smoke_test(
    raw_request: Request,
    response: Response,
    x_operator_token: Optional[str] = Header(None, alias="X-Operator-Token", description="Dedicated operator smoke-test secret token"),
) -> AssistantSmokeTestResponse:
    """Operator smoke-test probe."""
    # 1. Check if endpoint is enabled
    configured_token = getattr(settings, "ASSISTANT_SMOKE_TEST_TOKEN", "")
    if not configured_token or not configured_token.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant operator smoke test is disabled (operator token not configured).",
        )

    # 2. Enforce strict smoke-test rate limit BEFORE authentication (3 attempts per 10 minutes)
    # This prevents brute-force operator token guessing attacks.
    client_ip = get_client_ip(raw_request)
    allowed, retry_after = await smoke_test_rate_limiter.check(client_ip)
    if not allowed:
        logger.warning("Operator smoke-test rate limit exceeded", extra={"client_ip": client_ip, "retry_after": retry_after})
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Operator smoke-test rate limit exceeded. Maximum 3 requests per 10 minutes.",
            headers={"Retry-After": str(retry_after)},
        )

    # 3. Check presence of operator token
    if not x_operator_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing operator token.",
        )

    # 4. Disallow using GEMINI_API_KEY as the operator token
    gemini_key = getattr(settings, "GEMINI_API_KEY", "")
    if gemini_key and secrets.compare_digest(x_operator_token, gemini_key):
        logger.warning("Operator smoke-test rejected: Attempt to use GEMINI_API_KEY as operator token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid operator token.",
        )

    # 5. Constant-time credential comparison
    if not secrets.compare_digest(x_operator_token, configured_token):
        logger.warning("Operator smoke-test rejected: Invalid operator token supplied.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid operator token.",
        )

    # 6. Execute minimal authenticated diagnostic probe
    success, category, latency_ms = await assistant_service.run_smoke_test()

    return AssistantSmokeTestResponse(
        success=success,
        configured_model=settings.GEMINI_MODEL or "gemini-3.8-flash",
        latency_ms=latency_ms,
        diagnostic_category=category,
    )
