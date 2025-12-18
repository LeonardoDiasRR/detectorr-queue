"""
Value Object para nome de câmera.
"""


class NameVO:
    """
    Value Object que representa o nome de uma câmera.
    Deve ser uma string não vazia.
    """

    def __init__(self, camera_name: str):
        """
        Inicializa o NameVO.

        :param camera_name: Nome da câmera (string não vazia).
        :raises TypeError: Se camera_name não for uma string.
        :raises ValueError: Se camera_name for vazio ou apenas espaços em branco.
        """
        if not isinstance(camera_name, str):
            raise TypeError(f"camera_name deve ser uma string, recebido: {type(camera_name).__name__}")
        
        camera_name = camera_name.strip()
        
        if not camera_name:
            raise ValueError("camera_name não pode ser vazio ou apenas espaços em branco")
        
        self._value = camera_name

    def value(self) -> str:
        """
        Retorna o valor do nome da câmera.

        :return: Nome da câmera como string.
        """
        return self._value

    def __eq__(self, other) -> bool:
        """Compara dois NameVO por igualdade."""
        if not isinstance(other, NameVO):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Representação string do objeto."""
        return f"NameVO('{self._value}')"

    def __str__(self) -> str:
        """Conversão para string."""
        return self._value
