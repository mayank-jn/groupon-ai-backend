"""
Source adapters package for Groupon AI Knowledge Assistant.

This package provides extensible source adapters for different data sources
like document uploads, Confluence, and other custom sources.
"""

from .base.factory import SourceFactory
from .base.interfaces import SourceAdapter, DocumentProcessor, SourceResult

__all__ = [
    'SourceFactory',
    'SourceAdapter', 
    'DocumentProcessor',
    'SourceResult'
] 