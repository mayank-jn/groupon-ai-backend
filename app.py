# app.py

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from sources import SourceFactory
from sources.document_upload import DocumentUploadAdapter
from sources.confluence import ConfluenceAdapter
from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME
from retrieval.openai_assistant import answer as assistant_answer, reset_thread
import os
import openai

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Source type mapping from user-friendly names to metadata source_type values
SOURCE_TYPE_MAPPING = {
    "all": None,  # No filtering
    "engineering_docs": ["document_upload"],  # Document uploads
    "confluence_docs": ["confluence"],  # Confluence pages
    "jira_tickets": ["jira"],  # Future JIRA integration
}

def get_source_types_filter(source: str) -> Optional[List[str]]:
    """Convert user-friendly source name to list of source_type values for filtering."""
    if source == "engineering_docs":
        return ["document_upload"]  # After migration, all docs will have proper source_type
    elif source == "confluence_docs":
        return ["confluence"]
    elif source == "jira_tickets":
        return ["jira"]
    elif source == "all":
        return None  # No filtering
    else:
        return None

# Pydantic models for Confluence source inputs
class ConfluenceSpaceInput(BaseModel):
    """Input for processing an entire Confluence space."""
    space_key: str = Field(..., description="The Confluence space key (e.g., 'ENGINEERING')")
    title_filter: Optional[str] = Field(None, description="Filter pages by title containing this text")
    label_filter: Optional[str] = Field(None, description="Filter pages by this label")

class ConfluencePageInput(BaseModel):
    """Input for processing a specific Confluence page."""
    page_id: str = Field(..., description="The Confluence page ID")

class ConfluenceSearchInput(BaseModel):
    """Input for searching Confluence content."""
    search_query: str = Field(..., description="Search terms to find pages")
    space_key: Optional[str] = Field(None, description="Optional: restrict search to specific space")

class ConfluenceUrlInput(BaseModel):
    """Input for processing a page from its URL."""
    page_url: str = Field(..., description="Full URL to the Confluence page")

# Union type for all possible Confluence inputs
ConfluenceSourceInput = Union[ConfluenceSpaceInput, ConfluencePageInput, ConfluenceSearchInput, ConfluenceUrlInput]

# Search request model
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    source: str = Field("all", description="Source to search in: 'all', 'engineering_docs', 'confluence_docs', 'jira_tickets'")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "query": "How to deploy services?",
                    "source": "all"
                },
                {
                    "query": "Project planning template",
                    "source": "confluence_docs"
                },
                {
                    "query": "API documentation",
                    "source": "engineering_docs"
                }
            ]
        }

# Minimal request model - authentication handled via environment variables
class ConfluenceIngestRequest(BaseModel):
    source_input: ConfluenceSourceInput = Field(..., description="What to ingest from Confluence")
    max_pages: Optional[int] = Field(100, description="Maximum number of pages to process")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "source_input": {"space_key": "Engineering"},
                    "max_pages": 50
                },
                {
                    "source_input": {"page_id": "123456789"}
                },
                {
                    "source_input": {"search_query": "API documentation"}
                }
            ]
        }

app = FastAPI(
    title="Groupon AI Knowledge Assistant Backend", 
    description="AI-powered knowledge assistant using OpenAI Assistant APIs with Qdrant vector search and extensible source adapters", 
    version="3.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:3000",
        "https://groupon-ai-frontend-1167.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load vector store once at startup
vector_store = VectorStore()

# Register source adapters
SourceFactory.register_adapter('document_upload', DocumentUploadAdapter)
SourceFactory.register_adapter('confluence', ConfluenceAdapter)

@app.post("/upload")
async def upload_doc(file: UploadFile = File(...)):
    try:
        # Get document upload adapter
        adapter = SourceFactory.get_adapter('document_upload', {
            'embedding_model': EMBEDDING_MODEL_NAME,
            'upload_dir': 'sample_docs'
        })
        
        # Validate input
        if not adapter.validate_input(file):
            return {"status": "error", "message": f"Unsupported file type: {file.filename}"}
        
        # Process the document
        source_results = adapter.process_source(file)
        
        # Prepare data for embedding
        chunks = [result.content for result in source_results]
        
        # Generate embeddings
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL_NAME,
            input=chunks
        )
        embeddings = [d.embedding for d in response.data]

        # Cloud safe collection create
        vector_store.create_collection_if_not_exists(vector_size=len(embeddings[0]))
        
        # Create metadata for vector store
        metadatas = []
        for i, result in enumerate(source_results):
            # Extract file extension for improved compatibility
            file_extension = os.path.splitext(file.filename)[1].lower().lstrip('.') if file.filename else 'unknown'
            
            metadata = {
                # Core content fields
                "text": result.content,
                "source": result.title or file.filename,
                "source_type": result.source_type,
                "source_id": result.source_id,
                "title": result.title or file.filename,
                
                # File-specific metadata for backward compatibility
                "file_type": file_extension,  # e.g., 'pdf', 'docx', 'txt'
                "filename": file.filename,
                "file_extension": file_extension,
                
                # Content processing metadata
                "chunk_index": result.metadata.get('chunk_index', 0),
                "total_chunks": result.metadata.get('total_chunks', 1),
                "was_chunked": result.metadata.get('was_chunked', False),
                "original_token_count": result.metadata.get('original_token_count'),
                "chunk_token_count": result.metadata.get('chunk_token_count'),
                
                # Processing information
                "processor": result.metadata.get('processor', 'DocumentUploadAdapter'),
                "embedding_model": EMBEDDING_MODEL_NAME,
                "ingested_at": datetime.utcnow().isoformat(),
                
                # File system metadata
                "file_size": result.metadata.get('file_size'),
                "file_path": result.metadata.get('file_path'),
                
                # Timestamps 
                "created": result.created_date.isoformat() if result.created_date else None,
                "last_modified": result.updated_date.isoformat() if result.updated_date else None,
                
                # Author and categorization
                "author": result.author,
                "tags": result.tags or [file_extension, 'document'],
                
                # Access control (for consistency with Confluence)
                "allowed_user_ids": [],
                "visibility": "internal",
            }
            
            # Add format-specific metadata
            if file_extension == 'pdf':
                metadata["page_count"] = result.metadata.get('page_count')
            
            metadatas.append(metadata)
        
        vector_store.upsert_embeddings(embeddings, metadatas)
        
        # Get processing information from first result
        first_result = source_results[0]
        was_chunked = first_result.metadata.get('was_chunked', False)
        original_token_count = first_result.metadata.get('original_token_count', 0)
        
        return {
            "status": "success", 
            "chunks_uploaded": len(chunks), 
            "doc_title": first_result.title or file.filename,
            "was_chunked": was_chunked,
            "processing_method": "chunked" if was_chunked else "single_embedding",
            "original_token_count": original_token_count,
            "embedding_token_limit": 8000,
            "source_type": first_result.source_type,
            "processor_used": first_result.metadata.get('processor', 'unknown')
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/confluence/ingest")
async def ingest_confluence(request: ConfluenceIngestRequest):
    """Ingest content from Confluence into the knowledge base.
    
    Authentication is handled automatically via environment variables:
    - CONFLUENCE_URL
    - CONFLUENCE_USERNAME  
    - CONFLUENCE_API_TOKEN
    """
    try:
        # Build configuration from environment variables
        confluence_config = {
            'confluence_url': os.getenv('CONFLUENCE_URL'),
            'username': os.getenv('CONFLUENCE_USERNAME'),
            'api_token': os.getenv('CONFLUENCE_API_TOKEN'),
            'embedding_model': EMBEDDING_MODEL_NAME,
            'max_pages': request.max_pages
        }
        
        # Validate required environment variables
        required_env_vars = ['CONFLUENCE_URL', 'CONFLUENCE_USERNAME', 'CONFLUENCE_API_TOKEN']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            return {
                "status": "error", 
                "message": f"Missing required environment variables: {', '.join(missing_vars)}",
                "note": "Set these in your .env file for automatic authentication"
            }
        
        try:
            adapter = SourceFactory.get_adapter('confluence', confluence_config)
        except Exception as adapter_error:
            return {"status": "error", "message": f"Failed to create Confluence adapter: {str(adapter_error)}", "config_debug": {k: v if k != 'api_token' else f"{v[:10]}..." if v else None for k, v in confluence_config.items()}}
        
        # The adapter is already initialized by SourceFactory.get_adapter()
        # No need to call initialize() again
        
        # Convert Pydantic model to dict for adapter processing
        source_input = request.source_input.model_dump()
        if not adapter.validate_input(source_input):
            return {"status": "error", "message": "Invalid source input provided"}
        
        # Process Confluence content
        source_results = adapter.process_source(source_input)
        
        if not source_results:
            return {"status": "error", "message": "No content found or processed"}
        
        # Prepare data for embedding
        chunks = [result.content for result in source_results]
        
        # Generate embeddings
        response = openai.embeddings.create(
            model=EMBEDDING_MODEL_NAME,
            input=chunks
        )
        embeddings = [d.embedding for d in response.data]

        # Cloud safe collection create
        vector_store.create_collection_if_not_exists(vector_size=len(embeddings[0]))
        
        # Create enhanced metadata for vector store with version tracking
        metadatas = []
        for i, result in enumerate(source_results):
            metadata = {
                # Content and identification
                "text": result.content,
                "source": result.title or f"Confluence Page {result.source_id}",
                "source_type": result.source_type,
                "source_id": result.source_id,
                "title": result.title,
                
                # Confluence-specific metadata
                "page_id": result.metadata.get('page_id'),
                "space_key": result.metadata.get('space_key'),
                "space_name": result.metadata.get('space_name'),
                
                # Version tracking (critical for detecting stale embeddings)
                "version": result.metadata.get('version_number'),
                "version_when": result.metadata.get('version_when'),
                "last_modified": result.metadata.get('last_modified'),
                "created": result.metadata.get('creation_date'),
                
                # Author information
                "author": result.author,
                "author_id": result.metadata.get('author_id'),
                
                # Content processing metadata
                "chunk_index": result.metadata.get('chunk_index', 0),
                "total_chunks": result.metadata.get('total_chunks', 1),
                "was_chunked": result.metadata.get('was_chunked', False),
                "original_token_count": result.metadata.get('original_token_count'),
                "chunk_token_count": result.metadata.get('chunk_token_count'),
                
                # Processing info
                "processor": result.metadata.get('processor', 'ConfluenceAdapter'),
                "embedding_model": EMBEDDING_MODEL_NAME,
                "ingested_at": datetime.utcnow().isoformat(),
                
                # Access control (prepared for future use)
                "allowed_user_ids": [],  # To be populated when implementing access control
                "visibility": "internal",  # Default visibility level
            }
            
            # Add optional fields
            if result.tags:
                metadata["tags"] = result.tags
            if result.url:
                metadata["url"] = result.url
                
            metadatas.append(metadata)
        
        vector_store.upsert_embeddings(embeddings, metadatas)
        
        # Get processing summary
        total_pages = len(set(result.metadata.get('page_id') for result in source_results))
        total_chunks = len(source_results)
        spaces = list(set(result.metadata.get('space_key') for result in source_results if result.metadata.get('space_key')))
        
        return {
            "status": "success",
            "pages_processed": total_pages,
            "chunks_uploaded": total_chunks,
            "spaces": spaces,
            "source_type": "confluence",
            "embedding_model": EMBEDDING_MODEL_NAME,
            "processing_summary": {
                "total_pages": total_pages,
                "total_chunks": total_chunks,
                "avg_chunks_per_page": round(total_chunks / total_pages, 2) if total_pages > 0 else 0
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/search")
async def search_query(request: SearchRequest):
    """Search endpoint using OpenAI's Assistants API with source filtering."""
    # Validate source parameter
    if request.source not in SOURCE_TYPE_MAPPING:
        return {
            "error": f"Invalid source '{request.source}'. Valid options: {list(SOURCE_TYPE_MAPPING.keys())}"
        }
    
    source_types = get_source_types_filter(request.source)
    result = assistant_answer(request.query, source_types=source_types)
    result["search_source"] = request.source
    result["filtered_by"] = source_types
    return result

@app.post("/reset-chat")
async def reset_chat():
    """Reset assistant conversation thread."""
    reset_thread()
    return {"status": "success", "message": "Assistant conversation thread reset."}

@app.get("/search/sources")
async def get_search_sources():
    """Get available source types for search filtering."""
    return {
        "available_sources": list(SOURCE_TYPE_MAPPING.keys()),
        "source_descriptions": {
            "all": "Search across all content types",
            "engineering_docs": "Search only uploaded documents (PDFs, TXT, MD, DOCX, etc.)",
            "confluence_docs": "Search only Confluence pages", 
            "jira_tickets": "Search only JIRA tickets (future feature)"
        },
        "source_mapping": {
            source: types for source, types in SOURCE_TYPE_MAPPING.items() if types is not None
        }
    }

@app.get("/confluence/status")
async def get_confluence_status():
    """Get status of Confluence pages in the knowledge base with version information."""
    try:
        # Query vector store for all Confluence entries
        # This would need to be implemented in VectorStore class
        # For now, return structure example
        return {
            "status": "available",
            "message": "Confluence integration active with version tracking",
            "features": [
                "Version-based staleness detection",
                "Per-page metadata tracking",
                "Incremental update capability",
                "Access control ready"
            ],
            "metadata_fields": [
                "version", "version_when", "last_modified", "created",
                "page_id", "space_key", "author", "author_id",
                "ingested_at", "embedding_model", "visibility"
            ],
            "note": "Use version field to detect stale embeddings - re-ingest pages with higher version numbers"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api-status")
async def get_api_status():
    """Get current API configuration and status."""
    return {
        "version": "3.0",
        "method": "openai_assistant_api",
        "search_endpoint": "/search",
        "reset_endpoint": "/reset-chat",
        "description": "Simplified API using only OpenAI Assistant with source filtering",
        "features": [
            "OpenAI Assistant API integration",
            "Source-based content filtering", 
            "Thread-based conversation management",
            "Extensible source adapter architecture",
            "Conditional document chunking",
            "Confluence version tracking",
            "Document migration support"
        ],
        "available_sources": list(SOURCE_TYPE_MAPPING.keys())
    }

@app.post("/migrate/documents")
async def migrate_documents():
    """Migrate existing documents to have proper source_type for backward compatibility."""
    try:
        # Get all points with null source_type
        null_points = vector_store.get_all_points_with_null_source_type()
        
        if not null_points:
            return {
                "status": "success",
                "message": "No documents found with null source_type",
                "migrated_count": 0
            }
        
        migrated_count = 0
        failed_count = 0
        
        for point in null_points:
            try:
                # Extract file info from the document title/source
                title = point.payload.get("source", "")
                
                # Determine if this looks like a document upload
                if any(title.lower().endswith(ext) for ext in ['.pdf', '.docx', '.txt', '.md', '.doc']):
                    # Extract file extension
                    file_extension = None
                    for ext in ['.pdf', '.docx', '.txt', '.md', '.doc']:
                        if title.lower().endswith(ext):
                            file_extension = ext.lstrip('.')
                            break
                    
                    # Create enhanced metadata
                    new_metadata = {
                        **point.payload,  # Keep existing metadata
                        "source_type": "document_upload",
                        "file_type": file_extension,
                        "file_extension": file_extension,
                        "filename": title,
                        "title": title,
                        "tags": [file_extension, "document", "migrated"],
                        "migrated_at": datetime.utcnow().isoformat(),
                        "embedding_model": EMBEDDING_MODEL_NAME,
                        "visibility": "internal",
                        "allowed_user_ids": []
                    }
                    
                    # Update the point
                    if vector_store.update_point_metadata(point.id, new_metadata):
                        migrated_count += 1
                    else:
                        failed_count += 1
                        
            except Exception as e:
                print(f"Error migrating point {point.id}: {e}")
                failed_count += 1
        
        return {
            "status": "success",
            "message": f"Migration completed",
            "total_null_documents": len(null_points),
            "migrated_count": migrated_count,
            "failed_count": failed_count,
            "note": "Documents with null source_type have been updated to 'document_upload' with enhanced metadata"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
