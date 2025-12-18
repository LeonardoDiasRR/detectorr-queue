"""
Objeto de configuração centralizado.
Fornece acesso type-safe às configurações.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class CameraConfig:
    """Configuração de uma câmera individual."""
    id: int
    name: str
    url: str
    token: str = ""


@dataclass
class ModeloDeteccaoConfig:
    """Configuração do modelo de detecção."""
    model_path: str = "yolo-models/yolov12n-face.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.75


@dataclass
class ModeloLandmarkConfig:
    """Configuração do modelo de landmarks."""
    model_path: str = "yolo-models/yolov8n-face.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45


@dataclass
class TrackingConfig:
    """Configuração do rastreamento (ByteTrack)."""
    iou_threshold: float = 0.3
    max_age: int = 30
    min_hits: int = 3
    max_frames: int = 500


@dataclass
class FindFaceConfig:
    """Configuração do FindFace."""
    url_base: str
    user: str
    password: str
    uuid: str


@dataclass
class ProcessingConfig:
    """Configuração de processamento."""
    cpu_batch_size: int = 1
    gpu_batch_size: int = 32
    gpu_devices: List[int] = None
    
    def __post_init__(self):
        """Inicializa valores padrão após criação."""
        if self.gpu_devices is None:
            self.gpu_devices = [0]


@dataclass
class StorageConfig:
    """Configuração de armazenamento."""
    save_images: bool = True
    project_dir: str = "./imagens/"
    results_dir: str = "rtsp_byte_track_results"


@dataclass
class TrackConfig:
    """Configuração de track."""
    min_movement_percentage: float = 0.1
    min_movement_pixels: float = 50.0


@dataclass
class FilterConfig:
    """Configuração de filtros de detecção."""
    min_bbox_width: int = 30
    min_confidence: float = 0.5


@dataclass
class PerformanceConfig:
    """Configuração de otimizações de performance."""
    detection_skip_frames: int = 2
    inference_size: int = 640


@dataclass
class QueueConfig:
    """Configuração de filas."""
    frame_queue_max_size: int = 128
    event_queue_max_size: int = 128
    findface_queue_max_size: int = 128


@dataclass
class CameraSettingsConfig:
    """Configuração de câmeras."""
    prefix: str = "TESTE"
    rtsp_reconnect_delay: int = 5
    rtsp_max_retries: int = 3


@dataclass
class DisplayConfig:
    """Configuração de exibição visual."""
    exibir_na_tela: bool = False
    window_width: int = 1280
    window_height: int = 720
    bbox_thickness: int = 2
    font_scale: float = 0.6
    fps_limit: int = 30


@dataclass
class WorkersConfig:
    """Configuração de workers."""
    detection_workers: int = 0
    track_workers: int = 0
    findface_workers: int = 0
    timeout: float = 0.5
    
    def __post_init__(self):
        """Calcula número de workers baseado em CPUs se não especificado."""
        import os
        cpu_count = os.cpu_count() or 8
        
        # detection_workers: min 4, max N (cpu_count)
        max_detection_workers = max(4, cpu_count)
        # track e findface workers: min 4, max N/2
        max_workers = max(4, cpu_count // 2)
        
        if self.detection_workers == 0:
            self.detection_workers = max_detection_workers
        if self.track_workers == 0:
            self.track_workers = max_workers
        if self.findface_workers == 0:
            self.findface_workers = max_workers


@dataclass
class LoggingConfig:
    """Configuração de logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class TensorRTConfig:
    """Configuração do TensorRT."""
    enabled: bool = True
    precision: str = "FP16"  # FP16, FP32, INT8
    workspace: int = 4  # Workspace em GB


@dataclass
class OpenVINOConfig:
    """Configuração do OpenVINO."""
    enabled: bool = True
    device: str = "AUTO"  # AUTO, CPU, GPU, NPU
    precision: str = "FP16"  # FP16, FP32, INT8


@dataclass
class AppSettings:
    """
    Configurações completas da aplicação.
    Objeto imutável que centraliza todas as configurações.
    """
    findface: FindFaceConfig
    modelo_deteccao: ModeloDeteccaoConfig
    modelo_landmark: ModeloLandmarkConfig
    tracking: TrackingConfig
    processing: ProcessingConfig
    filter: FilterConfig
    track: TrackConfig
    queues: QueueConfig
    performance: PerformanceConfig
    camera: CameraSettingsConfig
    logging: LoggingConfig
    workers: WorkersConfig
    display: DisplayConfig
    
    @property
    def device(self) -> str:
        """Retorna o dispositivo a ser usado (cuda ou cpu).
        
        Nota: Em configurações multi-GPU, retorna a primeira GPU da lista.
        O dispositivo específico é definido no momento da criação do modelo.
        """
        import torch
        if torch.cuda.is_available():
            return f"cuda:{self.processing.gpu_devices[0]}"
        return "cpu"
    
    @property
    def batch_size(self) -> int:
        """Retorna o batch size baseado no dispositivo."""
        if self.device.startswith("cuda"):
            return self.processing.gpu_batch_size
        return self.processing.cpu_batch_size