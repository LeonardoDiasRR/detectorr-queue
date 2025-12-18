"""
Value Object para landmarks faciais.
"""

from typing import Optional
import numpy as np


class LandmarksVO:
    """
    Value Object que representa landmarks (pontos-chave) faciais.
    Os landmarks são armazenados como um array numpy.
    """

    def __init__(self, landmarks: Optional[np.ndarray]):
        """
        Inicializa o LandmarksVO.

        :param landmarks: Array numpy com os landmarks faciais ou None.
        :raises TypeError: Se landmarks não for np.ndarray ou None.
        :raises ValueError: Se landmarks tiver formato inválido.
        """
        if landmarks is not None:
            if not isinstance(landmarks, np.ndarray):
                raise TypeError(f"landmarks deve ser np.ndarray ou None, recebido: {type(landmarks).__name__}")
            
            # Landmarks devem ter pelo menos 2 dimensões (pontos e coordenadas)
            if landmarks.ndim < 2:
                raise ValueError(f"landmarks deve ter pelo menos 2 dimensões, recebido: {landmarks.ndim}")
            
            # A última dimensão deve ser 2 (x, y) ou 3 (x, y, z)
            if landmarks.shape[-1] not in (2, 3):
                raise ValueError(
                    f"Última dimensão de landmarks deve ser 2 (x,y) ou 3 (x,y,z), "
                    f"recebido: {landmarks.shape[-1]}"
                )
            
            # Cria uma cópia para evitar mutação externa
            self._value = landmarks.copy()
        else:
            self._value = None

    def value(self) -> Optional[np.ndarray]:
        """
        Retorna o valor dos landmarks.

        :return: Array numpy com landmarks ou None.
        """
        if self._value is not None:
            return self._value.copy()  # Retorna cópia para evitar mutação
        return None

    def is_empty(self) -> bool:
        """
        Verifica se os landmarks estão vazios (None).

        :return: True se landmarks for None.
        """
        return self._value is None

    @property
    def num_points(self) -> int:
        """
        Retorna o número de pontos landmarks.

        :return: Número de pontos ou 0 se vazio.
        """
        if self._value is None:
            return 0
        return self._value.shape[0]

    @property
    def shape(self) -> Optional[tuple]:
        """
        Retorna o shape do array de landmarks.

        :return: Shape do array ou None se vazio.
        """
        if self._value is None:
            return None
        return self._value.shape

    def to_list(self) -> Optional[list]:
        """
        Converte landmarks para lista.

        :return: Lista com landmarks ou None.
        """
        if self._value is None:
            return None
        return self._value.tolist()

    def __eq__(self, other) -> bool:
        """Compara dois LandmarksVO por igualdade."""
        if not isinstance(other, LandmarksVO):
            return False
        
        # Ambos vazios
        if self._value is None and other._value is None:
            return True
        
        # Um vazio e outro não
        if self._value is None or other._value is None:
            return False
        
        # Compara arrays
        return np.array_equal(self._value, other._value)

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        if self._value is None:
            return hash(None)
        return hash(self._value.tobytes())

    def __repr__(self) -> str:
        """Representação string do objeto."""
        if self._value is None:
            return "LandmarksVO(None)"
        return f"LandmarksVO(shape={self.shape}, points={self.num_points})"

    def __str__(self) -> str:
        """Conversão para string."""
        if self._value is None:
            return "No landmarks"
        return f"{self.num_points} landmarks points"
