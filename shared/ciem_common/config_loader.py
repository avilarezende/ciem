"""Carregamento centralizado de arquivos YAML de configuração do CIEM."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _config_dir() -> Path:
    """Resolve o diretório de configuração a partir da variável ``CONFIG_PATH``.

    Padrão: ``./config`` relativo ao diretório de trabalho atual.
    O caminho pode ser absoluto ou relativo.
    """
    raw = os.environ.get("CONFIG_PATH", "./config")
    return Path(raw).expanduser().resolve()


def _read_yaml(filename: str) -> dict[str, Any]:
    """Lê um arquivo YAML do diretório de configuração.

    Args:
        filename: Nome do arquivo (ex.: ``main.yaml``).

    Returns:
        Dicionário com o conteúdo parseado ou ``{}`` se o arquivo não existir.
    """
    path = _config_dir() / filename
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


class MainConfig(BaseModel):
    """Configuração principal da plataforma CIEM (``config/main.yaml``).

    Attributes:
        platform_name: Nome exibido no painel e nos relatórios de auditoria.
        environment: Ambiente de execução (``production``, ``staging``, ``development``).
        audit_log_path: Caminho do arquivo de auditoria em formato JSON Lines.
        log_level: Nível de log da aplicação (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        collection_interval_seconds: Intervalo entre ciclos automáticos de coleta.
    """

    platform_name: str = Field(default="CIEM ZTNA", description="Nome da plataforma")
    environment: str = Field(default="development", description="Ambiente de execução")
    audit_log_path: str = Field(
        default="./logs/audit.jsonl",
        description="Arquivo JSON Lines para registros de auditoria de sessão",
    )
    log_level: str = Field(default="INFO", description="Nível de log global")
    collection_interval_seconds: int = Field(
        default=300,
        ge=30,
        description="Intervalo em segundos entre coletas automáticas",
    )


class ModuleEntry(BaseModel):
    """Entrada de configuração de um módulo coletor individual.

    Attributes:
        enabled: Se ``false``, o módulo é ignorado pelo orquestrador.
        description: Descrição legível para documentação interna.
        options: Parâmetros específicos repassados ao módulo (hosts, credenciais, etc.).
    """

    enabled: bool = Field(default=True, description="Habilita ou desabilita o módulo")
    description: str = Field(default="", description="Descrição do módulo")
    options: dict[str, Any] = Field(default_factory=dict, description="Opções do módulo")


class ModulesConfig(BaseModel):
    """Configuração dos módulos coletores (``config/modules.yaml``).

    A chave de cada módulo corresponde ao ``name`` retornado por :class:`CollectorModule`.
    """

    modules: dict[str, ModuleEntry] = Field(
        default_factory=dict,
        description="Mapa nome_do_módulo -> configuração",
    )

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ModulesConfig:
        """Constrói a configuração a partir do YAML bruto."""
        modules_raw = raw.get("modules", raw)
        if not isinstance(modules_raw, dict):
            return cls()
        modules: dict[str, ModuleEntry] = {}
        for name, entry in modules_raw.items():
            if isinstance(entry, dict):
                modules[name] = ModuleEntry.model_validate(entry)
            else:
                modules[name] = ModuleEntry(enabled=bool(entry))
        return cls(modules=modules)


class LocalUserEntry(BaseModel):
    """Usuário local definido em ``config/auth.yaml``.

    Attributes:
        username: Login do usuário.
        password_hash: Hash PBKDF2-SHA256 no formato ``salt$digest`` (gerado por ``auth``).
        role: Papel de acesso (``observer`` ou ``admin``).
        enabled: Se ``false``, o usuário não pode autenticar.
    """

    username: str
    password_hash: str
    role: str = Field(default="observer")
    enabled: bool = Field(default=True)


class LdapConfig(BaseModel):
    """Configuração do backend LDAP (``config/auth.yaml`` -> ``ldap``).

    Usuários locais em ``local_users`` continuam válidos mesmo com LDAP ativo.
    O usuário ``admin`` padrão é independente do LDAP.
    """

    enabled: bool = Field(default=False, description="Ativa autenticação LDAP após falha local")
    host: str = Field(default="ldap.exemplo.local", description="Hostname ou IP do servidor LDAP")
    port: int = Field(default=636, ge=1, le=65535, description="Porta LDAP/LDAPS")
    use_ssl: bool = Field(default=True, description="Usar LDAPS (TLS)")
    server_url: str = Field(
        default="",
        description="URL completa (opcional; se vazio, montada a partir de host/port/use_ssl)",
    )
    domain: str = Field(default="exemplo.local", description="Domínio AD/LDAP")
    base_dn: str = Field(default="ou=usuarios,dc=exemplo,dc=local")
    uid_attribute: str = Field(
        default="uid", description="Atributo de login (uid, sAMAccountName, etc.)"
    )
    user_filter: str = Field(default="(uid=%s)", description="Filtro de busca; %s = username")
    bind_dn: str = Field(default="")
    bind_password: str = Field(default="")
    ca_cert_path: str = Field(default="", description="Caminho do certificado CA / cadeia")
    client_cert_path: str = Field(default="", description="Certificado cliente (opcional)")
    display_name_attribute: str = Field(default="cn")
    group_role_mapping: dict[str, str] = Field(default_factory=dict)
    default_role: str = Field(default="observer")
    verify_ssl: bool = Field(default=True)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> LdapConfig:
        """Aceita nomes legados (server_uri, user_search_filter) e campos novos."""
        data = dict(raw) if isinstance(raw, dict) else {}
        if "server_url" not in data and "server_uri" in data:
            data["server_url"] = data.pop("server_uri")
        if "user_filter" not in data and "user_search_filter" in data:
            filt = str(data.pop("user_search_filter"))
            data["user_filter"] = filt.replace("{username}", "%s")
        # Inferir host/port a partir da URL se não informados
        url = str(data.get("server_url") or "")
        if url and "host" not in raw:
            parsed = url.replace("ldaps://", "").replace("ldap://", "")
            host_port = parsed.split("/")[0]
            if ":" in host_port:
                host, port_s = host_port.rsplit(":", 1)
                data.setdefault("host", host)
                if port_s.isdigit():
                    data.setdefault("port", int(port_s))
            else:
                data.setdefault("host", host_port)
            data.setdefault("use_ssl", url.startswith("ldaps://"))
        return cls.model_validate(data)

    def resolved_server_url(self) -> str:
        """URL efetiva do servidor LDAP."""
        if self.server_url.strip():
            return self.server_url.strip()
        scheme = "ldaps" if self.use_ssl else "ldap"
        return f"{scheme}://{self.host}:{self.port}"

    def to_yaml_dict(self) -> dict[str, Any]:
        """Serializa para gravação em auth.yaml."""
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "use_ssl": self.use_ssl,
            "server_url": self.resolved_server_url(),
            "domain": self.domain,
            "base_dn": self.base_dn,
            "uid_attribute": self.uid_attribute,
            "user_filter": self.user_filter,
            "bind_dn": self.bind_dn,
            "bind_password": self.bind_password,
            "ca_cert_path": self.ca_cert_path,
            "client_cert_path": self.client_cert_path,
            "display_name_attribute": self.display_name_attribute,
            "group_role_mapping": self.group_role_mapping,
            "default_role": self.default_role,
            "verify_ssl": self.verify_ssl,
        }


class AuthConfig(BaseModel):
    """Configuração de autenticação (``config/auth.yaml``)."""

    local_users: list[LocalUserEntry] = Field(default_factory=list)
    ldap: LdapConfig = Field(default_factory=LdapConfig)


class AiConfig(BaseModel):
    """Configuração de provedores de IA (``config/ai.yaml``).

    Apenas administradores configuram. Quando ``enabled``, os insights
    gerados ficam visíveis a todos os usuários autenticados e no Grafana.
    """

    enabled: bool = Field(default=False, description="Ativa geração e exibição de insights")
    provider: str = Field(default="openai_compatible", description="Tipo do provedor")
    base_url: str = Field(default="https://api.openai.com/v1", description="URL base da API")
    api_key: str = Field(default="", description="Chave de API do provedor")
    model: str = Field(default="gpt-4o-mini", description="Nome do modelo")
    organization: str = Field(default="", description="Organização OpenAI (opcional)")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1200, ge=64, le=16000)
    refresh_interval_seconds: int = Field(default=300, ge=30, le=86400)
    max_alarms: int = Field(default=40, ge=1, le=500)
    max_history: int = Field(default=60, ge=1, le=500)
    language: str = Field(default="pt-BR")
    verify_ssl: bool = Field(default=True)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    auth_header: str = Field(default="Authorization")
    auth_scheme: str = Field(default="Bearer")
    chat_path: str = Field(default="/chat/completions")
    system_prompt: str = Field(default="")

    def to_yaml_dict(self) -> dict[str, Any]:
        """Serializa para gravação em ai.yaml."""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model": self.model,
            "organization": self.organization,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "max_alarms": self.max_alarms,
            "max_history": self.max_history,
            "language": self.language,
            "verify_ssl": self.verify_ssl,
            "timeout_seconds": self.timeout_seconds,
            "auth_header": self.auth_header,
            "auth_scheme": self.auth_scheme,
            "chat_path": self.chat_path,
            "system_prompt": self.system_prompt,
        }

    def public_dict(self, *, include_secrets: bool = False) -> dict[str, Any]:
        """Dicionário para API (mascara api_key por padrão)."""
        data = self.to_yaml_dict()
        if include_secrets:
            return data
        key = data.get("api_key") or ""
        if key:
            data["api_key"] = ("*" * max(0, len(key) - 4)) + key[-4:]
            data["api_key_set"] = True
        else:
            data["api_key"] = ""
            data["api_key_set"] = False
        return data


@lru_cache(maxsize=1)
def load_main_config() -> MainConfig:
    """Carrega e valida ``config/main.yaml`` (ou equivalente em ``CONFIG_PATH``)."""
    return MainConfig.model_validate(_read_yaml("main.yaml"))


@lru_cache(maxsize=1)
def load_modules_config() -> ModulesConfig:
    """Carrega e valida ``config/modules.yaml``."""
    return ModulesConfig.from_raw(_read_yaml("modules.yaml"))


@lru_cache(maxsize=1)
def load_auth_config() -> AuthConfig:
    """Carrega e valida ``config/auth.yaml``."""
    raw = _read_yaml("auth.yaml")
    local_raw = raw.get("local_users", [])
    ldap_raw = raw.get("ldap", {})
    return AuthConfig(
        local_users=[LocalUserEntry.model_validate(u) for u in local_raw if isinstance(u, dict)],
        ldap=LdapConfig.from_raw(ldap_raw if isinstance(ldap_raw, dict) else {}),
    )


@lru_cache(maxsize=1)
def load_ai_config() -> AiConfig:
    """Carrega e valida ``config/ai.yaml``."""
    raw = _read_yaml("ai.yaml")
    ai_raw = raw.get("ai", raw)
    if not isinstance(ai_raw, dict):
        return AiConfig()
    return AiConfig.model_validate(ai_raw)


def save_ai_config(config: AiConfig) -> None:
    """Persiste ``AiConfig`` em ``config/ai.yaml``."""
    path = _config_dir() / "ai.yaml"
    payload = {"ai": config.to_yaml_dict()}
    header = (
        "# =============================================================================\n"
        "# CIEM — Inteligência Artificial (insights de logs / alarmes)\n"
        "# Atualizado pelo portal de administração.\n"
        "# Configurável apenas por administradores; insights visíveis a todos quando ativo.\n"
        "# Documentação: docs/AI.md\n"
        "# =============================================================================\n"
    )
    dumped = yaml.safe_dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False)
    path.write_text(header + "\n" + dumped, encoding="utf-8")
    clear_config_cache()


def update_ai_config(updates: dict[str, Any]) -> AiConfig:
    """Atualiza campos de IA e persiste em ai.yaml."""
    cfg = load_ai_config()
    current = cfg.to_yaml_dict()
    bool_keys = {"enabled", "verify_ssl"}
    int_keys = {
        "max_tokens",
        "refresh_interval_seconds",
        "max_alarms",
        "max_history",
        "timeout_seconds",
    }
    float_keys = {"temperature"}

    for key, value in updates.items():
        if key not in current and key not in AiConfig.model_fields:
            continue
        if key == "api_key" and isinstance(value, str) and value.strip().startswith("*"):
            # Campo mascarado na UI — não sobrescrever a chave existente
            continue
        if key in bool_keys:
            if isinstance(value, str):
                current[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                current[key] = bool(value)
        elif key in int_keys and value is not None:
            current[key] = int(value)
        elif key in float_keys and value is not None:
            current[key] = float(value)
        else:
            current[key] = (
                _coerce_option_value(value) if not isinstance(value, dict | list) else value
            )

    cfg = AiConfig.model_validate(current)
    save_ai_config(cfg)
    return load_ai_config()


def save_auth_config(config: AuthConfig) -> None:
    """Persiste ``AuthConfig`` em ``config/auth.yaml``."""
    path = _config_dir() / "auth.yaml"
    payload = {
        "local_users": [
            {
                "username": u.username,
                "password_hash": u.password_hash,
                "role": u.role,
                "enabled": u.enabled,
            }
            for u in config.local_users
        ],
        "ldap": config.ldap.to_yaml_dict(),
    }
    header = (
        "# =============================================================================\n"
        "# CIEM — Autenticação e Autorização\n"
        "# Atualizado pelo portal de administração.\n"
        "# Usuários locais funcionam independentemente do LDAP.\n"
        "# Usuário padrão: admin (altere a senha em produção).\n"
        "# Documentação: docs/AUTH.md\n"
        "# =============================================================================\n"
    )
    dumped = yaml.safe_dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False)
    path.write_text(header + "\n" + dumped, encoding="utf-8")
    clear_config_cache()


def update_ldap_config(updates: dict[str, Any]) -> LdapConfig:
    """Atualiza campos LDAP e persiste em auth.yaml."""
    cfg = load_auth_config()
    current = cfg.ldap.to_yaml_dict()
    for key, value in updates.items():
        if key in current or key in LdapConfig.model_fields:
            if key == "port" and value is not None:
                current[key] = int(value)
            elif key in {"enabled", "use_ssl", "verify_ssl"}:
                if isinstance(value, str):
                    current[key] = value.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    current[key] = bool(value)
            elif key == "group_role_mapping" and isinstance(value, dict):
                current[key] = {str(k): str(v) for k, v in value.items()}
            else:
                current[key] = value
    cfg.ldap = LdapConfig.from_raw(current)
    # Se server_url vazio, regenera
    if not str(updates.get("server_url") or "").strip():
        cfg.ldap.server_url = cfg.ldap.resolved_server_url()
    save_auth_config(cfg)
    return load_auth_config().ldap


def create_local_user(
    username: str, password: str, role: str = "observer", enabled: bool = True
) -> LocalUserEntry:
    """Cria usuário local com senha hasheada."""
    from ciem_common.auth import hash_password

    cfg = load_auth_config()
    if any(u.username == username for u in cfg.local_users):
        raise ValueError(f"Usuário '{username}' já existe")
    if role not in {"admin", "observer"}:
        raise ValueError("Papel deve ser admin ou observer")
    if not password:
        raise ValueError("Senha obrigatória")
    entry = LocalUserEntry(
        username=username,
        password_hash=hash_password(password),
        role=role,
        enabled=enabled,
    )
    cfg.local_users.append(entry)
    save_auth_config(cfg)
    return entry


def update_local_user(
    username: str,
    *,
    password: str | None = None,
    role: str | None = None,
    enabled: bool | None = None,
) -> LocalUserEntry:
    """Atualiza senha, papel ou status de um usuário local."""
    from ciem_common.auth import hash_password

    cfg = load_auth_config()
    for index, entry in enumerate(cfg.local_users):
        if entry.username != username:
            continue
        data = entry.model_dump()
        if password is not None:
            if not password:
                raise ValueError("Senha não pode ser vazia")
            data["password_hash"] = hash_password(password)
        if role is not None:
            if role not in {"admin", "observer"}:
                raise ValueError("Papel deve ser admin ou observer")
            # Não remover o último admin
            if entry.role == "admin" and role != "admin":
                admins = [u for u in cfg.local_users if u.role == "admin" and u.enabled]
                if len(admins) <= 1:
                    raise ValueError("Não é possível remover o papel admin do último administrador")
            data["role"] = role
        if enabled is not None:
            if entry.role == "admin" and entry.enabled and not enabled:
                admins = [u for u in cfg.local_users if u.role == "admin" and u.enabled]
                if len(admins) <= 1:
                    raise ValueError("Não é possível desabilitar o último administrador")
            data["enabled"] = enabled
        cfg.local_users[index] = LocalUserEntry.model_validate(data)
        save_auth_config(cfg)
        return cfg.local_users[index]
    raise KeyError(f"Usuário '{username}' não encontrado")


def delete_local_user(username: str) -> None:
    """Remove usuário local. Impede exclusão do último admin."""
    cfg = load_auth_config()
    target = next((u for u in cfg.local_users if u.username == username), None)
    if target is None:
        raise KeyError(f"Usuário '{username}' não encontrado")
    if target.role == "admin":
        admins = [u for u in cfg.local_users if u.role == "admin" and u.enabled]
        if len(admins) <= 1:
            raise ValueError(
                "Não é possível excluir o último administrador. "
                "Crie outro admin antes ou altere a senha do usuário admin."
            )
    cfg.local_users = [u for u in cfg.local_users if u.username != username]
    save_auth_config(cfg)


def is_module_enabled(module_name: str) -> bool:
    """Verifica se um módulo coletor está habilitado na configuração.

    Módulos ausentes em ``modules.yaml`` são considerados desabilitados.
    """
    modules = load_modules_config().modules
    entry = modules.get(module_name)
    return entry is not None and entry.enabled


def _coerce_option_value(value: Any) -> Any:
    """Normaliza valores vindos do portal (strings de formulário → tipos YAML)."""
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
        if re.fullmatch(r"-?\d+\.\d+", stripped):
            return float(stripped)
        if "," in stripped and not stripped.startswith("http"):
            parts = [p.strip() for p in stripped.split(",") if p.strip()]
            if parts and all(re.fullmatch(r"[A-Za-z0-9_\-]+", p) for p in parts):
                return parts
        return value
    return value


def set_module_enabled(module_name: str, enabled: bool) -> bool:
    """Atualiza ``enabled`` de um módulo em ``config/modules.yaml``.

    Preserva comentários e demais campos do arquivo. Retorna o novo estado.
    """
    path = _config_dir() / "modules.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    modules = load_modules_config().modules
    if module_name not in modules:
        raise KeyError(f"Módulo '{module_name}' não encontrado")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    module_indent = None
    in_module = False
    updated = False
    value = "true" if enabled else "false"

    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        if re.match(rf"^{re.escape(module_name)}\s*:", stripped):
            in_module = True
            module_indent = indent
            continue

        if in_module:
            if indent <= (module_indent or 0) and re.match(r"^[A-Za-z0-9_]+\s*:", stripped):
                break
            if re.match(r"^enabled\s*:", stripped):
                prefix = line[: line.index("enabled")]
                comment = ""
                if "#" in stripped:
                    comment = "  #" + stripped.split("#", 1)[1].rstrip("\n")
                newline = "\n" if line.endswith("\n") else ""
                lines[index] = f"{prefix}enabled: {value}{comment}{newline}"
                updated = True
                break

    if not updated:
        raise RuntimeError(f"Campo enabled não encontrado para módulo '{module_name}'")

    path.write_text("".join(lines), encoding="utf-8")
    clear_config_cache()
    return enabled


def update_module_config(
    module_name: str,
    *,
    enabled: bool | None = None,
    options: dict[str, Any] | None = None,
) -> ModuleEntry:
    """Atualiza ``enabled`` e/ou ``options`` de um módulo em ``modules.yaml``.

    - Somente ``enabled``: preserva comentários do arquivo.
    - Com ``options``: regrava o YAML a partir da configuração atual (mantém
      todos os módulos/descrições; comentários inline podem ser omitidos).
    """
    modules = load_modules_config().modules
    if module_name not in modules:
        raise KeyError(f"Módulo '{module_name}' não encontrado")

    if options is None:
        if enabled is None:
            return modules[module_name]
        set_module_enabled(module_name, enabled)
        return load_modules_config().modules[module_name]

    path = _config_dir() / "modules.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    raw = _read_yaml("modules.yaml")
    modules_raw: dict[str, Any] = raw.get("modules", raw)
    if not isinstance(modules_raw, dict) or module_name not in modules_raw:
        raise KeyError(f"Módulo '{module_name}' não encontrado")

    entry_raw = modules_raw[module_name]
    if not isinstance(entry_raw, dict):
        entry_raw = {"enabled": bool(entry_raw), "description": "", "options": {}}

    if enabled is not None:
        entry_raw["enabled"] = enabled

    current_options = entry_raw.get("options")
    if not isinstance(current_options, dict):
        current_options = {}
    merged = dict(current_options)
    for key, value in options.items():
        merged[key] = _coerce_option_value(value)
    entry_raw["options"] = merged
    modules_raw[module_name] = entry_raw

    out: dict[str, Any] = {"modules": modules_raw}
    header = (
        "# =============================================================================\n"
        "# CIEM — Módulos Coletores\n"
        "# Atualizado pelo portal de administração.\n"
        "# Documentação: docs/MODULES.md\n"
        "# =============================================================================\n"
    )
    dumped = yaml.safe_dump(
        out,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    path.write_text(header + "\n" + dumped, encoding="utf-8")
    clear_config_cache()
    return load_modules_config().modules[module_name]


class WikiPage(BaseModel):
    """Página da wiki colaborativa de serviços."""

    id: str = Field(description="Identificador estável (slug)")
    title: str = Field(description="Título exibido")
    body: str = Field(default="", description="Conteúdo em Markdown")
    updated_by: str = Field(default="system", description="Último editor")
    updated_at: str = Field(default="", description="ISO-8601 da última edição")


class WikiConfig(BaseModel):
    """Wiki colaborativa persistida em ``config/wiki.yaml``."""

    title: str = Field(default="Wiki de serviços")
    pages: list[WikiPage] = Field(default_factory=list)


def _default_wiki_pages() -> list[WikiPage]:
    return [
        WikiPage(
            id="rede",
            title="Rede e conectividade",
            body=(
                "## Rede institucional\n\n"
                "- Documente gateway, DNS e VPN/ZTNA aqui\n"
                "- Consoles também no **Navegador** do portal\n"
            ),
            updated_by="system",
            updated_at="2026-01-01T00:00:00Z",
        ),
        WikiPage(
            id="monitoramento",
            title="Monitoramento",
            body=(
                "## Monitoramento\n\n"
                "| Sistema | Uso |\n|---------|-----|\n"
                "| Zabbix | Alarmes e hosts |\n"
                "| Cacti | Tráfego |\n"
                "| Nagios | Checagens |\n"
            ),
            updated_by="system",
            updated_at="2026-01-01T00:00:00Z",
        ),
        WikiPage(
            id="acessos",
            title="Acessos e sessões",
            body=(
                "## Acessos\n\n"
                "- Sessões via **Sessões** / Guacamole (admin)\n"
                "- Auditoria completa de comandos\n"
            ),
            updated_by="system",
            updated_at="2026-01-01T00:00:00Z",
        ),
    ]


@lru_cache(maxsize=1)
def load_wiki_config() -> WikiConfig:
    """Carrega ``config/wiki.yaml`` (cria estrutura padrão se vazio)."""
    raw = _read_yaml("wiki.yaml")
    wiki_raw = raw.get("wiki", raw) if isinstance(raw, dict) else {}
    if not isinstance(wiki_raw, dict):
        wiki_raw = {}
    pages_raw = wiki_raw.get("pages") or []
    pages: list[WikiPage] = []
    if isinstance(pages_raw, list):
        for item in pages_raw:
            if isinstance(item, dict) and item.get("id") and item.get("title"):
                pages.append(WikiPage.model_validate(item))
    if not pages:
        pages = _default_wiki_pages()
    return WikiConfig(
        title=str(wiki_raw.get("title") or "Wiki de serviços"),
        pages=pages,
    )


def save_wiki_config(config: WikiConfig) -> None:
    """Persiste a wiki em ``config/wiki.yaml``."""
    path = _config_dir() / "wiki.yaml"
    payload = {
        "wiki": {
            "title": config.title,
            "pages": [p.model_dump() for p in config.pages],
        }
    }
    header = (
        "# =============================================================================\n"
        "# CIEM — Wiki colaborativa de serviços da instituição\n"
        "# Editável pelo portal (usuários autenticados). Documentação: docs/PORTAL.md\n"
        "# =============================================================================\n"
    )
    dumped = yaml.safe_dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False)
    path.write_text(header + "\n" + dumped, encoding="utf-8")
    load_wiki_config.cache_clear()


def upsert_wiki_page(
    page_id: str,
    *,
    title: str,
    body: str,
    updated_by: str,
    updated_at: str,
) -> WikiPage:
    """Cria ou atualiza uma página da wiki e persiste."""
    slug = re.sub(r"[^a-z0-9\-]+", "-", page_id.strip().lower()).strip("-")[:64]
    if not slug:
        raise ValueError("id inválido")
    clean_title = title.strip()[:120] or slug
    clean_body = body[:20000]
    cfg = load_wiki_config()
    pages = list(cfg.pages)
    found = False
    for idx, page in enumerate(pages):
        if page.id == slug:
            pages[idx] = WikiPage(
                id=slug,
                title=clean_title,
                body=clean_body,
                updated_by=updated_by,
                updated_at=updated_at,
            )
            found = True
            break
    if not found:
        pages.append(
            WikiPage(
                id=slug,
                title=clean_title,
                body=clean_body,
                updated_by=updated_by,
                updated_at=updated_at,
            )
        )
    save_wiki_config(WikiConfig(title=cfg.title, pages=pages))
    return next(p for p in load_wiki_config().pages if p.id == slug)


def delete_wiki_page(page_id: str) -> bool:
    """Remove página da wiki. Retorna True se removeu."""
    cfg = load_wiki_config()
    pages = [p for p in cfg.pages if p.id != page_id]
    if len(pages) == len(cfg.pages):
        return False
    if not pages:
        pages = _default_wiki_pages()
    save_wiki_config(WikiConfig(title=cfg.title, pages=pages))
    return True


def clear_config_cache() -> None:
    """Limpa o cache interno; útil em testes após alterar ``CONFIG_PATH``."""
    load_main_config.cache_clear()
    load_modules_config.cache_clear()
    load_auth_config.cache_clear()
    load_ai_config.cache_clear()
    load_wiki_config.cache_clear()
    from ciem_common.targets_loader import clear_targets_cache

    clear_targets_cache()
