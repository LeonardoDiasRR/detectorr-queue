"""
Script para listar as câmeras disponíveis no FindFace.
Utiliza o padrão Repository (DDD) para obter as câmeras virtuais configuradas.
"""

import logging
from src.infrastructure.clients import FindfaceMulti
from src.infrastructure.repositories import CameraRepositoryFindface
from src.infrastructure.config.config_loader import ConfigLoader


def main():
    """Lista todas as câmeras ativas disponíveis no FindFace."""
    
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Carrega configurações
        logger.info("Carregando configurações...")
        settings = ConfigLoader.load()
        
        # Cria cliente FindFace
        logger.info("Conectando ao FindFace...")
        findface_client = FindfaceMulti(
            url_base=settings.findface.url_base,
            user=settings.findface.user,
            password=settings.findface.password,
            uuid=settings.findface.uuid
        )
        
        # Faz login
        findface_client.login()
        logger.info("Login realizado com sucesso!")
        
        # Cria repositório de câmeras
        camera_repository = CameraRepositoryFindface(
            findface_client=findface_client,
            camera_prefix=settings.camera.prefix
        )
        
        # Obtém câmeras ativas
        logger.info(f"Buscando câmeras ativas com prefixo '{settings.camera.prefix}'...")
        cameras = camera_repository.get_active_cameras()
        
        # Exibe resultado
        if not cameras:
            logger.warning("Nenhuma câmera encontrada.")
        else:
            logger.info(f"\n{'='*80}")
            logger.info(f"Total de câmeras encontradas: {len(cameras)}")
            logger.info(f"{'='*80}\n")
            
            for i, camera in enumerate(cameras, 1):
                print(f"\n--- Câmera {i} ---")
                print(f"ID:     {camera.camera_id.value()}")
                print(f"Nome:   {camera.camera_name.value()}")
                print(f"Token:  {camera.camera_token.value()}")
                print(f"Source: {camera.source.value()}")
                print(f"Active: {camera.active}")
        
        # Faz logout
        findface_client.logout()
        logger.info("\nLogout realizado com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao listar câmeras: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
