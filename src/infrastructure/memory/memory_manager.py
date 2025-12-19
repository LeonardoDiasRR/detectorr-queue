"""
Gerenciador de Memória com Garbage Collection Assíncrono.

Executa garbage collection em uma thread separada para não bloquear
as threads críticas de processamento (detecção, tracking, envio).

DESIGN:
- GC roda a cada N segundos em background
- Não bloqueia loops principais
- Sincroniza com GPU se necessário
- Graceful shutdown ao parar aplicação
"""

import gc
import threading
import time
import logging
from typing import Optional

try:
    import torch
except ImportError:
    torch = None


class MemoryManager:
    """
    Gerenciador de memória com garbage collection assíncrono.
    
    PROBLEMA RESOLVIDO:
    Executar gc.collect() nos hot paths (detecção, tracking) bloqueia 
    a execução por 100-500ms a cada iteração, reduzindo throughput em 85%.
    
    SOLUÇÃO:
    GC em thread separada que roda a cada N segundos sem bloquear
    as threads críticas.
    
    BENEFÍCIOS:
    - ✅ Sem bloqueio dos hot paths
    - ✅ Memória mantida sob controle durante execução
    - ✅ GPU cache liberado periodicamente
    - ✅ Graceful shutdown
    
    EXEMPLO DE USO:
    ```python
    # Criar e iniciar
    memory_manager = MemoryManager(gc_interval_seconds=5.0)
    memory_manager.start()
    
    # ... Aplicação rodando ...
    
    # Parar
    memory_manager.stop()
    ```
    """
    
    def __init__(self, gc_interval_seconds: float = 5.0, logger_name: str = "MemoryManager"):
        """
        Inicializa o gerenciador de memória.
        
        :param gc_interval_seconds: Intervalo em segundos entre GC execuções.
                                   Padrão: 5 segundos
                                   - Menor (1-2s): Mais GC, menos memória acumulada, mais overhead
                                   - Maior (10-20s): Menos GC, mais memória acumulada, menos overhead
                                   - 5s: Balanço entre memória e performance
        :param logger_name: Nome do logger para mensagens.
        """
        self.gc_interval = gc_interval_seconds
        self.logger = logging.getLogger(logger_name)
        
        self._stop_event = threading.Event()
        self._gc_thread: Optional[threading.Thread] = None
        self._is_running = False
        
        # Estatísticas
        self._gc_count = 0
        self._objects_collected = 0
    
    def start(self) -> None:
        """
        Inicia a thread de garbage collection assíncrono.
        
        Seguro chamar múltiplas vezes - ignora se já está rodando.
        """
        if self._is_running:
            self.logger.warning("MemoryManager já está rodando")
            return
        
        self._is_running = True
        self._stop_event.clear()
        
        self._gc_thread = threading.Thread(
            target=self._gc_worker,
            daemon=True,
            name="MemoryManagerGC"
        )
        self._gc_thread.start()
        self.logger.info(
            f"✓ MemoryManager iniciado (intervalo: {self.gc_interval}s)"
        )
    
    def stop(self) -> None:
        """
        Para a thread de garbage collection assíncrono.
        
        Aguarda no máximo 5 segundos para thread terminar.
        Seguro chamar múltiplas vezes.
        """
        if not self._is_running:
            return
        
        self._stop_event.set()
        self.logger.info("Parando MemoryManager...")
        
        if self._gc_thread:
            self._gc_thread.join(timeout=5.0)
            if self._gc_thread.is_alive():
                self.logger.warning("MemoryManager thread não terminou em 5s")
        
        self._is_running = False
        self.logger.info(
            f"✓ MemoryManager parado | "
            f"GC executado {self._gc_count} vezes | "
            f"Objetos coletados: {self._objects_collected}"
        )
    
    def _gc_worker(self) -> None:
        """
        Worker thread que executa garbage collection periodicamente.
        
        Roda continuamente até stop_event ser setado.
        Não levanta exceções - apenas loga erros.
        """
        self.logger.debug(f"GC worker thread iniciado")
        
        while not self._stop_event.is_set():
            try:
                # Aguarda intervalo (respeitando stop_event)
                self._stop_event.wait(timeout=self.gc_interval)
                
                # Se foi setado, sai do loop
                if self._stop_event.is_set():
                    break
                
                # Executa garbage collection
                self._perform_gc()
                
            except Exception as e:
                self.logger.error(f"Erro no GC worker: {e}", exc_info=True)
        
        self.logger.debug("GC worker thread finalizado")
    
    def _perform_gc(self) -> None:
        """
        Executa garbage collection e libera recursos da GPU se necessário.
        
        IMPORTANTE: Executado em thread separada, não bloqueia aplicação.
        """
        try:
            # Executa coleta de garbage
            collected = gc.collect()
            self._gc_count += 1
            self._objects_collected += collected
            
            self.logger.debug(
                f"GC #{self._gc_count}: {collected} objetos coletados"
            )
            
            # Libera cache GPU se disponível
            self._free_gpu_cache()
            
        except Exception as e:
            self.logger.error(f"Erro durante gc.collect(): {e}", exc_info=True)
    
    def _free_gpu_cache(self) -> None:
        """
        Libera cache de GPU se PyTorch estiver disponível.
        
        Seguro chamar mesmo se GPU não estiver disponível.
        """
        if torch is None:
            return
        
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
                # Sincroniza com GPU para garantir que operação foi completada
                torch.cuda.synchronize()
                
                self.logger.debug("GPU cache liberado")
        except Exception as e:
            self.logger.warning(f"Erro ao liberar GPU cache: {e}")
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas de coleta de garbage.
        
        :return: Dicionário com estatísticas.
        """
        return {
            "is_running": self._is_running,
            "gc_count": self._gc_count,
            "objects_collected": self._objects_collected,
            "gc_interval": self.gc_interval
        }
    
    def __repr__(self) -> str:
        state = "ativo" if self._is_running else "inativo"
        return (
            f"MemoryManager(state={state}, interval={self.gc_interval}s, "
            f"gc_count={self._gc_count}, objects_collected={self._objects_collected})"
        )
