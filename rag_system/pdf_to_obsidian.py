#!/usr/bin/env python3
"""
pdf_to_obsidian.py — Интеграция RAG-системы с Obsidian.

Для каждого PDF из KMS/archive/ (рекурсивно):
  1. Извлекает текст первых 3 страниц через PyMuPDF.
  2. Отправляет текст в Ollama HTTP API для анализа.
  3. Создаёт .md файл в KMS/notes/ с YAML frontmatter.
  4. После обработки всех PDF — второй проход для построения wikilinks.

Запуск:
  python pdf_to_obsidian.py [--pdf-dir PATH] [--vault-dir PATH]
                             [--force] [--dry-run] [--model MODEL]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

# ─── Импорт конфигурации ───────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import config
except ImportError as exc:
    sys.exit(f"[ERROR] Не удалось импортировать config.py: {exc}")

# ─── Зависимости: PyMuPDF ──────────────────────────────────────────────────
try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit(
        "[ERROR] PyMuPDF не установлен. Выполните: pip install pymupdf"
    )

# ─── Константы ────────────────────────────────────────────────────────────
MAX_PAGES: int = 3          # сколько страниц читать из PDF
MAX_RETRIES: int = 2        # попыток запроса к Ollama
MIN_COMMON_TAGS: int = 2    # минимум общих тегов для wikilink
PAGES_TEXT_LIMIT: int = 6000  # лимит символов текста, передаваемого в промпт


# ══════════════════════════════════════════════════════════════════════════════
# Логирование
# ══════════════════════════════════════════════════════════════════════════════

def _setup_logging() -> logging.Logger:
    """Настраивает логгер, пишущий и в файл системы, и в stdout."""
    logger = logging.getLogger("pdf_to_obsidian")
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(
        fmt=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
    )

    # Файловый хендлер — тот же лог, что и у всей системы
    fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Консольный хендлер
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


log = _setup_logging()


# ══════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ══════════════════════════════════════════════════════════════════════════════

def slugify(text: str) -> str:
    """
    Преобразует произвольный текст в безопасное имя файла (slug).

    Пример: "CO2 Storage: a Review" → "co2_storage_a_review"
    """
    # Нормализация Unicode → ASCII
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Заменяем всё кроме букв, цифр и пробелов на пробел
    text = re.sub(r"[^\w\s-]", " ", text)
    # Пробелы и дефисы → _
    text = re.sub(r"[\s\-]+", "_", text).strip("_")
    return text or "untitled"


def normalise_tag(tag: str) -> str:
    """Приводит тег к нижнему регистру, пробелы → подчёркивание."""
    tag = tag.strip().lower()
    tag = re.sub(r"[\s\-]+", "_", tag)
    return tag


def extract_pdf_text(pdf_path: Path, max_pages: int = MAX_PAGES) -> str:
    """
    Извлекает текстовое содержимое первых `max_pages` страниц PDF.
    Возвращает пустую строку при ошибке.
    """
    try:
        doc = fitz.open(str(pdf_path))
        pages_text: list[str] = []
        for page_num in range(min(max_pages, len(doc))):
            page = doc.load_page(page_num)
            pages_text.append(page.get_text("text"))  # type: ignore[arg-type]
        doc.close()
        return "\n".join(pages_text)
    except Exception as exc:
        log.warning("Не удалось извлечь текст из %s: %s", pdf_path.name, exc)
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# Взаимодействие с Ollama
# ══════════════════════════════════════════════════════════════════════════════

def _build_prompt(text: str, taxonomy: list[str]) -> str:
    """Составляет промпт для Ollama."""
    taxonomy_str = ", ".join(taxonomy)
    # Обрезаем текст, чтобы не переполнять контекст
    truncated = text[:PAGES_TEXT_LIMIT]

    return f"""You are a scientific metadata extraction assistant for petroleum engineering papers.
Analyze the following text extracted from the first pages of a scientific PDF.

TAXONOMY OF ALLOWED TAGS (choose ONLY from this list for tags_from_taxonomy):
{taxonomy_str}

If you believe an important concept is NOT covered by the taxonomy, add it to tags_auto
with the prefix "auto/" (e.g. "auto/supercritical_co2"). Keep auto tags minimal.

All tags must be lowercase with spaces replaced by underscores.

Return ONLY a valid JSON object — no markdown, no explanations, no code fences.
Use null (not "null") for missing fields. Use empty arrays [] for missing lists.

Required JSON structure:
{{
  "title": "Article title in original language",
  "authors": ["Author1", "Author2"],
  "year": 2023,
  "journal": "Journal or conference name",
  "doi": "10.xxxx/xxxx or null",
  "keywords": ["keyword1", "keyword2"],
  "tags_from_taxonomy": ["tag1", "tag2", "tag3"],
  "tags_auto": ["auto/new_concept"],
  "summary_ru": "Краткое резюме на русском языке (3-5 предложений).",
  "summary_en": "Brief summary in English (2-3 sentences).",
  "methods": ["method1", "method2"],
  "software": ["PHREEQC", "tNavigator"],
  "key_findings": ["finding1", "finding2", "finding3"]
}}

PDF TEXT:
{truncated}
"""


def call_ollama(
    text: str,
    model: str,
    taxonomy: list[str],
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any] | None:
    """
    Отправляет текст в Ollama /api/generate и возвращает распарсенный JSON.
    При невалидном JSON повторяет до `max_retries` раз.
    Возвращает None если все попытки исчерпаны.
    """
    prompt = _build_prompt(text, taxonomy)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": config.OLLAMA_OPTIONS,
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                config.OLLAMA_API_URL,
                json=payload,
                timeout=config.OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")

            # Попытка найти JSON-объект в ответе (модель иногда добавляет пояснения)
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if not json_match:
                raise ValueError("В ответе Ollama не найден JSON-объект")
            parsed = json.loads(json_match.group())
            return parsed

        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            log.warning(
                "Попытка %d/%d: ошибка запроса к Ollama — %s",
                attempt, max_retries, exc,
            )

    return None


# ══════════════════════════════════════════════════════════════════════════════
# Формирование содержимого заметки
# ══════════════════════════════════════════════════════════════════════════════

EMPTY_META: dict[str, Any] = {
    "title": "",
    "authors": [],
    "year": None,
    "journal": "",
    "doi": None,
    "keywords": [],
    "tags_from_taxonomy": [],
    "tags_auto": [],
    "summary_ru": "",
    "summary_en": "",
    "methods": [],
    "software": [],
    "key_findings": [],
}


def _normalise_metadata(raw: dict[str, Any], pdf_name: str) -> dict[str, Any]:
    """
    Приводит метаданные от Ollama к ожидаемому формату:
    - гарантирует наличие всех ключей
    - нормализует теги
    - подставляет имя PDF как заглушку для title если он пуст
    """
    meta = {**EMPTY_META, **raw}

    # Заглушка для title
    if not meta.get("title"):
        meta["title"] = Path(pdf_name).stem

    # Нормализация тегов
    tax_tags = [normalise_tag(t) for t in (meta.get("tags_from_taxonomy") or [])]
    auto_tags_raw = meta.get("tags_auto") or []
    auto_tags: list[str] = []
    for t in auto_tags_raw:
        t = normalise_tag(t)
        if not t.startswith("auto/"):
            t = "auto/" + t
        auto_tags.append(t)

    meta["tags_from_taxonomy"] = tax_tags
    meta["tags_auto"] = auto_tags

    # Гарантируем списки
    for key in ("authors", "keywords", "methods", "software", "key_findings"):
        if not isinstance(meta.get(key), list):
            meta[key] = [str(meta[key])] if meta.get(key) else []

    return meta


def _all_tags(meta: dict[str, Any]) -> list[str]:
    """Возвращает полный список тегов (taxonomy + auto)."""
    return list(meta["tags_from_taxonomy"]) + list(meta["tags_auto"])


def _yaml_list(items: list[str]) -> str:
    """Форматирует Python-список для YAML inline: [item1, item2]."""
    escaped = [f'"{i}"' for i in items]
    return "[" + ", ".join(escaped) + "]"


def _build_note_content(
    meta: dict[str, Any],
    pdf_filename: str,
    today: str,
) -> str:
    """
    Собирает полный текст Markdown-заметки с YAML frontmatter.
    Раздел «Связанные статьи» пока пустой — заполняется вторым проходом.
    """
    title = meta["title"]
    authors = meta["authors"]
    year = meta.get("year") or "н/д"
    journal = meta.get("journal") or "н/д"
    doi = meta.get("doi") or "н/д"
    summary_ru = meta.get("summary_ru") or ""
    summary_en = meta.get("summary_en") or ""
    methods = meta.get("methods") or []
    software = meta.get("software") or []
    key_findings = meta.get("key_findings") or []
    tags = _all_tags(meta)

    # ── YAML frontmatter ──────────────────────────────────────────────────
    authors_yaml = _yaml_list(authors)
    tags_yaml = _yaml_list(tags)
    doi_yaml = f'"{doi}"'

    frontmatter = f"""---
title: "{title}"
authors: {authors_yaml}
year: {year}
journal: "{journal}"
doi: {doi_yaml}
tags: {tags_yaml}
date_indexed: {today}
source_pdf: "{pdf_filename}"
---"""

    # ── Основное тело ─────────────────────────────────────────────────────
    authors_str = ", ".join(authors) if authors else "н/д"
    methods_str = ", ".join(methods) if methods else "н/д"
    software_str = ", ".join(software) if software else "н/д"

    findings_md = (
        "\n".join(f"- {f}" for f in key_findings)
        if key_findings
        else "- н/д"
    )

    tags_obsidian = " ".join(f"#{t}" for t in tags) if tags else ""

    body = f"""
# {title}

## Метаданные
| Поле | Значение |
|------|----------|
| Авторы | {authors_str} |
| Год | {year} |
| Журнал | {journal} |
| DOI | {doi} |

## Резюме
{summary_ru}

*English summary: {summary_en}*

## Методы и ПО
**Методы:** {methods_str}
**Программное обеспечение:** {software_str}

## Ключевые выводы
{findings_md}

## Теги
{tags_obsidian}

## Связанные статьи
*Будет заполнено автоматически при наличии общих тегов*

---
*Проиндексировано: {today}*
"""
    return frontmatter + "\n" + body


# ══════════════════════════════════════════════════════════════════════════════
# Второй проход: построение wikilinks
# ══════════════════════════════════════════════════════════════════════════════

def _find_related(
    note_data: list[dict[str, Any]],
    min_common: int = MIN_COMMON_TAGS,
) -> dict[str, list[tuple[str, set[str]]]]:
    """
    Для каждой заметки находит другие заметки с >= min_common общими тегами.

    Параметры:
        note_data: список словарей с ключами 'slug', 'title', 'tags'
        min_common: минимальное число общих тегов

    Возвращает:
        dict[slug → list[(другой_title, общие_теги)]]
    """
    relations: dict[str, list[tuple[str, set[str]]]] = {
        nd["slug"]: [] for nd in note_data
    }

    for i, a in enumerate(note_data):
        for b in note_data[i + 1:]:
            common = set(a["tags"]) & set(b["tags"])
            if len(common) >= min_common:
                relations[a["slug"]].append((b["title"], common))
                relations[b["slug"]].append((a["title"], common))

    return relations


RELATED_SECTION_MARKER = "## Связанные статьи"
RELATED_PLACEHOLDER = "*Будет заполнено автоматически при наличии общих тегов*"


def _update_related_section(
    md_path: Path,
    related: list[tuple[str, set[str]]],
    dry_run: bool = False,
) -> None:
    """
    Обновляет раздел «Связанные статьи» в уже записанной заметке.
    """
    if not related:
        return  # нечего добавлять

    content = md_path.read_text(encoding="utf-8")

    lines: list[str] = []
    for title, common_tags in sorted(related, key=lambda x: -len(x[1])):
        tags_str = " ".join(f"#{t}" for t in sorted(common_tags))
        lines.append(
            f"- [[{title}]] ({len(common_tags)} общих тег(а): {tags_str})"
        )
    links_block = "\n".join(lines)

    new_section = (
        f"{RELATED_SECTION_MARKER}\n"
        f"{RELATED_PLACEHOLDER}\n"
        f"{links_block}"
    )

    if RELATED_PLACEHOLDER in content:
        new_content = content.replace(
            f"{RELATED_SECTION_MARKER}\n{RELATED_PLACEHOLDER}",
            new_section,
        )
    else:
        # Секция уже обновлялась — перезаписываем блок целиком
        pattern = re.compile(
            rf"({re.escape(RELATED_SECTION_MARKER)}\n).*?(\n---)",
            re.DOTALL,
        )
        new_content = pattern.sub(
            lambda m: m.group(1) + links_block + "\n" + m.group(2),
            content,
        )

    if dry_run:
        log.info("[DRY-RUN] Обновление раздела связей в: %s", md_path.name)
        return

    md_path.write_text(new_content, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# CLI и основная логика
# ══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация Obsidian-заметок из PDF через Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=config.KMS_ARCHIVE_DIR,
        help="Путь к папке с PDF (default: %(default)s)",
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=config.KMS_VAULT_DIR,
        help="Путь к Obsidian vault (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующие заметки",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать, что будет сделано, без записи файлов",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Модель Ollama (override config.OLLAMA_MODEL)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    pdf_dir: Path = args.pdf_dir
    vault_dir: Path = args.vault_dir
    force: bool = args.force
    dry_run: bool = args.dry_run
    model: str = args.model or config.OLLAMA_MODEL

    log.info("═" * 60)
    log.info("pdf_to_obsidian.py — старт")
    log.info("PDF-директория : %s", pdf_dir)
    log.info("Obsidian vault : %s", vault_dir)
    log.info("Модель Ollama  : %s", model)
    log.info("--force        : %s", force)
    log.info("--dry-run      : %s", dry_run)
    log.info("═" * 60)

    # ── Проверка директорий ───────────────────────────────────────────────
    if not pdf_dir.exists():
        log.error("PDF-директория не найдена: %s", pdf_dir)
        sys.exit(1)

    if not dry_run:
        vault_dir.mkdir(parents=True, exist_ok=True)
        log.info("Vault-директория создана/существует: %s", vault_dir)

    # ── Поиск PDF ─────────────────────────────────────────────────────────
    pdf_files = sorted(pdf_dir.rglob("*.pdf"))
    if not pdf_files:
        log.warning("PDF-файлы не найдены в %s", pdf_dir)
        sys.exit(0)

    log.info("Найдено PDF: %d", len(pdf_files))

    today = date.today().isoformat()
    taxonomy: list[str] = config.TAXONOMY

    # Список данных для второго прохода (wikilinks)
    note_data: list[dict[str, Any]] = []

    # ── Первый проход: создание заметок ───────────────────────────────────
    for pdf_path in tqdm(pdf_files, desc="Обработка PDF", unit="файл"):
        pdf_name = pdf_path.name
        log.info("Обрабатываю: %s", pdf_name)

        # Извлечение текста
        text = extract_pdf_text(pdf_path, max_pages=MAX_PAGES)
        if not text.strip():
            log.warning("Пустой текст в %s — пропуск", pdf_name)
            continue

        # Получение метаданных от Ollama
        raw_meta: dict[str, Any] | None = None
        failed = False

        if dry_run:
            log.info("[DRY-RUN] Пропуск вызова Ollama для %s", pdf_name)
            raw_meta = {}
        else:
            raw_meta = call_ollama(text, model=model, taxonomy=taxonomy)
            if raw_meta is None:
                log.error(
                    "Ollama не вернула валидный JSON для %s — заметка создаётся с пустыми метаданными",
                    pdf_name,
                )
                failed = True
                raw_meta = {}

        meta = _normalise_metadata(raw_meta, pdf_name)

        # Если title всё ещё пуст — используем stem PDF
        if not meta["title"]:
            meta["title"] = Path(pdf_name).stem

        # Slug и путь к заметке
        slug = slugify(meta["title"])
        md_filename = slug + ".md"
        md_path = vault_dir / md_filename

        # Проверка существования
        if md_path.exists() and not force:
            log.info("Заметка уже существует, пропуск: %s", md_filename)
            # Всё равно собираем данные для второго прохода
            existing_content = md_path.read_text(encoding="utf-8")
            # Попытка извлечь теги из frontmatter
            existing_tags = re.findall(r'"([\w/]+)"', existing_content[:1000])
            note_data.append(
                {
                    "slug": slug,
                    "title": meta["title"],
                    "tags": existing_tags,
                    "md_path": md_path,
                }
            )
            continue

        # Сборка содержимого заметки
        note_content = _build_note_content(meta, pdf_name, today)

        if failed:
            # Добавляем метку ручной проверки
            note_content = note_content.replace(
                "# " + meta["title"],
                "# ⚠️ " + meta["title"] + "\n\n> **⚠️ Требует ручной проверки** — Ollama не вернула валидные метаданные.",
            )

        if dry_run:
            log.info("[DRY-RUN] Создание заметки: %s", md_filename)
            print(f"\n{'─'*60}\n[DRY-RUN] {md_filename}\n{'─'*60}")
            print(note_content[:500] + "...\n")
        else:
            md_path.write_text(note_content, encoding="utf-8")
            log.info("Заметка создана: %s", md_filename)

        note_data.append(
            {
                "slug": slug,
                "title": meta["title"],
                "tags": _all_tags(meta),
                "md_path": md_path,
            }
        )

    # ── Второй проход: wikilinks ──────────────────────────────────────────
    log.info("Второй проход: построение wikilinks...")
    relations = _find_related(note_data, min_common=MIN_COMMON_TAGS)

    updated_count = 0
    for nd in tqdm(note_data, desc="Wikilinks", unit="заметка"):
        related = relations.get(nd["slug"], [])
        if not related:
            continue
        md_path: Path = nd["md_path"]
        if not md_path.exists() and not dry_run:
            continue
        _update_related_section(md_path, related, dry_run=dry_run)
        updated_count += 1

    log.info(
        "Готово. Обработано PDF: %d. Заметок обновлено wikilinks: %d.",
        len(note_data),
        updated_count,
    )
    log.info("Vault: %s", vault_dir)


if __name__ == "__main__":
    main()
