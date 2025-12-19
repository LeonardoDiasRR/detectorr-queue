"""
Async Queue Handler para logging não-bloqueante.

Implementa um handler que enfileira mensagens de log
e as escreve em uma thread separada.
"""

import logging
import queue
import threading
from typing import Optional


class AsyncQueueHandler(logging.Handler):
    """
    Handler que enfileira registros de log para processamento assíncrono.
    
    Em vez de escrever logs bloqueantemente no handler padrão,
    coloca mensagens em uma fila thread-safe e processa em background.
    
    BENEFÍCIO:
    Operações de logging (que podem envolver I/O, formatação cara, etc)
    não bloqueiam a thread crítica de processamento.
    """
    
    def __init__(self, log_queue: queue.Queue):
        """
        Inicializa o handler.
        
        :param log_queue: Queue thread-safe para enfileirar registros.
        """
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Enfileira um registro de log sem bloquear.
        
        :param record: LogRecord a enfileirar.
        """
        try:
            # Formata a mensagem na thread do caller (rápido)
            msg = self.format(record)
            
            # Enfileira sem bloquear (non-blocking)
            try:
                self.log_queue.put_nowait((record.levelname, msg))
            except queue.Full:
                # Fila cheia - descarta mensagem antiga ou descarta nova
                # Para não travar, apenas descarta
                pass
        except Exception:
            # Se erro ao enfileirar, não trava a aplicação
            self.handleError(record)


class AsyncLoggerWorker(threading.Thread):
    """
    Worker thread que processa logs enfileirados.
    
    Lê mensagens da fila e as escreve no handler real.
    """
    
    def __init__(
        self,
        log_queue: queue.Queue,
        handlers: list,
        stop_event: threading.Event,
        name: str = "AsyncLoggerWorker"
    ):
        """
        Inicializa o worker.
        
        :param log_queue: Queue com mensagens de log.
        :param handlers: Handlers reais para escrever (file, console, etc).
        :param stop_event: Event para sinalizar parada.
        :param name: Nome da thread.
        """
        super().__init__(daemon=True, name=name)
        self.log_queue = log_queue
        self.handlers = handlers
        self.stop_event = stop_event
    
    def run(self) -> None:
        """
        Roda o worker até stop_event ser setado.
        
        Processa logs da fila e os escreve nos handlers.
        """
        while not self.stop_event.is_set():
            try:
                # Aguarda log com timeout (responde a stop_event)
                try:
                    level, msg = self.log_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Escreve nos handlers
                for handler in self.handlers:
                    handler.emit_direct(level, msg)
                
            except Exception:
                # Não deixa erros no worker travar a thread
                pass
        
        # Processa logs restantes ao parar
        while not self.log_queue.empty():
            try:
                level, msg = self.log_queue.get_nowait()
                for handler in self.handlers:
                    handler.emit_direct(level, msg)
            except queue.Empty:
                break
            except Exception:
                pass


class RealLogHandler:
    """
    Wrapper para handlers reais (FileHandler, StreamHandler, etc).
    
    Permite escrever logs já formatados.
    """
    
    def __init__(self, handler: logging.Handler):
        """
        Inicializa com um handler real.
        
        :param handler: Handler do logging padrão.
        """
        self.handler = handler
        self.logger = logging.getLogger(handler.__class__.__name__)
    
    def emit_direct(self, level: str, msg: str) -> None:
        """
        Emite uma mensagem já formatada.
        
        :param level: Nível do log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        :param msg: Mensagem formatada.
        """
        try:
            # Cria um LogRecord com a mensagem já formatada
            record = logging.LogRecord(
                name=self.logger.name,
                level=getattr(logging, level),
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None
            )
            self.handler.emit(record)
        except Exception:
            pass
