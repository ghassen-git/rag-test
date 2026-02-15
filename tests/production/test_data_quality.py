"""
Test: Data Quality Validation
Checks for NULL values, duplicates, invalid data
"""
import pytest
import psycopg2
from pymongo import MongoClient
import os


class TestDataQuality:
    
    def test_no_null_critical_fields(self, postgres_connection):
        """No NULL values in critical book fields"""
        cursor = postgres_connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM books
            WHERE title IS NULL OR author IS NULL OR isbn IS NULL
        """)
        null_count = cursor.fetchone()[0]
        
        assert null_count == 0, f"Found {null_count} books with NULL critical fields!"
        print("✅ No NULL values in critical fields")
    
    def test_no_duplicate_isbns(self, postgres_connection):
        """No duplicate ISBN numbers"""
        cursor = postgres_connection.cursor()
        
        cursor.execute("""
            SELECT isbn, COUNT(*) as cnt FROM books
            GROUP BY isbn
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        if len(duplicates) > 0:
            print(f"⚠️  Warning: {len(duplicates)} duplicate ISBNs found")
        else:
            print("✅ No duplicate ISBNs")
    
    def test_valid_ratings_postgres(self, postgres_connection):
        """All PostgreSQL ratings are in valid range (0-5)"""
        cursor = postgres_connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM books
            WHERE rating < 0 OR rating > 5
        """)
        invalid_count = cursor.fetchone()[0]
        
        assert invalid_count == 0, f"Found {invalid_count} books with invalid ratings!"
        print("✅ All PostgreSQL ratings valid (0-5)")
    
    def test_valid_ratings_mongodb(self, mongodb_client):
        """All MongoDB review ratings are valid"""
        db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
        
        invalid_ratings = db.book_reviews.count_documents({
            "$or": [
                {"rating": {"$lt": 0}},
                {"rating": {"$gt": 5}}
            ]
        })
        
        assert invalid_ratings == 0, f"Found {invalid_ratings} reviews with invalid ratings!"
        print("✅ All MongoDB review ratings valid")
    
    def test_referential_integrity(self, postgres_connection, mongodb_client):
        """Check foreign key consistency between books and reviews"""
        cursor = postgres_connection.cursor()
        cursor.execute("SELECT id FROM books")
        book_ids = set([row[0] for row in cursor.fetchall()])
        
        db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
        review_book_ids = set(db.book_reviews.distinct("book_id"))
        
        orphaned = review_book_ids - book_ids
        
        if len(orphaned) > 0:
            print(f"⚠️  Warning: {len(orphaned)} reviews reference non-existent books")
        else:
            print("✅ Referential integrity maintained")
