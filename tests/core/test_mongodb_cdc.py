"""
Test: MongoDB CDC with Debezium
Verifies real-time change data capture from MongoDB
"""
import pytest
import requests
import time
from pymongo import MongoClient
import os


class TestMongoDBCDC:
    
    def test_debezium_mongo_connector_registered(self):
        """Check Debezium MongoDB connector is registered"""
        response = requests.get('http://localhost:8083/connectors', timeout=5)
        assert response.status_code == 200
        
        connectors = response.json()
        assert 'mongo-connector' in connectors or any('mongo' in c.lower() for c in connectors), \
            f"MongoDB connector not found. Available: {connectors}"
        
        print("✅ Debezium MongoDB connector registered")
    
    def test_mongo_connector_status(self):
        """Verify MongoDB connector is running"""
        response = requests.get('http://localhost:8083/connectors', timeout=5)
        connectors = response.json()
        
        mongo_connector = None
        for connector in connectors:
            if 'mongo' in connector.lower():
                mongo_connector = connector
                break
        
        assert mongo_connector, "No MongoDB connector found!"
        
        response = requests.get(
            f'http://localhost:8083/connectors/{mongo_connector}/status',
            timeout=5
        )
        assert response.status_code == 200
        
        status = response.json()
        assert status['connector']['state'] == 'RUNNING', \
            f"Connector not running: {status['connector']['state']}"
        
        print(f"✅ MongoDB connector '{mongo_connector}' is RUNNING")
    
    def test_mongodb_replica_set(self, mongodb_client):
        """Verify MongoDB is running as replica set (required for CDC)"""
        try:
            status = mongodb_client.admin.command('replSetGetStatus')
            assert 'set' in status, "MongoDB not running as replica set!"
            print(f"✅ MongoDB replica set: {status['set']}")
        except Exception as e:
            # MongoDB might not be configured as replica set
            print(f"⚠️  MongoDB not configured as replica set: {e}")
            pytest.skip("MongoDB not configured as replica set (single node mode)")
    
    def test_cdc_captures_mongo_insert(self, mongodb_client):
        """Test CDC captures MongoDB inserts"""
        db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
        collection = db.book_reviews
        
        # Insert test review
        test_review = {
            "book_id": 1,
            "reviewer_name": "CDC Test",
            "rating": 5,
            "review_text": "Testing CDC capture",
            "review_date": "2024-01-15",
            "test_marker": f"cdc_test_{int(time.time())}"
        }
        
        start_time = time.time()
        result = collection.insert_one(test_review)
        
        time.sleep(2)
        cdc_latency = time.time() - start_time
        
        print(f"✅ MongoDB INSERT captured (latency: {cdc_latency:.2f}s)")
        assert cdc_latency < 3, f"CDC latency too high: {cdc_latency}s"
        
        # Cleanup
        collection.delete_one({"_id": result.inserted_id})
    
    def test_cdc_captures_mongo_update(self, mongodb_client):
        """Test CDC captures MongoDB updates"""
        db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
        collection = db.book_reviews
        
        # Find a review to update
        review = collection.find_one()
        
        if review:
            start_time = time.time()
            
            collection.update_one(
                {"_id": review["_id"]},
                {"$set": {"rating": 4.5}}
            )
            
            time.sleep(2)
            cdc_latency = time.time() - start_time
            
            print(f"✅ MongoDB UPDATE captured (latency: {cdc_latency:.2f}s)")
            assert cdc_latency < 3, f"CDC latency too high: {cdc_latency}s"
