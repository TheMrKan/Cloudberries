from src.config import Settings
from qdrant_client import QdrantClient, models

settings = Settings()


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url="http://localhost:6333",
        api_key="cloudberries-secret-key",
        timeout=30,
    )


COLLECTION_NAME = "services"


def ensure_collection(client: QdrantClient) -> None:
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE,
        ),
    )


def upsert_service(
    client: QdrantClient,
    service_id: int,
    vector: list[float],
    payload: dict,
) -> None:
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=service_id,
                vector=vector,
                payload=payload,
            )
        ],
    )


def search_vector(
    client: QdrantClient,
    query_vector: list[float],
    limit: int = 20,
    filters: dict | None = None,
) -> list[dict]:
    must = []
    if filters:
        conditions = []
        if filters.get("fz_filter"):
            conditions.append(
                models.FieldCondition(
                    key="compliance_152fz",
                    match=models.MatchValue(value=True),
                )
            )
        if filters.get("regions"):
            conditions.append(
                models.FieldCondition(
                    key="regions",
                    match=models.MatchAny(any=filters["regions"]),
                )
            )
        if conditions:
            must.append(models.Filter(must=conditions))

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=models.Filter(must=must) if must else None,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    return [
        {
            "service_id": r.id,
            "score": r.score,
            **r.payload,
        }
        for r in results
    ]
