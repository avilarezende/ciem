"""Rotas SSO — integração portal CIEM com Guacamole."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.deps import require_admin, require_user
from ciem_common.auth import User
from ciem_common.sso import create_sso_token, guacamole_client_id, verify_sso_token
from ciem_common.targets_loader import load_targets_config

router = APIRouter(prefix="/sso", tags=["sso"])

SSO_COOKIE = "ciem_sso"


class GuacamoleSsoRequest(BaseModel):
    target_id: str | None = Field(default=None, description="ID do alvo em targets.yaml")


class GuacamoleSsoResponse(BaseModel):
    token: str
    login_url: str
    guacamole_url: str
    expires_in: int = 300
    target_name: str | None = None


def _target_by_id(target_id: str):
    cfg = load_targets_config()
    for target in cfg.targets:
        if target.id == target_id:
            return target
    return None


@router.post("/guacamole", response_model=GuacamoleSsoResponse)
async def create_guacamole_sso(
    body: GuacamoleSsoRequest | None = None,
    user: User = Depends(require_admin),
) -> GuacamoleSsoResponse:
    """Gera token SSO para acesso ao Guacamole sem novo login."""
    target_id = body.target_id if body else None
    target_name = None

    if target_id:
        target = _target_by_id(target_id)
        if not target or not target.enabled:
            raise HTTPException(status_code=404, detail=f"Alvo '{target_id}' não encontrado")
        target_name = target.name

    token = create_sso_token(user.username, target_id=target_id)
    login_url = f"/api/sso/guacamole/login?token={token}"
    if target_name:
        client_id = guacamole_client_id(target_name)
        guac_url = f"/guacamole/#/client/{client_id}"
    else:
        guac_url = "/guacamole/"

    return GuacamoleSsoResponse(
        token=token,
        login_url=login_url,
        guacamole_url=guac_url,
        target_name=target_name,
    )


@router.get("/guacamole/login")
async def guacamole_sso_login(
    token: str = Query(..., description="Token SSO"),
    response: Response = None,
) -> RedirectResponse:
    """Valida token SSO, define cookie e redireciona ao Guacamole."""
    payload = verify_sso_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token SSO inválido")

    target_id = payload.get("target")

    redirect_url = "/guacamole/"
    if target_id:
        target = _target_by_id(target_id)
        if target:
            client_id = guacamole_client_id(target.name)
            redirect_url = f"/guacamole/#/client/{client_id}"

    redirect = RedirectResponse(url=redirect_url, status_code=302)
    redirect.set_cookie(
        key=SSO_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=300,
        path="/",
    )
    return redirect


@router.get("/validate")
async def sso_validate(
    request: Request,
    token: str | None = Query(default=None),
    x_sso_token: str | None = Header(default=None),
) -> Response:
    """Validação interna para nginx auth_request (Guacamole)."""
    sso_token = token or x_sso_token or request.cookies.get(SSO_COOKIE)
    if not sso_token:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = verify_sso_token(sso_token)
    if not payload:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    response = Response(status_code=status.HTTP_200_OK)
    response.headers["X-CIEM-User"] = payload["user"]
    return response


@router.get("/status")
async def sso_status(user: User = Depends(require_user)) -> dict[str, Any]:
    """Verifica se o usuário autenticado pode usar SSO Guacamole."""
    return {
        "sso_available": user.role.value == "admin",
        "username": user.username,
    }
