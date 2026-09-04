"""Tokens SSO assinados para integração CIEM → Guacamole."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

_DEFAULT_SECRET = "change-me-in-production"
_SSO_TTL_SECONDS = int(os.environ.get("CIEM_SSO_TTL", "300"))


def _secret() -> bytes:
    return os.environ.get("CIEM_SECRET_KEY", _DEFAULT_SECRET).encode()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode())


def create_sso_token(
    username: str,
    *,
    target_id: str | None = None,
    ttl: int | None = None,
) -> str:
    """Gera token SSO assinado (HMAC-SHA256) com expiração.

    Formato (estilo JWT compacto): ``base64url(payload).base64url(signature)``.
    """
    expires = int(time.time()) + (ttl if ttl is not None else _SSO_TTL_SECONDS)
    payload: dict[str, Any] = {"user": username, "exp": expires}
    if target_id:
        payload["target"] = target_id
    data = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_secret(), data, hashlib.sha256).digest()
    return f"{_b64encode(data)}.{_b64encode(sig)}"


def verify_sso_token(token: str) -> dict[str, Any] | None:
    """Valida token SSO e retorna payload ou None."""
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        data = _b64decode(payload_b64)
        sig = _b64decode(sig_b64)
        expected = hmac.new(_secret(), data, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data.decode())
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except (ValueError, json.JSONDecodeError, KeyError):
        return None


def guacamole_client_id(connection_name: str) -> str:
    """Calcula identificador de conexão Guacamole (auth-file datasource)."""
    identifier = f"{connection_name}\0c\0default".encode()
    return base64.b64encode(identifier).decode()
