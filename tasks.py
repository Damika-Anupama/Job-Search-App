from celery import Celery
from celery.schedules import crontab
from config import REDIS_URL, HN_HIRING_URL
from scraper import get_job_postings
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
    jobs = get_job_postings(HN_HIRING_URL)
    if jobs:
        embed_and_index(jobs)
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