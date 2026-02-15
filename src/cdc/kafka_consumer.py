
from typing import Dict, Any, List, Callable

from kafka import KafkaConsumer
import asyncio
import json
import logging
import time

from kafka.errors import KafkaError

from src.config import settings
from src.embedding.chunker import text_chunker
from src.embedding.openai_embedder import openai_embedder
from src.vector_db.milvus_client import milvus_client
logger = logging.getLogger(__name__)

class CDCConsumer:

    def __init__(self):
        
        self.consumer = None
        self.running = False
        self.batch_size = 50
        self.batch_timeout = 0.5  # seconds
        self.event_buffer: List[Dict[str, Any]] = []
        self.last_flush_time = time.time()
    
    def connect(self) -> None:
        
        max_retries = 10
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    settings.kafka_topic_books,
                    settings.kafka_topic_reviews,
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    group_id=settings.kafka_consumer_group,
                    auto_offset_reset=settings.kafka_auto_offset_reset,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    max_poll_records=100,
                    fetch_min_bytes=1024,
                    fetch_max_wait_ms=500
                )
                logger.info(f"Connected to Kafka: {settings.kafka_bootstrap_servers}")
                return
            except KafkaError as e:
                logger.warning(f"Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
    
    async def start_consuming(self) -> None:
        
        if not self.consumer:
            self.connect()
        
        self.running = True
        logger.info("Starting CDC event consumption")
        
        try:
            while self.running:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=100, max_records=100)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        await self._process_event(record.topic, record.value)
                
                # Check if we should flush buffer
                current_time = time.time()
                should_flush = (
                    len(self.event_buffer) >= self.batch_size or
                    (self.event_buffer and
                     current_time - self.last_flush_time >= self.batch_timeout)
                )
                if should_flush:
                    await self._flush_buffer()
                
                # Small sleep to prevent tight loop
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in CDC consumer: {e}")
            raise
        finally:
            self.stop()
    
    async def _process_event(self, topic: str, event: Dict[str, Any]) -> None:
        
        try:
            # Determine source
            if "books.public.books" in topic:
                source = "postgres"
                await self._process_book_event(event, source)
            elif "reviews.books_reviews.reviews" in topic:
                source = "mongo"
                await self._process_review_event(event, source)
            else:
                logger.warning(f"Unknown topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error processing event from {topic}: {e}")
    
    async def _process_book_event(self, event: Dict[str, Any], source: str) -> None:

        logger.debug(f"Skipping book metadata indexing for book: {event.get('id')}")
    
    async def _process_review_event(self, event: Dict[str, Any], source: str) -> None:
        
        # Extract review data
        book_id = str(event.get("book_id", ""))
        review_text = event.get("review_text", "")
        rating = event.get("rating", 0)
        
        if not review_text:
            return
        
        # Create text for embedding
        text = f"Review (Rating: {rating}/5): {review_text}"
        
        # Add to buffer
        self.event_buffer.append({
            "book_id": book_id,
            "title": event.get("book_title", ""),
            "author": event.get("author", ""),
            "text": text,
            "source": source,
            "chapter": 0,
            "page_number": 0,
            "timestamp": int(time.time())
        })
        
        logger.debug(f"Buffered review event for book: {book_id}")
    
    async def _flush_buffer(self) -> None:
        
        if not self.event_buffer:
            return
        
        try:
            logger.info(f"Flushing {len(self.event_buffer)} events to Milvus")
            
            # Chunk texts
            all_chunks = []
            for event in self.event_buffer:
                chunks = text_chunker.chunk_text(
                    event["text"],
                    metadata={
                        "book_id": event["book_id"],
                        "title": event["title"],
                        "author": event["author"],
                        "source": event["source"],
                        "chapter": event["chapter"],
                        "page_number": event["page_number"],
                        "timestamp": event["timestamp"]
                    }
                )
                all_chunks.extend(chunks)
            
            if not all_chunks:
                self.event_buffer.clear()
                self.last_flush_time = time.time()
                return
            
            # Generate embeddings
            documents = await openai_embedder.embed_documents(all_chunks, text_field="content")
            
            # Prepare for Milvus
            milvus_data = []
            for doc in documents:
                milvus_data.append({
                    "id": f"{doc['book_id']}_{doc['chunk_index']}_{doc['timestamp']}",
                    "vector": doc["vector"],
                    "book_id": doc["book_id"],
                    "title": doc["title"],
                    "author": doc["author"],
                    "content": doc["content"],
                    "source": doc["source"],
                    "chapter": doc["chapter"],
                    "page_number": doc["page_number"],
                    "timestamp": doc["timestamp"]
                })
            
            # Upsert to Milvus
            milvus_client.upsert(milvus_data)
            
            logger.info(f"Successfully flushed {len(milvus_data)} chunks to Milvus")
            
        except Exception as e:
            logger.error(f"Error flushing buffer: {e}")
        finally:
            self.event_buffer.clear()
            self.last_flush_time = time.time()
    
    def stop(self) -> None:
        
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")

# Global consumer instance
cdc_consumer = CDCConsumer()
