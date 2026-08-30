import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_api_key_record, new_request_id
from app.core.lifespan import get_db, get_redis
from app.db.models import ApiKey
from app.providers.base import ChatMessage, ProviderError
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessageSchema,
    UsageSchema,
)
from app.services.cache import cache_key, check_rate_limit, get_cached_response, set_cached_response
from app.services.gateway import (
    complete_with_fallback,
    estimate_cost,
    log_request,
    log_usage,
    redact_messages,
)

router = APIRouter()


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    api_key: ApiKey = Depends(get_api_key_record),
    db: AsyncSession = Depends(get_db),
) -> ChatCompletionResponse:
    redis = get_redis()
    await check_rate_limit(api_key, redis)

    request_id = new_request_id()
    msg_dicts = [m.model_dump() for m in body.messages]
    ck = cache_key(body.model, msg_dicts)

    cached = await get_cached_response(redis, ck)
    if cached:
        await log_usage(
            db,
            api_key,
            provider=cached["provider"],
            model=body.model,
            prompt_tokens=cached["usage"]["prompt_tokens"],
            completion_tokens=cached["usage"]["completion_tokens"],
            cost=0.0,
            cached=True,
            request_id=request_id,
        )
        await db.commit()
        cached["id"] = request_id
        cached["cached"] = True
        return ChatCompletionResponse(**cached)

    messages = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    try:
        result, fallback_used = await complete_with_fallback(body.model, messages)
    except ProviderError as exc:
        await log_usage(
            db,
            api_key,
            provider="none",
            model=body.model,
            prompt_tokens=0,
            completion_tokens=0,
            cost=0.0,
            cached=False,
            request_id=request_id,
            status="error",
        )
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    cost = estimate_cost(result.prompt_tokens, result.completion_tokens)
    await log_usage(
        db,
        api_key,
        provider=result.provider,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost=cost,
        cached=False,
        request_id=request_id,
    )

    response = ChatCompletionResponse(
        id=request_id,
        model=result.model,
        choices=[
            ChatCompletionChoice(
                message=ChatMessageSchema(role="assistant", content=result.content),
            )
        ],
        usage=UsageSchema(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.prompt_tokens + result.completion_tokens,
        ),
        provider=result.provider,
        cached=False,
        fallback_used=fallback_used,
    )

    await log_request(
        db,
        api_key,
        request_id=request_id,
        endpoint="/v1/chat/completions",
        request_body=redact_messages(msg_dicts),
        response_body=json.dumps(response.model_dump()),
    )
    await db.commit()

    await set_cached_response(redis, ck, response.model_dump())
    return response
