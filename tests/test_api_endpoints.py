#!/usr/bin/env python3
"""
Test script for MongoDB user tracking API endpoints
"""

import requests
import json
import time
import sys
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """Test all user tracking API endpoints"""
    
    print("Testing MongoDB User Tracking API Endpoints\n")
    
    # Test data
    user_id = "test_user_api_123"
    job_id = "job_api_test_456"
    job_data = {
        "text": "Senior Python Developer at API Test Corp - Remote position with great benefits...",
        "score": 0.92,
        "vector_score": 0.85,
        "cross_score": 0.92,
        "source": "api_test"
    }
    
    try:
        # 1. Test API health check
        print("1. Testing API health check...")
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   API Status: {health_data.get('status', 'unknown')}")
            mongodb_status = health_data.get('components', {}).get('mongodb', {}).get('status', 'unknown')
            print(f"   MongoDB Status: {mongodb_status}")
            if mongodb_status != 'healthy':
                print("   ERROR: MongoDB not healthy")
                return False
            print("   SUCCESS: API and MongoDB healthy\n")
        else:
            print(f"   ERROR: Health check failed with status {response.status_code}")
            return False
        
        # 2. Test saving a job (POST /users/{user_id}/saved-jobs)
        print("2. Testing POST /users/{user_id}/saved-jobs...")
        save_data = {
            "job_id": job_id,
            "job_data": job_data
        }
        response = requests.post(f"{BASE_URL}/users/{user_id}/saved-jobs", json=save_data)
        if response.status_code == 201:
            result = response.json()
            print(f"   SUCCESS: Job saved - {result['message']}")
        else:
            print(f"   ERROR: Failed to save job - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        print()
        
        # 3. Test getting saved jobs (GET /users/{user_id}/saved-jobs)
        print("3. Testing GET /users/{user_id}/saved-jobs...")
        response = requests.get(f"{BASE_URL}/users/{user_id}/saved-jobs")
        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Retrieved {result['total_saved']} saved jobs")
            if result['jobs']:
                job = result['jobs'][0]
                print(f"   Job ID: {job['job_id']}")
                print(f"   Status: {job['status']}")
                print(f"   Job Text: {job['job_data']['text'][:50]}...")
            print(f"   Statistics: {result['statistics']}")
        else:
            print(f"   ERROR: Failed to get saved jobs - Status: {response.status_code}")
            return False
        print()
        
        # 4. Test updating job status (PUT /users/{user_id}/saved-jobs/{job_id})
        print("4. Testing PUT /users/{user_id}/saved-jobs/{job_id}...")
        update_data = {
            "status": "applied",
            "notes": "Applied through API test - looks promising!"
        }
        response = requests.put(f"{BASE_URL}/users/{user_id}/saved-jobs/{job_id}", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Status updated - {result['message']}")
            print(f"   New status: {result['new_status']}")
            print(f"   Notes: {result['notes']}")
        else:
            print(f"   ERROR: Failed to update job status - Status: {response.status_code}")
            return False
        print()
        
        # 5. Test filtering by status
        print("5. Testing status filtering...")
        response = requests.get(f"{BASE_URL}/users/{user_id}/saved-jobs?status=applied")
        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Found {result['total_saved']} applied jobs")
        else:
            print(f"   ERROR: Failed to filter jobs - Status: {response.status_code}")
            return False
        print()
        
        # 6. Test user statistics (GET /users/{user_id}/stats)
        print("6. Testing GET /users/{user_id}/stats...")
        response = requests.get(f"{BASE_URL}/users/{user_id}/stats")
        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Retrieved user statistics")
            print(f"   Total jobs: {result['total_jobs']}")
            print(f"   By status: {result['by_status']}")
            print(f"   Recent activity: {result['recent_activity']}")
        else:
            print(f"   ERROR: Failed to get user stats - Status: {response.status_code}")
            return False
        print()
        
        # 7. Test removing a job (DELETE /users/{user_id}/saved-jobs/{job_id})
        print("7. Testing DELETE /users/{user_id}/saved-jobs/{job_id}...")
        response = requests.delete(f"{BASE_URL}/users/{user_id}/saved-jobs/{job_id}")
        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Job removed - {result['message']}")
        else:
            print(f"   ERROR: Failed to remove job - Status: {response.status_code}")
            return False
        print()
        
        # 8. Verify job was removed
        print("8. Verifying job removal...")
        response = requests.get(f"{BASE_URL}/users/{user_id}/saved-jobs")
        if response.status_code == 200:
            result = response.json()
            if result['total_saved'] == 0:
                print("   SUCCESS: Job successfully removed from database")
            else:
                print(f"   ERROR: Job still exists: {result['total_saved']} jobs remaining")
                return False
        else:
            print(f"   ERROR: Failed to verify removal - Status: {response.status_code}")
            return False
        print()
        
        print("SUCCESS: All API endpoint tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)