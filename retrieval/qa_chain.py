# retrieval/qa_chain.py

from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME
import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

vector_store = VectorStore()

# Global chat history (per session, in-memory)
chat_history = []

def build_context_from_sources(sources):
    context = "\n\n".join([f"Source {i+1}: {s.payload['text']}" for i, s in enumerate(sources)])
    return context

def build_messages(chat_history, query, context):
    # Start with system prompt
    messages = [{"role": "system", "content": "You are a helpful assistant for Groupon Engineers. Use the provided document context when possible. If you don't know, say 'I don't know'."}]
    
    # Add chat history
    messages.extend(chat_history)

    # Add current user question with context
    user_prompt = f"""
Question: {query}

Context:
{context}

Answer:
"""
    messages.append({"role": "user", "content": user_prompt})

    return messages

def answer(query, top_k=5, source_types=None):
    # Embed query
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=[query]
    )
    query_embedding = response.data[0].embedding

    # Search in Qdrant with optional source filtering
    hits = vector_store.search(query_embedding, top_k=top_k, source_types=source_types)

    # Build context
    context = build_context_from_sources(hits)

    # Build full messages list with chat history
    messages = build_messages(chat_history, query, context)

    # Call GPT
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    answer_text = response.choices[0].message.content

    # Add current Q&A to chat history
    chat_history.append({"role": "user", "content": query})
    chat_history.append({"role": "assistant", "content": answer_text})

    # Prepare sources
    sources = [
        {
            "title": hit.payload.get("source", "unknown"),
            "snippet": hit.payload.get("text", "")
        }
        for hit in hits
    ]

    return {
        "answer": answer_text,
        "sources": sources
    }

def reset_chat_history():
    """Call this if user starts a new chat."""
    global chat_history
    chat_history = []
