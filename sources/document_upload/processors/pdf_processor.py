"""
PDF document processor.
"""

import os
from datetime import datetime
from typing import List
import PyPDF2

from sources.base.interfaces import DocumentProcessor, SourceResult


class PDFProcessor(DocumentProcessor):
    """Processor for PDF documents."""
    
    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        return file_extension.lower() == '.pdf'
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return ['.pdf']
    
    def process_document(self, file_path: str, filename: str) -> SourceResult:
        """Process a PDF document and return structured content."""
        try:
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(open(file_path, "rb"))
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Get file metadata
            file_stats = os.stat(file_path)
            created_date = datetime.fromtimestamp(file_stats.st_ctime)
            updated_date = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Try to get PDF metadata
            title = filename
            author = None
            try:
                if pdf_reader.metadata:
                    title = pdf_reader.metadata.get('/Title', filename)
                    author = pdf_reader.metadata.get('/Author', None)
            except:
                pass  # Ignore metadata extraction errors
            
            return SourceResult(
                content=full_text.strip(),
                metadata={
                    'file_path': file_path,
                    'file_size': file_stats.st_size,
                    'page_count': len(pdf_reader.pages),
                    'processor': 'PDFProcessor'
                },
                source_type='document_upload',
                source_id=f"pdf_{filename}_{file_stats.st_mtime}",
                title=title,
                author=author,
                created_date=created_date,
                updated_date=updated_date,
                tags=['pdf', 'document']
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to process PDF {filename}: {str(e)}") 