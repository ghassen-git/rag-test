"""
Pytest configuration and shared fixtures for all tests
"""
import pytest
import os
import psycopg2
from pymongo import MongoClient
from pymilvus import connections
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test configuration
TEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds


@pytest.fixture(scope="session")
def postgres_connection():
    """Reusable PostgreSQL connection for all tests"""
    # Use localhost for tests running outside Docker
    host = os.getenv('POSTGRES_HOST', 'localhost')
    if host in ['postgres', 'rag-postgres']:
        host = 'localhost'
    
    conn = psycopg2.connect(
        host=host,
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'books_db'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres123')
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def mongodb_client():
    """Reusable MongoDB client for all tests"""
    # Use localhost for tests running outside Docker
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    if 'mongo:27017' in mongo_uri:
        mongo_uri = 'mongodb://localhost:27017/'
    
    client = MongoClient(mongo_uri)
    yield client
    client.close()


@pytest.fixture(scope="session")
def milvus_connection():
    """Reusable Milvus connection for all tests"""
    # Use localhost for tests running outside Docker
    host = os.getenv('MILVUS_HOST', 'localhost')
    if host in ['milvus-standalone', 'milvus', 'rag-milvus']:
        host = 'localhost'
    
    connections.connect(
        alias="default",
        host=host,
        port=int(os.getenv('MILVUS_PORT', 19530))
    )
    yield
    connections.disconnect("default")


@pytest.fixture
def api_base_url():
    """Base URL for API testing"""
    return os.getenv('API_BASE_URL', 'http://localhost:8000')


@pytest.fixture
def sample_book_data():
    """Sample book data for testing"""
    return {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "9999999999999",
        "description": "A test book about testing systems",
        "genre": "Technology",
        "publication_year": 2024
    }


@pytest.fixture
def sample_review_data():
    """Sample review data for testing"""
    return {
        "book_id": 1,
        "reviewer_name": "Test Reviewer",
        "rating": 5,
        "review_text": "This is a test review for testing purposes",
        "review_date": "2024-01-15"
    }


def wait_for_service(check_function, timeout=30, retry_delay=2):
    """
    Wait for a service to become available
    
    Args:
        check_function: Function that returns True when service is ready
        timeout: Maximum wait time in seconds
        retry_delay: Delay between retry attempts
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if check_function():
                return True
        except Exception:
            pass
        time.sleep(retry_delay)
    return False


@pytest.fixture(scope="session", autouse=True)
def wait_for_all_services():
    """Wait for all services to be ready before running tests"""
    
    def check_postgres():
        # Use localhost for tests running outside Docker
        host = os.getenv('POSTGRES_HOST', 'localhost')
        if host in ['postgres', 'rag-postgres']:
            host = 'localhost'
        
        conn = psycopg2.connect(
            host=host,
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'books_db'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres123')
        )
        conn.close()
        return True
    
    def check_mongodb():
        # Use localhost for tests running outside Docker
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        if 'mongo:27017' in mongo_uri:
            mongo_uri = 'mongodb://localhost:27017/'
        
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=2000
        )
        client.server_info()
        return True
    
    def check_milvus():
        # Use localhost for tests running outside Docker
        host = os.getenv('MILVUS_HOST', 'localhost')
        if host in ['milvus-standalone', 'milvus', 'rag-milvus']:
            host = 'localhost'
        
        connections.connect(
            host=host,
            port=int(os.getenv('MILVUS_PORT', 19530))
        )
        connections.disconnect("default")
        return True
    
    print("\n⏳ Waiting for services to start...")
    
    assert wait_for_service(check_postgres, 30), "PostgreSQL not ready!"
    print("✅ PostgreSQL ready")
    
    assert wait_for_service(check_mongodb, 30), "MongoDB not ready!"
    print("✅ MongoDB ready")
    
    assert wait_for_service(check_milvus, 30), "Milvus not ready!"
    print("✅ Milvus ready")
    
    print("✅ All services ready\n")
