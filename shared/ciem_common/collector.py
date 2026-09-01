"""Contrato base para módulos coletores CIEM."""

from abc import ABC, abstractmethod

from ciem_common.models import CollectResponse


class CollectorModule(ABC):
    """Interface que cada serviço coletor deve implementar."""

    name: str

    @abstractmethod
    async def collect(self) -> CollectResponse:
        """Executa a coleta e retorna dados normalizados."""
