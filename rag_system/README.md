# RAG-KMS — локальная система управления знаниями
## Офлайн-поиск по техническому архиву | Русский + English

> 🇬🇧 English version: [README_eng.md](README_eng.md)

Локальная система поиска и генерации ответов (RAG) по архиву научно-технических
документов. Работает в защищённом контуре: индексация и эмбеддинги выполняются
полностью офлайн, а в качестве LLM можно использовать как локальную Ollama, так и
облачные API (по желанию).

Тематический профиль базы знаний — нефтегазовая инженерия и геологическое
захоронение CO₂, но система не привязана к предметной области.

---

## Возможности

- **Мультиформатная индексация** — PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT
  (список форматов — `config.SUPPORTED_EXTENSIONS`).
- **Семантический поиск** по смыслу (а не по совпадению слов) на двух языках —
  русском и английском — через модель `intfloat/multilingual-e5-large`.
- **Кросс-языковой поиск** — один и тот же вопрос на RU и EN даёт совпадающий
  набор источников: перекос `e5` в сторону языка запроса компенсируется
  дабл-запросом (перевод вопроса на второй язык) и балансировкой выдачи.
- **Выбор языка ответа** в чате — 🌐 Авто / 🇷🇺 Русский / 🇬🇧 English (управляет
  языком формулировки ответа независимо от языка вопроса и источников).
- **Гибкий выбор LLM** — единый интерфейс `llm_provider.py` поддерживает 5
  провайдеров: `ollama`, `groq`, `deepseek`, `openrouter`, `lmstudio`.
  Переключение через `config.py` без изменения кода.
- **Веб-интерфейс** на Gradio с историей диалога и памятью контекста.
- **Автоматическая индексация** новых файлов через наблюдатель за папкой архива
  (`watcher.py`), устанавливаемый как systemd-сервис.
- **Интеграция с Obsidian** — автогенерация заметок с YAML-frontmatter,
  тегами из таксономии и wikilinks, а также запросы к RAG прямо из заметок.
- **MCP-сервер** — доступ к базе знаний из Claude Code как набор инструментов.

---

## Архитектура системы

```
        Документы (archive/, рекурсивно)
        PDF · DOCX · DOC · TXT · MD · XLSX · CSV · PPTX · ODT
                          │
          ┌───────────────┴────────────────┐
          ▼                                 ▼
   [watcher.py]                       (ручной запуск)
   авто-наблюдатель                          │
          │                                  │
          ▼                                  ▼
   ┌──────────────────────────────────────────────┐
   │  [ingest.py]  парсинг → chunking →            │
   │  multilingual-e5-large → ChromaDB (на диске)  │
   └──────────────────────────────────────────────┘
          │                                  │
          │                                  ▼
          │                        [doc_to_obsidian.py]
          │                        → заметки в notes/ (Obsidian)
          ▼
   ┌──────────────────────────────────────────────┐
   │  [rag_engine.py]  семантический поиск +       │
   │  генерация ответа через [llm_provider.py]     │
   └──────────────────────────────────────────────┘
       │            │              │
       ▼            ▼              ▼
  [chat_ui.py]  [mcp_rag_     [rag_query_from_
   Gradio UI     server.py]    obsidian.py]
                 Claude Code   запрос из заметки
```

### Раскладка каталогов (KMS)

Система рассчитана на структуру `~/KMS` (переопределяется переменной окружения
`KMS_HOME`):

```
~/KMS/
├── archive/      # исходные документы (может быть симлинком на USB-диск)
├── notes/        # хранилище Obsidian (генерируемые заметки)
└── rag_system/   # код системы (этот каталог)
```

> Путь к KMS вычисляется от `$HOME`, а **не** от расположения `rag_system`, —
> поэтому код можно держать где угодно, не ломая пути к архиву и заметкам
> (`config.KMS_DIR`, `config.KMS_ARCHIVE_DIR`, `config.KMS_VAULT_DIR`).

---

## Компоненты

| Файл | Назначение |
|---|---|
| `config.py` | Единая конфигурация: пути, форматы, чанкинг, эмбеддинги, LLM, таксономия, память диалога |
| `llm_provider.py` | Единый интерфейс к 5 LLM-провайдерам (Ollama + 4 OpenAI-совместимых) |
| `ingest.py` | Индексация документов всех форматов → ChromaDB |
| `rag_engine.py` | Семантический поиск + генерация ответа с цитатами |
| `chat_ui.py` | Веб-интерфейс Gradio (история, память контекста) |
| `watcher.py` | Наблюдатель за `archive/`: авто-индексация + авто-заметки |
| `mcp_rag_server.py` | MCP-сервер для Claude Code (4 инструмента) |
| `doc_to_obsidian.py` | Генерация Obsidian-заметок из документов всех форматов |
| `pdf_to_obsidian.py` | То же только для PDF (исторический предшественник `doc_to_obsidian.py`) |
| `rag_query_from_obsidian.py` | RAG-запрос с записью ответа в заметку Obsidian |
| `check_cross_language.py` | Диагностика кросс-языкового поиска: языки в индексе (`--stats`) и язык каждого чанка выдачи |
| `rag-watcher.service` | Шаблон systemd-юнита для `watcher.py` |
| `install_service.sh` | Установка наблюдателя как пользовательского systemd-сервиса |

---

## Требования

- **ОС:** Linux (протестировано на Ubuntu 22.04)
- **Python:** 3.10+ (используется 3.12)
- **RAM:** минимум 8 ГБ (рекомендуется 16 ГБ для больших архивов)
- **GPU (опционально):** CUDA-карта ускоряет генерацию эмбеддингов при индексации
- **LLM:** Ollama (по умолчанию) **или** ключ к облачному провайдеру
- **Системные пакеты** (для парсинга `.doc`):
  ```bash
  sudo apt install libreoffice antiword
  ```

---

## Установка

### 1. Виртуальное окружение и зависимости

```bash
cd ~/KMS/rag_system
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> При первом запуске модель эмбеддингов `intfloat/multilingual-e5-large` (~2.2 ГБ)
> загрузится автоматически с Hugging Face.

### 2. LLM-провайдер

**Вариант А — локальная Ollama (по умолчанию, без ключей):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve                       # в отдельном терминале или как сервис
ollama pull qwen2.5:7b             # или другая модель из config
```

**Вариант Б — облачный провайдер** (Groq бесплатен, DeepSeek/OpenRouter дёшевы) —
см. раздел [«Выбор LLM»](#выбор-llm).

---

## Использование

### Шаг 1. Документы

Поместите файлы в `~/KMS/archive/` (поддерживаются подпапки и симлинки):

```bash
cp ~/статьи/*.pdf ~/KMS/archive/
# или весь архив с внешнего диска:
ln -s /run/media/$USER/MyDisk/library ~/KMS/archive
```

### Шаг 2. Индексация

```bash
source .venv/bin/activate

python ingest.py                       # индексация ~/KMS/archive
python ingest.py --doc-dir /path/docs  # другой каталог (--pdf-dir — алиас)
python ingest.py --reset               # полный сброс базы перед индексацией
```

Повторный запуск **не переиндексирует всё** — уже обработанные файлы
пропускаются по хэшу; новые добавляются.

### Шаг 3. Запросы

**Веб-интерфейс (Gradio):**

```bash
python chat_ui.py                      # http://127.0.0.1:7860
python chat_ui.py --host 0.0.0.0 --port 7860   # доступ из локальной сети
```

> По умолчанию чат считает эмбеддинг запроса на CPU, оставляя GPU под LLM
> (важно на картах с 8 ГБ VRAM). Принудительно отдать чату GPU:
> `CUDA_VISIBLE_DEVICES=0 python chat_ui.py`.

**Консоль:**

```bash
python rag_engine.py "Как рассчитывается скин-фактор скважины?"
python rag_engine.py "What is Darcy velocity?" --top-k 8
python rag_engine.py --stats           # статистика коллекции
```

---

## Автоматическая индексация (watcher + systemd)

Наблюдатель следит за `~/KMS/archive/` и при появлении/изменении файла запускает
`ingest.py` и `doc_to_obsidian.py`.

**Разовый запуск:**

```bash
python watcher.py                      # следит за config.ARCHIVE_DIR
python watcher.py --watch-dir /path --interval 5
```

**Установка как systemd-сервис пользователя:**

```bash
chmod +x install_service.sh
./install_service.sh
```

Скрипт подставляет пользователя и пути в `rag-watcher.service`, копирует юнит в
`~/.config/systemd/user/`, включает и запускает сервис. Управление:

```bash
journalctl --user -u rag-watcher -f          # логи
systemctl --user restart rag-watcher
systemctl --user stop rag-watcher
```

> Если архив лежит на USB-диске, раскомментируйте `After=...mount` в
> `rag-watcher.service`, чтобы сервис стартовал после монтирования.

---

## Интеграция с Obsidian

Хранилище Obsidian — `~/KMS/notes/`.

**Генерация заметок из документов** (frontmatter + теги из таксономии + wikilinks):

```bash
python doc_to_obsidian.py                     # все форматы из archive/
python doc_to_obsidian.py --force             # перегенерировать существующие
python doc_to_obsidian.py --dry-run           # без записи файлов
python doc_to_obsidian.py --force-single PATH # один конкретный файл
python pdf_to_obsidian.py                     # только PDF (legacy-вариант)
```

Для каждого документа извлекается текст первых страниц, отправляется в LLM для
анализа, создаётся `.md` с YAML-frontmatter; вторым проходом строятся wikilinks
между заметками с ≥ `WIKILINK_MIN_COMMON_TAGS` общими тегами.

**RAG-запрос с записью ответа прямо в заметку:**

```bash
python rag_query_from_obsidian.py "Какие механизмы ловушки CO2 описаны в Sleipner?"
python rag_query_from_obsidian.py "Механизмы ловушки CO2" --note "RAG-запрос" --append
```

---

## MCP-сервер (Claude Code)

`mcp_rag_server.py` предоставляет Claude Code доступ к базе знаний как набор
инструментов:

| Инструмент | Назначение |
|---|---|
| `search_knowledge_base` | Семантический поиск (+ опц. генерация ответа LLM) |
| `list_documents` | Список проиндексированных документов |
| `get_document_info` | Информация о конкретном документе |
| `get_stats` | Статистика базы знаний |

Регистрация в `~/.claude/mcp_servers.json`:

```json
{
  "rag_kms": {
    "command": "python",
    "args": ["/home/<user>/KMS/rag_system/mcp_rag_server.py"],
    "cwd": "/home/<user>/KMS/rag_system"
  }
}
```

---

## Выбор LLM

Провайдер и модель задаются в `config.py`:

```python
LLM_PROVIDER = "ollama"          # ollama | groq | deepseek | openrouter | lmstudio
LLM_MODEL    = "qwen3.5:latest"  # модель для выбранного провайдера (уже установлена в этой системе)
LLM_API_KEY  = ""                # ключ для облачных (пусто для локальных)
```

API-ключ можно не хранить в файле, а задать переменной окружения:
`RAG_GROQ_API_KEY`, `RAG_DEEPSEEK_API_KEY`, `RAG_OPENROUTER_API_KEY`.

| Провайдер | Ключ | Пример модели | Примечание |
|---|---|---|---|
| `ollama` | — | `qwen2.5:7b`, `mistral`, `llama3.2` | Локально, офлайн (по умолчанию) |
| `lmstudio` | — | `local-model` | Локальный сервер LM Studio (:1234) |
| `groq` | да | `llama-3.3-70b-versatile` | Бесплатный тариф |
| `deepseek` | да | `deepseek-chat`, `deepseek-reasoner` | Очень дёшево |
| `openrouter` | да | `qwen/qwen3-14b:free` | 50+ моделей, есть бесплатные |

> Полностью офлайн-контур обеспечивают только `ollama` и `lmstudio`.
> Облачные провайдеры отправляют контекст запроса во внешний сервис.

---

## Конфигурация

Все параметры — в `config.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `SUPPORTED_EXTENSIONS` | 9 форматов | Какие файлы индексировать |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 512 / 64 | Размер и перекрытие чанков |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Модель эмбеддингов |
| `EMBEDDING_DEVICE` | `cpu` | Устройство для эмбеддингов (`cpu`/`cuda`/`None`); CPU по умолчанию, чтобы не конкурировать с Ollama за GPU |
| `EMBEDDING_BATCH_SIZE` | 32 | Батч эмбеддингов (уменьшить при нехватке памяти) |
| `CHROMA_COLLECTION_NAME` | `petroleum_papers` | Имя коллекции ChromaDB |
| `DEFAULT_TOP_K` / `MAX_CONTEXT_CHUNKS` | 7 / 8 | Извлекаемые / передаваемые в LLM чанки |
| `CROSS_LANGUAGE_BALANCE` | `True` | Балансировка выдачи по языку (RU/EN), чтобы запрос на одном языке не вытеснял источники на другом |
| `CROSS_LANGUAGE_TRANSLATE_QUERY` | `True` | Дабл-запрос: переводит вопрос на второй язык (ru↔en) и ищет обоими, объединяя пулы — иначе перекос `e5` оставляет пул одноязычным и балансировать нечего |
| `RETRIEVAL_FETCH_K` / `MIN_CHUNKS_PER_LANGUAGE` | 200 / 2 | Пул кандидатов до балансировки / гарантированный минимум чанков на язык |
| `LLM_PROVIDER` / `LLM_MODEL` | `ollama` / … | LLM-провайдер и модель |
| `OLLAMA_OPTIONS` | temp 0.2 … | Параметры генерации |
| `UI_HOST` / `UI_PORT` | `127.0.0.1` / 7860 | Адрес Gradio UI |
| `KMS_DIR` | `$HOME/KMS` | Корень KMS (env `KMS_HOME`) |
| `TAXONOMY` | список тегов | Теги для Obsidian-заметок |
| `MAX_HISTORY_MESSAGES` | 6 | Глубина памяти диалога |

---

## Структура проекта

```
rag_system/
├── config.py                  # конфигурация
├── llm_provider.py            # интерфейс к LLM-провайдерам
├── ingest.py                  # индексация → ChromaDB
├── rag_engine.py              # поиск + генерация
├── chat_ui.py                 # Gradio UI
├── watcher.py                 # авто-наблюдатель
├── mcp_rag_server.py          # MCP-сервер для Claude Code
├── doc_to_obsidian.py         # заметки Obsidian (все форматы)
├── pdf_to_obsidian.py         # заметки Obsidian (только PDF, legacy)
├── rag_query_from_obsidian.py # RAG-запрос из заметки
├── check_cross_language.py    # диагностика кросс-языкового поиска
├── obsidian_templates/        # шаблоны заметок Obsidian
├── rag-watcher.service        # шаблон systemd-юнита
├── install_service.sh         # установка сервиса
├── requirements.txt           # зависимости Python
├── README.md                  # эта документация
├── documents/                 # локальная папка для документов (опц.)
├── chroma_db/                 # векторная база ChromaDB (создаётся индексацией)
└── logs/
    ├── rag_system.log         # лог системы
    └── history/               # история диалогов (JSON)
```

---

## Устранение неполадок

**Ollama недоступна** (`Ошибка подключения к Ollama`):
```bash
ollama list        # проверить статус
ollama serve       # запустить сервер
```

**Модель не найдена:**
```bash
ollama pull qwen2.5:7b
```

**База пуста** (`не найдено релевантных документов`):
```bash
ls ~/KMS/archive/  # проверить наличие файлов
python ingest.py   # запустить индексацию
```

**Ошибка памяти при индексации** — уменьшите в `config.py`:
```python
EMBEDDING_BATCH_SIZE = 8
```

**Облачный провайдер: 401 / 429** — проверьте `LLM_API_KEY` (401) или дождитесь
сброса лимита / переключитесь на другого провайдера (429).

**Watcher следит не за той папкой** — `ARCHIVE_DIR` должен быть абсолютным;
проверьте `KMS_HOME`, если архив лежит по нестандартному пути.

---

## Лицензия

Проект для внутреннего использования. Зависимости — под своими лицензиями:
sentence-transformers (Apache 2.0), ChromaDB (Apache 2.0), Gradio (Apache 2.0),
PyMuPDF (AGPL-3.0 — для коммерческого использования нужна коммерческая лицензия),
Ollama (MIT).
