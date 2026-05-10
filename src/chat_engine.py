import json
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.llm import llm_complete, llm_with_results
from src.chat.service import ChatService
from src.search.bm25 import bm25_search
from src.search.qdrant_client import get_qdrant_client, search_vector
from src.search.hybrid import hybrid_rerank


def _make_embedding(text: str) -> list[float]:
    return [0.0] * 384


async def _run_search_tool(db: AsyncSession, structured) -> list[dict]:
    """Выполняет поисковый пайплайн — это и есть tool."""
    bm25_results = await bm25_search(
        db,
        keywords=structured.search_queries,
        compliance_filter=structured.compliance_filter,
        regions=structured.regions_filter,
    )

    qdrant = get_qdrant_client()
    vec = _make_embedding(" ".join(structured.search_queries))
    qdrant_filters = {}
    if structured.compliance_filter:
        qdrant_filters["compliance"] = structured.compliance_filter
    if structured.regions_filter:
        qdrant_filters["regions"] = structured.regions_filter

    vector_results = search_vector(
        qdrant,
        query_vector=vec,
        limit=20,
        filters=qdrant_filters,
    )

    ranked = hybrid_rerank(vector_results, bm25_results)
    return ranked[:10]


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

    # Шаг 1: LLM решает — ответить или вызвать tool
    decision = llm_complete([*history, {"role": "user", "text": text}])

    if "tool_call" in decision:
        # Шаг 2: шлём событие о вызове тула
        structured = decision["tool_call"]
        yield json.dumps(
            {
                "event": "tool_call",
                "data": {
                    "tool": "search_services",
                    "arguments": structured.model_dump(exclude_none=True),
                },
            }
        )

        # Шаг 3: выполняем поиск
        results = await _run_search_tool(db, structured)

        yield json.dumps({"event": "services", "data": results})

        # Шаг 4: LLM формирует ответ на основе результатов
        answer = llm_with_results([*history, {"role": "user", "text": text}], results)

    else:
        answer = decision.get("content", "")

    yield json.dumps({"event": "message", "data": {"text": answer}})

    await ChatService.append_message(db, session_id, "assistant", answer)

    yield json.dumps({"event": "done", "data": None})
