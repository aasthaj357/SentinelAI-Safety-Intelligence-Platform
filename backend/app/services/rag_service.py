import logging
import uuid
import math
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

# Lazy-load the embedding model to avoid blocking at import time
_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            import os
            os.environ["HF_HOME"] = os.path.abspath("tmp/hf_cache")
            os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.abspath("tmp/st_cache")
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer model: {e}. RAG embeddings will be unavailable.")
            _model = None
    return _model

class RagService:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    def embed_and_store(self, project_id: str, source_type: str, source_id: str, content: str, user_id: str = None, metadata: dict = None):
        """
        Chunks the content, generates embeddings, and stores them in Supabase knowledge_base.
        """
        if not content.strip():
            return

        # Ensure source_id is a valid UUID
        try:
            uuid.UUID(str(source_id))
            valid_source_id = str(source_id)
        except ValueError:
            valid_source_id = str(uuid.uuid4())

        chunks = self.text_splitter.split_text(content)

        for chunk in chunks:
            model = _get_model()
            if model is None:
                continue
            embedding = model.encode(chunk).tolist()
            try:
                result = supabase.table("knowledge_base").insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "source_type": source_type,
                    "source_id": valid_source_id,
                    "content": chunk,
                    "metadata": metadata or {},
                    "embedding": embedding
                }).execute()
                if getattr(result, 'error', None) or not getattr(result, 'data', None):
                    logger.error(
                        "Failed to insert knowledge_base chunk for project %s source_id %s: %s",
                        project_id,
                        valid_source_id,
                        getattr(result, 'error', None) or 'no data returned',
                    )
            except Exception as e:
                logger.error(
                    "Exception inserting knowledge_base chunk for project %s source_id %s: %s",
                    project_id,
                    valid_source_id,
                    e,
                )

    def similarity_search(self, project_id: str, query: str, user_id: str = None, top_k: int = 5) -> list:
        """
        Embeds the query and performs a vector similarity search via Supabase RPC.
        """
        model = _get_model()
        if model is None:
            return []
        query_embedding = model.encode(query).tolist()
        
        try:
            # RPC match_knowledge filters by project_id
            res = supabase.rpc('match_knowledge', {
                'query_embedding': query_embedding,
                'match_threshold': 0.3,
                'match_count': top_k,
                'p_project_id': project_id
            }).execute()
            
            data = res.data if res.data else []
            if user_id:
                data = [d for d in data if d.get("user_id") == user_id]
            return data
        except Exception as e:
            print(f"RAG RPC search error, using local fallback: {e}")
            return self._local_similarity_search(project_id, query_embedding, user_id, top_k)

    def _local_similarity_search(self, project_id: str, query_embedding: list, user_id: str, top_k: int) -> list:
        try:
            query = supabase.table("knowledge_base").select(
                "id,project_id,user_id,source_type,source_id,content,metadata,embedding"
            ).eq("project_id", project_id)
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.limit(200).execute()
        except Exception as e:
            logger.error("Local RAG fallback failed to fetch rows for project %s: %s", project_id, e)
            return []

        def cosine(a, b):
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(float(x) * float(y) for x, y in zip(a, b))
            mag_a = math.sqrt(sum(float(x) * float(x) for x in a))
            mag_b = math.sqrt(sum(float(y) * float(y) for y in b))
            if not mag_a or not mag_b:
                return 0.0
            return dot / (mag_a * mag_b)

        ranked = []
        for row in res.data or []:
            score = cosine(query_embedding, row.get("embedding") or [])
            row.pop("embedding", None)
            row["similarity"] = score
            ranked.append(row)

        ranked.sort(key=lambda row: row.get("similarity", 0), reverse=True)
        return ranked[:top_k]

rag_service = RagService()

def get_rag_service():
    return rag_service
