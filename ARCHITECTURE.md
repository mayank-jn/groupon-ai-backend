# Groupon AI Knowledge Assistant - Architecture Overview

## 🏗️ Clean & Focused Architecture

This project follows a clean, production-ready architecture with no unnecessary placeholder code.

## 📁 Directory Structure

```
groupon-ai-backend/
├── app.py                          # 🚀 Main FastAPI application
├── config.py                       # ⚙️ Configuration management
├── requirements.txt                 # 📦 Python dependencies
├── ARCHITECTURE.md                  # 📋 This file
├── LOCAL_SETUP.md                   # 🛠️ Development guide
├── test_*.py                        # 🧪 Test scripts
├── sources/                         # 🔌 Extensible source adapters
│   ├── base/                        # 📐 Abstract interfaces & factory
│   ├── document_upload/             # 📄 Document processing (✅ Complete)
│   └── confluence/                  # 🚧 Future implementation
├── retrieval/                       # 🔍 RAG & Assistant API integration
├── embeddings/                      # 🎯 Vector operations
├── ingest/                          # 📥 Legacy document processing
└── sample_docs/                     # 📚 Test documents
```

## 🔧 Technology Stack

### Core Components
- **FastAPI**: High-performance async web framework
- **OpenAI Assistant API**: Primary conversational AI (with traditional RAG fallback)
- **Qdrant Cloud**: Vector database for semantic search
- **Factory Pattern**: Extensible source adapter architecture

### AI Pipeline
```
Document Upload → Source Adapter → Conditional Chunking → Embeddings → Qdrant
Query → Assistant API (primary) → Traditional RAG (fallback) → Response
```

## 🔌 Source Adapter Architecture

### Current Implementation ✅
**Document Upload Adapter**: 
- PDF, DOCX, TXT, MD support
- Conditional chunking based on token limits
- Metadata extraction
- Format-specific processors

### Future Extension 🚧
**Confluence Adapter**: 
- Planned for confluence integration
- Clean placeholder without unused code

### Design Principles
- **Single Responsibility**: Each adapter handles one source type
- **Open/Closed**: Easy to extend, no modification of existing code
- **Interface Compliance**: All adapters implement same contract
- **No Dead Code**: Only implemented features, no unused placeholders

## 🎯 API Design

### Primary Endpoints (Assistant API + Fallback)
- `POST /search` - Intelligent search with automatic fallback
- `POST /reset-chat` - Thread reset with fallback
- `POST /upload` - Document processing via source adapters

### Explicit Control Endpoints
- `POST /search/traditional` - Direct traditional RAG
- `POST /search/assistant` - Direct Assistant API
- Various reset endpoints for specific methods

### Information Endpoints
- `GET /api-status` - Current configuration
- `GET /sources` - Available source adapters
- `GET /document-info` - Processing capabilities

## 💡 Key Benefits

### 🧹 Clean Codebase
- No unused placeholder code
- Only production-ready features
- Clear separation of concerns

### 🔧 Extensible Design
- Easy to add new source types
- Factory pattern for adapter management
- Standardized interfaces

### 🛡️ Robust Operation
- Automatic fallback mechanisms
- Graceful error handling
- Comprehensive testing

### 🚀 Performance Optimized
- Conditional chunking saves resources
- Assistant API for better context management
- Efficient vector operations

## 🧪 Testing Strategy

### Test Scripts Available
- `test_assistant_integration.py` - API integration testing
- `test_source_factory.py` - Adapter pattern verification
- `test_conditional_chunking.py` - Chunking logic validation

### Coverage Areas
- Source adapter functionality
- API endpoint behavior
- Fallback mechanisms
- Error handling

## 🚀 Deployment Ready

### Local Development
- Simple setup with clear documentation
- Visual indicators for development mode
- Hot reloading and proxy configuration

### Production Deployment
- Environment-aware configuration
- Scalable architecture
- Monitor-friendly error handling

This architecture balances simplicity with extensibility, providing a solid foundation for the Groupon AI Knowledge Assistant while maintaining clean, maintainable code. 