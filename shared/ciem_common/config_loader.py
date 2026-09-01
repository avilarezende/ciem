"""Carregamento centralizado de arquivos YAML de configuração do CIEM."""

from __future__ import annotations

import os
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

    Attributes:
        enabled: Ativa tentativa de autenticação via LDAP após falha local.
        server_uri: URI do servidor (ex.: ``ldap://dc01.empresa.local:389``).
        base_dn: DN base para busca de usuários (ex.: ``dc=empresa,dc=local``).
        bind_dn: DN da conta de serviço para bind inicial (opcional).
        bind_password: Senha da conta de serviço (opcional; preferir variável de ambiente).
        user_search_filter: Filtro LDAP com placeholder ``{username}``.
        group_role_mapping: Mapa grupo LDAP -> papel CIEM (``observer``/``admin``).
    """

    enabled: bool = Field(default=False)
    server_uri: str = Field(default="ldap://localhost:389")
    base_dn: str = Field(default="dc=example,dc=com")
    bind_dn: str = Field(default="")
    bind_password: str = Field(default="")
    user_search_filter: str = Field(default="(uid={username})")
    group_role_mapping: dict[str, str] = Field(default_factory=dict)


class AuthConfig(BaseModel):
    """Configuração de autenticação (``config/auth.yaml``)."""

    local_users: list[LocalUserEntry] = Field(default_factory=list)
    ldap: LdapConfig = Field(default_factory=LdapConfig)


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
        ldap=LdapConfig.model_validate(ldap_raw if isinstance(ldap_raw, dict) else {}),
    )


def is_module_enabled(module_name: str) -> bool:
    """Verifica se um módulo coletor está habilitado na configuração.

    Módulos ausentes em ``modules.yaml`` são considerados desabilitados.
    """
    modules = load_modules_config().modules
    entry = modules.get(module_name)
    return entry is not None and entry.enabled


def clear_config_cache() -> None:
    """Limpa o cache interno; útil em testes após alterar ``CONFIG_PATH``."""
    load_main_config.cache_clear()
    load_modules_config.cache_clear()
    load_auth_config.cache_clear()
