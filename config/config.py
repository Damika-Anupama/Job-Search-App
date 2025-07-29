import os
from dotenv import load_dotenv
from enum import Enum

# Load environment variables from .env file
load_dotenv()

class AppMode(Enum):
    LIGHTWEIGHT = "lightweight"  # Simple keyword search, no ML
    FULL_ML = "full-ml"          # Local embeddings + reranking
    CLOUD_ML = "cloud-ml"        # HF inference + reranking

# Application Mode Configuration
APP_MODE = AppMode(os.getenv("APP_MODE", "full-ml"))

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Pinecone Configuration (only needed for ML modes)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "job-search-index")

# Hugging Face Configuration (only for cloud-ml mode)
HF_INFERENCE_API = os.getenv("HF_INFERENCE_API")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_DIMENSION = 384 # Dimension for all-MiniLM-L6-v2 (local) / sentence-transformers default

# MongoDB Configuration (for user data and job tracking)
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "job-search-app")

# Mode validation
def validate_mode_config():
    """Validate configuration based on selected mode"""
    if APP_MODE in [AppMode.FULL_ML, AppMode.CLOUD_ML]:
        if not PINECONE_API_KEY:
            raise ValueError(f"{APP_MODE.value} mode requires PINECONE_API_KEY")
    
    if APP_MODE == AppMode.CLOUD_ML:
        if not HF_INFERENCE_API or not HF_TOKEN:
            raise ValueError("cloud-ml mode requires HF_INFERENCE_API and HF_TOKEN")

# Validate on import
validate_mode_config()

# Scraping Configuration
HN_HIRING_URL = "https://news.ycombinator.com/item?id=42575537" # Jan 2025 thread
REMOTEOK_API_URL = "https://remoteok.io/api"  # Remote OK API
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"  # Arbeit Now API
THEMUSE_API_URL = "https://www.themuse.com/api/public/jobs?category=Software%20Engineer&page=0"  # The Muse API

# Job Filtering Configuration
JOB_FILTER_KEYWORDS = ["python", "javascript", "react", "node", "java", "go", "rust", "machine learning", "ai", "data science"]
JOB_FILTER_LOCATIONS = ["remote", "san francisco", "new york", "london", "berlin", "toronto"]
JOB_EXCLUDE_KEYWORDS = ["unpaid", "internship", "volunteer"]