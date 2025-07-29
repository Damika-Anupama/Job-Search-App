#!/usr/bin/env python3
"""
Minimal FastAPI backend for container testing
"""
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Test Backend")

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10

@app.get("/")
def read_root():
    return {"message": "Container test backend is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "container-test-backend"}

@app.post("/search/")
def search_jobs(request: SearchRequest):
    # Mock job results for testing
    mock_jobs = [
        {
            "id": f"job_{i}",
            "title": f"Python Developer {i}",
            "company": f"Tech Company {i}",
            "location": "Remote",
            "description": f"Looking for a Python developer with {i} years experience",
            "text": f"Python Developer {i} - Tech Company {i} - Remote location job posting",
            "relevance_score": 0.9 - (i * 0.1)
        }
        for i in range(1, min(request.max_results + 1, 6))
    ]
    
    return {
        "jobs": mock_jobs,
        "total_results": len(mock_jobs),
        "query": request.query,
        "message": "Container backend working correctly!"
    }

@app.post("/users/{user_id}/saved-jobs")
def save_job(user_id: str, job_data: dict):
    return {"status": "saved", "user_id": user_id, "job_id": job_data.get("job_id")}

@app.get("/users/{user_id}/saved-jobs")
def get_saved_jobs(user_id: str):
    return {"saved_jobs": [], "user_id": user_id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)