from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Service, Provider


async def bm25_search(
    db: AsyncSession,
    keywords: list[str],
    fz_filter: bool | None = None,
    regions: list[str] | None = None,
) -> list[dict]:
    if not keywords:
        return []

    clean = [k.strip() for k in keywords if k.strip()]
    if not clean:
        return []

    ilike_conditions = []
    for kw in clean:
        pattern = f"%{kw}%"
        ilike_conditions.append(
            or_(
                Service.name.ilike(pattern),
                Service.description.ilike(pattern),
                Provider.name.ilike(pattern),
            )
        )

    stmt = (
        select(
            Service.service_id,
            Service.name,
            Service.description,
            Service.pricing_elements,
            Service.compliance_tags,
            Service.regions,
            Provider.name.label("provider_name"),
        )
        .join(Provider, Provider.provider_id == Service.provider_id)
        .where(or_(*ilike_conditions))
    )

    if fz_filter:
        stmt = stmt.where(Service.compliance_tags.contains(["152-FZ"]))

    if regions:
        stmt = stmt.where(Service.regions.has_any(regions))

    result = await db.execute(stmt)
    rows = result.mappings().all()

    scored = []
    for row in rows:
        text = (
            f"{row['name']} {row['description'] or ''} {row['provider_name']}".lower()
        )
        match_count = sum(1 for k in clean if k.lower() in text)
        scored.append(
            {
                "service_id": row["service_id"],
                "name": row["name"],
                "provider_name": row["provider_name"],
                "compliance_tags": row["compliance_tags"]
                if isinstance(row["compliance_tags"], list)
                else [],
                "regions": row["regions"] if isinstance(row["regions"], list) else [],
                "pricing_elements": row["pricing_elements"]
                if isinstance(row["pricing_elements"], list)
                else [],
                "score": match_count / len(clean),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
