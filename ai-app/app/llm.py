import re
from pathlib import Path
from typing import TypedDict, AsyncGenerator

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .config import settings
from .models import Conversation, Message


llm = ChatGroq(model=settings.groq_model)

_BEWERBUNGEN_PATH = Path("/app/bewerbungen")
_SAFE_ID = re.compile(r"^[a-z0-9-]+$")


def build_system_message(bewerbung_id: str) -> SystemMessage:
    if not _SAFE_ID.match(bewerbung_id):
        raise ValueError(f"Invalid bewerbung_id: {bewerbung_id!r}")
    base = _BEWERBUNGEN_PATH / bewerbung_id
    lebenslauf_path = base / "Lebenslauf.md"
    anschreiben_path = base / "Anschreiben.md"
    lebenslauf = lebenslauf_path.read_text() if lebenslauf_path.exists() else ""
    anschreiben = anschreiben_path.read_text() if anschreiben_path.exists() else ""
    parts = ["You are a helpful assistant representing the person described below."]
    if lebenslauf:
        parts.append(f"## Lebenslauf\n{lebenslauf.strip()}")
    if anschreiben:
        parts.append(f"## Anschreiben\n{anschreiben.strip()}")
    return SystemMessage(content="\n\n".join(parts))


# ---------------------------------------------------------------------------
# LangGraph state types
# ---------------------------------------------------------------------------

class ChatInput(TypedDict):
    question: str
    history: list[BaseMessage]  # pre-loaded from DB by the router, includes system message


class ChatState(TypedDict):
    question: str
    history: list[BaseMessage]
    answer: str


class ChatOutput(TypedDict):
    answer: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def prepare_context_node(state: ChatInput) -> dict:
    return {"history": state["history"] + [HumanMessage(content=state["question"])]}


async def generate_node(state: ChatState) -> dict:
    """Call the LLM with the full context and return its answer."""
    response = await llm.ainvoke(state["history"])
    return {"answer": response.content}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = (
    StateGraph(ChatState, input_schema=ChatInput, output_schema=ChatOutput)
    .add_node("prepare_context", prepare_context_node)
    .add_node("generate", generate_node)
    .add_edge(START, "prepare_context")
    .add_edge("prepare_context", "generate")
    .add_edge("generate", END)
    .compile()
)


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------

async def stream_graph(question: str, history: list[BaseMessage]) -> AsyncGenerator[str, None]:
    """
    Yield text tokens as the LLM produces them.

    LangGraph's astream_events() fires an 'on_chat_model_stream' event for
    every token chunk. We filter to just those and forward the content string.
    """
    async for event in graph.astream_events(
        {"question": question, "history": history},
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                yield chunk.content


# ---------------------------------------------------------------------------
# DB helpers — called by the router, not the graph.
# Keeping DB logic outside the graph makes nodes testable without a database.
# ---------------------------------------------------------------------------

async def load_context(conversation: Conversation, db: AsyncSession) -> list[BaseMessage]:
    """
    Build the full message list for the graph:
      [system_msg, optional_summary_msg, ...unsummarized_messages]

    The system message is loaded from disk based on conversation.bewerbung_id.
    """
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.is_summarized == False,  # noqa: E712
        )
        .order_by(Message.created_at)
    )
    recent = result.scalars().all()

    messages: list[BaseMessage] = [build_system_message(conversation.bewerbung_id)]
    if conversation.summary:
        messages.append(
            SystemMessage(content=f"Summary of earlier conversation:\n{conversation.summary}")
        )
    for msg in recent:
        messages.append(
            HumanMessage(content=msg.content) if msg.role == "user" else AIMessage(content=msg.content)
        )
    return messages


async def maybe_summarize(conversation: Conversation, db: AsyncSession) -> None:
    """
    When unsummarized messages exceed settings.summary_threshold, fold the
    oldest ones into conversation.summary and mark them as summarized.

    This keeps the active context window bounded while the full history stays
    in the database.
    """
    count_result = await db.execute(
        select(func.count()).where(
            Message.conversation_id == conversation.id,
            Message.is_summarized == False,  # noqa: E712
        )
    )
    count = count_result.scalar() or 0

    if count <= settings.summary_threshold:
        return

    to_summarize_result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.is_summarized == False,  # noqa: E712
        )
        .order_by(Message.created_at)
        .limit(count - settings.keep_recent)
    )
    to_summarize = to_summarize_result.scalars().all()

    if not to_summarize:
        return

    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in to_summarize)
    existing = f"Existing summary:\n{conversation.summary}\n\n" if conversation.summary else ""

    result = await llm.ainvoke([
        SystemMessage(content=(
            "Produce a concise summary of the conversation below, preserving all key facts, "
            "decisions, and context needed for future responses. Write in third person."
        )),
        HumanMessage(content=f"{existing}Messages to summarize:\n{history_text}"),
    ])
    conversation.summary = result.content

    for msg in to_summarize:
        msg.is_summarized = True

    await db.commit()
