
from typing import Optional

from pydantic_settings import BaseSettings
class Settings(BaseSettings):

    # OpenAI Configuration
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-4-turbo"
    openai_max_retries: int = 3
    openai_timeout: int = 30
    
    # Mathpix Configuration
    mathpix_app_id: str
    mathpix_app_key: str
    mathpix_api_url: str = "https://api.mathpix.com/v3/text"
    
    # PostgreSQL Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "books_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres123"
    
    # MongoDB Configuration
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "books_reviews"
    mongo_user: Optional[str] = None
    mongo_password: Optional[str] = None
    
    # Milvus Configuration
    milvus_host: str = "milvus-standalone"
    milvus_port: int = 19530
    milvus_collection: str = "book_embeddings"
    milvus_index_type: str = "HNSW"
    milvus_metric_type: str = "IP"
    milvus_dimension: int = 1536
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_books: str = "books.public.books"
    kafka_topic_reviews: str = "reviews.books_reviews.reviews"
    kafka_topic_pdfs: str = "pdfs.processed"
    kafka_consumer_group: str = "rag-consumer-group"
    kafka_auto_offset_reset: str = "earliest"
    
    # Debezium Configuration
    debezium_connector_url: str = "http://debezium:8083"
    debezium_postgres_connector: str = "postgres-connector"
    debezium_mongo_connector: str = "mongo-connector"
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    chunk_size: int = 600
    chunk_overlap: int = 100
    top_k_results: int = 5
    
    # Rate Limiting
    embedding_rate_limit: int = 50
    embedding_rate_period: int = 1
    ocr_rate_limit: int = 10
    ocr_rate_period: int = 1
    
    # Redis Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl: int = 604800
    
    # Blob Storage (for temporary file uploads)
    blob_storage_path: str = "/data/pdfs"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
