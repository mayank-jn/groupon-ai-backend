"""
Document upload source adapter.

This adapter handles document uploads and processes them using appropriate processors.
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from sources.base.interfaces import SourceAdapter, SourceResult
from .processors import PDFProcessor, DOCXProcessor, TextProcessor
from ingest.pdf_ingest import chunk_text_conditionally, count_tokens


class DocumentUploadAdapter(SourceAdapter):
    """Source adapter for document uploads."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.processors = [
            PDFProcessor(),
            DOCXProcessor(),
            TextProcessor()
        ]
        self.embedding_model = config.get('embedding_model', 'text-embedding-3-small') if config else 'text-embedding-3-small'
        self.upload_dir = config.get('upload_dir', 'sample_docs') if config else 'sample_docs'
    
    def get_source_type(self) -> str:
        """Return the type of this source adapter."""
        return 'document_upload'
    
    def initialize(self) -> bool:
        """Initialize the source adapter."""
        try:
            # Ensure upload directory exists
            os.makedirs(self.upload_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"Failed to initialize DocumentUploadAdapter: {e}")
            return False
    
    def validate_input(self, source_input: Any) -> bool:
        """Validate that the input is appropriate for this source adapter."""
        if isinstance(source_input, (UploadFile, StarletteUploadFile)):
            filename = source_input.filename
            if filename:
                file_extension = os.path.splitext(filename)[1].lower()
                return any(processor.supports_format(file_extension) for processor in self.processors)
        elif isinstance(source_input, str):
            # File path validation
            if os.path.exists(source_input):
                file_extension = os.path.splitext(source_input)[1].lower()
                return any(processor.supports_format(file_extension) for processor in self.processors)
        
        return False
    
    def process_source(self, source_input: Any, **kwargs) -> List[SourceResult]:
        """Process input from this source and return list of SourceResult objects."""
        if isinstance(source_input, (UploadFile, StarletteUploadFile)):
            return self._process_upload_file(source_input, **kwargs)
        elif isinstance(source_input, str):
            return self._process_file_path(source_input, **kwargs)
        else:
            raise ValueError(f"Unsupported input type: {type(source_input)}")
    
    def _process_upload_file(self, upload_file, **kwargs) -> List[SourceResult]:
        """Process an uploaded file."""
        if not upload_file.filename:
            raise ValueError("Upload file must have a filename")
        
        # Save the uploaded file
        file_path = os.path.join(self.upload_dir, upload_file.filename)
        
        # Read file content
        file_content = upload_file.file.read()
        
        # Write to disk
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Reset file pointer for potential future use
        upload_file.file.seek(0)
        
        # Process the saved file
        return self._process_file_path(file_path, **kwargs)
    
    def _process_file_path(self, file_path: str, **kwargs) -> List[SourceResult]:
        """Process a file from file path."""
        filename = os.path.basename(file_path)
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Find appropriate processor
        processor = None
        for proc in self.processors:
            if proc.supports_format(file_extension):
                processor = proc
                break
        
        if not processor:
            raise ValueError(f"No processor found for file type: {file_extension}")
        
        # Process the document
        source_result = processor.process_document(file_path, filename)
        
        # Apply conditional chunking to the content
        original_token_count = count_tokens(source_result.content, model=self.embedding_model)
        chunks = chunk_text_conditionally(source_result.content, model=self.embedding_model)
        
        # Create SourceResult objects for each chunk
        results = []
        for i, chunk in enumerate(chunks):
            chunk_result = SourceResult(
                content=chunk,
                metadata={
                    **source_result.metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'original_token_count': original_token_count,
                    'chunk_token_count': count_tokens(chunk, model=self.embedding_model),
                    'was_chunked': len(chunks) > 1
                },
                source_type=source_result.source_type,
                source_id=f"{source_result.source_id}_chunk_{i}" if len(chunks) > 1 else source_result.source_id,
                title=source_result.title,
                author=source_result.author,
                created_date=source_result.created_date,
                updated_date=source_result.updated_date,
                url=source_result.url,
                tags=source_result.tags
            )
            results.append(chunk_result)
        
        return results
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return information about this adapter's capabilities."""
        all_formats = []
        for processor in self.processors:
            all_formats.extend(processor.get_supported_formats())
        
        return {
            'source_type': self.get_source_type(),
            'supported_formats': all_formats,
            'features': [
                'file_upload',
                'conditional_chunking',
                'metadata_extraction',
                'multiple_formats'
            ],
            'embedding_model': self.embedding_model,
            'upload_directory': self.upload_dir,
            'processors': [
                {
                    'name': proc.__class__.__name__,
                    'formats': proc.get_supported_formats()
                }
                for proc in self.processors
            ]
        }
    
    def cleanup(self) -> None:
        """Optional cleanup method."""
        # Nothing specific to cleanup for document upload adapter
        pass 