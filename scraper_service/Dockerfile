FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

RUN playwright install --with-deps chromium

COPY src/ src/

CMD ["celery", "-A", "scraper_service.celery_app", "worker", "--loglevel=info", "--concurrency=2"]