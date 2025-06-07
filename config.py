import os
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

EMBEDDING_MODEL_NAME = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)
COLLECTION_NAME = "groupon_docs"
