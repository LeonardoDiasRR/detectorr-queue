"""
Value Object para representar um frame completo (ndarray).
"""

import numpy as np


class FullFrameVO:
    """
    Value Object que encapsula um frame completo como ndarray.
    Garante imutabilidade e validação do array numpy.
    """

    def __init__(self, ndarray: np.ndarray, copy: bool = False):
        """
        Inicializa o FullFrameVO.

        :param ndarray: Array numpy representando a imagem do frame.
        :param copy: Se True, faz cópia (seguro). Se False, usa referência (rápido, otimizado).
        :raises TypeError: Se ndarray não for np.ndarray.
        :raises ValueError: Se ndarray for vazio ou inválido.
        """
        if not isinstance(ndarray, np.ndarray):
            raise TypeError(f"ndarray deve ser np.ndarray, recebido: {type(ndarray).__name__}")
        
        if ndarray.size == 0:
            raise ValueError("ndarray não pode ser vazio")
        
        if ndarray.ndim < 2:
            raise ValueError(f"ndarray deve ter pelo menos 2 dimensões, recebido: {ndarray.ndim}")
        
        # OTIMIZAÇÃO: Copia apenas se necessário (default=False para performance)
        if copy:
            self._ndarray = ndarray.copy()
        else:
            # Usa referência direta - MUITO mais rápido, sem overhead de memória
            self._ndarray = ndarray
        
        self._ndarray.flags.writeable = False  # Torna o array read-only

    def value(self, copy: bool = True) -> np.ndarray:
        """
        Retorna o array numpy.
        
        :param copy: Se True, retorna cópia. Se False, retorna referência read-only.
        :return: Array numpy (cópia ou referência).
        """
        return self._ndarray.copy() if copy else self._ndarray
    
    @property
    def ndarray_readonly(self) -> np.ndarray:
        """
        Acesso direto read-only ao ndarray - ZERO cópias.
        Usar quando não precisa modificar o array.
        
        :return: Referência read-only ao ndarray.
        """
        return self._ndarray

    @property
    def shape(self) -> tuple:
        """Retorna as dimensões do frame."""
        return self._ndarray.shape

    @property
    def height(self) -> int:
        """Retorna a altura do frame."""
        return self._ndarray.shape[0]

    @property
    def width(self) -> int:
        """Retorna a largura do frame."""
        return self._ndarray.shape[1]

    @property
    def channels(self) -> int:
        """Retorna o número de canais do frame (ou 1 se grayscale)."""
        return self._ndarray.shape[2] if self._ndarray.ndim == 3 else 1

    def __eq__(self, other) -> bool:
        """Compara dois FullFrameVO por igualdade."""
        if not isinstance(other, FullFrameVO):
            return False
        return np.array_equal(self._ndarray, other._ndarray)

    def __hash__(self) -> int:
        """Retorna o hash do FullFrameVO."""
        # Hash baseado no shape e alguns pixels para performance
        return hash((self._ndarray.shape, self._ndarray.tobytes()[:1000]))

    def __repr__(self) -> str:
        """Representação string do FullFrameVO."""
        return f"FullFrameVO(shape={self.shape}, dtype={self._ndarray.dtype})"

    def __str__(self) -> str:
        """Conversão para string."""
        return f"FullFrame {self.width}x{self.height}x{self.channels}"
