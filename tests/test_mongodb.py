#!/usr/bin/env python3
"""
Simple test script for MongoDB user tracking functionality
"""

import sys
import json
from datetime import datetime
from mongodb_service import mongodb_service, MongoDBServiceError

def test_mongodb_functionality():
    """Test all MongoDB user tracking features"""
    
    if not mongodb_service:
        print("ERROR: MongoDB service not initialized")
        return False
    
    print("Testing MongoDB User Tracking Functionality\n")
    
    # Test data
    test_user_id = "test_user_123"
    test_job_id = "job_test_456"
    test_job_data = {
        "text": "Senior Python Developer at Tech Corp - Remote position with competitive salary...",
        "score": 0.95,
        "vector_score": 0.88,
        "cross_score": 0.95,
        "source": "test"
    }
    
    try:
        # 1. Test health check
        print("1. Testing MongoDB health check...")
        health = mongodb_service.health_check()
        print(f"   Health status: {health['status']}")
        if health['status'] != 'healthy':
            print(f"   Error: {health.get('error', 'Unknown error')}")
            return False
        print("   SUCCESS: MongoDB connection healthy\n")
        
        # 2. Test saving a job
        print("2. Testing job saving...")
        success = mongodb_service.save_job(test_user_id, test_job_id, test_job_data)
        if success:
            print("   SUCCESS: Job saved successfully")
        else:
            print("   ERROR: Failed to save job")
            return False
        print()
        
        # 3. Test getting saved jobs
        print("3. Testing job retrieval...")
        saved_jobs = mongodb_service.get_saved_jobs(test_user_id)
        if saved_jobs and len(saved_jobs) > 0:
            print(f"   SUCCESS: Retrieved {len(saved_jobs)} saved jobs")
            job = saved_jobs[0]
            print(f"   Job ID: {job['job_id']}")
            print(f"   Status: {job['status']}")
            print(f"   Saved at: {job['saved_at']}")
        else:
            print("   ERROR: No saved jobs found")
            return False
        print()
        
        # 4. Test updating job status
        print("4. Testing job status update...")
        success = mongodb_service.update_job_status(
            test_user_id, 
            test_job_id, 
            "applied", 
            "Applied through company website"
        )
        if success:
            print("   SUCCESS: Job status updated successfully")
        else:
            print("   ERROR: Failed to update job status")
            return False
        print()
        
        # 5. Test getting job statistics
        print("5. Testing job statistics...")
        stats = mongodb_service.get_job_stats(test_user_id)
        print(f"   Total jobs: {stats['total']}")
        print(f"   By status: {stats['by_status']}")
        print(f"   Recent activity: {stats['recent_activity']}")
        print("   SUCCESS: Statistics retrieved successfully\n")
        
        # 6. Test filtering by status
        print("6. Testing status filtering...")
        applied_jobs = mongodb_service.get_saved_jobs(test_user_id, status="applied")
        if applied_jobs and len(applied_jobs) > 0:
            print(f"   SUCCESS: Found {len(applied_jobs)} applied jobs")
        else:
            print("   ERROR: No applied jobs found after status update")
            return False
        print()
        
        # 7. Test removing a job
        print("7. Testing job removal...")
        success = mongodb_service.remove_saved_job(test_user_id, test_job_id)
        if success:
            print("   SUCCESS: Job removed successfully")
        else:
            print("   ERROR: Failed to remove job")
            return False
        print()
        
        # 8. Verify job was removed
        print("8. Verifying job removal...")
        remaining_jobs = mongodb_service.get_saved_jobs(test_user_id)
        if len(remaining_jobs) == 0:
            print("   SUCCESS: Job successfully removed from database")
        else:
            print(f"   ERROR: Job still exists: {len(remaining_jobs)} jobs remaining")
            return False
        print()
        
        print("SUCCESS: All MongoDB tests passed successfully!")
        return True
        
    except MongoDBServiceError as e:
        print(f"ERROR: MongoDB service error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_mongodb_functionality()
    sys.exit(0 if success else 1)