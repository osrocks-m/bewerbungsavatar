import uuid
from datetime import datetime
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    bewerbung_id: str
    client_id: str


class ConversationResponse(BaseModel):
    id: uuid.UUID
    bewerbung_id: str
    client_id: str
    title: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    is_summarized: bool
    created_at: datetime

    model_config = {"from_attributes": True}
