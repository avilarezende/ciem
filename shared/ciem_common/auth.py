"""Autenticação local e integração LDAP (stub) para a plataforma CIEM."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ciem_common.config_loader import load_auth_config
from ciem_common.interfaces import UserRole

if TYPE_CHECKING:
    from ciem_common.config_loader import AuthConfig


class User(BaseModel):
    """Usuário autenticado na plataforma ZTNA.

    Attributes:
        username: Identificador de login.
        role: Papel de acesso (:class:`UserRole`).
        auth_source: Origem da autenticação (``local`` ou ``ldap``).
        display_name: Nome amigável opcional para exibição no painel.
    """

    username: str
    role: UserRole
    auth_source: str = Field(default="local", description="Fonte: local ou ldap")
    display_name: str | None = Field(default=None, description="Nome de exibição")


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Gera hash PBKDF2-SHA256 para armazenamento seguro em ``auth.yaml``.

    Formato retornado: ``<salt_hex>$<digest_hex>``

    Use esta função ao provisionar usuários locais no arquivo de configuração.
    """
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 260_000)
    return f"{salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Compara senha em texto plano com hash armazenado em configuração."""
    try:
        salt_hex, expected_hex = password_hash.split("$", maxsplit=1)
    except ValueError:
        return False
    computed = hash_password(password, salt=salt_hex)
    return hmac.compare_digest(computed, f"{salt_hex}${expected_hex}")


def _resolve_role(raw_role: str) -> UserRole:
    """Normaliza string de configuração para :class:`UserRole`."""
    normalized = raw_role.strip().lower()
    if normalized == UserRole.ADMIN.value:
        return UserRole.ADMIN
    return UserRole.OBSERVER


def authenticate_local(
    username: str,
    password: str,
    config: AuthConfig | None = None,
) -> User | None:
    """Autentica usuário contra a lista ``local_users`` de ``config/auth.yaml``.

    Args:
        username: Login informado pelo operador.
        password: Senha em texto plano (nunca persistida em log).
        config: Configuração opcional; padrão carrega via :func:`load_auth_config`.

    Returns:
        Instância de :class:`User` se credenciais válidas; ``None`` caso contrário.
    """
    auth_cfg = config or load_auth_config()
    for entry in auth_cfg.local_users:
        if not entry.enabled:
            continue
        if entry.username != username:
            continue
        if not verify_password(password, entry.password_hash):
            return None
        return User(
            username=entry.username,
            role=_resolve_role(entry.role),
            auth_source="local",
            display_name=entry.username,
        )
    return None


def authenticate_ldap(
    username: str,
    password: str,
    config: AuthConfig | None = None,
) -> User | None:
    """Stub de autenticação LDAP — integração real será implementada em versão futura.

    Quando ``ldap.enabled`` for ``true`` na configuração, este método deverá:
    1. Conectar ao ``server_uri`` configurado.
    2. Executar bind com ``bind_dn``/``bind_password`` (se definidos).
    3. Buscar o usuário com ``user_search_filter`` substituindo ``{username}``.
    4. Validar credenciais e mapear grupos via ``group_role_mapping``.

    Atualmente retorna ``None`` e registra que LDAP não está implementado.
    """
    auth_cfg = config or load_auth_config()
    if not auth_cfg.ldap.enabled:
        return None

    # Stub: LDAP ainda não implementado — evita falha silenciosa em produção.
    raise NotImplementedError(
        "Autenticação LDAP ainda não implementada. "
        f"Servidor configurado: {auth_cfg.ldap.server_uri}. "
        "Use autenticação local ou desabilite ldap.enabled em auth.yaml."
    )


def authenticate(username: str, password: str, config: AuthConfig | None = None) -> User | None:
    """Tenta autenticação local e, se habilitado, LDAP (quando disponível)."""
    user = authenticate_local(username, password, config=config)
    if user is not None:
        return user

    auth_cfg = config or load_auth_config()
    if not auth_cfg.ldap.enabled:
        return None

    try:
        return authenticate_ldap(username, password, config=config)
    except NotImplementedError:
        return None
