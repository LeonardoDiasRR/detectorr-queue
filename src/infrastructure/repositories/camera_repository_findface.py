"""
Implementação do repositório de câmeras usando FindFace Multi API.
Infrastructure Layer - implementação concreta da interface do domínio.
"""

from typing import List
import logging
from src.infrastructure.clients import FindfaceMulti, FindfaceMultiAsync
from src.domain.entities import Camera
from src.domain.repositories import CameraRepository
from src.domain.value_objects import IdVO, NameVO, CameraTokenVO, CameraSourceVO


class CameraRepositoryFindface(CameraRepository):
    """
    Implementação concreta do CameraRepository usando FindFace Multi API.
    """

    def __init__(self, findface_client, camera_prefix: str = 'TESTE'):
        """
        Inicializa o repositório de câmeras do FindFace.

        :param findface_client: Instância do cliente FindfaceMulti ou FindfaceMultiAsync.
        :param camera_prefix: Prefixo para filtrar grupos de câmeras virtuais.
        """
        # Aceita tanto FindfaceMulti quanto FindfaceMultiAsync (wrapper)
        if not isinstance(findface_client, (FindfaceMulti, FindfaceMultiAsync)):
            raise TypeError(
                "O parâmetro 'findface_client' deve ser uma instância de FindfaceMulti "
                "ou FindfaceMultiAsync."
            )
        
        self.findface = findface_client
        self.camera_prefix = camera_prefix
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_active_cameras(self) -> List[Camera]:
        """
        Obtém todas as câmeras ativas do FindFace.
        
        :return: Lista de entidades Camera ativas.
        """
        cameras = []

        try:
            # Obtém grupos de câmeras
            grupos = self.findface.get_camera_groups()["results"]
            grupos_filtrados = [
                g for g in grupos 
                if g["name"].lower().startswith(self.camera_prefix.lower())
            ]

            # Para cada grupo, obtém câmeras ATIVAS
            for grupo in grupos_filtrados:
                cameras_response = self.findface.get_cameras(
                    camera_groups=[grupo["id"]],
                    external_detector=True,
                    ordering='id',
                    active=True  # Filtra apenas câmeras ativas
                )["results"]
                
                # Filtra câmeras com RTSP no comment
                cameras_filtradas = [
                    c for c in cameras_response 
                    if c.get("comment", "").startswith("rtsp://")
                ]
                
                # Converte para entidades Camera
                for camera_data in cameras_filtradas:
                    camera = Camera(
                        camera_id=IdVO(camera_data["id"]),
                        camera_name=NameVO(camera_data["name"]),
                        camera_token=CameraTokenVO(camera_data["external_detector_token"]),
                        source=CameraSourceVO(camera_data["comment"].strip()),
                        active=camera_data.get("active", True)
                    )
                    cameras.append(camera)

            self.logger.info(f"Obtidas {len(cameras)} câmeras ativas do FindFace")
            return cameras

        except Exception as e:
            self.logger.error(f"Erro ao obter câmeras do FindFace: {e}", exc_info=True)
            return []
