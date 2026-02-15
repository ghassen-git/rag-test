
from typing import Set

from pathlib import Path
import asyncio
import logging
import time

from src.config import settings
from src.embedding.chunker import text_chunker
from src.embedding.openai_embedder import openai_embedder
from src.ocr.mathpix_client import mathpix_client
from src.vector_db.milvus_client import milvus_client
logger = logging.getLogger(__name__)

class PDFProcessor:

    def __init__(self):
        
        self.storage_path = Path(settings.blob_storage_path)
        self.processed_files: Set[str] = set()  # Track processed files to avoid duplicates
    
    async def _process_single_pdf(
        self,
        pdf_path: str,
        book_id: str = None,
        chapter: int = None,
        title: str = None
    ) -> None:
        
        logger.info(f"Processing PDF: {pdf_path}")

        path_obj = Path(pdf_path)
        filename = path_obj.stem
        
        if book_id is None or chapter is None or title is None:
            parts = filename.split("_", 2)
            if book_id is None:
                book_id = parts[0] if len(parts) > 0 else "unknown"
            if chapter is None:
                chapter = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            if title is None:
                title = parts[2] if len(parts) > 2 else filename
        
        # Perform OCR
        ocr_result = await mathpix_client.process_pdf(pdf_path)
        
        extracted_text = ocr_result.get("text", "")

        if not extracted_text or len(extracted_text.strip()) < 10:
            logger.warning(
                f"Mathpix returned empty/minimal text for {pdf_path}, "
                f"trying PyPDF2 fallback"
            )
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    fallback_text = ""
                    for page in pdf_reader.pages:
                        fallback_text += page.extract_text() + "\n"
                    
                    if fallback_text.strip():
                        extracted_text = fallback_text
                        logger.info(
                            f"PyPDF2 extracted {len(extracted_text)} characters"
                        )
                    else:
                        logger.warning(
                            f"PyPDF2 also failed to extract text from {pdf_path}"
                        )
            except Exception as e:
                logger.error(f"PyPDF2 fallback failed: {e}")
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            logger.warning(
                f"No text extracted from {pdf_path} after all attempts"
            )
            return
        
        # Try to detect chapters in the text
        chapters = self._detect_chapters(extracted_text)
        
        if len(chapters) > 1:
            logger.info(f"Detected {len(chapters)} chapters in PDF")
            # Process each chapter separately
            for chapter_num, chapter_text in chapters.items():
                await self._process_chapter_text(
                    chapter_text,
                    book_id,
                    chapter_num,
                    title
                )
        else:
            # Process as single chapter
            await self._process_chapter_text(
                extracted_text,
                book_id,
                chapter if chapter is not None else 1,
                title
            )
    
    def _detect_chapters(self, text: str) -> dict:
        
        import re
        
        patterns = [
            (r'CHAPTER\s+([IVXLCDM]+)', 'roman'),  # CHAPTER I, CHAPTER XIV
            (r'CHAPTER\s+(\d+)', 'digit'),  # CHAPTER 1, CHAPTER 14
            (r'Chapter\s+(\d+)', 'digit'),  # Chapter 1
            (r'CHAPTER\s+([A-Z][A-Z]+)', 'word'),  # CHAPTER ONE, CHAPTER SIX
            (r'CHAPTER\s+([A-Z][a-z]+)', 'word'),  # CHAPTER One, CHAPTER Six
        ]
        
        chapters = {}
        chapter_positions = []
        
        # Find all chapter markers
        for pattern, num_type in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                pos = match.start()
                chapter_marker = match.group(0)
                chapter_num_str = match.group(1)
                
                # Convert to integer based on type
                try:
                    if num_type == 'digit':
                        chapter_num = int(chapter_num_str)
                    elif num_type == 'roman':
                        chapter_num = self._roman_to_int(chapter_num_str)
                    elif num_type == 'word':
                        chapter_num = self._word_to_int(chapter_num_str)
                    else:
                        continue
                    
                    # Avoid duplicates at same position
                    if not any(p[0] == pos for p in chapter_positions):
                        chapter_positions.append((pos, chapter_num, chapter_marker))
                        logger.debug(f"Found chapter marker: {chapter_marker} at position {pos}")
                except Exception as e:
                    logger.debug(f"Could not parse chapter number '{chapter_num_str}': {e}")
                    continue
        
        # Sort by position
        chapter_positions.sort(key=lambda x: x[0])
        
        logger.info(f"Detected {len(chapter_positions)} chapter markers")
        
        # Extract text for each chapter
        if len(chapter_positions) > 1:
            for i, (pos, num, marker) in enumerate(chapter_positions):
                if i < len(chapter_positions) - 1:
                    next_pos = chapter_positions[i + 1][0]
                    chapter_text = text[pos:next_pos]
                else:
                    chapter_text = text[pos:]
                
                chapters[num] = chapter_text
                logger.debug(f"Chapter {num}: {len(chapter_text)} characters")
        
        return chapters
    
    def _roman_to_int(self, s: str) -> int:
        
        roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        result = 0
        for i in range(len(s)):
            if i > 0 and roman[s[i]] > roman[s[i - 1]]:
                result += roman[s[i]] - 2 * roman[s[i - 1]]
            else:
                result += roman[s[i]]
        return result
    
    def _word_to_int(self, word: str) -> int:
        
        # Normalize to title case for matching
        word_normalized = word.capitalize()
        
        words = {
            'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5,
            'Six': 6, 'Seven': 7, 'Eight': 8, 'Nine': 9, 'Ten': 10,
            'Eleven': 11, 'Twelve': 12, 'Thirteen': 13, 'Fourteen': 14,
            'Fifteen': 15, 'Sixteen': 16, 'Seventeen': 17, 'Eighteen': 18,
            'Nineteen': 19, 'Twenty': 20, 'Twenty-one': 21, 'Twenty-two': 22,
            'Twenty-three': 23, 'Twenty-four': 24, 'Twenty-five': 25,
            'Twenty-six': 26, 'Twenty-seven': 27, 'Twenty-eight': 28,
            'Twenty-nine': 29, 'Thirty': 30
        }
        
        result = words.get(word_normalized)
        if result:
            return result
        
        # Try uppercase version
        word_upper = word.upper()
        words_upper = {k.upper(): v for k, v in words.items()}
        return words_upper.get(word_upper, 1)
    
    async def _process_chapter_text(
        self,
        text: str,
        book_id: str,
        chapter: int,
        title: str
    ) -> None:

        # Chunk text
        chunks = text_chunker.chunk_text(
            text,
            metadata={
                "book_id": str(book_id) if book_id else "unknown",
                "title": str(title) if title else "Unknown",
                "author": "Unknown",
                "source": "pdf",
                "chapter": int(chapter) if chapter is not None else 0,
                "page_number": 0,
                "timestamp": int(time.time())
            }
        )
        
        if not chunks:
            logger.warning(f"No chunks created from chapter {chapter}")
            return
        
        # Generate embeddings
        documents = await openai_embedder.embed_documents(chunks, text_field="content")
        
        # Prepare for Milvus
        milvus_data = []
        for doc in documents:
            chunk_id = (
                f"{doc['book_id']}_ch{doc['chapter']}_"
                f"p{doc['page_number']}_{doc['chunk_index']}"
            )
            
            # Ensure all fields have correct types
            milvus_data.append({
                "id": str(chunk_id),
                "vector": doc["vector"],
                "book_id": str(doc.get("book_id", "unknown")),
                "title": str(doc.get("title", "Unknown"))[:512],
                "author": str(doc.get("author", "Unknown"))[:256],
                "content": str(doc.get("content", ""))[:4096],
                "source": str(doc.get("source", "pdf"))[:64],
                "chapter": int(doc.get("chapter", 0)),
                "page_number": int(doc.get("page_number", 0)),
                "timestamp": int(doc.get("timestamp", int(time.time())))
            })
        
        # Insert into Milvus
        milvus_client.insert(milvus_data)
        
        logger.info(
            f"Successfully processed chapter {chapter}: "
            f"{len(milvus_data)} chunks indexed"
        )

# Global processor instance
pdf_processor = PDFProcessor()
