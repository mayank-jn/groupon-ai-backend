import os
import time
import openai
from dotenv import load_dotenv
from embeddings.vector_store import VectorStore
from config import EMBEDDING_MODEL_NAME

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Global assistant and thread identifiers
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
_thread_id = None
vector_store = VectorStore()


def _build_context(hits):
    """Return a context string from Qdrant search hits."""
    return "\n\n".join([
        hit.payload.get("text", "")
        for hit in hits
    ])


def _ensure_assistant():
    """Create an assistant if none exists."""
    global assistant_id
    if assistant_id:
        return assistant_id

    assistant = openai.beta.assistants.create(
        name="Groupon Assistant",
        instructions=(
            "You are a helpful assistant for Groupon engineers. Use your"
            " knowledge and built-in retrieval capabilities to answer questions."
        ),
        model="gpt-4o",
    )
    assistant_id = assistant.id
    return assistant_id


def _ensure_thread():
    """Create a thread if none exists."""
    global _thread_id
    if _thread_id is None:
        thread = openai.beta.threads.create()
        _thread_id = thread.id
    return _thread_id


def answer(query: str, source_types=None) -> dict:
    """Submit a query to the assistant and return its answer."""
    aid = _ensure_assistant()
    tid = _ensure_thread()

    # Fetch context from Qdrant with optional source filtering
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=[query],
    )
    query_embedding = response.data[0].embedding
    hits = vector_store.search(query_embedding, top_k=5, source_types=source_types)
    context = _build_context(hits)

    message_content = f"Context:\n{context}\n\nQuestion: {query}"

    openai.beta.threads.messages.create(
        thread_id=tid,
        role="user",
        content=message_content,
    )

    run = openai.beta.threads.runs.create(
        thread_id=tid,
        assistant_id=aid,
    )

    # Poll until run is complete
    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=tid, run_id=run.id
        )
        if run_status.status == "completed":
            break
        if run_status.status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(f"Run {run_status.status}")
        time.sleep(0.5)

    messages = openai.beta.threads.messages.list(thread_id=tid)
    for msg in messages.data:
        if msg.role == "assistant":
            answer_text = msg.content[0].text.value
            break
    else:
        answer_text = ""

    return {"answer": answer_text, "assistant_id": aid, "thread_id": tid}


def reset_thread() -> None:
    """Start a new thread for a fresh conversation."""
    global _thread_id
    _thread_id = None
