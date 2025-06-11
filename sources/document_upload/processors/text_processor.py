"""
Text document processor for TXT and MD files.
"""

import os
from datetime import datetime
from typing import List

from sources.base.interfaces import DocumentProcessor, SourceResult


class TextProcessor(DocumentProcessor):
    """Processor for text documents (TXT, MD)."""
    
    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        return file_extension.lower() in ['.txt', '.md']
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return ['.txt', '.md']
    
    def process_document(self, file_path: str, filename: str) -> SourceResult:
        """Process a text document and return structured content."""
        try:
            # Read text file
            with open(file_path, 'r', encoding='utf-8') as file:
                full_text = file.read()
            
            # Get file metadata
            file_stats = os.stat(file_path)
            created_date = datetime.fromtimestamp(file_stats.st_ctime)
            updated_date = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Determine document type and tags
            file_extension = os.path.splitext(filename)[1].lower()
            tags = ['text', 'document']
            if file_extension == '.md':
                tags.append('markdown')
            elif file_extension == '.txt':
                tags.append('plaintext')
            
            # Extract title from filename or first line for markdown
            title = filename
            if file_extension == '.md' and full_text.strip():
                first_line = full_text.strip().split('\n')[0]
                if first_line.startswith('#'):
                    title = first_line.lstrip('#').strip()
            
            return SourceResult(
                content=full_text.strip(),
                metadata={
                    'file_path': file_path,
                    'file_size': file_stats.st_size,
                    'line_count': len(full_text.splitlines()),
                    'encoding': 'utf-8',
                    'processor': 'TextProcessor'
                },
                source_type='document_upload',
                source_id=f"text_{filename}_{file_stats.st_mtime}",
                title=title,
                created_date=created_date,
                updated_date=updated_date,
                tags=tags
            )
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    full_text = file.read()
                
                file_stats = os.stat(file_path)
                created_date = datetime.fromtimestamp(file_stats.st_ctime)
                updated_date = datetime.fromtimestamp(file_stats.st_mtime)
                
                return SourceResult(
                    content=full_text.strip(),
                    metadata={
                        'file_path': file_path,
                        'file_size': file_stats.st_size,
                        'line_count': len(full_text.splitlines()),
                        'encoding': 'latin-1',
                        'processor': 'TextProcessor'
                    },
                    source_type='document_upload',
                    source_id=f"text_{filename}_{file_stats.st_mtime}",
                    title=filename,
                    created_date=created_date,
                    updated_date=updated_date,
                    tags=['text', 'document']
                )
            except Exception as e:
                raise RuntimeError(f"Failed to process text file {filename}: {str(e)}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to process text file {filename}: {str(e)}") 