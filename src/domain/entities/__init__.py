"""
Entidades do domínio da aplicação.
"""

from .camera_entity import Camera
from .frame_entity import Frame
from .event_entity import Event
from .track_entity import Track

__all__ = [
    'Camera',
    'Frame',
    'Event',
    'Track',
]
