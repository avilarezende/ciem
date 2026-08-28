"""Orquestração da conversa."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import generate_reply
from app.memory import save_message, update_user_from_message, user_context_summary
from app.models import User
from app.persona import SYSTEM_PROMPT
from app.rag import query_context


async def handle_chat(
    session: AsyncSession,
    user: User,
    message: str,
) -> str:
    user = await update_user_from_message(session, user, message)
    await save_message(session, user, "user", message)

    rag_context = query_context("operacional", message, top_k=6)
    inst_context = query_context("institucional", message, top_k=3)
    maint_context = query_context("manutencoes", message, top_k=4)

    full_context = "\n\n".join(
        filter(
            None,
            [
                f"Dados do usuário:\n{await user_context_summary(user)}",
                f"Fontes operacionais:\n{rag_context}" if rag_context else "",
                f"Contexto institucional:\n{inst_context}" if inst_context else "",
                f"Manutenções:\n{maint_context}" if maint_context else "",
            ],
        )
    )

    reply = await generate_reply(SYSTEM_PROMPT, message, full_context)
    await save_message(session, user, "assistant", reply)
    return reply
