"""
Cross-encoder reranking module for improved search relevance.

This module implements a two-stage search process:
1. Initial vector search (broad candidate selection)  
2. Cross-encoder reranking (precise relevance scoring)
"""

# Conditional import for cross-encoder (graceful fallback)
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("Warning: sentence-transformers not available. Cross-encoder reranking disabled.")
import logging
from typing import List, Dict, Tuple
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobReranker:
    """
    Handles cross-encoder reranking for job search results.
    
    Uses a pre-trained cross-encoder model to provide more accurate
    relevance scores than the initial vector search.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the reranker with a cross-encoder model.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the cross-encoder model with error handling."""
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("Cross-encoder not available - using fallback ranking")
            self.model = None
            return
            
        try:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            start_time = time.time()
            
            self.model = CrossEncoder(self.model_name)
            
            load_time = time.time() - start_time
            logger.info(f"Cross-encoder model loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            self.model = None
    
    def rerank_jobs(self, query: str, jobs: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Rerank job search results using cross-encoder for better relevance.
        
        Args:
            query: User's search query
            jobs: List of job dictionaries from Pinecone search
            top_k: Number of top results to return after reranking
            
        Returns:
            Reranked list of jobs with updated scores
        """
        if not self.model:
            logger.warning("Cross-encoder model not available, returning original results")
            return jobs[:top_k]
        
        if not jobs:
            return []
        
        try:
            logger.info(f"Reranking {len(jobs)} jobs for query: '{query[:50]}...'")
            start_time = time.time()
            
            # Prepare query-document pairs for cross-encoder
            query_doc_pairs = []
            for job in jobs:
                # Use job text content for reranking
                job_text = job.get('metadata', {}).get('text', job.get('text', ''))
                # Truncate very long job descriptions to avoid model limits
                truncated_text = job_text[:512] if len(job_text) > 512 else job_text
                query_doc_pairs.append([query, truncated_text])
            
            # Get cross-encoder scores
            cross_scores = self.model.predict(query_doc_pairs)
            
            # Update jobs with new cross-encoder scores
            reranked_jobs = []
            for i, job in enumerate(jobs):
                job_copy = job.copy()
                
                # Store both original vector score and new cross-encoder score
                job_copy['vector_score'] = job.get('score', 0.0)
                job_copy['cross_score'] = float(cross_scores[i])
                job_copy['score'] = float(cross_scores[i])  # Use cross-encoder score as primary
                
                reranked_jobs.append(job_copy)
            
            # Sort by cross-encoder score (descending)
            reranked_jobs.sort(key=lambda x: x['cross_score'], reverse=True)
            
            rerank_time = time.time() - start_time
            logger.info(f"Reranking completed in {rerank_time:.2f}s")
            
            # Return top_k results
            return reranked_jobs[:top_k]
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Fallback to original results if reranking fails
            return jobs[:top_k]
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "model_loaded": self.model is not None,
            "model_type": "cross-encoder"
        }

# Global reranker instance (lazy loaded)
_reranker_instance = None

def get_reranker() -> JobReranker:
    """
    Get or create a global reranker instance.
    
    Returns:
        JobReranker instance
    """
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = JobReranker()
    return _reranker_instance

def rerank_search_results(query: str, jobs: List[Dict], top_k: int = 10) -> List[Dict]:
    """
    Convenience function to rerank search results.
    
    Args:
        query: User's search query
        jobs: List of job dictionaries from search
        top_k: Number of top results to return
        
    Returns:
        Reranked list of jobs
    """
    reranker = get_reranker()
    return reranker.rerank_jobs(query, jobs, top_k)