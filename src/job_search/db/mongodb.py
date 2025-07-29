"""
MongoDB service for user data and job tracking functionality.

This module handles all MongoDB operations including:
- User job tracking (saved jobs, application status)
- Database connection management
- Data validation and schema enforcement
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError
from ..core.config import settings

logger = logging.getLogger(__name__)

class MongoDBServiceError(Exception):
    """Custom exception for MongoDB service errors"""
    pass

class MongoDBService:
    """Service class for MongoDB operations"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        if not settings.MONGODB_CONNECTION_STRING:
            raise MongoDBServiceError("MongoDB connection string not configured")
        
        try:
            self.client = MongoClient(settings.MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DATABASE_NAME]
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info(f"Successfully connected to MongoDB database: {settings.MONGODB_DATABASE_NAME}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise MongoDBServiceError(f"MongoDB connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise MongoDBServiceError(f"MongoDB initialization error: {e}")
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Index on user_id for fast user queries
            self.db.users.create_index("user_id", unique=True)
            
            # Compound index on user_id and job_id for saved jobs
            self.db.users.create_index([("user_id", 1), ("saved_jobs.job_id", 1)])
            
            # Index on saved job status for filtering
            self.db.users.create_index("saved_jobs.status")
            
            # Index on saved date for sorting
            self.db.users.create_index("saved_jobs.saved_at")
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create MongoDB indexes: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check MongoDB connection health"""
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "No connection"}
            
            # Ping the server
            self.client.admin.command('ping')
            
            # Get database stats
            stats = self.db.command("dbstats")
            
            return {
                "status": "healthy",
                "database": settings.MONGODB_DATABASE_NAME,
                "collections": len(self.db.list_collection_names()),
                "storage_size": stats.get("storageSize", 0),
                "data_size": stats.get("dataSize", 0)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user document by user_id"""
        try:
            return self.db.users.find_one({"user_id": user_id})
        except PyMongoError as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to fetch user: {e}")
    
    def create_user_if_not_exists(self, user_id: str) -> Dict[str, Any]:
        """Create user document if it doesn't exist"""
        try:
            user_doc = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "saved_jobs": [],
                "profile": {
                    "preferences": {},
                    "search_history": []
                }
            }
            
            # Use upsert to create only if doesn't exist
            result = self.db.users.update_one(
                {"user_id": user_id},
                {"$setOnInsert": user_doc},
                upsert=True
            )
            
            # Return the user document
            return self.get_user(user_id)
            
        except DuplicateKeyError:
            # User already exists, return existing
            return self.get_user(user_id)
        except PyMongoError as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to create user: {e}")
    
    def save_job(self, user_id: str, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Save a job for a user"""
        try:
            # Ensure user exists
            self.create_user_if_not_exists(user_id)
            
            saved_job = {
                "job_id": job_id,
                "saved_at": datetime.utcnow(),
                "status": "saved",
                "notes": "",
                "job_data": job_data,
                "application_date": None,
                "interview_dates": [],
                "updated_at": datetime.utcnow()
            }
            
            # Check if job is already saved
            existing = self.db.users.find_one({
                "user_id": user_id,
                "saved_jobs.job_id": job_id
            })
            
            if existing:
                raise MongoDBServiceError(f"Job {job_id} is already saved for user {user_id}")
            
            # Add the job to user's saved jobs
            result = self.db.users.update_one(
                {"user_id": user_id},
                {"$push": {"saved_jobs": saved_job}}
            )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error saving job {job_id} for user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to save job: {e}")
    
    def get_saved_jobs(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all saved jobs for a user, optionally filtered by status"""
        try:
            user = self.get_user(user_id)
            if not user:
                return []
            
            saved_jobs = user.get("saved_jobs", [])
            
            # Filter by status if provided
            if status:
                saved_jobs = [job for job in saved_jobs if job.get("status") == status]
            
            # Sort by saved date (most recent first)
            saved_jobs.sort(key=lambda x: x.get("saved_at", datetime.min), reverse=True)
            
            return saved_jobs
            
        except PyMongoError as e:
            logger.error(f"Error fetching saved jobs for user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to fetch saved jobs: {e}")
    
    def update_job_status(self, user_id: str, job_id: str, status: str, notes: str = None) -> bool:
        """Update the status of a saved job"""
        try:
            valid_statuses = ["saved", "applied", "interviewing", "offered", "rejected", "withdrawn"]
            if status not in valid_statuses:
                raise MongoDBServiceError(f"Invalid status: {status}. Must be one of {valid_statuses}")
            
            update_data = {
                "saved_jobs.$.status": status,
                "saved_jobs.$.updated_at": datetime.utcnow()
            }
            
            if notes is not None:
                update_data["saved_jobs.$.notes"] = notes
            
            if status == "applied":
                update_data["saved_jobs.$.application_date"] = datetime.utcnow()
            
            result = self.db.users.update_one(
                {
                    "user_id": user_id,
                    "saved_jobs.job_id": job_id
                },
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise MongoDBServiceError(f"Job {job_id} not found for user {user_id}")
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error updating job {job_id} status for user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to update job status: {e}")
    
    def remove_saved_job(self, user_id: str, job_id: str) -> bool:
        """Remove a saved job from user's list"""
        try:
            result = self.db.users.update_one(
                {"user_id": user_id},
                {"$pull": {"saved_jobs": {"job_id": job_id}}}
            )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error removing job {job_id} for user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to remove saved job: {e}")
    
    def get_job_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's saved jobs"""
        try:
            user = self.get_user(user_id)
            if not user:
                return {"total": 0, "by_status": {}}
            
            saved_jobs = user.get("saved_jobs", [])
            total = len(saved_jobs)
            
            # Count by status
            status_counts = {}
            for job in saved_jobs:
                status = job.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total": total,
                "by_status": status_counts,
                "recent_activity": len([j for j in saved_jobs if 
                    (datetime.utcnow() - j.get("updated_at", datetime.min)).days <= 7])
            }
            
        except PyMongoError as e:
            logger.error(f"Error getting job stats for user {user_id}: {e}")
            raise MongoDBServiceError(f"Failed to get job statistics: {e}")
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Global instance
try:
    mongodb_service = MongoDBService()
except Exception as e:
    logger.warning(f"MongoDB service initialization failed: {e}")
    mongodb_service = None