import pytest
from unittest.mock import Mock, patch, MagicMock
from indexing import get_embedding, embed_and_index, get_pinecone_index
from embedding_service import EmbeddingServiceError
from config import AppMode


class TestIndexing:
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service"""
        with patch('indexing.embedding_service') as mock_service:
            mock_service.get_embedding.return_value = [0.1] * 768
            yield mock_service
    
    @pytest.fixture
    def mock_pinecone(self):
        """Mock Pinecone components"""
        with patch('indexing.Pinecone') as mock_pinecone_class, \
             patch('indexing.PINECONE_API_KEY', 'test-key'), \
             patch('indexing.PINECONE_INDEX_NAME', 'test-index'):
            
            mock_pc_instance = Mock()
            mock_pinecone_class.return_value = mock_pc_instance
            
            # Mock index list and creation
            mock_pc_instance.list_indexes.return_value = []
            mock_pc_instance.create_index.return_value = None
            
            # Mock index object
            mock_index = Mock()
            mock_pc_instance.Index.return_value = mock_index
            
            yield {
                'pc_class': mock_pinecone_class,
                'pc_instance': mock_pc_instance,
                'index': mock_index
            }
    
    def test_get_embedding_full_ml_mode(self, mock_embedding_service):
        """Test get_embedding function in full-ml mode"""
        with patch('indexing.APP_MODE', AppMode.FULL_ML):
            result = get_embedding("test text")
            
            assert result == [0.1] * 768
            mock_embedding_service.get_embedding.assert_called_once_with("test text", fallback=False)
    
    def test_get_embedding_cloud_ml_mode(self, mock_embedding_service):
        """Test get_embedding function in cloud-ml mode with fallback"""
        with patch('indexing.APP_MODE', AppMode.CLOUD_ML):
            result = get_embedding("test text")
            
            assert result == [0.1] * 768
            mock_embedding_service.get_embedding.assert_called_once_with("test text", fallback=True)
    
    def test_get_embedding_lightweight_mode(self, mock_embedding_service):
        """Test get_embedding function raises error in lightweight mode"""
        with patch('indexing.APP_MODE', AppMode.LIGHTWEIGHT):
            with pytest.raises(EmbeddingServiceError, match="not supported in lightweight mode"):
                get_embedding("test text")
    
    def test_get_embedding_service_failure(self, mock_embedding_service):
        """Test get_embedding function when embedding service fails"""
        with patch('indexing.APP_MODE', AppMode.FULL_ML):
            mock_embedding_service.get_embedding.side_effect = EmbeddingServiceError("Service down")
            
            with pytest.raises(EmbeddingServiceError, match="Service down"):
                get_embedding("test text")
    
    def test_get_pinecone_index_existing(self, mock_pinecone):
        """Test get_pinecone_index when index already exists"""
        # Mock existing index
        mock_index_obj = Mock()
        mock_index_obj.name = 'test-index'
        mock_pinecone['pc_instance'].list_indexes.return_value = [mock_index_obj]
        
        index = get_pinecone_index()
        
        assert index is not None
        mock_pinecone['pc_instance'].create_index.assert_not_called()
        mock_pinecone['pc_instance'].Index.assert_called_once_with('test-index')
    
    def test_get_pinecone_index_create_new(self, mock_pinecone):
        """Test get_pinecone_index creates new index when it doesn't exist"""
        # Mock no existing indexes
        mock_pinecone['pc_instance'].list_indexes.return_value = []
        
        with patch('indexing.ServerlessSpec') as mock_spec:
            index = get_pinecone_index()
            
            assert index is not None
            mock_pinecone['pc_instance'].create_index.assert_called_once()
            mock_pinecone['pc_instance'].Index.assert_called_once_with('test-index')
    
    def test_get_pinecone_index_no_api_key(self):
        """Test get_pinecone_index raises error when API key is missing"""
        with patch('indexing.PINECONE_API_KEY', None):
            with pytest.raises(ValueError, match="PINECONE_API_KEY is not set"):
                get_pinecone_index()
    
    def test_embed_and_index_empty_jobs(self, mock_pinecone):
        """Test embed_and_index with empty job list"""
        with patch('indexing.index', mock_pinecone['index']):
            embed_and_index([])
            
            mock_pinecone['index'].upsert.assert_not_called()
    
    def test_embed_and_index_single_batch(self, mock_embedding_service, mock_pinecone):
        """Test embed_and_index with jobs that fit in single batch"""
        jobs = [
            {'id': 'job1', 'text': 'Python developer position'},
            {'id': 'job2', 'text': 'Java developer role'}
        ]
        
        with patch('indexing.index', mock_pinecone['index']), \
             patch('indexing.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.side_effect = [[0.1] * 768, [0.2] * 768]
            
            embed_and_index(jobs, batch_size=32)
            
            # Verify upsert was called once with correct vectors
            mock_pinecone['index'].upsert.assert_called_once()
            call_args = mock_pinecone['index'].upsert.call_args[1]['vectors']
            
            assert len(call_args) == 2
            assert call_args[0]['id'] == 'job1'
            assert call_args[0]['values'] == [0.1] * 768
            assert call_args[0]['metadata']['text'] == 'Python developer position'
    
    def test_embed_and_index_multiple_batches(self, mock_embedding_service, mock_pinecone):
        """Test embed_and_index with jobs requiring multiple batches"""
        jobs = [
            {'id': f'job{i}', 'text': f'Job description {i}'}
            for i in range(5)
        ]
        
        with patch('indexing.index', mock_pinecone['index']), \
             patch('indexing.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.side_effect = [[0.1] * 768] * 5
            
            embed_and_index(jobs, batch_size=2)
            
            # Should be called 3 times (2+2+1)
            assert mock_pinecone['index'].upsert.call_count == 3
    
    def test_embed_and_index_embedding_failure(self, mock_embedding_service, mock_pinecone):
        """Test embed_and_index when embedding generation fails"""
        jobs = [{'id': 'job1', 'text': 'Test job'}]
        
        with patch('indexing.index', mock_pinecone['index']), \
             patch('indexing.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.side_effect = EmbeddingServiceError("Service failed")
            
            with pytest.raises(EmbeddingServiceError):
                embed_and_index(jobs)
    
    def test_embed_and_index_pinecone_failure(self, mock_embedding_service, mock_pinecone):
        """Test embed_and_index when Pinecone upsert fails"""
        jobs = [{'id': 'job1', 'text': 'Test job'}]
        
        with patch('indexing.index', mock_pinecone['index']), \
             patch('indexing.get_embedding') as mock_get_embedding:
            
            mock_get_embedding.return_value = [0.1] * 768
            mock_pinecone['index'].upsert.side_effect = Exception("Pinecone error")
            
            with pytest.raises(Exception, match="Pinecone error"):
                embed_and_index(jobs)