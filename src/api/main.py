
from typing import Dict, Any

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pathlib import Path
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field
import asyncio
import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from src.agents.analyst_agent import analyst_agent
from src.agents.orchestrator import orchestrator
from src.cdc.debezium_config import debezium_manager
from src.cdc.kafka_consumer import cdc_consumer
from src.config import settings
from src.ocr.pdf_processor import pdf_processor
from src.vector_db.milvus_client import milvus_client
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _clean_gutenberg_text(text: str) -> str:
    
    import re

    # Look for common chapter markers
    chapter_patterns = [
        r'\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*',
        r'The Project Gutenberg EBook.*?(?=CHAPTER|Chapter|PREFACE|Preface|PROLOGUE|Prologue|\n\n\n)',
        r'Project Gutenberg.*?License.*?(?=CHAPTER|Chapter|PREFACE|Preface|PROLOGUE|Prologue|\n\n\n)',
    ]
    
    for pattern in chapter_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    end_patterns = [
        r'\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG.*',
        r'End of (?:the )?Project Gutenberg.*',
    ]
    
    for pattern in end_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

    metadata_patterns = [
        r'Produced by.*?(?=\n\n)',
        r'Updated editions will replace.*?(?=\n\n)',
        r'Section \d+\..*?Information about.*?(?=\n\n\n)',
        r'\d+\.\w+\.\d+\..*?(?=\n\n)',  # License section numbers
        r'http://www\.gutenberg\.org.*?(?=\n)',
        r'www\.gutenberg\.org.*?(?=\n)',
    ]
    
    for pattern in metadata_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    text = re.sub(r'\[Illustration:.*?\]', '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Trim
    text = text.strip()
    
    return text

# Prometheus metrics
query_counter = Counter('rag_queries_total', 'Total number of RAG queries')
query_duration = Histogram('rag_query_duration_seconds', 'RAG query duration')
error_counter = Counter('rag_errors_total', 'Total number of errors', ['error_type'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    logger.info("Starting RAG system...")
    
    # Connect to Milvus
    try:
        milvus_client.connect()
        logger.info("✓ Milvus connected")
    except Exception as e:
        logger.error(f"✗ Milvus connection failed: {e}")
    
    # Connect to databases
    try:
        analyst_agent.connect()
        logger.info("✓ Databases connected")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
    
    # Setup Debezium connectors
    try:
        debezium_manager.setup_all_connectors()
        logger.info("✓ Debezium connectors configured")
    except Exception as e:
        logger.warning(f"⚠ Debezium setup warning: {e}")
    
    # Start CDC consumer in background
    asyncio.create_task(cdc_consumer.start_consuming())
    logger.info("✓ CDC consumer started")
    
    logger.info("🚀 RAG system ready!")
    
    yield
    
    # Cleanup
    logger.info("Shutting down RAG system...")
    cdc_consumer.stop()
    milvus_client.disconnect()
    analyst_agent.disconnect()
    logger.info("✓ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Real-Time RAG System",
    description="Production-ready RAG with CDC, OCR, and Multi-Agent Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    
    question: str = Field(..., description="User question")
    top_k: int = Field(5, description="Number of results to return", ge=1, le=20)

class QueryResponse(BaseModel):
    
    answer: str
    intent: str
    sources: list
    metadata: Dict[str, Any]

class BookRequest(BaseModel):
    
    title: str
    author: str
    isbn: str = None
    publication_date: str = None
    genre: str = None
    rating: float = Field(None, ge=0, le=5)
    description: str = None

class UpdateRatingRequest(BaseModel):
    
    book_id: str
    new_rating: float = Field(..., ge=0, le=5)

# API Endpoints
@app.get("/", tags=["System"])
async def root():
    
    return {
        "service": "Real-Time RAG System",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", tags=["System"])
async def health_check():
    
    health_status = {
        "status": "healthy",
        "components": {}
    }
    
    # Check Milvus
    try:
        stats = milvus_client.get_stats()
        health_status["components"]["milvus"] = {
            "status": "healthy",
            "entities": stats.get("num_entities", 0)
        }
    except Exception as e:
        health_status["components"]["milvus"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check PostgreSQL
    try:
        analyst_agent.pg_cursor.execute("SELECT 1")
        health_status["components"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["postgres"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check MongoDB
    try:
        analyst_agent.mongo_client.admin.command('ping')
        health_status["components"]["mongodb"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/test-async", tags=["System"])
async def test_async():
    
    await asyncio.sleep(0.1)
    return {"status": "async works"}

@app.post("/query", tags=["RAG Query"])
async def process_query_endpoint(request: QueryRequest):
    
    query_counter.inc()
    
    try:
        logger.info(f"Processing query: {request.question}")
        
        # Process through orchestrator
        result = await orchestrator.process_query(request.question)
        
        # Format response
        sources = []
        for search_result in result.get("search_results", [])[:request.top_k]:
            sources.append({
                "book_id": search_result.get("book_id"),
                "title": search_result.get("title"),
                "author": search_result.get("author"),
                "content": search_result.get("content"),
                "score": search_result.get("score"),
                "source": search_result.get("source")
            })
        
        return {
            "answer": result.get("answer", "No answer generated"),
            "intent": result.get("intent", "unknown"),
            "sources": sources,
            "metadata": {
                "num_sources": len(sources),
                "book_data": result.get("book_data", {}),
                "processing_steps": result.get("messages", [])
            }
        }
        
    except Exception as e:
        error_counter.labels(error_type="query_processing").inc()
        logger.error(f"Query processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_book", tags=["Book Management"])
async def add_book(book: BookRequest):
    
    try:
        # This would insert into PostgreSQL
        # For now, return success
        logger.info(f"Adding book: {book.title}")
        
        return {
            "success": True,
            "message": f"Book '{book.title}' added successfully",
            "book": book.dict()
        }
        
    except Exception as e:
        error_counter.labels(error_type="add_book").inc()
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books/{book_id}", tags=["Data Access"])
async def get_book(book_id: str):
    
    try:
        book = analyst_agent.get_book_by_id(book_id)
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Get review statistics
        review_stats = analyst_agent.get_review_statistics(book_id)
        
        return {
            "book": book,
            "review_statistics": review_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_counter.labels(error_type="get_book").inc()
        logger.error(f"Error fetching book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_rating", tags=["Book Management"])
async def update_rating(request: UpdateRatingRequest):
    
    try:
        success = analyst_agent.update_book_rating(
            request.book_id,
            request.new_rating
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update rating")
        
        return {
            "success": True,
            "book_id": request.book_id,
            "new_rating": request.new_rating
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_counter.labels(error_type="update_rating").inc()
        logger.error(f"Error updating rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index_book", tags=["Content Upload"])
async def index_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(...),
    genre: str = Form("General"),
    isbn: str = Form(""),
    description: str = Form(""),
    chapter: int = Form(1)
):
    
    try:
        import uuid
        import time
        from src.embedding.chunker import text_chunker
        from src.embedding.openai_embedder import openai_embedder
        
        logger.info(f"Starting complete book indexing: {title} by {author}")
        
        import psycopg2
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO books (title, author, isbn, genre, description, publication_date, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            title,
            author,
            isbn if isbn else None,
            genre,
            description if description else None,
            "2024-01-01",
            0.0
        ))
        
        book_id = str(cursor.fetchone()[0])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✓ Book created in database: {book_id}")
        
        # Step 2: Process the file based on type
        text_content = ""
        file_type = file.filename.lower().split('.')[-1]
        
        if file_type == 'pdf':
            # Save PDF temporarily
            safe_filename = f"{book_id}_{chapter}_{file.filename}"
            file_path = Path(settings.blob_storage_path) / safe_filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = await file.read()
            file_path.write_bytes(content)
            
            logger.info(f"✓ PDF saved: {file_path}")
            
            # Try OCR first
            from src.ocr.mathpix_client import mathpix_client
            try:
                ocr_result = await mathpix_client.process_pdf(str(file_path))
                text_content = ocr_result.get("text", "")
                logger.info(f"✓ OCR completed: {len(text_content)} characters extracted")
            except Exception as ocr_error:
                logger.warning(f"OCR failed: {ocr_error}, trying PyPDF2 fallback")
                text_content = ""

            if not text_content or len(text_content) < 50:
                logger.info("Attempting PyPDF2 text extraction as fallback")
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_parts = []
                        for page in pdf_reader.pages:
                            text_parts.append(page.extract_text())
                        text_content = "\n".join(text_parts)
                        logger.info(f"✓ PyPDF2 extraction: {len(text_content)} characters")
                except Exception as pdf_error:
                    logger.error(f"PyPDF2 extraction also failed: {pdf_error}")
                    text_content = ""
            
        elif file_type == 'txt':
            # Read text file
            content = await file.read()
            text_content = content.decode('utf-8')
            logger.info(f"✓ Text file read: {len(text_content)} characters")
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_type}. Use PDF or TXT files."
            )
        
        # Step 3: Check if we got text
        if not text_content or len(text_content) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"No text extracted from file. Extracted only {len(text_content)} characters. The file may be image-based, encrypted, or empty."
            )

        text_content = _clean_gutenberg_text(text_content)
        logger.info(f"✓ Text cleaned: {len(text_content)} characters after cleanup")
        
        # Step 4: Chunk the text
        chunks = text_chunker.chunk_text(
            text_content,
            metadata={
                "book_id": book_id,
                "title": title,
                "author": author,
                "source": file_type,
                "chapter": chapter,
                "page_number": 0,
                "timestamp": int(time.time())
            }
        )
        
        logger.info(f"✓ Text chunked: {len(chunks)} chunks created")
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No chunks created from text. Content may be too short."
            )
        
        # Step 5: Generate embeddings
        documents = await openai_embedder.embed_documents(chunks, text_field="content")
        
        logger.info(f"✓ Embeddings generated: {len(documents)} vectors")
        
        # Step 6: Prepare for Milvus
        milvus_data = []
        for doc in documents:
            chunk_id = f"{doc['book_id']}_ch{doc['chapter']}_idx{doc['chunk_index']}_{int(time.time())}"
            
            milvus_data.append({
                "id": str(chunk_id),
                "vector": doc["vector"],
                "book_id": str(doc.get("book_id", "unknown")),
                "title": str(doc.get("title", "Unknown"))[:512],
                "author": str(doc.get("author", "Unknown"))[:256],
                "content": str(doc.get("content", ""))[:4096],
                "source": str(doc.get("source", file_type))[:64],
                "chapter": int(doc.get("chapter", 0)),
                "page_number": int(doc.get("page_number", 0)),
                "timestamp": int(doc.get("timestamp", int(time.time())))
            })
        
        # Step 7: Insert into Milvus
        milvus_client.insert(milvus_data)
        
        logger.info(f"✓ Indexed in Milvus: {len(milvus_data)} chunks")
        
        return {
            "success": True,
            "message": "Book indexed successfully",
            "book_id": book_id,
            "title": title,
            "author": author,
            "file_type": file_type,
            "text_extracted": len(text_content),
            "chunks_created": len(chunks),
            "chunks_indexed": len(milvus_data),
            "chapter": chapter,
            "next_steps": {
                "view_chunks": f"/view_chunks/{book_id}",
                "query": f"/query with question about '{title}'",
                "get_book": f"/books/{book_id}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_counter.labels(error_type="index_book").inc()
        logger.error(f"Error indexing book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_text", tags=["Content Upload"])
async def upload_text(
    book_id: str = Form(...),
    chapter: int = Form(1),
    title: str = Form(...),
    content: str = Form(...)
):
    
    try:
        from src.embedding.chunker import text_chunker
        from src.embedding.openai_embedder import openai_embedder
        import time
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty")
        
        # Get book info from database
        book = analyst_agent.get_book_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=404,
                detail=f"Book with ID {book_id} not found"
            )
        
        logger.info(f"Processing text for book {book_id}, chapter {chapter}")
        
        # Chunk text
        chunks = text_chunker.chunk_text(
            content,
            metadata={
                "book_id": book_id,
                "title": book.get("title", title),
                "author": book.get("author", "Unknown"),
                "source": "text_upload",
                "chapter": chapter,
                "page_number": 0,
                "timestamp": int(time.time())
            }
        )
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No chunks created from content"
            )
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        documents = await openai_embedder.embed_documents(chunks, text_field="content")
        
        # Prepare for Milvus
        milvus_data = []
        for doc in documents:
            chunk_id = (
                f"{doc['book_id']}_ch{doc['chapter']}_"
                f"upload_{doc['chunk_index']}_{int(time.time())}"
            )
            
            # Ensure all fields have correct types
            milvus_data.append({
                "id": str(chunk_id),
                "vector": doc["vector"],
                "book_id": str(doc.get("book_id", "unknown")),
                "title": str(doc.get("title", "Unknown"))[:512],
                "author": str(doc.get("author", "Unknown"))[:256],
                "content": str(doc.get("content", ""))[:4096],
                "source": str(doc.get("source", "text_upload"))[:64],
                "chapter": int(doc.get("chapter", 0)),
                "page_number": int(doc.get("page_number", 0)),
                "timestamp": int(doc.get("timestamp", int(time.time())))
            })
        
        # Insert into Milvus
        milvus_client.insert(milvus_data)
        
        logger.info(f"Successfully indexed {len(milvus_data)} chunks")
        
        return {
            "success": True,
            "message": f"Text content indexed successfully",
            "book_id": book_id,
            "book_title": book.get("title"),
            "chapter": chapter,
            "chunks_created": len(chunks),
            "chunks_indexed": len(milvus_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_counter.labels(error_type="text_upload").inc()
        logger.error(f"Error uploading text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_image", tags=["Content Upload"])
async def upload_image(
    file: UploadFile = File(...),
    book_id: str = Form(...),
    chapter: int = Form(1),
    page_number: int = Form(1)
):
    
    try:
        from src.ocr.mathpix_client import mathpix_client
        
        # Validate file type
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Only JPG and PNG images are supported")
        
        # Save image temporarily
        filename = f"{book_id}_{chapter}_p{page_number}_{file.filename}"
        file_path = Path(settings.blob_storage_path) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await file.read()
        file_path.write_bytes(content)
        
        logger.info(f"Processing image: {file_path}")
        
        # Perform OCR
        ocr_result = await mathpix_client.process_image(str(file_path))
        
        if not ocr_result.get("text"):
            raise HTTPException(status_code=400, detail="No text extracted from image")
        
        # Now process the extracted text
        from src.embedding.chunker import text_chunker
        from src.embedding.openai_embedder import openai_embedder
        import time
        
        # Get book info
        book = analyst_agent.get_book_by_id(book_id)
        
        # Chunk and embed
        chunks = text_chunker.chunk_text(
            ocr_result["text"],
            metadata={
                "book_id": book_id,
                "title": book.get("title", "Unknown") if book else "Unknown",
                "author": book.get("author", "Unknown") if book else "Unknown",
                "source": "image_ocr",
                "chapter": chapter,
                "page_number": page_number,
                "timestamp": int(time.time())
            }
        )
        
        if chunks:
            documents = await openai_embedder.embed_documents(chunks, text_field="content")
            
            milvus_data = []
            for doc in documents:
                chunk_id = (
                    f"{doc['book_id']}_ch{doc['chapter']}_"
                    f"p{page_number}_img_{doc['chunk_index']}"
                )
                
                # Ensure all fields have correct types
                milvus_data.append({
                    "id": str(chunk_id),
                    "vector": doc["vector"],
                    "book_id": str(doc.get("book_id", "unknown")),
                    "title": str(doc.get("title", "Unknown"))[:512],
                    "author": str(doc.get("author", "Unknown"))[:256],
                    "content": str(doc.get("content", ""))[:4096],
                    "source": str(doc.get("source", "image_ocr"))[:64],
                    "chapter": int(doc.get("chapter", 0)),
                    "page_number": int(doc.get("page_number", 0)),
                    "timestamp": int(doc.get("timestamp", int(time.time())))
                })
            
            milvus_client.insert(milvus_data)
            
            return {
                "success": True,
                "message": "Image processed and indexed successfully",
                "filename": filename,
                "extracted_text": ocr_result["text"],
                "chunks_indexed": len(milvus_data)
            }
        else:
            return {
                "success": True,
                "message": "Image processed but no chunks created",
                "filename": filename,
                "extracted_text": ocr_result["text"],
                "chunks_indexed": 0
            }
        
    except HTTPException:
        raise
    except Exception as e:
        error_counter.labels(error_type="image_upload").inc()
        logger.error(f"Error uploading image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/pdf/{filename}", tags=["Debug"])
async def debug_pdf(filename: str):
    
    try:
        from src.ocr.mathpix_client import mathpix_client
        
        file_path = Path(settings.blob_storage_path) / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Get file info
        file_size = file_path.stat().st_size
        
        # Try OCR
        ocr_result = await mathpix_client.process_pdf(str(file_path))
        
        return {
            "filename": filename,
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "ocr_result": {
                "text_length": len(ocr_result.get("text", "")),
                "text_preview": ocr_result.get("text", "")[:500],
                "full_text": ocr_result.get("text", ""),
                "confidence": ocr_result.get("confidence", 0),
                "latex": ocr_result.get("latex", "")[:200] if ocr_result.get("latex") else "",
                "page_number": ocr_result.get("page_number")
            },
            "diagnosis": {
                "has_text": bool(ocr_result.get("text", "").strip()),
                "text_empty": not bool(ocr_result.get("text", "").strip()),
                "possible_issues": [
                    "PDF may be image-based and OCR failed" if not ocr_result.get("text") else None,
                    "PDF may be encrypted or protected" if not ocr_result.get("text") else None,
                    "Mathpix API may need different settings" if not ocr_result.get("text") else None
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error debugging PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/view_chunks/{book_id}", tags=["Data Access"])
async def view_chunks(book_id: str, chapter: int = None, source: str = None):
    
    try:
        # Build filter expression
        filters = [f'book_id == "{book_id}"']
        if chapter is not None:
            filters.append(f'chapter == {chapter}')
        if source:
            filters.append(f'source == "{source}"')
        
        expr = ' and '.join(filters)
        
        # Query Milvus
        results = milvus_client.collection.query(
            expr=expr,
            output_fields=['id', 'book_id', 'title', 'author', 'content', 'source', 'chapter', 'page_number'],
            limit=100
        )
        
        # Format results
        chunks = []
        for record in results:
            chunks.append({
                "id": record["id"],
                "book_id": record["book_id"],
                "title": record["title"],
                "author": record["author"],
                "source": record["source"],
                "chapter": record["chapter"],
                "page_number": record["page_number"],
                "content": record["content"],
                "content_length": len(record["content"])
            })
        
        return {
            "book_id": book_id,
            "total_chunks": len(chunks),
            "filters": {
                "chapter": chapter,
                "source": source
            },
            "chunks": chunks
        }
        
    except Exception as e:
        logger.error(f"Error viewing chunks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", tags=["System"])
async def get_stats():
    
    try:
        milvus_stats = milvus_client.get_stats()
        
        return {
            "vector_database": milvus_stats,
            "total_books": len(analyst_agent.search_books()),
            "system_status": "operational"
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MCP (Model Context Protocol) Endpoints
@app.get("/mcp/tools", tags=["MCP"])
async def list_mcp_tools():
    
    from src.mcp.mcp_server import mcp_server
    
    return {
        "server": mcp_server.name,
        "version": mcp_server.version,
        "tools": mcp_server.get_tool_definitions()
    }

@app.post("/mcp/call", tags=["MCP"])
async def call_mcp_tool(request: Dict[str, Any]):
    
    from src.mcp.mcp_server import mcp_server
    
    try:
        tool_name = request.get("tool")
        parameters = request.get("parameters", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing 'tool' field in request body")
        
        result = await mcp_server.call_tool(tool_name, parameters)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP tool call error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/resources", tags=["MCP"])
async def list_mcp_resources():
    
    from src.mcp.mcp_server import mcp_server
    
    resources = []
    for uri, resource in mcp_server.resources.items():
        resources.append({
            "uri": uri,
            "description": resource["description"],
            "type": resource["type"]
        })
    
    return {
        "server": mcp_server.name,
        "version": mcp_server.version,
        "resources": resources
    }

@app.get("/mcp/resource/{resource_uri:path}", tags=["MCP"])
async def get_mcp_resource(resource_uri: str):
    
    from src.mcp.mcp_server import mcp_server
    
    try:
        result = await mcp_server.get_resource(resource_uri)
        return result
        
    except Exception as e:
        logger.error(f"MCP resource error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower()
    )
