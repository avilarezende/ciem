"""Rate limiting do CIEM via slowapi (limites por endpoint)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limites por endpoint. Quando CIEM_RATE_LIMIT_ENABLED=0 (ex.: testes locais),
# o limiter fica desativado sem mudar o código.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=True,
    storage_uri="memory://",
) if __import__("os").getenv("CIEM_RATE_LIMIT_ENABLED", "1") != "0" else Limiter(
    key_func=get_remote_address,
    enabled=False,
    storage_uri="memory://",
)

# Limites padrão
LOGIN_LIMIT = "5/minute"       # força bruta em /auth/login
SESSION_LIMIT = "30/minute"    # início de sessão
CONFIG_WRITE_LIMIT = "20/minute"  # mudanças de configuração (admin)
GENERAL_LIMIT = "300/minute"   # demais endpoints autenticados