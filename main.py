from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import redis
import json
from config import REDIS_URL
from indexing import get_embedding, index as pinecone_index
from tasks import crawl_and_index
import re

# Initialize FastAPI app
app = FastAPI(
    title="Advanced Job Search API",
    description="""
    🚀 **AI-Powered Multi-Source Job Search Platform**
    
    Discover your perfect job with advanced semantic search and intelligent filtering across multiple job boards.
    
    **Data Sources:**
    - 🔥 Hacker News "Who is Hiring?" threads
    - 🌍 Remote OK (remote jobs)
    - 💼 Arbeit Now (European jobs)
    - 🎯 The Muse (curated positions)
    
    **Advanced Features:**
    - 🧠 **Semantic Search** - Find jobs by meaning, not just keywords
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required and preferred technologies
    - 📈 **Experience Levels** - Junior to senior positions
    - 🏢 **Company Size** - Startups to enterprise
    - 💰 **Salary Requirements** - Minimum compensation filtering
    - ⚡ **Smart Scoring** - Relevance boosting based on preferences
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Intelligent Caching** - Lightning-fast repeat searches
    
    Perfect for developers, data scientists, and tech professionals seeking their next opportunity!
    """,
    version="2.0.0"
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
    locations: List[str] = Field(
        default=[],
        description="Filter jobs by location (OR logic - any match included). Leave empty to search all locations.",
        examples=[["remote"], ["san francisco", "new york"], ["london", "berlin"]]
    )
    required_skills: List[str] = Field(
        default=[],
        description="Skills that MUST be present in the job (AND logic - all required). Use sparingly to avoid empty results.",
        examples=[["python"], ["react"], ["aws"]]
    )
    preferred_skills: List[str] = Field(
        default=[],
        description="Skills that boost relevance if present (OR logic - optional). Safe to use multiple.",
        examples=[["docker", "redis"], ["postgresql", "mongodb"], ["machine learning"]]
    )
    exclude_keywords: List[str] = Field(
        default=[],
        description="Keywords to exclude from results. Safe to use.",
        examples=[["internship", "unpaid"], ["on-site"], ["php"]]
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return (1-50)"
    )
    # Temporarily disable these advanced filters
    # min_salary: int = Field(
    #     default=0,
    #     description="Minimum salary requirement (0 = no minimum)",
    #     examples=[50000, 80000, 120000]
    # )
    # job_level: List[str] = Field(
    #     default=[],
    #     description="Job experience levels to include",
    #     examples=[["junior"], ["senior", "lead"], ["entry", "mid", "senior"]]
    # )
    # company_size: List[str] = Field(
    #     default=[],
    #     description="Preferred company sizes",
    #     examples=[["startup"], ["big tech", "enterprise"], ["startup", "mid-size"]]
    # )

class JobResult(BaseModel):
    id: str = Field(description="Unique job posting identifier")
    score: float = Field(description="Relevance score (0-1, higher is more relevant)")
    text: str = Field(description="Complete job posting text")

class SearchResponse(BaseModel):
    source: str = Field(description="Data source: 'cache' for cached results, 'pinecone' for fresh search")
    results: List[JobResult] = Field(description="List of relevant job postings")
    total_found: int = Field(description="Total number of jobs found before pagination")
    filters_applied: Dict[str, Any] = Field(description="Summary of filters that were applied")

def simplified_filter_jobs(jobs, request: SearchRequest):
    """
    Apply simplified filtering based on core user preferences.
    
    Args:
        jobs: List of job dictionaries from Pinecone search
        request: SearchRequest with filtering parameters
        
    Returns:
        Filtered and scored list of jobs
    """
    filtered_jobs = []
    
    for job in jobs:
        job_text_lower = job['metadata']['text'].lower()
        should_include = True
        relevance_boost = 0
        
        # Exclude jobs with blacklisted keywords (safe filter)
        if request.exclude_keywords:
            for exclude_keyword in request.exclude_keywords:
                if exclude_keyword.lower() in job_text_lower:
                    should_include = False
                    break
        
        if not should_include:
            continue
        
        # Check location requirements (OR logic)
        if request.locations:
            location_found = False
            for location in request.locations:
                if location.lower() in job_text_lower:
                    location_found = True
                    relevance_boost += 0.15
                    break
            if not location_found:
                continue
        
        # Check required skills (AND logic - be very careful here)
        if request.required_skills:
            all_required_found = True
            for skill in request.required_skills:
                if skill.lower() not in job_text_lower:
                    all_required_found = False
                    break
            if not all_required_found:
                continue
            else:
                relevance_boost += 0.25  # Big boost for having all required skills
        
        # Check preferred skills (OR logic - boost relevance if present)
        if request.preferred_skills:
            preferred_count = 0
            for skill in request.preferred_skills:
                if skill.lower() in job_text_lower:
                    preferred_count += 1
                    relevance_boost += 0.1  # Boost per preferred skill found
        
        # Apply relevance boost to original score
        boosted_score = min(1.0, job['score'] + relevance_boost)
        
        filtered_jobs.append({
            'id': job['id'],
            'score': boosted_score,
            'text': job['metadata']['text']
        })
    
    # Sort by boosted score (highest first) and limit results
    filtered_jobs.sort(key=lambda x: x['score'], reverse=True)
    
    return filtered_jobs[:request.max_results]

@app.post("/search", response_model=SearchResponse)
def search_jobs(request: SearchRequest):
    """
    Advanced semantic job search with personalized filtering.
    
    This endpoint performs semantic search across indexed job postings from multiple sources 
    including Hacker News, Remote OK, Arbeit Now, and The Muse. Results are filtered based 
    on your preferences and ranked by relevance score.
    
    **Enhanced Features:**
    - **Semantic search** - finds jobs by meaning, not just keywords
    - **Location filtering** - specify preferred locations (OR logic)
    - **Skills filtering** - required skills (AND) and preferred skills (OR) 
    - **Experience level** - filter by junior, mid, senior, lead positions
    - **Company size** - startup, mid-size, big tech, enterprise
    - **Salary filtering** - minimum salary requirements
    - **Exclusions** - block unwanted keywords (internship, unpaid, etc.)
    - **Smart scoring** - relevance boosting based on preferences
    - **Redis caching** - fast repeat queries
    
    **Example Advanced Searches:**
    ```json
    {
      "query": "python backend developer",
      "locations": ["remote", "san francisco"],
      "required_skills": ["python", "postgresql"],
      "preferred_skills": ["docker", "aws"],
      "job_level": ["senior"],
      "company_size": ["startup", "mid-size"],
      "min_salary": 120000,
      "exclude_keywords": ["php", "on-site"],
      "max_results": 15
    }
    ```
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection not available.")

    # Create cache key based on search parameters
    cache_params = {
        "query": request.query.lower().strip(),
        "locations": sorted(request.locations),
        "required_skills": sorted(request.required_skills),
        "preferred_skills": sorted(request.preferred_skills),
        "exclude_keywords": sorted(request.exclude_keywords),
        "max_results": request.max_results
    }
    cache_key = f"advanced_search:{hash(str(cache_params))}"

    # 1. Check cache first
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            print(f"Cache HIT for advanced query")
            cached_data = json.loads(cached_result)
            return {
                "source": "cache", 
                "results": cached_data["results"],
                "total_found": cached_data["total_found"],
                "filters_applied": cached_data["filters_applied"]
            }
    except redis.exceptions.RedisError as e:
        print(f"Redis cache read error: {e}")

    print(f"Cache MISS for advanced query: '{request.query}'")

    # 2. If not in cache, perform the search
    query_vector = get_embedding(request.query)

    # Query Pinecone with more results to allow for filtering
    search_top_k = min(100, request.max_results * 5)  # Get extra results for filtering
    
    try:
        search_result = pinecone_index.query(
            vector=query_vector,
            top_k=search_top_k,
            include_metadata=True
        )
        
        if not search_result['matches']:
            return {
                "source": "pinecone", 
                "results": [],
                "total_found": 0,
                "filters_applied": cache_params
            }
        
        total_found = len(search_result['matches'])
        
        # Apply simplified filtering
        filtered_results = simplified_filter_jobs(search_result['matches'], request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying Pinecone: {e}")

    # 3. Prepare response data
    response_data = {
        "source": "pinecone",
        "results": filtered_results,
        "total_found": total_found,
        "filters_applied": cache_params
    }

    # 4. Store the result in cache
    try:
        redis_client.set(cache_key, json.dumps({
            "results": filtered_results,
            "total_found": total_found,
            "filters_applied": cache_params
        }), ex=1800)  # Cache for 30 minutes (shorter for personalized results)
    except redis.exceptions.RedisError as e:
        print(f"Redis cache write error: {e}")

    return response_data

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