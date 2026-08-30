from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessageSchema]
    temperature: float = Field(default=0.7, ge=0, le=2)


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessageSchema
    finish_reason: str = "stop"


class UsageSchema(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageSchema
    provider: str
    cached: bool = False
    fallback_used: bool = False


class ApiKeyCreate(BaseModel):
    name: str
    project_id: str = "default"
    rate_limit_requests: int = 100
    budget_usd: float | None = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    project_id: str
    is_active: bool
    rate_limit_requests: int
    budget_usd: float | None
    spent_usd: float


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str
