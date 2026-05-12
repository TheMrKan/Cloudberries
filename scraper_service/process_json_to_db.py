#!/usr/bin/env python3
"""
Standalone script to process JSON files and save them to the database.
Usage: python process_json_to_db.py <json_file1> [json_file2 ...]
"""

import json
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from scraper_service.config import Settings
from scraper_service.models import BaseModel, Provider, ServiceType, Service, ServiceParameterValue

settings = Settings()


def get_sync_engine():
    """Create a synchronous engine from the async db_url."""
    db_url = settings.db_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return create_engine(db_url, echo=settings.db_echo)


def _guess_service_type_id(service_name: str) -> str:
    """Guess service type from service name."""
    name_lower = service_name.lower()

    if any(kw in name_lower for kw in ["vcpu", "cpu", "процессор", "compute", "вычисл"]):
        return "compute"
    elif any(kw in name_lower for kw in ["ram", "память", "memory", "озу"]):
        return "memory"
    elif any(kw in name_lower for kw in ["диск", "disk", "storage", "хранилищ", "hdd", "ssd", "nvme"]):
        return "storage"
    elif any(kw in name_lower for kw in ["network", "сеть", "bandwidth", "трафик", "ip"]):
        return "network"
    elif any(kw in name_lower for kw in ["load balancer", "балансировщик", "lb"]):
        return "load_balancer"
    elif any(kw in name_lower for kw in ["kubernetes", "k8s", "контейнер"]):
        return "kubernetes"
    elif any(kw in name_lower for kw in ["database", "бд", "postgresql", "mysql", "mongodb", "redis"]):
        return "database"
    else:
        return "other"


def process_json_file(json_file_path: str) -> dict:
    """
    Process a single JSON file and save to database.
    
    Args:
        json_file_path: Path to the JSON file
        
    Returns:
        Dict with status and results
    """
    if not os.path.exists(json_file_path):
        return {"status": "error", "message": f"File not found: {json_file_path}", "file": json_file_path}

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        engine = get_sync_engine()
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            provider_id = data.get("provider_id", "unknown")
            provider_name = data.get("provider_name", "Unknown Provider")

            # Upsert provider
            provider = session.query(Provider).filter_by(provider_id=provider_id).first()
            if not provider:
                provider = Provider(provider_id=provider_id, name=provider_name)
                session.add(provider)
                session.flush()

            services = data.get("services", [])
            saved_count = 0

            for svc_data in services:
                service_name = svc_data.get("name", "")
                description = svc_data.get("description")

                # Determine service type based on name
                type_id = _guess_service_type_id(service_name)

                # Get pricing elements
                pricing_elements = svc_data.get("pricing_elements", [])

                if pricing_elements:
                    for pe in pricing_elements:
                        price_val = pe.get("price", 0)
                        uom_val = pe.get("uom", "")

                        service = Service(
                            provider_id=provider_id,
                            type_id=type_id,
                            uom=uom_val,
                            price=price_val,
                        )
                        session.add(service)
                        session.flush()

                        # Store extra data as parameter values
                        extra_data = svc_data.get("extra_data", {})
                        compliance_tags = svc_data.get("compliance_tags", [])

                        # Save compliance tags as parameter
                        if compliance_tags:
                            spv = ServiceParameterValue(
                                service_id=service.service_id,
                                parameter_id="compliance",
                                value=1.0,
                            )
                            session.add(spv)

                        saved_count += 1
                else:
                    # No pricing elements, save with price=0
                    service = Service(
                        provider_id=provider_id,
                        type_id=type_id,
                        uom="",
                        price=0,
                    )
                    session.add(service)
                    session.flush()
                    saved_count += 1

            session.commit()

            return {
                "status": "completed",
                "provider_id": provider_id,
                "services_saved": saved_count,
                "file": json_file_path
            }
        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e), "file": json_file_path}
        finally:
            session.close()
    except Exception as e:
        return {"status": "error", "message": f"Failed to read/parse JSON: {str(e)}", "file": json_file_path}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python process_json_to_db.py <json_file1> [json_file2 ...]")
        print("Example: python process_json_to_db.py cloud_docs/t1_cloud_prices.json")
        sys.exit(1)

    json_files = sys.argv[1:]
    results = []

    print(f"Processing {len(json_files)} JSON file(s)...")
    print("-" * 50)

    for json_file in json_files:
        print(f"Processing: {json_file}")
        result = process_json_file(json_file)
        results.append(result)
        
        if result["status"] == "completed":
            print(f"  [OK] Saved {result['services_saved']} services for provider {result['provider_id']}")
        else:
            print(f"  [ERROR] {result['message']}")
        print()

    # Summary
    completed = sum(1 for r in results if r["status"] == "completed")
    failed = len(results) - completed
    
    print("-" * 50)
    print(f"Summary: {completed} succeeded, {failed} failed")
    
    if failed > 0:
        print("Failed files:")
        for result in results:
            if result["status"] == "error":
                print(f"  - {result['file']}: {result['message']}")
        sys.exit(1)
    else:
        print("All files processed successfully!")


if __name__ == "__main__":
    main()