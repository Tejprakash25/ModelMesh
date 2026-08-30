from app.providers.base import ChatMessage, CompletionResult, Provider, ProviderError


class MockPrimaryProvider(Provider):
    name = "mock-primary"

    async def complete(self, model: str, messages: list[ChatMessage]) -> CompletionResult:
        if model == "fail":
            raise ProviderError("Simulated primary provider failure")
        last = messages[-1].content if messages else ""
        prompt_text = " ".join(m.content for m in messages)
        prompt_tokens = max(1, len(prompt_text.split()))
        completion = f"[mock-primary/{model}] Echo: {last}"
        completion_tokens = max(1, len(completion.split()))
        return CompletionResult(
            content=completion,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            provider=self.name,
        )


class MockFallbackProvider(Provider):
    name = "mock-fallback"

    async def complete(self, model: str, messages: list[ChatMessage]) -> CompletionResult:
        last = messages[-1].content if messages else ""
        prompt_text = " ".join(m.content for m in messages)
        prompt_tokens = max(1, len(prompt_text.split()))
        completion = f"[mock-fallback/{model}] Fallback response: {last}"
        completion_tokens = max(1, len(completion.split()))
        return CompletionResult(
            content=completion,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            provider=self.name,
        )


class OpenAIProviderStub(Provider):
    """Interface stub — wire OPENAI_API_KEY in production."""

    name = "openai-stub"

    async def complete(self, model: str, messages: list[ChatMessage]) -> CompletionResult:
        raise ProviderError("OpenAI provider not configured — set OPENAI_API_KEY")


class AnthropicProviderStub(Provider):
    name = "anthropic-stub"

    async def complete(self, model: str, messages: list[ChatMessage]) -> CompletionResult:
        raise ProviderError("Anthropic provider not configured — set ANTHROPIC_API_KEY")
