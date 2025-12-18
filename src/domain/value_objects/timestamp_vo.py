"""
Value Object para timestamp.
"""

from datetime import datetime


class TimestampVO:
    """
    Value Object que representa um timestamp (carimbo de data/hora).
    """

    def __init__(self, timestamp: datetime):
        """
        Inicializa o TimestampVO.

        :param timestamp: Timestamp como objeto datetime.
        :raises TypeError: Se timestamp não for datetime.
        """
        if not isinstance(timestamp, datetime):
            raise TypeError(f"timestamp deve ser datetime, recebido: {type(timestamp).__name__}")
        
        self._value = timestamp

    def value(self) -> datetime:
        """
        Retorna o valor do timestamp.

        :return: Timestamp como datetime.
        """
        return self._value

    def iso_format(self) -> str:
        """
        Retorna o timestamp no formato ISO 8601.

        :return: String no formato ISO 8601.
        """
        return self._value.isoformat()

    def timestamp(self) -> float:
        """
        Retorna o timestamp Unix (segundos desde epoch).

        :return: Timestamp Unix como float.
        """
        return self._value.timestamp()

    def __eq__(self, other) -> bool:
        """Compara dois TimestampVO por igualdade."""
        if not isinstance(other, TimestampVO):
            return False
        return self._value == other._value

    def __lt__(self, other) -> bool:
        """Compara se este TimestampVO é anterior a outro."""
        if not isinstance(other, TimestampVO):
            return NotImplemented
        return self._value < other._value

    def __le__(self, other) -> bool:
        """Compara se este TimestampVO é anterior ou igual a outro."""
        if not isinstance(other, TimestampVO):
            return NotImplemented
        return self._value <= other._value

    def __gt__(self, other) -> bool:
        """Compara se este TimestampVO é posterior a outro."""
        if not isinstance(other, TimestampVO):
            return NotImplemented
        return self._value > other._value

    def __ge__(self, other) -> bool:
        """Compara se este TimestampVO é posterior ou igual a outro."""
        if not isinstance(other, TimestampVO):
            return NotImplemented
        return self._value >= other._value

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Representação string do objeto."""
        return f"TimestampVO('{self._value.isoformat()}')"

    def __str__(self) -> str:
        """Conversão para string."""
        return self._value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @classmethod
    def now(cls) -> 'TimestampVO':
        """
        Cria um TimestampVO com o timestamp atual.

        :return: Nova instância de TimestampVO.
        """
        return cls(datetime.now())
