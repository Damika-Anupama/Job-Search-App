"""
Job search endpoints.
"""

from fastapi import APIRouter, HTTPException
from ..models import SearchRequest, SearchResponse
from ...core.search import SearchService
from ...core.config import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)

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
    
    Note: In demo mode, this simulates the indexing process.
    """
    # Mock indexing for demo purposes
    logger.info("🔄 Received request to trigger indexing job")
    
    return {
        "message": "Job indexing task has been triggered and is running in the background.",
        "status": "accepted",
        "mode": "demo",
        "note": "In demo mode, the system uses pre-configured job data for search results."
    }