"""
Fila thread-safe para eventos de detecção facial.
"""

import queue
from typing import Optional
from src.domain.entities import Event


class EventQueue:
    """Fila thread-safe para armazenar eventos de detecção."""
    
    def __init__(self, maxsize: int = 128):
        """
        Inicializa a fila de eventos.
        
        :param maxsize: Tamanho máximo da fila.
        """
        self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, event: Event, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Adiciona um evento à fila.
        
        :param event: Evento a ser adicionado.
        :param block: Se True, bloqueia até ter espaço.
        :param timeout: Timeout em segundos (None = infinito).
        :return: True se adicionado com sucesso, False se fila cheia (quando block=False).
        """
        try:
            self._queue.put(event, block=block, timeout=timeout)
            return True
        except queue.Full:
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Event]:
        """
        Remove e retorna um evento da fila.
        
        :param block: Se True, bloqueia até ter item disponível.
        :param timeout: Timeout em segundos (None = infinito).
        :return: Evento ou None se fila vazia (quando block=False).
        """
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def qsize(self) -> int:
        """Retorna o tamanho aproximado da fila."""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Verifica se a fila está vazia."""
        return self._queue.empty()
    
    def full(self) -> bool:
        """Verifica se a fila está cheia."""
        return self._queue.full()
    
    def task_done(self):
        """Indica que uma tarefa foi concluída."""
        self._queue.task_done()
    
    def join(self):
        """Bloqueia até que todos os itens sejam processados."""
        self._queue.join()
