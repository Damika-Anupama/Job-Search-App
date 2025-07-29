#!/usr/bin/env python3
"""
Simple backend test that works with our new structure
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

app = FastAPI(
    title="Job Search API Test",
    description="Simple test backend for frontend integration",
    version="1.0.0"
)

class SearchRequest(BaseModel):
    query: str
    max_results: int = 20
    locations: List[str] = []
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    exclude_keywords: List[str] = []

class JobResult(BaseModel):
    id: str
    score: float
    text: str

class SearchResponse(BaseModel):
    source: str
    results: List[JobResult]
    total_found: int
    filters_applied: Dict[str, Any]
    reranked: bool = False

@app.get("/")
def root():
    return {
        "message": "Job Search API Test is running",
        "version": "1.0.0",
        "docs": "Visit /docs for API documentation"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "mode": "test",
        "components": {
            "api": {"status": "healthy"},
            "test_mode": {"status": "healthy"}
        }
    }

@app.post("/search/", response_model=SearchResponse)
def search_jobs(request: SearchRequest):
    """Test search endpoint that returns dummy data"""
    
    # Create dummy job results
    dummy_jobs = [
        {
            "id": f"test_job_{i}",
            "score": 0.9 - (i * 0.1),
            "text": f"""Senior Python Developer - Remote

Company: Tech Corp {i}
Location: Remote / San Francisco

We are looking for a talented Python developer to join our growing team. 

Requirements:
- 3+ years Python experience
- Experience with Django/FastAPI
- Knowledge of databases (PostgreSQL, MongoDB)
- Strong problem-solving skills

What we offer:
- Competitive salary
- Remote work flexibility
- Great benefits package
- Career growth opportunities

Apply now to join our innovative team!"""
        }
        for i in range(1, min(request.max_results + 1, 6))
    ]
    
    return SearchResponse(
        source="test",
        results=dummy_jobs,
        total_found=len(dummy_jobs),
        filters_applied={
            "query": request.query,
            "locations": request.locations,
            "required_skills": request.required_skills,
            "exclude_keywords": request.exclude_keywords
        },
        reranked=False
    )

@app.post("/search/trigger-indexing")
def trigger_indexing():
    """Test indexing endpoint"""
    return {"message": "Test indexing triggered (no actual indexing performed)"}

# User tracking endpoints (dummy implementations)
@app.post("/users/{user_id}/saved-jobs")
def save_job(user_id: str, job_data: Dict[str, Any]):
    return {
        "message": f"Job saved for user {user_id} (test mode)",
        "job_id": job_data.get("job_id", "test_job"),
        "user_id": user_id
    }

@app.get("/users/{user_id}/saved-jobs")
def get_saved_jobs(user_id: str, status: str = None):
    return {
        "user_id": user_id,
        "total_saved": 0,
        "jobs": [],
        "statistics": {"total": 0, "by_status": {}, "recent_activity": 0}
    }

@app.put("/users/{user_id}/saved-jobs/{job_id}")
def update_job_status(user_id: str, job_id: str, status_data: Dict[str, Any]):
    return {
        "message": f"Job {job_id} status updated (test mode)",
        "job_id": job_id,
        "user_id": user_id,
        "new_status": status_data.get("status", "saved")
    }

@app.delete("/users/{user_id}/saved-jobs/{job_id}")
def remove_saved_job(user_id: str, job_id: str):
    return {
        "message": f"Job {job_id} removed from saved jobs (test mode)",
        "job_id": job_id,
        "user_id": user_id
    }

@app.get("/users/{user_id}/stats")
def get_user_stats(user_id: str):
    return {
        "user_id": user_id,
        "total_jobs": 0,
        "by_status": {},
        "recent_activity": 0
    }

if __name__ == "__main__":
    print("Starting test backend server...")
    print("API will be available at: http://localhost:8001")
    print("API docs at: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)