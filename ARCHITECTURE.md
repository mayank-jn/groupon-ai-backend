# Groupon AI Knowledge Assistant - Architecture Overview

## 🏗️ World-Class Multi-Source Architecture

This project implements a production-ready, extensible architecture with comprehensive multi-source search capabilities across documents, GitHub repositories, and Confluence spaces.

## 📁 Directory Structure

```
groupon-ai-backend/
├── app.py                          # 🚀 Main FastAPI application with unified search
├── config.py                       # ⚙️ Configuration management
├── requirements.txt                 # 📦 Python dependencies
├── ARCHITECTURE.md                  # 📋 This file
├── CONFLUENCE_SETUP.md              # 🏢 Confluence integration guide
├── README.md                        # 📖 Comprehensive documentation
├── test_*.py                        # 🧪 Test scripts for all components
├── sources/                         # 🔌 Extensible source adapters (✅ Complete)
│   ├── base/                        # 📐 Abstract interfaces & factory
│   │   ├── factory.py               # Factory pattern implementation
│   │   └── interfaces.py            # Source adapter contracts
│   ├── document_upload/             # 📄 Document processing (✅ Complete)
│   │   └── adapter.py               # PDF, DOCX, TXT, MD processing
│   ├── github/                      # 🐙 GitHub Live search (✅ Complete)
│   │   └── adapter.py               # Function-level code extraction
│   └── confluence/                  # 🏢 Confluence integration (✅ Complete)
│       └── adapter.py               # Space and page ingestion
├── embeddings/                      # 🎯 Vector operations
│   └── vector_store.py              # Qdrant client wrapper
├── retrieval/                       # 🔍 RAG & search integration
├── ingest/                          # 📥 Document processing utilities
│   └── pdf_ingest.py                # Conditional chunking logic
└── sample_docs/                     # 📚 Test documents
```

## 🔧 Technology Stack

### Core Components
- **FastAPI**: High-performance async web framework with unified search API
- **OpenAI GPT-4**: Advanced language model for contextual responses
- **OpenAI Embeddings**: text-embedding-3-small for semantic search
- **Qdrant Cloud**: Managed vector database for multi-source search
- **Source Adapter Pattern**: Extensible architecture for multiple data sources

### Multi-Source Integration
- **GitHub API**: Repository indexing with function-level extraction
- **Confluence API**: Space and page ingestion with metadata preservation
- **Document Processing**: PDF, DOCX, TXT, MD with intelligent chunking
- **Factory Pattern**: Clean adapter registration and management

### AI Pipeline
```
Multi-Source Ingestion → Enhanced Metadata → Embeddings → Unified Vector Store
Unified Query → Intent Detection → Multi-Source Search → Context Assembly → GPT-4 Response
```

## 🔌 Source Adapter Architecture

### ✅ Document Upload Adapter (Complete)
**Features**: 
- PDF, DOCX, TXT, MD support with format-specific processing
- Conditional chunking based on token limits for optimal embedding
- Metadata extraction: title, author, creation date
- Enhanced validation for multiple file types

### ✅ GitHub Live Search Adapter (Complete)
**Features**:
- Function-level extraction for Python, JavaScript, TypeScript, Java, Go
- Semantic tagging: api, authentication, database, testing, configuration
- Technology detection: React, FastAPI, Docker, Kubernetes, PostgreSQL
- Intelligent chunking by logical code blocks
- Repository-level metadata with branch and commit tracking

### ✅ Confluence Integration Adapter (Complete)
**Features**:
- Complete space crawling with pagination support
- HTML to clean text conversion with BeautifulSoup
- Metadata preservation: authors, tags, spaces, URLs, version history
- Label support for enhanced categorization
- Multiple authentication methods (API token, bearer token)

### Design Principles
- **Single Responsibility**: Each adapter handles one source type with full feature completeness
- **Open/Closed**: Easy to extend with new sources without modifying existing code
- **Interface Compliance**: All adapters implement standardized SourceAdapter contract
- **Production Ready**: Comprehensive error handling, logging, and validation

## 🎯 Unified API Design

### Primary Search Endpoint
- `POST /search` - Intelligent search across all sources with automatic routing
  - Optional source filtering (github_live, confluence, document)
  - Enhanced metadata in responses (function names, semantic tags, tech stack)
  - Relevance scoring and source attribution
  - Conversation context management

### Multi-Source Ingestion Endpoints
- `POST /upload` - Document processing with enhanced validation
- `POST /github/ingest` - Repository ingestion with function-level extraction
- `POST /confluence/ingest` - Space and page ingestion with metadata

### System Information Endpoints
- `GET /sources` - Available source adapters with capabilities
- `GET /document-info` - Processing capabilities and statistics
- `GET /docs` - Interactive API documentation

## 💡 Key Architectural Benefits

### 🧹 Production-Ready Codebase
- Complete implementation of all major source adapters
- Comprehensive error handling and validation
- No placeholder or dead code - only production features
- Clear separation of concerns with clean interfaces

### 🔧 Multi-Source Intelligence
- Unified search across documents, code repositories, and knowledge bases
- Function-level granularity for code search
- Semantic tagging and technology detection
- Enhanced metadata integration in responses

### 🛡️ Robust Operation
- Automatic fallback mechanisms for service outages
- Graceful error handling with detailed logging
- Input validation and sanitization
- Rate limiting and cost optimization

### 🚀 Performance Optimized
- Conditional chunking saves embedding costs
- Intelligent caching and vector storage
- Async FastAPI for concurrent request handling
- Optimized vector search with relevance scoring

## 🧪 Comprehensive Testing Strategy

### Available Test Scripts
- `test_source_factory.py` - Source adapter factory and registration
- `test_conditional_chunking.py` - Chunking logic validation
- `test_assistant_integration.py` - End-to-end API testing
- `test_confluence_adapter.py` - Confluence integration testing

### Coverage Areas
- Multi-source adapter functionality and error handling
- Unified search API behavior across all sources
- Metadata extraction and semantic tagging
- Vector storage and retrieval operations
- Authentication and permission validation

## 🌐 Enhanced Search Capabilities

### Function-Level Code Search
- Precise function and method extraction from repositories
- Semantic understanding of code relationships and dependencies
- Technology stack detection and categorization
- Cross-repository pattern recognition

### Intelligent Content Processing
- Conditional chunking based on content type and size
- Format-specific processing for optimal text extraction
- Metadata preservation across all source types
- Version tracking and freshness indicators

### Advanced Query Processing
- Intent detection for automatic source routing
- Multi-source result aggregation and ranking
- Relevance scoring with confidence indicators
- Context-aware response generation

## 🚀 Production Deployment Architecture

### Scalable Infrastructure
- **Frontend**: Vercel CDN with global edge distribution
- **Backend**: Railway/Heroku with auto-scaling FastAPI
- **Vector Database**: Qdrant Cloud with managed scaling
- **External APIs**: GitHub, Confluence, OpenAI with rate limiting

### Environment Configuration
```bash
# Multi-Source Integration
OPENAI_API_KEY=sk-...
QDRANT_URL=https://xxx.qdrant.tech
QDRANT_API_KEY=xxx
GITHUB_TOKEN=ghp_...
CONFLUENCE_URL=https://company.atlassian.net/wiki
CONFLUENCE_USERNAME=service@company.com
CONFLUENCE_API_TOKEN=xxx
```

### Performance Metrics
- **Query Response Time**: < 2 seconds for 95th percentile
- **Function-Level Search**: < 1 second for code repository searches
- **Multi-Source Search**: Parallel processing across all sources
- **Concurrent Users**: Support for 100+ simultaneous users

## 🔮 Future Architecture Enhancements

### Phase 2: Advanced Intelligence
- **Multi-Modal Processing**: Diagram and image understanding
- **Code Visualization**: Automatic architecture diagram generation
- **Cross-Source Analytics**: Pattern recognition across all data sources

### Phase 3: Enterprise Integration
- **SSO Integration**: Enterprise authentication and authorization
- **API Ecosystem**: Integration with development tools and workflows
- **Advanced Analytics**: Usage patterns and knowledge gap analysis

## 📊 Architecture Success Metrics

### Technical Excellence
- **Zero Downtime**: Robust error handling and fallback mechanisms
- **Sub-Second Search**: Optimized vector operations and caching
- **Multi-Source Coverage**: 100% of engineering knowledge sources integrated
- **Function-Level Precision**: Exact code location and context

### Developer Experience
- **Unified Interface**: Single search for all engineering knowledge
- **Rich Metadata**: Complete context with source attribution
- **Conversation Continuity**: Multi-turn technical discussions
- **Real-Time Results**: Instant feedback and progressive enhancement

This architecture represents a world-class implementation of multi-source intelligent search, combining the best practices of modern software architecture with advanced AI capabilities to create a comprehensive knowledge management system for engineering teams. 