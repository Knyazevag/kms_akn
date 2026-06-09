#!/usr/bin/env python3
"""
rag_query_from_obsidian.py — RAG-запрос из заметок Obsidian.

Использование:
    python rag_query_from_obsidian.py "Вопрос" [--note "Имя заметки"] [--vault-dir /path] [--top-k 5] [--append]

Примеры:
    python rag_query_from_obsidian.py "Какие механизмы ловушки CO2 описаны в Sleipner?"
    python rag_query_from_obsidian.py "Механизмы ловушки CO2" --note "RAG-запрос 2024-01-15"
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Импорт RAGEngine ────────────────────────────────────────────────────────
# Добавляем папку rag_system в sys.path, чтобы импорт работал независимо
# от того, откуда запущен скрипт.
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))

try:
    from rag_engine import RAGEngine
except ImportError as exc:
    print(f"[ERROR] Не удалось импортировать RAGEngine: {exc}", file=sys.stderr)
    print("Убедитесь, что rag_engine.py находится в той же папке, что и этот скрипт.", file=sys.stderr)
    sys.exit(1)

try:
    import config
except ImportError:
    config = None  # config необязателен — значения можно передать через аргументы

# ── Логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Вспомогательные функции ─────────────────────────────────────────────────

def _default_vault_dir() -> str:
    """Возвращает путь к vault из config или пустую строку."""
    if config and hasattr(config, "OBSIDIAN_VAULT_DIR"):
        return str(config.OBSIDIAN_VAULT_DIR)
    return ""


def _find_note_file(vault_dir: str, note_name: str) -> Path:
    """
    Ищет файл заметки в vault_dir.
    Поддерживает имя без расширения или с расширением .md.
    Выбрасывает FileNotFoundError, если файл не найден.
    """
    vault = Path(vault_dir)
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault не найден: {vault_dir}")

    # Нормализуем имя
    note_stem = note_name.removesuffix(".md")

    # Прямое совпадение
    candidate = vault / f"{note_stem}.md"
    if candidate.exists():
        return candidate

    # Рекурсивный поиск по всем подпапкам
    matches = list(vault.rglob(f"{note_stem}.md"))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"Заметка '{note_name}.md' не найдена в vault: {vault_dir}"
    )


def _replace_section(content: str, header: str, new_body: str) -> str:
    """
    Заменяет тело секции с заголовком `header` (например '## Ответ RAG')
    на `new_body`. Секция считается завершённой при следующем заголовке ##
    или конце файла.
    """
    # Паттерн: заголовок секции + всё до следующего ## или EOF
    pattern = re.compile(
        r"(^" + re.escape(header) + r"\s*\n)"   # сам заголовок
        r"(.*?)"                                  # тело секции (ленивое)
        r"(?=^##\s|\Z)",                          # до следующего ## или EOF
        re.MULTILINE | re.DOTALL,
    )

    replacement = r"\g<1>" + new_body.rstrip("\n") + "\n\n"
    new_content, count = pattern.subn(replacement, content)

    if count == 0:
        # Секция не найдена — добавляем в конец
        log.warning("Секция '%s' не найдена в заметке, добавляем в конец.", header)
        new_content = content.rstrip("\n") + f"\n\n{header}\n\n{new_body.rstrip()}\n"

    return new_content


def _format_sources_md(sources: list[dict]) -> str:
    """
    Форматирует список источников в нумерованный markdown-список.

    Ожидаемые поля в каждом источнике (словаре):
        - filename / source / file  — имя файла
        - page / page_number        — номер страницы (опционально)
        - language / lang           — язык (опционально)
    """
    if not sources:
        return "*Источники не найдены.*\n"

    lines = []
    for i, src in enumerate(sources, start=1):
        # Извлекаем имя файла из разных возможных ключей
        filename = (
            src.get("filename")
            or src.get("source")
            or src.get("file")
            or "неизвестный источник"
        )
        filename = Path(filename).name  # оставляем только basename

        # Номер страницы
        page = src.get("page") or src.get("page_number")
        page_str = f" — стр. {page}" if page else ""

        # Язык
        lang = src.get("language") or src.get("lang") or ""
        lang_str = f" [{lang}]" if lang else ""

        lines.append(f"{i}. {filename}{page_str}{lang_str}")

    return "\n".join(lines) + "\n"


def _format_answer_md(answer: str, model: str, top_k: int) -> str:
    """Оборачивает ответ LLM в markdown с метаданными."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"{answer.strip()}\n\n"
        f"*Модель: {model} | top-k: {top_k} | {ts}*\n"
    )


def _update_processed_line(content: str) -> str:
    """Обновляет строку '*Запрос обработан: —*' на текущую дату-время."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_line = f"*Запрос обработан: {ts}*"
    # Заменяем строку вида "*Запрос обработан: ...*"
    updated = re.sub(
        r"\*Запрос обработан:.*?\*",
        new_line,
        content,
    )
    return updated


# ── Основная логика ─────────────────────────────────────────────────────────

def run_rag_query(
    question: str,
    top_k: int = 5,
) -> dict:
    """
    Инициализирует RAGEngine и выполняет запрос.
    Возвращает словарь с ключами: answer, sources, model.
    """
    log.info("Инициализация RAGEngine...")
    try:
        engine = RAGEngine()
    except Exception as exc:
        raise RuntimeError(f"Не удалось инициализировать RAGEngine: {exc}") from exc

    log.info("Выполняется запрос: %s", question[:80])
    try:
        result = engine.query(question, top_k=top_k)
    except Exception as exc:
        raise RuntimeError(f"Ошибка при выполнении RAG-запроса: {exc}") from exc

    # Нормализуем формат ответа — RAGEngine может возвращать разные структуры
    if isinstance(result, dict):
        answer = result.get("answer") or result.get("response") or str(result)
        sources = result.get("sources") or result.get("contexts") or []
        model = result.get("model") or getattr(engine, "model_name", "unknown")
    else:
        # Если вернулась строка
        answer = str(result)
        sources = []
        model = getattr(engine, "model_name", "unknown")

    return {"answer": answer, "sources": sources, "model": model}


def write_to_note(
    note_path: Path,
    answer: str,
    sources: list[dict],
    model: str,
    top_k: int,
    append: bool = False,
) -> None:
    """Вставляет ответ и источники в заметку Obsidian."""
    content = note_path.read_text(encoding="utf-8")

    answer_md = _format_answer_md(answer, model, top_k)
    sources_md = _format_sources_md(sources)

    if append:
        # Режим --append: добавляем блок в конец файла
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = (
            f"\n---\n"
            f"## Ответ RAG ({ts})\n\n"
            f"{answer_md}\n"
            f"## Источники ({ts})\n\n"
            f"{sources_md}"
        )
        content = content.rstrip("\n") + "\n" + block
    else:
        # Режим по умолчанию: заменяем секции
        content = _replace_section(content, "## Ответ RAG", answer_md)
        content = _replace_section(content, "## Источники", sources_md)
        content = _update_processed_line(content)

    note_path.write_text(content, encoding="utf-8")
    log.info("Заметка обновлена: %s", note_path)


def print_result(question: str, answer: str, sources: list[dict], model: str, top_k: int) -> None:
    """Выводит результат в stdout в читаемом формате."""
    separator = "─" * 60
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{separator}")
    print(f"  RAG-ОТВЕТ")
    print(f"{separator}")
    print(f"\n📌 Вопрос:\n  {question}\n")
    print(f"💬 Ответ:\n{answer}\n")
    print(f"  Модель: {model} | top-k: {top_k} | {ts}")

    if sources:
        print(f"\n📚 Источники:")
        for i, src in enumerate(sources, start=1):
            filename = (
                src.get("filename") or src.get("source") or src.get("file") or "?"
            )
            filename = Path(filename).name
            page = src.get("page") or src.get("page_number")
            page_str = f", стр. {page}" if page else ""
            lang = src.get("language") or src.get("lang") or ""
            lang_str = f" [{lang}]" if lang else ""
            print(f"  {i}. {filename}{page_str}{lang_str}")

    print(f"\n{separator}\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG-запрос из заметок Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "question",
        help="Вопрос для RAG-системы",
    )
    parser.add_argument(
        "--note",
        metavar="NOTE_NAME",
        default=None,
        help="Имя заметки в Obsidian vault (без .md). "
             "Если указано, ответ будет вставлен в заметку.",
    )
    parser.add_argument(
        "--vault-dir",
        metavar="PATH",
        default=_default_vault_dir(),
        help="Путь к папке vault Obsidian. "
             "По умолчанию берётся из config.OBSIDIAN_VAULT_DIR.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        metavar="K",
        help="Количество релевантных фрагментов для передачи в LLM (default: 5).",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Добавить ответ в конец заметки, не заменяя существующие секции.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ── Выполняем RAG-запрос ─────────────────────────────────────────────────
    try:
        result = run_rag_query(args.question, top_k=args.top_k)
    except RuntimeError as exc:
        log.error("%s", exc)
        sys.exit(1)

    answer = result["answer"]
    sources = result["sources"]
    model = result["model"]

    # ── Обновляем заметку или выводим в stdout ───────────────────────────────
    if args.note:
        if not args.vault_dir:
            log.error(
                "Не указан --vault-dir и config.OBSIDIAN_VAULT_DIR не задан. "
                "Укажите путь к vault явно."
            )
            sys.exit(1)

        try:
            note_path = _find_note_file(args.vault_dir, args.note)
        except FileNotFoundError as exc:
            log.error("%s", exc)
            sys.exit(1)

        write_to_note(
            note_path=note_path,
            answer=answer,
            sources=sources,
            model=model,
            top_k=args.top_k,
            append=args.append,
        )
        print(f"✓ Ответ записан в заметку: {note_path}")
    else:
        print_result(args.question, answer, sources, model, args.top_k)


if __name__ == "__main__":
    main()
