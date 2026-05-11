import math
from typing import Any


def hybrid_rerank(
    vector_results: list[dict],
    bm25_results: list[dict],
    w_vector: float = 0.5,
    w_bm25: float = 0.5,
) -> list[dict]:
    """
    Сливает результаты vector search и bm25, нормализует скоры,
    возвращает единый ранжированный список.
    """
    scores_map: dict[int, dict[str, Any]] = {}

    max_vec = max((r["score"] for r in vector_results), default=0) or 1
    max_bm25 = max((r["score"] for r in bm25_results), default=0) or 1

    for r in vector_results:
        sid = r["service_id"]
        scores_map[sid] = {
            **{k: v for k, v in r.items() if k != "score"},
            "_vec_score": r["score"] / max_vec,
            "_bm25_score": 0.0,
        }

    for r in bm25_results:
        sid = r["service_id"]
        if sid in scores_map:
            scores_map[sid]["_bm25_score"] = r["score"] / max_bm25
        else:
            scores_map[sid] = {
                **{k: v for k, v in r.items() if k != "score"},
                "_vec_score": 0.0,
                "_bm25_score": r["score"] / max_bm25,
            }

    ranked = []
    for sid, data in scores_map.items():
        final = w_vector * data["_vec_score"] + w_bm25 * data["_bm25_score"]
        ranked.append({**data, "relevance_score": final})

    ranked.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Убираем служебные поля
    for item in ranked:
        item.pop("_vec_score", None)
        item.pop("_bm25_score", None)

    return ranked
