"""
Value Object para bounding box.
"""

from typing import Tuple


class BboxVO:
    """
    Value Object que representa um bounding box (caixa delimitadora).
    Formato: (x1, y1, x2, y2) onde (x1, y1) é o canto superior esquerdo
    e (x2, y2) é o canto inferior direito.
    """

    def __init__(self, bbox: Tuple[int, int, int, int]):
        """
        Inicializa o BboxVO.

        :param bbox: Tupla com coordenadas (x1, y1, x2, y2).
        :raises TypeError: Se bbox não for uma tupla.
        :raises ValueError: Se bbox não tiver exatamente 4 elementos ou se as coordenadas forem inválidas.
        """
        if not isinstance(bbox, tuple):
            raise TypeError(f"bbox deve ser uma tupla, recebido: {type(bbox).__name__}")
        
        if len(bbox) != 4:
            raise ValueError(f"bbox deve ter exatamente 4 elementos, recebido: {len(bbox)}")
        
        if not all(isinstance(coord, (int, float)) for coord in bbox):
            raise TypeError("Todas as coordenadas do bbox devem ser numéricas")
        
        x1, y1, x2, y2 = bbox
        
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            raise ValueError(f"Coordenadas do bbox não podem ser negativas: {bbox}")
        
        if x2 <= x1:
            raise ValueError(f"x2 ({x2}) deve ser maior que x1 ({x1})")
        
        if y2 <= y1:
            raise ValueError(f"y2 ({y2}) deve ser maior que y1 ({y1})")
        
        # Converte para inteiros
        self._value = (int(x1), int(y1), int(x2), int(y2))

    def value(self) -> Tuple[int, int, int, int]:
        """
        Retorna o valor do bounding box.

        :return: Tupla com coordenadas (x1, y1, x2, y2).
        """
        return self._value

    @property
    def x1(self) -> int:
        """Retorna a coordenada x1 (esquerda)."""
        return self._value[0]

    @property
    def y1(self) -> int:
        """Retorna a coordenada y1 (topo)."""
        return self._value[1]

    @property
    def x2(self) -> int:
        """Retorna a coordenada x2 (direita)."""
        return self._value[2]

    @property
    def y2(self) -> int:
        """Retorna a coordenada y2 (base)."""
        return self._value[3]

    @property
    def width(self) -> int:
        """Retorna a largura do bounding box."""
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        """Retorna a altura do bounding box."""
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        """Retorna a área do bounding box."""
        return self.width * self.height

    def to_list(self) -> list:
        """Retorna o bbox como lista [x1, y1, x2, y2]."""
        return list(self._value)

    def __eq__(self, other) -> bool:
        """Compara dois BboxVO por igualdade."""
        if not isinstance(other, BboxVO):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Retorna o hash do valor."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Representação string do objeto."""
        return f"BboxVO({self._value})"

    def __str__(self) -> str:
        """Conversão para string."""
        return f"({self.x1}, {self.y1}, {self.x2}, {self.y2})"
