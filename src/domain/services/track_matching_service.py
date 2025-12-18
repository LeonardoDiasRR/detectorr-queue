"""
Domain Service para matching de eventos a tracks.
Implementa algoritmos de associação baseados em IoU e distância de centros.
"""

import numpy as np
from typing import Tuple, Optional
from src.domain.value_objects import BboxVO


class TrackMatchingService:
    """
    Serviço de domínio para cálculos de matching entre eventos e tracks.
    Implementa estratégias de associação baseadas em sobreposição de bounding boxes.
    """
    
    @staticmethod
    def calcular_iou(bbox1: BboxVO, bbox2: BboxVO) -> float:
        """
        Calcula o IoU (Intersection over Union) entre duas bounding boxes.
        Usa a média das áreas ao invés do IoU tradicional (união).
        
        :param bbox1: Primeira bounding box.
        :param bbox2: Segunda bounding box.
        :return: Valor entre 0.0 (sem sobreposição) e 1.0 (sobreposição total).
        """
        b1 = bbox1.value()  # (x1, y1, x2, y2)
        b2 = bbox2.value()
        
        # Coordenadas da área de interseção
        x1_inter = max(b1[0], b2[0])
        y1_inter = max(b1[1], b2[1])
        x2_inter = min(b1[2], b2[2])
        y2_inter = min(b1[3], b2[3])
        
        # Calcula área de interseção
        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0
        
        area_inter = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Calcula áreas individuais
        area_b1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area_b2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        
        # Evita divisão por zero
        if area_b1 == 0 or area_b2 == 0:
            return 0.0
        
        # Usa média das áreas ao invés da união (comportamento do sistema legado)
        area_media = (area_b1 + area_b2) / 2.0
        
        return area_inter / area_media
    
    @staticmethod
    def calcular_distancia_centros(bbox1: BboxVO, bbox2: BboxVO) -> float:
        """
        Calcula a distância euclidiana entre os centros de duas bounding boxes.
        
        :param bbox1: Primeira bounding box.
        :param bbox2: Segunda bounding box.
        :return: Distância em pixels.
        """
        b1 = bbox1.value()
        b2 = bbox2.value()
        
        # Calcula centros
        centro1_x = (b1[0] + b1[2]) / 2.0
        centro1_y = (b1[1] + b1[3]) / 2.0
        
        centro2_x = (b2[0] + b2[2]) / 2.0
        centro2_y = (b2[1] + b2[3]) / 2.0
        
        # Distância euclidiana
        distancia = np.sqrt((centro1_x - centro2_x)**2 + (centro1_y - centro2_y)**2)
        
        return float(distancia)
    
    @staticmethod
    def calcular_limiar_iou(frame_width: int, frame_height: int) -> float:
        """
        Calcula limiar adaptativo de IoU baseado na resolução do frame.
        
        Limiares por resolução (conforme sistema legado):
        - ≤640px: 0.2
        - ≤1280px: 0.15
        - ≤1920px: 0.12
        - >1920px: 0.1
        
        :param frame_width: Largura do frame.
        :param frame_height: Altura do frame.
        :return: Limiar de IoU.
        """
        max_dim = max(frame_width, frame_height)
        
        if max_dim <= 640:
            return 0.2
        elif max_dim <= 1280:
            return 0.15
        elif max_dim <= 1920:
            return 0.12
        else:
            return 0.1
    
    @staticmethod
    def calcular_limiar_distancia(frame_width: int, frame_height: int, 
                                   percentual: float = 0.07) -> float:
        """
        Calcula limiar máximo de distância entre centros.
        Padrão: 7% da diagonal do frame (configurável).
        
        :param frame_width: Largura do frame.
        :param frame_height: Altura do frame.
        :param percentual: Percentual da diagonal (default: 0.07 = 7%).
        :return: Limiar de distância em pixels.
        """
        diagonal = np.sqrt(frame_width**2 + frame_height**2)
        return float(diagonal * percentual)
    
    @staticmethod
    def match_evento_com_track(evento_bbox: BboxVO, track_bbox: BboxVO,
                               frame_width: int, frame_height: int) -> Tuple[float, float]:
        """
        Calcula scores de matching entre um evento e um track.
        
        :param evento_bbox: Bounding box do evento.
        :param track_bbox: Bounding box do último evento do track.
        :param frame_width: Largura do frame.
        :param frame_height: Altura do frame.
        :return: Tupla (iou_score, distancia_centros).
        """
        iou = TrackMatchingService.calcular_iou(evento_bbox, track_bbox)
        distancia = TrackMatchingService.calcular_distancia_centros(evento_bbox, track_bbox)
        
        return (iou, distancia)
