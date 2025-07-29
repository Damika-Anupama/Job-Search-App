import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "job-search-index")

# Hugging Face Configuration (currently for the mock, but ready for the real one)
HF_INFERENCE_API = os.getenv("HF_INFERENCE_API")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_DIMENSION = 768 # Dimension for nomic-embed-text-v1.5

# Scraping Configuration
HN_HIRING_URL = "https://news.ycombinator.com/item?id=42575537" # Jan 2025 thread
REMOTEOK_API_URL = "https://remoteok.io/api"  # Remote OK API
ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"  # Arbeit Now API
THEMUSE_API_URL = "https://www.themuse.com/api/public/jobs?category=Software%20Engineer&page=0"  # The Muse API

# Job Filtering Configuration
JOB_FILTER_KEYWORDS = ["python", "javascript", "react", "node", "java", "go", "rust", "machine learning", "ai", "data science"]
JOB_FILTER_LOCATIONS = ["remote", "san francisco", "new york", "london", "berlin", "toronto"]
JOB_EXCLUDE_KEYWORDS = ["unpaid", "internship", "volunteer"]