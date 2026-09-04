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
    1. Conectar ao ``server_url`` (ou host:port) configurado.
    2. Validar certificado CA em ``ca_cert_path`` se ``verify_ssl``.
    3. Executar bind com ``bind_dn``/``bind_password`` (se definidos).
    4. Buscar o usuário com ``user_filter`` (``%s`` = username) e ``uid_attribute``.
    5. Validar credenciais e mapear grupos via ``group_role_mapping``.

    Usuários locais (incluindo o ``admin`` padrão) continuam autenticando
    independentemente do LDAP — a autenticação local é sempre tentada primeiro.

    Atualmente retorna ``None`` quando LDAP está habilitado mas ainda não
    implementado (não levanta exceção no fluxo de login).
    """
    auth_cfg = config or load_auth_config()
    if not auth_cfg.ldap.enabled:
        return None

    # Stub: LDAP configurável no portal; bind real em versão futura.
    _ = (username, password, auth_cfg.ldap.resolved_server_url())
    return None


def authenticate(username: str, password: str, config: AuthConfig | None = None) -> User | None:
    """Tenta autenticação local primeiro; se falhar e LDAP estiver habilitado, tenta LDAP.

    Usuários locais sempre têm prioridade. O admin padrão em ``auth.yaml``
    funciona mesmo com LDAP ativo.
    """
    user = authenticate_local(username, password, config=config)
    if user is not None:
        return user

    auth_cfg = config or load_auth_config()
    if not auth_cfg.ldap.enabled:
        return None

    return authenticate_ldap(username, password, config=config)
