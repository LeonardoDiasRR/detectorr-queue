"""
Use Case para detecção facial e tracking usando YOLO + ByteTrack.
"""

import logging
import gc
import torch
import numpy as np
from typing import Optional, List, Dict
from threading import Event as ThreadEvent
from ultralytics import YOLO

from src.domain.entities import Frame, Event
from src.domain.value_objects import IdVO, BboxVO, ConfidenceVO, LandmarksVO
from src.application.queues import FrameQueue, EventQueue
from src.application.services import LandmarkDetectionService
from src.application.display.circular_buffer import CircularBuffer
from src.application.display.display_service import AnnotatedFrame
from src.infrastructure.config.settings import ModeloDeteccaoConfig, TrackingConfig, ProcessingConfig, PerformanceConfig, FilterConfig, DisplayConfig


class DetectFacesUseCase:
    """Use Case responsável por detectar faces e fazer tracking."""
    
    def __init__(
        self,
        frame_queue: FrameQueue,
        event_queue: EventQueue,
        modelo_deteccao_config: ModeloDeteccaoConfig,
        tracking_config: TrackingConfig,
        processing_config: ProcessingConfig,
        performance_config: PerformanceConfig,
        filter_config: FilterConfig,
        gpu_id: int,
        landmark_service: LandmarkDetectionService,
        stop_event: ThreadEvent,
        display_config: DisplayConfig,
        display_buffers: Optional[Dict[str, CircularBuffer]] = None,
        shared_model: Optional[YOLO] = None,
        queue_timeout: float = 0.5
    ):
        """
        Inicializa o use case.
        
        :param frame_queue: Fila de frames de entrada.
        :param event_queue: Fila de eventos de saída.
        :param modelo_deteccao_config: Configurações do modelo de detecção.
        :param tracking_config: Configurações do tracking.
        :param processing_config: Configurações de processamento.
        :param performance_config: Configurações de performance.
        :param filter_config: Configurações de filtros.
        :param gpu_id: ID da GPU a ser utilizada.
        :param landmark_service: Serviço de detecção de landmarks.
        :param stop_event: Evento para parar a execução.
        :param display_config: Configurações de display visual.
        :param display_buffers: Dicionário de buffers de display por camera_id (opcional).
        :param shared_model: Modelo YOLO compartilhado entre workers (opcional).
        """
        self.frame_queue = frame_queue
        self.event_queue = event_queue
        self.modelo_deteccao_config = modelo_deteccao_config
        self.tracking_config = tracking_config
        self.processing_config = processing_config
        self.performance_config = performance_config
        self.filter_config = filter_config
        self.gpu_id = gpu_id
        self.stop_event = stop_event
        self.queue_timeout = queue_timeout
        
        self.logger = logging.getLogger(f"{__name__}.GPU{gpu_id}")
        self.model: Optional[YOLO] = shared_model  # Usa modelo compartilhado se fornecido
        self.device = self._get_device()
        self.batch_size = self._get_batch_size()
        self.landmark_service = landmark_service
        
        # Display (opcional)
        self.display_config = display_config
        self.display_buffers = display_buffers or {}
        
        self._event_counter = 0
    
    def _get_device(self) -> str:
        """Determina o device a ser usado."""
        if torch.cuda.is_available():
            return f"cuda:{self.gpu_id}"
        return "cpu"
    
    def _get_batch_size(self) -> int:
        """Determina o batch size baseado no device."""
        if self.device.startswith("cuda"):
            return self.processing_config.gpu_batch_size
        return self.processing_config.cpu_batch_size
    
    def execute(self):
        """Executa a detecção e tracking de faces."""
        self.logger.info(f"Iniciando detector de faces na {self.device}")
        
        try:
            # Otimizações de memória GPU
            if torch.cuda.is_available():
                # Desabilita benchmark do cuDNN (economiza memória)
                torch.backends.cudnn.benchmark = False
                # Ativa modo determinístico (mais lento mas economiza memória)
                torch.backends.cudnn.deterministic = True
                # Libera cache antes de começar
                torch.cuda.empty_cache()
            
            # Carrega modelo apenas se não foi fornecido (compartilhado)
            if self.model is None:
                try:
                    self._load_model()
                except Exception as e:
                    self.logger.error(f"Erro ao carregar modelo de detecção: {e}", exc_info=True)
                    raise
            
            self._detection_loop()
        except Exception as e:
            self.logger.error(f"Erro no detector de faces: {e}", exc_info=True)
        finally:
            self.logger.info("Detector de faces finalizado")
    
    def _load_model(self):
        """Carrega o modelo YOLO."""
        self.logger.info(f"Carregando modelo de detecção: {self.modelo_deteccao_config.model_path}")
        self.model = YOLO(self.modelo_deteccao_config.model_path)
        self.model.to(self.device)
        self.logger.info(f"Modelo carregado com sucesso no {self.device}")
    
    def _detection_loop(self):
        """Loop principal de detecção."""
        batch_count = 0
        gc_interval = 3  # Forçar GC a cada 3 batches (MAIS agressivo: era 5)
        
        while not self.stop_event.is_set():
            try:
                # Obtém batch de frames
                frames = self.frame_queue.get_batch(self.batch_size, timeout=self.queue_timeout)
                
                if not frames:
                    continue
                
                self.logger.debug(f"Consumidos {len(frames)} frames da fila (tamanho atual: {self.frame_queue.qsize()})")
                
                try:
                    # Processa batch
                    self._process_batch(frames)
                except Exception as e:
                    self.logger.error(f"Erro ao processar batch de {len(frames)} frames: {e}", exc_info=True)
                finally:
                    # Marca frames como processados
                    for _ in frames:
                        self.frame_queue.task_done()
                    
                    # Libera referências aos frames para GC
                    frames.clear()
                    del frames
                
                # Garbage collection AGRESSIVO e periódico
                batch_count += 1
                if batch_count >= gc_interval:
                    try:
                        gc.collect()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                        batch_count = 0
                    except Exception as e:
                        self.logger.warning(f"Erro ao executar garbage collection: {e}")
            except Exception as e:
                self.logger.error(f"Erro no loop principal de detecção: {e}", exc_info=True)
                # Continua executando mesmo com erro
    
    def _process_batch(self, frames: List[Frame]):
        """
        Processa um batch de frames.
        
        :param frames: Lista de frames a processar.
        """
        self.logger.debug(f"Processando batch de {len(frames)} frames. Display ativado: {self.display_config.exibir_na_tela if self.display_config else 'config None'}, Buffers: {len(self.display_buffers)}")
        
        # Prepara imagens para inferência
        images = [frame.full_frame.value() for frame in frames]
        
        try:
            try:
                # Executa detecção (tracking será feito manualmente)
                results = self.model.predict(
                    source=images,
                    conf=self.modelo_deteccao_config.confidence_threshold,
                    iou=self.modelo_deteccao_config.iou_threshold,
                    imgsz=self.performance_config.inference_size,
                    device=self.device,
                    verbose=False,
                    stream=False
                )
            except Exception as e:
                self.logger.error(f"Erro ao executar inferência do modelo YOLO: {e}", exc_info=True)
                return
            
            # Processa cada frame de resultados
            try:
                for frame, result in zip(frames, results):
                    try:
                        self._process_detections(frame, result)
                    except Exception as e:
                        self.logger.error(f"Erro ao processar detecções do frame: {e}", exc_info=True)
            except Exception as e:
                self.logger.error(f"Erro ao iterar sobre resultados: {e}", exc_info=True)
        finally:
            # Libera memória das imagens
            images.clear()
            del images
            
            # Limpa cache GPU AGRESSIVAMENTE
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()  # Garante que cache foi liberado
            except Exception as e:
                self.logger.warning(f"Erro ao limpar cache GPU: {e}")
    
    def _process_detections(self, frame: Frame, result):
        """
        Processa detecções de um frame.
        
        :param frame: Frame processado.
        :param result: Resultado do YOLO.
        """
        if result.boxes is None or len(result.boxes) == 0:
            # Se display ativado e sem detecções, ainda pode enviar frame vazio
            if self.display_config and self.display_config.exibir_na_tela:
                self.logger.debug(f"Enviando frame vazio para display (sem detecções)")
                try:
                    self._send_to_display(frame, [])
                except Exception as e:
                    self.logger.warning(f"Erro ao enviar frame vazio para display: {e}")
            return
        
        try:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
        except Exception as e:
            self.logger.error(f"Erro ao extrair boxes do resultado YOLO: {e}", exc_info=True)
            return
        
        # Obtém frame completo
        try:
            full_frame = frame.full_frame.value()
        except Exception as e:
            self.logger.error(f"Erro ao obter frame completo: {e}", exc_info=True)
            return
        
        # Coleta todos os crops de faces para detecção em batch
        face_crops = []
        detection_data = []  # Lista para armazenar dados de cada detecção
        
        try:
            for idx in range(len(boxes)):
                try:
                    bbox = boxes[idx]
                    confidence = float(confidences[idx])
                    
                    # Extrai crop da face
                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                    face_crop = full_frame[y1:y2, x1:x2]
                    
                    face_crops.append(face_crop)
                    detection_data.append({
                        'bbox': bbox,
                        'confidence': confidence
                    })
                except Exception as e:
                    self.logger.warning(f"Erro ao processar detecção {idx}: {e}")
                    continue
            
            if not face_crops:
                self.logger.debug("Nenhum crop de face válido extraído")
                return
            
            # Detecta em um único lote todos os landmarks do frame (batch processing)
            try:
                landmarks_list = self.landmark_service.detect_batch(face_crops)
            except Exception as e:
                self.logger.error(f"Erro ao detectar landmarks em batch: {e}", exc_info=True)
                landmarks_list = [None] * len(face_crops)
            
            # Cria eventos para cada detecção
            events_for_display = []
            for detection, landmarks_vo in zip(detection_data, landmarks_list):
                try:
                    self._event_counter += 1
                    
                    # ISOLAMENTO: Cria evento com cópia do frame
                    # Cada evento tem seu próprio frame (isolado)
                    event = Event(
                        id=IdVO(self._event_counter),
                        frame=frame.copy(),  # Cópia isolada do frame
                        bbox=BboxVO(tuple(detection['bbox'].tolist())),
                        confidence=ConfidenceVO(detection['confidence']),
                        landmarks=landmarks_vo
                    )
                    
                    # Enfileira evento (que já tem sua cópia de frame)
                    if not self.event_queue.put(event, block=False):
                        self.logger.warning(f"Fila de eventos cheia, evento {self._event_counter} descartado")
                        # Limpa evento se não foi enfileirado
                        try:
                            event.cleanup()
                        except Exception as cleanup_error:
                            self.logger.warning(f"Erro ao fazer cleanup do evento: {cleanup_error}")
                    else:
                        # Armazena para display
                        events_for_display.append(event)
                except Exception as e:
                    self.logger.warning(f"Erro ao criar evento de detecção: {e}")
                    continue
            
            # ISOLAMENTO: Deleta o frame original após criar todos os eventos
            # Cada evento tem sua própria cópia de frame agora
            try:
                self._release_frame_memory(frame)
            except Exception as e:
                self.logger.warning(f"Erro ao liberar memória do frame: {e}")
            
            # Envia para display se ativado
            if self.display_config and self.display_config.exibir_na_tela:
                self.logger.debug(f"Enviando frame com {len(events_for_display)} detecções para display")
                try:
                    self._send_to_display(frame, events_for_display)
                except Exception as e:
                    self.logger.warning(f"Erro ao enviar frame para display: {e}")
        finally:
            # Libera memória das estruturas temporárias
            try:
                face_crops.clear()
                detection_data.clear()
                del face_crops, detection_data
                del boxes, confidences
            except Exception as e:
                self.logger.warning(f"Erro ao limpar estruturas temporárias: {e}")
            
            # Libera frame da memória (não mais necessário)
            # O frame será removido da referência quando sair desta função
            try:
                if result is not None:
                    del result  # Deleta o resultado do modelo também
            except Exception as e:
                self.logger.warning(f"Erro ao deletar resultado do modelo: {e}")
    
    def _release_frame_memory(self, frame: Frame) -> None:
        """
        Libera COMPLETAMENTE a memória de um frame após ser processado.
        
        IMPORTANTE: Frame foi enfileirado → pode ser descartado completamente.
        A imagem não será mais necessária após ser salva em eventos/fila.
        
        Cascata de limpeza:
        - Zera full_frame → libera ~7MB de memória numpy
        - Zera metadados do frame
        
        :param frame: Frame cujas referências devem ser liberadas.
        """
        try:
            if hasattr(frame, '_full_frame') and frame._full_frame is not None:
                # Zera o FullFrameVO completamente
                frame._full_frame = None
        except Exception:
            pass  # Deixa o GC fazer o trabalho
    
    def _send_to_display(self, frame: Frame, events: List[Event]):
        """
        Envia frame anotado para buffer de display (não-bloqueante).
        
        :param frame: Frame original
        :param events: Lista de eventos detectados neste frame
        """
        self.logger.debug(f"_send_to_display chamado com {len(events)} eventos")
        
        camera_id = str(frame.camera_id.value())  # Converte para string para consistência com buffer keys
        
        self.logger.debug(f"camera_id extraído: {camera_id}, buffers disponíveis: {list(self.display_buffers.keys())}")
        
        # Verifica se existe buffer para esta câmera
        if camera_id not in self.display_buffers:
            self.logger.debug(f"Buffer de display não encontrado para camera_id: {camera_id}")
            return
        
        # Cria AnnotatedFrame
        annotated_frame = AnnotatedFrame(
            frame=frame.full_frame.value(),
            camera_id=camera_id,
            events=events,
            timestamp=frame.timestamp.timestamp()
        )
        
        # Adiciona ao buffer (não-bloqueante, descarta se cheio)
        try:
            success = self.display_buffers[camera_id].put_nowait(annotated_frame)
            if success:
                self.logger.debug(f"Frame enviado ao buffer de display para {camera_id}, eventos: {len(events)}")
            else:
                self.logger.warning(f"Falha ao enviar frame ao buffer de display para {camera_id}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar frame ao buffer de display: {e}")
            pass
