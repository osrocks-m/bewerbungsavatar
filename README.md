# LLM Chat

A persistent chat application backed by OpenRouter's LLM API, built as a portfolio project to demonstrate microservice architecture, LangChain integration, and full-stack observability.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design rationale.

---

## Prerequisites

- Docker + Docker Compose
- An [OpenRouter API key](https://openrouter.ai/workspaces/default/keys)

---

## Getting started

```bash
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY

docker compose up --build # On dev systems
docker compose -f docker-compose.yml up # on prod systems
```

- Frontend: http://localhost:3000
- AI App + API docs: http://localhost:8000/redoc http://localhost:8000/docs
- PostgreSQL: localhost:5432 (user/db: `chat`, password from `.env`)

---

## Database migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org). Migrations run automatically on container start via `entrypoint.sh` (`alembic upgrade head`).

### Workflow when you change a model

```bash
# 1. Edit ai-app/app/models.py

# 2. Generate a migration (run from the ai-app/ directory)
docker compose exec ai-app alembic revision --autogenerate -m "short description"

# 3. Review the generated file in alembic/versions/ — autogenerate is good but not perfect.
#    Check that upgrade() and downgrade() look correct before committing.

# 4. Apply it
docker compose exec ai-app alembic upgrade head
```

### Other useful commands

```bash
# Show current migration state
docker compose exec ai-app alembic current

# Show full migration history
docker compose exec ai-app alembic history

# Roll back one step
docker compose exec ai-app alembic downgrade -1
```

### How the async bridge works

Alembic is synchronous; the app uses an async SQLAlchemy engine (`asyncpg`). `alembic/env.py` bridges this with `async_engine_from_config` + `connection.run_sync()` — the engine is async, but Alembic is handed a synchronous proxy to run its migrations through.

---

## Observability

Loki and Tempo run as local containers. Grafana and Prometheus live on `neptun.tale-manta.ts.net`.

Add these datasources in Grafana once the stack is running:

| Datasource | URL |
|---|---|
| Loki | `http://<this-host-tailscale-ip>:3100` |
| Tempo | `http://<this-host-tailscale-ip>:3200` |

Services send telemetry to the OTel Collector at `localhost:4317` (OTLP gRPC). The collector fans it out to Prometheus (remote_write), Loki, and Tempo.

---

## Project layout

```
.
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md          # design decisions and data flow
├── ai-app/                  # FastAPI + LangChain — the AI backend
│   ├── alembic/             # database migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py        # settings via environment variables
│   │   ├── database.py      # SQLAlchemy async engine
│   │   ├── models.py        # ORM models (Conversation, Message)
│   │   ├── schemas.py       # Pydantic request/response types
│   │   ├── llm.py           # OpenRouter via LangChain, summarization logic
│   │   └── routers/
│   │       └── conversations.py
│   └── entrypoint.sh        # runs migrations then starts uvicorn
├── frontend/                # Next.js — bootstrapped from official example
├── grafana/                 # pre-existing Grafana/Prometheus stack on neptun
└── observability/           # OTel Collector, Loki, and Tempo configs
```
