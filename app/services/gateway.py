import asyncio
import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ApiKey, RequestLog, UsageLog
from app.providers.base import ChatMessage, ProviderError
from app.providers.registry import get_provider, resolve_provider_for_model
from app.services.cache import cache_key, get_cached_response, set_cached_response

logger = structlog.get_logger()


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens / 1000 * settings.cost_per_1k_prompt_tokens
        + completion_tokens / 1000 * settings.cost_per_1k_completion_tokens
    )


def redact_messages(messages: list[dict]) -> str:
    if settings.redact_logs:
        return json.dumps([{"role": m["role"], "content": "[REDACTED]"} for m in messages])
    return json.dumps(messages)


async def complete_with_fallback(
    model: str,
    messages: list[ChatMessage],
    max_retries: int = 2,
) -> tuple:
    provider_name = resolve_provider_for_model(model)
    fallback_name = settings.fallback_provider
    chain = [provider_name]
    if fallback_name != provider_name:
        chain.append(fallback_name)

    last_error: Exception | None = None
    for attempt, pname in enumerate(chain):
        provider = get_provider(pname)
        for retry in range(max_retries + 1):
            try:
                result = await provider.complete(model, messages)
                if attempt > 0:
                    logger.info("provider_fallback_success", provider=pname, model=model)
                return result, attempt > 0
            except ProviderError as exc:
                last_error = exc
                logger.warning(
                    "provider_error",
                    provider=pname,
                    attempt=retry,
                    error=str(exc),
                )
                if retry < max_retries:
                    await asyncio.sleep(0.05 * (retry + 1))
    raise ProviderError(str(last_error) if last_error else "All providers failed")


async def log_usage(
    db: AsyncSession,
    api_key: ApiKey,
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float,
    cached: bool,
    request_id: str,
    status: str = "success",
) -> None:
    total = prompt_tokens + completion_tokens
    db.add(
        UsageLog(
            api_key_id=api_key.id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
            cached=cached,
            request_id=request_id,
            status=status,
        )
    )
    api_key.spent_usd += cost


async def log_request(
    db: AsyncSession,
    api_key: ApiKey,
    *,
    request_id: str,
    endpoint: str,
    request_body: str,
    response_body: str,
) -> None:
    db.add(
        RequestLog(
            api_key_id=api_key.id,
            request_id=request_id,
            endpoint=endpoint,
            request_body=request_body,
            response_body=response_body,
        )
    )
