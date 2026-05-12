"""
Task for parsing direct PDF URLs (T1 Cloud, Yandex Cloud, etc.)
and converting them to Markdown files.
"""
import os
import requests
from io import BytesIO
import pdfplumber
import pandas as pd

from scraper_service.celery_app import celery_app
from scraper_service.config import Settings

settings = Settings()


def extract_tables_from_pdf(pdf_url: str) -> str | None:
    """Download PDF from URL, extract tables, return markdown string."""
    all_data = []

    try:
        print(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                }
                table = page.extract_table(table_settings=table_settings)
                if table:
                    all_data.extend(table)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF from {pdf_url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

    if not all_data:
        print("No tables found.")
        return None

    if len(all_data) > 1 and all_data[0] is not None:
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
    elif len(all_data) == 1 and all_data[0] is not None:
        df = pd.DataFrame(columns=all_data[0])
    else:
        print("Could not form DataFrame.")
        return None

    df = df.replace('\n', ' ', regex=True)
    df = df.replace(r'\s+', ' ', regex=True).applymap(lambda x: str(x).strip() if pd.notna(x) else x)
    
    return df.to_markdown(index=False)


def extract_yandex_prices(pdf_url: str):
    """Extract Yandex prices from PDF - wrapper for compatibility."""
    all_data = []

    try:
        print(f"Downloading PDF from: {pdf_url}")
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                })
                if table:
                    all_data.extend(table)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading or processing PDF from {pdf_url}: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return pd.DataFrame()

    if not all_data:
        print("No tables found or extracted.")
        return pd.DataFrame()

    if len(all_data) > 1 and all_data[0] is not None:
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
    elif len(all_data) == 1 and all_data[0] is not None:
        df = pd.DataFrame(columns=all_data[0])
    else:
        print("Could not form DataFrame: Missing headers or data.")
        return pd.DataFrame()

    df = df.replace('\n', ' ', regex=True)
    df = df.replace(r'\s+', ' ', regex=True).applymap(lambda x: str(x).strip() if pd.notna(x) else x)

    return df


@celery_app.task(bind=True, name="scraper_service.tasks.parse_direct_pdfs.parse_direct_pdf")
def parse_direct_pdf(self, pdf_url: str, output_filename: str,
                     folder: str = None) -> dict:
    """
    Parse a single direct PDF URL and save as Markdown.
    """
    if folder is None:
        folder = settings.cloud_docs_folder

    if not os.path.exists(folder):
        os.makedirs(folder)

    md_content = extract_tables_from_pdf(pdf_url)

    if md_content is None:
        return {"status": "error", "message": f"Failed to extract tables from {pdf_url}"}

    md_path = os.path.join(folder, output_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return {"status": "completed", "md_file": md_path}


@celery_app.task(bind=True, name="scraper_service.tasks.parse_direct_pdfs.parse_all_direct_pdfs")
def parse_all_direct_pdfs(self, folder: str = None) -> dict:
    """
    Parse all known direct PDF URLs (T1 Cloud, Yandex Cloud).
    """
    PDF_SOURCES = [
        {
            "url": "https://t1-cloud.ru/media-files/T1Cloud/sitepages/Prilozhenie_1_Tarifnoe_prilozhenie_13_04_2026.pdf",
            "output": "t1_cloud_prices.md",
            "provider_hint": "T1 Cloud",
        },
        {
            "url": "https://storage.yandexcloud.net/cloud-www-assets/blog-assets/ru/posts/2025/11/vat-changes-ru-2025/%D0%A2%D0%B0%D1%80%D0%B8%D1%84%D1%8B_Yandex_%D0%A1loud_RU.pdf",
            "output": "yandex_cloud_prices.md",
            "provider_hint": "Yandex Cloud",
        },
    ]

    if folder is None:
        folder = settings.cloud_docs_folder

    if not os.path.exists(folder):
        os.makedirs(folder)

    results = []
    for source in PDF_SOURCES:
        result = parse_direct_pdf.apply_async(
            args=[source["url"], source["output"], folder]
        )
        data = result.get(timeout=120)
        if data.get("status") == "completed":
            results.append({
                "md_file": data["md_file"],
                "provider_hint": source["provider_hint"],
            })

    return {
        "status": "completed",
        "md_files": results,
        "count": len(results),
    }