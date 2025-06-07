# embeddings/vector_store.py

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
import uuid
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    def create_collection_if_not_exists(self, vector_size):
        try:
            self.client.get_collection(COLLECTION_NAME)
            print("Collection already exists — skipping create.")
        except Exception:
            print("Collection does not exist — creating...")
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            print("Collection created.")

    def upsert_embeddings(self, embeddings, metadatas):
        points = []
        for idx, embedding in enumerate(embeddings):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(id=point_id, vector=embedding, payload=metadatas[idx]))
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)

    def search(self, query_vector, top_k=5):
        hits = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )
        return hits
