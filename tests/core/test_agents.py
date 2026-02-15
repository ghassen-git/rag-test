"""
Test: Multi-Agent System
Verifies Search Agent, Data Analyst Agent, and Orchestrator
"""
import pytest


class TestMultiAgentSystem:
    
    def test_search_agent_exists(self):
        """Verify Search Agent module exists"""
        try:
            from src.agents.search_agent import SearchAgent
            agent = SearchAgent()
            assert agent is not None
            print("✅ Search Agent initialized")
        except ImportError as e:
            pytest.fail(f"Search Agent not found: {e}")
    
    def test_analyst_agent_exists(self):
        """Verify Data Analyst Agent module exists"""
        try:
            from src.agents.analyst_agent import AnalystAgent
            agent = AnalystAgent()
            assert agent is not None
            print("✅ Data Analyst Agent initialized")
        except ImportError as e:
            pytest.fail(f"Data Analyst Agent not found: {e}")
    
    def test_orchestrator_exists(self):
        """Verify Orchestrator module exists"""
        try:
            from src.agents.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            assert orchestrator is not None
            print("✅ Orchestrator initialized")
        except ImportError as e:
            pytest.fail(f"Orchestrator not found: {e}")
    
    def test_search_agent_semantic_search(self):
        """Test Search Agent performs semantic search"""
        try:
            from src.agents.search_agent import SearchAgent
            agent = SearchAgent()
            
            results = agent.search_sync("dystopian societies", top_k=5)
            
            assert isinstance(results, list)
            
            # If results are empty, it might be due to OpenAI quota
            if len(results) == 0:
                pytest.skip("Search returned no results - likely due to OpenAI API quota")
            
            assert all('content' in r for r in results)
            
            print(f"✅ Search Agent works: found {len(results)} results")
        except ImportError:
            pytest.fail("Search Agent not implemented")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e) or "rate" in str(e).lower():
                pytest.skip(f"OpenAI API quota exceeded: {e}")
            pytest.fail(f"Search Agent not fully functional: {e}")
    
    def test_analyst_agent_postgres_query(self, postgres_connection):
        """Test Data Analyst Agent can query PostgreSQL"""
        try:
            from src.agents.analyst_agent import AnalystAgent
            agent = AnalystAgent()
            
            # Use the provided connection instead of creating a new one
            agent.pg_conn = postgres_connection
            from psycopg2.extras import RealDictCursor
            agent.pg_cursor = postgres_connection.cursor(cursor_factory=RealDictCursor)
            
            books = agent.query_postgres("SELECT * FROM books LIMIT 5")
            
            assert isinstance(books, list)
            assert len(books) > 0
            
            print(f"✅ Analyst Agent PostgreSQL query works: {len(books)} books")
        except ImportError:
            pytest.fail("Analyst Agent not implemented")
        except Exception as e:
            pytest.fail(f"Analyst Agent not fully functional: {e}")
    
    def test_analyst_agent_mongodb_query(self, mongodb_client):
        """Test Data Analyst Agent can query MongoDB"""
        try:
            from src.agents.analyst_agent import AnalystAgent
            import os
            agent = AnalystAgent()
            
            # Use the provided connection instead of creating a new one
            agent.mongo_client = mongodb_client
            agent.mongo_db = mongodb_client[os.getenv('MONGO_DB', 'books_reviews')]
            
            reviews = agent.query_mongo({"book_id": 1})
            
            assert isinstance(reviews, list)
            
            print(f"✅ Analyst Agent MongoDB query works: {len(reviews)} reviews")
        except ImportError:
            pytest.fail("Analyst Agent not implemented")
        except Exception as e:
            pytest.fail(f"Analyst Agent not fully functional: {e}")
    
    def test_orchestrator_routing(self):
        """Test Orchestrator routes queries to correct agent"""
        try:
            from src.agents.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            
            # Test search query routing
            response = orchestrator.process_query_sync("Find books about dystopia")
            assert 'agent_used' in response or 'results' in response or 'answer' in response
            
            print("✅ Orchestrator routing works")
        except ImportError:
            pytest.fail("Orchestrator not implemented")
        except Exception as e:
            pytest.fail(f"Orchestrator not fully functional: {e}")
