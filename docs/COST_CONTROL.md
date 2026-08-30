# Cost Control

## Per-Request Estimation

```
cost = (prompt_tokens / 1000) * COST_PER_1K_PROMPT
     + (completion_tokens / 1000) * COST_PER_1K_COMPLETION
```

Defaults in `app/core/config.py` (tuned for mock/demo).

## Usage Tracking

Every completion writes to `usage_logs`:

- `prompt_tokens`, `completion_tokens`, `total_tokens`
- `estimated_cost_usd`
- `cached=true` for cache hits (cost logged as 0)

## Budgets

API keys may set `budget_usd`. Gateway increments `spent_usd` on each non-cached completion.

Query spend: `GET /usage` with Bearer token.

## Analytics

Aggregate by key, model, provider via SQL on `usage_logs` — suitable for Grafana/Metabase dashboards.
