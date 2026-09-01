"""Carregamento de alvos de manutenção (``config/targets.yaml``)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from ciem_common.config_loader import _read_yaml


class TargetCredential(BaseModel):
    """Credenciais de acesso a um alvo de manutenção."""

    username: str = ""
    password: str = ""
    ssh_key_path: str = ""


class MaintenanceTarget(BaseModel):
    """Equipamento acessível via sessão Guacamole (SSH/RDP/VNC)."""

    id: str
    name: str
    hostname: str
    port: int = 22
    protocol: str = "ssh"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class TargetsConfig(BaseModel):
    """Configuração de alvos e credenciais (``config/targets.yaml``)."""

    targets: list[MaintenanceTarget] = Field(default_factory=list)
    credentials: dict[str, TargetCredential] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TargetsConfig:
        targets_raw = raw.get("targets", [])
        creds_raw = raw.get("credentials", {})
        targets = [MaintenanceTarget.model_validate(t) for t in targets_raw if isinstance(t, dict)]
        credentials = {
            key: TargetCredential.model_validate(val)
            for key, val in creds_raw.items()
            if isinstance(val, dict)
        }
        return cls(targets=targets, credentials=credentials)

    def enabled_targets(self) -> list[MaintenanceTarget]:
        return [t for t in self.targets if t.enabled]

    def credential_for(self, target_id: str) -> TargetCredential:
        return self.credentials.get(target_id, TargetCredential())


@lru_cache(maxsize=1)
def load_targets_config() -> TargetsConfig:
    """Carrega e valida ``config/targets.yaml``."""
    return TargetsConfig.from_raw(_read_yaml("targets.yaml"))


def clear_targets_cache() -> None:
    load_targets_config.cache_clear()
