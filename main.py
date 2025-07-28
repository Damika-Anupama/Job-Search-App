from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import json
from config import REDIS_URL
from indexing import get_embedding, index as pinecone_index

# Initialize FastAPI app
app = FastAPI(title="Job Search API")

# Connect to Redis for caching
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None

# Pydantic model for the search query
class SearchRequest(BaseModel):
    query: str

@app.post("/search")
def search_jobs(request: SearchRequest):
    """
    Accepts a search query, and returns the most relevant job postings.
    Uses Redis for caching search results.
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

@app.get("/")
def read_root():
    return {"message": "Job Search API is running. Go to /docs to see the endpoints."}