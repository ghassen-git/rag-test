
from typing import Dict, Any, List

import json
import logging

from src.agents.analyst_agent import analyst_agent
logger = logging.getLogger(__name__)

class MCPServer:

    def __init__(self):
        
        self.name = "BookDatabaseMCP"
        self.version = "1.0.0"
        self.tools = self._register_tools()
        self.resources = self._register_resources()
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        
        return {
            "read_book_metadata": {
                "description": "Query PostgreSQL for book metadata by ID",
                "parameters": {
                    "book_id": {"type": "string", "required": True}
                },
                "handler": self._read_book_metadata
            },
            "search_books": {
                "description": "Search books with filters (title, author, genre, rating)",
                "parameters": {
                    "title": {"type": "string", "required": False},
                    "author": {"type": "string", "required": False},
                    "genre": {"type": "string", "required": False},
                    "min_rating": {"type": "number", "required": False}
                },
                "handler": self._search_books
            },
            "read_reviews": {
                "description": "Query MongoDB for book reviews",
                "parameters": {
                    "book_id": {"type": "string", "required": True}
                },
                "handler": self._read_reviews
            },
            "update_rating": {
                "description": "Update book rating in PostgreSQL",
                "parameters": {
                    "book_id": {"type": "string", "required": True},
                    "new_rating": {"type": "number", "required": True}
                },
                "handler": self._update_rating
            },
            "add_review": {
                "description": "Insert new review in MongoDB",
                "parameters": {
                    "book_id": {"type": "string", "required": True},
                    "user_id": {"type": "string", "required": True},
                    "username": {"type": "string", "required": True},
                    "rating": {"type": "number", "required": True},
                    "review_text": {"type": "string", "required": True}
                },
                "handler": self._add_review
            },
            "aggregate_reviews": {
                "description": "Perform analytics on review data",
                "parameters": {
                    "book_id": {"type": "string", "required": True}
                },
                "handler": self._aggregate_reviews
            }
        }
    
    def _register_resources(self) -> Dict[str, Dict[str, Any]]:
        
        return {
            "postgres://books": {
                "description": "PostgreSQL books table",
                "type": "database",
                "handler": self._get_books_resource
            },
            "mongo://reviews": {
                "description": "MongoDB reviews collection",
                "type": "database",
                "handler": self._get_reviews_resource
            }
        }
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        tool = self.tools[tool_name]
        handler = tool["handler"]
        
        try:
            result = await handler(**parameters)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Tool '{tool_name}' error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_resource(self, resource_uri: str) -> Dict[str, Any]:
        
        if resource_uri not in self.resources:
            return {"error": f"Resource '{resource_uri}' not found"}
        
        resource = self.resources[resource_uri]
        handler = resource["handler"]
        
        try:
            result = await handler()
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Resource '{resource_uri}' error: {e}")
            return {"success": False, "error": str(e)}
    
    # Tool handlers
    async def _read_book_metadata(self, book_id: str) -> Dict[str, Any]:
        
        book = analyst_agent.get_book_by_id(book_id)
        return book if book else {}
    
    async def _search_books(
        self,
        title: str = None,
        author: str = None,
        genre: str = None,
        min_rating: float = None
    ) -> List[Dict[str, Any]]:
        
        return analyst_agent.search_books(title, author, genre, min_rating)
    
    async def _read_reviews(self, book_id: str) -> List[Dict[str, Any]]:
        
        return analyst_agent.get_reviews_for_book(book_id)
    
    async def _update_rating(self, book_id: str, new_rating: float) -> Dict[str, Any]:
        
        success = analyst_agent.update_book_rating(book_id, new_rating)
        return {"success": success, "book_id": book_id, "new_rating": new_rating}
    
    async def _add_review(
        self,
        book_id: str,
        user_id: str,
        username: str,
        rating: int,
        review_text: str
    ) -> Dict[str, Any]:
        
        from datetime import datetime
        
        review_data = {
            "book_id": book_id,
            "user_id": user_id,
            "username": username,
            "rating": rating,
            "review_text": review_text,
            "helpful_count": 0,
            "created_at": datetime.now()
        }
        
        success = analyst_agent.add_review(review_data)
        return {"success": success, "review": review_data}
    
    async def _aggregate_reviews(self, book_id: str) -> Dict[str, Any]:
        
        return analyst_agent.get_review_statistics(book_id)
    
    # Resource handlers
    async def _get_books_resource(self) -> List[Dict[str, Any]]:
        
        return analyst_agent.search_books()
    
    async def _get_reviews_resource(self) -> List[Dict[str, Any]]:
        
        return []
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        
        definitions = []
        for name, tool in self.tools.items():
            definitions.append({
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            })
        return definitions

# Global MCP server instance
mcp_server = MCPServer()
