# KMS — Интеллектуальная система поиска по документам

Локальная RAG-система (Retrieval-Augmented Generation) для поиска и анализа
больших архивов научных и технических документов. Работает полностью офлайн.

## Возможности
- Индексация документов (PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT) в ChromaDB.
- Ответы на вопросы по содержимому архива со ссылками на источники (RU/EN).
- Автоматическое создание структурированных заметок Obsidian с тегами и графом связей.
- Наблюдатель за папкой: новые файлы индексируются автоматически (в т.ч. на USB/NTFS).
- Несколько LLM-провайдеров: Ollama (локально), Groq, DeepSeek, OpenRouter, LM Studio.
- Опциональное GPU-ускорение индексации (NVIDIA CUDA).
- Интеграция с Claude Code через MCP.

## Документация
Полное руководство пользователя — [`rag_final_guide.md`](rag_final_guide.md)
(сборка в PDF: [`rag_final_guide.pdf`](rag_final_guide.pdf)).

## Структура
- `rag_system/` — код системы (индексация, RAG-движок, чат-UI, наблюдатель, MCP-сервер, шаблоны).
- `rag_final_guide.md` / `.pdf` — руководство пользователя.
- `generate_rag_final_guide.py` — генератор фирменного PDF из руководства.

## Быстрый старт
См. разделы 1–3 руководства. Кратко:
```bash
cd rag_system
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ollama + модель, затем:
python ingest.py          # индексация
python chat_ui.py         # веб-интерфейс на http://127.0.0.1:7860
```

---
Автор: Александр Князев. Версия 5.1.

## Лицензия

[MIT](LICENSE) © 2026 Александр Князев.
