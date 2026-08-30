# Providers

## Implemented

| Provider | Status | Description |
|----------|--------|-------------|
| `mock-primary` | Active | Default demo provider; fails when `model=fail` |
| `mock-fallback` | Active | Secondary provider in fallback chain |
| `openai-stub` | Stub | Wire `OPENAI_API_KEY` for production |
| `anthropic-stub` | Stub | Wire `ANTHROPIC_API_KEY` for production |

## Model Aliases

| Alias | Routes to |
|-------|-----------|
| `gpt-4o-mini` | mock-primary |
| `gpt-4o` | mock-primary |
| `claude-3-haiku` | mock-primary |
| `default` | mock-primary |

Configure in `app/providers/registry.py`.

## Adding a Provider

1. Subclass `Provider` in `app/providers/`
2. Implement `async def complete(model, messages) -> CompletionResult`
3. Register in `PROVIDERS` dict
4. Add env-based factory if credentials required

## Fallback

`FALLBACK_PROVIDER` env (default `mock-fallback`) is used when primary raises `ProviderError` after retries.
