"""Interfaces e modelos de dados compartilhados pelos módulos coletores do CIEM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    """Papel de acesso do usuário na plataforma ZTNA.

    OBSERVER: acesso somente leitura a sessões, métricas e relatórios de auditoria.
    ADMIN: acesso completo, incluindo configuração de módulos e gerenciamento de usuários.
    """

    OBSERVER = "observer"
    ADMIN = "admin"


@dataclass(slots=True)
class CollectorResult:
    """Resultado padronizado retornado por um módulo coletor após cada ciclo de coleta.

    Attributes:
        module_name: Nome identificador do módulo (ex.: ``ssh_sessions``, ``firewall``).
        timestamp: Momento UTC em que a coleta foi finalizada.
        status: Estado da execução — ``success``, ``partial`` ou ``error``.
        data: Payload estruturado com os dados coletados (formato depende do módulo).
        errors: Lista de mensagens de erro ou avisos registrados durante a coleta.
    """

    module_name: str
    timestamp: datetime
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SessionRecord:
    """Registro de uma sessão de manutenção de rede auditada pela plataforma.

    Attributes:
        session_id: Identificador único da sessão (UUID ou ID do bastion/jump host).
        user: Nome de usuário que iniciou a sessão.
        target_host: Hostname ou endereço IP do equipamento alvo.
        protocol: Protocolo utilizado (ex.: ``ssh``, ``telnet``, ``rdp``).
        started_at: Data/hora UTC de início da sessão.
        ended_at: Data/hora UTC de encerramento; ``None`` se a sessão ainda estiver ativa.
        commands: Lista de comandos executados durante a sessão (quando disponível).
        duration_seconds: Duração total em segundos; calculada automaticamente se possível.
    """

    session_id: str
    user: str
    target_host: str
    protocol: str
    started_at: datetime
    ended_at: datetime | None = None
    commands: list[str] = field(default_factory=list)
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        """Calcula ``duration_seconds`` quando ``ended_at`` estiver definido."""
        if self.duration_seconds is None and self.ended_at is not None:
            delta = self.ended_at - self.started_at
            self.duration_seconds = max(delta.total_seconds(), 0.0)


class CollectorModule(ABC):
    """Contrato base que todo módulo coletor do CIEM deve implementar.

    Cada módulo é responsável por extrair dados de uma fonte específica
    (sessões SSH, logs de firewall, inventário de ativos, etc.) e expor
    um resultado padronizado via :class:`CollectorResult`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único do módulo usado em configuração e métricas."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Indica se o módulo está habilitado na configuração atual."""

    @abstractmethod
    def collect(self) -> CollectorResult:
        """Executa um ciclo de coleta e retorna o resultado estruturado."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verifica conectividade e pré-requisitos do módulo sem coletar dados completos."""

    @abstractmethod
    def get_config_schema(self) -> dict[str, Any]:
        """Retorna o esquema JSON Schema das opções de configuração aceitas pelo módulo."""
