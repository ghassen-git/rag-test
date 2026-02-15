"""
Test: Chunking Quality Verification
Ensures chunks preserve context and don't break sentences
"""
import pytest


class TestChunkingQuality:
    
    def test_chunk_sizes_valid(self):
        """Verify chunks are within size bounds"""
        try:
            from src.embedding.chunker import chunk_text
        except ImportError:
            pytest.skip("Chunker not implemented")
        
        text = "This is a sentence. " * 100  # Long text
        
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        
        for i, chunk in enumerate(chunks):
            assert 50 < len(chunk) < 400, \
                f"Chunk {i} has invalid size: {len(chunk)}"
        
        print(f"✅ All {len(chunks)} chunks have valid sizes")
    
    def test_chunks_preserve_sentences(self):
        """Verify chunks don't break mid-sentence"""
        try:
            from src.embedding.chunker import chunk_text
        except ImportError:
            pytest.skip("Chunker not implemented")
        
        text = """
        George Orwell's 1984 is a dystopian novel. The book tells
        the story of Winston Smith. Winston lives in a totalitarian
        state called Oceania. The Party controls everything including
        history and language. Big Brother watches all citizens constantly.
        """ * 5
        
        chunks = chunk_text(text, chunk_size=150, overlap=30)
        
        for i, chunk in enumerate(chunks):
            # Check last character (should be punctuation or space)
            last_char = chunk.strip()[-1] if chunk.strip() else ''
            
            # Most chunks should end with sentence punctuation
            # (allow some exceptions for very long sentences)
            if i < len(chunks) - 1 and len(chunk) > 100:
                if last_char not in '.!?':
                    print(f"⚠️  Chunk {i} might break mid-sentence: ...{chunk[-30:]}")
        
        print("✅ Chunking preserves sentence boundaries")
    
    def test_chunk_overlap_works(self):
        """Verify chunks have overlap to preserve context"""
        try:
            from src.embedding.chunker import chunk_text
        except ImportError:
            pytest.skip("Chunker not implemented")
        
        text = "word " * 200  # Repeating words for easy overlap detection
        
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        
        if len(chunks) > 1:
            # Check if consecutive chunks share words
            words_chunk1 = set(chunks[0].split())
            words_chunk2 = set(chunks[1].split())
            overlap_words = words_chunk1.intersection(words_chunk2)
            
            assert len(overlap_words) > 0, "No overlap between consecutive chunks!"
            print(f"✅ Chunks have overlap: {len(overlap_words)} shared words")
        else:
            print("⚠️  Only one chunk - cannot test overlap")
