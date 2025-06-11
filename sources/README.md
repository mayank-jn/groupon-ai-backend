# Source Adapters Architecture

This package implements an extensible factory pattern for source adapters, enabling easy integration of different data sources into the Groupon AI Knowledge Assistant.

## Architecture Overview

```
sources/
├── base/
│   ├── interfaces.py          # Abstract base classes
│   └── factory.py             # Source factory
├── document_upload/           # Document upload adapter ✅
│   ├── adapter.py            
│   └── processors/           # Format-specific processors
│       ├── pdf_processor.py
│       ├── docx_processor.py
│       └── text_processor.py
└── confluence/               # Future: Confluence integration 🚧
```

## Core Interfaces

### SourceAdapter (Abstract Base Class)
All source adapters must implement:
- `get_source_type()` - Return adapter type identifier
- `initialize()` - Setup and validate adapter
- `validate_input()` - Check if input is valid for this adapter
- `process_source()` - Process input and return SourceResult objects
- `get_capabilities()` - Return adapter capabilities and features

### DocumentProcessor (Abstract Base Class)
Document processors must implement:
- `supports_format()` - Check if file format is supported
- `process_document()` - Extract content and metadata
- `get_supported_formats()` - List of supported file extensions

### SourceResult (Data Class)
Standardized result object containing:
- `content` - Extracted text content
- `metadata` - Processing and file metadata
- `source_type` - Type of source adapter
- `source_id` - Unique identifier
- `title`, `author`, `created_date`, `updated_date` - Optional metadata
- `url`, `tags` - Additional metadata

## Factory Pattern

### Registration
```python
from sources import SourceFactory
from sources.document_upload import DocumentUploadAdapter

# Register adapter
SourceFactory.register_adapter('document_upload', DocumentUploadAdapter)
```

### Usage
```python
# Get adapter instance
adapter = SourceFactory.get_adapter('document_upload', config)

# Process source
results = adapter.process_source(input_data)
```

### Factory Features
- **Adapter Registration** - Dynamic adapter registration
- **Instance Caching** - Reuse initialized adapters
- **Capability Discovery** - Query adapter capabilities
- **Error Handling** - Graceful failure handling

## Current Implementation

### Document Upload Adapter ✅
- **Supported Formats**: PDF, DOCX, TXT, MD
- **Features**: 
  - Conditional chunking based on token limits
  - Metadata extraction
  - Multiple file format processors
  - Automatic format detection

#### Processors:
- **PDFProcessor**: PyPDF2-based text extraction with metadata
- **DOCXProcessor**: python-docx with document properties
- **TextProcessor**: Plain text and Markdown with encoding detection

## Future Implementation

### Confluence Adapter 🚧
**Planned Features**:
- Space crawling and page retrieval
- Content extraction from Confluence markup
- Metadata extraction (author, dates, labels)
- Incremental sync capabilities

**Configuration**:
```python
config = {
    'confluence_url': 'https://company.atlassian.net',
    'api_token': 'your_token',
    'username': 'your_username'
}
```



## Usage Examples

### Basic Document Upload
```python
# Initialize factory
SourceFactory.register_adapter('document_upload', DocumentUploadAdapter)

# Get adapter
adapter = SourceFactory.get_adapter('document_upload', {
    'embedding_model': 'text-embedding-3-small',
    'upload_dir': 'sample_docs'
})

# Process file
results = adapter.process_source(uploaded_file)

# Each result contains chunked content ready for embedding
for result in results:
    print(f"Chunk: {result.content[:100]}...")
    print(f"Metadata: {result.metadata}")
```

### Adding Custom Adapter
```python
class CustomAdapter(SourceAdapter):
    def get_source_type(self):
        return 'custom_source'
    
    def initialize(self):
        # Setup custom source connection
        return True
    
    def validate_input(self, source_input):
        # Validate input format
        return True
    
    def process_source(self, source_input, **kwargs):
        # Process and return SourceResult objects
        return [SourceResult(...)]
    
    def get_capabilities(self):
        return {'source_type': 'custom_source', 'features': [...]}

# Register and use
SourceFactory.register_adapter('custom_source', CustomAdapter)
```

## Benefits

### Separation of Concerns ✅
- Each adapter handles one specific source type
- Document processors are separated by file format
- Clear interface boundaries

### Extensibility ✅
- Easy to add new source types
- Pluggable architecture
- No modification of existing code required

### Maintainability ✅
- Standardized interfaces
- Consistent error handling
- Centralized adapter management

### Testability ✅
- Each component can be tested independently
- Mock adapters for testing
- Clear input/output contracts

## Testing

Run the test script to verify the factory pattern:
```bash
python test_source_factory.py
```

This will demonstrate:
- Adapter registration and discovery
- Capability querying
- Input validation
- Architecture benefits

## API Integration

The factory pattern is integrated into the FastAPI endpoints:

- `POST /upload` - Uses document_upload adapter
- `GET /sources` - Lists all available adapters
- `GET /document-info` - Shows adapter capabilities

This architecture enables seamless extension to new data sources while maintaining clean separation of concerns and consistent interfaces. 