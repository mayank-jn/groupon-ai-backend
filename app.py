# app.py

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sources import SourceFactory
from sources.document_upload import DocumentUploadAdapter
from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME
from retrieval.qa_chain import answer as rag_answer, reset_chat_history
from retrieval.openai_assistant import answer as assistant_answer, reset_thread
import os
import openai

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="Groupon AI Knowledge Assistant Backend", 
    description="AI-powered knowledge assistant using OpenAI Assistant APIs with Qdrant vector search and extensible source adapters", 
    version="2.0"
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
            metadata = {
                "text": result.content,
                "source": result.title or file.filename,
                "source_type": result.source_type,
                "source_id": result.source_id,
                "chunk_index": result.metadata.get('chunk_index', 0),
                "total_chunks": result.metadata.get('total_chunks', 1),
                "was_chunked": result.metadata.get('was_chunked', False)
            }
            if result.author:
                metadata["author"] = result.author
            if result.tags:
                metadata["tags"] = result.tags
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

@app.post("/search")
async def search_query(query: str):
    """Primary search endpoint using OpenAI's Assistants API."""
    try:
        result = assistant_answer(query)
        return result
    except Exception as e:
        # Fallback to traditional RAG if assistant fails
        print(f"Assistant API failed, falling back to RAG: {e}")
        try:
            result = rag_answer(query)
            result["fallback_used"] = "traditional_rag"
            result["fallback_reason"] = str(e)
            return result
        except Exception as fallback_error:
            return {
                "answer": "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                "error": "Both assistant and RAG methods failed",
                "assistant_error": str(e),
                "rag_error": str(fallback_error)
            }

@app.post("/reset-chat")
async def reset_chat():
    """Primary reset endpoint using Assistant API thread reset."""
    try:
        reset_thread()
        return {"status": "success", "message": "Assistant conversation thread reset."}
    except Exception as e:
        # Fallback to traditional chat history reset
        print(f"Assistant reset failed, falling back to traditional reset: {e}")
        try:
            reset_chat_history()
            return {
                "status": "success", 
                "message": "Traditional chat history cleared (assistant reset failed).",
                "fallback_used": True,
                "fallback_reason": str(e)
            }
        except Exception as fallback_error:
            return {
                "status": "error",
                "message": "Both assistant and traditional reset methods failed",
                "assistant_error": str(e),
                "traditional_error": str(fallback_error)
            }

# Legacy endpoints for backward compatibility and explicit choice
@app.post("/search/traditional")
async def search_traditional(query: str):
    """Traditional RAG search endpoint (legacy/explicit use)."""
    result = rag_answer(query)
    result["method"] = "traditional_rag"
    return result

@app.post("/search/assistant")
async def search_assistant(query: str):
    """Assistant API search endpoint (explicit use)."""
    result = assistant_answer(query)
    result["method"] = "assistant_api"
    return result

@app.post("/reset-chat/traditional")
async def reset_traditional():
    """Traditional chat history reset (legacy/explicit use)."""
    reset_chat_history()
    return {"status": "success", "message": "Traditional chat history cleared.", "method": "traditional"}

@app.post("/reset-chat/assistant")
async def reset_assistant():
    """Assistant thread reset (explicit use)."""
    reset_thread()
    return {"status": "success", "message": "Assistant thread reset.", "method": "assistant"}

@app.get("/document-info")
async def get_document_info():
    """Get information about document processing capabilities and limits."""
    return {
        "available_adapters": SourceFactory.list_available_adapters(),
        "adapter_capabilities": SourceFactory.get_all_capabilities(),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "token_limit": 8000,
        "chunking_strategy": {
            "method": "conditional",
            "description": "Documents are only chunked if they exceed the token limit",
            "chunk_size": 1000,
            "overlap": 200
        },
        "architecture": "Factory pattern with extensible source adapters"
    }

@app.get("/sources")
async def get_source_adapters():
    """Get detailed information about all available source adapters."""
    return {
        "available_adapters": SourceFactory.list_available_adapters(),
        "capabilities": SourceFactory.get_all_capabilities()
    }

@app.get("/api-status")
async def get_api_status():
    """Get current API configuration and status."""
    return {
        "version": "2.0",
        "primary_method": "openai_assistant_api",
        "fallback_method": "traditional_rag",
        "search_endpoint": "/search (Assistant API with RAG fallback)",
        "reset_endpoint": "/reset-chat (Assistant thread reset with traditional fallback)",
        "legacy_endpoints": {
            "traditional_search": "/search/traditional",
            "assistant_search": "/search/assistant", 
            "traditional_reset": "/reset-chat/traditional",
            "assistant_reset": "/reset-chat/assistant"
        },
        "features": [
            "OpenAI Assistant API integration",
            "Automatic fallback to traditional RAG", 
            "Thread-based conversation management",
            "Extensible source adapter architecture",
            "Conditional document chunking"
        ]
    }
