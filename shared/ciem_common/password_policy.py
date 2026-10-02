"""Política de senhas locais (OWASP ASVS 2.1 / A07)."""

from __future__ import annotations

import os
import re

# Comprimento mínimo configurável (padrão 10 — ASVS sugere ≥12 em produção).
_MIN_LEN = int(os.environ.get("CIEM_PASSWORD_MIN_LENGTH", "10"))
_MAX_LEN = int(os.environ.get("CIEM_PASSWORD_MAX_LENGTH", "128"))

_COMMON = frozenset(
    {
        "password",
        "password1",
        "password123",
        "admin123",
        "observer123",
        "12345678",
        "1234567890",
        "qwerty123",
        "letmein",
        "welcome1",
        "changeme",
        "ciem1234",
        "adminadmin",
    }
)


class PasswordPolicyError(ValueError):
    """Senha rejeitada pela política."""


def validate_password(password: str, *, username: str | None = None) -> None:
    """Valida senha local; levanta :class:`PasswordPolicyError` se inválida."""
    if not isinstance(password, str):
        raise PasswordPolicyError("Senha inválida.")
    if len(password) < _MIN_LEN:
        raise PasswordPolicyError(f"A senha deve ter pelo menos {_MIN_LEN} caracteres.")
    if len(password) > _MAX_LEN:
        raise PasswordPolicyError(f"A senha deve ter no máximo {_MAX_LEN} caracteres.")
    if password.lower() in _COMMON:
        raise PasswordPolicyError("Senha demasiado comum — escolha outra.")
    if username and password.lower() == username.lower():
        raise PasswordPolicyError("A senha não pode ser igual ao nome de usuário.")
    # Exige pelo menos uma letra e um dígito (ASVS 2.1.4 simplificado).
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise PasswordPolicyError("A senha deve conter letras e números.")
