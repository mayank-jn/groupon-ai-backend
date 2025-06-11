#!/usr/bin/env python3
"""
Test script to demonstrate the source factory pattern and extensible adapters.
"""

from sources import SourceFactory
from sources.document_upload import DocumentUploadAdapter


def test_source_factory():
    print("=== Source Factory Pattern Test ===\n")
    
    # Register adapters
    SourceFactory.register_adapter('document_upload', DocumentUploadAdapter)
    
    print("1. Available Adapters:")
    adapters = SourceFactory.list_available_adapters()
    for adapter in adapters:
        print(f"   - {adapter}")
    print()
    
    print("2. Adapter Capabilities:")
    capabilities = SourceFactory.get_all_capabilities()
    for adapter_type, caps in capabilities.items():
        print(f"   {adapter_type}:")
        if 'status' in caps and caps['status'] == 'not_implemented':
            print(f"     Status: {caps['status']}")
            if 'planned_features' in caps:
                print(f"     Planned Features: {', '.join(caps['planned_features'])}")
        else:
            print(f"     Supported Formats: {caps.get('supported_formats', [])}")
            print(f"     Features: {caps.get('features', [])}")
            if 'processors' in caps:
                print(f"     Processors:")
                for proc in caps['processors']:
                    print(f"       - {proc['name']}: {proc['formats']}")
        print()
    
    print("3. Testing Document Upload Adapter:")
    try:
        # Get adapter instance
        config = {
            'embedding_model': 'text-embedding-3-small',
            'upload_dir': 'sample_docs'
        }
        adapter = SourceFactory.get_adapter('document_upload', config)
        
        print(f"   Adapter Type: {adapter.get_source_type()}")
        print(f"   Initialization: {'Success' if adapter.initialize() else 'Failed'}")
        
        # Test file validation
        test_files = ['test.pdf', 'test.docx', 'test.txt', 'test.xyz']
        print("   File Validation Tests:")
        for filename in test_files:
            # Create a mock file path for validation
            is_valid = any(
                proc.supports_format(filename.split('.')[-1] if '.' in filename else '')
                for proc in adapter.processors
            )
            print(f"     {filename}: {'✓' if is_valid else '✗'}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n4. Architecture Benefits:")
    print("   ✓ Separation of Concerns - Each adapter handles one source type")
    print("   ✓ Extensibility - Easy to add new source adapters")
    print("   ✓ Factory Pattern - Centralized adapter management")
    print("   ✓ Interface Compliance - All adapters follow same contract")
    print("   ✓ Pluggable Architecture - Adapters can be added/removed dynamically")
    
    print("\n5. Future Extensions Ready:")
    print("   → Confluence: Space/page crawling, API integration")
    print("   → Custom Sources: Any data source can be added easily")
    print("   → Clean Architecture: No unused placeholder code")


if __name__ == "__main__":
    test_source_factory() 