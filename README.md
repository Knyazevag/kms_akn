# KMS — Intelligent Document Search System

> **Languages:** 🇬🇧 English (below) · [🇷🇺 Русский](#kms--интеллектуальная-система-поиска-по-документам)

A local RAG (Retrieval-Augmented Generation) system for searching and analyzing
large archives of scientific and technical documents. Runs fully offline.

## Features
- Indexing of documents (PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT) into ChromaDB.
- Answering questions about the archive content with references to sources (RU/EN).
- Automatic creation of structured Obsidian notes with tags and a link graph.
- Folder watcher: new files are indexed automatically (including on USB/NTFS).
- Multiple LLM providers: Ollama (local), Groq, DeepSeek, OpenRouter, LM Studio.
- Optional GPU acceleration of indexing (NVIDIA CUDA).
- Integration with Claude Code via MCP.

## Documentation
- 🇬🇧 User guide (English) — [`rag_final_guide_eng.md`](rag_final_guide_eng.md).
- 🇷🇺 User guide (Russian) — [`rag_final_guide.md`](rag_final_guide.md)
  (PDF build: [`rag_final_guide.pdf`](rag_final_guide.pdf)).
- Technical description of the system — [`rag_system/README_eng.md`](rag_system/README_eng.md)
  ([Russian](rag_system/README.md)).

## Structure
- `rag_system/` — system code (indexing, RAG engine, chat UI, watcher, MCP server, templates);
  README in English and Russian (`README_eng.md` / `README.md`).
- `rag_final_guide.md` / `.pdf` — user guide (RU); `rag_final_guide_eng.md` — English version.
- `generate_rag_final_guide.py` — generator of the branded PDF from the guide.

## Quick start
See sections 1–3 of the guide. In short:
```bash
cd rag_system
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ollama + a model, then:
python ingest.py          # indexing
python chat_ui.py         # web interface at http://127.0.0.1:7860
```

---
Author: Alexander Knyazev, Head of the Decarbonization Technologies Department. Version 5.1.

## License

[MIT](LICENSE) © 2026 Alexander Knyazev.

---
---

# KMS — Интеллектуальная система поиска по документам

> **Языки:** [🇬🇧 English](#kms--intelligent-document-search-system) · 🇷🇺 Русский (ниже)

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
- 🇷🇺 Руководство пользователя — [`rag_final_guide.md`](rag_final_guide.md)
  (сборка в PDF: [`rag_final_guide.pdf`](rag_final_guide.pdf)).
- 🇬🇧 User guide (English) — [`rag_final_guide_eng.md`](rag_final_guide_eng.md).
- Техническое описание системы — [`rag_system/README.md`](rag_system/README.md)
  ([English](rag_system/README_eng.md)).

## Структура
- `rag_system/` — код системы (индексация, RAG-движок, чат-UI, наблюдатель, MCP-сервер, шаблоны);
  README на русском и английском (`README.md` / `README_eng.md`).
- `rag_final_guide.md` / `.pdf` — руководство пользователя (RU); `rag_final_guide_eng.md` — английская версия.
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
Автор: Александр Князев, начальник отдела технологий декарбонизации. Версия 5.1.

## Лицензия

[MIT](LICENSE) © 2026 Александр Князев.
