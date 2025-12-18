"""
Serviço para detecção de landmarks faciais.
"""

import logging
import numpy as np
from typing import Optional, List
from ultralytics import YOLO

from src.domain.value_objects import LandmarksVO
from src.infrastructure.config.settings import ModeloLandmarkConfig


class LandmarkDetectionService:
    """Serviço responsável por detectar landmarks faciais em crops de faces."""
    
    def __init__(self, modelo_landmark_config: ModeloLandmarkConfig, device: str = "cpu"):
        """
        Inicializa o serviço de detecção de landmarks.
        
        :param modelo_landmark_config: Configurações do modelo de landmarks.
        :param device: Device para inferência (cpu ou cuda:N).
        """
        self.modelo_landmark_config = modelo_landmark_config
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Carrega modelo
        self._load_model()
    
    def _load_model(self):
        """Carrega o modelo YOLO de landmarks."""
        try:
            self.logger.info(f"Carregando modelo de landmarks: {self.modelo_landmark_config.model_path}")
            self.model = YOLO(self.modelo_landmark_config.model_path)
            self.model.to(self.device)
            self.logger.info(f"Modelo de landmarks carregado no {self.device}")
        except Exception as e:
            self.logger.error(f"Erro ao carregar modelo de landmarks: {e}")
            raise
    
    def detect_batch(self, face_crops: List[np.ndarray]) -> List[LandmarksVO]:
        """
        Detecta landmarks faciais em um batch de crops de faces.
        
        :param face_crops: Lista de imagens de crops de faces (numpy arrays).
        :return: Lista de LandmarksVO com os landmarks detectados.
        """
        if not face_crops:
            return []
        
        try:
            # Executa inferência em batch
            results = self.model.predict(
                source=face_crops,
                conf=self.modelo_landmark_config.confidence_threshold,
                iou=self.modelo_landmark_config.iou_threshold,
                verbose=False,
                device=self.device,
                stream=False
            )
            
            # Processa resultados
            landmarks_list = []
            for result in results:
                # Verifica se há keypoints
                if not hasattr(result, 'keypoints') or result.keypoints is None:
                    landmarks_list.append(LandmarksVO(None))
                    continue
                
                keypoints_data = result.keypoints.xy.cpu().numpy()
                
                if len(keypoints_data) == 0:
                    landmarks_list.append(LandmarksVO(None))
                    continue
                
                # Retorna o primeiro conjunto de landmarks (esperado apenas uma face no crop)
                landmarks = keypoints_data[0]
                landmarks_list.append(LandmarksVO(landmarks))
            
            return landmarks_list
            
        except Exception as e:
            self.logger.warning(f"Erro ao detectar landmarks em batch: {e}")
            # Retorna lista com None para cada crop
            return [LandmarksVO(None) for _ in face_crops]
