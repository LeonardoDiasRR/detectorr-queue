"""
Interface do repositório de câmeras (Domain Layer).
Define o contrato que as implementações concretas devem seguir.
"""

from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import Camera


class CameraRepository(ABC):
    """
    Interface abstrata para repositório de câmeras.
    Segue o padrão Repository do DDD.
    """

    @abstractmethod
    def get_active_cameras(self) -> List[Camera]:
        """
        Obtém todas as câmeras ativas do sistema.
        
        :return: Lista de entidades Camera ativas.
        """
        pass
