"""
Entidade Event representando uma detecção de face em um frame.
"""

from typing import Optional
from src.domain.entities.frame_entity import Frame
from src.domain.value_objects import IdVO, BboxVO, ConfidenceVO, LandmarksVO


class Event:
    """
    Entidade que representa uma detecção de face (evento) em um frame específico.
    """

    def __init__(
        self,
        id: IdVO,
        frame: Frame,
        bbox: BboxVO,
        confidence: ConfidenceVO,
        landmarks: LandmarksVO,
        face_quality_score: Optional[ConfidenceVO] = None
    ):
        """
        Inicializa a entidade Event.

        :param id: ID único do evento.
        :param frame: Frame onde a face foi detectada.
        :param bbox: Bounding box da face.
        :param confidence: Confiança da detecção YOLO.
        :param landmarks: Landmarks faciais.
        :param face_quality_score: Score de qualidade da face (calculado automaticamente se None).
        """
        if not isinstance(id, IdVO):
            raise TypeError(f"id deve ser IdVO, recebido: {type(id).__name__}")
        if not isinstance(frame, Frame):
            raise TypeError(f"frame deve ser Frame, recebido: {type(frame).__name__}")
        if not isinstance(bbox, BboxVO):
            raise TypeError(f"bbox deve ser BboxVO, recebido: {type(bbox).__name__}")
        if not isinstance(confidence, ConfidenceVO):
            raise TypeError(f"confidence deve ser ConfidenceVO, recebido: {type(confidence).__name__}")
        if not isinstance(landmarks, LandmarksVO):
            raise TypeError(f"landmarks deve ser LandmarksVO, recebido: {type(landmarks).__name__}")
        if face_quality_score is not None and not isinstance(face_quality_score, ConfidenceVO):
            raise TypeError(f"face_quality_score deve ser ConfidenceVO, recebido: {type(face_quality_score).__name__}")

        self._id = id
        self._frame = frame
        self._bbox = bbox
        self._confidence = confidence
        self._landmarks = landmarks

        # Calcula o score de qualidade se não foi fornecido
        if face_quality_score is None:
            # Import aqui para evitar circular import
            from src.domain.services.face_quality_service import FaceQualityService
            self._face_quality_score = FaceQualityService.calculate_quality(
                bbox=bbox,
                confidence=confidence,
                frame=frame,
                landmarks=landmarks
            )
        else:
            self._face_quality_score = face_quality_score

    @property
    def id(self) -> IdVO:
        """Retorna o ID do evento."""
        return self._id

    @property
    def frame(self) -> Frame:
        """Retorna o frame do evento."""
        return self._frame

    @property
    def bbox(self) -> BboxVO:
        """Retorna o bounding box."""
        return self._bbox

    @property
    def confidence(self) -> ConfidenceVO:
        """Retorna a confiança da detecção."""
        return self._confidence

    @property
    def landmarks(self) -> LandmarksVO:
        """Retorna os landmarks."""
        return self._landmarks

    @property
    def face_quality_score(self) -> ConfidenceVO:
        """Retorna o score de qualidade da face."""
        return self._face_quality_score

    @property
    def camera_id(self) -> IdVO:
        """Retorna o ID da câmera (delegado ao frame)."""
        return self._frame.camera_id

    @property
    def camera_name(self):
        """Retorna o nome da câmera (delegado ao frame)."""
        return self._frame.camera_name

    @property
    def camera_token(self):
        """Retorna o token da câmera (delegado ao frame)."""
        return self._frame.camera_token

    def to_dict(self) -> dict:
        """
        Converte o evento para dicionário.

        :return: Dicionário com os dados do evento.
        """
        return {
            "id": self._id.value(),
            "frame_id": self._frame.id.value(),
            "bbox": self._bbox.value(),
            "confidence": self._confidence.value(),
            "landmarks": self._landmarks.to_list() if not self._landmarks.is_empty() else None,
            "face_quality_score": self._face_quality_score.value(),
            "camera_id": self.camera_id.value(),
            "camera_name": self.camera_name.value(),
            "camera_token": self.camera_token.value()
        }

    def __eq__(self, other) -> bool:
        """Verifica igualdade baseada no ID."""
        if not isinstance(other, Event):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Retorna hash baseado no ID."""
        return hash(self._id)

    def __repr__(self) -> str:
        """Representação técnica do evento."""
        return (
            f"Event(id={self._id.value()}, "
            f"frame_id={self._frame.id.value()}, "
            f"bbox={self._bbox}, "
            f"confidence={self._confidence.value():.4f}, "
            f"quality={self._face_quality_score.value():.4f})"
        )

    def __str__(self) -> str:
        """Representação legível do evento."""
        return f"Event {self._id.value()} (Quality: {self._face_quality_score.value():.4f})"
