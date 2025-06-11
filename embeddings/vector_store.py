# embeddings/vector_store.py

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition, MatchValue, PayloadSchemaType, IsNullCondition
import uuid
from typing import Optional, List
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    def create_collection_if_not_exists(self, vector_size):
        """Create the collection if missing and recreate if dimension differs."""
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            stored_size = info.config.params.vectors.size
            if stored_size != vector_size:
                print(
                    f"Collection dimension {stored_size} != {vector_size} -- recreating..."
                )
                self.client.recreate_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
                self._create_indexes()
                print("Collection recreated with indexes.")
            else:
                print("Collection already exists with correct dimension.")
                self._ensure_indexes()
        except Exception:
            print("Collection does not exist -- creating...")
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            self._create_indexes()
            print("Collection created with indexes.")
            
    def _create_indexes(self):
        """Create indexes for filtering fields."""
        try:
            # Create index for source_type field
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="source_type",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print("✅ Created index for source_type field")
        except Exception as e:
            print(f"⚠️  Could not create source_type index: {e}")
            
    def _ensure_indexes(self):
        """Ensure required indexes exist."""
        try:
            # Check if source_type index exists, create if not
            collection_info = self.client.get_collection(COLLECTION_NAME)
            # If we can get collection info, try to create index (it will be ignored if exists)
            self._create_indexes()
        except Exception as e:
            print(f"⚠️  Could not ensure indexes: {e}")

    def create_collection(self, vector_size):
        """Always recreate the collection."""
        self.client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_embeddings(self, embeddings, metadatas):
        points = []
        for idx, embedding in enumerate(embeddings):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(id=point_id, vector=embedding, payload=metadatas[idx]))
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)

    def search(self, query_vector, top_k=5, source_types: Optional[List[str]] = None):
        """Search vectors with optional source type filtering."""
        query_filter = None
        
        if source_types:
            # Filter out None values for now - we'll fix this with migration
            actual_source_types = [st for st in source_types if st is not None]
            
            if actual_source_types:
                # Create filter for source types
                source_conditions = [
                    FieldCondition(key="source_type", match=MatchValue(value=source_type))
                    for source_type in actual_source_types
                ]
                
                if len(source_conditions) == 1:
                    query_filter = Filter(must=[source_conditions[0]])
                else:
                    # Use should condition for OR logic between multiple source types
                    query_filter = Filter(should=source_conditions)
        
        hits = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter
        )
        return hits

    def get_all_points_with_null_source_type(self, limit=1000):
        """Get all points that have null source_type for migration purposes."""
        try:
            # Use scroll to get points without filtering - we'll check source_type in the results
            points, next_page_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Filter for points with null source_type
            null_source_points = []
            for point in points:
                if point.payload.get("source_type") is None:
                    null_source_points.append(point)
            
            return null_source_points
        except Exception as e:
            print(f"Error getting null source type points: {e}")
            return []
    
    def update_point_metadata(self, point_id, new_metadata):
        """Update metadata for a specific point."""
        try:
            self.client.set_payload(
                collection_name=COLLECTION_NAME,
                payload=new_metadata,
                points=[point_id]
            )
            return True
        except Exception as e:
            print(f"Error updating point {point_id}: {e}")
            return False
