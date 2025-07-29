"""
Core interfaces for dependency injection and abstraction.

This module defines the contract interfaces that different implementations
must follow, enabling easy swapping of services and testing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

# Database Interfaces
class VectorDatabaseInterface(ABC):
    """Interface for vector database operations"""
    
    @abstractmethod
    async def search(self, vector: List[float], k: int, namespace: str = None) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def upsert(self, vectors: List[Dict[str, Any]], namespace: str = None) -> bool:
        """Insert or update vectors"""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str], namespace: str = None) -> bool:
        """Delete vectors by IDs"""
        pass

class CacheInterface(ABC):
    """Interface for caching operations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set cached value with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        pass

class DocumentDatabaseInterface(ABC):
    """Interface for document database operations"""
    
    @abstractmethod
    async def find_one(self, collection: str, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find single document"""
        pass
    
    @abstractmethod
    async def find_many(self, collection: str, filter: Dict[str, Any], limit: int = None) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        pass
    
    @abstractmethod
    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert single document, return ID"""
        pass
    
    @abstractmethod
    async def update_one(self, collection: str, filter: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update single document"""
        pass

# ML Service Interfaces
class EmbeddingServiceInterface(ABC):
    """Interface for text embedding services"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass

class RerankingServiceInterface(ABC):
    """Interface for reranking services"""
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Rerank documents based on query relevance"""
        pass

# Message Queue Interfaces
class MessageQueueInterface(ABC):
    """Interface for message queue operations"""
    
    @abstractmethod
    async def publish(self, queue: str, message: Dict[str, Any]) -> bool:
        """Publish message to queue"""
        pass
    
    @abstractmethod
    async def consume(self, queue: str, callback) -> None:
        """Consume messages from queue"""
        pass

# Storage Interfaces
class StorageInterface(ABC):
    """Interface for file/object storage"""
    
    @abstractmethod
    async def upload(self, key: str, data: bytes, metadata: Dict[str, Any] = None) -> str:
        """Upload data and return URL"""
        pass
    
    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data by key"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete object by key"""
        pass

# Monitoring Interfaces
class MetricsInterface(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    def increment_counter(self, name: str, tags: Dict[str, str] = None) -> None:
        """Increment counter metric"""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record histogram value"""
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set gauge value"""
        pass

class LoggerInterface(ABC):
    """Interface for structured logging"""
    
    @abstractmethod
    def info(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log info message"""
        pass
    
    @abstractmethod
    def error(self, message: str, extra: Dict[str, Any] = None, exc_info: bool = False) -> None:
        """Log error message"""
        pass
    
    @abstractmethod
    def warning(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log warning message"""
        pass