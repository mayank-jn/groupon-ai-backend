# embeddings/embed.py

from ingest.pdf_ingest import load_pdf, chunk_text
from embeddings.vector_store import VectorStore
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL_NAME
import os

def main():
    pdf_path = "sample_docs/sample.pdf"
    text = load_pdf(pdf_path)
    chunks = chunk_text(text)

    print(f"Loaded {len(chunks)} chunks from PDF.")

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = model.encode(chunks)

    vector_store = VectorStore()
    vector_store.create_collection(vector_size=embeddings.shape[1])

    metadatas = [{"text": chunk, "source": os.path.basename(pdf_path)} for chunk in chunks]
    vector_store.upsert_embeddings(embeddings, metadatas)

    print("Embeddings pushed to Qdrant.")

if __name__ == "__main__":
    main()
