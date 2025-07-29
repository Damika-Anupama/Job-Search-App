import pytest
import os
from unittest.mock import patch
from config import AppMode, validate_mode_config


class TestConfig:
    
    def test_app_mode_enum(self):
        """Test AppMode enum values"""
        assert AppMode.LIGHTWEIGHT.value == "lightweight"
        assert AppMode.FULL_ML.value == "full-ml"
        assert AppMode.CLOUD_ML.value == "cloud-ml"
    
    @patch.dict(os.environ, {
        'APP_MODE': 'lightweight'
    })
    def test_lightweight_mode_validation_success(self):
        """Test that lightweight mode doesn't require ML credentials"""
        # This should not raise any exception
        with patch('config.APP_MODE', AppMode.LIGHTWEIGHT):
            validate_mode_config()  # Should pass without error
    
    @patch.dict(os.environ, {
        'APP_MODE': 'full-ml',
        'PINECONE_API_KEY': 'test-key'
    })
    def test_full_ml_mode_validation_success(self):
        """Test that full-ml mode validation passes with Pinecone key"""
        with patch('config.APP_MODE', AppMode.FULL_ML), \
             patch('config.PINECONE_API_KEY', 'test-key'):
            validate_mode_config()  # Should pass without error
    
    @patch.dict(os.environ, {
        'APP_MODE': 'full-ml'
    })
    def test_full_ml_mode_validation_failure(self):
        """Test that full-ml mode validation fails without Pinecone key"""
        with patch('config.APP_MODE', AppMode.FULL_ML), \
             patch('config.PINECONE_API_KEY', None):
            with pytest.raises(ValueError, match="full-ml mode requires PINECONE_API_KEY"):
                validate_mode_config()
    
    @patch.dict(os.environ, {
        'APP_MODE': 'cloud-ml',
        'PINECONE_API_KEY': 'test-key',
        'HF_INFERENCE_API': 'http://test-api',
        'HF_TOKEN': 'test-token'
    })
    def test_cloud_ml_mode_validation_success(self):
        """Test that cloud-ml mode validation passes with all required credentials"""
        with patch('config.APP_MODE', AppMode.CLOUD_ML), \
             patch('config.PINECONE_API_KEY', 'test-key'), \
             patch('config.HF_INFERENCE_API', 'http://test-api'), \
             patch('config.HF_TOKEN', 'test-token'):
            validate_mode_config()  # Should pass without error
    
    @patch.dict(os.environ, {
        'APP_MODE': 'cloud-ml',
        'PINECONE_API_KEY': 'test-key'
    })
    def test_cloud_ml_mode_validation_failure_no_hf(self):
        """Test that cloud-ml mode validation fails without HF credentials"""
        with patch('config.APP_MODE', AppMode.CLOUD_ML), \
             patch('config.PINECONE_API_KEY', 'test-key'), \
             patch('config.HF_INFERENCE_API', None), \
             patch('config.HF_TOKEN', None):
            with pytest.raises(ValueError, match="cloud-ml mode requires HF_INFERENCE_API and HF_TOKEN"):
                validate_mode_config()
    
    @patch.dict(os.environ, {
        'APP_MODE': 'cloud-ml',
        'HF_INFERENCE_API': 'http://test-api',
        'HF_TOKEN': 'test-token'
    })
    def test_cloud_ml_mode_validation_failure_no_pinecone(self):
        """Test that cloud-ml mode validation fails without Pinecone key"""
        with patch('config.APP_MODE', AppMode.CLOUD_ML), \
             patch('config.PINECONE_API_KEY', None), \
             patch('config.HF_INFERENCE_API', 'http://test-api'), \
             patch('config.HF_TOKEN', 'test-token'):
            with pytest.raises(ValueError, match="cloud-ml mode requires PINECONE_API_KEY"):
                validate_mode_config()
    
    def test_hf_model_dimension(self):
        """Test that HF model dimension is correctly set"""
        from config import HF_MODEL_DIMENSION
        assert HF_MODEL_DIMENSION == 768