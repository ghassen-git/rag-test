"""Tests for RAG system."""
import asyncio
import pytest

from src.embedding.chunker import text_chunker
from src.embedding.openai_embedder import openai_embedder
class TestChunker:
    """Test text chunking."""
    
    def test_chunk_text(self):
        """Test basic text chunking."""
        text = "This is a test sentence. " * 50
        chunks = text_chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all("content" in chunk for chunk in chunks)
        assert all(len(chunk["content"]) <= 800 for chunk in chunks)
    
    def test_empty_text(self):
        """Test empty text handling."""
        chunks = text_chunker.chunk_text("")
        assert len(chunks) == 0
    
    def test_chunk_metadata(self):
        """Test metadata attachment."""
        text = "Test text for chunking."
        metadata = {"book_id": "123", "title": "Test Book"}
        chunks = text_chunker.chunk_text(text, metadata)
        
        assert len(chunks) > 0
        assert chunks[0]["book_id"] == "123"
        assert chunks[0]["title"] == "Test Book"


class TestEmbedder:
    """Test embedding generation."""
    
    @pytest.mark.asyncio
    async def test_embed_text(self):
        """Test single text embedding."""
        text = "This is a test sentence for embedding."
        
        try:
            embedding = await openai_embedder.embed_text(text)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e) or "rate" in str(e).lower():
                pytest.skip(f"OpenAI API quota exceeded: {e}")
            raise
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # OpenAI text-embedding-3-small dimension
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding."""
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence."
        ]
        
        try:
            embeddings = await openai_embedder.embed_batch(texts)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e) or "rate" in str(e).lower():
                pytest.skip(f"OpenAI API quota exceeded: {e}")
            raise
        
        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_embed_documents(self):
        """Test document embedding."""
        documents = [
            {"content": "First document content."},
            {"content": "Second document content."}
        ]
        
        try:
            result = await openai_embedder.embed_documents(documents)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e) or "rate" in str(e).lower():
                pytest.skip(f"OpenAI API quota exceeded: {e}")
            raise
        
        assert len(result) == 2
        assert all("vector" in doc for doc in result)
        assert all(len(doc["vector"]) == 1536 for doc in result)


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self):
        """Test complete pipeline from text to embeddings."""
        text = """
        1984 is a dystopian novel by George Orwell. The story takes place in 
        Airstrip One, a province of the superstate Oceania. The protagonist, 
        Winston Smith, works for the Ministry of Truth, where he rewrites 
        historical records to match the party's propaganda.
        """
        
        # Chunk text
        chunks = text_chunker.chunk_text(
            text,
            metadata={"book_id": "1", "title": "1984", "author": "George Orwell"}
        )
        
        assert len(chunks) > 0
        
        # Generate embeddings
        try:
            documents = await openai_embedder.embed_documents(chunks, text_field="content")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e) or "rate" in str(e).lower():
                pytest.skip(f"OpenAI API quota exceeded: {e}")
            raise
        
        assert len(documents) == len(chunks)
        assert all("vector" in doc for doc in documents)
        assert all("book_id" in doc for doc in documents)


# Test scenarios from requirements
class TestScenarios:
    """Test specific scenarios from requirements."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_scenario(self):
        """Test: Find books about dystopian societies."""
        # This would test the full search pipeline
        query = "Find books about dystopian societies"
        # Would call search_agent.search(query)
        pass
    
    @pytest.mark.asyncio
    async def test_hybrid_query_scenario(self):
        """Test: What's the average rating of sci-fi books published after 2000?"""
        # This would test analyst_agent queries
        pass
    
    @pytest.mark.asyncio
    async def test_action_query_scenario(self):
        """Test: Update the rating of '1984' to 5 stars."""
        # This would test update operations
        pass
    
    @pytest.mark.asyncio
    async def test_multi_source_scenario(self):
        """Test: Show me reviews for 'Animal Farm' and summarize criticisms."""
        # This would test orchestrator combining multiple sources
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
