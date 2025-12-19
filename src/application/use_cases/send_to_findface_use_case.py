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
            try:
                event = self.findface_queue.get(block=True, timeout=self.queue_timeout)
                
                if event is None:
                    continue
                
                self.logger.debug(
                    f"Consumido evento {event.id.value() if event.id else 'UNKNOWN'} da fila do FindFace "
                    f"(câmera: {event.camera_id.value() if event.camera_id else 'UNKNOWN'}, tamanho fila: {self.findface_queue.qsize()})"
                )
                
                try:
                    self._send_event(event)
                except Exception as e:
                    self.logger.error(f"Erro ao enviar evento: {e}", exc_info=True)
                finally:
                    try:
                        self.findface_queue.task_done()
                    except Exception as e:
                        self.logger.warning(f"Erro ao marcar task_done: {e}")
                    
                    # Garbage collection periódico AGRESSIVO
                    send_count += 1
                    if send_count >= gc_interval:
                        try:
                            import gc
                            gc.collect()
                            send_count = 0
                        except Exception as e:
                            self.logger.warning(f"Erro ao executar garbage collection: {e}")
            except Exception as e:
                self.logger.error(f"Erro no loop de envio ao FindFace: {e}", exc_info=True)
    
    def _send_event(self, event: Event):
        """
        Envia um evento ao FindFace.
        
        IMPORTANTE: Após esta função (com ou sem erro), o evento deve ser
        completamente descartado da memória via cleanup().
        
        :param event: Evento a enviar.
        """
        fullframe_bytes = None  # Inicializa como None para evitar erro no finally
        
        try:
            try:
                # Extrai informações do evento com proteção contra None
                camera_id = event.camera_id.value() if event.camera_id else None
                camera_token = event.camera_token.value() if event.camera_token else None
                # Timestamp em formato ISO com timezone
                timestamp = event.frame.timestamp.iso_format_with_tz() if event.frame else None
                bbox = event.bbox.value() if event.bbox else None
                fullframe = event.frame.full_frame.value() if event.frame and event.frame.full_frame else None
                
                # Valida se todos os dados foram extraídos
                if camera_id is None or camera_token is None or timestamp is None or bbox is None or fullframe is None:
                    raise ValueError(f"Evento incompleto: faltam dados necessários")
            except Exception as e:
                self.logger.error(f"Erro ao extrair informações do evento: {e}", exc_info=True)
                raise
            
            try:
                # Converte bbox para ROI [left, top, right, bottom]
                roi = [
                    int(bbox[0]),  # left (x1)
                    int(bbox[1]),  # top (y1)
                    int(bbox[2]),  # right (x2)
                    int(bbox[3])   # bottom (y2)
                ]
            except Exception as e:
                self.logger.error(f"Erro ao converter bbox para ROI: {e}", exc_info=True)
                raise
            
            try:
                # Converte fullframe numpy array para bytes
                import cv2
                _, buffer = cv2.imencode('.jpg', fullframe)
                fullframe_bytes = buffer.tobytes()
                
                # Libera buffer de memória imediatamente
                del buffer
                del fullframe  # Libera frame grande da memória
            except Exception as e:
                self.logger.error(f"Erro ao codificar frame para JPEG: {e}", exc_info=True)
                raise
            
            try:
                # Envia ao FindFace usando o SDK
                response = self.findface_client.add_face_event(
                    token=camera_token,
                    fullframe=fullframe_bytes,
                    camera=camera_id,
                    timestamp=timestamp,
                    roi=roi,
                    mf_selector="biggest"
                )
            except Exception as e:
                self._failure_count += 1
                self.logger.error(
                    f"Erro ao chamar FindFace API para evento {event.id.value() if event.id else 'UNKNOWN'}: {e}",
                    exc_info=True
                )
                raise
            
            try:
                self._success_count += 1
                
                # Extrai informações do resultado com proteção
                findface_event_id = response.get('id', 'N/A') if response else 'N/A'
                matches_count = response.get('matches', {}).get('count', 0) if isinstance(response.get('matches') if response else None, dict) else 0
                
                # Log com proteção contra None
                event_id = event.id.value() if event.id else 'UNKNOWN'
                camera_name = event.camera_name.value() if event.camera_name else 'UNKNOWN'
                quality = event.face_quality_score.value() if event.face_quality_score else 0.0
                
                self.logger.info(
                    f"✓ Evento {event_id} enviado ao FindFace | "
                    f"câmera: {camera_name} | "
                    f"qualidade: {quality:.4f} | "
                    f"findface_id: {findface_event_id} | "
                    f"matches: {matches_count}"
                )
            except Exception as e:
                self.logger.warning(f"Erro ao processar resposta do FindFace: {e}")
            
        except Exception as e:
            self._failure_count += 1
            self.logger.error(
                f"Falha ao enviar evento {event.id.value() if event.id else 'UNKNOWN'} ao FindFace: {e}",
                exc_info=True
            )
        finally:
            # Libera memória do fullframe_bytes se foi criado
            try:
                if fullframe_bytes is not None:
                    del fullframe_bytes
            except Exception as e:
                self.logger.warning(f"Erro ao deletar fullframe_bytes: {e}")
            
            # ISOLAMENTO: Deleta a cópia do evento após processamento
            # O evento na fila é uma cópia, não há race condition com Track
            # Track já foi finalizado e deletado
            try:
                if event is not None and hasattr(event, 'cleanup'):
                    event.cleanup()
            except Exception as e:
                self.logger.warning(f"Erro ao fazer cleanup do evento: {e}")
    
    def _log_statistics(self):
        """Loga estatísticas de envio."""
        total = self._success_count + self._failure_count
        if total > 0:
            success_rate = (self._success_count / total) * 100
            self.logger.info(
                f"Estatísticas de envio: {self._success_count} sucessos, "
                f"{self._failure_count} falhas ({success_rate:.1f}% taxa de sucesso)"
            )
