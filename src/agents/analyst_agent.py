
from typing import Dict, Any, List, Optional

from pymongo import MongoClient
import logging
import psycopg2

from psycopg2.extras import RealDictCursor

from src.config import settings
logger = logging.getLogger(__name__)

class DataAnalystAgent:

    def __init__(self):
        
        self.name = "DataAnalystAgent"
        self.description = (
            "Queries PostgreSQL for book metadata and MongoDB for reviews, "
            "performs aggregations and analytics"
        )
        
        # PostgreSQL connection
        self.pg_conn = None
        self.pg_cursor = None
        
        # MongoDB connection
        self.mongo_client = None
        self.mongo_db = None
    
    def connect(self) -> None:
        
        try:
            # Connect to PostgreSQL
            self.pg_conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            self.pg_cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to PostgreSQL")
            
            # Connect to MongoDB
            self.mongo_client = MongoClient(settings.mongo_uri)
            self.mongo_db = self.mongo_client[settings.mongo_db]
            logger.info("Connected to MongoDB")
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def get_book_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        
        try:
            if not self.pg_cursor:
                self.connect()
            query = "SELECT * FROM books WHERE id = %s"
            self.pg_cursor.execute(query, (book_id,))
            result = self.pg_cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching book {book_id}: {e}")
            return None
    
    def query_postgres(self, query: str) -> List[Dict[str, Any]]:
        """Execute a raw PostgreSQL query and return results"""
        try:
            if not self.pg_cursor:
                self.connect()
            self.pg_cursor.execute(query)
            results = self.pg_cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error executing PostgreSQL query: {e}")
            return []
    
    def query_mongo(self, filter_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a MongoDB query and return results"""
        try:
            if not self.mongo_db:
                self.connect()
            reviews = list(self.mongo_db.reviews.find(filter_dict, {"_id": 0}))
            return reviews
        except Exception as e:
            logger.error(f"Error executing MongoDB query: {e}")
            return []
    
    def get_all_books(self, limit: int = 20) -> List[Dict[str, Any]]:
        
        try:
            query = "SELECT * FROM books ORDER BY rating DESC LIMIT %s"
            self.pg_cursor.execute(query, (limit,))
            results = self.pg_cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching all books: {e}")
            return []
    
    def search_books(
        self,
        title: str = None,
        author: str = None,
        genre: str = None,
        min_rating: float = None
    ) -> List[Dict[str, Any]]:
        
        try:
            conditions = []
            params = []
            
            if title:
                conditions.append("title ILIKE %s")
                params.append(f"%{title}%")
            if author:
                conditions.append("author ILIKE %s")
                params.append(f"%{author}%")
            if genre:
                conditions.append("genre = %s")
                params.append(genre)
            if min_rating is not None:
                conditions.append("rating >= %s")
                params.append(min_rating)
            
            query = "SELECT * FROM books"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY rating DESC"
            
            self.pg_cursor.execute(query, params)
            results = self.pg_cursor.fetchall()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def get_books_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        
        return self.search_books(genre=genre)
    
    def get_average_rating_by_genre(self, genre: str) -> float:
        
        try:
            query = "SELECT AVG(rating) as avg_rating FROM books WHERE genre = %s"
            self.pg_cursor.execute(query, (genre,))
            result = self.pg_cursor.fetchone()
            return float(result['avg_rating']) if result and result['avg_rating'] else 0.0
        except Exception as e:
            logger.error(f"Error calculating average rating: {e}")
            return 0.0
    
    def update_book_rating(self, book_id: str, new_rating: float) -> bool:
        
        try:
            query = "UPDATE books SET rating = %s WHERE id = %s"
            self.pg_cursor.execute(query, (new_rating, book_id))
            self.pg_conn.commit()
            logger.info(f"Updated rating for book {book_id} to {new_rating}")
            return True
        except Exception as e:
            logger.error(f"Error updating rating: {e}")
            self.pg_conn.rollback()
            return False
    
    def get_reviews_for_book(self, book_id: str) -> List[Dict[str, Any]]:
        
        try:
            # Ensure book_id is a string for MongoDB query
            book_id_str = str(book_id)
            
            reviews = list(self.mongo_db.reviews.find(
                {"book_id": book_id_str},
                {"_id": 0}
            ).sort("helpful_count", -1))
            return reviews
        except Exception as e:
            logger.error(f"Error fetching reviews: {e}")
            return []
    
    def get_review_statistics(self, book_id: str) -> Dict[str, Any]:
        
        try:
            # Ensure book_id is a string for MongoDB query
            book_id_str = str(book_id)
            
            pipeline = [
                {"$match": {"book_id": book_id_str}},
                {"$group": {
                    "_id": "$book_id",
                    "total_reviews": {"$sum": 1},
                    "average_rating": {"$avg": "$rating"},
                    "total_helpful": {"$sum": "$helpful_count"}
                }}
            ]
            
            result = list(self.mongo_db.reviews.aggregate(pipeline))
            if result:
                return {
                    "total_reviews": result[0]["total_reviews"],
                    "average_rating": round(result[0]["average_rating"], 2),
                    "total_helpful_votes": result[0]["total_helpful"]
                }
            return {"total_reviews": 0, "average_rating": 0.0, "total_helpful_votes": 0}
            
        except Exception as e:
            logger.error(f"Error calculating review statistics: {e}")
            return {"total_reviews": 0, "average_rating": 0.0, "total_helpful_votes": 0}
    
    def add_review(self, review_data: Dict[str, Any]) -> bool:
        
        try:
            self.mongo_db.reviews.insert_one(review_data)
            logger.info(f"Added review for book {review_data.get('book_id')}")
            return True
        except Exception as e:
            logger.error(f"Error adding review: {e}")
            return False
    
    def format_book_info(self, book: Dict[str, Any]) -> str:
        
        if not book:
            return "Book not found."
        
        info = f"**{book['title']}** by {book['author']}\n"
        info += f"- ISBN: {book.get('isbn', 'N/A')}\n"
        info += f"- Genre: {book.get('genre', 'N/A')}\n"
        info += f"- Rating: {book.get('rating', 0)}/5\n"
        info += f"- Published: {book.get('publication_date', 'N/A')}\n"
        if book.get('description'):
            info += f"\n{book['description']}\n"
        
        return info
    
    def disconnect(self) -> None:
        
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("Disconnected from databases")

# Global agent instance
analyst_agent = DataAnalystAgent()

# Alias for backward compatibility
AnalystAgent = DataAnalystAgent
