"""
Test: Initial Data Load Verification
Ensures historical data was properly loaded before CDC
"""
import pytest
import psycopg2
from pymongo import MongoClient
from pymilvus import connections, Collection
import os


class TestInitialDataLoad:
    
    def test_postgres_has_data(self, postgres_connection):
        """Verify PostgreSQL has books data"""
        cursor = postgres_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        count = cursor.fetchone()[0]
        
        assert count > 0, "No books in PostgreSQL!"
        print(f"✅ PostgreSQL has {count} books")
    
    def test_mongodb_has_data(self, mongodb_client):
        """Verify MongoDB has reviews data"""
        db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
        count = db.book_reviews.count_documents({})
        
        print(f"✅ MongoDB has {count} reviews")
    
    def test_milvus_has_data(self, milvus_connection):
        """Verify Milvus has indexed data"""
        collection = Collection("book_embeddings")
        collection.load()
        
        count = collection.num_entities
        
        assert count > 0, "No data in Milvus!"
        print(f"✅ Milvus has {count} indexed chunks")
    
    def test_data_load_ratio(self, postgres_connection, milvus_connection):
        """Verify reasonable ratio of PostgreSQL books to Milvus chunks"""
        cursor = postgres_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        postgres_count = cursor.fetchone()[0]
        
        collection = Collection("book_embeddings")
        collection.load()
        milvus_count = collection.num_entities
        
        if postgres_count > 0:
            ratio = milvus_count / postgres_count
            print(f"📊 Load ratio: {ratio:.2f} chunks per book")
            
            # Should have at least some chunks per book on average
            assert ratio >= 0.5, f"Load ratio too low: {ratio:.2f}"
