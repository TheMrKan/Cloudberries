import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper_service.celery_app import celery_app
from scraper_service.config import Settings
from scraper_service.models import BaseModel, Provider, ServiceType, Service, ServiceParameterValue

settings = Settings()


def get_sync_engine():
    """Create a synchronous engine from the async db_url."""
    db_url = settings.db_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return create_engine(db_url, echo=settings.db_echo)


@celery_app.task(bind=True, name="scraper_service.tasks.json_to_db.save_to_database")
def save_to_database(self, json_file_path: str):
    if not os.path.exists(json_file_path):
        return {"status": "error", "message": f"File not found: {json_file_path}"}

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
        }
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


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