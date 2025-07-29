"""
Main FastAPI application entry point.

This is the new, clean main application file that assembles all components.
"""

import logging
from fastapi import FastAPI
from .core.config import settings
from .api.routes import health, search, users

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_app_description():
    """Generate mode-specific application description"""
    base_desc = """🚀 **Multi-Source Job Search Platform**
    
    Discover your perfect job with intelligent filtering across multiple job boards.
    
    **Data Sources:**
    - 🔥 Hacker News "Who is Hiring?" threads
    - 🌍 Remote OK (remote jobs)
    - 💼 Arbeit Now (European jobs)
    - 🎯 The Muse (curated positions)
    """
    
    mode_descriptions = {
        "lightweight": """
    **🚀 LIGHTWEIGHT MODE**
    - ⚡ **Fast Keyword Search** - Simple text matching
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required skills filtering
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Redis Caching** - Fast repeat searches
        """,
        "full-ml": """
    **🧠 FULL ML MODE (Local)**
    - 🔍 **Semantic Search** - Find jobs by meaning using local ML models
    - 🎯 **Cross-Encoder Reranking** - Advanced relevance scoring
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required and preferred technologies
    - ⚡ **Smart Scoring** - Relevance boosting based on preferences
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Intelligent Caching** - Lightning-fast repeat searches
        """,
        "cloud-ml": """
    **☁️ CLOUD ML MODE (HuggingFace)**
    - 🌐 **Cloud Semantic Search** - HuggingFace Inference API embeddings
    - 🎯 **Cross-Encoder Reranking** - Advanced relevance scoring
    - 🔄 **Local Fallback** - Automatic fallback to local models if cloud fails
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required and preferred technologies
    - ⚡ **Smart Scoring** - Relevance boosting based on preferences
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Intelligent Caching** - Lightning-fast repeat searches
    - 📊 **Health Monitoring** - Real-time cloud service status
        """
    }
    
    return base_desc + mode_descriptions.get(settings.APP_MODE.value, "")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=f"Job Search API ({settings.APP_MODE.value.upper()})",
        description=get_app_description(),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Include routers
    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(users.router)
    
    # Root endpoint
    @app.get("/")
    def read_root():
        """
        API Health Check
        
        Returns API status and links to documentation
        """
        features = ["Redis caching", "Multi-source job scraping", "User job tracking"]
        
        if settings.APP_MODE.value == "lightweight":
            features.extend(["Fast keyword search", "Location filtering"])
        else:
            features.extend(["Semantic search", "Vector similarity matching", "Cross-encoder reranking"])
            if settings.APP_MODE.value == "cloud-ml":
                features.append("HuggingFace cloud inference")
        
        return {
            "message": f"Job Search API is running in {settings.APP_MODE.value} mode",
            "docs": "Visit /docs for interactive API documentation",
            "version": "2.0.0",
            "mode": settings.APP_MODE.value,
            "features": features
        }
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)