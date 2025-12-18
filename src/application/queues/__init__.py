"""
Filas thread-safe para comunicação entre componentes.
"""

from .frame_queue import FrameQueue
from .event_queue import EventQueue
from .findface_queue import FindfaceQueue

__all__ = ["FrameQueue", "EventQueue", "FindfaceQueue"]
