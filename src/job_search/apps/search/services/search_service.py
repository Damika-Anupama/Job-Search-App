"""
Enterprise Search Service with clean architecture.

This service implements the business logic for job searching,
using dependency injection for all external dependencies.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from ....shared.core.interfaces import (
    VectorDatabaseInterface, 
    CacheInterface, 
    EmbeddingServiceInterface,
    RerankingServiceInterface,
    MetricsInterface,
    LoggerInterface
)
from ..models.search_models import SearchQuery, SearchResult, JobDocument
from ..repositories.job_repository import JobRepository


class SearchService:
    """
    Enterprise-grade search service with proper separation of concerns.
    
    Features:
    - Dependency injection for all external services
    - Comprehensive caching strategy
    - Metrics and logging
    - Error handling and resilience
    - Domain-specific business logic
    """
    
    def __init__(self,
                 vector_db: VectorDatabaseInterface,
                 cache: CacheInterface,
                 embedding_service: EmbeddingServiceInterface,
                 reranking_service: RerankingServiceInterface,
                 job_repository: JobRepository,
                 metrics: MetricsInterface,
                 logger: LoggerInterface,
                 cache_ttl: int = 3600):
        """
        Initialize search service with all dependencies.
        
        Args:
            vector_db: Vector database for similarity search
            cache: Caching service for performance
            embedding_service: Text embedding generation
            reranking_service: Result reranking for relevance
            job_repository: Job data access layer
            metrics: Metrics collection service
            logger: Structured logging service
            cache_ttl: Cache time-to-live in seconds
        """
        self.vector_db = vector_db
        self.cache = cache
        self.embedding_service = embedding_service
        self.reranking_service = reranking_service
        self.job_repository = job_repository
        self.metrics = metrics
        self.logger = logger
        self.cache_ttl = cache_ttl
    
    async def search(self, query: SearchQuery, user_id: str = None) -> SearchResult:
        """
        Perform comprehensive job search with caching and metrics.
        
        Args:
            query: Structured search query
            user_id: Optional user ID for personalization
            
        Returns:
            SearchResult with jobs and metadata
        """
        search_start_time = datetime.utcnow()
        
        try:
            # Increment search counter
            self.metrics.increment_counter(
                "search_requests_total",
                {"user_id": user_id or "anonymous", "query_type": query.search_type}
            )
            
            # Generate cache key
            cache_key = self._generate_cache_key(query, user_id)
            
            # Try cache first
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                self.metrics.increment_counter("search_cache_hits_total")
                self.logger.info(
                    "Search cache hit",
                    extra={
                        "user_id": user_id,
                        "query": query.text,
                        "cache_key": cache_key
                    }
                )
                return cached_result
            
            self.metrics.increment_counter("search_cache_misses_total")
            
            # Perform actual search
            result = await self._perform_search(query, user_id)
            
            # Cache result
            await self._cache_result(cache_key, result)
            
            # Record metrics
            search_duration = (datetime.utcnow() - search_start_time).total_seconds()
            self.metrics.record_histogram(
                "search_duration_seconds",
                search_duration,
                {"query_type": query.search_type}
            )
            
            self.logger.info(
                "Search completed",
                extra={
                    "user_id": user_id,
                    "query": query.text,
                    "results_count": len(result.jobs),
                    "duration_seconds": search_duration,
                    "cache_key": cache_key
                }
            )
            
            return result
            
        except Exception as e:
            self.metrics.increment_counter("search_errors_total")
            self.logger.error(
                "Search failed",
                extra={
                    "user_id": user_id,
                    "query": query.text,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def _perform_search(self, query: SearchQuery, user_id: str = None) -> SearchResult:
        """Perform the actual search operation"""
        
        # Step 1: Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query.text)
        
        # Step 2: Vector similarity search
        candidates = await self.vector_db.search(
            vector=query_embedding,
            k=query.candidate_pool_size or 100,
            namespace=query.namespace
        )
        
        if not candidates:
            return SearchResult(
                jobs=[],
                total_found=0,
                query=query,
                search_metadata={
                    "stage": "vector_search",
                    "candidates_found": 0,
                    "reranked": False
                }
            )
        
        # Step 3: Apply filters
        filtered_candidates = await self._apply_filters(candidates, query)
        
        # Step 4: Rerank for relevance
        if query.enable_reranking and len(filtered_candidates) > 1:
            reranked_jobs = await self.reranking_service.rerank(
                query=query.text,
                documents=filtered_candidates,
                top_k=query.max_results
            )
        else:
            # Just take top results
            reranked_jobs = filtered_candidates[:query.max_results]
        
        # Step 5: Enrich with additional data
        enriched_jobs = await self._enrich_job_data(reranked_jobs, user_id)
        
        return SearchResult(
            jobs=enriched_jobs,
            total_found=len(candidates),
            query=query,
            search_metadata={
                "stage": "complete",
                "candidates_found": len(candidates),
                "filtered_candidates": len(filtered_candidates),
                "reranked": query.enable_reranking,
                "final_results": len(enriched_jobs)
            }
        )
    
    async def _apply_filters(self, candidates: List[Dict[str, Any]], query: SearchQuery) -> List[Dict[str, Any]]:
        """Apply business logic filters to search candidates"""
        filtered = []
        
        for candidate in candidates:
            job_text = candidate.get('metadata', {}).get('text', '').lower()
            
            # Location filter
            if query.locations:
                location_match = any(loc.lower() in job_text for loc in query.locations)
                if not location_match:
                    continue
            
            # Required skills (all must be present)
            if query.required_skills:
                skills_match = all(skill.lower() in job_text for skill in query.required_skills)
                if not skills_match:
                    continue
            
            # Exclude keywords
            if query.exclude_keywords:
                has_excluded = any(keyword.lower() in job_text for keyword in query.exclude_keywords)
                if has_excluded:
                    continue
            
            # Salary filter
            if query.min_salary:
                # This would require more sophisticated salary extraction
                # For now, we'll skip this complex logic
                pass
            
            filtered.append(candidate)
        
        return filtered
    
    async def _enrich_job_data(self, jobs: List[Dict[str, Any]], user_id: str = None) -> List[JobDocument]:
        """Enrich job data with additional information"""
        enriched_jobs = []
        
        for job in jobs:
            # Convert to domain model
            job_doc = JobDocument.from_search_result(job)
            
            # Add user-specific data if available
            if user_id:
                # Check if user has saved this job
                job_doc.is_saved = await self.job_repository.is_job_saved(user_id, job_doc.id)
                # Add user interaction history
                job_doc.user_interactions = await self.job_repository.get_user_interactions(user_id, job_doc.id)
            
            # Add company information
            if job_doc.company_name:
                company_info = await self.job_repository.get_company_info(job_doc.company_name)
                if company_info:
                    job_doc.company_info = company_info
            
            enriched_jobs.append(job_doc)
        
        return enriched_jobs
    
    def _generate_cache_key(self, query: SearchQuery, user_id: str = None) -> str:
        """Generate deterministic cache key for query"""
        key_data = {
            "query": query.text.lower().strip(),
            "locations": sorted(query.locations) if query.locations else [],
            "required_skills": sorted(query.required_skills) if query.required_skills else [],
            "exclude_keywords": sorted(query.exclude_keywords) if query.exclude_keywords else [],
            "max_results": query.max_results,
            "user_id": user_id,
            "search_type": query.search_type
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[SearchResult]:
        """Get search result from cache"""
        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return SearchResult.from_dict(cached_data)
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_result(self, cache_key: str, result: SearchResult) -> None:
        """Cache search result"""
        try:
            await self.cache.set(cache_key, result.to_dict(), ttl=self.cache_ttl)
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {e}")

    async def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query"""
        # This could use ML-based query completion or popular searches
        suggestions = await self.job_repository.get_popular_search_terms(partial_query, limit)
        
        self.metrics.increment_counter("search_suggestions_requested")
        
        return suggestions
    
    async def get_trending_searches(self, time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Get trending search queries"""
        trending = await self.job_repository.get_trending_searches(time_window_hours)
        
        return trending