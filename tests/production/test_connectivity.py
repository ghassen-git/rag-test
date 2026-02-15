"""
Test: Service Connectivity
Verifies all services can communicate
"""
import pytest
import psycopg2
from pymongo import MongoClient
from pymilvus import connections
import requests
import os


class TestServiceConnectivity:
    
    def test_postgres_connectivity(self):
        """Test PostgreSQL is reachable"""
        try:
            # Use localhost for tests running outside Docker
            host = os.getenv('POSTGRES_HOST', 'localhost')
            if host in ['postgres', 'rag-postgres']:
                host = 'localhost'
            
            conn = psycopg2.connect(
                host=host,
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'books_db'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres123'),
                connect_timeout=5
            )
            conn.close()
            print("✅ PostgreSQL reachable")
        except Exception as e:
            pytest.fail(f"Cannot connect to PostgreSQL: {e}")
    
    def test_mongodb_connectivity(self):
        """Test MongoDB is reachable"""
        try:
            # Use localhost for tests running outside Docker
            mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
            if 'mongo:27017' in mongo_uri:
                mongo_uri = 'mongodb://localhost:27017/'
            
            client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000
            )
            client.server_info()
            print("✅ MongoDB reachable")
        except Exception as e:
            pytest.fail(f"Cannot connect to MongoDB: {e}")
    
    def test_milvus_connectivity(self):
        """Test Milvus is reachable"""
        try:
            # Use localhost for tests running outside Docker
            host = os.getenv('MILVUS_HOST', 'localhost')
            if host in ['milvus-standalone', 'milvus', 'rag-milvus']:
                host = 'localhost'
            
            connections.connect(
                alias="test_conn",
                host=host,
                port=int(os.getenv('MILVUS_PORT', 19530)),
                timeout=5
            )
            connections.disconnect("test_conn")
            print("✅ Milvus reachable")
        except Exception as e:
            pytest.fail(f"Cannot connect to Milvus: {e}")
    
    def test_kafka_connectivity(self):
        """Test Kafka/Debezium is reachable"""
        try:
            response = requests.get('http://localhost:8083/connectors', timeout=5)
            assert response.status_code == 200
            print("✅ Kafka/Debezium reachable")
        except Exception as e:
            pytest.fail(f"Cannot connect to Kafka: {e}")
    
    def test_api_connectivity(self):
        """Test FastAPI application is reachable"""
        try:
            response = requests.get(
                os.getenv('API_BASE_URL', 'http://localhost:8000') + '/health',
                timeout=5
            )
            # 200 or 404 is OK (endpoint might not exist), but should be reachable
            assert response.status_code in [200, 404]
            print("✅ FastAPI application reachable")
        except Exception as e:
            pytest.fail(f"Cannot connect to FastAPI: {e}")
    
    def test_all_services_health(self):
        """Verify all services respond to health checks"""
        # Use localhost for tests running outside Docker
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        if postgres_host in ['postgres', 'rag-postgres']:
            postgres_host = 'localhost'
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        if 'mongo:27017' in mongo_uri:
            mongo_uri = 'mongodb://localhost:27017/'
        
        milvus_host = os.getenv('MILVUS_HOST', 'localhost')
        if milvus_host in ['milvus-standalone', 'milvus', 'rag-milvus']:
            milvus_host = 'localhost'
        
        services = {
            'PostgreSQL': lambda: psycopg2.connect(
                host=postgres_host,
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'books_db'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres123')
            ).close(),
            'MongoDB': lambda: MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=2000
            ).server_info(),
            'Milvus': lambda: connections.connect(
                host=milvus_host,
                port=int(os.getenv('MILVUS_PORT', 19530))
            ) and connections.disconnect("default"),
        }
        
        healthy = []
        unhealthy = []
        
        for name, check in services.items():
            try:
                check()
                healthy.append(name)
            except Exception as e:
                unhealthy.append(f"{name}: {str(e)[:50]}")
        
        print(f"\n✅ Healthy services: {', '.join(healthy)}")
        if unhealthy:
            print(f"⚠️  Unhealthy services: {', '.join(unhealthy)}")
        
        assert len(unhealthy) == 0, f"Some services are unhealthy: {unhealthy}"
