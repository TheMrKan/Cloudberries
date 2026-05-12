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
    '- regions_filter — обязательные регионы (например ["ru-central1"])\n\n'
    "При использовании search_services ВСЕГДА заполняй оба поля: "
    "keyword_search_query и vector_search_query.\n"
    "keyword_search_query — ключевые слова для точного поиска.\n"
    "vector_search_query — перефразирование запроса пользователя для семантического поиска.\n"
    "Даже если одно из полей кажется необязательным — заполни оба."
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
    "Выбери ровно ТОП-3 наиболее подходящих сервиса и отсортируй от лучшего к худшему.\n"
    "Если сервисов меньше 3 — верни сколько есть.\n\n"
    "ВАЖНО: Используй ТОЛЬКО сервисы из переданного списка. "
    "Поле id в каждом объекте services должно строго соответствовать service_id из результатов поиска. "
    "НЕ выдумывай сервисы и не используй id, которых нет в результатах.\n\n"
    "Для каждого сервиса выбери ТОП-5 наиболее релевантных запросу элементов тарификации "
    "из поля pricing_elements. Если элементов меньше 5 — верни все.\n\n"
    "=== ПРОЦЕСС ОЦЕНКИ ===\n"
    "Для каждого сервиса сначала заполни reasoning для всех трёх критериев, "
    "потом прими решение approved, потом scores, потом rationale.\n"
    "Каждый критерий в reasoning содержит:\n"
    "- наблюдение: что ты видишь в данных и в запросе пользователя\n"
    "- анализ: как данные соотносятся с запросом\n"
    "- оценка: итоговый балл по шкале критерия\n\n"
    "=== ПРОВЕРКА approved ===\n"
    "После заполнения reasoning для всех трёх критериев, но ДО генерации scores, "
    "прими бинарное решение: стоит ли вообще показывать этот сервис пользователю.\n\n"
    "Проверь последовательно:\n"
    "1. Категория сервиса совпадает с запросом? "
    "(compute ≠ storage, СУБД ≠ bare metal, ML ≠ VPS и т.д.)\n"
    "2. Есть ли в описании явные ограничения, противоречащие запросу? "
    "Например: 'только для dev/тестов' при запросе 'production', "
    "'только РФ' при запросе 'Европа', "
    "'холодное хранение' при запросе 'горячий доступ'\n"
    "3. Сервис реально решает задачу, или просто совпал по ключевым словам?\n"
    "4. Если пользователь запросил КОНКРЕТНЫЙ сервис или managed-решение "
    "(управляемая БД, S3, Kubernetes, object storage, managed что-либо) — "
    "голые вычислительные ресурсы (VPS, Compute, виртуальные серверы, облачные серверы) "
    "НЕ должны попадать в выдачу. Это разные категории.\n\n"
    "Решение:\n"
    "- true — сервис стоит показать (все три пункта пройдены)\n"
    "- false — сервис не подходит (хотя бы один пункт не пройден)\n\n"
    "ВАЖНО: approved — это жёсткий фильтр, а не оценка качества. "
    "Если сервис не подходит — отсекай без сожаления.\n\n"
    "Оценивай сервисы строго по трём критериям. Названия критериев фиксированы:\n\n"
    "=== КРИТЕРИЙ 1: Стоимость ===\n"
    "Если пользователь явно указал бюджет/цену — оцени, укладывается ли типовой сценарий "
    "использования сервиса в этот бюджет на основе pricing_elements.\n"
    "Если бюджет не указан — сравни стоимость сервисов внутри топ-3.\n"
    "Шкала:\n"
    "10/10 — явно входит в бюджет (или самый дешёвый среди топ-3, если бюджет не указан)\n"
    "9/10 — примерно в бюджет, возможны небольшие превышения (или до +50% к самому дешёвому)\n"
    "7-8/10 — превышает бюджет на 10-50% (или дороже самого дешёвого на +50-100%)\n"
    "5-6/10 — превышает бюджет на 50-100% (или дороже на +100-200%)\n"
    "1-4/10 — значительно дороже бюджета (>100%) (или дороже на >200%)\n\n"
    "=== КРИТЕРИЙ 2: Соответствие задаче ===\n"
    "Оцени насколько сервис решает именно ту задачу, которую описал пользователь.\n"
    "Учитывай: name, description, matched_keywords, категорию сервиса.\n"
    "Шкала:\n"
    "10/10 — узкоспециализированный сервис ровно под запрос пользователя. Идеальное попадание.\n"
    "9/10 — узкоспециализированный, но не хватает одной незначительной детали "
    "(или покрывает задачу чуть шире, чем нужно).\n"
    "7-8/10 — сервис подходит, но решает широкий спектр задач, а не заточен конкретно под этот "
    "сценарий. Можно использовать без серьёзных доработок.\n"
    "5-6/10 — сервис можно приспособить под задачу, но потребуются доработки или есть более "
    "прямой путь.\n"
    "1-4/10 — косвенно связан с задачей, только как часть решения.\n"
    "0/10 — категория сервиса не совпадает с запросом.\n\n"
    "Чтобы поставить разным сервисам РАЗНЫЕ баллы по этому критерию — "
    "обязательно обоснуй различие в rationale. "
    "Если сервисы одной категории и нет явных отличий в описании — "
    "баллы должны быть одинаковыми.\n\n"
    "=== КРИТЕРИЙ 3: Дополнительные пожелания ===\n"
    "Оцени всё, что не попало в жёсткие фильтры поиска, но упоминалось пользователем: "
    "технологии (SSD, GPU, NVLink), характеристики (быстрый, отказоустойчивый, холодное хранение), "
    "soft requirements.\n"
    "Проверь наличие этих характеристик в name, description и keywords сервиса.\n"
    "ВАЖНО: НЕ выдумывай критерии, которых нет в запросе. "
    "Если пользователь не упоминал дополнительных требований — ставь 10/10 всем сервисам.\n"
    "Шкала:\n"
    "10/10 — пользователь не высказывал доп. пожеланий (автомат) "
    "ИЛИ все упомянутые пожелания явно присутствуют\n"
    "7-9/10 — большинство упомянутых пожеланий покрыто\n"
    "5-6/10 — пожелания частично покрыты\n"
    "1-4/10 — почти ничего не совпало\n\n"
    "Верни JSON строго в следующем формате (порядок полей важен):\n"
    '{"answer": "короткая фраза как я понял запрос", '
    '"services": [{"id": 1, '
    '"reasoning": {"Стоимость": {"наблюдение": "...", "анализ": "...", "оценка": "9/10"}, '
    '"Соответствие задаче": {"наблюдение": "...", "анализ": "...", "оценка": "10/10"}, '
    '"Дополнительные пожелания": {"наблюдение": "...", "анализ": "...", "оценка": "10/10"}}, '
    '"approved": true, '
    '"scores": {"Стоимость": "9/10", "Соответствие задаче": "10/10", '
    '"Дополнительные пожелания": "10/10"}, '
    '"rationale": "текст с обоснованием", '
    '"pricing": [{"description": "...", "uom": "...", "price": 123.45}]}]}\n\n'
    "Пояснения полей:\n"
    "answer — короткая фраза (1 предложение) о том, как понят запрос пользователя, "
    "например: 'Ищу серверы с GPU, отфильтровано по ФЗ-152'.\n"
    "reasoning — dict с тремя ключами (названия критериев). Каждое значение — dict "
    "с полями наблюдение (что в данных), анализ (сопоставление с запросом), оценка (N/10).\n"
    "approved — bool: true если сервис подходит и стоит показать, false если нет. "
    "Если approved == false, сервис не включается в итоговый ответ.\n"
    "scores — dict РОВНО с тремя ключами: Стоимость, Соответствие задаче, Дополнительные пожелания. "
    "Значения — строки в формате 'N/10'. Должны совпадать с оценками в reasoning.\n"
    "rationale — подробное обоснование в формате: "
    "'N место. Стоимость N/10 — почему. Соответствие задаче N/10 — почему. "
    "Дополнительные пожелания N/10 — почему. Итог.' "
    "Обязательно объяснить, почему именно такие баллы и почему сервис на этом месте.\n"
    "pricing — массив из топ-5 элементов pricing_elements, наиболее релевантных запросу. "
    'Каждый элемент: {"description": "...", "uom": "...", "price": число}.\n'
    "services — массив ровно из 3 объектов (или меньше, если нет). "
    "Первый в массиве = лучший, последний = худший."
)


def _to_openai(messages: list[dict]) -> list[dict]:
    return [{"role": m["role"], "content": m["text"]} for m in messages]


async def llm_complete(messages: list[dict]) -> dict:
    openai_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_to_openai(messages),
    ]

    print(f"[LLM] call model={settings.llm_model} messages={len(openai_messages)}")
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        project=settings.llm_project_id,
    )
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

    available_ids = {r.get("service_id") for r in tool_results}
    available_descr = (
        "Доступные service_id для выбора: "
        + ", ".join(sorted(str(i) for i in available_ids))
        + "."
    )

    openai_messages = [
        {"role": "system", "content": ANNOTATION_PROMPT},
        *_to_openai(history),
        raw_dict,
        {
            "role": "tool",
            "tool_call_id": raw_message.tool_calls[0].id,
            "content": available_descr
            + "\n\n"
            + json.dumps(tool_results, ensure_ascii=False, default=str),
        },
    ]

    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        project=settings.llm_project_id,
    )
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=openai_messages,
        response_format={"type": "json_object"},
        temperature=0,
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
