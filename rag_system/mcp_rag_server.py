"""
mcp_rag_server.py — MCP-сервер для интеграции RAG-системы с Claude Code.

Предоставляет инструменты (tools) для Claude Code:
  - search_knowledge_base   — семантический поиск по базе знаний
  - list_documents          — список проиндексированных документов
  - get_document_info       — информация о конкретном документе
  - get_stats               — статистика базы знаний

Запуск:
    python mcp_rag_server.py

Настройка в Claude Code (~/.claude/mcp_servers.json):
    {
      "rag_kms": {
        "command": "python",
        "args": ["/home/<user>/KMS/rag_system/mcp_rag_server.py"],
        "cwd": "/home/<user>/KMS/rag_system"
      }
    }
"""

import json
import logging
import sys
import os
from pathlib import Path
from typing import Any

# Добавляем директорию rag_system в sys.path для импорта config и rag_engine
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))

import chromadb
import requests
from sentence_transformers import SentenceTransformer

import config
from llm_provider import LLMProvider, PROVIDER_CONFIGS

# ─────────────────────────────────────────────────────────────
# Логирование (только stderr — stdout зарезервирован для MCP)
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] mcp_rag: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_rag")

# ─────────────────────────────────────────────────────────────
# Инициализация ChromaDB и модели эмбеддингов (один раз)
# ─────────────────────────────────────────────────────────────

logger.info("Загрузка модели эмбеддингов %s ...", config.EMBEDDING_MODEL)
_embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
logger.info("Модель загружена.")

_chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
_collection = _chroma_client.get_or_create_collection(
    name=config.CHROMA_COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
logger.info(
    "ChromaDB: коллекция '%s', документов в базе: %d",
    config.CHROMA_COLLECTION_NAME,
    _collection.count(),
)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _embed_query(query: str) -> list[float]:
    """Создаёт эмбеддинг для поискового запроса с обязательным префиксом."""
    prefixed = f"query: {query}"
    return _embedding_model.encode(prefixed, normalize_embeddings=True).tolist()


def _check_ollama() -> str | None:
    """Проверяет доступность Ollama. Возвращает имя модели или None."""
    try:
        resp = requests.get(config.OLLAMA_TAGS_URL, timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        for model_name in [config.OLLAMA_MODEL, config.OLLAMA_FALLBACK_MODEL]:
            for avail in models:
                if avail.startswith(model_name):
                    return avail
        return models[0] if models else None
    except Exception:
        return None


def _ask_ollama(model: str, context: str, query: str) -> str:
    """Генерирует ответ через Ollama HTTP API."""
    prompt = (
        f"Контекст из базы знаний:\n{context}\n\n"
        f"Вопрос: {query}\n\n"
        "Ответь на основе предоставленного контекста. "
        "Цитируй источники в формате [Файл: <имя>, стр. <номер>]."
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "system": config.SYSTEM_PROMPT,
        "stream": False,
        "options": config.OLLAMA_OPTIONS,
    }
    resp = requests.post(config.OLLAMA_API_URL, json=payload, timeout=config.OLLAMA_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


# ─────────────────────────────────────────────────────────────
# Реализация инструментов
# ─────────────────────────────────────────────────────────────

def tool_search_knowledge_base(
    query: str,
    top_k: int = 5,
    generate_answer: bool = True,
    file_filter: str = "",
) -> dict[str, Any]:
    """
    Семантический поиск по базе знаний + генерация ответа через Ollama.

    Args:
        query:           Поисковый запрос (русский или английский).
        top_k:           Количество релевантных фрагментов (1–20, по умолчанию 5).
        generate_answer: Генерировать развёрнутый ответ через LLM (по умолчанию True).
        file_filter:     Фильтр по имени файла (необязательно, частичное совпадение).
    """
    top_k = max(1, min(20, top_k))
    query_embedding = _embed_query(query)

    where_clause = None
    if file_filter:
        where_clause = {"source_file": {"$contains": file_filter}}

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_clause,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    context_parts = []

    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            relevance = round(1.0 - dist, 3)
            source_file = meta.get("source_file", "unknown")
            page = meta.get("page", "?")
            file_type = meta.get("file_type", "")

            snippet = doc[:200].strip().replace("\n", " ")
            if len(doc) > 200:
                snippet += "..."

            chunk = {
                "relevance": relevance,
                "source_file": source_file,
                "page": page,
                "file_type": file_type,
                "text_preview": doc[:300] + ("..." if len(doc) > 300 else ""),
                "snippet": snippet,
            }
            chunks.append(chunk)

            context_parts.append(
                f"[{len(chunks)}] [Файл: {source_file}, стр. {page}]\n{doc}"
            )

    answer = None
    model_used = None

    if generate_answer and chunks:
        model_used = _check_ollama()
        if model_used:
            try:
                context_text = "\n\n---\n\n".join(context_parts)
                answer = _ask_ollama(model_used, context_text, query)
            except Exception as e:
                answer = f"[Ошибка генерации ответа: {e}]"
                logger.warning("Ollama error: %s", e)
        else:
            answer = "[Ollama недоступна — показаны только релевантные фрагменты]"

    return {
        "query": query,
        "chunks_found": len(chunks),
        "chunks": chunks,
        "answer": answer,
        "model_used": model_used,
    }


def tool_list_documents(limit: int = 50) -> dict[str, Any]:
    """
    Возвращает список уникальных файлов, проиндексированных в базе знаний.

    Args:
        limit: Максимальное количество файлов (по умолчанию 50).
    """
    limit = max(1, min(200, limit))
    total = _collection.count()

    if total == 0:
        return {"total_chunks": 0, "unique_files": 0, "files": []}

    # Получаем метаданные всех чанков (ограниченно)
    fetch_limit = min(total, 5000)
    results = _collection.get(limit=fetch_limit, include=["metadatas"])

    seen = {}
    for meta in results["metadatas"]:
        fname = meta.get("source_file", "unknown")
        if fname not in seen:
            seen[fname] = {
                "file": fname,
                "file_type": meta.get("file_type", ""),
                "chunk_count": 0,
                "pages": set(),
            }
        seen[fname]["chunk_count"] += 1
        page = meta.get("page")
        if page and page != "?":
            seen[fname]["pages"].add(page)

    files = []
    for info in sorted(seen.values(), key=lambda x: x["file"])[:limit]:
        files.append({
            "file": info["file"],
            "file_type": info["file_type"],
            "chunks": info["chunk_count"],
            "pages": len(info["pages"]) or None,
        })

    return {
        "total_chunks": total,
        "unique_files": len(seen),
        "shown": len(files),
        "files": files,
    }


def tool_get_document_info(filename: str) -> dict[str, Any]:
    """
    Возвращает подробную информацию о конкретном документе в базе.

    Args:
        filename: Имя файла (или его часть) для поиска.
    """
    results = _collection.get(
        where={"source_file": {"$contains": filename}},
        include=["documents", "metadatas"],
    )

    if not results["ids"]:
        return {"found": False, "filename_query": filename}

    metadatas = results["metadatas"]
    source_file = metadatas[0].get("source_file", filename)
    file_type = metadatas[0].get("file_type", "")

    pages = sorted({
        m.get("page") for m in metadatas
        if m.get("page") and m.get("page") != "?"
    })

    # Первые 500 символов первого чанка как превью
    preview = results["documents"][0][:500] if results["documents"] else ""

    return {
        "found": True,
        "source_file": source_file,
        "file_type": file_type,
        "total_chunks": len(results["ids"]),
        "pages_indexed": pages[:20],
        "text_preview": preview,
    }


def tool_get_stats() -> dict[str, Any]:
    """Возвращает общую статистику базы знаний, LLM-провайдера и статус сервисов."""
    total_chunks = _collection.count()

    # Подсчёт уникальных файлов и форматов
    unique_files = 0
    format_counts: dict[str, int] = {}

    if total_chunks > 0:
        fetch_limit = min(total_chunks, 5000)
        results = _collection.get(limit=fetch_limit, include=["metadatas"])
        unique_files_set = set()
        for meta in results["metadatas"]:
            unique_files_set.add(meta.get("source_file", "?"))
            ft = meta.get("file_type", "unknown")
            format_counts[ft] = format_counts.get(ft, 0) + 1
        unique_files = len(unique_files_set)

    # Информация о текущем LLM-провайдере
    try:
        provider = LLMProvider.from_config()
        provider_info = provider.get_info()
        availability = provider.check_availability()
        provider_status = "online" if availability["ok"] else "offline"
        provider_error = availability.get("error", "")
    except Exception as e:
        provider_info = {"provider": "?", "model": "?", "description": str(e), "api_key_set": False}
        provider_status = "error"
        provider_error = str(e)

    # Обратная совместимость: статус Ollama если провайдер = ollama
    ollama_model = _check_ollama() if provider_info.get("provider") == "ollama" else None

    return {
        "knowledge_base": {
            "total_chunks": total_chunks,
            "unique_documents": unique_files,
            "collection_name": config.CHROMA_COLLECTION_NAME,
            "embedding_model": config.EMBEDDING_MODEL,
            "format_distribution": format_counts,
        },
        "llm_provider": {
            "provider": provider_info["provider"],
            "model": provider_info["model"],
            "description": provider_info["description"],
            "status": provider_status,
            "api_key_set": provider_info["api_key_set"],
            "error": provider_error,
        },
        "available_providers": list(PROVIDER_CONFIGS.keys()),
        "supported_formats": sorted(config.SUPPORTED_EXTENSIONS),
    }


# ─────────────────────────────────────────────────────────────
# MCP-протокол (JSON-RPC 2.0 через stdin/stdout)
# ─────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_knowledge_base": {
        "fn": tool_search_knowledge_base,
        "description": (
            "Семантический поиск по базе знаний нефтегазовых документов. "
            "Находит релевантные фрагменты и генерирует ответ через локальный LLM (Ollama). "
            "База содержит PDF, DOCX, TXT, XLSX, PPTX и другие документы. "
            "Поддерживает русский и английский языки."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос на русском или английском языке.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Количество релевантных фрагментов (1–20). По умолчанию 5.",
                    "default": 5,
                },
                "generate_answer": {
                    "type": "boolean",
                    "description": "Генерировать развёрнутый ответ через LLM. По умолчанию true.",
                    "default": True,
                },
                "file_filter": {
                    "type": "string",
                    "description": "Необязательный фильтр по имени файла.",
                    "default": "",
                },
            },
            "required": ["query"],
        },
    },
    "list_documents": {
        "fn": tool_list_documents,
        "description": "Возвращает список всех документов, проиндексированных в базе знаний.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Максимум файлов в ответе (по умолчанию 50).",
                    "default": 50,
                },
            },
        },
    },
    "get_document_info": {
        "fn": tool_get_document_info,
        "description": "Подробная информация о конкретном документе в базе знаний.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Имя файла или его часть для поиска.",
                },
            },
            "required": ["filename"],
        },
    },
    "get_stats": {
        "fn": tool_get_stats,
        "description": (
            "Статистика базы знаний: количество документов, чанков, "
            "форматы файлов, статус Ollama и активная модель."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
}


def _make_tools_list() -> list[dict]:
    tools = []
    for name, info in TOOL_REGISTRY.items():
        tools.append({
            "name": name,
            "description": info["description"],
            "inputSchema": info["inputSchema"],
        })
    return tools


def _send(obj: dict) -> None:
    """Отправляет JSON-объект в stdout (MCP-протокол)."""
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _handle_request(req: dict) -> None:
    """Обрабатывает один JSON-RPC запрос."""
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    # ── initialize ──────────────────────────────────────────
    if method == "initialize":
        _send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "rag-kms",
                    "version": "4.0.0",
                },
            },
        })

    # ── tools/list ──────────────────────────────────────────
    elif method == "tools/list":
        _send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": _make_tools_list()},
        })

    # ── tools/call ──────────────────────────────────────────
    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOL_REGISTRY:
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}",
                },
            })
            return

        try:
            fn = TOOL_REGISTRY[tool_name]["fn"]
            result = fn(**tool_args)
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2),
                        }
                    ],
                    "isError": False,
                },
            })
        except Exception as e:
            logger.exception("Ошибка при вызове инструмента '%s': %s", tool_name, e)
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Ошибка: {type(e).__name__}: {e}",
                        }
                    ],
                    "isError": True,
                },
            })

    # ── notifications (не требуют ответа) ───────────────────
    elif method.startswith("notifications/"):
        pass

    # ── неизвестный метод ───────────────────────────────────
    elif req_id is not None:
        _send({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        })


# ─────────────────────────────────────────────────────────────
# Главный цикл
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("MCP RAG-сервер запущен. Ожидание команд на stdin...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            logger.warning("Невалидный JSON: %s | строка: %s", e, line[:80])
            continue
        try:
            _handle_request(req)
        except Exception as e:
            logger.exception("Необработанная ошибка: %s", e)


if __name__ == "__main__":
    main()
