"""Proteções contra SSRF em URLs de saída (OWASP A10)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """URL bloqueada por política anti-SSRF."""


_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google",
    }
)


def validate_outbound_url(url: str, *, allow_http: bool = False) -> str:
    """Valida URL usada pelo core para chamadas de saída (IA, webhooks, etc.).

    Bloqueia esquemas não-HTTP(S), hosts locais/metadata e IPs privados/loopback
    (após resolução DNS), reduzindo risco de SSRF.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL vazia ou inválida.")

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("https",) and not (allow_http and scheme == "http"):
        raise UnsafeURLError("Apenas HTTPS é permitido para URLs de saída.")
    if not parsed.hostname:
        raise UnsafeURLError("URL sem hostname.")

    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        raise UnsafeURLError(f"Host bloqueado por política SSRF: {host}")

    allow_private = __import__("os").environ.get("CIEM_SSRF_ALLOW_PRIVATE", "0") == "1"

    def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if str(ip) in {"169.254.169.254", "169.254.170.2"}:
            return True
        if allow_private:
            return bool(ip.is_loopback or ip.is_unspecified)
        return bool(
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )

    # Bloqueia literais IP privados/loopback/link-local/metadata.
    try:
        ip = ipaddress.ip_address(host)
        if _blocked_ip(ip):
            raise UnsafeURLError(f"Endereço IP não permitido: {host}")
        return url.strip()
    except ValueError:
        pass  # hostname não é IP literal

    # Resolve DNS e verifica cada endereço.
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Falha ao resolver host: {host}") from exc

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _blocked_ip(ip):
            raise UnsafeURLError(f"Host resolve para rede não permitida ({addr}).")

    return url.strip()
