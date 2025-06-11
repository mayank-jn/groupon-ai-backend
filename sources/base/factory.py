"""
Source factory for creating and managing source adapters.
"""

from typing import Dict, Type, Any, Optional, List
from .interfaces import SourceAdapter


class SourceFactory:
    """Factory class for creating and managing source adapters."""
    
    _adapters: Dict[str, Type[SourceAdapter]] = {}
    _initialized_adapters: Dict[str, SourceAdapter] = {}
    
    @classmethod
    def register_adapter(cls, source_type: str, adapter_class: Type[SourceAdapter]) -> None:
        """Register a new source adapter class."""
        if not issubclass(adapter_class, SourceAdapter):
            raise ValueError(f"Adapter class must inherit from SourceAdapter")
        
        cls._adapters[source_type] = adapter_class
        print(f"Registered source adapter: {source_type}")
    
    @classmethod
    def get_adapter(cls, source_type: str, config: Optional[Dict[str, Any]] = None) -> SourceAdapter:
        """Get an instance of the specified source adapter."""
        if source_type not in cls._adapters:
            raise ValueError(f"Unknown source adapter type: {source_type}")
        
        # Return existing initialized adapter if available and config hasn't changed
        cache_key = f"{source_type}_{hash(str(sorted((config or {}).items())))}"
        if cache_key in cls._initialized_adapters:
            return cls._initialized_adapters[cache_key]
        
        # Create new adapter instance
        adapter_class = cls._adapters[source_type]
        adapter = adapter_class(config)
        
        # Initialize the adapter
        if not adapter.initialize():
            raise RuntimeError(f"Failed to initialize source adapter: {source_type}")
        
        # Cache the initialized adapter
        cls._initialized_adapters[cache_key] = adapter
        return adapter
    
    @classmethod
    def list_available_adapters(cls) -> List[str]:
        """Get list of all registered adapter types."""
        return list(cls._adapters.keys())
    
    @classmethod
    def get_adapter_capabilities(cls, source_type: str) -> Dict[str, Any]:
        """Get capabilities of a specific adapter type without initializing it."""
        if source_type not in cls._adapters:
            raise ValueError(f"Unknown source adapter type: {source_type}")
        
        # Create temporary instance to get capabilities
        adapter_class = cls._adapters[source_type]
        temp_adapter = adapter_class()
        capabilities = temp_adapter.get_capabilities()
        temp_adapter.cleanup()
        
        return capabilities
    
    @classmethod
    def cleanup_all(cls) -> None:
        """Cleanup all initialized adapters."""
        for adapter in cls._initialized_adapters.values():
            try:
                adapter.cleanup()
            except Exception as e:
                print(f"Error cleaning up adapter: {e}")
        
        cls._initialized_adapters.clear()
    
    @classmethod
    def get_all_capabilities(cls) -> Dict[str, Dict[str, Any]]:
        """Get capabilities of all registered adapters."""
        capabilities = {}
        for source_type in cls._adapters.keys():
            try:
                capabilities[source_type] = cls.get_adapter_capabilities(source_type)
            except Exception as e:
                capabilities[source_type] = {"error": str(e)}
        
        return capabilities 