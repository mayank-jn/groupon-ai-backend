"""
Base interfaces and factory for source adapters.
"""

from .interfaces import SourceAdapter, DocumentProcessor, SourceResult
from .factory import SourceFactory

__all__ = ['SourceAdapter', 'DocumentProcessor', 'SourceResult', 'SourceFactory'] 