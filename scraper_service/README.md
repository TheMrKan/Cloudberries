# Scraper Service

Separate service for cloud pricing data extraction using Celery.

## Architecture

```
PDF (cloud.ru) → Markdown → JSON (via LLM) → Database
```

## Pipeline Steps

1. **PDF → MD** (`tasks/pdf_to_md.py`): Selenium crawls cloud.ru, downloads PDFs, extracts tables to Markdown
2. **MD → JSON** (`tasks/md_to_json.py`): LLM (OpenAI API) extracts structured data from Markdown tables
3. **JSON → DB** (`tasks/json_to_db.py`): Saves structured data to PostgreSQL using the same schema as Cloudberries backend

## Setup

### 1. Install dependencies

```bash
cd scraper_service
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Required env vars:
- `OPENAI_API_KEY` — your OpenAI API key
- `DB_URL` — PostgreSQL connection string (same as Cloudberries backend)
- `REDIS_URL` — Redis connection string

### 3. Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 4. Start Celery Worker

```bash
cd scraper_service/src
celery -A scraper_service.celery_app worker --loglevel=info --concurrency=2
```

## Usage

### Run full pipeline (crawl cloud.ru → save to DB)

```python
from scraper_service.tasks.pipeline import run_full_pipeline

# Run asynchronously
result = run_full_pipeline.delay(
    start_url="https://cloud.ru/documents/tariffs/index",
    max_depth=5,
    provider_hint="Cloud.ru cloud services"
)
print(result.get(timeout=600))
```

### Run individual tasks

```python
from scraper_service.tasks.pdf_to_md import crawl_cloud_ru
from scraper_service.tasks.md_to_json import process_md_file
from scraper_service.tasks.json_to_db import save_to_database

# Step 1: Crawl and convert PDFs to MD
result = crawl_cloud_ru.delay()
md_files = result.get(timeout=600)

# Step 2: Convert MD to JSON
for md_path in md_files.get("md_files", []):
    json_result = process_md_file.delay(md_path, provider_hint="Cloud.ru")
    json_data = json_result.get(timeout=300)

    # Step 3: Save to DB
    if json_data.get("status") == "completed":
        save_to_database.delay(json_data["json_path"])
```

## Docker

```bash
docker build -t scraper-service .
docker run --env-file .env scraper-service