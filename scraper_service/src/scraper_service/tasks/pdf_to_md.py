import os
import time
import glob
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pdfplumber
import pandas as pd

from scraper_service.celery_app import celery_app
from scraper_service.config import Settings

settings = Settings()

BLACKLIST = [
    'cookie-policy', 'politic', 'privacy', 'offer-cervice',
    'personal-data', 'legal-information', 'usage-terms',
    'recommendation-technologies-rules'
]

ALLOWED_PREFIXES = [
    '/documents/tariffs/'
]


def setup_browser():
    """Setup Playwright browser"""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = context.new_page()
    return playwright, browser, context, page


def download_and_process_pdf(url, folder=None, line_limit=None):
    if folder is None:
        folder = settings.cloud_docs_folder
    if line_limit is None:
        line_limit = settings.markdown_line_limit

    file_name_base = url.split('/')[-1].split('?')[0].lower()
    if file_name_base.endswith('.pdf'):
        file_name_base = file_name_base[:-4]

    if any(bad_word in file_name_base for bad_word in BLACKLIST):
        return None

    if not os.path.exists(folder):
        os.makedirs(folder)

    pdf_path = os.path.join(folder, file_name_base + ".pdf")
    md_path = os.path.join(folder, file_name_base + ".md")

    try:
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code == 200:
            with open(pdf_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

            all_tables_md = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table_data in tables:
                        if table_data:
                            headers = table_data[0]
                            rows = table_data[1:]
                            df = pd.DataFrame(rows, columns=headers)
                            all_tables_md.append(df.to_markdown(index=False))

            processed_content = "\n\n".join([md for md in all_tables_md if md.strip()])

            if processed_content:
                lines = processed_content.strip().split('\n')
                if len(lines) > line_limit:
                    truncated_lines = lines[:line_limit]
                    processed_content = "\n".join(truncated_lines) + "\n... (truncated)"
                else:
                    processed_content = processed_content.strip()
            else:
                return None

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)

            return md_path
    except Exception as e:
        print(f"Error processing {url}: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    return None


def crawl(playwright, browser, context, page, url, current_depth, max_depth, visited):
    results = []
    if current_depth > max_depth or url in visited:
        return results

    visited.add(url)

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        soup = BeautifulSoup(page.content(), 'html.parser')

        pdf_links = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
        for pdf_link in pdf_links:
            md_path = download_and_process_pdf(urljoin(url, pdf_link))
            if md_path:
                results.append(md_path)
                break

        if current_depth < max_depth:
            sub_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc == urlparse(url).netloc:
                    if any(prefix in full_url for prefix in ALLOWED_PREFIXES):
                        if full_url not in visited:
                            sub_links.append(full_url)

            for link in sub_links:
                results.extend(crawl(playwright, browser, context, page, link, current_depth + 1, max_depth, visited))

    except Exception as e:
        print(f"Error crawling {url}: {e}")

    return results


@celery_app.task(bind=True, name="scraper_service.tasks.pdf_to_md.crawl_cloud_ru")
def crawl_cloud_ru(self, start_url="https://cloud.ru/documents/tariffs/index", max_depth=5):
    playwright, browser, context, page = setup_browser()
    visited = set()
    try:
        md_files = crawl(playwright, browser, context, page, start_url, 0, max_depth, visited)
        return {"status": "completed", "md_files": md_files, "count": len(md_files)}
    finally:
        page.close()
        context.close()
        browser.close()
        playwright.stop()