"""Stub LLM — имитирует ReAct: либо отвечает текстом, либо вызывает tool."""

from src.chat.schemas import StructuredSearch

SEARCH_KEYWORDS = [
    "найди",
    "подбери",
    "ищи",
    "сервис",
    "провайдер",
    "облако",
    "нужен",
    "хочу",
    "посоветуй",
]


def llm_complete(
    messages: list[dict],
) -> dict:
    """
    Заглушка LLM с tool calling.
    Возвращает {"role": "assistant", "content": str} | {"role": "assistant", "tool_call": StructuredSearch}.
    """
    last = messages[-1]["text"] if messages else ""

    if any(kw in last.lower() for kw in SEARCH_KEYWORDS):
        structured = StructuredSearch(
            fz_filter="152-фз" in last.lower() or "152фз" in last.lower(),
            regions_filter=None,
            search_queries=[last],
        )
        return {"role": "assistant", "tool_call": structured}

    return {"role": "assistant", "content": "Чем ещё могу помочь?"}


def llm_with_results(
    history: list[dict],
    tool_results: list[dict],
) -> str:
    if not tool_results:
        return "Ничего не нашлось. Попробуй изменить запрос."

    top = tool_results[:3]
    lines = []
    for t in top:
        name = t.get("name", "Сервис")
        provider = t.get("provider_name", "")
        elems = t.get("pricing_elements", [])
        prices = ", ".join(
            f"{e.get('price', '')} {e.get('uom', '')}" for e in elems[:2]
        )
        lines.append(f"**{provider} — {name}**: {prices}")

    return "Вот что удалось найти:\n\n" + "\n".join(lines)
