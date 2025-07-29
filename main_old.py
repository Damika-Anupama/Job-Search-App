from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import redis
import json
from config import REDIS_URL, APP_MODE, AppMode
from embedding_service import embedding_service, EmbeddingServiceError
from mongodb_service import mongodb_service, MongoDBServiceError
from tasks import crawl_and_index
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conditional imports based on mode
if APP_MODE in [AppMode.FULL_ML, AppMode.CLOUD_ML]:
    from indexing import get_embedding, index as pinecone_index
    from reranker import rerank_search_results
else:
    pinecone_index = None
    rerank_search_results = None

# Generate mode-specific description
def get_app_description():
    base_desc = """🚀 **Multi-Source Job Search Platform**
    
    Discover your perfect job with intelligent filtering across multiple job boards.
    
    **Data Sources:**
    - 🔥 Hacker News "Who is Hiring?" threads
    - 🌍 Remote OK (remote jobs)
    - 💼 Arbeit Now (European jobs)
    - 🎯 The Muse (curated positions)
    """
    
    if APP_MODE == AppMode.LIGHTWEIGHT:
        return base_desc + """
    **🚀 LIGHTWEIGHT MODE**
    - ⚡ **Fast Keyword Search** - Simple text matching
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required skills filtering
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Redis Caching** - Fast repeat searches
        """
    elif APP_MODE == AppMode.FULL_ML:
        return base_desc + """
    **🧠 FULL ML MODE (Local)**
    - 🔍 **Semantic Search** - Find jobs by meaning using local ML models
    - 🎯 **Cross-Encoder Reranking** - Advanced relevance scoring
    - 📍 **Location Filtering** - Remote, specific cities, or regions
    - 🛠️ **Skills Matching** - Required and preferred technologies
    - ⚡ **Smart Scoring** - Relevance boosting based on preferences
    - 🚫 **Keyword Exclusions** - Block unwanted job types
    - 💾 **Intelligent Caching** - Lightning-fast repeat searches
        """
    else:  # CLOUD_ML
        return base_desc + """
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

# Initialize FastAPI app
app = FastAPI(
    title=f"Job Search API ({APP_MODE.value.upper()})",
    description=get_app_description(),
    version="3.0.0"
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
    score: float = Field(description="Final relevance score (cross-encoder reranked)")
    text: str = Field(description="Complete job posting text")
    vector_score: float = Field(default=0.0, description="Original vector similarity score")
    cross_score: float = Field(default=0.0, description="Cross-encoder reranking score")

class SearchResponse(BaseModel):
    source: str = Field(description="Data source: 'cache' for cached results, 'pinecone' for fresh search")
    results: List[JobResult] = Field(description="List of relevant job postings (reranked by cross-encoder)")
    total_found: int = Field(description="Total number of jobs found before pagination")
    filters_applied: Dict[str, Any] = Field(description="Summary of filters that were applied")
    reranked: bool = Field(default=False, description="Whether results were reranked using cross-encoder")
    candidates_retrieved: int = Field(default=0, description="Number of candidates retrieved for reranking")

# User tracking models
class SaveJobRequest(BaseModel):
    job_id: str = Field(description="Unique identifier of the job to save")
    job_data: Dict[str, Any] = Field(description="Complete job data including text, metadata, etc.")

class UpdateJobStatusRequest(BaseModel):
    status: str = Field(
        description="New status for the job",
        examples=["saved", "applied", "interviewing", "offered", "rejected", "withdrawn"]
    )
    notes: Optional[str] = Field(default="", description="Optional notes about the status change")

class SavedJob(BaseModel):
    job_id: str = Field(description="Unique identifier of the saved job")
    saved_at: datetime = Field(description="When the job was saved")
    status: str = Field(description="Current status of the job application")
    notes: str = Field(description="User notes about this job")
    job_data: Dict[str, Any] = Field(description="Complete job information")
    application_date: Optional[datetime] = Field(default=None, description="Date when applied (if status is applied)")
    interview_dates: List[datetime] = Field(default=[], description="List of interview dates")
    updated_at: datetime = Field(description="Last time this job was updated")

class SavedJobsResponse(BaseModel):
    user_id: str = Field(description="User identifier")
    total_saved: int = Field(description="Total number of saved jobs")
    jobs: List[SavedJob] = Field(description="List of saved jobs")
    statistics: Dict[str, Any] = Field(description="Job application statistics")

class UserStatsResponse(BaseModel):
    user_id: str = Field(description="User identifier")
    total_jobs: int = Field(description="Total number of saved jobs")
    by_status: Dict[str, int] = Field(description="Count of jobs by status")
    recent_activity: int = Field(description="Number of jobs updated in last 7 days")

def lightweight_search_jobs(request: SearchRequest):
    """
    Simple keyword-based search for lightweight mode (no ML/vector search).
    Searches cached job data using keyword matching.
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection required for lightweight search")
    
    try:
        # Get all cached jobs (in a real implementation, you'd want a proper job storage)
        # For now, we'll return a message indicating lightweight mode limitations
        return {
            "source": "lightweight",
            "results": [],
            "total_found": 0,
            "filters_applied": {
                "query": request.query,
                "locations": request.locations,
                "required_skills": request.required_skills,
                "exclude_keywords": request.exclude_keywords
            },
            "reranked": False,
            "candidates_retrieved": 0,
            "message": "Lightweight mode: Vector search disabled. Use trigger-indexing endpoint to populate simple keyword search."
        }
    except Exception as e:
        logger.error(f"Lightweight search error: {e}")
        raise HTTPException(status_code=500, detail=f"Lightweight search error: {e}")

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
    🚀 **Job Search with Mode-Specific Processing**
    
    This endpoint adapts its behavior based on the current application mode:
    
    **🚀 LIGHTWEIGHT MODE:**
    - Simple keyword-based search
    - No ML processing or vector embeddings
    - Fast response times with basic filtering
    
    **🧠 FULL ML MODE:**
    - Local semantic vector search with sentence transformers
    - Cross-encoder reranking for improved relevance
    - Two-stage search: broad retrieval + precise reranking
    
    **☁️ CLOUD ML MODE:**
    - HuggingFace Inference API for embeddings
    - Automatic fallback to local models if cloud fails
    - Cross-encoder reranking with detailed health monitoring
    
    **✨ Common Features:**
    - **Smart filtering** - Location, skills, keyword exclusions
    - **Relevance boosting** - Preferred skills increase scores  
    - **Intelligent caching** - Fast repeat queries
    - **Health monitoring** - Component status tracking
    
    **Example Search:**
    ```json
    {
      "query": "python backend developer remote",
      "locations": ["remote"],
      "required_skills": ["python"],
      "preferred_skills": ["django", "docker", "aws"],
      "exclude_keywords": ["internship", "unpaid"],
      "max_results": 10
    }
    ```
    """
    
    # Handle lightweight mode separately
    if APP_MODE == AppMode.LIGHTWEIGHT:
        return lightweight_search_jobs(request)
    
    # For ML modes, ensure required components are available
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection not available.")
    
    if not pinecone_index:
        raise HTTPException(status_code=503, detail="Vector search not available - Pinecone index not initialized.")

    # Create cache key based on search parameters
    cache_params = {
        "query": request.query.lower().strip(),
        "locations": sorted(request.locations),
        "required_skills": sorted(request.required_skills),
        "preferred_skills": sorted(request.preferred_skills),
        "exclude_keywords": sorted(request.exclude_keywords),
        "max_results": request.max_results,
        "mode": APP_MODE.value
    }
    cache_key = f"search_{APP_MODE.value}:{hash(str(cache_params))}"

    # 1. Check cache first
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache HIT for {APP_MODE.value} query")
            cached_data = json.loads(cached_result)
            return {
                "source": "cache", 
                "results": cached_data["results"],
                "total_found": cached_data["total_found"],
                "filters_applied": cached_data["filters_applied"],
                "reranked": cached_data.get("reranked", False),
                "candidates_retrieved": cached_data.get("candidates_retrieved", 0)
            }
    except redis.exceptions.RedisError as e:
        logger.warning(f"Redis cache read error: {e}")

    logger.info(f"Cache MISS for {APP_MODE.value} query: '{request.query}'")

    # 2. Generate embedding with mode-specific handling
    try:
        # For cloud-ml mode, don't use fallback in search to surface real HF inference issues
        fallback = False
        query_vector = embedding_service.get_embedding(request.query, fallback=fallback)
    except EmbeddingServiceError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")

    # Stage 1: Broad candidate retrieval from Pinecone
    # Get more candidates than needed for reranking (candidate selection stage)
    candidate_top_k = min(100, max(50, request.max_results * 8))  # Get 8x more candidates for reranking
    
    try:
        print(f"Stage 1: Retrieving {candidate_top_k} candidates from vector search")
        search_result = pinecone_index.query(
            vector=query_vector,
            top_k=candidate_top_k,
            include_metadata=True
        )
        
        if not search_result['matches']:
            return {
                "source": "pinecone", 
                "results": [],
                "total_found": 0,
                "filters_applied": cache_params,
                "reranked": False,
                "candidates_retrieved": 0
            }
        
        total_found = len(search_result['matches'])
        print(f"Retrieved {total_found} candidates from vector search")
        
        # Apply simplified filtering first (before reranking to reduce compute)
        filtered_candidates = simplified_filter_jobs(search_result['matches'], 
                                                   # Get more results for reranking
                                                   type('TempRequest', (), {**request.__dict__, 'max_results': min(50, len(search_result['matches']))})())
        
        if not filtered_candidates:
            return {
                "source": "pinecone", 
                "results": [],
                "total_found": total_found,
                "filters_applied": cache_params,
                "reranked": False,
                "candidates_retrieved": total_found
            }
        
        print(f"Stage 2: Reranking {len(filtered_candidates)} filtered candidates")
        
        # Stage 2: Cross-encoder reranking for precise relevance scoring
        reranked_results = rerank_search_results(
            query=request.query, 
            jobs=filtered_candidates, 
            top_k=request.max_results
        )
        
        print(f"Reranking complete: returning top {len(reranked_results)} results")
        
        # Format results for API response
        final_results = []
        for job in reranked_results:
            final_results.append({
                'id': job['id'],
                'score': job.get('cross_score', job.get('score', 0.0)),
                'text': job.get('metadata', {}).get('text', job.get('text', '')),
                'vector_score': job.get('vector_score', job.get('score', 0.0)),
                'cross_score': job.get('cross_score', job.get('score', 0.0))
            })
        
        # Prepare response
        response_data = {
            "source": "pinecone",
            "results": final_results,
            "total_found": total_found,
            "filters_applied": cache_params,
            "reranked": True,
            "candidates_retrieved": len(filtered_candidates)
        }
        
        # Cache the reranked results
        try:
            redis_client.set(cache_key, json.dumps({
                "results": final_results,
                "total_found": total_found,
                "filters_applied": cache_params,
                "reranked": True,
                "candidates_retrieved": len(filtered_candidates)
            }), ex=1800)  # Cache for 30 minutes
        except redis.exceptions.RedisError as e:
            print(f"Redis cache write error: {e}")
        
        return response_data
        
    except Exception as e:
        print(f"Error in two-stage search: {e}")
        raise HTTPException(status_code=500, detail=f"Error in search pipeline: {e}")

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
    features = ["Redis caching", "Multi-source job scraping"]
    
    if APP_MODE == AppMode.LIGHTWEIGHT:
        features.extend(["Fast keyword search", "Location filtering"])
    else:
        features.extend(["Semantic search", "Vector similarity matching", "Cross-encoder reranking"])
        if APP_MODE == AppMode.CLOUD_ML:
            features.append("HuggingFace cloud inference")
    
    return {
        "message": f"Job Search API is running in {APP_MODE.value} mode", 
        "docs": "Visit /docs for interactive API documentation",
        "version": "3.0.0",
        "mode": APP_MODE.value,
        "features": features
    }

@app.get("/health", 
    summary="System Health Check",
    description="Comprehensive health check of all system components"
)
def health_check():
    """
    Comprehensive health check endpoint.
    
    **Returns:**
    - Overall system status
    - Individual component health
    - Mode-specific diagnostics
    """
    health_status = {
        "status": "healthy",
        "mode": APP_MODE.value,
        "components": {}
    }
    
    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            health_status["components"]["redis"] = {"status": "healthy", "message": "Connected"}
        else:
            health_status["components"]["redis"] = {"status": "unhealthy", "message": "Not connected"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["redis"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "degraded"
    
    # Check embedding service
    embedding_health = embedding_service.health_check()
    health_status["components"]["embedding_service"] = embedding_health
    
    if embedding_health["status"] in ["unhealthy", "degraded"]:
        health_status["status"] = embedding_health["status"]
    
    # Check Pinecone (for ML modes)
    if APP_MODE in [AppMode.FULL_ML, AppMode.CLOUD_ML]:
        try:
            if pinecone_index:
                # Simple index stats check
                stats = pinecone_index.describe_index_stats()
                health_status["components"]["pinecone"] = {
                    "status": "healthy",
                    "total_vectors": stats.get("total_vector_count", 0),
                    "namespaces": len(stats.get("namespaces", {}))
                }
            else:
                health_status["components"]["pinecone"] = {"status": "unhealthy", "message": "Index not initialized"}
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["components"]["pinecone"] = {"status": "unhealthy", "message": str(e)}
            health_status["status"] = "unhealthy"
    
    # Check MongoDB
    if mongodb_service:
        mongodb_health = mongodb_service.health_check()
        health_status["components"]["mongodb"] = mongodb_health
        
        if mongodb_health["status"] != "healthy":
            health_status["status"] = "degraded"
    else:
        health_status["components"]["mongodb"] = {"status": "unhealthy", "message": "MongoDB service not initialized"}
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/health/embedding", 
    summary="Embedding Service Health",
    description="Detailed health check for embedding service"
)
def embedding_health():
    """
    Detailed embedding service health check.
    
    **Returns:**
    - Embedding service status
    - Mode-specific diagnostics  
    - API availability (for cloud mode)
    """
    return embedding_service.health_check()

@app.post("/trigger-indexing", status_code=202)
def trigger_indexing_job():
    """
    Triggers the background task to scrape and index jobs.
    Returns immediately with a 202 Accepted response.
    """
    print("Received request to trigger indexing job.")
    crawl_and_index.delay() # Use .delay() to send the task to the Celery worker
    return {"message": "Job indexing task has been triggered and is running in the background."}

# User tracking endpoints
@app.post("/users/{user_id}/saved-jobs", status_code=201)
def save_job_for_user(user_id: str, request: SaveJobRequest):
    """
    💾 **Save a Job for User Tracking**
    
    Allows users to save jobs to their personal tracking list for later reference.
    This transforms the application from just a search engine into a personalized job tracker.
    
    **Features:**
    - 📌 **Personal Job Lists** - Save interesting jobs to review later
    - 📊 **Application Tracking** - Track your job application journey
    - 🔍 **Job Data Storage** - Full job details preserved for offline viewing
    - ⏰ **Timestamp Tracking** - Know when you saved each job
    
    **What gets saved:**
    - Complete job posting text and metadata
    - Timestamp when job was saved
    - Initial status set to "saved"
    - User-specific tracking information
    
    **Example Request:**
    ```json
    {
      "job_id": "ro_1093607",
      "job_data": {
        "text": "Python Backend Developer at Example Corp...",
        "score": 0.95,
        "vector_score": 0.88,
        "cross_score": 0.95
      }
    }
    ```
    
    The job will be added to your personal tracking dashboard where you can:
    - Update application status (applied, interviewing, etc.)
    - Add personal notes
    - Track application timeline
    """
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.save_job(user_id, request.job_id, request.job_data)
        if success:
            return {
                "message": f"Job {request.job_id} saved successfully for user {user_id}",
                "job_id": request.job_id,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save job")
            
    except MongoDBServiceError as e:
        if "already saved" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/saved-jobs", response_model=SavedJobsResponse)
def get_saved_jobs_for_user(user_id: str, status: Optional[str] = None):
    """
    📋 **Get User's Saved Jobs**
    
    Retrieve all jobs that a user has saved, with optional filtering by application status.
    This endpoint provides a complete view of the user's job application pipeline.
    
    **Features:**
    - 📱 **Complete Job Dashboard** - See all your saved jobs in one place
    - 🔍 **Status Filtering** - Filter by application stage
    - 📊 **Application Statistics** - Get insights into your job search progress
    - 📅 **Timeline View** - Jobs sorted by most recently saved
    
    **Status Filters Available:**
    - `saved` - Jobs you've bookmarked but haven't applied to yet
    - `applied` - Jobs where you've submitted applications
    - `interviewing` - Jobs where you're in the interview process
    - `offered` - Jobs where you've received offers
    - `rejected` - Applications that weren't successful
    - `withdrawn` - Applications you've withdrawn
    
    **Response includes:**
    - Complete job details for offline viewing
    - Application timeline and status history
    - Personal notes and reminders
    - Statistics about your job search progress
    
    **Example Usage:**
    - `GET /users/john123/saved-jobs` - All saved jobs
    - `GET /users/john123/saved-jobs?status=applied` - Only applied jobs
    - `GET /users/john123/saved-jobs?status=interviewing` - Jobs in interview stage
    """
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        saved_jobs = mongodb_service.get_saved_jobs(user_id, status)
        stats = mongodb_service.get_job_stats(user_id)
        
        return SavedJobsResponse(
            user_id=user_id,
            total_saved=len(saved_jobs),
            jobs=saved_jobs,
            statistics=stats
        )
        
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/users/{user_id}/saved-jobs/{job_id}")
def update_job_status_for_user(user_id: str, job_id: str, request: UpdateJobStatusRequest):
    """
    ✏️ **Update Job Application Status**
    
    Update the status of a saved job as you progress through the application process.
    This endpoint is crucial for tracking your job search journey and staying organized.
    
    **Status Progression Examples:**
    1. **saved** → **applied** (when you submit application)
    2. **applied** → **interviewing** (when you get interview calls)
    3. **interviewing** → **offered** (when you receive job offer)
    4. **interviewing** → **rejected** (when application doesn't succeed)
    5. **applied** → **withdrawn** (when you withdraw application)
    
    **Available Statuses:**
    - 📌 **saved** - Job is bookmarked for future action
    - 📝 **applied** - Application has been submitted
    - 🎤 **interviewing** - In interview process (phone, video, onsite)
    - 🎉 **offered** - Job offer received
    - ❌ **rejected** - Application was not successful
    - 🚫 **withdrawn** - You withdrew your application
    
    **Features:**
    - ⏰ **Automatic Timestamps** - Application date tracked when status = "applied"
    - 📝 **Personal Notes** - Add context about status changes
    - 📊 **Progress Tracking** - Monitor your application pipeline
    - 🔄 **Status History** - Keep track of all changes
    
    **Example Request:**
    ```json
    {
      "status": "applied",
      "notes": "Applied through company website. Great culture fit!"
    }
    ```
    
    **Pro Tips:**
    - Use notes to track important details (interview feedback, salary discussions)
    - Update status promptly to maintain accurate pipeline view
    - Review your statistics to identify areas for improvement
    """
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.update_job_status(
            user_id, 
            job_id, 
            request.status, 
            request.notes
        )
        
        if success:
            return {
                "message": f"Job {job_id} status updated to '{request.status}' for user {user_id}",
                "job_id": job_id,
                "user_id": user_id,
                "new_status": request.status,
                "notes": request.notes
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update job status")
            
    except MongoDBServiceError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "Invalid status" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.delete("/users/{user_id}/saved-jobs/{job_id}")
def remove_saved_job_for_user(user_id: str, job_id: str):
    """
    🗑️ **Remove Saved Job**
    
    Remove a job from your saved jobs list. This is useful for cleaning up your 
    job tracker when positions are no longer relevant.
    
    **When to use:**
    - Job posting has expired or been filled
    - You're no longer interested in the position
    - Company/role doesn't match your criteria anymore
    - Cleaning up old saved jobs
    
    **Note:** This action cannot be undone. The job and all associated tracking 
    data (status, notes, timeline) will be permanently removed.
    """
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        success = mongodb_service.remove_saved_job(user_id, job_id)
        
        if success:
            return {
                "message": f"Job {job_id} removed from saved jobs for user {user_id}",
                "job_id": job_id,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found in saved jobs for user {user_id}")
            
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/stats", response_model=UserStatsResponse)
def get_user_job_stats(user_id: str):
    """
    📊 **Get Job Search Statistics**
    
    Get comprehensive statistics about your job search progress. Perfect for 
    tracking your application pipeline and identifying areas for improvement.
    
    **Statistics Include:**
    - **Total Jobs Saved** - Overall count of jobs in your tracker
    - **Status Breakdown** - Count of jobs at each application stage
    - **Recent Activity** - Jobs updated in the last 7 days
    - **Application Pipeline** - Visual overview of your job search progress
    
    **Use Cases:**
    - Track your job search velocity
    - Identify bottlenecks in your application process
    - Monitor application success rates
    - Generate progress reports for career coaching
    - Set goals for weekly application targets
    
    **Example Response:**
    ```json
    {
      "user_id": "john123",
      "total_jobs": 25,
      "by_status": {
        "saved": 10,
        "applied": 8,
        "interviewing": 4,
        "offered": 2,
        "rejected": 1
      },
      "recent_activity": 5
    }
    ```
    """
    if not mongodb_service:
        raise HTTPException(status_code=503, detail="User tracking service unavailable")
    
    try:
        stats = mongodb_service.get_job_stats(user_id)
        
        return UserStatsResponse(
            user_id=user_id,
            total_jobs=stats["total"],
            by_status=stats["by_status"],
            recent_activity=stats["recent_activity"]
        )
        
    except MongoDBServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))