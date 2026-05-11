import json

from openai import AsyncOpenAI

from src.chat.schemas import StructuredSearch
from src.config import Settings

settings = Settings()

SYSTEM_PROMPT = (
    "Ты — помощник по подбору облачных сервисов среди российских провайдеров. "
    "Твоя задача — помочь пользователю найти подходящие сервисы.\n\n"
    "Если пользователь просит найти, подобрать или сравнить сервисы — "
    "используй функцию search_services для поиска по каталогу.\n"
    "Если пользователь просто здоровается или задаёт общий вопрос — ответь текстом.\n\n"
    "Поля search_services:\n"
    "- keyword_search_query — ключевые слова для поиска по тегам сервиса\n"
    "- vector_search_query — описание для семантического поиска\n"
    '- compliance_filter — обязательные compliance-теги (например ["ФЗ-152"])\n'
    '- regions_filter — обязательные регионы (например ["ru-central1"])'
)

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "search_services",
        "description": "Поиск облачных сервисов в каталоге",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword_search_query": {
                    "type": "string",
                    "description": "Ключевые слова для поиска по тегам сервиса",
                },
                "vector_search_query": {
                    "type": "string",
                    "description": "Запрос для семантического поиска по описанию",
                },
                "compliance_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Фильтр по compliance (ФЗ-152 и т.д.)",
                },
                "regions_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Фильтр по регионам",
                },
            },
        },
    },
}

ANNOTATION_PROMPT = (
    "На основе результатов поиска составь ответ пользователю.\n\n"
    "Верни JSON строго в формате:\n"
    '{"answer": "текст ответа", "services": [{"id": 1, "rationale": "почему подходит", "scores": {"Стоимость": "7/10", "Соответствие задаче": "8/10"}}]}\n\n'
    "scores — dict с произвольными названиями критериев и оценками в формате 'N/10'.\n"
    "rationale — короткое обоснование (1-2 предложения) на русском.\n"
    "answer — ответ пользователю с перечислением подходящих сервисов."
)


def _to_openai(messages: list[dict]) -> list[dict]:
    return [{"role": m["role"], "content": m["text"]} for m in messages]


async def llm_complete(messages: list[dict]) -> dict:
    openai_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_to_openai(messages),
    ]

    print(f"[LLM] call model={settings.llm_model} messages={len(openai_messages)}")
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=openai_messages,
        tools=[TOOL_DEF],
        tool_choice="auto",
    )

    msg = response.choices[0].message
    print(
        f"[LLM] response role={msg.role} has_tool_calls={bool(msg.tool_calls)} has_content={bool(msg.content)}"
    )

    if msg.tool_calls:
        tc = msg.tool_calls[0]
        args = json.loads(tc.function.arguments)
        print(f"[LLM] tool_call name={tc.function.name} args={args}")
        return {
            "role": "assistant",
            "tool_call": StructuredSearch(**args),
            "raw_message": msg,
        }

    print(f"[LLM] text response={msg.content[:200]}")
    return {"role": "assistant", "content": msg.content or ""}


async def llm_with_results(
    history: list[dict],
    raw_message,
    tool_results: list[dict],
) -> tuple[str, list[dict]]:
    """Returns (answer_text, annotations) where annotations = [{id, rationale, scores}]."""
    raw_dict = {
        "role": "assistant",
        "content": raw_message.content,
        "tool_calls": [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in raw_message.tool_calls
        ],
    }
    print(f"[LLM] llm_with_results tool_results={len(tool_results)}")

    openai_messages = [
        {"role": "system", "content": ANNOTATION_PROMPT},
        *_to_openai(history),
        raw_dict,
        {
            "role": "tool",
            "tool_call_id": raw_message.tool_calls[0].id,
            "content": json.dumps(tool_results, ensure_ascii=False, default=str),
        },
    ]

    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=openai_messages,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    print(f"[LLM] llm_with_results raw={raw[:300]}")

    try:
        data = json.loads(raw)
        answer = data.get("answer", "Ничего не нашлось.")
        annotations = data.get("services", [])
    except json.JSONDecodeError:
        answer = raw
        annotations = []

    return answer, annotations
