"""
Value Object para representar um índice de confiança.
"""

import numbers


class ConfidenceVO:
    """
    Value Object que representa um índice de confiança entre 0.0 e 1.0.
    """

    def __init__(self, confidence: float):
        """
        Inicializa o VO de confiança.

        :param confidence: Valor de confiança entre 0.0 e 1.0.
        :raises TypeError: Se confidence não for um número.
        :raises ValueError: Se confidence estiver fora do intervalo [0.0, 1.0].
        """
        # Aceita qualquer tipo numérico (int, float, numpy.float32, etc)
        if not isinstance(confidence, numbers.Number):
            raise TypeError(f"confidence deve ser um número, recebido: {type(confidence).__name__}")
        
        # Converte para float nativo do Python
        confidence = float(confidence)
        
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence deve estar entre 0.0 e 1.0, recebido: {confidence}")
        
        self._confidence = confidence

    def value(self) -> float:
        """Retorna o valor da confiança."""
        return self._confidence

    def percentage(self) -> float:
        """Retorna a confiança como percentual (0-100)."""
        return self._confidence * 100.0

    def is_high(self, threshold: float = 0.7) -> bool:
        """
        Verifica se a confiança é alta.

        :param threshold: Limiar para considerar alta confiança (padrão: 0.7).
        :return: True se a confiança for >= threshold.
        """
        return self._confidence >= threshold

    def __eq__(self, other) -> bool:
        """Verifica igualdade baseada no valor."""
        if not isinstance(other, ConfidenceVO):
            return False
        return abs(self._confidence - other._confidence) < 1e-9

    def __lt__(self, other) -> bool:
        """Operador menor que."""
        if not isinstance(other, ConfidenceVO):
            return NotImplemented
        return self._confidence < other._confidence

    def __le__(self, other) -> bool:
        """Operador menor ou igual."""
        if not isinstance(other, ConfidenceVO):
            return NotImplemented
        return self._confidence <= other._confidence

    def __gt__(self, other) -> bool:
        """Operador maior que."""
        if not isinstance(other, ConfidenceVO):
            return NotImplemented
        return self._confidence > other._confidence

    def __ge__(self, other) -> bool:
        """Operador maior ou igual."""
        if not isinstance(other, ConfidenceVO):
            return NotImplemented
        return self._confidence >= other._confidence

    def __hash__(self) -> int:
        """Retorna hash baseado no valor."""
        return hash(self._confidence)

    def __repr__(self) -> str:
        """Representação técnica do VO."""
        return f"ConfidenceVO({self._confidence:.4f})"

    def __str__(self) -> str:
        """Representação legível do VO."""
        return f"{self._confidence:.4f}"
