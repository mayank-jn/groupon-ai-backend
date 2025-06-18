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
        
        try:
            # Create index for repo field (needed for GitHub repository filtering)
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="repo",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print("✅ Created index for repo field")
        except Exception as e:
            print(f"⚠️  Could not create repo index: {e}")
            
    def _ensure_indexes(self):
        """Ensure required indexes exist."""
        try:
            # Check if indexes exist, create if not
            collection_info = self.client.get_collection(COLLECTION_NAME)
            # If we can get collection info, try to create indexes (they will be ignored if they exist)
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
    
    def get_ingested_github_repositories(self):
        """Get all unique GitHub repositories that have been ingested."""
        try:
            # Use scroll to get all GitHub points
            all_repos = set()
            next_page_offset = None
            
            while True:
                points, next_page_offset = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                    offset=next_page_offset,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="source_type", match=MatchValue(value="github"))]
                    )
                )
                
                # Extract repository names from metadata
                for point in points:
                    repo_name = point.payload.get("repo")
                    if repo_name:
                        all_repos.add(repo_name)
                
                if next_page_offset is None:
                    break
            
            return list(all_repos)
        except Exception as e:
            print(f"Error getting ingested GitHub repositories: {e}")
            return []

    def search_github_semantic(self, query_vector, top_k=10, repositories=None, languages=None, semantic_tags=None, score_threshold=0.3):
        """
        Advanced semantic search specifically for GitHub content with enhanced filtering.
        
        Args:
            query_vector: The embedding vector for the search query
            top_k: Number of results to return
            repositories: List of repository names to search within
            languages: List of programming languages to filter by
            semantic_tags: List of semantic tags to filter by
            score_threshold: Minimum similarity score threshold
        """
        try:
            # Build complex filter conditions
            filter_conditions = [
                FieldCondition(key="source_type", match=MatchValue(value="github"))
            ]
            
            # Repository filtering
            if repositories:
                if len(repositories) == 1:
                    filter_conditions.append(
                        FieldCondition(key="repo", match=MatchValue(value=repositories[0]))
                    )
                else:
                    repo_conditions = [
                        FieldCondition(key="repo", match=MatchValue(value=repo))
                        for repo in repositories
                    ]
                    # Use should condition for OR logic between repositories
                    filter_conditions.append(Filter(should=repo_conditions))
            
            # Language filtering
            if languages:
                if len(languages) == 1:
                    filter_conditions.append(
                        FieldCondition(key="language", match=MatchValue(value=languages[0]))
                    )
                else:
                    lang_conditions = [
                        FieldCondition(key="language", match=MatchValue(value=lang))
                        for lang in languages
                    ]
                    filter_conditions.append(Filter(should=lang_conditions))
            
            # Semantic tags filtering
            if semantic_tags:
                # This requires the semantic_tags to be stored as an array in the payload
                for tag in semantic_tags:
                    filter_conditions.append(
                        FieldCondition(key="semantic_tags", match=MatchValue(value=tag))
                    )
            
            # Combine all conditions with AND logic
            query_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Perform the search
            hits = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
                score_threshold=score_threshold
            )
            
            return hits
            
        except Exception as e:
            print(f"Error in GitHub semantic search: {e}")
            return []

    def get_github_repository_stats(self, repo_name):
        """Get detailed statistics for a specific GitHub repository."""
        try:
            points, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
                with_vectors=False,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="source_type", match=MatchValue(value="github")),
                        FieldCondition(key="repo", match=MatchValue(value=repo_name))
                    ]
                )
            )
            
            if not points:
                return None
            
            # Analyze the repository
            stats = {
                "repo_name": repo_name,
                "total_chunks": len(points),
                "languages": {},
                "chunk_types": {},
                "semantic_tags": {},
                "file_extensions": {},
                "functions": [],
                "documentation_sections": []
            }
            
            for point in points:
                payload = point.payload
                
                # Language distribution
                lang = payload.get("language", "unknown")
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1
                
                # Chunk type distribution
                chunk_type = payload.get("chunk_type", "unknown")
                stats["chunk_types"][chunk_type] = stats["chunk_types"].get(chunk_type, 0) + 1
                
                # Semantic tags
                tags = payload.get("semantic_tags", [])
                for tag in tags:
                    stats["semantic_tags"][tag] = stats["semantic_tags"].get(tag, 0) + 1
                
                # File extensions
                ext = payload.get("file_extension", "unknown")
                stats["file_extensions"][ext] = stats["file_extensions"].get(ext, 0) + 1
                
                # Function names
                if payload.get("function_name"):
                    stats["functions"].append({
                        "name": payload["function_name"],
                        "file": payload.get("name", "unknown"),
                        "path": payload.get("path", "unknown")
                    })
                
                # Documentation sections
                if payload.get("section_title"):
                    stats["documentation_sections"].append({
                        "title": payload["section_title"],
                        "file": payload.get("name", "unknown"),
                        "path": payload.get("path", "unknown")
                    })
            
            return stats
            
        except Exception as e:
            print(f"Error getting repository stats for {repo_name}: {e}")
            return None

    def search_github_by_function(self, function_name, repositories=None):
        """Search for specific functions across GitHub repositories."""
        try:
            filter_conditions = [
                FieldCondition(key="source_type", match=MatchValue(value="github")),
                FieldCondition(key="function_name", match=MatchValue(value=function_name))
            ]
            
            if repositories:
                if len(repositories) == 1:
                    filter_conditions.append(
                        FieldCondition(key="repo", match=MatchValue(value=repositories[0]))
                    )
                else:
                    repo_conditions = [
                        FieldCondition(key="repo", match=MatchValue(value=repo))
                        for repo in repositories
                    ]
                    filter_conditions.append(Filter(should=repo_conditions))
            
            points, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=50,
                with_payload=True,
                with_vectors=False,
                scroll_filter=Filter(must=filter_conditions)
            )
            
            return points
            
        except Exception as e:
            print(f"Error searching for function {function_name}: {e}")
            return []

    def get_github_tech_stack_analysis(self):
        """Analyze technology stack across all ingested GitHub repositories."""
        try:
            points, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
                with_vectors=False,
                scroll_filter=Filter(
                    must=[FieldCondition(key="source_type", match=MatchValue(value="github"))]
                )
            )
            
            analysis = {
                "total_repositories": len(self.get_ingested_github_repositories()),
                "total_chunks": len(points),
                "languages": {},
                "tech_stacks": {},
                "semantic_concepts": {},
                "file_types": {}
            }
            
            for point in points:
                payload = point.payload
                
                # Language analysis
                lang = payload.get("language", "unknown")
                analysis["languages"][lang] = analysis["languages"].get(lang, 0) + 1
                
                # Tech stack analysis
                tech_stack = payload.get("tech_stack", [])
                for tech in tech_stack:
                    analysis["tech_stacks"][tech] = analysis["tech_stacks"].get(tech, 0) + 1
                
                # Semantic concepts
                tags = payload.get("semantic_tags", [])
                for tag in tags:
                    analysis["semantic_concepts"][tag] = analysis["semantic_concepts"].get(tag, 0) + 1
                
                # File types
                ext = payload.get("file_extension", "unknown")
                analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
            
            return analysis
            
        except Exception as e:
            print(f"Error in tech stack analysis: {e}")
            return None
