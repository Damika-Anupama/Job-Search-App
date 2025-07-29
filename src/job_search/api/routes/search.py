"""
Job search endpoints.
"""

from fastapi import APIRouter, HTTPException
from ..models import SearchRequest, SearchResponse
from ...core.search import SearchService
from ...core.config import settings

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
def search_jobs(request: SearchRequest):
    """
    🚀 **Job Search with Mode-Specific Processing**
    
    This endpoint adapts its behavior based on the current application mode:
    
    **🚀 LIGHTWEIGHT MODE:**
    - Simple keyword-based search
    - No ML processing or vector embeddings
    - Fast response times with basic filtering
    
    **🧠 FULL ML MODE:**
    - Local semantic vector search with sentence transformers
    - Cross-encoder reranking for improved relevance
    - Two-stage search: broad retrieval + precise reranking
    
    **☁️ CLOUD ML MODE:**
    - HuggingFace Inference API for embeddings
    - Automatic fallback to local models if cloud fails
    - Cross-encoder reranking with detailed health monitoring
    
    **✨ Common Features:**
    - **Smart filtering** - Location, skills, keyword exclusions
    - **Relevance boosting** - Preferred skills increase scores  
    - **Intelligent caching** - Fast repeat queries
    - **Health monitoring** - Component status tracking
    """
    search_service = SearchService()
    return search_service.search(request)

@router.post("/trigger-indexing", status_code=202)
def trigger_indexing_job():
    """
    Triggers the background task to scrape and index jobs.
    Returns immediately with a 202 Accepted response.
    """
    from ...scraping.tasks import crawl_and_index
    
    print("Received request to trigger indexing job.")
    crawl_and_index.delay()  # Use .delay() to send the task to the Celery worker
    return {"message": "Job indexing task has been triggered and is running in the background."}