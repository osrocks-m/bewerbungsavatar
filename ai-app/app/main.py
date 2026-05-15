from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine
from .routers import conversations
from .telemetry import configure_telemetry, reattach_log_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic (entrypoint.sh runs "alembic upgrade head" before this starts).
    # Re-attach after uvicorn's logging.config.dictConfig() clears root logger handlers.
    reattach_log_handler()
    yield


app = FastAPI(title="LLM Chat API", version="0.1.0", lifespan=lifespan)

configure_telemetry(app, engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
