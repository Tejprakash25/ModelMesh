from app.providers.base import Provider
from app.providers.mock import (
    AnthropicProviderStub,
    MockFallbackProvider,
    MockPrimaryProvider,
    OpenAIProviderStub,
)

PROVIDERS: dict[str, Provider] = {
    "mock-primary": MockPrimaryProvider(),
    "mock-fallback": MockFallbackProvider(),
    "openai-stub": OpenAIProviderStub(),
    "anthropic-stub": AnthropicProviderStub(),
}

MODEL_ALIASES: dict[str, str] = {
    "gpt-4o-mini": "mock-primary",
    "gpt-4o": "mock-primary",
    "claude-3-haiku": "mock-primary",
    "default": "mock-primary",
}


def get_provider(name: str) -> Provider:
    if name not in PROVIDERS:
        raise KeyError(f"Unknown provider: {name}")
    return PROVIDERS[name]


def resolve_provider_for_model(model: str) -> str:
    return MODEL_ALIASES.get(model, MODEL_ALIASES["default"])
