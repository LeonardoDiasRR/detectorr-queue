"""
AsyncLogger - Logger não-bloqueante para aplicação.

Executa logging em thread separada para não bloquear
operações críticas de processamento.

PROBLEMA RESOLVIDO:
logging.info(), logger.debug(), etc fazem formatação de strings
e I/O, o que pode levar 5-50ms por log. Em 60 fps com 60 detecções/s,
isso é MUITO bloqueante.

SOLUÇÃO:
Enfileirar logs em uma queue thread-safe e processá-los em background.
Isso permite que a thread crítica continue processando sem esperar.
"""

import logging
import queue
import threading
from typing import Optional


class AsyncLogger:
    """
    Logger assíncrono que não bloqueia threads críticas.
    
    Enfileira mensagens de log e as processa em uma thread separada.
    
    BENEFÍCIO:
    Operações de logging não bloqueiam o hot path.
    Melhoria esperada: +30% throughput
    
    EXEMPLO:
    ```python
    # Criar logger assíncrono
    async_logger = AsyncLogger("myapp")
    async_logger.start()
    
    logger = async_logger.get_logger(__name__)
    
    # Usar normalmente
    logger.info(f"Processado {count} eventos")  # Não bloqueia!
    
    # Parar ao finalizar
    async_logger.stop()
    ```
    """
    
    def __init__(
        self,
        name: str,
        queue_size: int = 10000,
        level: int = logging.INFO
    ):
        """
        Inicializa o AsyncLogger.
        
        :param name: Nome da aplicação/logger.
        :param queue_size: Tamanho máximo da fila de logs.
        :param level: Nível mínimo de log a processar.
        """
        self.name = name
        self.queue_size = queue_size
        self.level = level
        
        # Fila thread-safe para enfileirar logs
        self._log_queue: queue.Queue = queue.Queue(maxsize=queue_size)
        
        # Event para sinalizar parada
        self._stop_event = threading.Event()
        
        # Logger raiz
        self._root_logger = logging.getLogger(name)
        self._root_logger.setLevel(level)
        
        # Handlers reais (console, arquivo, etc)
        self._real_handlers = []
        
        # Worker thread
        self._worker_thread: Optional[threading.Thread] = None
        self._is_running = False
    
    def start(self) -> None:
        """
        Inicia o AsyncLogger com thread worker.
        
        Cria handlers para console e arquivo (padrão).
        Inicia thread de processamento de logs.
        """
        if self._is_running:
            return
        
        # Configura handlers padrão (console)
        self._setup_default_handlers()
        
        # Inicia worker thread
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._log_worker,
            daemon=True,
            name="AsyncLoggerWorker"
        )
        self._worker_thread.start()
        
        self._is_running = True
        self._root_logger.info(f"✓ AsyncLogger iniciado (queue size: {self.queue_size})")
    
    def stop(self) -> None:
        """
        Para o AsyncLogger gracefully.
        
        Processa logs restantes e para a worker thread.
        """
        if not self._is_running:
            return
        
        self._root_logger.info("Parando AsyncLogger...")
        self._stop_event.set()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                self._root_logger.warning("Worker thread não terminou em 5s")
        
        self._is_running = False
        self._root_logger.info("✓ AsyncLogger parado")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtém um logger que usa async queue.
        
        :param name: Nome do logger (tipicamente __name__).
        :return: Logger configurado com AsyncQueueHandler.
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        
        # Remove handlers antigos
        logger.handlers.clear()
        
        # Adiciona handler assíncrono
        async_handler = AsyncQueueHandler(self._log_queue)
        async_handler.setLevel(self.level)
        
        # Formata para mostrar level e mensagem
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        async_handler.setFormatter(formatter)
        
        logger.addHandler(async_handler)
        logger.propagate = False  # Não propaga para logger raiz
        
        return logger
    
    def _setup_default_handlers(self) -> None:
        """
        Configura handlers padrão (console).
        
        Estes handlers receberão logs processados pela worker thread.
        """
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self._real_handlers.append(console_handler)
        self._root_logger.addHandler(console_handler)
    
    def _log_worker(self) -> None:
        """
        Worker que processa logs da fila.
        
        Roda até stop_event ser setado.
        """
        while not self._stop_event.is_set():
            try:
                # Aguarda log com timeout
                try:
                    level, msg = self._log_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Escreve nos handlers reais
                for handler in self._real_handlers:
                    try:
                        # Emite como INFO (a formatação já inclui level)
                        record = logging.LogRecord(
                            name=self.name,
                            level=getattr(logging, level),
                            pathname="",
                            lineno=0,
                            msg=msg,
                            args=(),
                            exc_info=None
                        )
                        handler.emit(record)
                    except Exception:
                        pass
                
            except Exception:
                pass
        
        # Processa logs restantes ao parar
        while not self._log_queue.empty():
            try:
                level, msg = self._log_queue.get_nowait()
                for handler in self._real_handlers:
                    try:
                        record = logging.LogRecord(
                            name=self.name,
                            level=getattr(logging, level),
                            pathname="",
                            lineno=0,
                            msg=msg,
                            args=(),
                            exc_info=None
                        )
                        handler.emit(record)
                    except Exception:
                        pass
            except queue.Empty:
                break


class AsyncQueueHandler(logging.Handler):
    """
    Handler que enfileira registros para processamento assíncrono.
    
    Não bloqueia a thread de origem.
    """
    
    def __init__(self, log_queue: queue.Queue):
        """
        Inicializa o handler.
        
        :param log_queue: Queue para enfileirar logs.
        """
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Enfileira um registro sem bloquear.
        
        :param record: LogRecord a enfileirar.
        """
        try:
            # Formata mensagem (rápido na thread do caller)
            msg = self.format(record)
            
            # Enfileira sem bloquear
            try:
                self.log_queue.put_nowait((record.levelname, msg))
            except queue.Full:
                # Fila cheia - descarta para não travar
                pass
        except Exception:
            self.handleError(record)
