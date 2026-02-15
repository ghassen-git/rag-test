
from typing import List, Dict, Any, Optional

from pymilvus import connections, Collection, utility
import logging
import time

from pymilvus.client.types import LoadState

from src.config import settings
from src.vector_db.schema import (
    create_book_embeddings_schema,
    get_index_params,
    get_search_params
)

logger = logging.getLogger(__name__)

class MilvusClient:

    def __init__(self):
        
        self.collection_name = settings.milvus_collection
        self.collection: Optional[Collection] = None
        self._connected = False
    
    def connect(self) -> None:
        
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                connections.connect(
                    alias="default",
                    host=settings.milvus_host,
                    port=settings.milvus_port,
                    timeout=10
                )
                self._connected = True
                logger.info(f"Connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
                self._initialize_collection()
                return
            except Exception as e:
                logger.warning(f"Milvus connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
    
    def _initialize_collection(self) -> None:
        
        try:
            if utility.has_collection(self.collection_name):
                logger.info(f"Loading existing collection: {self.collection_name}")
                self.collection = Collection(self.collection_name)
                self.collection.load()
            else:
                logger.info(f"Creating new collection: {self.collection_name}")
                schema = create_book_embeddings_schema()
                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                    using='default'
                )
                
                # Create HNSW index
                index_params = get_index_params()
                self.collection.create_index(
                    field_name="vector",
                    index_params=index_params
                )
                logger.info("Created HNSW index on vector field")
                
                # Load collection into memory
                self.collection.load()
                logger.info("Collection loaded into memory")
                
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def insert(self, data: List[Dict[str, Any]]) -> List[str]:
        
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            # Transform data into column format
            entities = self._transform_to_entities(data)
            
            # Insert data
            insert_result = self.collection.insert(entities)
            self.collection.flush()
            
            logger.info(f"Inserted {len(data)} embeddings into Milvus")
            return insert_result.primary_keys
            
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise
    
    def upsert(self, data: List[Dict[str, Any]]) -> None:
        
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            entities = self._transform_to_entities(data)
            self.collection.upsert(entities)
            self.collection.flush()
            logger.info(f"Upserted {len(data)} embeddings")
        except Exception as e:
            logger.error(f"Failed to upsert data: {e}")
            raise
    
    def search(
        self,
        query_vectors: List[List[float]],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
        output_fields: Optional[List[str]] = None
    ) -> List[List[Dict[str, Any]]]:
        
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        if output_fields is None:
            output_fields = ["id", "book_id", "title", "author", "content", "source", "chapter", "page_number"]
        
        try:
            search_params = get_search_params()
            
            results = self.collection.search(
                data=query_vectors,
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=output_fields
            )
            
            # Transform results to list of dicts
            formatted_results = []
            for hits in results:
                hit_list = []
                for hit in hits:
                    hit_dict = {
                        "id": hit.id,
                        "distance": hit.distance,
                        "score": hit.distance,  # IP metric, higher is better
                    }
                    # Add output fields
                    for field in output_fields:
                        hit_dict[field] = hit.entity.get(field)
                    hit_list.append(hit_dict)
                formatted_results.append(hit_list)
            
            logger.info(f"Search completed: {len(query_vectors)} queries, top_k={top_k}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete(self, expr: str) -> None:
        
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            self.collection.delete(expr)
            self.collection.flush()
            logger.info(f"Deleted entities matching: {expr}")
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            stats = self.collection.num_entities
            try:
                is_loaded = utility.load_state(self.collection_name) == LoadState.Loaded
            except:
                is_loaded = False
            
            return {
                "collection_name": self.collection_name,
                "num_entities": stats,
                "loaded": is_loaded
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
    
    def _transform_to_entities(
        self,
        data: List[Dict[str, Any]]
    ) -> List[List[Any]]:
        
        if not data:
            return []
        
        # Get all field names from schema
        fields = ["id", "vector", "book_id", "title", "author", "content", 
                  "source", "chapter", "page_number", "timestamp"]
        
        # Create column-oriented data
        entities = []
        for field in fields:
            column = [item.get(field) for item in data]
            entities.append(column)
        
        return entities
    
    def disconnect(self) -> None:
        
        if self._connected:
            connections.disconnect("default")
            self._connected = False
            logger.info("Disconnected from Milvus")

# Global client instance
milvus_client = MilvusClient()
