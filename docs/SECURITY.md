# Security

## Authentication

- Clients send `Authorization: Bearer sk-...`
- Only SHA-256 hash stored in database
- Inactive keys rejected with 401

## Rate Limiting

- Per-key sliding window in Redis
- Returns HTTP 429 when exceeded
- Limits configurable per key at creation

## Budget Control

- Optional `budget_usd` per API key
- Returns HTTP 402 when `spent_usd >= budget_usd`

## Log Redaction

Set `REDACT_LOGS=true` to store `[REDACTED]` instead of message content in `request_logs`.

## Production Checklist

- [ ] Rotate `DEV_API_KEY`; do not use default keys in production
- [ ] TLS termination at reverse proxy
- [ ] Restrict admin endpoints (`/keys`, `/usage`) to internal network or separate admin keys
- [ ] Enable `REDACT_LOGS` for PII-sensitive deployments
- [ ] Store provider API keys in secrets manager, not `.env` in repo
