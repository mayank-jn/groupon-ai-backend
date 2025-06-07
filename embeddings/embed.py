# embeddings/embed.py

from ingest.pdf_ingest import load_pdf, chunk_text
from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME
import os
import openai
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def main():
    pdf_path = "sample_docs/sample.pdf"
    text = load_pdf(pdf_path)
    chunks = chunk_text(text)

    print(f"Loaded {len(chunks)} chunks from PDF.")

    response = openai.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=chunks
    )
    embeddings = [d.embedding for d in response.data]

    vector_store = VectorStore()
    vector_store.create_collection(vector_size=len(embeddings[0]))

    metadatas = [{"text": chunk, "source": os.path.basename(pdf_path)} for chunk in chunks]
    vector_store.upsert_embeddings(embeddings, metadatas)

    print("Embeddings pushed to Qdrant.")

if __name__ == "__main__":
    main()
