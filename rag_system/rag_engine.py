"""
rag_engine.py — Движок RAG (Retrieval-Augmented Generation).

Класс RAGEngine реализует:
  - Поиск релевантных чанков в ChromaDB по семантической близости.
  - Генерацию ответа через Ollama HTTP API с системным промптом.
  - Форматирование ответа с цитатами источников (файл + страница).

Ollama вызывается напрямую через HTTP (requests), без Python SDK.
"""

import datetime
import json
import logging
import sys
import uuid
from typing import Optional

import chromadb
import requests
from sentence_transformers import SentenceTransformer

import config
from llm_provider import LLMProvider

# ─────────────────────────────────────────────────────────────
# Настройка логирования
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rag_engine")


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _check_ollama_availability(model: str) -> str:
    """
    Проверяет доступность Ollama и наличие нужной модели.
    Возвращает имя модели, которую следует использовать.
    Если основная модель недоступна — переключается на запасную.
    """
    try:
        response = requests.get(config.OLLAMA_TAGS_URL, timeout=5)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]
        logger.info(f"Доступные модели Ollama: {available_models}")

        # Ищем основную модель (с учётом тегов вида "llama3:latest")
        for avail in available_models:
            if avail.startswith(model):
                logger.info(f"Используется модель: {avail}")
                return avail

        # Пробуем запасную модель
        for avail in available_models:
            if avail.startswith(config.OLLAMA_FALLBACK_MODEL):
                logger.warning(
                    f"Модель '{model}' не найдена. Используется запасная: {avail}"
                )
                return avail

        # Если вообще ничего нет — берём первую доступную
        if available_models:
            logger.warning(f"Используется первая доступная модель: {available_models[0]}")
            return available_models[0]

        logger.error("Ollama не содержит ни одной загруженной модели.")
        return model  # Возвращаем оригинал, ошибка проявится при запросе

    except requests.exceptions.ConnectionError:
        logger.error(
            "Ollama недоступна! Убедитесь, что сервер запущен: `ollama serve`"
        )
        return model
    except Exception as e:
        logger.error(f"Ошибка при проверке Ollama: {e}")
        return model


def _format_sources(chunks: list[dict]) -> list[dict]:
    """
    Дедуплицирует и форматирует список источников с фрагментами текста.
    Возвращает список словарей:
        {"file_name": str, "page_num": int, "language": str, "snippet": str, "index": int}
    """
    seen = set()
    sources = []
    idx = 1
    for chunk in chunks:
        meta = chunk["metadata"]
        text = chunk["text"]
        key = (meta.get("file_name", "?"), meta.get("page_num", 0))
        if key not in seen:
            seen.add(key)
            snippet = text[:200].strip().replace("\n", " ")
            if len(text) > 200:
                snippet += "..."
            sources.append({
                "index": idx,
                "file_name": meta.get("file_name", "Неизвестный файл"),
                "page_num": meta.get("page_num", 0),
                "language": meta.get("language", "unknown"),
                "snippet": snippet,
            })
            idx += 1
    return sources



# ─────────────────────────────────────────────────────────────
# Управление памятью диалога
# ─────────────────────────────────────────────────────────────


class ConversationMemory:
    """
    Хранит историю диалога в памяти и на диске (JSON).

    Каждая сессия — отдельный JSON-файл:
        logs/history/<session_id>.json

    Формат файла:
        {
            "session_id": "...",
            "created_at": "...",
            "updated_at": "...",
            "messages": [
                {"role": "user", "content": "...", "timestamp": "..."},
                {"role": "assistant", "content": "...", "timestamp": "...", "sources": [...]}
            ]
        }
    """

    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.history_dir = config.HISTORY_DIR
        self.messages = []
        self._file_path = self.history_dir / f"{self.session_id}.json"

        # Загружаем существующую сессию если есть
        if self._file_path.exists():
            self._load()

        logger.info(f"ConversationMemory: сессия {self.session_id}")

    def add_user_message(self, content):
        """Добавляет сообщение пользователя."""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        })

    def add_assistant_message(self, content, sources=None):
        """Добавляет ответ ассистента с источниками."""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "sources": sources or [],
        })
        self._save()

    def get_llm_messages(self):
        """
        Возвращает последние N пар сообщений в формате для Ollama API.
        Исключает поле 'sources' и 'timestamp' — только role + content.
        """
        llm_messages = []
        for msg in self.messages[-(config.MAX_HISTORY_MESSAGES * 2):]:
            llm_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return llm_messages

    def clear(self):
        """Очищает историю текущей сессии."""
        self.messages = []
        if self._file_path.exists():
            self._file_path.unlink()
        logger.info(f"История сессии {self.session_id} очищена.")

    def export_markdown(self):
        """Экспортирует диалог в Markdown-формате."""
        lines = [f"# Диалог RAG — Сессия {self.session_id}\n"]
        lines.append(f"*Создан: {self.messages[0]['timestamp'] if self.messages else 'N/A'}*\n\n")

        for msg in self.messages:
            role_label = "**Вопрос:**" if msg["role"] == "user" else "**Ответ:**"
            lines.append(f"### {role_label}\n")
            lines.append(f"{msg['content']}\n")

            if msg.get("sources"):
                lines.append("\n**Источники:**\n")
                for src in msg["sources"]:
                    snippet = src.get('snippet', '')
                    lines.append(
                        f"- [{src['index']}] `{src['file_name']}`, стр. {src['page_num']} "
                        f"— *{snippet[:80]}...*\n"
                    )
            lines.append("\n---\n\n")

        return "".join(lines)

    def get_sessions_list(self):
        """Возвращает список всех сохранённых сессий."""
        sessions = []
        for f in sorted(self.history_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = json.load(fh)
                sessions.append({
                    "session_id": data.get("session_id", f.stem),
                    "created_at": data.get("created_at", "?"),
                    "message_count": len(data.get("messages", [])),
                })
            except Exception:
                pass
        return sessions[:config.MAX_SAVED_SESSIONS]

    def _save(self):
        """Сохраняет историю на диск."""
        data = {
            "session_id": self.session_id,
            "created_at": self.messages[0]["timestamp"] if self.messages else datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "messages": self.messages,
        }
        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории: {e}")

    def _load(self):
        """Загружает историю с диска."""
        try:
            with open(self._file_path, encoding="utf-8") as f:
                data = json.load(f)
            self.messages = data.get("messages", [])
            logger.info(f"Загружена история сессии {self.session_id}: {len(self.messages)} сообщений.")
        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
            self.messages = []


# ─────────────────────────────────────────────────────────────
# Основной класс RAGEngine
# ─────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Движок RAG для научных PDF-архивов в области нефтегазовой инженерии.

    Использование:
        engine = RAGEngine()
        result = engine.query("Как рассчитать скин-фактор скважины?")
        print(result["answer"])
        print(result["sources"])
    """

    def __init__(
        self,
        model_name: str = config.OLLAMA_MODEL,
        embedding_model: str = config.EMBEDDING_MODEL,
    ) -> None:
        """
        Инициализирует движок: загружает эмбеддинг-модель и подключается к ChromaDB.
        """
        logger.info("Инициализация RAGEngine...")

        # 1. Загрузка модели эмбеддингов (используется та же, что при индексации)
        logger.info(f"Загрузка модели эмбеддингов: {embedding_model}")
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info("Модель эмбеддингов загружена.")
        except Exception as e:
            logger.critical(f"Не удалось загрузить модель эмбеддингов: {e}")
            raise

        # 2. Подключение к ChromaDB (должна быть предварительно заполнена через ingest.py)
        logger.info(f"Подключение к ChromaDB: {config.CHROMA_PERSIST_DIR}")
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=str(config.CHROMA_PERSIST_DIR),
            )
            self.collection = self.chroma_client.get_collection(
                name=config.CHROMA_COLLECTION_NAME
            )
            doc_count = self.collection.count()
            logger.info(f"Коллекция загружена. Документов: {doc_count}")
            if doc_count == 0:
                logger.warning(
                    "Коллекция пуста! Сначала запустите индексацию: python ingest.py"
                )
        except Exception as e:
            logger.error(f"Ошибка подключения к ChromaDB: {e}")
            raise

        # 3. Инициализация LLM-провайдера
        self.provider = LLMProvider.from_config()
        self.llm_model = self.provider.model  # для обратной совместимости
        logger.info(
            f"RAGEngine готов. Провайдер: {self.provider.provider_name}, "
            f"модель: {self.provider.model}"
        )

    # ─────────────────────────────────────────────────────────
    # Поиск релевантных чанков
    # ─────────────────────────────────────────────────────────

    def retrieve(
        self,
        question: str,
        top_k: int = config.DEFAULT_TOP_K,
    ) -> list[dict]:
        """
        Выполняет семантический поиск по ChromaDB.

        Возвращает список словарей:
            {"text": str, "metadata": dict, "distance": float}
        """
        # Добавляем обязательный префикс для multilingual-e5 при запросе
        query_text = f"query: {question}"

        try:
            query_embedding = self.embedding_model.encode(
                query_text,
                normalize_embeddings=config.NORMALIZE_EMBEDDINGS,
            ).tolist()
        except Exception as e:
            logger.error(f"Ошибка генерации эмбеддинга запроса: {e}")
            raise

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Ошибка поиска в ChromaDB: {e}")
            raise

        # Разворачиваем результаты (ChromaDB возвращает вложенные списки)
        chunks = []
        if results and results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                })

        logger.info(f"Найдено релевантных чанков: {len(chunks)} для вопроса: '{question[:80]}...'")
        return chunks

    # ─────────────────────────────────────────────────────────
    # Формирование контекста для LLM
    # ─────────────────────────────────────────────────────────

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Формирует строку контекста из найденных чанков с метаданными.
        Каждый чанк снабжён заголовком с источником.
        """
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk["metadata"]
            file_name = meta.get("file_name", "Неизвестный файл")
            page_num = meta.get("page_num", "?")
            lang = meta.get("language", "?")
            header = f"[{i}] [Источник: {file_name}, стр. {page_num}, язык: {lang}]"
            context_parts.append(f"{header}\n{chunk['text']}")

        return "\n\n---\n\n".join(context_parts)

    # ─────────────────────────────────────────────────────────
    # Генерация ответа через Ollama HTTP API
    # ─────────────────────────────────────────────────────────

    def generate_answer(
        self,
        question: str,
        context: str,
        chat_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Вызывает Ollama HTTP API для генерации ответа на основе контекста.

        Аргументы:
            question: Вопрос пользователя.
            context: Текстовый контекст из релевантных чанков.
            chat_history: Список предыдущих сообщений [{"role": ..., "content": ...}].

        Возвращает: строку с ответом модели.
        """
        # Формируем пользовательский промпт с контекстом
        user_prompt = (
            f"Фрагменты из научных документов (каждый помечен номером [N]):\n\n{context}\n\n"
            f"---\n\nВопрос: {question}\n\n"
            f"Ответь, используя ТОЛЬКО предоставленный контекст. "
            f"Ссылайся на источники по номеру: [1], [2] и т.д. "
            f"В конце ответа перечисли использованные источники."
        )

        # Собираем историю сообщений
        messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        if chat_history:
            # Добавляем не более 6 последних сообщений истории
            messages.extend(chat_history[-6:])
        messages.append({"role": "user", "content": user_prompt})

        logger.debug(
            f"Запрос к {self.provider.provider_name}/{self.provider.model}, "
            f"сообщений={len(messages)}"
        )
        return self.provider.chat(messages)

    # ─────────────────────────────────────────────────────────
    # Публичный метод: полный цикл RAG
    # ─────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_k: int = config.DEFAULT_TOP_K,
        memory: Optional["ConversationMemory"] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> dict:
        """
        Выполняет полный цикл RAG: поиск -> генерация -> форматирование.

        Аргументы:
            question: Вопрос пользователя.
            top_k: Количество извлекаемых чанков.
            memory: Объект ConversationMemory (предпочтительно).
            chat_history: Список сообщений [{role, content}] (устаревший параметр, для обратной совместимости).

        Возвращает словарь:
            {
                "answer": str,
                "sources": list[dict],   # с полем snippet и index
                "chunks": list[dict],
                "context": str,
            }
        """
        logger.info(f"Запрос: '{question[:100]}'")

        # Шаг 1: Семантический поиск
        try:
            chunks = self.retrieve(question, top_k=top_k)
        except Exception as e:
            return {"answer": f"Ошибка поиска по базе знаний: {e}", "sources": [], "chunks": [], "context": ""}

        if not chunks:
            return {
                "answer": (
                    "В базе знаний не найдено релевантных документов для данного вопроса. "
                    "Убедитесь, что архив проиндексирован (python ingest.py)."
                ),
                "sources": [], "chunks": [], "context": "",
            }

        # Шаг 2: Формирование контекста
        context = self._build_context(chunks)

        # Шаг 3: Получение истории для LLM
        if memory is not None:
            history_for_llm = memory.get_llm_messages()
        else:
            history_for_llm = chat_history or []

        # Шаг 4: Генерация ответа
        answer = self.generate_answer(question, context, chat_history=history_for_llm)

        # Шаг 5: Форматирование источников с snippets
        sources = _format_sources(chunks)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": chunks,
            "context": context,
        }

    def get_collection_stats(self) -> dict:
        """
        Возвращает статистику коллекции ChromaDB и информацию о провайдере.
        """
        try:
            count = self.collection.count()
            provider_info = self.provider.get_info()
            return {
                "collection_name": config.CHROMA_COLLECTION_NAME,
                "document_count": count,
                "persist_dir": str(config.CHROMA_PERSIST_DIR),
                "embedding_model": config.EMBEDDING_MODEL,
                "llm_provider": provider_info["provider"],
                "llm_model": provider_info["model"],
                "llm_description": provider_info["description"],
                "llm_api_key_set": provider_info["api_key_set"],
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}


# ─────────────────────────────────────────────────────────────
# Быстрый тест из командной строки
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Тест RAG-движка из командной строки")
    parser.add_argument("question", nargs="?", help="Вопрос для RAG-системы")
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    parser.add_argument("--stats", action="store_true", help="Показать статистику коллекции")
    args = parser.parse_args()

    engine = RAGEngine()

    if args.stats:
        stats = engine.get_collection_stats()
        print("\n=== Статистика коллекции ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print()

    if args.question:
        result = engine.query(args.question, top_k=args.top_k)
        print("\n=== ОТВЕТ ===")
        print(result["answer"])
        print("\n=== ИСТОЧНИКИ ===")
        for src in result["sources"]:
            print(f"  • {src['file_name']}, стр. {src['page_num']} [{src['language']}]")
    elif not args.stats:
        parser.print_help()
