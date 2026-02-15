
from typing import Dict, Any, List

import logging

from src.embedding.openai_embedder import openai_embedder
from src.vector_db.milvus_client import milvus_client
logger = logging.getLogger(__name__)

class SearchAgent:

    def __init__(self):
        
        self.name = "SearchAgent"
        self.description = (
            "Performs semantic search in Milvus vector database "
            "to find relevant book passages and reviews"
        )
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_expr: str = None
    ) -> List[Dict[str, Any]]:
        
        try:
            logger.info(f"SearchAgent: Searching for '{query}' (top_k={top_k})")
            
            # Generate query embedding
            query_embedding = await openai_embedder.embed_text(query)
            
            # Search in Milvus
            results = milvus_client.search(
                query_vectors=[query_embedding],
                top_k=top_k,
                filter_expr=filter_expr,
                output_fields=["id", "book_id", "title", "author", "content", "source", "chapter", "page_number"]
            )
            
            # Format results
            formatted_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    score = hit.get("score", 0.0)
                    relevance = (
                        "high" if score > 0.8
                        else "medium" if score > 0.6
                        else "low"
                    )
                    formatted_results.append({
                        "book_id": hit.get("book_id"),
                        "title": hit.get("title"),
                        "author": hit.get("author"),
                        "content": hit.get("content"),
                        "source": hit.get("source"),
                        "chapter": hit.get("chapter"),
                        "page_number": hit.get("page_number"),
                        "score": score,
                        "relevance": relevance
                    })
            
            logger.info(f"SearchAgent: Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"SearchAgent error: {e}")
            return []
    
    async def search_by_book(
        self,
        query: str,
        book_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        
        filter_expr = f"book_id == '{book_id}'"
        return await self.search(query, top_k, filter_expr)
    
    async def search_by_source(
        self,
        query: str,
        source: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        
        filter_expr = f"source == '{source}'"
        return await self.search(query, top_k, filter_expr)
    
    def search_sync(
        self,
        query: str,
        top_k: int = 5,
        filter_expr: str = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for search method"""
        import asyncio
        
        # Create a new event loop for this synchronous call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self.search(query, top_k, filter_expr))
            return result
        finally:
            loop.close()
    
    def format_results_for_llm(
        self,
        results: List[Dict[str, Any]]
    ) -> str:
        
        if not results:
            return "No relevant passages found."
        
        formatted = "## Relevant Passages:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"\n### Result {i}\n"
            formatted += f"**Book:** {result['title']} by {result['author']}\n"
            formatted += f"**Source:** {result['source']}"
            if result['chapter'] > 0:
                formatted += f", Chapter {result['chapter']}"
            if result['page_number'] > 0:
                formatted += f", Page {result['page_number']}"
            formatted += f"\n\n{result['content']}\n\n"
            formatted += "---\n\n"
        
        return formatted

# Global agent instance
search_agent = SearchAgent()
