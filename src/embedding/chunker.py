
from typing import List, Dict, Any

import logging
import re

from src.config import settings
logger = logging.getLogger(__name__)

class TextChunker:

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        # Clean text
        text = self._clean_text(text)

        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)

            if sentence_length > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(
                        self._create_chunk(chunk_text, chunk_index, metadata)
                    )
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence
                sub_chunks = self._split_long_sentence(sentence)
                for sub_chunk in sub_chunks:
                    chunks.append(self._create_chunk(sub_chunk, chunk_index, metadata))
                    chunk_index += 1
                continue

            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = chunk_text[-self.chunk_overlap:] if len(chunk_text) > self.chunk_overlap else chunk_text
                current_chunk = [overlap_text, sentence]
                current_length = len(overlap_text) + sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(self._create_chunk(chunk_text, chunk_index, metadata))
        
        logger.info(f"Chunked text into {len(chunks)} segments")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        text = re.sub(r'[^\w\s.,!?;:()\-\'"]+', '', text)
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        
        words = sentence.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _create_chunk(
        self,
        text: str,
        index: int,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        
        chunk = {
            "content": text,
            "chunk_index": index,
            "char_count": len(text),
            # Default values to ensure no None
            "book_id": "unknown",
            "title": "Unknown",
            "author": "Unknown",
            "source": "unknown",
            "chapter": 0,
            "page_number": 0,
            "timestamp": 0
        }
        
        if metadata:

            for key, value in metadata.items():
                if value is not None:
                    chunk[key] = value
        
        return chunk

# Global chunker instance
text_chunker = TextChunker()


# Convenience function for tests
def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
    """
    Simple chunking function for testing.
    Returns list of text chunks.
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = chunker.chunk_text(text)
    return [chunk['content'] for chunk in chunks]
