"""
Application configuration management.

This module handles all configuration loading and validation.
"""

import os
from pathlib import Path
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from config/.env
config_dir = Path(__file__).parent.parent.parent.parent / "config"
env_file = config_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

class AppMode(Enum):
    """Application deployment modes"""
    LIGHTWEIGHT = "lightweight"  # Simple keyword search, no ML
    FULL_ML = "full-ml"          # Local embeddings + reranking
    CLOUD_ML = "cloud-ml"        # HF inference + reranking

class Settings:
    """Application settings container"""
    
    # Application Mode Configuration
    APP_MODE: AppMode = AppMode(os.getenv("APP_MODE", "full-ml"))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Pinecone Configuration (only needed for ML modes)
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "job-search-index")
    
    # Hugging Face Configuration (only for cloud-ml mode)
    HF_INFERENCE_API: Optional[str] = os.getenv("HF_INFERENCE_API")
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")
    HF_MODEL_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2
    
    # MongoDB Configuration (for user data and job tracking)
    MONGODB_CONNECTION_STRING: Optional[str] = os.getenv("MONGODB_CONNECTION_STRING")
    MONGODB_DATABASE_NAME: str = os.getenv("MONGODB_DATABASE_NAME", "job-search-app")
    
    # Scraping Configuration
    HN_HIRING_URL: str = os.getenv("HN_HIRING_URL", "https://news.ycombinator.com/item?id=42575537")
    REMOTEOK_API_URL: str = "https://remoteok.io/api"
    ARBEITNOW_API_URL: str = "https://www.arbeitnow.com/api/job-board-api"
    THEMUSE_API_URL: str = "https://www.themuse.com/api/public/jobs?category=Software%20Engineer&page=0"
    
    # Job Filtering Configuration
    JOB_FILTER_KEYWORDS: list = [
        "python", "javascript", "react", "node", "java", "go", "rust", 
        "machine learning", "ai", "data science"
    ]
    JOB_FILTER_LOCATIONS: list = [
        "remote", "san francisco", "new york", "london", "berlin", "toronto"
    ]
    JOB_EXCLUDE_KEYWORDS: list = ["unpaid", "internship", "volunteer"]
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration based on selected mode"""
        if cls.APP_MODE in [AppMode.FULL_ML, AppMode.CLOUD_ML]:
            if not cls.PINECONE_API_KEY:
                raise ValueError(f"{cls.APP_MODE.value} mode requires PINECONE_API_KEY")
        
        if cls.APP_MODE == AppMode.CLOUD_ML:
            if not cls.HF_INFERENCE_API or not cls.HF_TOKEN:
                raise ValueError("cloud-ml mode requires HF_INFERENCE_API and HF_TOKEN")

# Global settings instance
settings = Settings()

# Validate on import
settings.validate()