"""
check_cross_language.py — проверка кросс-языкового поиска.

Два независимых от LLM шага:
  1. --stats        Сколько чанков каждого языка лежит в индексе (ChromaDB).
                    Если англоязычных чанков 0 — балансировать нечего, дело
                    в индексации, а не в поиске.
  2. <вопрос>       Прогоняет ТОЛЬКО retrieve() (без генерации ответа, Ollama
                    не нужна) и показывает язык каждого попавшего в выдачу чанка.

Примеры:
    python check_cross_language.py --stats
    python check_cross_language.py "Как рассчитать скин-фактор скважины?"
    python check_cross_language.py --top-k 7 "методы захоронения CO2"
"""

import argparse
from collections import Counter

import chromadb

import config


def index_language_stats() -> None:
    """Считает распределение языков по всем чанкам коллекции."""
    client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
    collection = client.get_collection(name=config.CHROMA_COLLECTION_NAME)

    total = collection.count()
    # Тянем только метаданные (без документов и эмбеддингов — быстро)
    data = collection.get(include=["metadatas"])
    langs = Counter(m.get("language", "unknown") for m in data["metadatas"])
    files_by_lang: dict[str, set] = {}
    for m in data["metadatas"]:
        files_by_lang.setdefault(m.get("language", "unknown"), set()).add(
            m.get("file_name", "?")
        )

    print(f"\n=== Языки в индексе (коллекция '{config.CHROMA_COLLECTION_NAME}') ===")
    print(f"Всего чанков: {total}\n")
    for lang, n in langs.most_common():
        print(f"  {lang:8} {n:6} чанков   из {len(files_by_lang[lang])} файлов")
    if langs.get("en", 0) == 0:
        print("\n⚠️  Англоязычных чанков НЕТ в индексе — балансировать нечего.")
        print("    Проверьте, что английские документы лежат в archive/ и "
              "проиндексированы (python ingest.py).")
    print()


def retrieval_check(question: str, top_k: int) -> None:
    """Прогоняет только поиск и печатает язык каждого чанка выдачи."""
    from rag_engine import RAGEngine

    engine = RAGEngine()
    chunks = engine.retrieve(question, top_k=top_k)

    print(f"\n=== Выдача retrieve() для запроса ===\n  «{question}»\n")
    dist = Counter(c["metadata"].get("language", "unknown") for c in chunks)
    print(f"Распределение языков в топ-{top_k}: {dict(dist)}\n")
    for i, c in enumerate(chunks, 1):
        meta = c["metadata"]
        print(
            f"  [{i}] [{meta.get('language', '?'):3}] "
            f"dist={c['distance']:.4f}  "
            f"{meta.get('file_name', '?')}, стр. {meta.get('page_num', '?')}"
        )
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Проверка кросс-языкового поиска RAG")
    parser.add_argument("question", nargs="?", help="Вопрос для проверки поиска")
    parser.add_argument("--top-k", type=int, default=config.DEFAULT_TOP_K)
    parser.add_argument("--stats", action="store_true",
                        help="Показать распределение языков в индексе")
    args = parser.parse_args()

    if args.stats:
        index_language_stats()
    if args.question:
        retrieval_check(args.question, args.top_k)
    if not args.stats and not args.question:
        parser.print_help()
