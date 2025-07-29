import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import requests
from embedding_service import EmbeddingService, EmbeddingServiceError, HuggingFaceInferenceError
from config import AppMode


class TestEmbeddingService:
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for different modes"""
        with patch('embedding_service.APP_MODE') as mock_mode, \
             patch('embedding_service.HF_INFERENCE_API', 'http://test-api'), \
             patch('embedding_service.HF_TOKEN', 'test-token'), \
             patch('embedding_service.HF_MODEL_DIMENSION', 384):
            yield mock_mode
    
    @pytest.fixture
    def embedding_service(self, mock_config):
        """Create a fresh embedding service instance for each test"""
        return EmbeddingService()
    
    def test_lightweight_mode_raises_error(self, mock_config, embedding_service):
        """Test that lightweight mode raises error for embedding requests"""
        mock_config.return_value = AppMode.LIGHTWEIGHT
        embedding_service.mode = AppMode.LIGHTWEIGHT
        
        with pytest.raises(EmbeddingServiceError, match="not supported in lightweight mode"):
            embedding_service.get_embedding("test text")
    
    @patch('embedding_service.SentenceTransformer')
    def test_full_ml_mode_local_embedding(self, mock_transformer, mock_config, embedding_service):
        """Test local embedding generation in full-ml mode"""
        mock_config.return_value = AppMode.FULL_ML
        embedding_service.mode = AppMode.FULL_ML
        
        # Mock the transformer model
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        result = embedding_service.get_embedding("test text")
        
        assert result == mock_embedding.tolist()
        mock_model.encode.assert_called_once_with("test text", normalize_embeddings=True)
    
    @patch('embedding_service.requests.post')
    def test_cloud_ml_mode_hf_success(self, mock_post, mock_config, embedding_service):
        """Test successful HuggingFace inference in cloud-ml mode"""
        mock_config.return_value = AppMode.CLOUD_ML
        embedding_service.mode = AppMode.CLOUD_ML
        
        # Mock successful HF API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [[0.1, 0.2, 0.3] + [0.0] * 381]  # 384 dimensions
        mock_post.return_value = mock_response
        
        result = embedding_service.get_embedding("test text")
        
        assert len(result) == 384
        assert result[0] == 0.1
        mock_post.assert_called_once()
    
    @patch('embedding_service.requests.post')
    def test_cloud_ml_mode_hf_timeout(self, mock_post, mock_config, embedding_service):
        """Test HuggingFace API timeout handling"""
        mock_config.return_value = AppMode.CLOUD_ML
        embedding_service.mode = AppMode.CLOUD_ML
        
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(HuggingFaceInferenceError, match="timeout"):
            embedding_service.get_embedding("test text")
    
    @patch('embedding_service.requests.post')
    @patch('embedding_service.SentenceTransformer')
    def test_cloud_ml_mode_fallback(self, mock_transformer, mock_post, mock_config, embedding_service):
        """Test fallback to local model when HF fails"""
        mock_config.return_value = AppMode.CLOUD_ML
        embedding_service.mode = AppMode.CLOUD_ML
        
        # Mock HF API failure
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        # Mock local model
        mock_model = Mock()
        mock_embedding = np.array([0.5, 0.6, 0.7, 0.8])
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model
        
        result = embedding_service.get_embedding("test text", fallback=True)
        
        assert result == mock_embedding.tolist()
        mock_model.encode.assert_called_once()
    
    def test_empty_text_raises_error(self, mock_config, embedding_service):
        """Test that empty text raises appropriate error"""
        mock_config.return_value = AppMode.FULL_ML
        embedding_service.mode = AppMode.FULL_ML
        
        with pytest.raises(EmbeddingServiceError, match="Empty text provided"):
            embedding_service.get_embedding("")
        
        with pytest.raises(EmbeddingServiceError, match="Empty text provided"):
            embedding_service.get_embedding("   ")
    
    @patch('embedding_service.SentenceTransformer')
    def test_health_check_full_ml(self, mock_transformer, mock_config, embedding_service):
        """Test health check for full-ml mode"""
        mock_config.return_value = AppMode.FULL_ML
        embedding_service.mode = AppMode.FULL_ML
        
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1] * 384)
        mock_transformer.return_value = mock_model
        
        health = embedding_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["mode"] == "full-ml"
        assert "local_model" in health["details"]
    
    @patch('embedding_service.requests.post')
    def test_health_check_cloud_ml_healthy(self, mock_post, mock_config, embedding_service):
        """Test health check for cloud-ml mode when HF is available"""
        mock_config.return_value = AppMode.CLOUD_ML
        embedding_service.mode = AppMode.CLOUD_ML
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [[0.1] * 384]
        mock_post.return_value = mock_response
        
        health = embedding_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["details"]["hf_inference"] == "available"
    
    @patch('embedding_service.requests.post')
    @patch('embedding_service.SentenceTransformer')
    def test_health_check_cloud_ml_degraded(self, mock_transformer, mock_post, mock_config, embedding_service):
        """Test health check for cloud-ml mode when HF fails but local works"""
        mock_config.return_value = AppMode.CLOUD_ML
        embedding_service.mode = AppMode.CLOUD_ML
        
        # Mock HF failure
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        # Mock local model working
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1] * 384)
        mock_transformer.return_value = mock_model
        
        health = embedding_service.health_check()
        
        assert health["status"] == "degraded"
        assert health["details"]["hf_inference"] == "unavailable"
        assert health["details"]["local_fallback"] == "available"
    
    def test_health_check_lightweight(self, mock_config, embedding_service):
        """Test health check for lightweight mode"""
        mock_config.return_value = AppMode.LIGHTWEIGHT
        embedding_service.mode = AppMode.LIGHTWEIGHT
        
        health = embedding_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["mode"] == "lightweight"
        assert "no ML dependencies" in health["details"]["message"]
    
    @patch('embedding_service.SentenceTransformer')
    def test_batch_embeddings(self, mock_transformer, mock_config, embedding_service):
        """Test batch embedding generation"""
        mock_config.return_value = AppMode.FULL_ML
        embedding_service.mode = AppMode.FULL_ML
        
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_model
        
        texts = ["text1", "text2", "text3"]
        results = embedding_service.get_embeddings_batch(texts)
        
        assert len(results) == 3
        assert all(len(embedding) == 3 for embedding in results)
        assert mock_model.encode.call_count == 3
    
    def test_batch_embeddings_empty_list(self, mock_config, embedding_service):
        """Test batch embeddings with empty input"""
        result = embedding_service.get_embeddings_batch([])
        assert result == []