"""
Health check endpoints.
"""

from fastapi import APIRouter
from ..models import HealthResponse
from ...core.config import settings
from ...db.mongodb import mongodb_service
from ...ml.embeddings import embedding_service

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", response_model=HealthResponse)
def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns:
        - Overall system status
        - Individual component health
        - Mode-specific diagnostics
    """
    health_status = {
        "status": "healthy",
        "mode": settings.APP_MODE.value,
        "components": {}
    }
    
    # Check embedding service
    if embedding_service:
        embedding_health = embedding_service.health_check()
        health_status["components"]["embedding_service"] = embedding_health
        
        if embedding_health["status"] in ["unhealthy", "degraded"]:
            health_status["status"] = embedding_health["status"]
    
    # Check MongoDB
    if mongodb_service:
        mongodb_health = mongodb_service.health_check()
        health_status["components"]["mongodb"] = mongodb_health
        
        if mongodb_health["status"] != "healthy":
            health_status["status"] = "degraded"
    else:
        health_status["components"]["mongodb"] = {
            "status": "unhealthy", 
            "message": "MongoDB service not initialized"
        }
        health_status["status"] = "degraded"
    
    return health_status

@router.get("/embedding")
def embedding_health():
    """
    Detailed embedding service health check.
    
    Returns:
        - Embedding service status
        - Mode-specific diagnostics  
        - API availability (for cloud mode)
    """
    if not embedding_service:
        return {"status": "unhealthy", "message": "Embedding service not initialized"}
    
    return embedding_service.health_check()