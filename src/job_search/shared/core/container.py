"""
Dependency Injection Container for enterprise-grade service management.

This container manages all service dependencies and their lifecycles,
enabling easy testing, configuration, and service swapping.
"""

from typing import Dict, Any, Type, TypeVar, Callable, Optional
from functools import lru_cache
import inspect
from ..core.interfaces import *

T = TypeVar('T')

class ServiceContainer:
    """
    Dependency Injection Container with automatic dependency resolution.
    
    Features:
    - Singleton and transient service lifetimes
    - Automatic constructor injection
    - Interface-to-implementation binding
    - Lazy initialization
    - Configuration-based service resolution
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> 'ServiceContainer':
        """Register a service as singleton (one instance for lifetime)"""
        key = self._get_key(interface)
        self._services[key] = {
            'type': 'singleton',
            'interface': interface,
            'implementation': implementation,
            'instance': None
        }
        return self
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> 'ServiceContainer':
        """Register a service as transient (new instance each time)"""
        key = self._get_key(interface)
        self._services[key] = {
            'type': 'transient',
            'interface': interface,
            'implementation': implementation
        }
        return self
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> 'ServiceContainer':
        """Register a factory function for service creation"""
        key = self._get_key(interface)
        self._factories[key] = factory
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> 'ServiceContainer':
        """Register an existing instance"""
        key = self._get_key(interface)
        self._singletons[key] = instance
        return self
    
    def configure(self, service_type: Type[T], **config) -> 'ServiceContainer':
        """Add configuration for a service"""
        key = self._get_key(service_type)
        self._configurations[key] = config
        return self
    
    def get(self, interface: Type[T]) -> T:
        """Get service instance with automatic dependency injection"""
        key = self._get_key(interface)
        
        # Check if already cached as singleton
        if key in self._singletons:
            return self._singletons[key]
        
        # Check if factory exists
        if key in self._factories:
            instance = self._factories[key]()
            if key in self._services and self._services[key]['type'] == 'singleton':
                self._singletons[key] = instance
            return instance
        
        # Get service configuration
        if key not in self._services:
            raise ValueError(f"Service {interface.__name__} not registered")
        
        service_config = self._services[key]
        implementation = service_config['implementation']
        
        # Create instance with dependency injection
        instance = self._create_instance(implementation, key)
        
        # Cache singleton
        if service_config['type'] == 'singleton':
            self._singletons[key] = instance
        
        return instance
    
    def _create_instance(self, implementation: Type[T], service_key: str) -> T:
        """Create instance with automatic constructor dependency injection"""
        constructor = implementation.__init__
        signature = inspect.signature(constructor)
        
        kwargs = {}
        config = self._configurations.get(service_key, {})
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            # Check if parameter is in configuration
            if param_name in config:
                kwargs[param_name] = config[param_name]
                continue
            
            # Try to resolve as service dependency
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependency = self.get(param.annotation)
                    kwargs[param_name] = dependency
                except ValueError:
                    # If dependency not found and has default, use default
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise ValueError(f"Cannot resolve dependency {param.annotation.__name__} for {implementation.__name__}")
        
        return implementation(**kwargs)
    
    def _get_key(self, service_type: Type) -> str:
        """Get unique key for service type"""
        return f"{service_type.__module__}.{service_type.__name__}"
    
    def clear(self) -> None:
        """Clear all registrations (useful for testing)"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._configurations.clear()

# Global container instance
container = ServiceContainer()

def get_service(interface: Type[T]) -> T:
    """Convenience function to get service from global container"""
    return container.get(interface)

def inject(interface: Type[T]) -> Callable:
    """Decorator for dependency injection in functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_service(interface)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator

# Example usage and configuration
def configure_container() -> ServiceContainer:
    """Configure the dependency injection container with default services"""
    
    # This would be called at application startup
    # Container configuration would be driven by environment/config
    
    from ...infrastructure.database.mongodb_impl import MongoDBService
    from ...infrastructure.database.redis_impl import RedisService
    from ...infrastructure.database.pinecone_impl import PineconeService
    from ...ml.embeddings import EmbeddingService
    
    container.clear()
    
    # Register database services
    # container.register_singleton(DocumentDatabaseInterface, MongoDBService)
    # container.register_singleton(CacheInterface, RedisService)  
    # container.register_singleton(VectorDatabaseInterface, PineconeService)
    
    # Register ML services
    # container.register_singleton(EmbeddingServiceInterface, EmbeddingService)
    
    # Add configurations
    # container.configure(MongoDBService, 
    #                    connection_string=settings.MONGODB_CONNECTION_STRING,
    #                    database_name=settings.MONGODB_DATABASE_NAME)
    
    return container