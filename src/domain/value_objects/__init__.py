"""
Value Objects para o domínio da aplicação.
"""

from .id_vo import IdVO
from .name_vo import NameVO
from .camera_token_vo import CameraTokenVO
from .camera_source_vo import CameraSourceVO
from .bbox_vo import BboxVO
from .confidence_vo import ConfidenceVO
from .landmarks_vo import LandmarksVO
from .timestamp_vo import TimestampVO
from .full_frame_vo import FullFrameVO

__all__ = [
    'IdVO',
    'NameVO',
    'CameraTokenVO',
    'CameraSourceVO',
    'BboxVO',
    'ConfidenceVO',
    'LandmarksVO',
    'TimestampVO',
    'FullFrameVO',
]
