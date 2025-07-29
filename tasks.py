from celery import Celery
from celery.schedules import crontab
from config import (
    REDIS_URL, HN_HIRING_URL, REMOTEOK_API_URL, ARBEITNOW_API_URL, THEMUSE_API_URL,
    JOB_FILTER_KEYWORDS, JOB_FILTER_LOCATIONS, JOB_EXCLUDE_KEYWORDS
)
from scraper import (
    get_job_postings, scrape_remoteok_api, scrape_arbeitnow_api, scrape_themusedev_api,
    deduplicate_jobs, filter_jobs
)
from indexing import embed_and_index

# Initialize Celery
celery_app = Celery(
    "job_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional: Configure Celery to automatically discover tasks
celery_app.autodiscover_tasks()

@celery_app.task
def crawl_and_index():
    """The main background task to be run periodically."""
    print("--- [Celery Task] Starting job crawl and index ---")
    
    # Collect jobs from multiple sources
    all_jobs = []
    
    # Scrape Hacker News
    try:
        hn_jobs = get_job_postings(HN_HIRING_URL)
        if hn_jobs:
            all_jobs.extend(hn_jobs)
            print(f"Added {len(hn_jobs)} jobs from Hacker News")
    except Exception as e:
        print(f"Error scraping Hacker News: {e}")
    
    # Scrape Remote OK
    try:
        ro_jobs = scrape_remoteok_api(REMOTEOK_API_URL)
        if ro_jobs:
            all_jobs.extend(ro_jobs)
            print(f"Added {len(ro_jobs)} jobs from Remote OK")
    except Exception as e:
        print(f"Error scraping Remote OK: {e}")
    
    # Scrape Arbeit Now
    try:
        an_jobs = scrape_arbeitnow_api(ARBEITNOW_API_URL)
        if an_jobs:
            all_jobs.extend(an_jobs)
            print(f"Added {len(an_jobs)} jobs from Arbeit Now")
    except Exception as e:
        print(f"Error scraping Arbeit Now: {e}")
    
    # Scrape The Muse
    try:
        tm_jobs = scrape_themusedev_api(THEMUSE_API_URL)
        if tm_jobs:
            all_jobs.extend(tm_jobs)
            print(f"Added {len(tm_jobs)} jobs from The Muse")
    except Exception as e:
        print(f"Error scraping The Muse: {e}")
    
    if not all_jobs:
        print("No jobs found from any source")
        return
    
    print(f"Total jobs collected: {len(all_jobs)}")
    
    # Apply deduplication
    unique_jobs = deduplicate_jobs(all_jobs)
    
    # Apply filtering (optional - can be disabled by setting empty lists in config)
    if JOB_FILTER_KEYWORDS or JOB_FILTER_LOCATIONS or JOB_EXCLUDE_KEYWORDS:
        filtered_jobs = filter_jobs(
            unique_jobs,
            keywords=JOB_FILTER_KEYWORDS if JOB_FILTER_KEYWORDS else None,
            locations=JOB_FILTER_LOCATIONS if JOB_FILTER_LOCATIONS else None,
            exclude_keywords=JOB_EXCLUDE_KEYWORDS if JOB_EXCLUDE_KEYWORDS else None
        )
    else:
        filtered_jobs = unique_jobs
        print("No filtering applied - using all unique jobs")
    
    # Index the final processed jobs
    if filtered_jobs:
        print(f"Final jobs to index: {len(filtered_jobs)}")
        embed_and_index(filtered_jobs)
    else:
        print("No jobs remaining after filtering")
    
    print("--- [Celery Task] Job crawl and index finished ---")

# Define a periodic task schedule (Celery Beat)
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run the task every day at 2 AM UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        crawl_and_index.s(),
        name='Crawl and index jobs daily'
    )
    # For testing, let's also run it 60 seconds after startup
    sender.add_periodic_task(60.0, crawl_and_index.s(), name='Crawl and index on startup (test)')