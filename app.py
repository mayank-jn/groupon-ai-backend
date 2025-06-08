# app.py

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ingest.pdf_ingest import load_pdf, chunk_text
from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME
from retrieval.qa_chain import answer as rag_answer, reset_chat_history
import os
import openai

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Groupon RAG Backend", description="Conversational RAG with Qdrant & GPT", version="1.0")

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

@app.post("/upload")
async def upload_doc(file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_path = f"sample_docs/{file.filename}"
    os.makedirs("sample_docs", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    text = load_pdf(file_path)
    chunks = chunk_text(text)
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=chunks
    )
    embeddings = [d.embedding for d in response.data]

    # Cloud safe collection create
    vector_store.create_collection_if_not_exists(vector_size=len(embeddings[0]))
    metadatas = [{"text": chunk, "source": file.filename} for chunk in chunks]
    vector_store.upsert_embeddings(embeddings, metadatas)

    return {"status": "success", "chunks_uploaded": len(chunks), "doc_title": file.filename}

@app.post("/search")
async def search_query(query: str):
    result = rag_answer(query)
    return result

@app.post("/reset-chat")
async def reset_chat():
    reset_chat_history()
    return {"status": "success", "message": "Chat history cleared."}
