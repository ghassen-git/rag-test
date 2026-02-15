# RAG System with MCP Integration

A production-ready RAG (Retrieval-Augmented Generation) system for book analysis with Model Context Protocol support.

## Features

- PDF processing with OCR (Mathpix)
- Vector search (Milvus)
- Multi-database support (PostgreSQL, MongoDB)
- Real-time CDC with Kafka & Debezium
- MCP server for database operations
- Multi-agent orchestration with LangGraph

## Quick Start

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Wait for services to be ready
sleep 15

# Index a book via API (recommended)
curl -X POST http://localhost:8000/index_book \
  -F "file=@data/sample_books/your-book.pdf" \
  -F "title=Your Book Title" \
  -F "author=Author Name" \
  -F "genre=Fiction"

# Query the system
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the highest rated books?"}'
```

## API Endpoints

### Book Indexing
- `POST /index_book` - Upload and index a book (PDF or TXT) - creates book record, extracts text, generates embeddings, and indexes in vector DB

### Querying
- `POST /query` - Ask questions about books with multi-agent processing
- `GET /books/{book_id}` - Get book details and review statistics
- `GET /view_chunks/{book_id}` - View indexed chunks for a book

### Additional Upload Options
- `POST /upload_text` - Index plain text content for existing book
- `POST /upload_image` - OCR and index image content

### System
- `GET /health` - Health check for all components
- `GET /stats` - System statistics

### MCP Integration
- `GET /mcp/tools` - List available MCP tools
- `POST /mcp/call` - Execute MCP tools
- `GET /mcp/resources` - List MCP resources

## Project Structure

```
src/
├── api/          # FastAPI endpoints
├── agents/       # LangGraph agents
├── mcp/          # MCP server
├── ocr/          # PDF processing & OCR
├── embedding/    # Text chunking & embeddings
├── vector_db/    # Milvus client
└── cdc/          # Kafka & Debezium

data/
├── sample_books/ # Sample PDFs for testing
├── mongo_init.js # MongoDB initialization
└── postgres_init.sql # PostgreSQL schema
```

## MCP Integration

The system exposes 6 database tools via MCP:

1. `read_book_metadata` - Query book info
2. `search_books` - Search with filters
3. `read_reviews` - Get reviews
4. `update_rating` - Update ratings
5. `add_review` - Add reviews
6. `aggregate_reviews` - Get statistics

### Using MCP Tools

```bash
# List tools
curl http://localhost:8000/mcp/tools

# Search books
curl -X POST http://localhost:8000/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "search_books", "parameters": {"min_rating": 4.5}}'

# Update via natural language
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Update the rating of book 1 to 4.5"}'
```

## Indexing Books

The primary way to index books is via the `/index_book` API endpoint:

```bash
# Index a PDF book
curl -X POST http://localhost:8000/index_book \
  -F "file=@path/to/book.pdf" \
  -F "title=The Great Gatsby" \
  -F "author=F. Scott Fitzgerald" \
  -F "genre=Fiction" \
  -F "isbn=9780743273565" \
  -F "description=A classic American novel"

# Index a text file
curl -X POST http://localhost:8000/index_book \
  -F "file=@path/to/book.txt" \
  -F "title=My Book" \
  -F "author=Author Name" \
  -F "genre=Non-Fiction"
```

This endpoint handles everything automatically:
1. Creates book record in PostgreSQL
2. Extracts text (OCR for PDFs, direct read for TXT)
3. Cleans and chunks the text
4. Generates embeddings
5. Indexes in Milvus vector database

## Environment Variables

Required:
- `OPENAI_API_KEY` - OpenAI API key
- `MATHPIX_APP_ID` - Mathpix app ID
- `MATHPIX_APP_KEY` - Mathpix app key

Optional (have defaults):
- Database credentials
- Kafka settings
- Model configurations

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# View logs
docker-compose logs -f api

# Reset data
./cleanup_and_reset.sh
```

## Tech Stack

- **API**: FastAPI
- **Agents**: LangGraph, LangChain
- **LLM**: OpenAI GPT-4
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Milvus
- **Databases**: PostgreSQL, MongoDB
- **Streaming**: Kafka, Debezium
- **OCR**: Mathpix
- **Containers**: Docker

## License

MIT
