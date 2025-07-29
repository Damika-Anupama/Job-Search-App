#!/usr/bin/env python3
"""
Debug script to test frontend-backend communication
"""
import requests
import json

def test_backend_direct():
    """Test backend API directly"""
    print("Testing backend API directly...")
    
    try:
        # Test health endpoint
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health Status: {health_response.status_code}")
        print(f"Health Response: {health_response.text}")
        
        # Test search endpoint  
        search_data = {
            "query": "python developer",
            "max_results": 5
        }
        
        search_response = requests.post(
            "http://localhost:8000/search/",
            json=search_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nSearch Status: {search_response.status_code}")
        print(f"Search Headers: {dict(search_response.headers)}")
        
        if search_response.status_code == 200:
            result = search_response.json()
            print(f"Jobs Found: {len(result.get('jobs', []))}")
            print(f"Response Keys: {list(result.keys())}")
            
            if result.get('jobs'):
                first_job = result['jobs'][0]
                print(f"First Job: {first_job.get('title', 'No title')}")
        else:
            print(f"Error Response: {search_response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_docker_network():
    """Test from inside frontend container"""
    print("\nTesting from inside frontend container...")
    
    import subprocess
    
    try:
        # Test backend connectivity from frontend container
        result = subprocess.run([
            "docker", "exec", "job-search-frontend-dev",
            "python", "-c", """
import requests
import json

try:
    # Test backend connection
    response = requests.post(
        'http://backend:8000/search/',
        json={'query': 'python developer', 'max_results': 3},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Jobs: {len(data.get("jobs", []))}')
        print('Frontend can reach backend!')
    else:
        print(f'Error: {response.text}')
        
except Exception as e:
    print(f'Error: {e}')
"""
        ], capture_output=True, text=True, timeout=30)
        
        print("Docker exec output:")
        print(result.stdout)
        if result.stderr:
            print("Docker exec errors:")
            print(result.stderr)
            
    except Exception as e:
        print(f"Docker test error: {e}")

if __name__ == "__main__":
    print("Frontend-Backend Communication Test\n")
    test_backend_direct()
    test_docker_network()
    print("\nTest completed!")