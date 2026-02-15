"""
Mock embedder for testing without hitting OpenAI API
"""
import numpy as np
from typing import List


class MockEmbedder:
    """Mock embedder that generates deterministic embeddings for testing"""
    
    def __init__(self):
        self.dimension = 1536
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate mock embeddings based on text content.
        Similar texts will have similar embeddings.
        """
        embeddings = []
        
        for text in texts:
            # Create a deterministic embedding based on text content
            text_lower = text.lower()
            
            # Define semantic keywords
            semantic_keywords = ['orwell', 'dystopian', 'totalitarian', 'government', 'novel', 'society', 'explore']
            
            # Count matching keywords
            keyword_matches = sum(1 for word in semantic_keywords if word in text_lower)
            
            # Create base embedding with deterministic seed
            text_hash = hash(text)
            np.random.seed(abs(text_hash) % (2**32))
            base_embedding = np.random.randn(self.dimension).astype(float) * 0.1
            
            if keyword_matches > 0:
                # Create a strong semantic component for related texts
                # Use a fixed seed for the semantic component so related texts get the same component
                np.random.seed(12345)
                semantic_component = np.random.randn(self.dimension).astype(float)
                
                # Mix base and semantic components
                # Higher keyword match = more semantic component
                semantic_weight = min(keyword_matches / len(semantic_keywords), 1.0) * 0.95
                embedding = base_embedding * (1 - semantic_weight) + semantic_component * semantic_weight
            else:
                embedding = base_embedding
            
            # Normalize to unit vector
            embedding = embedding / np.linalg.norm(embedding)
            
            embeddings.append(embedding.tolist())
        
        return embeddings
