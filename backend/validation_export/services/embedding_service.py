import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from backend.validation_export import validation_settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class EmbeddingService:
    """
    Dedicated Embedding Service supporting Duplicate Detection, Semantic Similarity,
    and grounding checks. Features in-memory caching and a local fallback.
    """
    def __init__(self):
        self.cache: Dict[str, List[float]] = {}
        # Try to initialize Gemini embedding client if possible
        self.gemini_available = False
        try:
            import google.generativeai as genai
            import os
            if os.getenv("GEMINI_API_KEY"):
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                self.gemini_available = True
                logger.info("Gemini Embedding API is available.")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini Embedding API: {str(e)}. Using local fallback.")

    async def get_embedding(self, text: str) -> List[float]:
        """
        Retrieves the embedding vector for a given text. Uses cache if available.
        """
        if not text:
            return [0.0] * 384  # default size
            
        if text in self.cache:
            return self.cache[text]

        vector = None
        if self.gemini_available:
            try:
                import google.generativeai as genai
                # Use text-embedding-004
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="semantic_similarity"
                )
                vector = response["embedding"]
            except Exception as e:
                logger.error(f"Gemini embedding generation failed: {str(e)}. Falling back to local vectorizer.")
                self.gemini_available = False


        if vector is None:
            # Local fallback: Generate a simple deterministic vector using token hashing
            vector = self._generate_local_vector(text)

        self.cache[text] = vector
        return vector

    def _generate_local_vector(self, text: str) -> List[float]:
        """
        A lightweight, deterministic token-hashing vectorizer that serves as a
        robust, offline fallback (producing 384-dimensional normalized vectors).
        """
        import hashlib
        tokens = text.lower().split()
        vector = np.zeros(384)
        
        if not tokens:
            return vector.tolist()

        for token in tokens:
            # Hash token to multiple dimensions to create a sparse representation
            for i in range(3):
                h = int(hashlib.md5((token + str(i)).encode('utf-8')).hexdigest(), 16)
                idx = h % 384
                vector[idx] += 1.0

        # L2 Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector.tolist()

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculates the cosine similarity between two texts.
        """
        v1 = await self.get_embedding(text1)
        v2 = await self.get_embedding(text2)
        
        a = np.array(v1)
        b = np.array(v2)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(dot_product / (norm_a * norm_b))

    async def find_duplicates(self, stories: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
        """
        Detects pairwise duplicate stories based on DUPLICATE_THRESHOLD.
        Returns a list of tuples: (story_id_1, story_id_2, similarity_score)
        """
        duplicates = []
        n = len(stories)
        
        # Pre-compute embeddings
        embeddings = []
        for s in stories:
            text = f"{s.get('title', '')} {s.get('user_story_text', '')}"
            embeddings.append((s.get("id", "UNKNOWN"), text))

        for i in range(n):
            for j in range(i + 1, n):
                id1, text1 = embeddings[i]
                id2, text2 = embeddings[j]
                
                sim = await self.calculate_similarity(text1, text2)
                if sim >= validation_settings.DUPLICATE_THRESHOLD:
                    duplicates.append((id1, id2, sim))
                    
        return duplicates
