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
HF_MODEL_DIMENSION = 768 # Dimension for nomic-embed-text-v1.5

# Scraping Configuration
HN_HIRING_URL = "https://news.ycombinator.com/item?id=42575537" # Jan 2025 thread