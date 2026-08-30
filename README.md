# ModelMesh

> **A production-oriented, OpenAI-compatible LLM gateway built with FastAPI, PostgreSQL, Redis, and pluggable model providers.**

ModelMesh sits between client applications and LLM providers and adds a consistent API layer for **authentication, rate limiting, caching, provider fallback, usage tracking, budget control, request auditing, and observability-ready infrastructure**.

**Author:** Tejprakash Mirashi
**GitHub:** [Tejprakash25/ModelMesh](https://github.com/Tejprakash25/ModelMesh)

---

## Overview

Applications integrating multiple LLM providers often need to solve the same operational problems repeatedly:

* How should API access be authenticated?
* How can requests be rate-limited per client?
* How can repeated requests avoid unnecessary model calls?
* What happens when a primary provider fails?
* How much token usage and estimated cost does each client generate?
* How can individual clients be restricted by budget?
* How should request activity be audited?
* How can providers be added without rewriting the gateway?

**ModelMesh provides these capabilities behind a single OpenAI-compatible API.**

Instead of every application handling provider management and operational controls independently:

```text
Client Application
       |
       v
   ModelMesh
       |
  +----+-------------------+
  |    |      |      |     |
  v    v      v      v     v
 Auth Rate   Cache  Usage Fallback
 Limit       Control Billing Provider
       |
       v
   LLM Provider
```

The gateway is designed around a **stateless API layer**, with PostgreSQL used for durable application data and Redis used for ephemeral caching and rate-limiting state.

---

## Key Features

### OpenAI-Compatible API

Expose an OpenAI-style endpoint:

```text
POST /v1/chat/completions
```

Clients send standard bearer-authenticated chat completion requests.

### API Key Authentication

* API keys are generated using secure random tokens.
* Only the **SHA-256 hash** of a key is stored in PostgreSQL.
* Inactive or invalid keys are rejected.
* Each key can have its own project ID, rate limit, and optional budget.

### Provider Routing and Fallback

Model aliases are mapped to providers through a pluggable provider registry.

```text
Request
   |
   v
Primary Provider
   |
   +---- success ------> Response
   |
   +---- failure
          |
        retry
          |
          v
   Fallback Provider
          |
          v
        Response
```

The gateway retries provider failures and automatically switches to the configured fallback provider when necessary.

### Redis Rate Limiting

ModelMesh implements a **per-API-key sliding-window rate limiter** using Redis sorted sets.

Example:

```text
100 requests / 60 seconds
```

Requests beyond the configured limit receive:

```text
HTTP 429 Too Many Requests
```

### Response Caching

Responses can be cached in Redis using a SHA-256 cache key derived from:

```text
model + messages
```

Repeated requests can therefore return directly from cache instead of invoking a provider again.

```text
Request
  |
  v
Cache Lookup
  |
  +---- HIT ----> Cached Response
  |
  +---- MISS ---> Provider
```

Cached requests are logged with zero additional estimated provider cost.

### Usage and Cost Tracking

Each completion records:

* Prompt tokens
* Completion tokens
* Total tokens
* Provider
* Model
* Estimated cost
* Cache status
* Request ID
* Request status

Estimated cost is calculated as:

```text
cost =
(prompt_tokens / 1000 × prompt_price)
+
(completion_tokens / 1000 × completion_price)
```

### Budget Control

API keys may define an optional USD budget.

When:

```text
spent_usd >= budget_usd
```

the gateway returns:

```text
HTTP 402 Payment Required
```

### Request Auditing

Requests and responses can be persisted in PostgreSQL with configurable message redaction.

Set:

```env
REDACT_LOGS=true
```

to replace message content with:

```text
[REDACTED]
```

in request logs.

### Provider Abstraction

Providers implement a common asynchronous interface:

```python
class Provider(ABC):
    async def complete(
        self,
        model: str,
        messages: list[ChatMessage]
    ) -> CompletionResult:
        ...
```

This keeps provider-specific implementation separate from gateway logic.

### Async Architecture

The application uses:

* FastAPI
* Async SQLAlchemy
* asyncpg
* async Redis
* asynchronous provider interfaces

This keeps I/O-heavy request handling non-blocking.

---

## Architecture

```text
                         +----------------------+
                         |     Client App       |
                         +----------+-----------+
                                    |
                                    | Bearer API Key
                                    v
                         +----------------------+
                         |     ModelMesh API    |
                         |      FastAPI         |
                         +----------+-----------+
                                    |
                  +-----------------+------------------+
                  |                 |                  |
                  v                 v                  v
             Authentication    Rate Limiting       Cache Lookup
                  |                 |                  |
                  v                 v                  v
             PostgreSQL           Redis              Redis
                  |
                  +-----------------------------+
                                                |
                                                v
                                     Provider Resolution
                                                |
                              +-----------------+----------------+
                              |                                  |
                              v                                  v
                       Primary Provider                  Fallback Provider
                              |                                  |
                              +----------------+-----------------+
                                               |
                                               v
                                         LLM Response
                                               |
                            +------------------+------------------+
                            |                                     |
                            v                                     v
                      Usage / Cost Logging                  Request Logging
                            |                                     |
                            +------------------+------------------+
                                               |
                                               v
                                          PostgreSQL
```

---

## Request Flow

A typical `/v1/chat/completions` request follows this sequence:

```text
1. Validate Bearer API key
        |
2. Check budget
        |
3. Check Redis rate limit
        |
4. Generate request ID
        |
5. Build cache key
        |
6. Check Redis cache
        |
        +---- cache hit ----> log usage as cached -> return
        |
        +---- cache miss
                    |
7. Resolve primary provider
                    |
8. Retry failed provider calls
                    |
9. Fallback to secondary provider when required
                    |
10. Estimate cost
                    |
11. Persist usage data
                    |
12. Persist request/response audit log
                    |
13. Store successful response in Redis
                    |
14. Return OpenAI-compatible response
```

---

## Technology Stack

| Technology            | Purpose                            |
| --------------------- | ---------------------------------- |
| **Python 3.12**       | Application language               |
| **FastAPI**           | REST API framework                 |
| **Pydantic Settings** | Configuration management           |
| **SQLAlchemy 2.x**    | Async ORM and database access      |
| **PostgreSQL 16**     | API keys, usage logs, request logs |
| **Redis 7**           | Cache and rate limiting            |
| **Alembic**           | Database schema migrations         |
| **HTTPX**             | Async HTTP client foundation       |
| **Structlog**         | Structured JSON logging            |
| **Prometheus Client** | Metrics integration foundation     |
| **OpenTelemetry**     | Tracing/instrumentation foundation |
| **Docker**            | Containerization                   |
| **GitHub Actions**    | Continuous integration             |
| **Pytest**            | Automated testing                  |
| **Ruff**              | Linting and code quality           |

---

## Project Structure

```text
ModelMesh/
│
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── admin.py
│   │       └── chat.py
│   │
│   ├── auth/
│   │   ├── deps.py
│   │   └── keys.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── lifespan.py
│   │   └── logging.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── models.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── mock.py
│   │   └── registry.py
│   │
│   ├── schemas/
│   │   └── openai.py
│   │
│   ├── services/
│   │   ├── cache.py
│   │   ├── gateway.py
│   │   └── seed.py
│   │
│   └── main.py
│
├── alembic/
│   ├── versions/
│   │   └── 001_initial.py
│   └── env.py
│
├── frontend/
│   └── index.html
│
├── tests/
│   └── test_gateway.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── COST_CONTROL.md
│   ├── PROVIDERS.md
│   └── SECURITY.md
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── ROADMAP.md
```

---

## Database Design

ModelMesh currently uses three primary tables.

### `api_keys`

Stores API client metadata and hashed credentials.

```text
id
name
key_hash
key_prefix
project_id
is_active
rate_limit_requests
rate_limit_window_seconds
budget_usd
spent_usd
created_at
```

### `usage_logs`

Stores token usage and estimated cost for every completion.

```text
id
api_key_id
provider
model
prompt_tokens
completion_tokens
total_tokens
estimated_cost_usd
cached
status
request_id
created_at
```

### `request_logs`

Stores request and response audit information.

```text
id
api_key_id
request_id
endpoint
request_body
response_body
created_at
```

Database changes are managed through **Alembic migrations**.

---

## API Endpoints

### Chat Completions

```http
POST /v1/chat/completions
```

Example:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-dev-docker-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {
        "role": "user",
        "content": "Hello ModelMesh"
      }
    ]
  }'
```

### Health

```http
GET /health
```

### Provider Information

```http
GET /providers
```

### Usage Summary

```http
GET /usage
```

Requires a valid bearer API key.

### API Key Management

```http
GET  /keys
POST /keys
```

---

## Providers

The project includes a provider abstraction and registry.

Current providers:

```text
mock-primary
mock-fallback
openai-stub
anthropic-stub
```

The mock providers are fully usable for local development and testing.

The OpenAI and Anthropic implementations are currently **stubs**, intended to be connected to real provider APIs later.

### Adding a New Provider

1. Create a provider class implementing `Provider`.
2. Implement the async `complete()` method.
3. Register the provider in `app/providers/registry.py`.
4. Add any required credentials through environment configuration.

This allows provider-specific code to remain isolated from the gateway.

---

## Local Setup

### Prerequisites

Install:

* Python 3.10+
* PostgreSQL
* Redis

Or use Docker Compose to start the complete local infrastructure.

Python **3.12** is used by the project's Dockerfile and CI workflow.

---

## Option 1 — Run with Docker Compose

Clone the repository:

```bash
git clone https://github.com/Tejprakash25/ModelMesh.git
cd ModelMesh
```

Start all services:

```bash
docker compose up --build
```

This starts:

```text
ModelMesh API   -> http://localhost:8000
PostgreSQL      -> localhost:5433
Redis           -> localhost:6380
```

The API container automatically:

1. Runs Alembic migrations.
2. Starts Uvicorn.
3. Seeds the development API key.

Open:

```text
http://localhost:8000/docs
```

to view the FastAPI Swagger documentation.

Dashboard:

```text
http://localhost:8000/dashboard
```

---

## Option 2 — Run Locally

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -e ".[dev]"
```

Copy the environment template:

```bash
cp .env.example .env
```

Update the database and Redis settings if necessary.

Run migrations:

```bash
alembic upgrade head
```

Start the application:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

## Environment Configuration

Example `.env`:

```env
APP_NAME=ModelMesh
ENVIRONMENT=development
DEBUG=true

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/llm_gateway
REDIS_URL=redis://localhost:6379/0

DEFAULT_PROVIDER=mock-primary
FALLBACK_PROVIDER=mock-fallback

CACHE_TTL_SECONDS=3600
CACHE_ENABLED=true

RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

REDACT_LOGS=false

OTEL_ENABLED=false
OTEL_SERVICE_NAME=ModelMesh

DEV_API_KEY=sk-dev-local-key-change-me
```

### Important

The example credentials are intended for local development only.

Never use the development API key or default database credentials in production.

---

## Testing

The project includes automated asynchronous tests using:

* Pytest
* pytest-asyncio
* SQLite for isolated test database execution
* Fake Redis

Run:

```bash
pytest -q
```

The current test suite covers:

```text
✓ Health endpoint
✓ Authentication enforcement
✓ Successful chat completion
✓ Rate limiting
✓ Provider fallback
✓ Usage logging
✓ Cache hits
```

---

## Code Quality

Run Ruff:

```bash
ruff check app tests
```

The GitHub Actions workflow runs both linting and tests automatically.

```text
Push / Pull Request
        |
        v
GitHub Actions
        |
   +----+----+
   |         |
 Ruff      Pytest
   |         |
   +----+----+
        |
     CI Result
```

---

## Security Considerations

ModelMesh includes several application-level security controls:

### API key storage

Raw API keys are never persisted. Only SHA-256 hashes are stored.

### Budget enforcement

Requests are rejected when configured spending limits are reached.

### Rate limiting

Each API key receives independent Redis-backed request limits.

### Log redaction

Sensitive request content can be hidden using:

```env
REDACT_LOGS=true
```

### Production hardening

Before production deployment:

* Rotate all development credentials.
* Terminate TLS at the reverse proxy/load balancer.
* Move provider secrets to a proper secret manager.
* Restrict administrative endpoints.
* Enable log redaction where sensitive data may be present.
* Review database access policies.
* Replace development API keys with managed credentials.

---

## Observability

The project includes the foundation for production observability:

* Structured JSON logging with Structlog
* Prometheus client dependency
* OpenTelemetry API/SDK
* FastAPI OpenTelemetry instrumentation

These components provide a foundation for extending the gateway with centralized metrics, distributed traces, and monitoring infrastructure.

---

## Why ModelMesh?

Modern LLM applications often need more than a direct API call to a single model provider.

ModelMesh centralizes operational concerns into one gateway:

```text
               +------------------+
               |   Client Apps    |
               +--------+---------+
                        |
                        v
                +---------------+
                |   ModelMesh   |
                +---------------+
                  /     |      \
                 /      |       \
             Security  Cost   Reliability
               |        |         |
               v        v         v
             Auth    Budgets   Fallbacks
                     Usage     Retries
                              Caching
                                 |
                                 v
                           LLM Providers
```

This makes the gateway a useful foundation for applications that need centralized **provider management, access control, reliability mechanisms, and usage governance**.

---

## Design Principles

ModelMesh is structured around several engineering principles:

### Separation of concerns

API routes, authentication, provider logic, persistence, configuration, and gateway behavior are separated into focused modules.

### Provider abstraction

The gateway does not depend directly on a single model provider implementation.

### Stateless API layer

The application layer can be replicated horizontally, while PostgreSQL and Redis hold shared state.

### Async I/O

Database, Redis, and provider operations use asynchronous interfaces.

### Configuration-driven behavior

Providers, caching, budgets, rate limits, logging, and environment behavior can be changed through configuration rather than hard-coded application flow.

### Testability

Core gateway behavior is covered using isolated database and Redis test doubles.

---

## Current Scope

### Implemented

* OpenAI-compatible chat completion endpoint
* API key authentication
* SHA-256 API key storage
* Redis sliding-window rate limiting
* Redis response caching
* Provider abstraction
* Provider retry logic
* Provider fallback
* Usage and token tracking
* Estimated cost calculation
* Per-key budgets
* Request auditing
* Optional log redaction
* PostgreSQL persistence
* Alembic migrations
* Async SQLAlchemy
* Docker Compose environment
* Automated tests
* GitHub Actions CI
* Basic usage/provider dashboard

### Planned

The current roadmap includes:

* Real OpenAI provider integration
* Real Anthropic provider integration
* Per-project budget alerts
* Request log export
* S3-based export workflows
* TypeScript-based admin UI

See [ROADMAP.md](ROADMAP.md) for the current roadmap.

---

## Future Architecture

The project is designed to grow toward:

```text
                    Load Balancer
                         |
              +----------+----------+
              |                     |
              v                     v
        ModelMesh API 1       ModelMesh API 2
              |                     |
              +----------+----------+
                         |
             +-----------+-----------+
             |                       |
             v                       v
        PostgreSQL                 Redis
        Durable State          Cache / Limits
             |
             v
       Usage / Audit Data
```

Provider integrations can then be expanded behind the same common provider interface without changing the client-facing API.

---

## License

This software, source code, and associated documentation files (the "Software") 
are strictly private, confidential, and proprietary to [Tejprakash Mirashi].
---

## Author

**Tejprakash Mirashi**

GitHub: [Tejprakash25](https://github.com/Tejprakash25)

Repository: [github.com/Tejprakash25/ModelMesh](https://github.com/Tejprakash25/ModelMesh)
