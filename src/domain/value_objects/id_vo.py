"""
Value Object para ID de câmera.
"""


class IdVO:
    """
    Value Object que representa o ID de uma câmera.
    Deve ser um número inteiro válido.
    """

    def __init__(self, camera_id: int):
        """
        Inicializa o IdVO.

        :param camera_id: ID da câmera (inteiro).
        :raises TypeError: Se camera_id não for um inteiro.
        :raises ValueError: Se camera_id for negativo.
        """
        if not isinstance(camera_id, int):
            raise TypeError(f"camera_id deve ser um inteiro, recebido: {type(camera_id).__name__}")
        
        if camera_id < 0:
            raise ValueError(f"camera_id deve ser não-negativo, recebido: {camera_id}")
        
        self._value = camera_id

    def value(self) -> int:
        """
        Retorna o valor do ID da câmera.

        :return: ID da câmera como inteiro.
        """
        return self._value

    def __eq__(self, other) -> bool:
        """Compara dois IdVO por igualdade."""
        if not isinstance(other, IdVO):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Representação string do objeto."""
        return f"IdVO({self._value})"

    def __str__(self) -> str:
        """Conversão para string."""
        return str(self._value)
