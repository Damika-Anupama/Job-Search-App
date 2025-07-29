"""
Frontend configuration settings.
"""

import os
from typing import Dict, Any

class FrontendSettings:
    """Frontend application settings"""
    
    # Backend API Configuration  
    BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://backend:8000")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    
    # UI Configuration
    PAGE_TITLE = "🚀 AI Job Discovery Platform"
    PAGE_ICON = "🔍"
    LAYOUT = "wide"
    INITIAL_SIDEBAR_STATE = "expanded"
    
    # Search Configuration
    DEFAULT_MAX_RESULTS = 20
    MAX_SEARCH_QUERY_LENGTH = 500
    SEARCH_PLACEHOLDER = "e.g., 'Senior Python Developer Remote' or 'Machine Learning Engineer San Francisco'"
    
    # Job Status Options
    JOB_STATUS_OPTIONS = [
        "📌 Saved",
        "📝 Applied", 
        "📞 Phone Screen",
        "💻 Technical Interview",
        "🎤 Final Interview",
        "🎉 Offer Received",
        "❌ Rejected",
        "🚫 Withdrawn"
    ]
    
    # Color Scheme
    COLORS = {
        "primary": "#1f77b4",
        "secondary": "#ff7f0e", 
        "success": "#2ca02c",
        "warning": "#d62728",
        "info": "#17a2b8",
        "light": "#f8f9fa",
        "dark": "#343a40"
    }
    
    # API Endpoints (matching new backend structure)
    ENDPOINTS = {
        "search": "/search/",
        "trigger_indexing": "/search/trigger-indexing",
        "health": "/health/",
        "embedding_health": "/health/embedding",
        "save_job": "/users/{user_id}/saved-jobs",
        "get_saved_jobs": "/users/{user_id}/saved-jobs",
        "update_job_status": "/users/{user_id}/saved-jobs/{job_id}",
        "remove_saved_job": "/users/{user_id}/saved-jobs/{job_id}",
        "user_stats": "/users/{user_id}/stats"
    }
    
    # Cache Settings
    CACHE_TTL = 300  # 5 minutes
    MAX_CACHE_SIZE = 100
    
    # Performance Settings
    JOBS_PER_PAGE = 10
    AUTO_REFRESH_INTERVAL = 30  # seconds
    
    @classmethod
    def get_api_url(cls, endpoint: str, **kwargs) -> str:
        """Get full API URL for endpoint"""
        endpoint_path = cls.ENDPOINTS.get(endpoint, endpoint)
        if kwargs:
            endpoint_path = endpoint_path.format(**kwargs)
        return f"{cls.BACKEND_BASE_URL}{endpoint_path}"

settings = FrontendSettings()