import json
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.llm import llm_complete, llm_with_results
from src.chat.service import ChatService
from src.search.embeddings import get_embedding
from src.search.keyword_search import get_engine as get_keyword_engine
from src.search.qdrant_client import get_qdrant_client, search_vector


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _sse(event: str, data):
    return (
        f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
    )


def _to_service_result(svc: dict, annotations: list[dict]) -> dict:
    ann = {}
    for a in annotations:
        if a.get("id") == svc["service_id"]:
            ann = a
            break
    return {
        "id": svc["service_id"],
        "name": svc["name"],
        "provider": svc.get("provider_name", ""),
        "description": svc.get("description"),
        "compliance_tags": svc.get("compliance_tags", []) or svc.get("compliance", []),
        "regions": svc.get("regions", []),
        "pricing_elements": svc.get("pricing_elements", []),
        "rationale": ann.get("rationale", ""),
        "scores": ann.get("scores", {}),
        "matched_keywords": svc.get("matched_keywords", []),
    }


async def _run_search_tool(structured) -> list[dict]:
    print(
        f"[SEARCH] keyword_query={structured.keyword_search_query} vector_query={structured.vector_search_query} compliance={structured.compliance_filter} regions={structured.regions_filter}"
    )
    all_results = []

    if structured.keyword_search_query:
        kw_results = get_keyword_engine().search(
            query=structured.keyword_search_query,
            compliance_filter=structured.compliance_filter,
            regions=structured.regions_filter,
        )
        print(f"[SEARCH] bm25 results={len(kw_results)}")
        all_results.extend(kw_results)

    if structured.vector_search_query:
        qdrant = get_qdrant_client()
        vec = await get_embedding(structured.vector_search_query)
        qdrant_filters = {}
        if structured.compliance_filter:
            qdrant_filters["compliance"] = structured.compliance_filter
        if structured.regions_filter:
            qdrant_filters["regions"] = structured.regions_filter

        vec_results = search_vector(
            qdrant,
            query_vector=vec,
            limit=20,
            filters=qdrant_filters,
        )

        for r in vec_results:
            r["compliance_tags"] = r.pop("compliance", r.get("compliance_tags", []))

        seen = {r["service_id"] for r in all_results}
        for r in vec_results:
            if r["service_id"] not in seen:
                r["_source"] = "vector"
                all_results.append(r)
                seen.add(r["service_id"])
            else:
                existing = next(
                    x for x in all_results if x["service_id"] == r["service_id"]
                )
                existing["_source"] = "keyword+vector"
    else:
        for r in all_results:
            r["_source"] = "keyword"

    if structured.keyword_search_query:
        for r in all_results:
            print(
                f"[SEARCH] {r['name']} source={r.get('_source', '?')} score={r.get('score')}"
            )
        query_tokens = _tokenize(structured.keyword_search_query)
        for r in all_results:
            matched = []
            for kw in r.get("keywords") or []:
                kw_lower = kw.lower()
                if any(t in kw_lower for t in query_tokens):
                    matched.append(kw)
            r["matched_keywords"] = sorted(matched)
    else:
        for r in all_results:
            r["matched_keywords"] = []

    return all_results[:10]


async def chat_pipeline(
    db: AsyncSession,
    session_id: str,
    text: str,
) -> AsyncGenerator[str, None]:
    session = await ChatService.get_session(db, session_id)
    if not session:
        yield _sse("error", {"text": "Session not found"})
        return

    history = session.messages

    print(f"[ENGINE] history_len={len(history)} text={text}")

    print("[ENGINE] step1: calling llm_complete...")
    decision = await llm_complete([*history, {"role": "user", "text": text}])
    print(f"[ENGINE] step1: decision keys={list(decision.keys())}")

    final_results = []

    if "tool_call" in decision:
        structured = decision["tool_call"]
        structured_dump = structured.model_dump(exclude_none=True)
        print(f"[ENGINE] tool_call args={structured_dump}")

        print("[ENGINE] running search...")
        results = await _run_search_tool(structured)
        print(f"[ENGINE] search results count={len(results)}")

        print("[ENGINE] calling llm_with_results...")
        answer, annotations = await llm_with_results(
            [*history, {"role": "user", "text": text}],
            decision["raw_message"],
            results,
        )
        print(f"[ENGINE] answer={answer[:200]}")
        print(f"[ENGINE] annotations={annotations}")

        svc_by_id = {s["service_id"]: s for s in results}
        for ann in annotations:
            svc = svc_by_id.get(ann.get("id"))
            if svc is None:
                print(
                    f"[ENGINE] WARNING: annotation id={ann.get('id')} not found in results"
                )
                continue
            result_item = _to_service_result(svc, annotations)
            yield _sse("search_result", result_item)
            final_results.append(result_item)

    else:
        answer = decision.get("content", "")
        print(f"[ENGINE] text answer={answer[:200]}")

    yield _sse("token", answer)

    await ChatService.append_message(db, session_id, "assistant", answer)
    if final_results:
        session.results = final_results
        await db.commit()

    yield _sse("done", None)
