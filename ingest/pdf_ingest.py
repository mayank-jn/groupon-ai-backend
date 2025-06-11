# ingest/pdf_ingest.py

import PyPDF2
import tiktoken
from docx import Document
import os

# OpenAI text-embedding-3-small has a limit of 8192 tokens
# We'll use a conservative limit to account for potential encoding variations
EMBEDDING_TOKEN_LIMIT = 8000

def load_document(file_path):
    """Load document content based on file extension."""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return load_pdf(file_path)
    elif file_extension == '.docx':
        return load_docx(file_path)
    elif file_extension in ['.txt', '.md']:
        return load_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def load_pdf(file_path):
    """Extract text from PDF files."""
    pdf_reader = PyPDF2.PdfReader(open(file_path, "rb"))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

def load_docx(file_path):
    """Extract text from DOCX files."""
    doc = Document(file_path)
    full_text = ""
    for paragraph in doc.paragraphs:
        full_text += paragraph.text + "\n"
    return full_text

def load_text(file_path):
    """Load plain text files."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def count_tokens(text, model="text-embedding-3-small"):
    """Count tokens in text using tiktoken for the specified model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))

def chunk_text_conditionally(text, model="text-embedding-3-small", chunk_size=1000, overlap=200):
    """
    Chunk text only if it exceeds the embedding model's token limit.
    Returns a list of chunks (even if just one chunk for the entire text).
    """
    token_count = count_tokens(text, model)
    
    if token_count <= EMBEDDING_TOKEN_LIMIT:
        # Document is small enough to embed as a single chunk
        return [text]
    else:
        # Document exceeds limit, need to chunk it
        return chunk_text(text, chunk_size, overlap)

def chunk_text(text, chunk_size=1000, overlap=200):
    """Traditional chunking function for larger documents."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
