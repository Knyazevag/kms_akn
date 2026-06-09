# RAG-система для научных PDF-архивов
## Нефтегазовая инженерия | Русский + English

Локальная система поиска и генерации ответов (RAG) по научным PDF-документам. Работает полностью offline — данные не покидают ваш компьютер.

---

## Архитектура системы

```
PDF-файлы
    │
    ▼
[ingest.py] → PyMuPDF → Chunking → multilingual-e5-large → ChromaDB (диск)
                                                                  │
[chat_ui.py] ← Gradio UI                                          │
    │                                                             │
    ▼                                                             │
[rag_engine.py] ──── семантический поиск ────────────────────────┘
    │
    ▼
Ollama API (llama3 / mistral) → Ответ + источники
```

**Компоненты:**
| Компонент | Назначение |
|---|---|
| `config.py` | Единая конфигурация всех параметров |
| `ingest.py` | Индексация PDF → ChromaDB |
| `rag_engine.py` | Поиск + генерация ответа |
| `chat_ui.py` | Веб-интерфейс Gradio |

---

## Требования

- **ОС:** Ubuntu 20.04+ (протестировано на 22.04)
- **Python:** 3.10+
- **Ollama:** установлен и запущен
- **RAM:** минимум 8 ГБ (рекомендуется 16 ГБ для больших архивов)
- **GPU (опционально):** CUDA-совместимая карта ускорит генерацию эмбеддингов

---

## Установка

### 1. Установка Ollama

```bash
# Установка
curl -fsSL https://ollama.com/install.sh | sh

# Запуск сервера Ollama (в отдельном терминале или как сервис)
ollama serve

# Загрузка языковой модели (выберите одну)
ollama pull llama3          # Рекомендуется (4.7 ГБ)
# ollama pull mistral       # Альтернатива (4.1 ГБ)
# ollama pull gemma2        # Лёгкая альтернатива
```

### 2. Клонирование / копирование проекта

```bash
# Перейдите в директорию проекта
cd /путь/к/rag_system
```

### 3. Создание виртуального окружения

```bash
# Создание окружения
python3 -m venv .venv

# Активация
source .venv/bin/activate
```

### 4. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Примечание:** Установка `sentence-transformers` и PyTorch может занять несколько минут.
> При первом запуске модель `intfloat/multilingual-e5-large` (~1.2 ГБ) будет загружена автоматически с Hugging Face.

---

## Использование

### Шаг 1: Подготовка PDF-документов

Поместите PDF-файлы в директорию `documents/`:

```bash
mkdir -p documents
cp /путь/к/вашим/статьям/*.pdf documents/

# Или создайте символические ссылки на существующую папку
ln -s /media/data/petroleum_papers documents/papers
```

Директория `documents/` поддерживает **рекурсивную структуру** — PDF можно организовывать в подпапки:
```
documents/
├── reservoir_engineering/
│   ├── darcy_flow_2023.pdf
│   └── skin_factor_analysis.pdf
├── drilling/
│   └── wellbore_integrity.pdf
└── enhanced_recovery/
    └── eor_methods_review.pdf
```

### Шаг 2: Индексация документов

```bash
# Активируйте окружение (если ещё не активировано)
source .venv/bin/activate

# Базовая индексация
python ingest.py

# Индексация из другой директории
python ingest.py --pdf-dir /media/data/papers

# Переиндексация (удаляет существующую базу и создаёт новую)
python ingest.py --reset
```

**Ожидаемый вывод:**
```
2024-01-15 10:23:45 [INFO] ingest: Запуск индексации PDF-архива
2024-01-15 10:23:45 [INFO] ingest: Директория с PDF: /rag_system/documents
2024-01-15 10:23:47 [INFO] ingest: Загрузка модели 'intfloat/multilingual-e5-large'...
2024-01-15 10:24:10 [INFO] ingest: Модель загружена успешно.
Обработка PDF: 100%|████████████████| 47/47 [05:23<00:00,  6.88с/файл]
Индексация чанков: 100%|████████████| 8432/8432 [03:11<00:00, 44.1чанк/с]
2024-01-15 10:32:55 [INFO] ingest: Индексация завершена за 525.3 сек.
2024-01-15 10:32:55 [INFO] ingest: Обработано чанков: 8432
```

### Шаг 3: Запуск веб-интерфейса

```bash
# Запуск Gradio UI
python chat_ui.py

# Откройте в браузере:
# http://127.0.0.1:7860
```

> Интерфейс доступен только локально. Для доступа с другого устройства в сети:
> ```bash
> python chat_ui.py --host 0.0.0.0 --port 7860
> ```

### Консольный режим (без UI)

```bash
# Быстрый вопрос из терминала
python rag_engine.py "Как рассчитывается скин-фактор скважины?"

# С указанием числа источников
python rag_engine.py "What is Darcy velocity?" --top-k 8

# Статистика базы знаний
python rag_engine.py --stats
```

---

## Конфигурация

Все параметры настраиваются в файле `config.py`:

| Параметр | Значение по умолчанию | Описание |
|---|---|---|
| `CHUNK_SIZE` | 512 | Размер чанка в символах |
| `CHUNK_OVERLAP` | 64 | Перекрытие между чанками |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Модель эмбеддингов |
| `OLLAMA_MODEL` | `llama3` | Основная LLM |
| `OLLAMA_FALLBACK_MODEL` | `mistral` | Резервная LLM |
| `DEFAULT_TOP_K` | 5 | Число извлекаемых чанков |
| `PDF_DIR` | `./documents` | Директория с PDF |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Путь к базе ChromaDB |
| `UI_PORT` | 7860 | Порт веб-интерфейса |

**Пример: смена модели на Mistral**

Откройте `config.py` и измените:
```python
OLLAMA_MODEL: str = "mistral"
```

---

## Добавление новых документов

При добавлении новых PDF **не нужно переиндексировать всё** — достаточно запустить `ingest.py` снова. Система использует `upsert`, поэтому существующие документы обновятся, а новые добавятся:

```bash
cp /новые/статьи/*.pdf documents/
python ingest.py
```

Для полной переиндексации (если изменили `CHUNK_SIZE` или модель эмбеддингов):
```bash
python ingest.py --reset
```

---

## Устранение неполадок

### Ollama недоступна

```
Ошибка подключения к Ollama. Убедитесь, что сервер запущен.
```
**Решение:**
```bash
# Проверьте статус
ollama list

# Запустите сервер
ollama serve
```

### Модель не найдена

```
Модель 'llama3' не найдена.
```
**Решение:**
```bash
ollama pull llama3
```

### ChromaDB пуста

```
В базе знаний не найдено релевантных документов.
```
**Решение:**
```bash
# Убедитесь, что PDF-файлы в директории
ls documents/

# Запустите индексацию
python ingest.py
```

### Ошибка памяти при генерации эмбеддингов

**Решение:** Уменьшите размер батча в `config.py`:
```python
EMBEDDING_BATCH_SIZE: int = 8   # Вместо 32
```

### Медленная генерация ответов

- Используйте более лёгкую модель: `ollama pull gemma2:2b`
- Измените в `config.py`: `OLLAMA_MODEL = "gemma2:2b"`

---

## Структура файлов проекта

```
rag_system/
├── config.py          # Конфигурация
├── ingest.py          # Индексация PDF
├── rag_engine.py      # RAG-движок
├── chat_ui.py         # Gradio интерфейс
├── requirements.txt   # Зависимости Python
├── README.md          # Эта документация
├── documents/         # Папка для PDF-файлов (создаётся автоматически)
├── chroma_db/         # База данных ChromaDB (создаётся при индексации)
└── logs/
    └── rag_system.log # Лог-файл системы
```

---

## Лицензия

Проект для внутреннего использования. Зависимости распространяются под своими лицензиями:
- sentence-transformers: Apache 2.0
- ChromaDB: Apache 2.0
- PyMuPDF: AGPL-3.0 (для коммерческого использования требуется коммерческая лицензия)
- Gradio: Apache 2.0
- Ollama: MIT
