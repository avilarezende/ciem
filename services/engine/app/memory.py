"""Serviço de memória persistente do usuário."""

import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_loader import find_institution
from app.models import Message, User


def _extract_name(text: str) -> str | None:
    m = re.search(r"(?:sou|me chamo|meu nome é)\s+([A-Za-zÀ-ú][A-Za-zÀ-ú\s]{1,40})", text, re.I)
    return m.group(1).strip() if m else None


def _extract_institution(text: str) -> str | None:
    inst = find_institution(text)
    return inst["sigla"] if inst else None


async def get_or_create_user(
    session: AsyncSession,
    external_id: str,
    channel: str = "web",
) -> User:
    result = await session.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(external_id=external_id, channel=channel)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_from_message(session: AsyncSession, user: User, text: str) -> User:
    nome = _extract_name(text)
    if nome and not user.nome:
        user.nome = nome
    sigla = _extract_institution(text)
    if sigla and not user.instituicao_sigla:
        user.instituicao_sigla = sigla
    await session.commit()
    await session.refresh(user)
    return user


async def save_message(session: AsyncSession, user: User, role: str, content: str) -> None:
    session.add(Message(user_id=user.id, role=role, content=content))
    await session.commit()


async def user_context_summary(user: User) -> str:
    parts = []
    if user.nome:
        parts.append(f"Nome: {user.nome}")
    if user.instituicao_sigla:
        parts.append(f"Instituição vinculada: {user.instituicao_sigla}")
    if user.email:
        parts.append(f"E-mail: {user.email}")
    if user.telefone:
        parts.append(f"Telefone: {user.telefone}")
    if user.preferencias_json:
        parts.append(f"Preferências: {user.preferencias_json}")
    return "\n".join(parts) if parts else "Usuário ainda não identificado plenamente."


async def set_user_profile(
    session: AsyncSession,
    user: User,
    *,
    nome: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    instituicao_sigla: str | None = None,
    preferencias: dict | None = None,
) -> User:
    if nome:
        user.nome = nome
    if email:
        user.email = email
    if telefone:
        user.telefone = telefone
    if instituicao_sigla:
        user.instituicao_sigla = instituicao_sigla
    if preferencias is not None:
        user.preferencias_json = json.dumps(preferencias, ensure_ascii=False)
    await session.commit()
    await session.refresh(user)
    return user
