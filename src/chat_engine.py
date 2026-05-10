import json
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.llm import llm_complete, llm_with_results
from src.chat.service import ChatService
from src.search.keyword_search import get_engine as get_keyword_engine
from src.search.qdrant_client import get_qdrant_client, search_vector


def _make_embedding(text: str) -> list[float]:
    return [0.0] * 384


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
        vec = _make_embedding(structured.vector_search_query)
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

        seen = {r["service_id"] for r in all_results}
        for r in vec_results:
            if r["service_id"] not in seen:
                all_results.append(r)
                seen.add(r["service_id"])

    return all_results[:10]


async def chat_pipeline(
    db: AsyncSession,
    session_id: str,
    text: str,
) -> AsyncGenerator[str, None]:
    session = await ChatService.get_session(db, session_id)
    if not session:
        yield json.dumps({"event": "error", "data": {"text": "Session not found"}})
        return

    history = session.messages

    print(f"[ENGINE] history_len={len(history)} text={text}")

    # Шаг 1: LLM решает — ответить или вызвать tool
    print("[ENGINE] step1: calling llm_complete...")
    decision = await llm_complete([*history, {"role": "user", "text": text}])
    print(f"[ENGINE] step1: decision keys={list(decision.keys())}")

    if "tool_call" in decision:
        # Шаг 2: шлём событие о вызове тула
        structured = decision["tool_call"]
        structured_dump = structured.model_dump(exclude_none=True)
        print(f"[ENGINE] step2: tool_call args={structured_dump}")
        yield json.dumps(
            {
                "event": "tool_call",
                "data": {
                    "tool": "search_services",
                    "arguments": structured_dump,
                },
            }
        )

        # Шаг 3: выполняем поиск
        print("[ENGINE] step3: running search...")
        results = await _run_search_tool(structured)
        print(f"[ENGINE] step3: results count={len(results)}")

        yield json.dumps({"event": "services", "data": results})

        # Шаг 4: LLM формирует ответ на основе результатов
        print("[ENGINE] step4: calling llm_with_results...")
        answer = await llm_with_results(
            [*history, {"role": "user", "text": text}],
            decision["raw_message"],
            results,
        )
        print(f"[ENGINE] step4: answer={answer[:200]}")

    else:
        answer = decision.get("content", "")
        print(f"[ENGINE] else: text answer={answer[:200]}")

    yield json.dumps({"event": "message", "data": {"text": answer}})

    await ChatService.append_message(db, session_id, "assistant", answer)

    yield json.dumps({"event": "done", "data": None})
