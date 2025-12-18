"""
Use Case para enviar eventos ao FindFace.
"""

import logging
from threading import Event as ThreadEvent

from src.domain.entities import Event
from src.application.queues import FindfaceQueue
from src.infrastructure.clients import FindfaceMulti


class SendToFindfaceUseCase:
    """Use Case responsável por enviar eventos ao FindFace."""
    
    def __init__(
        self,
        findface_queue: FindfaceQueue,
        findface_client: FindfaceMulti,
        stop_event: ThreadEvent,
        queue_timeout: float = 0.5
    ):
        """
        Inicializa o use case.
        
        :param findface_queue: Fila de eventos a enviar.
        :param findface_client: Cliente do FindFace.
        :param stop_event: Evento para parar a execução.
        """
        self.findface_queue = findface_queue
        self.findface_client = findface_client
        self.stop_event = stop_event
        self.queue_timeout = queue_timeout
        
        self.logger = logging.getLogger(__name__)
        self._success_count = 0
        self._failure_count = 0
    
    def execute(self):
        """Executa o envio de eventos ao FindFace."""
        self.logger.info("Iniciando envio ao FindFace")
        
        try:
            self._send_loop()
        except Exception as e:
            self.logger.error(f"Erro no envio ao FindFace: {e}", exc_info=True)
        finally:
            self._log_statistics()
            self.logger.info("Envio ao FindFace finalizado")
    
    def _send_loop(self):
        """Loop principal de envio."""
        send_count = 0
        gc_interval = 5  # GC a cada 5 eventos enviados (reduzido de 10)
        
        while not self.stop_event.is_set():
            event = self.findface_queue.get(block=True, timeout=self.queue_timeout)
            
            if event is None:
                continue
            
            self.logger.debug(
                f"Consumido evento {event.id.value()} da fila do FindFace "
                f"(câmera: {event.camera_id.value()}, tamanho fila: {self.findface_queue.qsize()})"
            )
            
            try:
                self._send_event(event)
            finally:
                self.findface_queue.task_done()
                
                # Garbage collection periódico AGRESSIVO
                send_count += 1
                if send_count >= gc_interval:
                    import gc
                    gc.collect()
                    send_count = 0
    
    def _send_event(self, event: Event):
        """
        Envia um evento ao FindFace.
        
        :param event: Evento a enviar.
        """
        fullframe_bytes = None  # Inicializa como None para evitar erro no finally
        
        try:
            # Extrai informações do evento
            camera_id = event.camera_id.value()
            camera_token = event.camera_token.value()
            timestamp = event.frame.timestamp.iso_format()
            bbox = event.bbox.value()
            fullframe = event.frame.full_frame.value()
            
            # Converte bbox para ROI [left, top, right, bottom]
            roi = [
                int(bbox[0]),  # left (x1)
                int(bbox[1]),  # top (y1)
                int(bbox[2]),  # right (x2)
                int(bbox[3])   # bottom (y2)
            ]
            
            # Converte fullframe numpy array para bytes
            import cv2
            _, buffer = cv2.imencode('.jpg', fullframe)
            fullframe_bytes = buffer.tobytes()
            
            # Libera buffer de memória imediatamente
            del buffer
            del fullframe  # Libera frame grande da memória
            
            # Envia ao FindFace usando o SDK
            response = self.findface_client.add_face_event(
                token=camera_token,
                fullframe=fullframe_bytes,
                camera=camera_id,
                timestamp=timestamp,
                roi=roi,
                mf_selector="biggest"
            )
            
            self._success_count += 1
            self.logger.info(
                f"Evento {event.id.value()} enviado com sucesso ao FindFace "
                f"(câmera: {event.camera_name.value()}, "
                f"qualidade: {event.face_quality_score:.4f}, "
                f"response: {response.get('id', 'N/A')})"
            )
            
        except Exception as e:
            self._failure_count += 1
            self.logger.error(
                f"Falha ao enviar evento {event.id.value()} ao FindFace: {e}",
                exc_info=False
            )
        finally:
            # Libera memória do evento após envio (verifica se foi criada)
            if fullframe_bytes is not None:
                del fullframe_bytes
    
    def _log_statistics(self):
        """Loga estatísticas de envio."""
        total = self._success_count + self._failure_count
        if total > 0:
            success_rate = (self._success_count / total) * 100
            self.logger.info(
                f"Estatísticas de envio: {self._success_count} sucessos, "
                f"{self._failure_count} falhas ({success_rate:.1f}% taxa de sucesso)"
            )
