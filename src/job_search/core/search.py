"""
Core search functionality.

This module handles the main search logic with mode-specific processing.
"""

import json
import logging
from typing import Dict, Any, List
import redis
from fastapi import HTTPException

from .config import settings, AppMode
from ..api.models import SearchRequest, SearchResponse, JobResult
from ..ml.embeddings import embedding_service, EmbeddingServiceError
from ..db.redis_client import redis_client

logger = logging.getLogger(__name__)

class SearchService:
    """Main search service that handles all search modes"""
    
    def __init__(self):
        self.redis_client = redis_client
        
        # Import ML components only if needed
        if settings.APP_MODE in [AppMode.FULL_ML, AppMode.CLOUD_ML]:
            try:
                from ..ml.indexing import get_embedding, index as pinecone_index
                from ..ml.reranking import rerank_search_results
                self.pinecone_index = pinecone_index
                self.rerank_search_results = rerank_search_results
            except ImportError as e:
                logger.error(f"Failed to import ML components: {e}")
                self.pinecone_index = None
                self.rerank_search_results = None
        else:
            self.pinecone_index = None
            self.rerank_search_results = None
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Main search entry point that routes to appropriate search method
        """
        if settings.APP_MODE == AppMode.LIGHTWEIGHT:
            return self._lightweight_search(request)
        else:
            return self._ml_search(request)
    
    def _lightweight_search(self, request: SearchRequest) -> SearchResponse:
        """
        Simple keyword-based search for lightweight mode (no ML/vector search).
        """
        if not self.redis_client:
            raise HTTPException(status_code=503, detail="Redis connection required for lightweight search")
        
        try:
            # In a real implementation, you'd search through cached job data
            return SearchResponse(
                source="lightweight",
                results=[],
                total_found=0,
                filters_applied={
                    "query": request.query,
                    "locations": request.locations,
                    "required_skills": request.required_skills,
                    "exclude_keywords": request.exclude_keywords
                },
                reranked=False,
                candidates_retrieved=0
            )
        except Exception as e:
            logger.error(f"Lightweight search error: {e}")
            raise HTTPException(status_code=500, detail=f"Lightweight search error: {e}")
    
    def _ml_search(self, request: SearchRequest) -> SearchResponse:
        """
        ML-powered search with vector similarity and reranking
        """
        if not self.redis_client:
            raise HTTPException(status_code=503, detail="Redis connection not available.")
        
        if not self.pinecone_index:
            raise HTTPException(status_code=503, detail="Vector search not available - Pinecone index not initialized.")

        # Create cache key
        cache_params = self._build_cache_params(request)
        cache_key = f"search_{settings.APP_MODE.value}:{hash(str(cache_params))}"

        # 1. Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        logger.info(f"Cache MISS for {settings.APP_MODE.value} query: '{request.query}'")

        # 2. Generate embedding
        try:
            query_vector = embedding_service.get_embedding(request.query, fallback=False)
        except EmbeddingServiceError as e:
            logger.error(f"Embedding generation failed: {e}")
            raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")

        # 3. Vector search
        candidate_top_k = min(100, max(50, request.max_results * 8))
        
        try:
            search_result = self.pinecone_index.query(
                vector=query_vector,
                top_k=candidate_top_k,
                include_metadata=True
            )
            
            if not search_result['matches']:
                return self._empty_response(cache_params)
            
            total_found = len(search_result['matches'])
            
            # 4. Apply filtering
            filtered_candidates = self._filter_jobs(search_result['matches'], request)
            
            if not filtered_candidates:
                return SearchResponse(
                    source="pinecone",
                    results=[],
                    total_found=total_found,
                    filters_applied=cache_params,
                    reranked=False,
                    candidates_retrieved=total_found
                )
            
            # 5. Rerank results
            reranked_results = self.rerank_search_results(
                query=request.query,
                jobs=filtered_candidates,
                top_k=request.max_results
            )
            
            # 6. Format and cache results
            final_results = self._format_results(reranked_results)
            response_data = SearchResponse(
                source="pinecone",
                results=final_results,
                total_found=total_found,
                filters_applied=cache_params,
                reranked=True,
                candidates_retrieved=len(filtered_candidates)
            )
            
            self._cache_result(cache_key, response_data)
            return response_data
            
        except Exception as e:
            logger.error(f"Error in ML search: {e}")
            raise HTTPException(status_code=500, detail=f"Error in search pipeline: {e}")
    
    def _build_cache_params(self, request: SearchRequest) -> Dict[str, Any]:
        """Build cache parameters dictionary"""
        return {
            "query": request.query.lower().strip(),
            "locations": sorted(request.locations),
            "required_skills": sorted(request.required_skills),
            "preferred_skills": sorted(request.preferred_skills),
            "exclude_keywords": sorted(request.exclude_keywords),
            "max_results": request.max_results,
            "mode": settings.APP_MODE.value
        }
    
    def _get_cached_result(self, cache_key: str) -> SearchResponse:
        """Get cached search result"""
        try:
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache HIT for {settings.APP_MODE.value} query")
                cached_data = json.loads(cached_result)
                return SearchResponse(
                    source="cache",
                    results=[JobResult(**result) for result in cached_data["results"]],
                    total_found=cached_data["total_found"],
                    filters_applied=cached_data["filters_applied"],
                    reranked=cached_data.get("reranked", False),
                    candidates_retrieved=cached_data.get("candidates_retrieved", 0)
                )
        except redis.exceptions.RedisError as e:
            logger.warning(f"Redis cache read error: {e}")
        return None
    
    def _cache_result(self, cache_key: str, response: SearchResponse) -> None:
        """Cache search result"""
        try:
            cache_data = {
                "results": [result.dict() for result in response.results],
                "total_found": response.total_found,
                "filters_applied": response.filters_applied,
                "reranked": response.reranked,
                "candidates_retrieved": response.candidates_retrieved
            }
            self.redis_client.set(cache_key, json.dumps(cache_data), ex=1800)  # Cache for 30 minutes
        except redis.exceptions.RedisError as e:
            logger.warning(f"Redis cache write error: {e}")
    
    def _filter_jobs(self, jobs: List[Dict], request: SearchRequest) -> List[Dict]:
        """Apply filtering logic to job results"""
        filtered_jobs = []
        
        for job in jobs:
            job_text_lower = job['metadata']['text'].lower()
            should_include = True
            relevance_boost = 0
            
            # Exclude jobs with blacklisted keywords
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
            
            # Check required skills (AND logic)
            if request.required_skills:
                all_required_found = True
                for skill in request.required_skills:
                    if skill.lower() not in job_text_lower:
                        all_required_found = False
                        break
                if not all_required_found:
                    continue
                else:
                    relevance_boost += 0.25
            
            # Check preferred skills (OR logic)
            if request.preferred_skills:
                for skill in request.preferred_skills:
                    if skill.lower() in job_text_lower:
                        relevance_boost += 0.1
            
            # Apply relevance boost
            boosted_score = min(1.0, job['score'] + relevance_boost)
            
            filtered_jobs.append({
                'id': job['id'],
                'score': boosted_score,
                'text': job['metadata']['text']
            })
        
        # Sort by boosted score
        filtered_jobs.sort(key=lambda x: x['score'], reverse=True)
        return filtered_jobs[:min(50, len(filtered_jobs))]
    
    def _format_results(self, reranked_results: List[Dict]) -> List[JobResult]:
        """Format reranked results for API response"""
        final_results = []
        for job in reranked_results:
            final_results.append(JobResult(
                id=job['id'],
                score=job.get('cross_score', job.get('score', 0.0)),
                text=job.get('metadata', {}).get('text', job.get('text', '')),
                vector_score=job.get('vector_score', job.get('score', 0.0)),
                cross_score=job.get('cross_score', job.get('score', 0.0))
            ))
        return final_results
    
    def _empty_response(self, cache_params: Dict[str, Any]) -> SearchResponse:
        """Return empty search response"""
        return SearchResponse(
            source="pinecone",
            results=[],
            total_found=0,
            filters_applied=cache_params,
            reranked=False,
            candidates_retrieved=0
        )