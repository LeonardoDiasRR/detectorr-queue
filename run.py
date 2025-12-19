"""
Script principal para executar a aplicação de detecção facial.

Fluxo da aplicação:
1. Lê configurações do config.yaml e .env
2. Conecta ao FindFace e obtém câmeras ativas
3. Inicia workers de detecção (YOLO + ByteTrack)
4. Inicia gerenciador de tracks
5. Inicia workers de envio ao FindFace
6. Inicia captura de streams RTSP
7. Aguarda sinal de parada (Ctrl+C ou SIGTERM)
8. Finaliza gracefully processando todas as filas
"""

import sys
import logging
from pathlib import Path

# Adiciona diretório raiz ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config.config_loader import ConfigLoader
from src.infrastructure.clients import FindfaceMulti
from src.infrastructure.repositories import CameraRepositoryFindface
from src.infrastructure.logging import AsyncLogger
from src.infrastructure.clients import FindfaceMulti, FindfaceMultiAsync
from src.application.orchestrator import ApplicationOrchestrator


def setup_logging(log_config):
    """
    Configura sistema de logging assíncrono.
    
    :param log_config: Configurações de logging.
    """
    # Define arquivo de log (será truncado a cada execução)
    log_file = project_root / "application.log"
    
    # Cria e inicia AsyncLogger
    async_logger = AsyncLogger(
        "detectorr-queue",
        queue_size=10000,
        level=getattr(logging, log_config.level.upper()),
        log_file=str(log_file)  # Arquivo será limpo (mode='w') a cada start
    )
    async_logger.start()
    
    # Retorna logger assíncrono para uso na aplicação
    return async_logger


def main():
    """Função principal da aplicação."""
    async_logger = None
    orchestrator = None
    findface_client = None
    findface_async_wrapper = None
    try:
        # Carrega configurações
        print("Carregando configurações...")
        settings = ConfigLoader.load()
        
        # Configura logging assíncrono
        async_logger = setup_logging(settings.logging)
        logger = async_logger.get_logger(__name__)
        logger.info("Configurações carregadas com sucesso")
        
        # Cria cliente FindFace
        logger.info("Conectando ao FindFace...")
        try:
            findface_client = FindfaceMulti(
                url_base=settings.findface.url_base,
                user=settings.findface.user,
                password=settings.findface.password,
                uuid=settings.findface.uuid
            )
            logger.info("Conexão com FindFace estabelecida")
            
            # Envolve com wrapper assíncrono (pool de conexões)
            try:
                findface_async_wrapper = FindfaceMultiAsync(
                    findface_client,
                    pool_connections=10,
                    pool_maxsize=20,
                    timeout=30.0
                )
                logger.info("Pool de conexões httpx ativado para FindFace")
                # Usa wrapper ao invés do cliente original
                findface_client = findface_async_wrapper
            except Exception as e:
                logger.warning(f"Erro ao criar pool async: {e}. Usando cliente padrão.")
        except Exception as e:
            logger.warning(f"Erro ao conectar ao FindFace: {e}")
            logger.warning("Continuando sem FindFace...")
            findface_client = None
        
        # Cria repositório de câmeras
        try:
            camera_repository = CameraRepositoryFindface(
                findface_client=findface_client,
                camera_prefix=settings.camera.prefix
            )
        except Exception as e:
            logger.error(f"Erro ao criar repositório de câmeras: {e}", exc_info=True)
            raise
        
        # Cria orquestrador
        try:
            orchestrator = ApplicationOrchestrator(
                settings=settings,
                camera_repository=camera_repository,
                findface_client=findface_client
            )
        except Exception as e:
            logger.error(f"Erro ao criar orquestrador: {e}", exc_info=True)
            raise
        
        # Inicia aplicação
        try:
            orchestrator.start()
        except Exception as e:
            logger.error(f"Erro ao iniciar aplicação: {e}", exc_info=True)
            raise
        
        # Aguarda até ser interrompido
        try:
            orchestrator.wait()
        except KeyboardInterrupt:
            pass
        
        return 0
        
    except KeyboardInterrupt:
        if async_logger:
            logger = async_logger.get_logger(__name__)
            logger.info("Interrupção via teclado detectada (CTRL+C)")
        if orchestrator:
            try:
                orchestrator.stop()
            except Exception as e:
                if async_logger:
                    logger.error(f"Erro ao parar orquestrador: {e}", exc_info=True)
        return 0
    except Exception as e:
        if async_logger:
            logger = async_logger.get_logger(__name__)
            logger.error(f"Erro fatal na aplicação: {e}", exc_info=True)
        if orchestrator:
            try:
                orchestrator.stop()
            except Exception as stop_error:
                if async_logger:
                    logger.error(f"Erro ao parar orquestrador durante tratamento de erro: {stop_error}", exc_info=True)
        return 1
    finally:
        # Fecha pool de conexões
        if findface_async_wrapper:
            try:
                findface_async_wrapper.close()
            except:
                pass
        
        # Faz logout do FindFace (se for o cliente original, não o wrapper)
        if findface_client and not isinstance(findface_client, FindfaceMultiAsync):
            # É o cliente original, pode fazer logout
            try:
                findface_client.logout()
                if async_logger:
                    logger = async_logger.get_logger(__name__)
                    logger.info("Logout do FindFace realizado")
            except:
                pass
        elif isinstance(findface_client, FindfaceMultiAsync):
            # É o wrapper, fazer logout do cliente interno
            try:
                findface_client.client.logout()
                if async_logger:
                    logger = async_logger.get_logger(__name__)
                    logger.info("Logout do FindFace realizado")
            except:
                pass
        
        # Para AsyncLogger
        if async_logger:
            async_logger.stop()


if __name__ == "__main__":
    exit(main())
