"""
Value Object para fonte/URL da câmera.
"""

import re
from typing import Any


class CameraSourceVO:
    """
    Value Object que representa a fonte/URL RTSP de uma câmera.
    Valida que a string não está vazia e segue o formato de URL RTSP.
    """

    # Padrão regex para validar URLs RTSP
    RTSP_PATTERN = re.compile(
        r'^rtsp://'  # Deve começar com rtsp://
        r'(?:'  # Grupo não capturante para credenciais opcionais
        r'([^:@]+)'  # Username
        r'(?::([^@]+))?'  # Password opcional
        r'@)?'  # @ após credenciais
        r'([^:/]+)'  # Host (IP ou domínio)
        r'(?::(\d+))?'  # Porta opcional
        r'(/.*)?$',  # Caminho opcional
        re.IGNORECASE
    )

    def __init__(self, source: str):
        """
        Inicializa o CameraSourceVO.

        :param source: URL RTSP da câmera.
        :raises ValueError: Se a fonte estiver vazia ou não for uma URL RTSP válida.
        :raises TypeError: Se source não for uma string.
        """
        if not isinstance(source, str):
            raise TypeError(f"source deve ser string, recebido: {type(source).__name__}")
        
        if not source or not source.strip():
            raise ValueError("source não pode ser vazio")
        
        source = source.strip()
        
        if not self.RTSP_PATTERN.match(source):
            raise ValueError(f"source deve ser uma URL RTSP válida, recebido: {source}")
        
        self._source = source

    def value(self) -> str:
        """Retorna o valor da fonte."""
        return self._source

    def __eq__(self, other: Any) -> bool:
        """Compara dois CameraSourceVO por igualdade."""
        if not isinstance(other, CameraSourceVO):
            return False
        return self._source == other._source

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._source)

    def __repr__(self) -> str:
        """Representação string do VO."""
        # Oculta credenciais na representação
        masked_source = self._mask_credentials(self._source)
        return f"CameraSourceVO('{masked_source}')"

    def __str__(self) -> str:
        """Conversão para string."""
        return self._source

    @staticmethod
    def _mask_credentials(url: str) -> str:
        """
        Mascara credenciais na URL para exibição segura.
        
        :param url: URL RTSP com possíveis credenciais.
        :return: URL com credenciais mascaradas.
        """
        match = CameraSourceVO.RTSP_PATTERN.match(url)
        if match and match.group(1):  # Se houver username
            # Substitui credenciais por ***
            return re.sub(r'://[^@]+@', '://***:***@', url)
        return url

    def get_masked_source(self) -> str:
        """
        Retorna a URL com credenciais mascaradas.
        
        :return: URL RTSP com credenciais ocultas.
        """
        return self._mask_credentials(self._source)
