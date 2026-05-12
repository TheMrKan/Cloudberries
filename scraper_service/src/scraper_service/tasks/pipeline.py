from celery import chain, group
from scraper_service.celery_app import celery_app
from scraper_service.tasks.pdf_to_md import crawl_cloud_ru
from scraper_service.tasks.md_to_json import process_md_file, process_md_batch
from scraper_service.tasks.json_to_db import save_to_database
from scraper_service.tasks.parse_direct_pdfs import parse_all_direct_pdfs

@celery_app.task(name="scraper_service.tasks.pipeline.run_full_pipeline")
def run_full_pipeline(start_url="https://cloud.ru/documents/tariffs/index", max_depth=5, provider_hint=""):
    """
    Правильный Pipeline: PDF -> MD -> [Группа JSON] -> [Группа DB]
    Используем подписи (.s()) для передачи данных между задачами.
    """
    workflow = chain(
        crawl_cloud_ru.s(start_url, max_depth),
        handle_md_files.s(provider_hint)
    )
    workflow.apply_async()
    return {"status": "started", "message": "Pipeline workflow initiated"}

@celery_app.task(name="scraper_service.tasks.pipeline.handle_md_files")
def handle_md_files(md_files_result, provider_hint):
    """
    Эта задача получает список файлов и создает веер (group) задач.
    """
    if not md_files_result or md_files_result.get("status") != "completed":
        return {"status": "error", "detail": "Crawl failed"}

    md_files = md_files_result.get("md_files", [])
    
    if not md_files:
        return {"status": "completed", "message": "No files to process"}

    # Создаем группу задач: для каждого файла своя цепочка (MD -> JSON -> DB)
    job_group = group(
        chain(
            process_md_file.s(md_path, provider_hint),
            handle_save_to_db.s()
        )
        for md_path in md_files
    )
    
    job_group.apply_async()
    return {"status": "processing", "files_count": len(md_files)}

@celery_app.task(name="scraper_service.tasks.pipeline.handle_save_to_db")
def handle_save_to_db(json_data):
    """
    Вспомогательная задача для сохранения, если предыдущий шаг успешен.
    """
    if json_data and json_data.get("status") == "completed":
        save_to_database.delay(json_data["json_path"])
        return {"status": "saved", "path": json_data["json_path"]}
    return {"status": "skipped"}