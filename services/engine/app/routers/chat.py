"""API HTTP do motor de conversação."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_service import handle_chat
from app.database import get_session
from app.memory import get_or_create_user
from app.rag import ingest_documents

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    user_id: str = Field(..., description="Identificador estável do usuário no canal")
    channel: str = Field(default="web", description="web | telegram | discord | whatsapp")


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    channel: str


class IngestRequest(BaseModel):
    collection: str = "operacional"
    documents: list[dict]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    user = await get_or_create_user(session, body.user_id, body.channel)
    reply = await handle_chat(session, user, body.message)
    return ChatResponse(reply=reply, user_id=body.user_id, channel=body.channel)


@router.post("/rag/ingest")
async def rag_ingest(body: IngestRequest) -> dict:
    count = ingest_documents(body.collection, body.documents)
    return {"ingested": count, "collection": body.collection}
