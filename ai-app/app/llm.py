import re
from pathlib import Path
from typing import TypedDict, AsyncGenerator
import datetime

from langchain_openrouter import ChatOpenRouter
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .config import settings
from .models import Conversation, Message


llm = ChatOpenRouter(model=settings.openrouter_model)
_safeguard_llm = ChatOpenRouter(model="openai/gpt-oss-safeguard-20b")
_tracer = trace.get_tracer(__name__)

_BEWERBUNGEN_PATH = Path("/app/bewerbungen")
_SAFE_ID = re.compile(r"^[a-z0-9-]+$")

_OFF_TOPIC_QUESTION = (
    "The visitor has asked a question that falls outside the scope of the application documents. "
    "Respond politely and shortly, saying that as an avatar this is beyond your limits of knowlegde."
    "Invite the visitor to contact the applicant directly — refer to the phone number and email address listed in the "
    "Lebenslauf — to schedule an appointment for further discussion."
)

_MAX_EVENT_CONTENT = 8192


def _record_messages(span: trace.Span, messages: list[BaseMessage]) -> None:
    """Add each message as a span event so the full prompt stack is visible in traces."""
    for msg in messages:
        span.add_event(
            f"gen_ai.{msg.type}.message",
            {"content": str(msg.content)[:_MAX_EVENT_CONTENT]},
        )


def _read_bewerbung_docs(bewerbung_id: str) -> tuple[str, str, str]:
    """Return (lebenslauf, anschreiben, ausschreibung) texts for a bewerbung_id."""
    if not _SAFE_ID.match(bewerbung_id):
        raise ValueError(f"Invalid bewerbung_id: {bewerbung_id!r}")
    base = _BEWERBUNGEN_PATH / bewerbung_id
    def read(name: str) -> str:
        p = base / name
        return p.read_text() if p.exists() else ""
    return read("Lebenslauf.md"), read("Anschreiben.md"), read("Ausschreibung.md")


def _build_safeguard_policy(lebenslauf: str, anschreiben: str, ausschreibung: str) -> str:
    docs: list[str] = []
    if lebenslauf:
        docs.append(f"### Lebenslauf (CV)\n{lebenslauf.strip()}")
    if anschreiben:
        docs.append(f"### Anschreiben (Cover Letter)\n{anschreiben.strip()}")
    if ausschreibung:
        docs.append(f"### Ausschreibung (Job Posting)\n{ausschreibung.strip()}")
    doc_block = "\n\n".join(docs) if docs else "(no documents provided)"
    return f"""\
You are a topic-scope guardrail for an AI job-application assistant.

INSTRUCTIONS:
Decide whether the user message can be at least partially answered using the application \
documents below. Output only "0" or "1". Reasoning: low.

DEFINITIONS:
"Covered" means the documents contain information relevant to the question (personal background, \
qualifications, work experience, skills, the advertised position, cover-letter contents, contact \
details, etc.).
"Not covered" means the question concerns topics entirely unrelated to the applicant or the job posting.

VIOLATES (1 — not covered):
- General knowledge questions with no connection to the applicant or position.
- Requests to generate unrelated content (code, recipes, translations of unrelated text, etc.).
- Questions about topics not mentioned anywhere in the documents.

SAFE (0 — covered):
- Questions about the applicant's qualifications, work history, skills, education, or interests.
- Questions about the advertised position or the hiring organisation as described in the job posting.
- Requests for contact details or scheduling an appointment.
- Greetings and small talk manageable in the context of a job-application chat.

EXAMPLES:
User: "What experience do you have in team leadership?" → 0
User: "What is the capital of France?" → 1
User: "Can you tell me more about your approach to language development?" → 0
User: "Write me a Python script to sort a list." → 1
User: "What is your availability for an interview?" → 0
User: "Hi, I am from the hiring team." → 0

Output only: 0 or 1.

---
APPLICATION DOCUMENTS:

{doc_block}
"""


def build_system_message(bewerbung_id: str) -> SystemMessage:
    lebenslauf, anschreiben, ausschreibung = _read_bewerbung_docs(bewerbung_id)
    formatted_today = datetime.date.today().strftime("%Y-%m-%d")
    parts = [f"Today is {formatted_today}. You are a helpful assistant representing the person described below."]
    if lebenslauf:
        parts.append(f"## Lebenslauf\n{lebenslauf.strip()}")
    if anschreiben:
        parts.append(f"## Anschreiben\n{anschreiben.strip()}")
    if ausschreibung:
        parts.append(f"## Ausschreibung\n{ausschreibung.strip()}")
    return SystemMessage(content="\n\n".join(parts))


# ---------------------------------------------------------------------------
# LangGraph state types
# ---------------------------------------------------------------------------

class ChatInput(TypedDict):
    question: str
    history: list[BaseMessage]  # pre-loaded from DB by the router, includes system message
    bewerbung_id: str


class ChatState(TypedDict):
    question: str
    history: list[BaseMessage]
    answer: str
    bewerbung_id: str


class ChatOutput(TypedDict):
    answer: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def safeguard_node(state: ChatState) -> dict:
    """
    Call gpt-oss-safeguard-20b to decide whether the user's question is within
    the scope of the application documents. Out-of-scope questions are replaced
    with a prompt that asks the main model to suggest contacting the applicant.
    Fails open: if the safeguard call errors, the original question is kept.
    """
    is_off_topic = False
    try:
        lebenslauf, anschreiben, ausschreibung = _read_bewerbung_docs(state["bewerbung_id"])
        policy = _build_safeguard_policy(lebenslauf, anschreiben, ausschreibung)
        messages = [SystemMessage(content=policy), HumanMessage(content=state["question"])]
        with _tracer.start_as_current_span("gen_ai.safeguard") as span:
            span.set_attribute("gen_ai.request.model", "openai/gpt-oss-safeguard-20b")
            _record_messages(span, messages)
            response = await _safeguard_llm.ainvoke(messages)
            result = str(response.content).strip()
            span.add_event("gen_ai.choice", {"content": result})
            is_off_topic = result.startswith("1")
    except Exception:
        is_off_topic = False
    return {"question": _OFF_TOPIC_QUESTION if is_off_topic else state["question"]}


def prepare_context_node(state: ChatInput) -> dict:
    return {"history": state["history"] + [HumanMessage(content=state["question"])]}


async def generate_node(state: ChatState) -> dict:
    """Call the LLM with the full context and return its answer."""
    with _tracer.start_as_current_span("gen_ai.generate") as span:
        span.set_attribute("gen_ai.request.model", settings.openrouter_model)
        _record_messages(span, state["history"])
        response = await llm.ainvoke(state["history"])
        span.add_event("gen_ai.choice", {"content": str(response.content)[:_MAX_EVENT_CONTENT]})
    return {"answer": response.content}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = (
    StateGraph(ChatState, input_schema=ChatInput, output_schema=ChatOutput)
    .add_node("safeguard", safeguard_node)
    .add_node("prepare_context", prepare_context_node)
    .add_node("generate", generate_node)
    .add_edge(START, "safeguard")
    .add_edge("safeguard", "prepare_context")
    .add_edge("prepare_context", "generate")
    .add_edge("generate", END)
    .compile()
)


# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------

async def stream_graph(question: str, history: list[BaseMessage], bewerbung_id: str) -> AsyncGenerator[str, None]:
    """
    Yield text tokens as the LLM produces them.

    Emits a single emoji once the safeguard node completes (🦜 = on-topic, 🙊 = off-topic),
    then streams generate-node tokens via on_chat_model_stream events.
    """
    async for event in graph.astream_events(
        {"question": question, "history": history, "bewerbung_id": bewerbung_id},
        version="v2",
    ):
        node = event.get("metadata", {}).get("langgraph_node", "")
        if event["event"] == "on_chat_model_end" and node == "safeguard":
            output = event["data"].get("output")
            content = str(output.content).strip() if output else ""
            yield "🙊 " if content.startswith("1") else "🦜 "
        elif event["event"] == "on_chat_model_stream" and node == "generate":
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

    summarize_messages = [
        SystemMessage(content=(
            "Produce a concise summary of the conversation below, preserving all key facts, "
            "decisions, and context needed for future responses. Write in third person."
        )),
        HumanMessage(content=f"{existing}Messages to summarize:\n{history_text}"),
    ]
    with _tracer.start_as_current_span("gen_ai.summarize") as span:
        span.set_attribute("gen_ai.request.model", settings.openrouter_model)
        _record_messages(span, summarize_messages)
        result = await llm.ainvoke(summarize_messages)
        span.add_event("gen_ai.choice", {"content": str(result.content)[:_MAX_EVENT_CONTENT]})
    conversation.summary = result.content

    for msg in to_summarize:
        msg.is_summarized = True

    await db.commit()
