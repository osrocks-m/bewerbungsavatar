import json
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_session
from ..models import Conversation, Message
from ..schemas import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
from ..llm import load_context, stream_graph, maybe_summarize

router = APIRouter(tags=["conversations"])

_BEWERBUNGEN_PATH = Path("/app/bewerbungen")


@router.get("/api/bewerbungen", response_model=list[str])
def list_bewerbungen():
    if not _BEWERBUNGEN_PATH.exists():
        return []
    return sorted(d.name for d in _BEWERBUNGEN_PATH.iterdir() if d.is_dir())


@router.post("/api/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_session),
):
    conversation = Conversation(bewerbung_id=body.bewerbung_id, client_id=body.client_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/api/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    bewerbung_id: str,
    x_client_id: str = Header(...),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.bewerbung_id == bewerbung_id,
            Conversation.client_id == x_client_id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.delete("/api/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_session)
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    await db.commit()


@router.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_session),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(conversation_id=conversation_id, role="user", content=body.content)
    db.add(user_msg)
    await db.commit()

    if not conversation.title:
        conversation.title = body.content[:80]
        await db.commit()

    async def generate() -> AsyncGenerator[str, None]:
        history = await load_context(conversation, db)
        full_response = ""

        try:
            async for token in stream_graph(body.content, history, conversation.bewerbung_id):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            await db.commit()

            await maybe_summarize(conversation, db)

            yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_msg.id)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
