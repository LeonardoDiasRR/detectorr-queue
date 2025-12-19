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
from src.application.orchestrator import ApplicationOrchestrator


def setup_logging(log_config):
    """
    Configura sistema de logging.
    
    :param log_config: Configurações de logging.
    """
    logging.basicConfig(
        level=getattr(logging, log_config.level.upper()),
        format=log_config.format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("application.log", mode='w', encoding="utf-8")
        ]
    )


def main():
    """Função principal da aplicação."""
    logger = logging.getLogger(__name__)
    orchestrator = None
    findface_client = None
    
    try:
        # Carrega configurações
        logger.info("Carregando configurações...")
        settings = ConfigLoader.load()
        
        # Configura logging
        setup_logging(settings.logging)
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
        logger.info("Interrupção via teclado detectada (CTRL+C)")
        if orchestrator:
            try:
                orchestrator.stop()
            except Exception as e:
                logger.error(f"Erro ao parar orquestrador: {e}", exc_info=True)
        return 0
    except Exception as e:
        logger.error(f"Erro fatal na aplicação: {e}", exc_info=True)
        if orchestrator:
            try:
                orchestrator.stop()
            except Exception as stop_error:
                logger.error(f"Erro ao parar orquestrador durante tratamento de erro: {stop_error}", exc_info=True)
        return 1
    finally:
        # Faz logout do FindFace
        if findface_client:
            try:
                findface_client.logout()
                logger.info("Logout do FindFace realizado")
            except:
                pass


if __name__ == "__main__":
    exit(main())
