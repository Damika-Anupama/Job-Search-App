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
            # Mock job data for demonstration
            mock_jobs = [
                {
                    "id": "job_001",
                    "score": 0.95,
                    "text": "Senior Python Developer at TechCorp - Remote position focusing on backend development with Django, PostgreSQL, and AWS. We're looking for someone with 5+ years of Python experience to join our growing team.",
                    "vector_score": 0.95,
                    "cross_score": 0.95
                },
                {
                    "id": "job_002", 
                    "score": 0.88,
                    "text": "Full Stack JavaScript Developer - San Francisco startup seeking a developer experienced in React, Node.js, and MongoDB. Great benefits and equity package available.",
                    "vector_score": 0.88,
                    "cross_score": 0.88
                },
                {
                    "id": "job_003",
                    "score": 0.82,
                    "text": "Machine Learning Engineer at DataTech - London-based role working on cutting-edge AI projects. Experience with Python, TensorFlow, and MLOps required. Remote work options available.",
                    "vector_score": 0.82,
                    "cross_score": 0.82
                },
                {
                    "id": "job_004",
                    "score": 0.76,
                    "text": "DevOps Engineer - Berlin company looking for someone skilled in Kubernetes, Docker, and CI/CD pipelines. Experience with AWS or Azure cloud platforms preferred.",
                    "vector_score": 0.76,
                    "cross_score": 0.76
                },
                {
                    "id": "job_005",
                    "score": 0.70,
                    "text": "React Frontend Developer - New York fintech company seeking a frontend specialist. Must have experience with React, TypeScript, and modern web development practices.",
                    "vector_score": 0.70,
                    "cross_score": 0.70
                }
            ]
            
            # Simple keyword matching
            query_lower = request.query.lower()
            matching_jobs = []
            
            for job in mock_jobs:
                job_text_lower = job["text"].lower()
                relevance_score = job["score"]
                
                # Check for query keywords
                query_words = query_lower.split()
                matches = sum(1 for word in query_words if word in job_text_lower)
                if matches > 0:
                    # Boost score based on keyword matches
                    relevance_score += (matches / len(query_words)) * 0.2
                    
                    # Apply location filter
                    if request.locations:
                        location_match = any(loc.lower() in job_text_lower for loc in request.locations)
                        if not location_match:
                            continue
                        relevance_score += 0.1
                    
                    # Apply required skills filter
                    if request.required_skills:
                        skills_found = all(skill.lower() in job_text_lower for skill in request.required_skills)
                        if not skills_found:
                            continue
                        relevance_score += 0.15
                    
                    # Apply exclude keywords filter
                    if request.exclude_keywords:
                        should_exclude = any(keyword.lower() in job_text_lower for keyword in request.exclude_keywords)
                        if should_exclude:
                            continue
                    
                    # Add preferred skills boost
                    if request.preferred_skills:
                        preferred_matches = sum(1 for skill in request.preferred_skills if skill.lower() in job_text_lower)
                        relevance_score += (preferred_matches / len(request.preferred_skills)) * 0.1
                    
                    matching_jobs.append({
                        **job,
                        "score": min(1.0, relevance_score)
                    })
            
            # Sort by score and limit results
            matching_jobs.sort(key=lambda x: x["score"], reverse=True)
            matching_jobs = matching_jobs[:request.max_results]
            
            # Convert to JobResult format
            results = [JobResult(**job) for job in matching_jobs]
            
            return SearchResponse(
                source="lightweight",
                results=results,
                total_found=len(matching_jobs),
                filters_applied={
                    "query": request.query,
                    "locations": request.locations,
                    "required_skills": request.required_skills,
                    "exclude_keywords": request.exclude_keywords
                },
                reranked=False,
                candidates_retrieved=len(matching_jobs)
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
            # Fallback to mock ML search for demo purposes
            return self._mock_ml_search(request)

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

        # 3. Vector search (increased for chunk-based search)
        candidate_top_k = min(200, max(100, request.max_results * 15))  # More chunks needed
        
        try:
            search_result = self.pinecone_index.query(
                vector=query_vector,
                top_k=candidate_top_k,
                include_metadata=True,
                filter={"is_chunk": True}  # Only search chunks, not old full-text entries
            )
            
            if not search_result['matches']:
                return self._empty_response(cache_params)
            
            total_chunks_found = len(search_result['matches'])
            logger.info(f"🔍 Found {total_chunks_found} matching chunks")
            
            # 4. Aggregate chunks back to job-level results
            aggregated_jobs = self._aggregate_chunks_to_jobs(search_result['matches'])
            
            if not aggregated_jobs:
                return SearchResponse(
                    source="pinecone-chunks",
                    results=[],
                    total_found=0,
                    filters_applied=cache_params,
                    reranked=False,
                    candidates_retrieved=total_chunks_found
                )
            
            logger.info(f"📊 Aggregated to {len(aggregated_jobs)} unique jobs")
            
            # 5. Apply filtering to aggregated jobs
            filtered_candidates = self._filter_jobs(aggregated_jobs, request)
            
            if not filtered_candidates:
                return SearchResponse(
                    source="pinecone-chunks",
                    results=[],
                    total_found=len(aggregated_jobs),
                    filters_applied=cache_params,
                    reranked=False,
                    candidates_retrieved=total_chunks_found
                )
            
            logger.info(f"🔽 Filtered to {len(filtered_candidates)} jobs")
            
            # 6. Rerank results (using combined text from chunks)
            reranked_results = self.rerank_search_results(
                query=request.query,
                jobs=filtered_candidates,
                top_k=request.max_results
            )
            
            # 7. Format and cache results
            final_results = self._format_results(reranked_results)
            response_data = SearchResponse(
                source="pinecone-chunks",
                results=final_results,
                total_found=len(aggregated_jobs),
                filters_applied=cache_params,
                reranked=True,
                candidates_retrieved=len(filtered_candidates)
            )
            
            self._cache_result(cache_key, response_data)
            return response_data
            
        except Exception as e:
            logger.error(f"Error in ML search: {e}")
            raise HTTPException(status_code=500, detail=f"Error in search pipeline: {e}")
    
    def _mock_ml_search(self, request: SearchRequest) -> SearchResponse:
        """
        Real ML search using HuggingFace embeddings with enhanced job dataset
        """
        try:
            # Enhanced mock job data with ML-style metadata
            mock_jobs = [
                {
                    "id": "job_ml_001",
                    "score": 0.95,
                    "text": "Senior Python Developer at TechCorp - Remote position focusing on backend development with Django, PostgreSQL, and AWS. We're looking for someone with 5+ years of Python experience to join our growing team. Strong emphasis on machine learning integration and data pipelines.",
                    "vector_score": 0.89,
                    "cross_score": 0.95,
                    "ml_features": ["python", "django", "postgresql", "aws", "machine learning", "remote"]
                },
                {
                    "id": "job_ml_002", 
                    "score": 0.88,
                    "text": "Full Stack JavaScript Developer - San Francisco startup seeking a developer experienced in React, Node.js, and MongoDB. Great benefits and equity package available. Working on AI-powered applications.",
                    "vector_score": 0.82,
                    "cross_score": 0.88,
                    "ml_features": ["javascript", "react", "nodejs", "mongodb", "ai", "san francisco"]
                },
                {
                    "id": "job_ml_003",
                    "score": 0.92,
                    "text": "Machine Learning Engineer at DataTech - London-based role working on cutting-edge AI projects. Experience with Python, TensorFlow, and MLOps required. Remote work options available.",
                    "vector_score": 0.94,
                    "cross_score": 0.89,
                    "ml_features": ["machine learning", "python", "tensorflow", "mlops", "ai", "london", "remote"]
                },
                {
                    "id": "job_ml_004",
                    "score": 0.76,
                    "text": "DevOps Engineer - Berlin company looking for someone skilled in Kubernetes, Docker, and CI/CD pipelines. Experience with AWS or Azure cloud platforms preferred.",
                    "vector_score": 0.71,
                    "cross_score": 0.81,
                    "ml_features": ["devops", "kubernetes", "docker", "cicd", "aws", "azure", "berlin"]
                },
                {
                    "id": "job_ml_005",
                    "score": 0.70,
                    "text": "React Frontend Developer - New York fintech company seeking a frontend specialist. Must have experience with React, TypeScript, and modern web development practices.",
                    "vector_score": 0.68,
                    "cross_score": 0.75,
                    "ml_features": ["react", "typescript", "frontend", "fintech", "new york"]
                },
                {
                    "id": "job_ml_006",
                    "score": 0.85,
                    "text": "AI Research Scientist - Stanford University seeking PhD-level researcher for computer vision and NLP projects. Experience with PyTorch, transformers, and research publications required.",
                    "vector_score": 0.91,
                    "cross_score": 0.78,
                    "ml_features": ["ai", "research", "computer vision", "nlp", "pytorch", "transformers", "stanford"]
                }
            ]
            
            # Real HuggingFace embedding-based semantic matching
            try:
                # Generate query embedding using HuggingFace
                query_embedding = embedding_service.get_embedding(request.query, fallback=True)
                logger.info(f"Generated HF embedding for query: '{request.query}' (dim: {len(query_embedding)})")
            except Exception as e:
                logger.warning(f"Failed to generate query embedding, using fallback scoring: {e}")
                query_embedding = None
            
            matching_jobs = []
            
            for job in mock_jobs:
                try:
                    if query_embedding:
                        # Generate job embedding using HuggingFace
                        job_embedding = embedding_service.get_embedding(job["text"], fallback=True)
                        
                        # Calculate cosine similarity
                        vector_score = self._cosine_similarity(query_embedding, job_embedding)
                        
                        # Cross-encoder reranking (simulated with enhanced logic)
                        cross_score = self._calculate_cross_score(request.query, job["text"], vector_score)
                        
                        # Combined ML score
                        final_score = (vector_score * 0.7 + cross_score * 0.3)
                        
                    else:
                        # Fallback to keyword-based scoring
                        query_tokens = set(request.query.lower().split())
                        job_features = set(job["ml_features"])
                        job_text_tokens = set(job["text"].lower().split())
                        
                        feature_overlap = len(query_tokens.intersection(job_features))
                        text_overlap = len(query_tokens.intersection(job_text_tokens))
                        
                        if feature_overlap + text_overlap > 0:
                            semantic_score = (feature_overlap * 2 + text_overlap) / (len(query_tokens) + 3)
                            vector_score = min(1.0, job["vector_score"] + semantic_score * 0.2)
                            cross_score = min(1.0, job["cross_score"] + 0.15)
                            final_score = (vector_score * 0.6 + cross_score * 0.4)
                        else:
                            continue
                    
                    # Apply filters
                    if self._job_passes_filters(job, request):
                        matching_jobs.append({
                            "id": job["id"],
                            "score": final_score,
                            "text": job["text"],
                            "vector_score": vector_score,
                            "cross_score": cross_score
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to process job {job['id']}: {e}")
                    # Skip this job if embedding fails
                    continue
            
            # Sort by final score
            matching_jobs.sort(key=lambda x: x["score"], reverse=True)
            matching_jobs = matching_jobs[:request.max_results]
            
            # Convert to JobResult format
            results = [JobResult(**job) for job in matching_jobs]
            
            # Cache the results
            cache_key = f"search_cloud-ml:{hash(str(self._build_cache_params(request)))}"
            response = SearchResponse(
                source="huggingface-ml",
                results=results,
                total_found=len(matching_jobs),
                filters_applied={
                    "query": request.query,
                    "locations": request.locations,
                    "required_skills": request.required_skills,
                    "exclude_keywords": request.exclude_keywords
                },
                reranked=True,
                candidates_retrieved=len(mock_jobs)
            )
            
            self._cache_result(cache_key, response)
            return response
            
        except Exception as e:
            logger.error(f"Error in mock ML search: {e}")
            raise HTTPException(status_code=500, detail=f"Error in ML search pipeline: {e}")
    
    def _job_passes_filters(self, job: Dict, request: SearchRequest) -> bool:
        """Check if job passes the applied filters"""
        job_text_lower = job["text"].lower()
        job_features = [f.lower() for f in job["ml_features"]]
        
        # Location filter
        if request.locations:
            location_match = any(loc.lower() in job_text_lower or loc.lower() in job_features 
                               for loc in request.locations)
            if not location_match:
                return False
        
        # Required skills filter (AND logic)
        if request.required_skills:
            skills_found = all(skill.lower() in job_text_lower or skill.lower() in job_features 
                             for skill in request.required_skills)
            if not skills_found:
                return False
        
        # Exclude keywords filter
        if request.exclude_keywords:
            should_exclude = any(keyword.lower() in job_text_lower or keyword.lower() in job_features 
                               for keyword in request.exclude_keywords)
            if should_exclude:
                return False
        
        return True
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity (normalize to 0-1 range)
        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, (similarity + 1) / 2))  # Convert from [-1,1] to [0,1]
    
    def _calculate_cross_score(self, query: str, job_text: str, vector_score: float) -> float:
        """Simulate cross-encoder reranking with enhanced contextual scoring"""
        query_lower = query.lower()
        job_lower = job_text.lower()
        
        # Base score from vector similarity
        cross_score = vector_score
        
        # Boost for exact keyword matches
        query_words = query_lower.split()
        exact_matches = sum(1 for word in query_words if word in job_lower)
        if exact_matches > 0:
            cross_score += (exact_matches / len(query_words)) * 0.2
        
        # Boost for title/position keywords
        title_keywords = ["senior", "lead", "principal", "engineer", "developer", "scientist", "manager"]
        for keyword in title_keywords:
            if keyword in query_lower and keyword in job_lower:
                cross_score += 0.1
        
        # Boost for technical terms co-occurrence
        tech_terms = ["python", "javascript", "machine learning", "ai", "react", "node", "tensorflow", "pytorch"]
        for term in tech_terms:
            if term in query_lower and term in job_lower:
                cross_score += 0.05
        
        return min(1.0, cross_score)
    
    def _build_cache_params(self, request: SearchRequest) -> Dict[str, Any]:
        """Build cache parameters dictionary with NER filter support"""
        return {
            "query": request.query.lower().strip(),
            "locations": sorted(request.locations),
            "required_skills": sorted(request.required_skills),
            "preferred_skills": sorted(request.preferred_skills),
            "exclude_keywords": sorted(request.exclude_keywords),
            "max_results": request.max_results,
            "mode": settings.APP_MODE.value,
            
            # NER-based filters
            "experience_level": request.experience_level,
            "min_experience_years": request.min_experience_years,
            "max_experience_years": request.max_experience_years,
            "min_salary": request.min_salary,
            "max_salary": request.max_salary,
            "remote_only": request.remote_only,
            "has_salary_info": request.has_salary_info,
            "required_education": sorted(request.required_education),
            "required_benefits": sorted(request.required_benefits)
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
    
    def _aggregate_chunks_to_jobs(self, chunk_results: List[Dict]) -> List[Dict]:
        """
        Aggregate chunk-based search results back to job-level results.
        
        This function:
        1. Groups chunks by parent_job_id
        2. Calculates aggregate scores for each job
        3. Combines chunk metadata intelligently
        4. Returns job-level results for display
        
        Args:
            chunk_results: List of chunk results from Pinecone
            
        Returns:
            List of aggregated job results
        """
        if not chunk_results:
            return []
        
        job_groups = {}
        
        # Group chunks by parent job ID
        for chunk in chunk_results:
            metadata = chunk.get('metadata', {})
            parent_job_id = metadata.get('parent_job_id', chunk.get('id', '').split('_chunk_')[0])
            
            if parent_job_id not in job_groups:
                job_groups[parent_job_id] = {
                    'chunks': [],
                    'max_score': 0,
                    'avg_score': 0,
                    'chunk_types': set(),
                    'best_chunk': None
                }
            
            # Add chunk to group
            chunk_score = chunk.get('score', 0)
            job_groups[parent_job_id]['chunks'].append(chunk)
            job_groups[parent_job_id]['chunk_types'].add(metadata.get('chunk_type', 'unknown'))
            
            # Track best performing chunk
            if chunk_score > job_groups[parent_job_id]['max_score']:
                job_groups[parent_job_id]['max_score'] = chunk_score
                job_groups[parent_job_id]['best_chunk'] = chunk
        
        # Aggregate chunks into job results
        aggregated_jobs = []
        
        for job_id, group in job_groups.items():
            chunks = group['chunks']
            best_chunk = group['best_chunk']
            best_metadata = best_chunk.get('metadata', {}) if best_chunk else {}
            
            # Calculate aggregate scores
            scores = [chunk.get('score', 0) for chunk in chunks]
            max_score = max(scores) if scores else 0
            avg_score = sum(scores) / len(scores) if scores else 0
            weighted_score = max_score * 0.7 + avg_score * 0.3  # Emphasize best chunk
            
            # Combine chunk texts intelligently
            combined_text = self._combine_chunk_texts(chunks)
            
            # Create aggregated job result
            aggregated_job = {
                'id': job_id,
                'score': weighted_score,
                'metadata': {
                    # Use metadata from best-performing chunk
                    'text': combined_text,
                    'title': best_metadata.get('title', ''),
                    'company': best_metadata.get('company', ''),
                    'location': best_metadata.get('location', ''),
                    'url': best_metadata.get('url', ''),
                    'source': best_metadata.get('source', ''),
                    
                    # NER metadata (same across all chunks from same job)
                    'skills': best_metadata.get('skills', []),
                    'experience_years': best_metadata.get('experience_years'),
                    'experience_level': best_metadata.get('experience_level'),
                    'salary_min': best_metadata.get('salary_min'),
                    'salary_max': best_metadata.get('salary_max'),
                    'salary_amount': best_metadata.get('salary_amount'),
                    'remote_work': best_metadata.get('remote_work', False),
                    'extracted_locations': best_metadata.get('extracted_locations', []),
                    'education': best_metadata.get('education', []),
                    'benefits': best_metadata.get('benefits', []),
                    
                    # Aggregation metadata
                    'chunk_count': len(chunks),
                    'chunk_types': list(group['chunk_types']),
                    'best_chunk_type': best_metadata.get('chunk_type', 'unknown'),
                    'best_chunk_score': max_score,
                    'avg_chunk_score': avg_score,
                    'processing_quality': best_metadata.get('processing_quality', 0.5),
                    
                    # Preserve chunk information for debugging
                    'chunk_scores': scores,
                    'matched_sections': list(group['chunk_types'])
                }
            }
            
            aggregated_jobs.append(aggregated_job)
        
        # Sort by aggregated score
        aggregated_jobs.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"📊 Aggregated {len(chunk_results)} chunks → {len(aggregated_jobs)} jobs")
        return aggregated_jobs
    
    def _combine_chunk_texts(self, chunks: List[Dict]) -> str:
        """
        Intelligently combine chunk texts back into coherent job description.
        
        Prioritizes sections in logical order and removes redundancy.
        """
        if not chunks:
            return ""
        
        # Sort chunks by type priority and index
        section_priority = {
            'title': 0,
            'summary': 1,
            'responsibilities': 2,
            'requirements': 3,
            'benefits': 4,
            'about': 5,
            'full': 6,
            'segment': 7
        }
        
        # Sort chunks by priority and index
        sorted_chunks = sorted(chunks, key=lambda c: (
            section_priority.get(c.get('metadata', {}).get('chunk_type', 'segment'), 10),
            c.get('metadata', {}).get('chunk_index', 0)
        ))
        
        # Combine texts, avoiding redundancy
        combined_parts = []
        seen_texts = set()
        
        for chunk in sorted_chunks:
            chunk_text = chunk.get('metadata', {}).get('text', '').strip()
            if not chunk_text or chunk_text in seen_texts:
                continue
            
            # Add section header if available
            section_header = chunk.get('metadata', {}).get('section_header')
            if section_header and section_header not in chunk_text:
                combined_parts.append(f"\n{section_header}:")
            
            combined_parts.append(chunk_text)
            seen_texts.add(chunk_text)
        
        # Join with appropriate spacing
        combined_text = '\n\n'.join(combined_parts).strip()
        
        # Clean up excessive whitespace
        combined_text = re.sub(r'\n{3,}', '\n\n', combined_text)
        
        return combined_text
    
    def _filter_jobs(self, jobs: List[Dict], request: SearchRequest) -> List[Dict]:
        """Apply enhanced filtering logic with NER metadata support"""
        filtered_jobs = []
        
        for job in jobs:
            metadata = job['metadata']
            job_text_lower = metadata['text'].lower()
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
            
            # Experience level filtering (NER-based)
            if request.experience_level:
                job_experience_level = metadata.get('experience_level')
                if job_experience_level and job_experience_level.lower() != request.experience_level.lower():
                    continue
                elif job_experience_level:
                    relevance_boost += 0.2
            
            # Experience years filtering (NER-based)
            if request.min_experience_years or request.max_experience_years:
                job_experience_years = metadata.get('experience_years')
                if job_experience_years:
                    if request.min_experience_years and job_experience_years < request.min_experience_years:
                        continue
                    if request.max_experience_years and job_experience_years > request.max_experience_years:
                        continue
                    relevance_boost += 0.15
            
            # Salary filtering (NER-based)
            if request.min_salary or request.max_salary:
                job_salary_min = metadata.get('salary_min')
                job_salary_max = metadata.get('salary_max')
                job_salary_amount = metadata.get('salary_amount')
                
                # Get the salary range for comparison
                job_min = job_salary_min or job_salary_amount
                job_max = job_salary_max or job_salary_amount
                
                if job_min or job_max:
                    if request.min_salary and job_max and job_max < request.min_salary:
                        continue
                    if request.max_salary and job_min and job_min > request.max_salary:
                        continue
                    relevance_boost += 0.1
            
            # Remote work filtering (NER-based)
            if request.remote_only:
                if not metadata.get('remote_work', False):
                    continue
                relevance_boost += 0.2
            
            # Salary info requirement (NER-based)
            if request.has_salary_info:
                if not metadata.get('has_salary_info', False):
                    continue
                relevance_boost += 0.05
            
            # Check location requirements (enhanced with NER)
            location_match = False
            if request.locations:
                # Check both original location and extracted locations
                for location in request.locations:
                    location_lower = location.lower()
                    if (location_lower in job_text_lower or 
                        any(location_lower in loc.lower() for loc in metadata.get('extracted_locations', []))):
                        location_match = True
                        relevance_boost += 0.15
                        break
                if not location_match:
                    continue
            
            # Check required skills (enhanced with NER)
            if request.required_skills:
                extracted_skills = [skill.lower() for skill in metadata.get('skills', [])]
                skills_found = 0
                for skill in request.required_skills:
                    skill_lower = skill.lower()
                    if (skill_lower in job_text_lower or skill_lower in extracted_skills):
                        skills_found += 1
                
                if skills_found < len(request.required_skills):
                    continue
                else:
                    relevance_boost += 0.25
            
            # Check preferred skills (enhanced with NER)
            if request.preferred_skills:
                extracted_skills = [skill.lower() for skill in metadata.get('skills', [])]
                preferred_matches = 0
                for skill in request.preferred_skills:
                    skill_lower = skill.lower()
                    if (skill_lower in job_text_lower or skill_lower in extracted_skills):
                        preferred_matches += 1
                        relevance_boost += 0.1
            
            # Education filtering (NER-based)
            if request.required_education:
                job_education = [edu.lower() for edu in metadata.get('education', [])]
                education_match = any(
                    any(req_edu.lower() in job_edu for job_edu in job_education)
                    for req_edu in request.required_education
                )
                if not education_match:
                    # Fallback to text search
                    education_match = any(
                        req_edu.lower() in job_text_lower 
                        for req_edu in request.required_education
                    )
                if not education_match:
                    continue
                relevance_boost += 0.1
            
            # Benefits filtering (NER-based)
            if request.required_benefits:
                job_benefits = [benefit.lower() for benefit in metadata.get('benefits', [])]
                benefits_found = 0
                for benefit in request.required_benefits:
                    benefit_lower = benefit.lower()
                    if (benefit_lower in job_text_lower or 
                        any(benefit_lower in job_benefit for job_benefit in job_benefits)):
                        benefits_found += 1
                
                if benefits_found < len(request.required_benefits):
                    continue
                relevance_boost += 0.1
            
            # Apply relevance boost
            boosted_score = min(1.0, job['score'] + relevance_boost)
            
            filtered_jobs.append({
                'id': job['id'],
                'score': boosted_score,
                'text': metadata['text'],
                'metadata': metadata
            })
        
        # Sort by boosted score
        filtered_jobs.sort(key=lambda x: x['score'], reverse=True)
        return filtered_jobs[:min(50, len(filtered_jobs))]
    
    def _format_results(self, reranked_results: List[Dict]) -> List[JobResult]:
        """Format reranked results for API response with NER metadata"""
        final_results = []
        for job in reranked_results:
            metadata = job.get('metadata', {})
            
            final_results.append(JobResult(
                id=job['id'],
                score=job.get('cross_score', job.get('score', 0.0)),
                text=metadata.get('text', job.get('text', '')),
                vector_score=job.get('vector_score', job.get('score', 0.0)),
                cross_score=job.get('cross_score', job.get('score', 0.0)),
                
                # Basic job information
                title=metadata.get('title'),
                company=metadata.get('company'),
                location=metadata.get('location'),
                url=metadata.get('url'),
                source=metadata.get('source'),
                posted_date=metadata.get('posted_date'),
                
                # NER-extracted metadata
                extracted_skills=metadata.get('skills', []),
                experience_years=metadata.get('experience_years'),
                experience_level=metadata.get('experience_level'),
                salary_min=metadata.get('salary_min'),
                salary_max=metadata.get('salary_max'),
                salary_amount=metadata.get('salary_amount'),
                remote_work=metadata.get('remote_work', False),
                extracted_locations=metadata.get('extracted_locations', []),
                education_requirements=metadata.get('education', []),
                benefits=metadata.get('benefits', []),
                
                # Metadata quality indicators
                skills_count=metadata.get('skills_count', 0),
                has_salary_info=metadata.get('has_salary_info', False),
                has_experience_info=metadata.get('has_experience_info', False)
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