import requests
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import logging
from ..core.config import settings, AppMode

logger = logging.getLogger(__name__)

class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors"""
    pass

class HuggingFaceInferenceError(EmbeddingServiceError):
    """Raised when HuggingFace inference fails"""
    pass

class EmbeddingService:
    """Handles text embeddings based on application mode"""
    
    def __init__(self):
        self.mode = settings.APP_MODE
        self._local_model = None
        self._hf_api_status = None
        
    def _get_local_model(self) -> SentenceTransformer:
        """Lazy load local sentence transformer model"""
        if self._local_model is None:
            if self.mode == AppMode.LIGHTWEIGHT:
                raise EmbeddingServiceError("Local embeddings not available in lightweight mode")
            
            logger.info("Loading local sentence transformer model...")
            self._local_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Local model loaded successfully")
        return self._local_model
    
    def _get_hf_embedding(self, text: str) -> List[float]:
        """Get embedding from Hugging Face Inference API"""
        if not settings.HF_INFERENCE_API or not settings.HF_TOKEN:
            raise HuggingFaceInferenceError("HuggingFace credentials not configured")
        
        headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}
        payload = {"inputs": text}
        
        try:
            response = requests.post(settings.HF_INFERENCE_API, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and isinstance(result[0], list):
                embedding = result[0]
            elif isinstance(result, list) and isinstance(result[0], (int, float)):
                embedding = result
            else:
                raise HuggingFaceInferenceError(f"Unexpected API response format: {type(result)}")
            
            if len(embedding) != settings.HF_MODEL_DIMENSION:
                raise HuggingFaceInferenceError(f"Expected {settings.HF_MODEL_DIMENSION} dimensions, got {len(embedding)}")
            
            self._hf_api_status = "healthy"
            return embedding
            
        except requests.exceptions.Timeout:
            self._hf_api_status = "timeout"
            raise HuggingFaceInferenceError("HuggingFace API timeout")
        except requests.exceptions.ConnectionError:
            self._hf_api_status = "connection_error"
            raise HuggingFaceInferenceError("Cannot connect to HuggingFace API")
        except requests.exceptions.HTTPError as e:
            self._hf_api_status = f"http_error_{e.response.status_code}"
            raise HuggingFaceInferenceError(f"HuggingFace API HTTP error: {e}")
        except Exception as e:
            self._hf_api_status = "unknown_error"
            raise HuggingFaceInferenceError(f"HuggingFace API error: {str(e)}")
    
    def _get_local_embedding(self, text: str) -> List[float]:
        """Get embedding from local model"""
        model = self._get_local_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def get_embedding(self, text: str, fallback: bool = False) -> List[float]:
        """
        Get text embedding based on current mode
        
        Args:
            text: Text to embed
            fallback: Whether to fallback to local model if cloud fails (cloud-ml mode only)
            
        Returns:
            List of floats representing the embedding
            
        Raises:
            EmbeddingServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("Empty text provided")
        
        text = text.strip()
        
        if self.mode == AppMode.LIGHTWEIGHT:
            raise EmbeddingServiceError("Embeddings not supported in lightweight mode")
        
        elif self.mode == AppMode.CLOUD_ML:
            try:
                return self._get_hf_embedding(text)
            except HuggingFaceInferenceError as e:
                if fallback:
                    logger.warning(f"HF inference failed, falling back to local: {e}")
                    return self._get_local_embedding(text)
                else:
                    raise
        
        elif self.mode == AppMode.FULL_ML:
            return self._get_local_embedding(text)
        
        else:
            raise EmbeddingServiceError(f"Unknown mode: {self.mode}")
    
    def get_embeddings_batch(self, texts: List[str], fallback: bool = False) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        if not texts:
            return []
        
        if self.mode == AppMode.LIGHTWEIGHT:
            raise EmbeddingServiceError("Embeddings not supported in lightweight mode")
        
        # For now, process individually. Could be optimized for batch processing
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text, fallback=fallback)
            embeddings.append(embedding)
        
        return embeddings
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of embedding service"""
        status = {
            "mode": self.mode.value,
            "status": "unknown",
            "details": {}
        }
        
        try:
            if self.mode == AppMode.LIGHTWEIGHT:
                status["status"] = "healthy"
                status["details"]["message"] = "Lightweight mode - no ML dependencies"
            
            elif self.mode == AppMode.FULL_ML:
                # Test local model
                test_embedding = self._get_local_embedding("test")
                status["status"] = "healthy"
                status["details"]["local_model"] = "available"
                status["details"]["embedding_dimension"] = len(test_embedding)
            
            elif self.mode == AppMode.CLOUD_ML:
                # Test HF inference
                try:
                    test_embedding = self._get_hf_embedding("test")
                    status["status"] = "healthy"
                    status["details"]["hf_inference"] = "available"
                    status["details"]["embedding_dimension"] = len(test_embedding)
                except HuggingFaceInferenceError as e:
                    status["status"] = "degraded"
                    status["details"]["hf_inference"] = "unavailable"
                    status["details"]["hf_error"] = str(e)
                    status["details"]["hf_api_status"] = self._hf_api_status
                    
                    # Check if local fallback works
                    try:
                        test_local = self._get_local_embedding("test")
                        status["details"]["local_fallback"] = "available"
                    except Exception as local_e:
                        status["details"]["local_fallback"] = f"unavailable: {local_e}"
                        status["status"] = "unhealthy"
        
        except Exception as e:
            status["status"] = "unhealthy"
            status["details"]["error"] = str(e)
        
        return status

# Global instance
embedding_service = EmbeddingService()

# Convenience functions for backward compatibility
def get_embedding(text: str, fallback: bool = False) -> List[float]:
    """Get embedding for text - backward compatible function"""
    return embedding_service.get_embedding(text, fallback=fallback)

def get_embeddings_batch(texts: List[str], fallback: bool = False) -> List[List[float]]:
    """Get embeddings for multiple texts - batch function"""
    return embedding_service.get_embeddings_batch(texts, fallback=fallback)