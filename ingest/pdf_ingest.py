
# ingest/pdf_ingest.py

import PyPDF2

def load_pdf(file_path):
    pdf_reader = PyPDF2.PdfReader(open(file_path, "rb"))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
