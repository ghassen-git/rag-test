# System Architecture - Real-Time Agentic RAG

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│                    (HTTP/REST API Consumers)                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION (Port 8000)                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATOR AGENT                             │  │
│  │                      (LangGraph StateGraph)                       │  │
│  │                                                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │  │
│  │  │  Intent         │  │  Route by       │  │  Synthesize     │ │  │
│  │  │  Analysis       │→ │  Intent         │→ │  Answer         │ │  │
│  │  └─────────────────┘  └────────┬────────┘  └─────────────────┘ │  │
│  │                                 │                                │  │
│  │                    ┌────────────┼────────────┐                  │  │
│  │                    ▼            ▼            ▼                   │  │
│  │         ┌──────────────┐ ┌──────────┐ ┌──────────────┐         │  │
│  │         │ Search Agent │ │ Analyst  │ │   Execute    │         │  │
│  │         │   (Milvus)   │ │  Agent   │ │   Action     │         │  │
│  │         └──────────────┘ └──────────┘ └──────────────┘         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    MCP SERVER (Tool Exposure)                     │  │
│  │  Tools: query_postgres, query_mongo, update_book, add_review     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MILVUS         │  │  POSTGRESQL     │  │  MONGODB        │
│  Vector DB      │  │  (Books)        │  │  (Reviews)      │
│  Port: 19530    │  │  Port: 5432     │  │  Port: 27017    │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │                    └────────┬───────────┘
         │                             │
         │                             ▼
         │                    ┌─────────────────┐
         │                    │   DEBEZIUM      │
         │                    │   CDC Layer     │
         │                    │   Port: 8083    │
         │                    └────────┬────────┘
         │                             │
         │                             ▼
         │                    ┌─────────────────┐
         │                    │     KAFKA       │
         │                    │  Message Broker │
         │                    │   Port: 9092    │
         │                    └────────┬────────┘
         │                             │
         │                             ▼
         │                    ┌─────────────────┐
         │                    │ KAFKA CONSUMER  │
         │                    │  + Embedder     │
         │                    └────────┬────────┘
         │                             │
         │    ┌────────────────────────┘
         │    │
         │    ▼
         │  ┌─────────────────┐
         │  │  Text Chunker   │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ OpenAI Embedder │
         │  │ (with Redis     │
         │  │  caching)       │
         │  └────────┬────────┘
         │           │
         └───────────┘
                 
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     REDIS       │  │     MINIO       │  │   ZOOKEEPER     │
│  Cache Layer    │  │  Blob Storage   │  │  Coordination   │
│  Port: 6379     │  │  Port: 9000     │  │  Port: 2181     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Data Flow Diagrams

### 1. Real-Time CDC Pipeline (Write Path)

```
┌──────────────┐
│   User       │
│   Action     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│  PostgreSQL / MongoDB                │
│  INSERT/UPDATE/DELETE                │
└──────┬───────────────────────────────┘
       │ (Write-Ahead Log / OpLog)
       ▼
┌──────────────────────────────────────┐
│  Debezium Connector                  │
│  - Captures change events            │
│  - Converts to JSON                  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Kafka Topic                         │
│  - dbserver1.public.books            │
│  - dbserver1.public.reviews          │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Kafka Consumer (in FastAPI app)    │
│  - Consumes change events            │
│  - Filters relevant operations       │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Text Chunker                        │
│  - Splits text into 500-char chunks  │
│  - 50-char overlap for context       │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  OpenAI Embedder                     │
│  - Generates 1536-dim vectors        │
│  - Uses text-embedding-3-small       │
│  - Redis caching for efficiency      │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Milvus Vector Database              │
│  - Upserts vectors with metadata     │
│  - IVF_FLAT index for fast search    │
└──────────────────────────────────────┘

⏱️  Total Latency: 2-5 seconds
```

### 2. RAG Query Pipeline (Read Path)

```
┌──────────────┐
│   User       │
│   Query      │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Orchestrator Agent                  │
│  Step 1: Analyze Intent              │
│  - "search" → semantic search        │
│  - "data" → structured query         │
│  - "action" → database update        │
│  - "hybrid" → combined approach      │
└──────┬───────────────────────────────┘
       │
       ├─────────────────┬─────────────────┐
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Search      │  │ Analyst     │  │ Execute     │
│ Agent       │  │ Agent       │  │ Action      │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Milvus      │  │ PostgreSQL  │  │ MCP Tools   │
│ Vector      │  │ + MongoDB   │  │ (Updates)   │
│ Search      │  │ Queries     │  │             │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Context Builder │
              │ - Combines all  │
              │   sources       │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ LLM Synthesis   │
              │ (OpenAI GPT-4)  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Final Answer    │
              │ with Citations  │
              └─────────────────┘

⏱️  Query Latency: 1-3 seconds
```

### 3. OCR Pipeline (Unstructured Data)

```
┌──────────────┐
│   PDF/Image  │
│   Upload     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│  MinIO Blob Storage                  │
│  - Monitors /data/your_books/        │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  PDF Processor                       │
│  - Detects new files                 │
│  - Validates format                  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Mathpix OCR Client                  │
│  - Extracts text from images/PDFs    │
│  - Handles mathematical notation     │
│  - Preserves layout                  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Text Chunker                        │
│  - Same as CDC pipeline              │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Embedder → Milvus                   │
│  - Same vectorization pipeline       │
└──────────────────────────────────────┘

⏱️  Processing Time: 5-30 seconds per document
```

## Component Details

### 1. Multi-Agent System (LangGraph)

**Orchestrator Agent:**
- Framework: LangGraph StateGraph
- State: TypedDict with query, intent, results, context
- Nodes: analyze_intent, search_vectors, query_databases, execute_action, synthesize_answer
- Edges: Conditional routing based on intent

**Search Agent:**
- Specialization: Semantic search in Milvus
- Methods: search(), search_by_book(), search_by_source()
- Returns: Top-K relevant passages with scores

**Data Analyst Agent:**
- Specialization: Structured database queries
- Databases: PostgreSQL (books), MongoDB (reviews)
- Methods: query_postgres(), query_mongo(), update_book_rating(), add_review()

### 2. Model Context Protocol (MCP)

**Server Implementation:**
- Protocol: JSON-RPC style tool calling
- Endpoint: `/mcp/tools` (list), `/mcp/call` (invoke)

**Exposed Tools:**
1. `query_postgres` - Execute SQL queries
2. `query_mongo` - Execute MongoDB queries
3. `update_book` - Update book metadata
4. `add_review` - Add new review

**Tool Schema:**
```json
{
  "name": "query_postgres",
  "description": "Execute SQL query on PostgreSQL",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"}
    },
    "required": ["query"]
  }
}
```

### 3. Vector Database (Milvus)

**Collection Schema:**
```python
{
  "id": "INT64",           # Primary key
  "book_id": "INT64",      # Foreign key to books table
  "title": "VARCHAR",      # Book title
  "author": "VARCHAR",     # Book author
  "content": "VARCHAR",    # Text chunk
  "source": "VARCHAR",     # Source type (book/review)
  "chapter": "INT64",      # Chapter number
  "page_number": "INT64",  # Page number
  "vector": "FLOAT_VECTOR" # 1536-dim embedding
}
```

**Index Configuration:**
- Type: IVF_FLAT
- Metric: Inner Product (IP)
- nlist: 128
- nprobe: 10

### 4. CDC Configuration

**PostgreSQL:**
- WAL Level: logical
- Plugin: pgoutput
- Slot: debezium
- Publication: dbz_publication

**MongoDB:**
- Requires: Replica set (optional for testing)
- OpLog: Tailable cursor
- Connector: MongoDB Source Connector

**Debezium:**
- Connector Class: PostgreSQL/MongoDB
- Transforms: Unwrap, route
- Topic Prefix: dbserver1

### 5. Embedding Strategy

**Model:** OpenAI text-embedding-3-small
- Dimensions: 1536
- Cost: $0.02 / 1M tokens
- Quality: High semantic understanding

**Chunking Strategy:**
- Chunk Size: 500 characters
- Overlap: 50 characters (10%)
- Rationale: Balance between context and granularity

**Caching:**
- Layer: Redis
- TTL: 7 days
- Key: SHA256(text + model)
- Hit Rate: ~60-70% in production

## Scalability Considerations

### Horizontal Scaling
- **API Layer**: Multiple FastAPI instances behind load balancer
- **Kafka**: Partitioned topics for parallel processing
- **Milvus**: Distributed deployment with multiple nodes

### Performance Optimizations
- **Batch Embedding**: Process multiple texts in single API call
- **Connection Pooling**: Reuse database connections
- **Async I/O**: Non-blocking operations throughout
- **Caching**: Redis for embeddings, reduce API calls by 60%

### Consistency Model
- **Eventual Consistency**: Vector store may lag behind source DB by 2-5 seconds
- **Timestamp Tracking**: All records have created_at/updated_at
- **Idempotent Upserts**: Safe to replay CDC events

## Error Handling

### Retry Strategies
- **OpenAI API**: Exponential backoff (3 retries, 4-10s wait)
- **Database**: Connection retry (5 attempts, 2s interval)
- **Kafka**: Consumer auto-commit with offset management

### Graceful Degradation
- **Embedding Failure**: Fall back to keyword search
- **Database Unavailable**: Return cached results
- **MCP Tool Error**: Return error message to user

### Monitoring
- **Health Checks**: `/health` endpoint checks all services
- **Logging**: Structured JSON logs with correlation IDs
- **Metrics**: Request latency, error rates, throughput

## Security

### Authentication
- API Keys: Environment variables only
- No Hardcoded Credentials: All in .env file
- .gitignore: Excludes .env from version control

### Data Protection
- Database: Password-protected
- Network: Internal Docker network
- Secrets: Mounted as environment variables

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Framework | FastAPI | 0.115+ | REST API server |
| Agent Framework | LangGraph | 0.2+ | Multi-agent orchestration |
| LLM | OpenAI GPT-4 | Latest | Response generation |
| Embeddings | OpenAI text-embedding-3-small | Latest | Vector generation |
| Vector DB | Milvus | 2.3+ | Semantic search |
| Relational DB | PostgreSQL | 15+ | Structured data |
| Document DB | MongoDB | 7+ | Semi-structured data |
| CDC | Debezium | 2.5+ | Change data capture |
| Message Broker | Kafka | 3.6+ | Event streaming |
| Cache | Redis | 7+ | Embedding cache |
| Object Storage | MinIO | Latest | Blob storage |
| OCR | Mathpix | Latest | Text extraction |
| Orchestration | Docker Compose | 2.0+ | Container management |

## Design Decisions

### Why LangGraph?
- State-based orchestration fits multi-agent workflows
- Built specifically for LLM agents
- Production-ready with error handling
- Easy to visualize and debug

### Why OpenAI Embeddings?
- High quality semantic understanding
- Cost-effective ($0.02/1M tokens)
- 1536 dimensions balance quality and performance
- Widely adopted and well-documented

### Why Milvus?
- Purpose-built for vector search
- Excellent performance at scale
- Rich query capabilities (filtering, hybrid search)
- Active community and enterprise support

### Why Debezium?
- Industry standard for CDC
- Supports multiple databases
- Reliable and battle-tested
- Minimal impact on source databases

## Future Enhancements

1. **Multi-modal Support**: Image embeddings with CLIP
2. **Advanced RAG**: Hypothetical document embeddings, query expansion
3. **Fine-tuning**: Custom embedding model for domain-specific data
4. **Monitoring**: Prometheus + Grafana dashboards
5. **Authentication**: OAuth2 + JWT tokens
6. **Rate Limiting**: Per-user quotas
7. **A/B Testing**: Multiple retrieval strategies
8. **Feedback Loop**: User ratings to improve retrieval
