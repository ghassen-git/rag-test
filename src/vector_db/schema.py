
from typing import Dict, Any

from pymilvus import CollectionSchema, FieldSchema, DataType
def create_book_embeddings_schema() -> CollectionSchema:
    
    fields = [
        FieldSchema(
            name="id",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=False,
            max_length=256,
            description="Unique identifier: {book_id}_{chunk_index}"
        ),
        FieldSchema(
            name="vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=1536,
            description="OpenAI text-embedding-3-small vector"
        ),
        FieldSchema(
            name="book_id",
            dtype=DataType.VARCHAR,
            max_length=128,
            description="Book identifier"
        ),
        FieldSchema(
            name="title",
            dtype=DataType.VARCHAR,
            max_length=512,
            description="Book title"
        ),
        FieldSchema(
            name="author",
            dtype=DataType.VARCHAR,
            max_length=256,
            description="Book author"
        ),
        FieldSchema(
            name="content",
            dtype=DataType.VARCHAR,
            max_length=4096,
            description="Text chunk content"
        ),
        FieldSchema(
            name="source",
            dtype=DataType.VARCHAR,
            max_length=64,
            description="Data source: postgres/mongo/pdf"
        ),
        FieldSchema(
            name="chapter",
            dtype=DataType.INT32,
            description="Chapter number (0 if not applicable)"
        ),
        FieldSchema(
            name="page_number",
            dtype=DataType.INT32,
            description="Page number (0 if not applicable)"
        ),
        FieldSchema(
            name="timestamp",
            dtype=DataType.INT64,
            description="Unix timestamp of ingestion"
        ),
    ]
    
    schema = CollectionSchema(
        fields=fields,
        description="Book embeddings with metadata for RAG system",
        enable_dynamic_field=True
    )
    
    return schema

def get_index_params() -> Dict[str, Any]:
    
    return {
        "index_type": "HNSW",
        "metric_type": "IP",
        "params": {
            "M": 16,  # Number of connections per layer
            "efConstruction": 200  # Build quality
        }
    }

def get_search_params() -> Dict[str, Any]:
    
    return {
        "metric_type": "IP",
        "params": {
            "ef": 64
        }
    }
