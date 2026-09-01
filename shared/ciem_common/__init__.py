"""Biblioteca compartilhada CIEM — interfaces, configuração, autenticação e auditoria."""

from ciem_common.app import create_collector_app
from ciem_common.audit import log_session, read_sessions
from ciem_common.auth import (
    User,
    authenticate,
    authenticate_ldap,
    authenticate_local,
    hash_password,
    verify_password,
)
from ciem_common.collector import CollectorModule
from ciem_common.config import load_config
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
    CollectorResult,
    SessionRecord,
    UserRole,
    CollectorModule as ZtnaCollectorModule,
)
from ciem_common.models import ActiveAlarm, CollectResponse, HistoryEvent

__all__ = [
    "ActiveAlarm",
    "AuthConfig",
    "CollectResponse",
    "CollectorModule",
    "CollectorResult",
    "HistoryEvent",
    "LdapConfig",
    "LocalUserEntry",
    "MainConfig",
    "ModuleEntry",
    "ModulesConfig",
    "SessionRecord",
    "User",
    "UserRole",
    "ZtnaCollectorModule",
    "authenticate",
    "authenticate_ldap",
    "authenticate_local",
    "clear_config_cache",
    "create_collector_app",
    "hash_password",
    "is_module_enabled",
    "load_auth_config",
    "load_config",
    "load_main_config",
    "load_modules_config",
    "log_session",
    "read_sessions",
    "verify_password",
]

__version__ = "0.1.0"
