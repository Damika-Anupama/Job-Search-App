from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import redis
import json
from config import REDIS_URL
from indexing import get_embedding, index as pinecone_index
from tasks import crawl_and_index

# Initialize FastAPI app
app = FastAPI(
    title="Job Search API",
    description="AI-powered semantic job search system that scrapes and indexes job postings from Hacker News 'Who is Hiring?' threads",
    version="1.0.0"
)

# Connect to Redis for caching
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None

# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(
        ..., 
        description="Search query to find relevant job postings",
        examples=[
            "python developer remote",
            "machine learning AI engineer",
            "frontend react javascript",
            "backend rust systems programming",
            "startup founding engineer",
            "data scientist remote"
        ]
    )

class JobResult(BaseModel):
    id: str = Field(description="Unique job posting identifier")
    score: float = Field(description="Relevance score (0-1, higher is more relevant)")
    text: str = Field(description="Complete job posting text")

class SearchResponse(BaseModel):
    source: str = Field(description="Data source: 'cache' for cached results, 'pinecone' for fresh search")
    results: List[JobResult] = Field(description="List of relevant job postings")

@app.post("/search", response_model=SearchResponse)
def search_jobs(request: SearchRequest):
    """
    Search for job postings using semantic similarity.
    
    This endpoint performs semantic search across indexed job postings from Hacker News 
    "Who is Hiring?" threads. Results are ranked by relevance score and cached for performance.
    
    **Features:**
    - Semantic search (finds jobs by meaning, not just keywords)
    - Redis caching for fast repeat queries
    - Returns top 5 most relevant results
    - Includes relevance scores
    
    **Example queries:**
    - "python developer remote" - Find remote Python positions
    - "machine learning startup" - Find ML roles at startups  
    - "frontend react" - Find React frontend positions
    - "backend rust systems" - Find systems programming roles
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection not available.")

    cache_key = f"search:{request.query.lower().strip()}"

    # 1. Check cache first
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            print(f"Cache HIT for query: '{request.query}'")
            return {"source": "cache", "results": json.loads(cached_result)}
    except redis.exceptions.RedisError as e:
        print(f"Redis cache read error: {e}")

    print(f"Cache MISS for query: '{request.query}'")

    # 2. If not in cache, perform the search
    # Get the embedding for the query (using our mock function)
    query_vector = get_embedding(request.query)

    # Query Pinecone
    try:
        search_result = pinecone_index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True
        )
        results = [{"id": match['id'], "score": match['score'], "text": match['metadata']['text']} for match in search_result['matches']]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying Pinecone: {e}")

    # 3. Store the result in cache
    try:
        redis_client.set(cache_key, json.dumps(results), ex=3600) # Cache for 1 hour
    except redis.exceptions.RedisError as e:
        print(f"Redis cache write error: {e}")

    return {"source": "pinecone", "results": results}

@app.get("/", 
    summary="API Health Check",
    description="Returns API status and links to documentation"
)
def read_root():
    """
    Health check endpoint that confirms the API is running.
    
    **Returns:**
    - API status message
    - Link to interactive documentation
    """
    return {
        "message": "Job Search API is running", 
        "docs": "Visit /docs for interactive API documentation",
        "version": "1.0.0",
        "features": [
            "Semantic job search",
            "Redis caching",
            "Hacker News job scraping",
            "Vector similarity matching"
        ]
    }

@app.post("/trigger-indexing", status_code=202)
def trigger_indexing_job():
    """
    Triggers the background task to scrape and index jobs.
    Returns immediately with a 202 Accepted response.
    """
    print("Received request to trigger indexing job.")
    crawl_and_index.delay() # Use .delay() to send the task to the Celery worker
    return {"message": "Job indexing task has been triggered and is running in the background."}