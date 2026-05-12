import os
import time
import glob
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pdfplumber
import pandas as pd

# 1. ЧЕРНЫЙ СПИСОК (что НЕ качаем)
BLACKLIST = [
    'cookie-policy', 'politic', 'privacy', 'offer-cervice',
    'personal-data', 'legal-information', 'usage-terms',
    'recommendation-technologies-rules'
]

# 2. БЕЛЫЙ СПИСОК ПРЕФИКСОВ (куда можно заходить с главной)
ALLOWED_PREFIXES = [
    '/documents/tariffs/'
]

# 3. Лимит строк для Markdown файлов (для MVP)
MARKDOWN_LINE_LIMIT = 150

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Try to find chromedriver in PATH or common locations
    driver_path = None
    if os.name == 'nt': # Windows
        # Check if chromedriver is in PATH
        from shutil import which
        if which("chromedriver"):
            driver_path = "chromedriver"
        else:
            # Common Windows locations
            paths = [
                os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads', 'chromedriver.exe'),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'chromedriver.exe'),
                'C:\\WebDriver\\bin\\chromedriver.exe',
                'C:\\chromedriver\\chromedriver.exe'
            ]
            for p in paths:
                if os.path.exists(p):
                    driver_path = p
                    break
    else: # Linux/Mac
        from shutil import which
        if which("chromedriver"):
            driver_path = "chromedriver"
        else:
            # Try glob for Colab/Linux paths
            driver_list = glob.glob('/content/chromedriver/**/chromedriver', recursive=True)
            if driver_list:
                driver_path = driver_list[0]
            elif os.path.exists('/usr/local/bin/chromedriver'):
                driver_path = '/usr/local/bin/chromedriver'
            elif os.path.exists('/usr/bin/chromedriver'):
                driver_path = '/usr/bin/chromedriver'

    if driver_path is None:
        # Fallback: assume chromedriver is in PATH or will be found by Service()
        # If not, this will raise an error
        try:
            service = Service()
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            raise FileNotFoundError(f"ChromeDriver not found. Please install it and ensure it's in PATH. Error: {e}")

    if not os.name == 'nt' and driver_path != "chromedriver":
        os.chmod(driver_path, 0o755)
        
    service = Service(executable_path=driver_path)
    return webdriver.Chrome(service=service, options=options)

def download_and_process_pdf(url, folder="cloud_docs", line_limit=MARKDOWN_LINE_LIMIT):
    file_name_base = url.split('/')[-1].split('?')[0].lower()
    if file_name_base.endswith('.pdf'):
        file_name_base = file_name_base[:-4]

    if any(bad_word in file_name_base for bad_word in BLACKLIST):
        return False

    if not os.path.exists(folder):
        os.makedirs(folder)

    pdf_path = os.path.join(folder, file_name_base + ".pdf")
    md_path = os.path.join(folder, file_name_base + ".md")

    try:
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code == 200:
            with open(pdf_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
            print(f"   [OK] Скачан PDF: {file_name_base}.pdf")

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
                    processed_content = "\n".join(truncated_lines) + "\n... (Содержание обрезано до " + str(line_limit) + " строк)"
                else:
                    processed_content = processed_content.strip()
            else:
                print(f"   [INFO] PDF {file_name_base}.pdf не содержит табличных данных для сохранения.")
                return False

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            print(f"   [OK] Сконвертирован и сохранен MD: {file_name_base}.md")
            return True
        else:
            print(f"   [ERROR] Не удалось скачать PDF с {url}. Статус: {r.status_code}")
    except Exception as e:
        print(f"   [ERROR] Произошла ошибка при обработке {url}: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"   [INFO] Удален временный PDF: {file_name_base}.pdf")
    return False

def crawl(driver, url, current_depth, max_depth, visited):
    if current_depth > max_depth or url in visited:
        return

    visited.add(url)
    print(f"{'  ' * current_depth}👉 Уровень {current_depth}: {url}")

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        pdf_links = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
        for pdf_link in pdf_links:
            if download_and_process_pdf(urljoin(url, pdf_link)):
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
                crawl(driver, link, current_depth + 1, max_depth, visited)

    except Exception as e:
        print(f"Ошибка: {e}")

def run_crawler(start_url, max_depth=2):
    driver = setup_driver()
    visited = set()
    try:
        crawl(driver, start_url, 0, max_depth, visited)
    finally:
        driver.quit()
        print("\nГотово. Скрипт прошел только по заданным префиксам и сохранил данные в Markdown.")

if __name__ == "__main__":
    TARGET = "https://cloud.ru/documents/tariffs/index"
    run_crawler(TARGET, max_depth=5)