from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    # Omit, or send null/empty, to have the server generate a new session_id
    # and return it - useful for a first message when the caller doesn't have
    # one yet. Pass it back on every following request to continue that
    # conversation.
    session_id: Optional[str] = Field(default=None, max_length=128)
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class ResetRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)


class ConfigResponse(BaseModel):
    app_name: str
    provider: str
    model: str
    rag_enabled: bool
    streaming: bool


class HealthResponse(BaseModel):
    status: str
