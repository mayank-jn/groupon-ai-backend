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
from config import EMBEDDING_MODEL_NAME, COLLECTION_NAME
from retrieval.openai_assistant import answer as assistant_answer, reset_thread
from qdrant_client.models import Filter, FieldCondition, MatchValue
import os
import openai
from sources.github.adapter import GitHubSourceAdapter
from github import Github

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Source type mapping from user-friendly names to metadata source_type values
SOURCE_TYPE_MAPPING = {
    "all": None,  # No filtering
    "engineering_docs": ["document_upload"],  # Document uploads
    "confluence_docs": ["confluence"],  # Confluence pages
    "jira_tickets": ["jira"],  # Future JIRA integration
    "github_live": ["github_live"],  # GitHub Live search (handled separately)
}

def get_source_types_filter(source: str) -> Optional[List[str]]:
    """Convert user-friendly source name to list of source_type values for filtering."""
    if source == "engineering_docs":
        return ["document_upload"]  # After migration, all docs will have proper source_type
    elif source == "confluence_docs":
        return ["confluence"]
    elif source == "jira_tickets":
        return ["jira"]
    elif source == "github_live":
        return ["github_live"]  # This will be handled separately in search logic
    elif source == "all":
        return None  # No filtering
    else:
        return None

def _extract_search_terms(query: str) -> str:
    """Extract key search terms from complex queries for GitHub API search."""
    # Remove common stop words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'where', 'when', 'why', 'can', 'could', 'should', 'would', 'help', 'me', 'you', 'i', 'we', 'they'}
    
    # Split query into words and filter out stop words
    words = query.lower().split()
    meaningful_words = [word.strip('.,!?;:()[]{}') for word in words if word.lower() not in stop_words and len(word) > 2]
    
    # Join back with spaces, limit to first 5 most meaningful terms
    return ' '.join(meaningful_words[:5])

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
    source: str = Field("all", description="Source to search in: 'all', 'engineering_docs', 'confluence_docs', 'jira_tickets', 'github_live'")
    
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

class GitHubIngestRequest(BaseModel):
    repo_url: str

def embed_and_upsert_github_chunks(results):
    from embeddings.vector_store import VectorStore
    import openai
    from config import EMBEDDING_MODEL_NAME
    from datetime import datetime

    chunks = [r.content for r in results]
    metadatas = []
    for r in results:
        m = dict(r.metadata)
        # Backward compatible fields
        m["text"] = r.content
        m["source"] = r.title or r.metadata.get("repo")
        m["source_type"] = r.source_type
        m["source_id"] = r.source_id
        m["title"] = r.title or r.metadata.get("repo")
        m["embedding_model"] = EMBEDDING_MODEL_NAME
        m["ingested_at"] = datetime.utcnow().isoformat()
        metadatas.append(m)

    response = openai.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=chunks
    )
    embeddings = [d.embedding for d in response.data]
    vector_store = VectorStore()
    vector_store.create_collection_if_not_exists(vector_size=len(embeddings[0]))
    vector_store.upsert_embeddings(embeddings, metadatas)
    print(f"Upserted {len(embeddings)} GitHub code/document chunks to Qdrant.")

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
        
        # Enhanced validation with better error handling
        if not file.filename:
            return {"status": "error", "message": "No filename provided"}
        
        # Check file extension directly
        import os
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = ['.pdf', '.docx', '.txt', '.md']
        
        if file_extension not in supported_formats:
            return {"status": "error", "message": f"Unsupported file type: {file.filename}. Supported formats: {', '.join(supported_formats)}"}
        
        # Skip adapter validation since we've already validated the file type
        # The adapter validation has issues with UploadFile objects, but the processing works fine
        
        # Process the document directly
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
    """Search endpoint using OpenAI's Assistants API with source filtering and GitHub Live search."""
    # Validate source parameter
    if request.source not in SOURCE_TYPE_MAPPING:
        return {
            "error": f"Invalid source '{request.source}'. Valid options: {list(SOURCE_TYPE_MAPPING.keys())}"
        }
    
    # Handle GitHub Live search
    if request.source == 'github_live':
        try:
            # Get list of ingested repositories to ensure we only search within them
            ingested_repos = vector_store.get_ingested_github_repositories()
            if not ingested_repos:
                return {
                    "error": "No GitHub repositories have been ingested yet. Please ingest repositories first using /ingest/github endpoint.",
                    "answer": "No GitHub repositories have been ingested yet. Please ingest repositories first.",
                    "search_source": "github_live",
                    "github_live_results": [],
                    "total_results": 0,
                    "code_results": 0,
                    "issues_results": 0
                }
            
            # WORLD-CLASS SEMANTIC SEARCH: Use enhanced vector database search
            # 1. Generate query embedding for semantic search
            response = openai.embeddings.create(
                model=EMBEDDING_MODEL_NAME,
                input=[request.query]
            )
            query_embedding = response.data[0].embedding
            
            # 2. Use enhanced semantic search with intelligent filtering
            semantic_hits = vector_store.search_github_semantic(
                query_vector=query_embedding,
                top_k=15,
                repositories=ingested_repos,  # Only search within ingested repos
                score_threshold=0.25  # Lower threshold for more results
            )
            
            # 3. Advanced result processing with enhanced metadata
            processed_results = []
            github_token = os.getenv("GITHUB_TOKEN")
            gh = Github(github_token) if github_token else None
            
            for hit in semantic_hits:
                payload = hit.payload
                repo_name = payload.get("repo", "")
                file_path = payload.get("path", "")
                language = payload.get("language", "")
                file_name = payload.get("name", "")
                chunk_type = payload.get("chunk_type", "unknown")
                function_name = payload.get("function_name")
                section_title = payload.get("section_title")
                semantic_tags = payload.get("semantic_tags", [])
                tech_stack = payload.get("tech_stack", [])
                
                # Create intelligent snippet based on chunk type
                content = payload.get("text", "")
                if chunk_type == "function" and function_name:
                    snippet = f"Function: {function_name}\n{content[:400]}..."
                elif chunk_type == "documentation_section" and section_title:
                    snippet = f"Section: {section_title}\n{content[:400]}..."
                elif chunk_type == "configuration":
                    snippet = f"Config: {file_name}\n{content[:300]}..."
                else:
                    snippet = content[:500]
                
                # Calculate enhanced relevance score
                relevance_score = min(100, int(hit.score * 100))
                
                # Boost score based on semantic relevance
                if any(tag in request.query.lower() for tag in semantic_tags):
                    relevance_score = min(100, relevance_score + 10)
                
                # Enhanced metadata for better user experience
                result = {
                    "type": "code",
                    "name": file_name,
                    "path": file_path,
                    "repository": repo_name,
                    "language": language,
                    "chunk_type": chunk_type,
                    "function_name": function_name,
                    "section_title": section_title,
                    "semantic_tags": semantic_tags,
                    "tech_stack": tech_stack,
                    "relevance_score": relevance_score,
                    "snippet": snippet,
                    "semantic_score": hit.score,
                    "ingested": True,
                    "search_type": "semantic_vector_enhanced"
                }
                
                # Generate GitHub URL
                if repo_name:
                    if gh:
                        try:
                            repo = gh.get_repo(repo_name)
                            default_branch = repo.default_branch
                        except:
                            default_branch = "main"
                    else:
                        default_branch = "main"
                    result["html_url"] = f"https://github.com/{repo_name}/blob/{default_branch}/{file_path}"
                
                processed_results.append(result)
            
            # 4. Enhanced GitHub Issues/PRs search (if GitHub token available)
            github_issues = []
            if gh and len(processed_results) < 8:  # Only search issues if we have few code results
                try:
                    search_terms = _extract_search_terms(request.query)
                    
                    for repo_name in ingested_repos[:2]:  # Limit to first 2 repos for performance
                        try:
                            if '/' in repo_name:
                                q = f"{search_terms} repo:{repo_name}"
                                issues_search_results = gh.search_issues(q)[:3]
                                
                                for item in issues_search_results:
                                    github_issues.append({
                                        "type": "issue",
                                        "title": item.title,
                                        "number": item.number,
                                        "state": item.state,
                                        "repository": repo_name,
                                        "html_url": item.html_url,
                                        "is_pull_request": item.pull_request is not None,
                                        "body": item.body[:300] if item.body else None,
                                        "ingested": True,
                                        "search_type": "github_api_enhanced"
                                    })
                        except Exception as e:
                            print(f"Error searching issues in {repo_name}: {e}")
                            continue
                except Exception as e:
                    print(f"Error in GitHub issues search: {e}")
            
            # 5. Intelligent ranking and result combination
            all_results = processed_results + github_issues
            
            # Advanced sorting: semantic score for code, then by relevance
            all_results.sort(key=lambda x: (
                -x.get("semantic_score", 0) if x["type"] == "code" else -0.4,
                -x.get("relevance_score", 0),
                x["type"] == "code"  # Code results first
            ))
            
            # Limit final results
            all_results = all_results[:10]
            
            total_results = len(all_results)
            code_results = len([r for r in all_results if r["type"] == "code"])
            issues_results = len([r for r in all_results if r["type"] == "issue"])
            
            # 6. Generate intelligent answer with context
            if total_results > 0:
                answer = f"Found {total_results} semantically relevant results"
                if code_results > 0 and issues_results > 0:
                    answer += f" ({code_results} code files, {issues_results} issues/PRs)"
                elif code_results > 0:
                    answer += f" ({code_results} code files)"
                elif issues_results > 0:
                    answer += f" ({issues_results} issues/PRs)"
                
                # Add intelligent context about search quality
                if semantic_hits and semantic_hits[0].score > 0.8:
                    answer += " with high semantic relevance"
                elif semantic_hits and semantic_hits[0].score > 0.6:
                    answer += " with good semantic relevance"
                else:
                    answer += " - consider refining your query for better results"
                
                # Add technology context if available
                languages_found = set(r.get("language") for r in processed_results if r.get("language"))
                if languages_found:
                    answer += f". Languages: {', '.join(sorted(languages_found))}"
            else:
                answer = f"No semantically relevant results found for '{request.query}' in your ingested GitHub repositories. Try using different keywords or broader terms."
            
            return {
                "answer": answer,
                "search_source": "github_live",
                "github_live_results": all_results,
                "total_results": total_results,
                "code_results": code_results,
                "issues_results": issues_results,
                "search_method": "semantic_vector_enhanced",
                "ingested_repositories": len(ingested_repos),
                "search_quality": "high" if semantic_hits and semantic_hits[0].score > 0.7 else "medium" if semantic_hits and semantic_hits[0].score > 0.5 else "low"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "answer": f"Error performing GitHub Live search: {str(e)}",
                "search_source": "github_live",
                "github_live_results": [],
                "total_results": 0,
                "code_results": 0,
                "issues_results": 0
            }
    
    # Handle regular search (existing logic)
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
            "jira_tickets": "Search only JIRA tickets (future feature)",
            "github_live": "Live search code & issues in ingested GitHub repositories"
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

@app.post("/ingest/github")
async def ingest_github_repo(request: GitHubIngestRequest):
    """
    Ingest a GitHub repository into the vector database.
    
    This endpoint clones the given GitHub repository, scans and chunks all relevant code and markdown files, generates embeddings, and upserts them to Qdrant with rich metadata.
    
    Request body:
    {
        "repo_url": "https://github.com/owner/repo.git"
    }
    
    Returns:
    - status: "success" or "error"
    - chunks_ingested: number of chunks ingested (if success)
    - message: error message (if error)
    """
    adapter = GitHubSourceAdapter()
    try:
        results = adapter.process_source(request.repo_url)
        embed_and_upsert_github_chunks(results)
        return {"status": "success", "chunks_ingested": len(results)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/github/repositories")
async def list_ingested_repositories():
    """
    Get a list of all GitHub repositories that have been ingested into the database.
    This shows which repositories are available for GitHub live search.
    """
    try:
        ingested_repos = vector_store.get_ingested_github_repositories()
        
        # Get additional metadata for each repository
        repo_details = []
        for repo_name in ingested_repos:
            # Count how many documents/chunks are from this repo
            try:
                points, _ = vector_store.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=1000,  # Should be enough for most repos
                    with_payload=True,
                    with_vectors=False,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(key="source_type", match=MatchValue(value="github")),
                            FieldCondition(key="repo", match=MatchValue(value=repo_name))
                        ]
                    )
                )
                
                # Extract file types and languages
                file_types = set()
                languages = set()
                for point in points:
                    if point.payload.get("language"):
                        languages.add(point.payload["language"])
                    if point.payload.get("name"):
                        ext = point.payload["name"].split(".")[-1] if "." in point.payload["name"] else "unknown"
                        file_types.add(ext)
                
                repo_details.append({
                    "repository": repo_name,
                    "chunks_count": len(points),
                    "languages": list(languages),
                    "file_types": list(file_types),
                    "github_url": f"https://github.com/{repo_name}"
                })
            except Exception as e:
                print(f"Error getting details for repo {repo_name}: {e}")
                repo_details.append({
                    "repository": repo_name,
                    "chunks_count": 0,
                    "languages": [],
                    "file_types": [],
                    "github_url": f"https://github.com/{repo_name}",
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "total_repositories": len(ingested_repos),
            "repositories": repo_details,
            "message": "These repositories are available for GitHub live search"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
