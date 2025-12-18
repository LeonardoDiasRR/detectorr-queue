"""
Fila thread-safe para frames capturados das câmeras.
"""

import queue
from typing import Optional
from src.domain.entities import Frame


class FrameQueue:
    """Fila thread-safe para armazenar frames."""
    
    def __init__(self, maxsize: int = 128):
        """
        Inicializa a fila de frames.
        
        :param maxsize: Tamanho máximo da fila.
        """
        self._queue = queue.Queue(maxsize=maxsize)
    
    def put(self, frame: Frame, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Adiciona um frame à fila.
        
        :param frame: Frame a ser adicionado.
        :param block: Se True, bloqueia até ter espaço.
        :param timeout: Timeout em segundos (None = infinito).
        :return: True se adicionado com sucesso, False se fila cheia (quando block=False).
        """
        try:
            self._queue.put(frame, block=block, timeout=timeout)
            return True
        except queue.Full:
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Frame]:
        """
        Remove e retorna um frame da fila.
        
        :param block: Se True, bloqueia até ter item disponível.
        :param timeout: Timeout em segundos (None = infinito).
        :return: Frame ou None se fila vazia (quando block=False).
        """
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def get_batch(self, batch_size: int, timeout: float = 0.1) -> list[Frame]:
        """
        Obtém um lote de frames da fila.
        
        :param batch_size: Tamanho máximo do lote.
        :param timeout: Timeout em segundos para aguardar cada frame.
        :return: Lista de frames (pode ser menor que batch_size).
        """
        frames = []
        for _ in range(batch_size):
            frame = self.get(block=True, timeout=timeout)
            if frame is None:
                break
            frames.append(frame)
        return frames
    
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
