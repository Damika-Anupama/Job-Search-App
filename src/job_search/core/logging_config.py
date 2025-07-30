"""
Centralized logging configuration for the job search application.

This module provides structured logging with proper formatting, handlers,
and log levels for different environments and components.
"""

import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to log level
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # Add module info for better debugging
        if hasattr(record, 'module'):
            record.module_info = f"[{record.module}]"
        else:
            record.module_info = f"[{record.name}]"
        
        return super().format(record)

def get_logging_config(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to files
        log_dir: Directory for log files
        
    Returns:
        Logging configuration dictionary
    """
    
    # Create logs directory if it doesn't exist
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
    
    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '[{asctime}] {levelname:8} | {name:25} | {funcName:15} | {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '[{asctime}] {levelname} | {module_info:20} | {message}',
                'style': '{',
                'datefmt': '%H:%M:%S'
            },
            'colored': {
                '()': ColoredFormatter,
                'format': '[{asctime}] {levelname:8} | {module_info:20} | {message}',
                'style': '{',
                'datefmt': '%H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'colored',
                'stream': sys.stdout
            }
        },
        'loggers': {
            # Application loggers
            'job_search': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'job_search.api': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'job_search.core': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'job_search.ml': {
                'level': log_level,
                'handlers': ['console'], 
                'propagate': False
            },
            'job_search.scraping': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'job_search.db': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            # Third-party loggers
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'celery': {
                'level': 'INFO', 
                'handlers': ['console'],
                'propagate': False
            },
            'requests': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }
    
    # Add file handlers if requested
    if log_to_file:
        # Main application log
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filename': str(Path(log_dir) / 'job_search.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
        
        # Error log
        config['handlers']['error_file'] = {
            'class': 'logging.handlers.RotatingFileHandler', 
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': str(Path(log_dir) / 'errors.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'encoding': 'utf-8'
        }
        
        # Scraping log (for background tasks)
        config['handlers']['scraping_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed', 
            'filename': str(Path(log_dir) / 'scraping.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'encoding': 'utf-8'
        }
        
        # Add file handlers to loggers
        for logger_name in ['job_search', 'job_search.api', 'job_search.core', 
                           'job_search.ml', 'job_search.db']:
            config['loggers'][logger_name]['handlers'].extend(['file', 'error_file'])
        
        # Scraping gets its own log file
        config['loggers']['job_search.scraping']['handlers'].extend(['scraping_file', 'error_file'])
        
        # Add file handlers to root
        config['root']['handlers'].extend(['file', 'error_file'])
    
    return config

def setup_logging(
    log_level: str = None,
    log_to_file: bool = None,
    log_dir: str = None
):
    """
    Setup application logging.
    
    Args:
        log_level: Override log level from environment
        log_to_file: Override file logging from environment  
        log_dir: Override log directory from environment
    """
    
    # Get configuration from environment or defaults
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO').upper()
    log_to_file = log_to_file if log_to_file is not None else os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    log_dir = log_dir or os.getenv('LOG_DIR', 'logs')
    
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_levels:
        log_level = 'INFO'
    
    # Get and apply configuration
    logging_config = get_logging_config(
        log_level=log_level,
        log_to_file=log_to_file,
        log_dir=log_dir
    )
    
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger('job_search.core.logging')
    logger.info(f"Logging initialized - Level: {log_level}, File logging: {log_to_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with consistent naming.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# Convenience function for module-level usage
def create_module_logger(module_name: str) -> logging.Logger:
    """
    Create a logger for a specific module with enhanced context.
    
    Args:
        module_name: Name of the module (__name__)
        
    Returns:
        Logger with module context
    """
    logger = logging.getLogger(module_name)
    
    # Add module context to all log records
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.module = module_name.split('.')[-1] if '.' in module_name else module_name
        return record
    
    logging.setLogRecordFactory(record_factory)
    
    return logger

# Example usage and testing
if __name__ == "__main__":
    # Test the logging configuration
    setup_logging(log_level="DEBUG", log_to_file=True)
    
    logger = get_logger("test_module")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")  
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print("Logging test completed - check logs/ directory for output files")