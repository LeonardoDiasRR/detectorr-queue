"""
Buffer Circular Thread-Safe para Display
Permite comunicação não-bloqueante entre DetectFacesUseCase e DisplayCameraUseCase
"""

import threading
from typing import Optional, Any
from collections import deque


class CircularBuffer:
    """
    Buffer circular thread-safe de tamanho fixo.
    Utilizado para armazenar frames anotados para exibição.
    
    Características:
    - Tamanho fixo (descarta frames antigos quando cheio)
    - Thread-safe (usa lock interno)
    - Operações não-bloqueantes (put_nowait, get_nowait)
    - Isolado da pipeline principal (não afeta performance)
    """
    
    def __init__(self, max_size: int = 5):
        """
        Inicializa buffer circular.
        
        Args:
            max_size: Tamanho máximo do buffer (padrão 5 frames)
        """
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        
    def put_nowait(self, item: Any) -> bool:
        """
        Adiciona item ao buffer sem bloquear.
        
        Se buffer estiver cheio, descarta o frame mais antigo.
        Esta operação NUNCA bloqueia.
        
        Args:
            item: Item a ser adicionado (geralmente um frame anotado)
            
        Returns:
            True se adicionou com sucesso, False caso contrário
        """
        try:
            with self._lock:
                self._buffer.append(item)
            return True
        except Exception:
            return False
            
    def get_nowait(self) -> Optional[Any]:
        """
        Remove e retorna item do buffer sem bloquear.
        
        Se buffer estiver vazio, retorna None.
        Esta operação NUNCA bloqueia.
        
        Returns:
            Item do buffer ou None se vazio
        """
        try:
            with self._lock:
                if len(self._buffer) > 0:
                    return self._buffer.popleft()
                return None
        except Exception:
            return None
            
    def clear(self):
        """Limpa todos os itens do buffer."""
        with self._lock:
            self._buffer.clear()
            
    def size(self) -> int:
        """Retorna número de itens no buffer."""
        with self._lock:
            return len(self._buffer)
            
    def is_empty(self) -> bool:
        """Verifica se buffer está vazio."""
        with self._lock:
            return len(self._buffer) == 0
