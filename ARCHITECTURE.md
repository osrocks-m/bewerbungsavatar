# LLM Chat — Architecture

Portfolio project demonstrating microservice architecture, LLM integration, and full-stack observability.

---

## Goal

A persistent, never-ending chat application backed by a real LLM. Conversations are stored in a database and continuously summarized so that context is never lost, even as chats grow indefinitely. Each concern lives in its own Docker container; the setup is designed to be migrated to Kubernetes later.

---

## Services

| Service | Technology | Port |
|---|---|---|
| `frontend` | Next.js (React) — bootstrapped from official example | 3000 |
| `ai-app` | FastAPI + LangChain (Python) | 8000 |
| `postgres` | PostgreSQL 16 | 5432 |
| `otel-collector` | OpenTelemetry Collector (contrib) | 4317 / 4318 |
| `loki` | Grafana Loki | 3100 |
| `tempo` | Grafana Tempo | 3200 |

**External (existing on `neptun.tale-manta.ts.net`):**
- Grafana: port 3002 — add Loki and Tempo datasources pointing at the Docker host's Tailscale IP
- Prometheus: port 9090 — receives metrics via remote_write from the OTel Collector

---

## LLM

Provider: **Groq** (OpenAI-compatible API).  
LangChain's `ChatOpenAI` is used with `base_url="https://api.groq.com/openai/v1"` — no Groq-specific SDK needed.

Configured via environment variables:
```
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile   # default
```

---

## Persistent Conversation Memory

The core AI feature. Each conversation in the database has:
- A **messages** table with every exchange, each flagged `is_summarized`
- A **summary** column on the conversation, holding a rolling LLM-generated summary

**How it works:**

1. On each user message, the LLM receives:  
   `[SystemMessage(summary)] + all unsummarized messages`
2. The response is streamed token-by-token via SSE and saved to the database.
3. After saving, `maybe_summarize()` checks the count of unsummarized messages.
4. When that count exceeds `SUMMARY_THRESHOLD` (default: 20), the oldest messages (all but the most recent `KEEP_RECENT`, default: 10) are passed to the LLM for summarization. The result is written to `conversation.summary` and the messages are flagged `is_summarized = true`.

This keeps the active context window bounded while the full exchange history is never deleted.

---

## API (ai-app)

All endpoints are prefixed `/api/conversations`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/` | Create a new conversation |
| `GET` | `/` | List all conversations (newest first) |
| `GET` | `/{id}/messages` | Fetch all messages for a conversation |
| `DELETE` | `/{id}` | Delete a conversation and all its messages |
| `POST` | `/{id}/messages` | Send a user message — returns SSE stream |

### SSE event format

```
data: {"type": "token",  "content": "Hello"}
data: {"type": "token",  "content": " world"}
data: {"type": "done",   "message_id": "<uuid>"}
data: {"type": "error",  "message": "..."}
```

---

## Database Schema

```
conversations
  id           UUID  PK
  title        TEXT  (auto-set from first message)
  summary      TEXT  (rolling LLM summary, nullable)
  created_at   TIMESTAMPTZ
  updated_at   TIMESTAMPTZ

messages
  id               UUID  PK
  conversation_id  UUID  FK → conversations
  role             TEXT  ("user" | "assistant")
  content          TEXT
  is_summarized    BOOL
  created_at       TIMESTAMPTZ
```

Tables are created automatically on `ai-app` startup (SQLAlchemy `create_all`). Add Alembic for schema migrations when the model stabilises.

---

## Observability

All services instrument via the **OpenTelemetry SDK** and push to `otel-collector:4317`.

The collector fans out:

```
metrics  →  Prometheus on neptun (remote_write)
logs     →  Loki container (port 3100)
traces   →  Tempo container (port 3200, via internal OTLP gRPC)
```

Add Loki (`http://<tailscale-host-ip>:3100`) and Tempo (`http://<tailscale-host-ip>:3200`) as datasources in the Grafana instance on neptun.

---

## Getting Started

```bash
# 1. Copy env file and fill in your Groq API key
cp .env.example .env

# 2. Start everything
docker compose up --build

# 3. Open the app
open http://localhost:3000

# 4. API docs (FastAPI auto-generated)
open http://localhost:8000/docs
```

---

## Repository Layout

```
.
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md
├── ai-app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app, CORS, lifespan
│       ├── config.py        # Settings via pydantic-settings
│       ├── database.py      # SQLAlchemy async engine + session factory
│       ├── models.py        # ORM models (Conversation, Message)
│       ├── schemas.py       # Pydantic request/response schemas
│       ├── llm.py           # LangChain + Groq, build_context, stream_response, maybe_summarize
│       └── routers/
│           └── conversations.py
├── frontend/                # Next.js — bootstrapped separately from official example
│   └── Dockerfile
├── grafana/
│   └── docker-compose.yml   # Grafana + Prometheus on neptun (pre-existing)
└── observability/
    ├── otel-collector-config.yaml
    ├── loki-config.yaml
    └── tempo-config.yaml
```

---

## Next Steps

- [ ] Bootstrap frontend from Next.js official chat example and wire it to the API
- [ ] Add OpenTelemetry instrumentation to `ai-app` (fastapi + sqlalchemy instrumentors are already in requirements.txt)
- [ ] Add Grafana dashboards for request latency, LLM token counts, error rates
- [ ] Add authentication (e.g. NextAuth.js on the frontend, API key / JWT on the backend)
- [ ] Write Kubernetes manifests (Deployments, Services, ConfigMaps, Secrets) to replace docker-compose
