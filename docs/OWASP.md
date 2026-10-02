# OWASP — alinhamento do CIEM

Mapeamento das práticas aplicadas ao portal/API CIEM face ao **OWASP Top 10 (2021)** e controles relevantes do **ASVS**.

| OWASP | Risco | Controles no CIEM |
|-------|--------|-------------------|
| **A01 Broken Access Control** | Escalada / IDOR | Papéis `admin`/`observer` via `require_admin` / `require_user`; token assinado com papel e revogação se usuário desativado; SSO Guacamole só admin |
| **A02 Cryptographic Failures** | Segredos fracos | Senhas PBKDF2-SHA256 (260k); sessão/SSO HMAC-SHA256; `CIEM_SECRET_KEY` obrigatória (fail-fast); TLS 1.2+ no proxy |
| **A03 Injection** | YAML/SQL/cmd | Entrada via Pydantic; sem SQL dinâmico; senhas nunca interpoladas em shell |
| **A04 Insecure Design** | Fluxos frágeis | Rate limit no login/sessão/config; política de senha; mocks de coletor desligados por padrão |
| **A05 Security Misconfiguration** | Headers/CORS/docs | Middleware de cabeçalhos; CORS sem `*`+credentials; `/docs` off em `production`; `server_tokens off`; CSP/HSTS no nginx |
| **A06 Vulnerable Components** | Deps desatualizadas | CI: ruff, bandit, gitleaks, **pip-audit** |
| **A07 Identification Failures** | Auth fraca | Política de senha (tamanho, complexidade, blocklist); rate limit 5/min no login; senhas padrão rotacionadas |
| **A08 Integrity Failures** | Supply chain | Builds Docker na CI; imagens versionadas; sem `curl \| bash` no runtime |
| **A09 Logging Failures** | Sem trilha | `ciem.security` JSON: `login_success` / `login_failure` / exceções; auditoria de sessões Guacamole |
| **A10 SSRF** | Pivot interno | `validate_outbound_url` antes de chamar provedor de IA (bloqueia localhost/metadata/IPs privados) |

## Variáveis relacionadas

| Variável | Efeito |
|----------|--------|
| `CIEM_SECRET_KEY` | Assinatura de sessão/SSO (obrigatória) |
| `CIEM_ENV=production` | Esconde `/docs`, mensagens 500 genéricas |
| `CIEM_CORS_ORIGINS` | Origens explícitas (evite `*` em produção) |
| `CIEM_TRUSTED_HOSTS` | Lista de hosts aceitos (TrustedHost) |
| `CIEM_PASSWORD_MIN_LENGTH` | Padrão `10` |
| `CIEM_SSRF_ALLOW_PRIVATE=1` | Permite IA/APIs em rede privada (lab) |
| `CIEM_RATE_LIMIT_ENABLED=0` | Desliga rate limit (só testes) |
| `CIEM_DOCS_ENABLED=1` | Força OpenAPI mesmo em production |

## Pendências conscientes

- **MFA/TOTP** ainda não implementado (ASVS 2.8) — tokens HMAC + rate limit mitigam força bruta
- **LDAP real** continua stub; quando implementado, validar bind e grupos com TLS
- Tokens SSO ainda podem aparecer em query string no redirect Guacamole — cookie `HttpOnly`/`Secure`/`SameSite=Strict` reduz impacto; evolução: trocar por one-time POST
- CSP do portal usa `'unsafe-inline'` por limitações do HTML estático atual — candidata a nonces numa iteração futura

## Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- Controles já documentados: [AUTH.md](AUTH.md), [DEPLOYMENT.md](DEPLOYMENT.md), [CI_CD.md](CI_CD.md)
