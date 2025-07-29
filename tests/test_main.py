#!/usr/bin/env python3
"""
Minimal FastAPI app for testing MongoDB user tracking endpoints
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from mongodb_service import mongodb_service, MongoDBServiceError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Job Search API - User Tracking Test",
    description="Testing MongoDB user tracking functionality",
    version="1.0.0"
)

# Pydantic models for user tracking
class SaveJobRequest(BaseModel):
    job_id: str = Field(description="Unique identifier of the job to save")
    job_data: Dict[str, Any] = Field(description="Complete job data including text, metadata, etc.")

class UpdateJobStatusRequest(BaseModel):
    status: str = Field(
        description="New status for the job",
        examples=["saved", "applied", "interviewing", "offered", "rejected", "withdrawn"]
    )
    notes: Optional[str] = Field(default="", description="Optional notes about the status change")

class SavedJob(BaseModel):
    job_id: str = Field(description="Unique identifier of the saved job")
    saved_at: datetime = Field(description="When the job was saved")
    status: str = Field(description="Current status of the job application")
    notes: str = Field(description="User notes about this job")
    job_data: Dict[str, Any] = Field(description="Complete job information")
    application_date: Optional[datetime] = Field(default=None, description="Date when applied (if status is applied)")
    interview_dates: List[datetime] = Field(default=[], description="List of interview dates")
    updated_at: datetime = Field(description="Last time this job was updated")

class SavedJobsResponse(BaseModel):
    user_id: str = Field(description="User identifier")
    total_saved: int = Field(description="Total number of saved jobs")
    jobs: List[SavedJob] = Field(description="List of saved jobs")
    statistics: Dict[str, Any] = Field(description="Job application statistics")

class UserStatsResponse(BaseModel):
    user_id: str = Field(description="User identifier")
    total_jobs: int = Field(description="Total number of saved jobs")
    by_status: Dict[str, int] = Field(description="Count of jobs by status")
    recent_activity: int = Field(description="Number of jobs updated in last 7 days")

# Health check endpoints
@app.get("/")
def read_root():
    return {
        "message": "Job Search API - User Tracking Test",
        "version": "1.0.0",
        "features": ["MongoDB user tracking", "Job saving", "Status updates"]
    }

@app.get("/health")
def health_check():
    health_status = {
        "status": "healthy",
        "components": {}
    }
    
    # Check MongoDB
    if mongodb_service:
        mongodb_health = mongodb_service.health_check()
        health_status["components"]["mongodb"] = mongodb_health
        
        if mongodb_health["status"] != "healthy":
            health_status["status"] = "degraded"
    else:
        health_status["components"]["mongodb"] = {"status": "unhealthy", "message": "MongoDB service not initialized"}
        health_status["status"] = "unhealthy"
    
    return health_status

# User tracking endpoints
@app.post("/users/{user_id}/saved-jobs", status_code=201)
def save_job_for_user(user_id: str, request: SaveJobRequest):
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.save_job(user_id, request.job_id, request.job_data)
        if success:
            return {
                "message": f"Job {request.job_id} saved successfully for user {user_id}",
                "job_id": request.job_id,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save job")
            
    except MongoDBServiceError as e:
        if "already saved" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/saved-jobs", response_model=SavedJobsResponse)
def get_saved_jobs_for_user(user_id: str, status: Optional[str] = None):
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        saved_jobs = mongodb_service.get_saved_jobs(user_id, status)
        stats = mongodb_service.get_job_stats(user_id)
        
        return SavedJobsResponse(
            user_id=user_id,
            total_saved=len(saved_jobs),
            jobs=saved_jobs,
            statistics=stats
        )
        
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/users/{user_id}/saved-jobs/{job_id}")
def update_job_status_for_user(user_id: str, job_id: str, request: UpdateJobStatusRequest):
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.update_job_status(
            user_id, 
            job_id, 
            request.status, 
            request.notes
        )
        
        if success:
            return {
                "message": f"Job {job_id} status updated to '{request.status}' for user {user_id}",
                "job_id": job_id,
                "user_id": user_id,
                "new_status": request.status,
                "notes": request.notes
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update job status")
            
    except MongoDBServiceError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "Invalid status" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.delete("/users/{user_id}/saved-jobs/{job_id}")
def remove_saved_job_for_user(user_id: str, job_id: str):
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.remove_saved_job(user_id, job_id)
        
        if success:
            return {
                "message": f"Job {job_id} removed from saved jobs for user {user_id}",
                "job_id": job_id,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found in saved jobs for user {user_id}")
            
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/stats", response_model=UserStatsResponse)
def get_user_job_stats(user_id: str):
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        stats = mongodb_service.get_job_stats(user_id)
        
        return UserStatsResponse(
            user_id=user_id,
            total_jobs=stats["total"],
            by_status=stats["by_status"],
            recent_activity=stats["recent_activity"]
        )
        
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)