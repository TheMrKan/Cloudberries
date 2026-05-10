import re

from rank_bm25 import BM25Okapi


_engine: "KeywordSearchEngine | None" = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _build_document_text(service: dict) -> str:
    return " ".join(service.get("keywords") or [])


class KeywordSearchEngine:
    def __init__(self):
        self._services: list[dict] = []
        self._corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def load(self, services: list[dict]):
        self._services = services
        self._corpus = [_tokenize(_build_document_text(s)) for s in services]
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
        else:
            self._bm25 = None

    @property
    def is_loaded(self) -> bool:
        return self._bm25 is not None

    def search(
        self,
        query: str,
        compliance_filter: list[str] | None = None,
        regions: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        if not self._bm25 or not self._services:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        indexed = list(range(len(self._services)))
        indexed.sort(key=lambda i: scores[i], reverse=True)

        results = []
        for idx in indexed:
            svc = self._services[idx]

            if compliance_filter:
                tags = svc.get("compliance_tags") or []
                if not all(t in tags for t in compliance_filter):
                    continue
            if regions:
                svc_regions = svc.get("regions") or []
                if not all(r in svc_regions for r in regions):
                    continue

            results.append(
                {
                    "service_id": svc["service_id"],
                    "name": svc["name"],
                    "provider_name": svc.get("provider_name", ""),
                    "compliance_tags": svc.get("compliance_tags") or [],
                    "regions": svc.get("regions") or [],
                    "pricing_elements": svc.get("pricing_elements") or [],
                    "score": float(scores[idx]),
                }
            )
            if len(results) >= limit:
                break

        return results


def get_engine() -> KeywordSearchEngine:
    global _engine
    if _engine is None:
        _engine = KeywordSearchEngine()
    return _engine


async def init_keyword_search(db_session):
    from sqlalchemy import select

    from src.db.models import Provider, Service

    result = await db_session.execute(
        select(
            Service.service_id,
            Service.name,
            Service.keywords,
            Service.compliance_tags,
            Service.regions,
            Service.pricing_elements,
            Provider.name.label("provider_name"),
        ).join(Provider, Provider.provider_id == Service.provider_id)
    )
    rows = result.mappings().all()

    services = [
        {
            "service_id": row["service_id"],
            "name": row["name"],
            "provider_name": row["provider_name"],
            "keywords": row["keywords"] if isinstance(row["keywords"], list) else [],
            "compliance_tags": row["compliance_tags"]
            if isinstance(row["compliance_tags"], list)
            else [],
            "regions": row["regions"] if isinstance(row["regions"], list) else [],
            "pricing_elements": row["pricing_elements"]
            if isinstance(row["pricing_elements"], list)
            else [],
        }
        for row in rows
    ]

    engine = get_engine()
    engine.load(services)
