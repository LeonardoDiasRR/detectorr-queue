"""
Entidade Camera do domínio.
"""

from typing import Dict, Any
from src.domain.value_objects import IdVO, NameVO, CameraTokenVO, CameraSourceVO


class Camera:
    """
    Entidade que representa uma câmera no sistema.
    """

    def __init__(
        self,
        camera_id: IdVO,
        camera_name: NameVO,
        camera_token: CameraTokenVO,
        source: CameraSourceVO,
        active: bool = True
    ):
        """
        Inicializa a entidade Camera.

        :param camera_id: ID da câmera (IdVO).
        :param camera_name: Nome da câmera (NameVO).
        :param camera_token: Token de autenticação da câmera (CameraTokenVO).
        :param source: URL RTSP da câmera (CameraSourceVO).
        :param active: Se a câmera está ativa (bool, padrão: True).
        :raises TypeError: Se algum parâmetro não for do tipo esperado.
        """
        if not isinstance(camera_id, IdVO):
            raise TypeError(f"camera_id deve ser IdVO, recebido: {type(camera_id).__name__}")
        
        if not isinstance(camera_name, NameVO):
            raise TypeError(f"camera_name deve ser NameVO, recebido: {type(camera_name).__name__}")
        
        if not isinstance(camera_token, CameraTokenVO):
            raise TypeError(f"camera_token deve ser CameraTokenVO, recebido: {type(camera_token).__name__}")
        
        if not isinstance(source, CameraSourceVO):
            raise TypeError(f"source deve ser CameraSourceVO, recebido: {type(source).__name__}")
        
        if not isinstance(active, bool):
            raise TypeError(f"active deve ser bool, recebido: {type(active).__name__}")
        
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._camera_token = camera_token
        self._source = source
        self._active = active

    @property
    def camera_id(self) -> IdVO:
        """Retorna o ID da câmera."""
        return self._camera_id

    @property
    def camera_name(self) -> NameVO:
        """Retorna o nome da câmera."""
        return self._camera_name

    @property
    def camera_token(self) -> CameraTokenVO:
        """Retorna o token da câmera."""
        return self._camera_token

    @property
    def source(self) -> CameraSourceVO:
        """Retorna a URL RTSP da câmera."""
        return self._source

    @property
    def active(self) -> bool:
        """Retorna se a câmera está ativa."""
        return self._active

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a entidade para um dicionário.

        :return: Dicionário com os dados da câmera.
        """
        return {
            'id': self._camera_id.value(),
            'name': self._camera_name.value(),
            'token': self._camera_token.value(),
            'source': self._source.value(),
            'active': self._active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Camera':
        """
        Cria uma instância de Camera a partir de um dicionário.

        :param data: Dicionário com os dados da câmera.
        :return: Instância de Camera.
        :raises KeyError: Se alguma chave obrigatória estiver ausente.
        """
        return cls(
            camera_id=IdVO(data['id']),
            camera_name=NameVO(data['name']),
            camera_token=CameraTokenVO(data['token']),
            source=CameraSourceVO(data['source']),
            active=data.get('active', True)
        )

    def __eq__(self, other) -> bool:
        """Compara duas câmeras por igualdade (baseado no ID)."""
        if not isinstance(other, Camera):
            return False
        return self._camera_id == other._camera_id

    def __hash__(self) -> int:
        """Retorna o hash da câmera (baseado no ID)."""
        return hash(self._camera_id)

    def __repr__(self) -> str:
        """Representação string da câmera."""
        return f"Camera(id={self._camera_id.value()}, name='{self._camera_name.value()}')"

    def __str__(self) -> str:
        """Conversão para string."""
        return f"Camera {self._camera_id.value()}: {self._camera_name.value()}"
