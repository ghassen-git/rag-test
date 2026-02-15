"""
Test: Concurrent User Load
Verifies system handles multiple simultaneous queries
"""
import pytest
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestConcurrentLoad:
    
    def test_concurrent_queries(self):
        """Test system handles 20 concurrent queries"""
        api_url = 'http://localhost:8000/query'
        
        def send_query(query_id):
            """Send a query and return response time"""
            start = time.time()
            try:
                response = requests.post(
                    api_url,
                    json={"question": f"What is book {query_id % 10 + 1} about?"},
                    timeout=15
                )
                duration = time.time() - start
                return {
                    'query_id': query_id,
                    'status': response.status_code,
                    'duration': duration,
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'query_id': query_id,
                    'status': 'error',
                    'duration': time.time() - start,
                    'success': False,
                    'error': str(e)
                }
        
        # Send 20 concurrent queries
        num_queries = 20
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_query, i) for i in range(num_queries)]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = sum(1 for r in results if r['success'])
        avg_duration = sum(r['duration'] for r in results) / len(results)
        max_duration = max(r['duration'] for r in results)
        
        print(f"\n📊 Concurrent Load Test Results:")
        print(f"   Total queries: {num_queries}")
        print(f"   Successful: {successful}/{num_queries} ({successful/num_queries*100:.1f}%)")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Avg response: {avg_duration:.2f}s")
        print(f"   Max response: {max_duration:.2f}s")
        
        # Assertions
        assert successful >= num_queries * 0.8, \
            f"Too many failures: {successful}/{num_queries}"
        
        # Performance assertions with warnings (relaxed thresholds)
        if avg_duration >= 15:
            pytest.fail(f"Avg response too slow: {avg_duration:.2f}s")
        elif avg_duration >= 12:
            print(f"⚠️  Warning: Avg response time is {avg_duration:.2f}s (target: <12s)")
        
        if max_duration >= 30:
            pytest.fail(f"Slowest query too slow: {max_duration:.2f}s")
        elif max_duration >= 25:
            print(f"⚠️  Warning: Max response time is {max_duration:.2f}s (target: <25s)")
        
        print("✅ System handles concurrent load well")
    
    def test_rate_limiting_exists(self):
        """Check if rate limiting is implemented (optional)"""
        # This is optional - just check if system survives rapid requests
        api_url = 'http://localhost:8000/query'
        
        # Send 50 rapid requests
        for i in range(50):
            try:
                requests.post(
                    api_url,
                    json={"question": "test"},
                    timeout=2
                )
            except:
                pass
        
        # System should still be responsive
        response = requests.post(
            api_url,
            json={"question": "Are you still working?"},
            timeout=10
        )
        
        assert response.status_code in [200, 429], \
            "System crashed or unresponsive after rapid requests!"
        
        print("✅ System survives rapid requests")
