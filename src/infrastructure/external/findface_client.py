"""
Factory para criar cliente FindFace Multi.
"""

from src.infrastructure.clients import FindfaceMulti
from src.infrastructure.config.settings import FindFaceConfig


def create_findface_client(config: FindFaceConfig) -> FindfaceMulti:
    """
    Cria e retorna uma instância configurada do cliente FindFace Multi.
    
    :param config: Configuração do FindFace.
    :return: Cliente FindfaceMulti autenticado.
    """
    return FindfaceMulti(
        url_base=config.url_base,
        user=config.user,
        password=config.password,
        uuid=config.uuid
    )
