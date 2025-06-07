# Groupon AI Knowledge Assistant - Backend

A FastAPI-based backend implementing RAG (Retrieval-Augmented Generation) for intelligent document search and Q&A using Qdrant vector database, OpenAI GPT-4, and SentenceTransformers.

## 🚀 Features

- **FastAPI Framework**: High-performance async Python web framework
- **RAG Implementation**: Retrieval-Augmented Generation for context-aware AI responses
- **Vector Search**: Qdrant integration for semantic document retrieval
- **OpenAI Integration**: GPT-4 for generating comprehensive answers
- **Document Processing**: Support for PDF, DOC, DOCX, TXT, and MD files
- **CORS Support**: Configured for frontend integration
- **Interactive API Docs**: Swagger UI at `/docs`
- **Chat Memory**: Conversation context management

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.104+
- **AI/ML**: 
  - OpenAI GPT-4 for text generation
  - SentenceTransformers for embeddings
  - LangChain for document processing and RAG pipeline
- **Vector Database**: Qdrant (Cloud or local Docker)
- **Document Processing**: PyPDF2 for PDF parsing
- **Server**: Uvicorn ASGI server
- **Environment**: python-dotenv for configuration

## 📋 API Endpoints

### Core Endpoints

#### `POST /search`
Search the knowledge base and get AI-generated responses.

**Request Body:**
```json
{
  "query": "string"
}
```

**Response:**
```json
{
  "answer": "AI-generated response with context",
  "sources": [
    {
      "title": "Document title",
      "snippet": "Relevant text snippet"
    }
  ]
}
```

#### `POST /reset-chat`
Reset the conversation history.

**Response:**
```json
{
  "message": "Chat history reset successfully"
}
```

#### `GET /docs`
Interactive API documentation (Swagger UI)

#### `GET /redoc`
Alternative API documentation (ReDoc)

## 🚦 Setup & Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Qdrant Cloud instance or Docker for local setup

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd groupon-ai-backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the backend directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Qdrant Configuration (Cloud)
QDRANT_URL=https://your-cluster-url.qdrant.tech
QDRANT_API_KEY=your_qdrant_api_key

# Or for local Qdrant
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=  # Leave empty for local
```

### 3. Qdrant Setup

#### Option A: Qdrant Cloud (Recommended)
1. Create an account at [Qdrant Cloud](https://cloud.qdrant.io/)
2. Create a new cluster
3. Get your cluster URL and API key
4. Update the `.env` file with your credentials

#### Option B: Local Docker
```bash
# Start Qdrant locally
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

### 4. Start the Server

```bash
# Development mode with auto-reload
python3 -m uvicorn app:app --reload --port 8000

# Production mode
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## 📁 Project Structure

```
groupon-ai-backend/
├── app.py                 # Main FastAPI application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── embeddings/          # Embedding utilities
│   └── __init__.py
├── ingest/              # Document processing
│   └── __init__.py
├── retrieval/           # Search and retrieval logic
│   └── __init__.py
└── sample_docs/         # Sample documents
    └── *.pdf            # Example documents
```

## 🔧 Dependencies

### Core Dependencies
```
fastapi                  # Web framework
uvicorn                 # ASGI server
langchain               # LLM framework
langchain_community     # Community integrations
sentence-transformers   # Embedding models
qdrant-client          # Vector database client
openai                 # OpenAI API client
python-dotenv          # Environment variables
PyPDF2                 # PDF processing
tqdm                   # Progress bars
python-multipart       # File upload support
```

## 🧠 How It Works

### RAG Pipeline

1. **Document Ingestion**:
   - Documents are processed and split into chunks
   - Text embeddings are generated using SentenceTransformers
   - Chunks are stored in Qdrant vector database

2. **Query Processing**:
   - User query is converted to embeddings
   - Semantic search finds relevant document chunks
   - Retrieved context is used to generate AI response

3. **Response Generation**:
   - OpenAI GPT-4 generates contextual answers
   - Sources are returned with the response
   - Conversation history is maintained

### Key Components

- **FastAPI App**: Main application with CORS middleware
- **Qdrant Client**: Vector database operations
- **OpenAI Client**: GPT-4 text generation
- **LangChain**: Document processing and RAG pipeline
- **SentenceTransformers**: Text embedding generation

## 🔍 Usage Examples

### Search Query
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the deal categorization work?"}'
```

### Reset Chat
```bash
curl -X POST "http://localhost:8000/reset-chat"
```

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Errors**:
   - Verify your API key in `.env`
   - Check your OpenAI account has sufficient credits

2. **Qdrant Connection Issues**:
   - Verify Qdrant URL and API key
   - For local setup, ensure Docker container is running

3. **Import Errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version compatibility (3.8+)

4. **CORS Issues**:
   - Frontend should run on allowed origins (localhost:5173, localhost:3000)
   - CORS middleware is configured in `app.py`

### Logs and Debugging

```bash
# Run with verbose logging
python3 -m uvicorn app:app --reload --port 8000 --log-level debug
```

## 🧪 Testing

Access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Test endpoints directly from the Swagger interface.

## 🚀 Deployment

### Production Configuration

1. **Environment Variables**: Set production values in `.env`
2. **HTTPS**: Configure SSL/TLS certificates
3. **Process Management**: Use process managers like supervisord or systemd
4. **Reverse Proxy**: Use nginx or similar for production deployment

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📄 License

This project is licensed under the MIT License.

## 🔗 Related Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [LangChain Documentation](https://python.langchain.com/)
