"""
Use Case para capturar stream RTSP e enfileirar frames.
"""

import cv2
import logging
import time
from typing import Optional
from threading import Event as ThreadEvent

from src.domain.entities import Camera, Frame
from src.domain.value_objects import IdVO, TimestampVO, FullFrameVO
from src.application.queues import FrameQueue
from src.infrastructure.config.settings import CameraSettingsConfig, PerformanceConfig


class StreamCameraUseCase:
    """Use Case responsável por capturar frames de uma câmera RTSP."""
    
    def __init__(
        self,
        camera: Camera,
        frame_queue: FrameQueue,
        camera_settings: CameraSettingsConfig,
        performance_config: PerformanceConfig,
        stop_event: ThreadEvent
    ):
        """
        Inicializa o use case.
        
        :param camera: Câmera a ser processada.
        :param frame_queue: Fila para enfileirar frames capturados.
        :param camera_settings: Configurações de câmera.
        :param performance_config: Configurações de performance.
        :param stop_event: Evento para parar a execução.
        """
        self.camera = camera
        self.frame_queue = frame_queue
        self.camera_settings = camera_settings
        self.performance_config = performance_config
        self.stop_event = stop_event
        self.logger = logging.getLogger(f"{__name__}.{camera.camera_name.value()}")
        
        self._frame_counter = 0
        self._capture: Optional[cv2.VideoCapture] = None
    
    def execute(self):
        """Executa a captura de frames do stream RTSP."""
        self.logger.info(f"Iniciando captura da câmera {self.camera.camera_name.value()}")
        
        retries = 0
        while not self.stop_event.is_set() and retries < self.camera_settings.rtsp_max_retries:
            try:
                self._connect()
                self._capture_loop()
            except Exception as e:
                retries += 1
                self.logger.error(
                    f"Erro na captura da câmera {self.camera.camera_name.value()}: {e}. "
                    f"Tentativa {retries}/{self.camera_settings.rtsp_max_retries}"
                )
                
                if retries < self.camera_settings.rtsp_max_retries:
                    self.logger.info(f"Aguardando {self.camera_settings.rtsp_reconnect_delay}s para reconectar...")
                    time.sleep(self.camera_settings.rtsp_reconnect_delay)
                else:
                    self.logger.error(f"Máximo de tentativas alcançado para câmera {self.camera.camera_name.value()}")
            finally:
                self._disconnect()
        
        self.logger.info(f"Captura finalizada para câmera {self.camera.camera_name.value()}")
    
    def _connect(self):
        """Conecta ao stream RTSP."""
        self.logger.info(f"Conectando ao RTSP: {self.camera.source.value()}")
        self._capture = cv2.VideoCapture(self.camera.source.value())
        
        if not self._capture.isOpened():
            raise ConnectionError(f"Não foi possível conectar ao RTSP: {self.camera.source.value()}")
        
        self.logger.info("Conexão RTSP estabelecida com sucesso")
    
    def _disconnect(self):
        """Desconecta do stream RTSP."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            self.logger.info("Conexão RTSP encerrada")
    
    def _capture_loop(self):
        """Loop principal de captura de frames."""
        while not self.stop_event.is_set():
            ret, frame_data = self._capture.read()
            
            if not ret or frame_data is None:
                self.logger.warning("Falha ao ler frame do RTSP")
                break
            
            self._frame_counter += 1
            
            # Cria entidade Frame
            frame = Frame(
                id=IdVO(self._frame_counter),
                camera_id=self.camera.camera_id,
                camera_name=self.camera.camera_name,
                camera_token=self.camera.camera_token,
                timestamp=TimestampVO.now(),
                full_frame=FullFrameVO(frame_data)
            )
            
            # Enfileira frame (não bloqueia se fila estiver cheia)
            if not self.frame_queue.put(frame, block=False):
                self.logger.warning("Fila de frames cheia")
