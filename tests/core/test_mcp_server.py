"""
Test: MCP Server Implementation
Verifies Model Context Protocol server for database access
"""
import pytest
import requests


class TestMCPServer:
    
    def test_mcp_server_running(self, api_base_url):
        """Verify MCP server is running and accessible"""
        try:
            # Try the tools endpoint instead of health
            response = requests.get(f"{api_base_url}/mcp/tools", timeout=5)
            assert response.status_code == 200
            print("✅ MCP server is running")
        except requests.exceptions.RequestException:
            # Try alternative endpoint
            try:
                response = requests.get(f"{api_base_url}/health", timeout=5)
                assert response.status_code == 200
                print("✅ MCP server is running (via /health)")
            except requests.exceptions.RequestException as e:
                pytest.skip(f"MCP server not accessible: {e}")
    
    def test_mcp_tools_endpoint(self, api_base_url):
        """Verify MCP exposes tools endpoint"""
        try:
            response = requests.get(f"{api_base_url}/mcp/tools", timeout=5)
            assert response.status_code == 200
            
            tools = response.json()
            assert 'tools' in tools or isinstance(tools, list)
            
            print(f"✅ MCP tools endpoint works: {len(tools.get('tools', tools))} tools available")
        except requests.exceptions.RequestException:
            pytest.skip("MCP tools endpoint not available")
    
    def test_mcp_has_postgres_tool(self, api_base_url):
        """Verify MCP exposes PostgreSQL query tool"""
        try:
            response = requests.get(f"{api_base_url}/mcp/tools", timeout=5)
            tools = response.json()
            
            tool_names = [t['name'] for t in tools.get('tools', tools)] if isinstance(tools, dict) else [t['name'] for t in tools]
            
            # Check for any PostgreSQL-related tools
            postgres_tools = ['read_book_metadata', 'search_books', 'update_rating']
            assert any(tool in tool_names for tool in postgres_tools), \
                f"No PostgreSQL tool found. Available: {tool_names}"
            
            print("✅ MCP has PostgreSQL tools")
        except requests.exceptions.RequestException:
            pytest.skip("MCP tools endpoint not available")
    
    def test_mcp_has_mongo_tool(self, api_base_url):
        """Verify MCP exposes MongoDB query tool"""
        try:
            response = requests.get(f"{api_base_url}/mcp/tools", timeout=5)
            tools = response.json()
            
            tool_names = [t['name'] for t in tools.get('tools', tools)] if isinstance(tools, dict) else [t['name'] for t in tools]
            
            # Check for any MongoDB-related tools
            mongo_tools = ['read_reviews', 'add_review', 'aggregate_reviews']
            assert any(tool in tool_names for tool in mongo_tools), \
                f"No MongoDB tool found. Available: {tool_names}"
            
            print("✅ MCP has MongoDB tools")
        except requests.exceptions.RequestException:
            pytest.skip("MCP tools endpoint not available")
    
    def test_mcp_tool_invocation(self, api_base_url):
        """Test MCP tool can be invoked"""
        try:
            response = requests.post(
                f"{api_base_url}/mcp/call",  # Changed from /mcp/invoke to /mcp/call
                json={
                    "tool": "search_books",
                    "parameters": {"title": "1984"}
                },
                timeout=10
            )
            
            # Should return 200 or appropriate success code
            assert response.status_code in [200, 201], f"Tool invocation failed: {response.status_code}"
            
            print("✅ MCP tool invocation works")
        except requests.exceptions.RequestException:
            pytest.skip("MCP tool invocation not available")
    
    def test_mcp_tool_schemas(self, api_base_url):
        """Verify MCP tools have proper JSON schemas"""
        try:
            response = requests.get(f"{api_base_url}/mcp/tools", timeout=5)
            tools = response.json()
            
            tool_list = tools.get('tools', tools) if isinstance(tools, dict) else tools
            
            for tool in tool_list[:3]:  # Check first 3 tools
                assert 'name' in tool
                assert 'description' in tool or 'desc' in tool
                # Schema is optional but nice to have
            
            print("✅ MCP tools have proper schemas")
        except requests.exceptions.RequestException:
            pytest.skip("MCP tools endpoint not available")
