"""Biblioteca compartilhada CIEM — interfaces, configuração, autenticação e auditoria."""

from ciem_common.audit import log_session, read_sessions
from ciem_common.auth import (
    User,
    authenticate,
    authenticate_ldap,
    authenticate_local,
    hash_password,
    verify_password,
)
from ciem_common.config_loader import (
    AuthConfig,
    LdapConfig,
    LocalUserEntry,
    MainConfig,
    ModuleEntry,
    ModulesConfig,
    clear_config_cache,
    is_module_enabled,
    load_auth_config,
    load_main_config,
    load_modules_config,
)
from ciem_common.interfaces import (
    CollectorModule,
    CollectorResult,
    SessionRecord,
    UserRole,
)

__all__ = [
    "AuthConfig",
    "CollectorModule",
    "CollectorResult",
    "LdapConfig",
    "LocalUserEntry",
    "MainConfig",
    "ModuleEntry",
    "ModulesConfig",
    "SessionRecord",
    "User",
    "UserRole",
    "authenticate",
    "authenticate_ldap",
    "authenticate_local",
    "clear_config_cache",
    "hash_password",
    "is_module_enabled",
    "load_auth_config",
    "load_main_config",
    "load_modules_config",
    "log_session",
    "read_sessions",
    "verify_password",
]

__version__ = "0.1.0"
