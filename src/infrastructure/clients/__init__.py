"""
Clientes externos (Infrastructure Layer).
"""

from .findface_multi import FindfaceMulti
from .findface_async import FindfaceMultiAsync

__all__ = ['FindfaceMulti', 'FindfaceMultiAsync']
