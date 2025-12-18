"""
Carregador de configurações.
Responsável por ler arquivos YAML e variáveis de ambiente,
convertendo-os em objetos de configuração type-safe.
"""

import os
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .settings import (
    AppSettings,
    FindFaceConfig,
    ModeloDeteccaoConfig,
    ModeloLandmarkConfig,
    TrackingConfig,
    ProcessingConfig,
    FilterConfig,
    TrackConfig,
    QueueConfig,
    CameraSettingsConfig,
    LoggingConfig,
    PerformanceConfig,
    WorkersConfig,
    DisplayConfig
)


class ConfigLoader:
    """Carrega configurações de arquivos e variáveis de ambiente."""
    
    @staticmethod
    def load_from_yaml(yaml_path: str = "config.yaml") -> dict:
        """
        Carrega configurações de arquivo YAML.
        
        :param yaml_path: Caminho para o arquivo YAML.
        :return: Dicionário com configurações.
        """
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {yaml_path}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    @staticmethod
    def load_from_env() -> FindFaceConfig:
        """
        Carrega configurações do FindFace de variáveis de ambiente.
        
        :return: Configuração do FindFace.
        :raises ValueError: Se variáveis obrigatórias não estiverem definidas.
        """
        load_dotenv()
        
        required_vars = ["FINDFACE_URL", "FINDFACE_USER", "FINDFACE_PASSWORD", "FINDFACE_UUID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}")
        
        return FindFaceConfig(
            url_base=os.getenv("FINDFACE_URL", ""),
            user=os.getenv("FINDFACE_USER", ""),
            password=os.getenv("FINDFACE_PASSWORD", ""),
            uuid=os.getenv("FINDFACE_UUID", "")
        )
    
    @classmethod
    def load(cls, yaml_path: str = "config.yaml") -> AppSettings:
        """
        Carrega todas as configurações da aplicação.
        
        :param yaml_path: Caminho para o arquivo YAML.
        :return: Objeto AppSettings completo.
        """
        # Carrega do YAML
        yaml_config = cls.load_from_yaml(yaml_path)
        
        # Carrega FindFace do .env
        findface_config = cls.load_from_env()
        
        # Modelo Detecção Config
        modelo_deteccao_data = yaml_config.get("modelo_deteccao", {})
        modelo_deteccao_config = ModeloDeteccaoConfig(
            model_path=modelo_deteccao_data.get("model_path", "yolo-models/yolov12n-face.pt"),
            confidence_threshold=modelo_deteccao_data.get("confidence_threshold", 0.5),
            iou_threshold=modelo_deteccao_data.get("iou_threshold", 0.75)
        )
        
        # Modelo Landmark Config
        modelo_landmark_data = yaml_config.get("modelo_landmark", {})
        modelo_landmark_config = ModeloLandmarkConfig(
            model_path=modelo_landmark_data.get("model_path", "yolo-models/yolov8n-face.pt"),
            confidence_threshold=modelo_landmark_data.get("confidence_threshold", 0.5),
            iou_threshold=modelo_landmark_data.get("iou_threshold", 0.45)
        )
        
        # Tracking Config
        tracking_data = yaml_config.get("tracking", {})
        tracking_config = TrackingConfig(
            iou_threshold=tracking_data.get("iou_threshold", 0.3),
            max_age=tracking_data.get("max_age", 30),
            min_hits=tracking_data.get("min_hits", 3),
            max_frames=tracking_data.get("max_frames", 500)
        )
        
        # Processing Config
        processing_data = yaml_config.get("processing", {})
        gpu_devices = processing_data.get("gpu_devices", [0])
        processing_config = ProcessingConfig(
            cpu_batch_size=processing_data.get("cpu_batch_size", 1),
            gpu_batch_size=processing_data.get("gpu_batch_size", 32),
            gpu_devices=gpu_devices if isinstance(gpu_devices, list) else [gpu_devices]
        )
        
        # Filter Config
        filter_data = yaml_config.get("filter", {})
        filter_config = FilterConfig(
            min_bbox_width=filter_data.get("min_bbox_width", 30),
            min_confidence=filter_data.get("min_confidence", 0.5)
        )
        
        # Track Config
        track_data = yaml_config.get("track", {})
        track_config = TrackConfig(
            min_movement_percentage=track_data.get("min_movement_percentage", 0.1),
            min_movement_pixels=track_data.get("min_movement_pixels", 50.0)
        )
        
        # Queue Config
        queue_data = yaml_config.get("queues", {})
        queue_config = QueueConfig(
            frame_queue_max_size=queue_data.get("frame_queue_max_size", 100),
            event_queue_max_size=queue_data.get("event_queue_max_size", 1000),
            findface_queue_max_size=queue_data.get("findface_queue_max_size", 100)
        )
        
        # Performance Config
        performance_data = yaml_config.get("performance", {})
        performance_config = PerformanceConfig(
            detection_skip_frames=performance_data.get("detection_skip_frames", 2),
            inference_size=performance_data.get("inference_size", 640)
        )
        
        # Camera Settings Config
        camera_data = yaml_config.get("camera", {})
        camera_config = CameraSettingsConfig(
            prefix=camera_data.get("prefix", "TESTE"),
            rtsp_reconnect_delay=camera_data.get("rtsp_reconnect_delay", 5),
            rtsp_max_retries=camera_data.get("rtsp_max_retries", 3)
        )
        
        # Logging Config
        logging_data = yaml_config.get("logging", {})
        logging_config = LoggingConfig(
            level=logging_data.get("level", "INFO"),
            format=logging_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        
        # Workers Config
        workers_data = yaml_config.get("workers", {})
        workers_config = WorkersConfig(
            detection_workers=workers_data.get("detection_workers") or 0,
            track_workers=workers_data.get("track_workers") or 0,
            findface_workers=workers_data.get("findface_workers") or 0
        )
        
        # Display Config
        display_data = yaml_config.get("display", {})
        display_config = DisplayConfig(
            exibir_na_tela=display_data.get("exibir_na_tela", False),
            window_width=display_data.get("window_width", 1280),
            window_height=display_data.get("window_height", 720),
            bbox_thickness=display_data.get("bbox_thickness", 2),
            font_scale=display_data.get("font_scale", 0.6),
            fps_limit=display_data.get("fps_limit", 30)
        )
        
        return AppSettings(
            findface=findface_config,
            modelo_deteccao=modelo_deteccao_config,
            modelo_landmark=modelo_landmark_config,
            tracking=tracking_config,
            processing=processing_config,
            filter=filter_config,
            track=track_config,
            queues=queue_config,
            performance=performance_config,
            camera=camera_config,
            logging=logging_config,
            workers=workers_config,
            display=display_config
        )