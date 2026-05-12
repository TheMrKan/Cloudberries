"""
Celery worker entry point.

Start with:
    celery -A scraper_service.celery_app worker --loglevel=info --concurrency=2

Start beat scheduler (for periodic tasks):
    celery -A scraper_service.celery_app beat --loglevel=info
"""
from scraper_service.celery_app import celery_app

# Import all tasks so they are registered
import scraper_service.tasks.pdf_to_md
import scraper_service.tasks.md_to_json
import scraper_service.tasks.json_to_db
import scraper_service.tasks.pipeline