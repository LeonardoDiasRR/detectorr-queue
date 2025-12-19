"""
DisplayCameraUseCase - Caso de Uso para Exibição Visual de uma Câmera
Thread isolada que consome buffer e exibe frames com cv2.imshow()
"""

import cv2
import time
import logging
import threading
from typing import Optional

from ..display.circular_buffer import CircularBuffer
from ..display.display_service import DisplayService, AnnotatedFrame
from ...infrastructure.config.settings import DisplayConfig


class DisplayCameraUseCase:
    """
    Caso de uso para exibição visual de uma câmera.
    
    Responsabilidades:
    - Consumir CircularBuffer de forma não-bloqueante
    - Renderizar frames usando DisplayService
    - Exibir usando cv2.imshow()
    - Gerenciar janela OpenCV
    - Controlar FPS de exibição
    - Detectar fechamento de janela (ESC ou X)
    
    Características:
    - Totalmente isolado da pipeline principal
    - Não bloqueia outras threads
    - Pode crashar sem afetar processamento
    - Read-only (apenas observa)
    """
    
    def __init__(
        self,
        camera_id: str,
        buffer: CircularBuffer,
        display_service: DisplayService,
        config: DisplayConfig
    ):
        """
        Inicializa use case de display.
        
        Args:
            camera_id: ID da câmera
            buffer: Buffer circular compartilhado
            display_service: Serviço de renderização
            config: Configurações de display
        """
        self.camera_id = camera_id
        self.buffer = buffer
        self.display_service = display_service
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Controle de execução
        self._stop_event = threading.Event()
        self._running = False
        
        # Nome da janela
        self.window_name = f"Detectorr - {camera_id}"
        
    def _calculate_frame_delay(self) -> float:
        """
        Calcula delay entre frames para controlar FPS.
        
        Returns:
            Delay em segundos
        """
        return 1.0 / self.config.fps_limit
        
    def _should_stop(self) -> bool:
        """
        Verifica se deve parar exibição.
        
        Pode parar por:
        - Stop event setado
        - Tecla ESC pressionada
        - Janela fechada pelo usuário
        
        Returns:
            True se deve parar
        """
        try:
            if self._stop_event.is_set():
                return True
        except Exception as e:
            self.logger.warning(f"[{self.camera_id}] Erro ao verificar stop_event: {e}")
        
        try:
            # Verifica tecla ESC (27)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                self.logger.info(f"[{self.camera_id}] ESC pressionado, fechando display")
                return True
        except Exception as e:
            self.logger.warning(f"[{self.camera_id}] Erro ao verificar teclado: {e}")
        
        try:
            # Verifica se janela foi fechada
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                self.logger.info(f"[{self.camera_id}] Janela fechada pelo usuário")
                return True
        except cv2.error:
            # Janela não existe mais
            return True
        except Exception as e:
            self.logger.warning(f"[{self.camera_id}] Erro ao verificar propriedade da janela: {e}")
            return True
        
        return False
        
    def run(self):
        """
        Loop principal de exibição.
        
        Executa até:
        - Stop event ser setado
        - ESC ser pressionado
        - Janela ser fechada
        """
        self._running = True
        self.logger.info(f"[{self.camera_id}] Iniciando display visual")
        
        frame_delay = 0
        frames_displayed = 0
        
        try:
            try:
                # Cria janela
                cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(
                    self.window_name,
                    self.config.window_width,
                    self.config.window_height
                )
                frame_delay = self._calculate_frame_delay()
            except Exception as e:
                self.logger.error(f"[{self.camera_id}] Erro ao criar janela: {e}", exc_info=True)
                raise
            
            last_frame_time = 0
            
            while not self._should_stop():
                try:
                    # Controla FPS
                    try:
                        current_time = time.time()
                        if current_time - last_frame_time < frame_delay:
                            time.sleep(0.001)  # Sleep curto para não travar CPU
                            try:
                                cv2.waitKey(1)  # Necessário para processar eventos da janela
                            except Exception:
                                pass
                            continue
                    except Exception as e:
                        self.logger.warning(f"[{self.camera_id}] Erro no controle de FPS: {e}")
                    
                    try:
                        # Tenta obter frame do buffer
                        annotated_frame: Optional[AnnotatedFrame] = self.buffer.get_nowait()
                        
                        if annotated_frame is None:
                            # Sem frames, aguarda um pouco
                            if frames_displayed == 0:
                                self.logger.debug(f"[{self.camera_id}] Aguardando frames no buffer...")
                            time.sleep(0.01)
                            try:
                                cv2.waitKey(1)  # Necessário para processar eventos da janela
                            except Exception:
                                pass
                            continue
                    except Exception as e:
                        self.logger.debug(f"[{self.camera_id}] Erro ao obter frame do buffer: {e}")
                        time.sleep(0.01)
                        continue
                    
                    try:
                        # Renderiza frame
                        rendered_frame = self.display_service.render_frame(annotated_frame)
                        
                        # Exibe
                        cv2.imshow(self.window_name, rendered_frame)
                        try:
                            cv2.waitKey(1)  # Necessário para atualizar a janela
                        except Exception:
                            pass
                        
                        frames_displayed += 1
                        if frames_displayed == 1:
                            self.logger.info(f"[{self.camera_id}] Primeiro frame exibido com sucesso!")
                        elif frames_displayed % 100 == 0:
                            self.logger.debug(f"[{self.camera_id}] {frames_displayed} frames exibidos")
                        last_frame_time = current_time
                    except Exception as e:
                        self.logger.warning(
                            f"[{self.camera_id}] Erro ao renderizar/exibir frame: {e}"
                        )
                except Exception as e:
                    self.logger.error(f"[{self.camera_id}] Erro no loop de display: {e}", exc_info=True)
                    time.sleep(0.1)  # Evita busy loop em caso de erro
            
        except Exception as e:
            self.logger.error(f"[{self.camera_id}] Erro fatal no display: {e}", exc_info=True)
        finally:
            # Cleanup
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass
            
            try:
                self._running = False
                self.logger.info(
                    f"[{self.camera_id}] Display finalizado. "
                    f"Frames exibidos: {frames_displayed}"
                )
            except Exception as e:
                self.logger.warning(f"[{self.camera_id}] Erro ao finalizar display: {e}")
            
    def stop(self):
        """
        Sinaliza para parar exibição.
        
        Método thread-safe para encerramento gracioso.
        """
        self.logger.info(f"[{self.camera_id}] Solicitando parada do display")
        self._stop_event.set()
        
    def is_running(self) -> bool:
        """Verifica se display está em execução."""
        return self._running
