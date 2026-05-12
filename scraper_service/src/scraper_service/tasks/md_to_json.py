import json
import os
from openai import OpenAI

from scraper_service.celery_app import celery_app
from scraper_service.config import Settings

settings = Settings()

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction specialist. Your task is to extract cloud service pricing information from markdown tables and convert it into a structured JSON format.

Rules:
1. NEVER invent or fabricate data. Only use what is explicitly present in the markdown.
2. If a field cannot be determined from the data, use null or omit it.
3. For compliance_tags: use an empty list [] unless the text explicitly mentions compliance standards like ФЗ-152, then use ["ФЗ-152"].
4. For extra_data: always include a "name" key with a human-readable Russian name for the service.
5. For pricing_elements: extract each distinct pricing component with description, uom (unit of measure), and price.
6. Extract all available data from the markdown tables.

Output JSON schema:
{
  "provider_id": "string (lowercase, no spaces, e.g. 'cloud_ru', 'yandex_cloud', 't1_cloud')",
  "provider_name": "string (human readable name in Russian)",
  "services": [
    {
      "name": "string (service name from the data)",
      "description": "string or null",
      "compliance_tags": ["string"] or [],
      "keywords": ["string"] or [],
      "regions": ["string"] or [],
      "pricing_elements": [
        {
          "description": "string",
          "uom": "string (unit of measure, e.g. 'шт', 'ГБ', 'час', 'месяц', 'минута')",
          "price": number
        }
      ],
      "extra_data": {
        "name": "string (human-readable Russian name)"
      }
    }
  ]
}"""


def extract_json_from_markdown(md_content: str, provider_hint: str = "") -> dict:
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    user_message = f"Extract cloud service pricing data from the following markdown tables and return valid JSON:\n\n{md_content}"

    if provider_hint:
        user_message = f"Provider context: {provider_hint}\n\n" + user_message

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


def extract_json_from_markdown_batch(md_contents: list, provider_hints: list = None) -> dict:
    """
    Process multiple markdown contents in a single LLM request.
    """
    if not md_contents:
        return {}
    
    # Combine all markdown contents with separators
    combined_content = ""
    for i, md_content in enumerate(md_contents):
        provider_hint = provider_hints[i] if provider_hints and i < len(provider_hints) else ""
        if provider_hint:
            combined_content += f"--- PROVIDER: {provider_hint} ---\n\n"
        combined_content += md_content + "\n\n---\n\n"
    
    user_message = f"Extract cloud service pricing data from the following markdown tables and return valid JSON. Each section may represent a different provider, clearly marked with '--- PROVIDER: [name] ---':\n\n{combined_content}"

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


@celery_app.task(bind=True, name="scraper_service.tasks.md_to_json.process_md_file")
def process_md_file(self, md_file_path: str, provider_hint: str = ""):
    if not os.path.exists(md_file_path):
        return {"status": "error", "message": f"File not found: {md_file_path}"}

    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    if not md_content.strip():
        return {"status": "error", "message": "Empty markdown file"}

    try:
        result = extract_json_from_markdown(md_content, provider_hint)

        # Save JSON alongside the MD file
        json_path = md_file_path.replace('.md', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return {
            "status": "completed",
            "json_path": json_path,
            "services_count": len(result.get("services", [])),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="scraper_service.tasks.md_to_json.process_md_batch")
def process_md_batch(self, md_file_paths: list, provider_hints: list = None):
    """
    Process multiple MD files in a single LLM request for efficiency.
    
    Args:
        md_file_paths: List of paths to MD files
        provider_hints: Optional list of provider hints (same length as md_file_paths)
    
    Returns:
        Dict with status and results for each file
    """
    if not md_file_paths:
        return {"status": "error", "message": "No MD files provided"}
    
    # Validate all files exist
    missing_files = [path for path in md_file_paths if not os.path.exists(path)]
    if missing_files:
        return {"status": "error", "message": f"Files not found: {missing_files}"}
    
    # Read all MD contents
    md_contents = []
    for path in md_file_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return {"status": "error", "message": f"Empty markdown file: {path}"}
                md_contents.append(content)
        except Exception as e:
            return {"status": "error", "message": f"Error reading file {path}: {str(e)}"}
    
    try:
        # Process batch
        result = extract_json_from_markdown_batch(md_contents, provider_hints)
        
        # Save individual JSON files alongside their MD files
        json_paths = []
        services_counts = []
        
        # For batch processing, we need to split the result appropriately
        # Since the LLM returns combined data, we'll save the full result to each file
        # A more sophisticated approach would parse and split by provider
        for md_path in md_file_paths:
            json_path = md_path.replace('.md', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            json_paths.append(json_path)
            
            # Count services (approximate for batch)
            services_count = len(result.get("services", [])) if isinstance(result, dict) else 0
            services_counts.append(services_count)
        
        return {
            "status": "completed",
            "json_paths": json_paths,
            "services_counts": services_counts,
            "processed_count": len(md_file_paths)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}