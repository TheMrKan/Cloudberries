import asyncio

import httpx

from src.config import Settings

settings = Settings()

EMBEDDING_DIMENSION = 256


async def _call(t: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.llm_base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": t,
                "dimensions": EMBEDDING_DIMENSION,
            },
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    results = []
    for t in texts:
        results.append(await _call(t))
        await asyncio.sleep(0.3)
    return results


async def get_embedding(text: str) -> list[float]:
    return await _call(text)
