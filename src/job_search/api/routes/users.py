"""
User tracking endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from ..models import (
    SaveJobRequest, UpdateJobStatusRequest, SavedJobsResponse, 
    UserStatsResponse
)
from ...db.mongodb import mongodb_service, MongoDBServiceError

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/{user_id}/saved-jobs", status_code=201)
def save_job_for_user(user_id: str, request: SaveJobRequest):
    """
    💾 **Save a Job for User Tracking**
    
    Allows users to save jobs to their personal tracking list for later reference.
    This transforms the application from just a search engine into a personalized job tracker.
    
    **Features:**
    - 📌 **Personal Job Lists** - Save interesting jobs to review later
    - 📊 **Application Tracking** - Track your job application journey
    - 🔍 **Job Data Storage** - Full job details preserved for offline viewing
    - ⏰ **Timestamp Tracking** - Know when you saved each job
    """
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

@router.get("/{user_id}/saved-jobs", response_model=SavedJobsResponse)
def get_saved_jobs_for_user(user_id: str, status: Optional[str] = None):
    """
    📋 **Get User's Saved Jobs**
    
    Retrieve all jobs that a user has saved, with optional filtering by application status.
    This endpoint provides a complete view of the user's job application pipeline.
    """
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

@router.put("/{user_id}/saved-jobs/{job_id}")
def update_job_status_for_user(user_id: str, job_id: str, request: UpdateJobStatusRequest):
    """
    ✏️ **Update Job Application Status**
    
    Update the status of a saved job as you progress through the application process.
    This endpoint is crucial for tracking your job search journey and staying organized.
    """
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

@router.delete("/{user_id}/saved-jobs/{job_id}")
def remove_saved_job_for_user(user_id: str, job_id: str):
    """
    🗑️ **Remove Saved Job**
    
    Remove a job from your saved jobs list. This is useful for cleaning up your 
    job tracker when positions are no longer relevant.
    """
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

@router.get("/{user_id}/stats", response_model=UserStatsResponse)
def get_user_job_stats(user_id: str):
    """
    📊 **Get Job Search Statistics**
    
    Get comprehensive statistics about your job search progress. Perfect for 
    tracking your application pipeline and identifying areas for improvement.
    """
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