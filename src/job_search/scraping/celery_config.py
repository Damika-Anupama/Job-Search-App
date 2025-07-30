"""
Production-ready Celery configuration.

This module provides optimized Celery settings for production deployment
with proper logging, monitoring, and error handling.
"""

import os
from celery.schedules import crontab

# Broker and backend configuration
broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Serialization settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Task execution settings
task_always_eager = False  # Set to True for synchronous testing
task_eager_propagates = True
task_ignore_result = False  # Keep results for monitoring
task_store_eager_result = True

# Worker settings
worker_prefetch_multiplier = 4  # Number of tasks to prefetch per worker
worker_max_tasks_per_child = 1000  # Restart worker after N tasks (prevents memory leaks)
worker_disable_rate_limits = False

# Task routing
task_routes = {
    'job_search.scraping.tasks.crawl_and_index': {'queue': 'scraping'},
    'job_search.scraping.tasks.health_check': {'queue': 'monitoring'},
    'job_search.scraping.tasks.test_task': {'queue': 'testing'},
}

# Task time limits (in seconds)
task_soft_time_limit = 3600  # 1 hour soft limit
task_time_limit = 3900  # 65 minutes hard limit (gives 5 min for cleanup)

# Result expiration
result_expires = 3600  # Results expire after 1 hour

# Beat schedule (periodic tasks)
beat_schedule = {
    'daily-job-scraping': {
        'task': 'job_search.scraping.tasks.crawl_and_index',
        'schedule': crontab(hour=2, minute=0),  # 2 AM UTC daily
        'options': {
            'queue': 'scraping',
            'routing_key': 'scraping',
        }
    },
    'health-check': {
        'task': 'job_search.scraping.tasks.health_check',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'options': {
            'queue': 'monitoring',
            'routing_key': 'monitoring',
        }
    },
    # Optional: Business hours scraping (uncomment to enable)
    # 'business-hours-scraping': {
    #     'task': 'job_search.scraping.tasks.crawl_and_index',
    #     'schedule': crontab(hour='9,12,15,18', minute=0, day_of_week='1-5'),
    #     'options': {
    #         'queue': 'scraping',
    #         'routing_key': 'scraping',
    #     }
    # },
}

# Logging configuration
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(name)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'

# Worker concurrency
worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '2'))

# Monitoring and health checks
worker_send_task_events = True
task_send_sent_event = True

# Security settings (for production)
task_reject_on_worker_lost = True
task_acks_late = True  # Acknowledge task after completion (safer for critical tasks)

# Error handling
task_reject_on_worker_lost = True
task_acks_late = True

# Broker connection settings
broker_connection_retry = True
broker_connection_retry_on_startup = True
broker_connection_max_retries = 10

# Advanced settings for production
worker_pool_restarts = True  # Enable pool restarts for better memory management

# Rate limiting (tasks per time period)
task_annotations = {
    'job_search.scraping.tasks.crawl_and_index': {
        'rate_limit': '10/h',  # Max 10 scraping tasks per hour
        'time_limit': 3600,    # 1 hour time limit
        'soft_time_limit': 3300,  # 55 minutes soft limit
    },
    'job_search.scraping.tasks.health_check': {
        'rate_limit': '120/h',  # Max 120 health checks per hour
        'time_limit': 30,       # 30 seconds time limit
    }
}

# Environment-specific overrides
if os.getenv('CELERY_ENVIRONMENT') == 'development':
    # Development settings
    task_always_eager = False
    worker_log_level = 'DEBUG'
    task_eager_propagates = True
    
elif os.getenv('CELERY_ENVIRONMENT') == 'testing':
    # Testing settings
    task_always_eager = True  # Synchronous execution for tests
    task_eager_propagates = True
    result_backend = 'cache+memory://'
    
elif os.getenv('CELERY_ENVIRONMENT') == 'production':
    # Production settings
    worker_log_level = 'INFO'
    worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))
    task_soft_time_limit = 7200  # 2 hours for production
    task_time_limit = 7500       # 2h 5min hard limit

# Security settings for production
if os.getenv('CELERY_SECURE', 'false').lower() == 'true':
    # Enable additional security measures
    task_reject_on_worker_lost = True
    task_acks_late = True
    worker_hijack_root_logger = False
    worker_log_color = False

# Monitoring integration (for production monitoring tools)
if os.getenv('ENABLE_CELERY_MONITORING', 'false').lower() == 'true':
    # Enable monitoring events
    worker_send_task_events = True
    task_send_sent_event = True
    
    # Add monitoring tasks
    beat_schedule['system-monitoring'] = {
        'task': 'job_search.scraping.tasks.system_health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {
            'queue': 'monitoring',
        }
    }