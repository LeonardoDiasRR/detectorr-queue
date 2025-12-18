"""
Orquestrador principal da aplicação.
Gerencia threads, filas e coordena os Use Cases.
"""

import logging
import signal
import threading
from typing import List, Dict
from threading import Event as ThreadEvent

from src.domain.entities import Camera
from src.domain.repositories import CameraRepository
from src.infrastructure.clients import FindfaceMulti
from src.infrastructure.config.settings import AppSettings
from src.application.queues import FrameQueue, EventQueue, FindfaceQueue
from src.application.use_cases import (
    StreamCameraUseCase,
    DetectFacesUseCase,
    ManageTracksUseCase,
    SendToFindfaceUseCase,
    DisplayCameraUseCase
)
from src.application.display.circular_buffer import CircularBuffer
from src.application.display.display_service import DisplayService


class ApplicationOrchestrator:
    """Orquestrador principal que coordena toda a aplicação."""
    
    def __init__(
        self,
        settings: AppSettings,
        camera_repository: CameraRepository,
        findface_client: FindfaceMulti
    ):
        """
        Inicializa o orquestrador.
        
        :param settings: Configurações da aplicação.
        :param camera_repository: Repositório de câmeras.
        :param findface_client: Cliente do FindFace.
        """
        self.settings = settings
        self.camera_repository = camera_repository
        self.findface_client = findface_client
        
        self.logger = logging.getLogger(__name__)
        
        # Evento para parada graceful
        self.stop_event = ThreadEvent()
        
        # Filas
        self.frame_queue = FrameQueue(maxsize=settings.queues.frame_queue_max_size)
        self.event_queue = EventQueue(maxsize=settings.queues.event_queue_max_size)
        self.findface_queue = FindfaceQueue(maxsize=settings.queues.findface_queue_max_size)
        
        # Threads
        self.threads: List[threading.Thread] = []
        
        # Câmeras ativas
        self.cameras: List[Camera] = []
        
        # Display (opcional)
        self.display_buffers: Dict[str, CircularBuffer] = {}
        self.display_service: DisplayService = None
        self.display_threads: List[threading.Thread] = []
        
        # Registra handlers de sinal
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Registra handlers para SIGTERM e SIGINT."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handler para sinais de interrupção.
        
        :param signum: Número do sinal.
        :param frame: Frame de execução.
        """
        self.logger.info(f"Sinal {signum} recebido. Iniciando parada graceful...")
        self.stop()
    
    def start(self):
        """Inicia a aplicação."""
        self.logger.info("=" * 80)
        self.logger.info("INICIANDO APLICAÇÃO DE DETECÇÃO FACIAL")
        self.logger.info("=" * 80)
        
        try:
            # Carrega câmeras ativas
            self._load_cameras()
            
            # Inicializa display se ativado
            if self.settings.display.exibir_na_tela:
                self._setup_display()
            
            # Inicia workers de detecção (um por GPU)
            self._start_detection_workers()
            
            # Inicia gerenciador de tracks
            self._start_track_manager()
            
            # Inicia workers de envio ao FindFace
            self._start_findface_workers()
            
            # Inicia streams de câmeras (uma thread por câmera)
            self._start_camera_streams()
            
            # Inicia display workers (se ativado)
            if self.settings.display.exibir_na_tela:
                self._start_display_workers()
            
            self.logger.info("Aplicação iniciada com sucesso!")
            self.logger.info(f"- {len(self.cameras)} câmeras ativas")
            self.logger.info(f"- {self.settings.workers.detection_workers} workers de detecção (frame_queue)")
            self.logger.info(f"- {self.settings.workers.track_workers} workers de gerenciamento de tracks (event_queue)")
            self.logger.info(f"- {self.settings.workers.findface_workers} workers de envio ao FindFace (findface_queue)")
            if self.settings.display.exibir_na_tela:
                self.logger.info(f"- {len(self.display_threads)} workers de display visual (1 por câmera)")
            self.logger.info(f"- {len(self.threads) + len(self.display_threads)} threads totais em execução")
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar aplicação: {e}", exc_info=True)
            self.stop()
            raise
    
    def _load_cameras(self):
        """Carrega câmeras ativas do repositório."""
        self.logger.info(f"Carregando câmeras com prefixo '{self.settings.camera.prefix}'...")
        
        self.cameras = self.camera_repository.get_active_cameras()
        
        if not self.cameras:
            raise ValueError(f"Nenhuma câmera ativa encontrada com prefixo '{self.settings.camera.prefix}'")
        
        self.logger.info(f"Câmeras carregadas:")
        for cam in self.cameras:
            self.logger.info(f"  - {cam.camera_name.value()} (ID: {cam.camera_id.value()})")
    
    def _setup_display(self):
        """Configura sistema de display visual."""
        self.logger.info("Configurando sistema de display visual...")
        
        # Cria serviço de display
        self.display_service = DisplayService(self.settings.display)
        
        # Cria buffer circular para cada câmera
        for camera in self.cameras:
            camera_id = camera.camera_id.value()
            self.display_buffers[camera_id] = CircularBuffer(max_size=5)
        
        self.logger.info(f"  - Display configurado para {len(self.display_buffers)} câmeras")
    
    def _start_detection_workers(self):
        """Inicia workers de detecção."""
        num_workers = self.settings.workers.detection_workers
        self.logger.info(f"Iniciando {num_workers} workers de detecção...")
        
        import torch
        from ultralytics import YOLO
        
        cuda_available = torch.cuda.is_available()
        num_gpus = torch.cuda.device_count() if cuda_available else 0
        
        # Determina device principal
        device = "cuda:0" if cuda_available else "cpu"
        
        # Carrega modelos UMA VEZ (compartilhados entre todos os workers)
        self.logger.info(f"Carregando modelo de detecção: {self.settings.modelo_deteccao.model_path}")
        detection_model = YOLO(self.settings.modelo_deteccao.model_path)
        detection_model.to(device)
        self.logger.info(f"Modelo de detecção carregado no {device}")
        
        # WARMUP: Inicializa callbacks do Ultralytics antes de threading
        # Previne ImportError de circular import em ambiente multi-thread
        import numpy as np
        dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
        self.logger.info("Aquecendo modelo de detecção (warmup)...")
        _ = detection_model.predict(dummy_image, verbose=False, imgsz=self.settings.performance.inference_size)
        self.logger.info("Warmup concluído")
        
        # Carrega modelo de landmarks UMA VEZ
        from src.application.services import LandmarkDetectionService
        self.logger.info(f"Carregando modelo de landmarks: {self.settings.modelo_landmark.model_path}")
        landmark_service = LandmarkDetectionService(
            modelo_landmark_config=self.settings.modelo_landmark,
            device=device
        )
        self.logger.info(f"Modelo de landmarks carregado no {device}")
        
        # Cria workers que compartilham os mesmos modelos
        for worker_id in range(num_workers):
            use_case = DetectFacesUseCase(
                frame_queue=self.frame_queue,
                event_queue=self.event_queue,
                modelo_deteccao_config=self.settings.modelo_deteccao,
                tracking_config=self.settings.tracking,
                processing_config=self.settings.processing,
                performance_config=self.settings.performance,
                filter_config=self.settings.filter,
                gpu_id=worker_id,  # ID do worker
                landmark_service=landmark_service,  # Compartilhado
                stop_event=self.stop_event,
                display_config=self.settings.display,
                display_buffers=self.display_buffers,
                shared_model=detection_model,  # Modelo compartilhado
                queue_timeout=self.settings.workers.timeout
            )
            
            thread = threading.Thread(
                target=use_case.execute,
                name=f"Detector{worker_id}",
                daemon=False
            )
            thread.start()
            self.threads.append(thread)
            
        self.logger.info(f"  - {num_workers} workers de detecção iniciados")
    
    def _start_track_manager(self):
        """Inicia gerenciadores de tracks."""
        num_workers = self.settings.workers.track_workers
        self.logger.info(f"Iniciando {num_workers} gerenciadores de tracks...")
        
        for i in range(num_workers):
            use_case = ManageTracksUseCase(
                event_queue=self.event_queue,
                findface_queue=self.findface_queue,
                tracking_config=self.settings.tracking,
                track_config=self.settings.track,
                stop_event=self.stop_event,
                queue_timeout=self.settings.workers.timeout
            )
            
            thread = threading.Thread(
                target=use_case.execute,
                name=f"TrackManager{i}",
                daemon=False
            )
            thread.start()
            self.threads.append(thread)
        
        self.logger.info(f"  - {num_workers} gerenciadores de tracks iniciados")
    
    def _start_findface_workers(self):
        """Inicia workers de envio ao FindFace."""
        num_workers = self.settings.workers.findface_workers
        self.logger.info(f"Iniciando {num_workers} workers de envio ao FindFace...")
        
        for i in range(num_workers):
            use_case = SendToFindfaceUseCase(
                findface_queue=self.findface_queue,
                findface_client=self.findface_client,
                stop_event=self.stop_event,
                queue_timeout=self.settings.workers.timeout
            )
            
            thread = threading.Thread(
                target=use_case.execute,
                name=f"FindfaceSender{i}",
                daemon=False
            )
            thread.start()
            self.threads.append(thread)
        
        self.logger.info(f"  - {num_workers} workers de FindFace iniciados")
    
    def _start_camera_streams(self):
        """Inicia streams de câmeras (uma thread por câmera)."""
        self.logger.info("Iniciando streams de câmeras...")
        
        for camera in self.cameras:
            use_case = StreamCameraUseCase(
                camera=camera,
                frame_queue=self.frame_queue,
                camera_settings=self.settings.camera,
                performance_config=self.settings.performance,
                stop_event=self.stop_event
            )
            
            thread = threading.Thread(
                target=use_case.execute,
                name=f"Camera_{camera.camera_name.value()}",
                daemon=False
            )
            thread.start()
            self.threads.append(thread)
        
        self.logger.info(f"  - {len(self.cameras)} streams de câmeras iniciados")
    
    def _start_display_workers(self):
        """Inicia workers de display visual (um por câmera)."""
        self.logger.info("Iniciando workers de display visual...")
        
        for camera in self.cameras:
            camera_id = camera.camera_id.value()
            buffer = self.display_buffers[camera_id]
            
            use_case = DisplayCameraUseCase(
                camera_id=camera_id,
                buffer=buffer,
                display_service=self.display_service,
                config=self.settings.display
            )
            
            thread = threading.Thread(
                target=use_case.run,
                name=f"Display_{camera.camera_name.value()}",
                daemon=True  # Display pode ser interrompido a qualquer momento
            )
            thread.start()
            self.display_threads.append(thread)
        
        self.logger.info(f"  - {len(self.display_threads)} workers de display iniciados")
    
    def wait(self):
        """Aguarda todas as threads finalizarem."""
        self.logger.info("Aguardando threads finalizarem...")
        
        try:
            for thread in self.threads:
                # Usa join com timeout para permitir KeyboardInterrupt
                while thread.is_alive():
                    thread.join(timeout=0.5)
        except KeyboardInterrupt:
            # Propaga o KeyboardInterrupt para ser tratado no main
            raise
        
        self.logger.info("Todas as threads finalizadas")
    
    def stop(self):
        """Para a aplicação gracefully."""
        if self.stop_event.is_set():
            return
        
        self.logger.info("=" * 80)
        self.logger.info("PARANDO APLICAÇÃO...")
        self.logger.info("=" * 80)
        
        # Sinaliza parada
        self.stop_event.set()
        
        # Aguarda filas serem processadas
        self._wait_for_queues()
        
        # Aguarda threads
        self.wait()
        
        self.logger.info("=" * 80)
        self.logger.info("APLICAÇÃO FINALIZADA")
        self.logger.info("=" * 80)
    
    def _wait_for_queues(self, timeout: float = 10.0):
        """
        Aguarda filas serem processadas.
        
        :param timeout: Timeout máximo em segundos.
        """
        self.logger.info("Aguardando processamento de filas...")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if (self.frame_queue.empty() and 
                self.event_queue.empty() and 
                self.findface_queue.empty()):
                self.logger.info("Todas as filas processadas")
                return
            
            time.sleep(0.5)
        
        # Log de filas não processadas
        if not self.frame_queue.empty():
            self.logger.warning(f"Fila de frames possui {self.frame_queue.qsize()} itens não processados")
        if not self.event_queue.empty():
            self.logger.warning(f"Fila de eventos possui {self.event_queue.qsize()} itens não processados")
        if not self.findface_queue.empty():
            self.logger.warning(f"Fila do FindFace possui {self.findface_queue.qsize()} itens não processados")
