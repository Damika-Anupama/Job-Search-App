"""
Celery tasks for job scraping and indexing.

This module defines background tasks for:
- Scraping jobs from multiple sources
- Deduplication and filtering
- Indexing jobs for search

Uses structured logging instead of print statements.
"""

import os
from celery import Celery
from celery.schedules import crontab
from typing import List, Dict, Any
from .scrapers import (
    get_job_postings as scrape_hackernews_jobs,
    scrape_remoteok_api as scrape_remoteok_jobs, 
    scrape_arbeitnow_api as scrape_arbeitnow_jobs, 
    scrape_themusedev_api as scrape_themuse_jobs, 
    deduplicate_jobs, 
    filter_jobs
)
from ..core.logging_config import get_logger

# Setup logging for this module
logger = get_logger(__name__)

# Redis URL from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery
celery_app = Celery(
    "job_search_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure Celery with inline settings (more reliable for Docker)
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'src.job_search.scraping.tasks.*': {'queue': 'scraping'},
    },
    
    # Task time limits
    task_soft_time_limit=3600,  # 1 hour
    task_time_limit=3900,       # 65 minutes
    
    # Worker settings
    worker_prefetch_multiplier=2,
    worker_max_tasks_per_child=1000,
    
    # Result expiration
    result_expires=3600,  # 1 hour
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@celery_app.task(bind=True, max_retries=3)
def crawl_and_index(self):
    """
    Main background task to scrape jobs from multiple sources and index them.
    
    This task:
    1. Scrapes jobs from multiple sources (HackerNews, RemoteOK, etc.)
    2. Deduplicates job listings
    3. Applies filtering if configured
    4. Indexes jobs for search
    
    Args:
        self: Celery task instance (for retries)
    """
    try:
        logger.info("🔄 Starting job crawl and index task")
        
        # Collect jobs from multiple sources
        all_jobs = []
        sources_scraped = 0
        
        # Job source URLs
        HN_URL = "https://news.ycombinator.com/item?id=30000000"  # Placeholder - should be current month
        REMOTEOK_URL = "https://remoteok.io/api"
        ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
        THEMUSE_URL = "https://www.themuse.com/api/public/jobs"
        
        # Scrape Hacker News
        try:
            logger.info("📰 Scraping Hacker News jobs")
            hn_jobs = scrape_hackernews_jobs(HN_URL)
            if hn_jobs:
                all_jobs.extend(hn_jobs)
                sources_scraped += 1
                logger.info(f"✅ Added {len(hn_jobs)} jobs from Hacker News")
            else:
                logger.warning("⚠️ No jobs found from Hacker News")
        except Exception as e:
            logger.error(f"❌ Error scraping Hacker News: {e}")
        
        # Scrape Remote OK
        try:
            logger.info("🌍 Scraping Remote OK jobs")
            ro_jobs = scrape_remoteok_jobs(REMOTEOK_URL)
            if ro_jobs:
                all_jobs.extend(ro_jobs)
                sources_scraped += 1
                logger.info(f"✅ Added {len(ro_jobs)} jobs from Remote OK")
            else:
                logger.warning("⚠️ No jobs found from Remote OK")
        except Exception as e:
            logger.error(f"❌ Error scraping Remote OK: {e}")
        
        # Scrape Arbeit Now
        try:
            logger.info("💼 Scraping Arbeit Now jobs")
            an_jobs = scrape_arbeitnow_jobs(ARBEITNOW_URL)
            if an_jobs:
                all_jobs.extend(an_jobs)
                sources_scraped += 1
                logger.info(f"✅ Added {len(an_jobs)} jobs from Arbeit Now")
            else:
                logger.warning("⚠️ No jobs found from Arbeit Now")
        except Exception as e:
            logger.error(f"❌ Error scraping Arbeit Now: {e}")
        
        # Scrape The Muse
        try:
            logger.info("🎯 Scraping The Muse jobs")
            tm_jobs = scrape_themuse_jobs(THEMUSE_URL)  
            if tm_jobs:
                all_jobs.extend(tm_jobs)
                sources_scraped += 1
                logger.info(f"✅ Added {len(tm_jobs)} jobs from The Muse")
            else:
                logger.warning("⚠️ No jobs found from The Muse")
        except Exception as e:
            logger.error(f"❌ Error scraping The Muse: {e}")
        
        if not all_jobs:
            logger.error("❌ No jobs found from any source")
            if sources_scraped == 0:
                # If no sources worked, retry the task
                logger.warning(f"🔄 Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
                raise self.retry(countdown=300)  # Retry in 5 minutes
            return {"status": "completed", "jobs_processed": 0, "message": "No jobs found"}
        
        logger.info(f"📊 Total jobs collected: {len(all_jobs)} from {sources_scraped} sources")
        
        # Apply deduplication
        logger.info("🔄 Deduplicating jobs")
        unique_jobs = deduplicate_jobs(all_jobs)
        duplicates_removed = len(all_jobs) - len(unique_jobs)
        if duplicates_removed > 0:
            logger.info(f"🗑️ Removed {duplicates_removed} duplicate jobs")
        
        # Apply filtering (get from environment)
        filter_keywords = os.getenv('JOB_FILTER_KEYWORDS', '').split(',') if os.getenv('JOB_FILTER_KEYWORDS') else []
        filter_locations = os.getenv('JOB_FILTER_LOCATIONS', '').split(',') if os.getenv('JOB_FILTER_LOCATIONS') else []
        exclude_keywords = os.getenv('JOB_EXCLUDE_KEYWORDS', '').split(',') if os.getenv('JOB_EXCLUDE_KEYWORDS') else []
        
        # Clean up empty strings
        filter_keywords = [k.strip() for k in filter_keywords if k.strip()]
        filter_locations = [l.strip() for l in filter_locations if l.strip()]
        exclude_keywords = [e.strip() for e in exclude_keywords if e.strip()]
        
        if filter_keywords or filter_locations or exclude_keywords:
            logger.info("🔍 Applying job filters")
            filtered_jobs = filter_jobs(
                unique_jobs,
                keywords=filter_keywords if filter_keywords else None,
                locations=filter_locations if filter_locations else None,
                exclude_keywords=exclude_keywords if exclude_keywords else None
            )
            filtered_count = len(unique_jobs) - len(filtered_jobs)
            if filtered_count > 0:
                logger.info(f"🗂️ Filtered out {filtered_count} jobs")
        else:
            filtered_jobs = unique_jobs
            logger.info("ℹ️ No filtering applied - using all unique jobs")
        
        # Index the final processed jobs
        if filtered_jobs:
            logger.info(f"📥 Indexing {len(filtered_jobs)} jobs")
            
            try:
                # Try to import and use the indexing function
                from ..ml.indexing import embed_and_index
                embed_and_index(filtered_jobs)
                logger.info("✅ Jobs successfully indexed")
            except ImportError:
                logger.warning("⚠️ ML indexing not available - jobs collected but not indexed")
            except Exception as e:
                logger.error(f"❌ Error during indexing: {e}")
                # Don't fail the task if indexing fails - jobs were still collected
        else:
            logger.warning("⚠️ No jobs remaining after filtering")
        
        logger.info("🎉 Job crawl and index task completed successfully")
        
        return {
            "status": "completed",
            "jobs_collected": len(all_jobs),
            "jobs_unique": len(unique_jobs),
            "jobs_final": len(filtered_jobs),
            "duplicates_removed": duplicates_removed,
            "sources_scraped": sources_scraped
        }
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in crawl_and_index task: {e}")
        # Retry on unexpected errors
        if self.request.retries < self.max_retries:
            logger.warning(f"🔄 Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=600)  # Retry in 10 minutes
        else:
            logger.error("❌ Max retries exceeded - task failed")
            raise

@celery_app.task
def health_check():
    """Simple health check task for monitoring"""
    logger.info("💓 Celery health check task executed")
    return {
        "status": "healthy", 
        "worker": "job_search_worker",
        "timestamp": "2024-01-01T00:00:00Z"  # This would be dynamic in real implementation
    }

# Define periodic task schedule (Celery Beat)
@celery_app.on_after_configure.connect  
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for Celery Beat scheduler"""
    
    logger.info("📅 Setting up periodic tasks")
    
    # Main job scraping task - run daily at 2 AM UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        crawl_and_index.s(),
        name='Daily job scraping at 2 AM UTC'
    )
    
    # Health check task - run every 30 minutes for monitoring  
    sender.add_periodic_task(
        crontab(minute='*/30'),
        health_check.s(),
        name='Health check every 30 minutes'
    )
    
    # Optional: More frequent scraping during business hours (disabled by default)
    # Uncomment to enable business hours scraping
    # sender.add_periodic_task(
    #     crontab(hour='9,12,15,18', minute=0, day_of_week='1-5'),  # 9am, 12pm, 3pm, 6pm on weekdays
    #     crawl_and_index.s(),
    #     name='Business hours job scraping'
    # )
    
    logger.info("✅ Periodic tasks configured")

# For testing purposes
@celery_app.task
def test_task(message: str = "Hello from Celery!"):
    """Simple test task"""
    logger.info(f"📝 Test task executed with message: {message}")
    return {"status": "success", "message": message}

if __name__ == "__main__":
    # This allows running the tasks directly for testing
    logger.info("🧪 Running tasks module in test mode")
    
    # Run a simple test
    result = test_task.delay("Testing Celery setup")
    logger.info(f"Task ID: {result.id}")
    
    # For local testing, you can also run:
    # result = crawl_and_index.delay()
    # logger.info(f"Crawl task ID: {result.id}")