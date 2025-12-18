"""
DisplayService - Serviço de Renderização Visual
Responsável por desenhar bboxes, labels e informações sobre os frames
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ...domain.entities.event_entity import Event
from ...infrastructure.config.settings import DisplayConfig


@dataclass
class AnnotatedFrame:
    """Frame anotado com detecções para exibição."""
    frame: np.ndarray
    camera_id: str
    events: List[Event]
    timestamp: float
    

class DisplayService:
    """
    Serviço de renderização visual.
    
    Responsabilidades:
    - Desenhar bounding boxes
    - Desenhar labels com informações
    - Redimensionar frames para exibição
    - Aplicar cores baseadas em qualidade
    """
    
    def __init__(self, config: DisplayConfig):
        """
        Inicializa serviço de display.
        
        Args:
            config: Configurações de display
        """
        self.config = config
        
    def _get_bbox_color(self, confidence: float, quality_score: Optional[float]) -> Tuple[int, int, int]:
        """
        Determina cor da bbox baseada em confiança e qualidade.
        
        Verde: Alta qualidade (>0.7)
        Amarelo: Média qualidade (0.4-0.7)
        Vermelho: Baixa qualidade (<0.4)
        
        Args:
            confidence: Confiança da detecção
            quality_score: Score de qualidade facial (pode ser None)
            
        Returns:
            Cor BGR para a bbox
        """
        # Se não tem qualidade, usa apenas confiança
        if quality_score is None:
            if confidence >= 0.7:
                return (0, 255, 0)  # Verde
            elif confidence >= 0.4:
                return (0, 255, 255)  # Amarelo
            else:
                return (0, 0, 255)  # Vermelho
        
        # Com qualidade, usa qualidade como critério
        if quality_score >= 0.7:
            return (0, 255, 0)  # Verde - Alta qualidade
        elif quality_score >= 0.4:
            return (0, 255, 255)  # Amarelo - Média qualidade
        else:
            return (0, 0, 255)  # Vermelho - Baixa qualidade
            
    def _draw_bbox(self, frame: np.ndarray, event: Event) -> np.ndarray:
        """
        Desenha bounding box e label em um evento.
        
        Args:
            frame: Frame onde desenhar
            event: Evento com detecção
            
        Returns:
            Frame com bbox desenhado
        """
        # Extrai coordenadas da bbox
        x1, y1, x2, y2 = event.bbox.to_xyxy()
        
        # Determina cor
        color = self._get_bbox_color(
            event.confidence.value,
            event.face_quality_score
        )
        
        # Desenha retângulo
        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            self.config.bbox_thickness
        )
        
        # Prepara texto do label
        label_parts = [f"Conf: {event.confidence.value:.2f}"]
        
        if event.face_quality_score is not None:
            label_parts.append(f"Qual: {event.face_quality_score:.2f}")
            
        label = " | ".join(label_parts)
        
        # Calcula posição do texto
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.config.font_scale
        thickness = 1
        
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        
        # Desenha fundo do texto
        text_x = x1
        text_y = y1 - 10 if y1 > 30 else y1 + text_height + 10
        
        cv2.rectangle(
            frame,
            (text_x, text_y - text_height - baseline),
            (text_x + text_width, text_y + baseline),
            color,
            -1  # Preenchido
        )
        
        # Desenha texto
        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            font,
            font_scale,
            (0, 0, 0),  # Texto preto
            thickness,
            cv2.LINE_AA
        )
        
        return frame
        
    def _draw_header(self, frame: np.ndarray, camera_id: str, num_detections: int) -> np.ndarray:
        """
        Desenha cabeçalho com informações da câmera.
        
        Args:
            frame: Frame onde desenhar
            camera_id: ID da câmera
            num_detections: Número de detecções no frame
            
        Returns:
            Frame com cabeçalho
        """
        header_text = f"Camera: {camera_id} | Deteccoes: {num_detections}"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self.config.font_scale
        thickness = 2
        color = (255, 255, 255)  # Branco
        
        # Desenha fundo preto no topo
        cv2.rectangle(
            frame,
            (0, 0),
            (frame.shape[1], 40),
            (0, 0, 0),
            -1
        )
        
        # Desenha texto
        cv2.putText(
            frame,
            header_text,
            (10, 25),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )
        
        return frame
        
    def render_frame(self, annotated_frame: AnnotatedFrame) -> np.ndarray:
        """
        Renderiza frame completo com todas as anotações.
        
        Args:
            annotated_frame: Frame anotado com eventos
            
        Returns:
            Frame renderizado pronto para exibição
        """
        # Copia frame para não modificar original
        frame = annotated_frame.frame.copy()
        
        # Desenha todas as detecções
        for event in annotated_frame.events:
            frame = self._draw_bbox(frame, event)
            
        # Desenha cabeçalho
        frame = self._draw_header(
            frame,
            annotated_frame.camera_id,
            len(annotated_frame.events)
        )
        
        # Redimensiona para tamanho de exibição
        frame_resized = cv2.resize(
            frame,
            (self.config.window_width, self.config.window_height),
            interpolation=cv2.INTER_LINEAR
        )
        
        return frame_resized
