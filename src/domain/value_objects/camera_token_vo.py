"""
Value Object para token de câmera.
"""


class CameraTokenVO:
    """
    Value Object que representa o token de autenticação de uma câmera.
    Deve ser uma string não vazia.
    """

    def __init__(self, camera_token: str):
        """
        Inicializa o CameraTokenVO.

        :param camera_token: Token da câmera (string não vazia).
        :raises TypeError: Se camera_token não for uma string.
        :raises ValueError: Se camera_token for vazio ou apenas espaços em branco.
        """
        if not isinstance(camera_token, str):
            raise TypeError(f"camera_token deve ser uma string, recebido: {type(camera_token).__name__}")
        
        camera_token = camera_token.strip()
        
        if not camera_token:
            raise ValueError("camera_token não pode ser vazio ou apenas espaços em branco")
        
        self._value = camera_token

    def value(self) -> str:
        """
        Retorna o valor do token da câmera.

        :return: Token da câmera como string.
        """
        return self._value

    def __eq__(self, other) -> bool:
        """Compara dois CameraTokenVO por igualdade."""
        if not isinstance(other, CameraTokenVO):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Representação string do objeto."""
        return f"CameraTokenVO('{self._value[:10]}...')"  # Mascara parte do token por segurança

    def __str__(self) -> str:
        """Conversão para string."""
        return self._value
