"""
Entidade Frame do domínio.
"""

from typing import Optional, Tuple
import numpy as np
import cv2
from src.domain.value_objects import IdVO, NameVO, CameraTokenVO, TimestampVO, FullFrameVO


class Frame:
    """
    Entidade que representa um frame capturado de uma câmera.
    """

    def __init__(
        self,
        id: IdVO,
        full_frame: FullFrameVO,
        camera_id: IdVO,
        camera_name: NameVO,
        camera_token: CameraTokenVO,
        timestamp: TimestampVO
    ):
        """
        Inicializa a entidade Frame.

        :param id: ID único do frame (IdVO).
        :param full_frame: Frame completo como FullFrameVO.
        :param camera_id: ID da câmera que capturou o frame (IdVO).
        :param camera_name: Nome da câmera que capturou o frame (NameVO).
        :param camera_token: Token de autenticação da câmera (CameraTokenVO).
        :param timestamp: Timestamp de captura do frame (TimestampVO).
        :raises TypeError: Se algum parâmetro não for do tipo esperado.
        """
        if not isinstance(id, IdVO):
            raise TypeError(f"id deve ser IdVO, recebido: {type(id).__name__}")
        
        if not isinstance(full_frame, FullFrameVO):
            raise TypeError(f"full_frame deve ser FullFrameVO, recebido: {type(full_frame).__name__}")
        
        if not isinstance(camera_id, IdVO):
            raise TypeError(f"camera_id deve ser IdVO, recebido: {type(camera_id).__name__}")
        
        if not isinstance(camera_name, NameVO):
            raise TypeError(f"camera_name deve ser NameVO, recebido: {type(camera_name).__name__}")
        
        if not isinstance(camera_token, CameraTokenVO):
            raise TypeError(f"camera_token deve ser CameraTokenVO, recebido: {type(camera_token).__name__}")
        
        if not isinstance(timestamp, TimestampVO):
            raise TypeError(f"timestamp deve ser TimestampVO, recebido: {type(timestamp).__name__}")
        
        self._id = id
        self._full_frame = full_frame
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._camera_token = camera_token
        self._timestamp = timestamp

    @property
    def id(self) -> IdVO:
        """Retorna o ID do frame."""
        return self._id

    @property
    def full_frame(self) -> FullFrameVO:
        """Retorna o FullFrameVO do frame."""
        return self._full_frame

    @property
    def ndarray(self) -> np.ndarray:
        """
        Retorna o array numpy do frame (cópia).
        Para operações read-only, use ndarray_readonly para evitar cópia.
        """
        return self._full_frame.value(copy=True)
    
    @property
    def ndarray_readonly(self) -> np.ndarray:
        """
        Retorna referência read-only ao array numpy do frame - ZERO cópias.
        OTIMIZAÇÃO: Use este método para operações de leitura.
        
        :return: Referência read-only ao ndarray.
        """
        return self._full_frame.ndarray_readonly

    @property
    def camera_id(self) -> IdVO:
        """Retorna o ID da câmera."""
        return self._camera_id

    @property
    def camera_name(self) -> NameVO:
        """Retorna o nome da câmera."""
        return self._camera_name

    @property
    def camera_token(self) -> CameraTokenVO:
        """Retorna o token da câmera."""
        return self._camera_token

    @property
    def timestamp(self) -> TimestampVO:
        """Retorna o timestamp de captura do frame."""
        return self._timestamp

    def jpg(self, quality: int = 95) -> bytes:
        """
        Converte o frame para formato JPEG e retorna como bytes.
        OTIMIZAÇÃO: Usa ndarray_readonly para evitar cópia desnecessária.

        :param quality: Qualidade de compressão JPEG (0-100), padrão 95.
        :return: Frame codificado em JPEG como bytes.
        :raises ValueError: Se a qualidade for inválida.
        :raises RuntimeError: Se a codificação falhar.
        """
        if not 0 <= quality <= 100:
            raise ValueError(f"Qualidade deve estar entre 0 e 100, recebido: {quality}")
        
        # OTIMIZAÇÃO: Usa ndarray_readonly - cv2.imencode não modifica a imagem
        success, buffer = cv2.imencode('.jpg', self.ndarray_readonly, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        if not success:
            raise RuntimeError("Falha ao codificar o frame em JPEG")
        
        return buffer.tobytes()

    @property
    def shape(self) -> Tuple[int, ...]:
        """Retorna as dimensões do frame (altura, largura, canais)."""
        return self._full_frame.shape

    @property
    def height(self) -> int:
        """Retorna a altura do frame."""
        return self._full_frame.height

    @property
    def width(self) -> int:
        """Retorna a largura do frame."""
        return self._full_frame.width

    def copy(self) -> 'Frame':
        """
        Cria uma cópia do frame.

        :return: Nova instância de Frame com FullFrameVO copiado.
        """
        return Frame(
            id=self._id,
            full_frame=FullFrameVO(self.ndarray),
            camera_id=self._camera_id,
            camera_name=self._camera_name,
            camera_token=self._camera_token,
            timestamp=self._timestamp
        )

    def __eq__(self, other) -> bool:
        """Compara dois frames por igualdade (baseado no ID)."""
        if not isinstance(other, Frame):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Retorna o hash do frame (baseado no ID)."""
        return hash(self._id)

    def __repr__(self) -> str:
        """Representação string do frame."""
        return (
            f"Frame(id={self._id.value()}, "
            f"shape={self.shape}, "
            f"camera_id={self._camera_id.value()}, "
            f"camera_name='{self._camera_name.value()}')"
        )

    def __str__(self) -> str:
        """Conversão para string."""
        return f"Frame {self._id.value()} from Camera {self._camera_id.value()}: {self.width}x{self.height}"
