from src.config import Settings
from qdrant_client import QdrantClient, models

settings = Settings()


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
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
    print(f"[QDRANT] search limit={limit} filters={filters}")
    must = []
    if filters:
        if filters.get("compliance"):
            for tag in filters["compliance"]:
                must.append(
                    models.FieldCondition(
                        key="compliance",
                        match=models.MatchValue(value=tag),
                    )
                )
        if filters.get("regions"):
            for region in filters["regions"]:
                must.append(
                    models.FieldCondition(
                        key="regions",
                        match=models.MatchValue(value=region),
                    )
                )

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=models.Filter(must=must) if must else None,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    count = len(response.points)
    print(f"[QDRANT] returned {count} results")
    return [
        {
            "service_id": r.id,
            "score": r.score,
            **r.payload,
        }
        for r in response.points
    ]
