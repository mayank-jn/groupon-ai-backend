"""
Base interfaces for source adapters.

This module defines the abstract base classes that all source adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourceResult:
    """Result object returned by source adapters."""
    content: str
    metadata: Dict[str, Any]
    source_type: str
    source_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""
    
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        pass
    
    @abstractmethod
    def process_document(self, file_path: str, filename: str) -> SourceResult:
        """Process a document and return structured content."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        pass


class SourceAdapter(ABC):
    """Abstract base class for all source adapters."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Return the type of this source adapter."""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the source adapter. Return True if successful."""
        pass
    
    @abstractmethod
    def process_source(self, source_input: Any, **kwargs) -> List[SourceResult]:
        """Process input from this source and return list of SourceResult objects."""
        pass
    
    @abstractmethod
    def validate_input(self, source_input: Any) -> bool:
        """Validate that the input is appropriate for this source adapter."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return information about this adapter's capabilities."""
        pass
    
    def cleanup(self) -> None:
        """Optional cleanup method. Override if needed."""
        pass 