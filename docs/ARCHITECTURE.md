# Architecture

## Components

| Layer | Responsibility |
|-------|----------------|
| **API** | OpenAI-compatible `/v1/chat/completions`, admin endpoints |
| **Auth** | SHA-256 hashed API keys in PostgreSQL |
| **Rate limiter** | Redis sorted-set sliding window per key |
| **Cache** | Redis JSON blob keyed by SHA-256(model + messages) |
| **Router** | Model alias → provider; primary + fallback chain |
| **Providers** | Pluggable `Provider.complete()` interface |
| **Billing** | `usage_logs` table + per-key `spent_usd` / `budget_usd` |
| **Audit** | `request_logs` with optional redaction |

## Request Flow

1. Validate Bearer API key
2. Check budget and rate limit
3. Cache lookup — return if hit (zero marginal cost)
4. Route to primary provider; retry; fallback on failure
5. Persist usage + request logs
6. Write cache entry

## Deployment

- Stateless API containers behind load balancer
- PostgreSQL for durable logs and keys
- Redis for ephemeral rate limit + cache data

See [docker-compose.yml](../docker-compose.yml) for local topology.
