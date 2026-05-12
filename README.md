# Cloudberries

Маркетплейс облачных находок — AI-ассистент для подбора облачных сервисов среди российских провайдеров.

## Архитектура

```
┌──────────┐     ┌──────────┐     ┌───────────┐
│  Browser │────▶│  Nginx   │────▶│  FastAPI  │
│ (React)  │     │ (прокси) │     │ (8000)    │
└──────────┘     └──────────┘     └─────┬─────┘
                                        │
                          ┌─────────────┼─────────────┐
                          │             │             │
                    ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼──────────┐
                    │ PostgreSQL│ │   Qdrant  │ │  LLM API       │
                    │ (5432)    │ │ (6333)    │ │ (Yandex GPT)   │
                    └───────────┘ └───────────┘ └────────────────┘

┌─────────────────────────────────────────────┐
│          Celery Worker (scraper_service)     │
│          Redis broker                        │
└─────────────────────────────────────────────┘
```

### Data Flow (поиск сервисов)

1. Пользователь вводит запрос → POST `/api/chat`
2. **LLM (stage 1)** решает: вызвать `search_services` tool или задать уточняющий вопрос
3. Если tool вызван: параллельный поиск по **BM25** (ключевые слова) и **Qdrant** (семантический вектор)
4. Результаты склеиваются (дедупликация по `service_id`), тоp-10
5. **LLM (stage 2)** получает результаты, скорит по трём критериям, отсеивает неподходящие (`approved`)
6. SSE-поток клиенту: `search_result` → `token` → `done`

## Tech Stack

### Бэкенд (`core_service/`)
- **Python 3.12** + **FastAPI** + **SQLAlchemy 2.0** (async)
- **PostgreSQL 16** — основная БД (провайдеры, сервисы, сессии чата)
- **Qdrant** — векторное хранилище (embeddings 256d, COSINE distance)
- **OpenAI SDK** — совместим с Yandex GPT API
- **rank-bm25** — keyword search
- **SQLAdmin** — админ-панель

### Фронтенд (`front_service/`)
- **React 19** + **TypeScript** + **Vite 6**
- **TailwindCSS 3.4** + shadcn/ui-like компоненты
- **SSE** — Server-Sent Events для стриминга ответа LLM

### Парсер (`scraper_service/`)
- **Celery** + **Redis** — распределённые задачи
- **Playwright** / **pdfplumber** — сбор данных с сайтов провайдеров

## Структура проекта

```
.
├── .env                          # Переменные окружения
├── docker-compose.yml            # PostgreSQL + Qdrant + app + frontend
├── nginx.conf                    # Reverse proxy для фронта
│
├── core_service/                 # ★ Бэкенд
│   ├── src/
│   │   ├── main.py               # FastAPI app, lifespan, CORS, admin
│   │   ├── config.py             # Pydantic Settings
│   │   ├── admin.py              # SQLAdmin (ProviderAdmin, ServiceAdmin)
│   │   ├── chat_engine.py        # ★ Пайплайн чата (decision → search → annotate)
│   │   ├── chat/
│   │   │   ├── router.py         # 4 эндпоинта API
│   │   │   ├── schemas.py        # Pydantic модели (StructuredSearch, ServiceResult, etc.)
│   │   │   ├── service.py        # ChatService CRUD
│   │   │   └── llm.py            # ★ LLM вызовы + промпты (SYSTEM_PROMPT, ANNOTATION_PROMPT)
│   │   ├── db/
│   │   │   ├── engine.py         # Async engine + session factory
│   │   │   └── models.py         # ORM: Provider, Service, ChatSession
│   │   └── search/
│   │       ├── embeddings.py     # HTTP-вызовы к API эмбеддингов (через httpx)
│   │       ├── keyword_search.py # BM25 + compliance/region фильтры
│   │       ├── qdrant_client.py  # Qdrant client (upsert, search, ensure_collection)
│   │       └── hybrid.py         # Нормализация + weighted rerank (не используется в пайплайне)
│   ├── seed_all.py               # Загрузка всех JSON + эмбеддинги в Qdrant
│   ├── Dockerfile
│   └── pyproject.toml
│
├── front_service/                # ★ Фронтенд
│   ├── src/
│   │   ├── App.tsx               # Основной компонент (3 фазы: catalog/chat/results)
│   │   ├── api.ts                # API-клиент + SSE парсер
│   │   └── components/ui/        # shadcn-like компоненты
│   ├── package.json
│   └── Dockerfile
│
├── scraper_service/              # Парсер цен (Celery)
│   └── src/scraper_service/
│       ├── tasks/pipeline.py     # Оркестрация: crawl → MD → JSON → DB
│       ├── tasks/pdf_to_md.py    # PDF → Markdown
│       ├── tasks/md_to_json.py   # Markdown → JSON через LLM
│       └── tasks/json_to_db.py   # JSON → PostgreSQL
│
│
├── alembic/                      # Миграции БД
└── qdrant_data/                  # Данные Qdrant (persistent volume)
```

**Всего сервисов:** 67 (6 провайдеров: Yandex Cloud, Cloud.ru, Selectel, VK Cloud, T1 Cloud, Cloud Provider)

## База данных

### Provider

| Поле | Тип | Описание |
|------|-----|----------|
| `provider_id` | String(32) PK | Идентификатор провайдера |
| `name` | String(128) | Название |

### Service

| Поле | Тип | Описание |
|------|-----|----------|
| `service_id` | Integer PK, auto | ID сервиса |
| `provider_id` | FK → Provider | Провайдер |
| `name` | String(256) | Название сервиса |
| `description` | String(2048) | Описание |
| `compliance_tags` | JSON[String] | Теги соответствия (ФЗ-152 и т.д.) |
| `keywords` | JSON[String] | Ключевые слова для BM25 |
| `regions` | JSON[String] | Регионы доступности |
| `pricing_elements` | JSON[{description, uom, price}] | Элементы тарификации |
| `extra_data` | JSON | Дополнительные данные |

### ChatSession

| Поле | Тип | Описание |
|------|-----|----------|
| `session_id` | String(36) PK | UUID сессии |
| `context` | JSON | Контекст (зарезервировано) |
| `messages` | JSON[{role, text, ...}] | История сообщений |
| `results` | JSON | Результаты поиска (кэш) |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

## API

Базовый URL: `http://localhost:8000/api` (через nginx: `http://localhost/api`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/services` | Список всех сервисов |
| POST | `/api/chat` | Отправить сообщение (SSE) |
| GET | `/api/session?session_id=...` | Получить сессию чата |
| DELETE | `/api/chat/{session_id}` | Удалить сессию |
| GET | `/health` | Health check |
| GET | `/admin` | SQLAdmin панель (admin:admin) |

### POST `/api/chat` — SSE события

```typescript
// Запрос
{ "session_id": "uuid", "message": "VPS под 152-ФЗ до 3000 ₽" }

// Ответ — поток SSE событий:
event: search_result
data: { "id": 1, "name": "...", "provider": "...", "description": "...",
        "compliance_tags": [...], "regions": [...], "pricing_elements": [...],
        "rationale": "...", "scores": {"Стоимость": "8/10", ...}, "matched_keywords": [...] }

event: token
data: { "text": "Подобрал несколько вариантов..." }

event: done
data: null
```

## LLM Интеграция

### Двухстадийный подход

**Stage 1 — `llm_complete()`** (`llm.py:177`):
- Системный промпт: правила когда вызывать `search_services` vs задавать уточняющие вопросы
- `tool_choice="auto"` — LLM решает, вызывать ли tool
- Если вызвал → возвращает `StructuredSearch` с полями `keyword_search_query`, `vector_search_query`, `compliance_filter`, `regions_filter`
- Если не вызвал → возвращает текст (приветствие, уточнение)

**Stage 2 — `llm_with_results()`** (`llm.py:215`):
- Получает результаты поиска (топ-10)
- Промпт `ANNOTATION_PROMPT` с schema-guided reasoning
- Для каждого сервиса заполняет `reasoning` (наблюдение → анализ → оценка), затем `approved`, `scores`, `rationale`
- Возвращает JSON с `answer` + топ-3 сервиса

### Системный промпт (`SYSTEM_PROMPT`)

- Конкретные запросы (категория + хотя бы одно требование) → сразу `search_services`
- Расплывчатые запросы → 1-2 уточняющих вопроса, НЕ вызывать tool
- Всегда заполнять оба поля: `keyword_search_query` и `vector_search_query`

### Промпт аннотации (`ANNOTATION_PROMPT`)

Три фиксированных критерия скоринга:

| Критерий | Вес | Описание |
|----------|-----|----------|
| **Стоимость** | N/10 | Бюджет пользователя / сравнение внутри топ-3 |
| **Соответствие задаче** | N/10 | Насколько сервис решает именно задачу пользователя |
| **Дополнительные пожелания** | N/10 | Технологии, характеристики, soft requirements |

Перед скорингом — `approved` (бинарный фильтр: категория, ограничения, реальная релевантность).

## Поиск

### BM25 (keyword search)

- Индекс строится из `keywords` сервисов при старте (`init_keyword_search`)
- Токенизация: `re.findall(r"\w+", text.lower())`
- Фильтрация по `compliance_tags` и `regions` — применяется после BM25 скоров
- Автоподстановка синонимов: `"152-ФЗ"` ↔ `"ФЗ-152"` при фильтрации

### Векторный (Qdrant)

- Размерность эмбеддингов: **256**
- Метрика: **COSINE**
- Текст для эмбеддинга: `name + " " + description + " " + " ".join(keywords)`
- API эмбеддингов: httpx напрямую (OpenAI SDK несовместим с Yandex Cloud API)
- Rate limit: `asyncio.sleep(0.3)` между вызовами

**Важно:** Поле в Qdrant называется `"compliance"` (не `"compliance_tags"`). Переименование происходит при загрузке (`seed_all.py`). При вычитке `chat_engine.py:76` переименовывает обратно.

## Фронтенд

### Компоненты (`App.tsx`)

Три фазы:
1. **Catalog** — сетка из 9 случайных сервисов, поисковая строка внизу
2. **Chat** — полноэкранный чат с LLM, стриминг ответа, кнопки-подсказки
3. **Results** — результаты поиска (для регионализации — история слева, результаты + чат справа)

Ключевые компоненты:
- `CatalogCard` — карточка сервиса с логотипом, тегами 152-ФЗ, регионами
- `ResultCardFull` — карточка результата с местом (#1-3), скорами, тарификацией, rationale
- `ScoreBar` — визуальная шкала 0-10
- `HistoryOverlay` — всплывающая история чата
- `ProviderIcon` — favicon провайдера

### SSE парсер (`api.ts`)

- Чтение `ReadableStream`, построчный разбор `event:` / `data:`
- Маппинг бэкендовых типов → фронтендовые (с нормализацией scores)

## Установка и запуск

### Локальная разработка

```bash
# 1. Запустить инфраструктуру
docker compose up postgres qdrant -d

# 2. Бэкенд
cd core_service
python -m pip install -e .
python init_db.py          # создать таблицы
python seed_all.py         # загрузить данные + эмбеддинги
uvicorn src.main:app --reload --port 8000

# 3. Фронтенд (отдельный терминал)
cd front_service
npm install
npm run dev                # Vite dev server → localhost:5173
```

### Docker Compose (полный стек)

```bash
docker compose up --build
# → Frontend: http://localhost
# → API:      http://localhost:8000
# → Admin:    http://localhost:8000/admin (admin:admin)
```

### Vite dev server + бэкенд

При `npm run dev` Vite настроен на прокси к `http://localhost:8000`.

## Переменные окружения (`.env`)

```env
DB_URL=postgresql+asyncpg://cloudberries:cloudberries@localhost:5432/cloudberries
LLM_API_KEY=...                          # Ключ Yandex GPT
LLM_BASE_URL=...
LLM_MODEL=...
LLM_PROJECT_ID=...
EMBEDDING_MODEL=...
```

Настройки по умолчанию: `core_service/src/config.py`. Переопределяются через `.env` или переменные окружения.


## Парсер (`scraper_service`)

Celery-воркер для автоматического сбора данных о ценах:

- **Расписание:** полный пайплайн каждый день в 3:00, пакетный сбор каждые 15 минут
- **Пайплайн:** crawl PDF → извлечение таблиц → LLM-конвертация в JSON → сохранение в БД

## Известные особенности

- **Yandex Cloud embedding API** несовместим с OpenAI SDK (ошибка "Base64 encoding format is not supported"). Эмбеддинги вызываются через httpx напрямую (`embeddings.py`)
- **Qdrant поле `compliance`**: при загрузке `compliance_tags` переименовывается в `compliance`. При вычитке — обратно. Фильтрация идёт по `key="compliance"`
- **tool_choice="auto"**: LLM может не вызвать tool даже для конкретного запроса. Если это происходит, ответ LLM отдаётся как текст без поиска
- **Синонимы 152-ФЗ/ФЗ-152**: в BM25 автоподстановка при фильтрации. В Qdrant зависит от того, что передал LLM

## Лицензия

MIT
