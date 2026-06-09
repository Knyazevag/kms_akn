"""
ingest.py — Индексация документов в векторную базу ChromaDB.

Поддерживаемые форматы: PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT.
Список форматов управляется через config.SUPPORTED_EXTENSIONS.

Алгоритм:
  1. Рекурсивный обход директории архива.
  2. Определение формата файла и выбор парсера.
  3. Нарезка текста на чанки с перекрытием.
  4. Батчевая генерация эмбеддингов через sentence-transformers.
  5. Сохранение чанков + эмбеддингов + метаданных в ChromaDB.

Запуск:
  python ingest.py [--doc-dir /path/to/docs] [--reset]
"""

import argparse
import hashlib
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import fitz  # PyMuPDF — для PDF
from langdetect import detect, LangDetectException
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import chromadb
from chromadb.config import Settings

import config

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
logger = logging.getLogger("ingest")


# ─────────────────────────────────────────────────────────────
# Парсеры для каждого формата
# ─────────────────────────────────────────────────────────────

def _is_ocrmypdf_available() -> bool:
    """Проверяет, установлен ли ocrmypdf."""
    try:
        result = subprocess.run(
            ["ocrmypdf", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_ocr_on_pdf(path: Path) -> "Path | None":
    """
    Запускает ocrmypdf на скане без текста.
    Создаёт файл <имя>_ocr.pdf рядом с оригиналом.
    Возвращает путь к OCR-версии или None при ошибке.
    """
    ocr_path = path.with_stem(path.stem + "_ocr")
    if ocr_path.exists():
        logger.info(f"OCR: найден кешированный файл '{ocr_path.name}', использую его.")
        return ocr_path

    logger.warning(
        f"PDF '{path.name}' не содержит текстового слоя — скан без OCR. "
        f"Запускаю ocrmypdf (rus+eng)..."
    )
    try:
        result = subprocess.run(
            [
                "ocrmypdf",
                "--language", "rus+eng",
                "--output-type", "pdf",
                "--skip-big",      # пропускать изображения > 4 МПикс (защита от зависания)
                "--optimize", "0", # не оптимизировать — ускоряет работу
                "--quiet",
                str(path),
                str(ocr_path),
            ],
            capture_output=True, text=True, timeout=300  # макс. 5 минут
        )
        if result.returncode == 0 and ocr_path.exists():
            logger.info(f"OCR: успешно создан '{ocr_path.name}'")
            return ocr_path
        else:
            logger.error(
                f"ocrmypdf завершился с ошибкой (код {result.returncode}) "
                f"для '{path.name}': {result.stderr[:300]}"
            )
            return None
    except subprocess.TimeoutExpired:
        logger.error(f"OCR: превышено время ожидания (5 мин) для '{path.name}'")
        return None
    except FileNotFoundError:
        logger.error(
            "ocrmypdf не установлен. Установите: "
            "sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-rus"
        )
        return None


def _pdf_has_text(path: Path, sample_pages: int = 3) -> bool:
    """
    Быстрая проверка: содержит ли PDF текстовый слой.
    Проверяет первые sample_pages страниц.
    Возвращает True, если суммарно найдено >= 50 символов текста.
    """
    try:
        doc = fitz.open(str(path))
        total_chars = 0
        pages_to_check = min(sample_pages, len(doc))
        for i in range(pages_to_check):
            total_chars += len(doc[i].get_text("text").strip())
        doc.close()
        return total_chars >= 50
    except Exception:
        return False


def extract_pdf(path: Path) -> list[dict]:
    """PDF → список {'page_num': int, 'text': str}.

    Автоматически обнаруживает сканы без OCR-слоя и запускает ocrmypdf.
    Если ocrmypdf не установлен — логирует предупреждение и возвращает [].
    """
    pages = []

    # Проверяем наличие текстового слоя
    if not _pdf_has_text(path):
        if _is_ocrmypdf_available():
            ocr_path = _run_ocr_on_pdf(path)
            if ocr_path is not None:
                # Рекурсивно извлекаем текст из OCR-версии
                pages = extract_pdf(ocr_path)
                if pages:
                    logger.info(
                        f"OCR: '{path.name}' — извлечено {len(pages)} страниц "
                        f"после распознавания."
                    )
                return pages
        else:
            logger.warning(
                f"PDF '{path.name}' является сканом без текстового слоя. "
                f"Файл пропущен. Для автоматического OCR установите: "
                f"sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-rus"
            )
            return []

    # Обычный PDF с текстом — стандартное извлечение
    try:
        doc = fitz.open(str(path))
        for page_num, page in enumerate(doc, start=1):
            try:
                text = _clean_text(page.get_text("text"))
                if text:
                    pages.append({"page_num": page_num, "text": text})
            except Exception as e:
                logger.warning(f"Ошибка страницы {page_num} в {path.name}: {e}")
        doc.close()
        logger.info(f"PDF: извлечено {len(pages)} страниц из '{path.name}'")
    except Exception as e:
        logger.error(f"Не удалось открыть PDF '{path}': {e}")
    return pages


def extract_docx(path: Path) -> list[dict]:
    """DOCX → список страниц (разбивка по параграфам, ~500 символов)"""
    try:
        from docx import Document  # python-docx
        doc = Document(str(path))
        full_text = "\n".join(
            p.text for p in doc.paragraphs if p.text.strip()
        )
        # Добавляем текст из таблиц
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    full_text += "\n" + row_text
        return _text_to_pages(full_text, path.name)
    except ImportError:
        logger.error("python-docx не установлен. Выполните: pip install python-docx")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения DOCX '{path}': {e}")
        return []


def extract_doc(path: Path) -> list[dict]:
    """DOC (старый формат Word) → список страниц через LibreOffice или antiword."""
    # Сначала пробуем конвертацию через LibreOffice (надёжнее)
    try:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "txt:Text",
             "--outdir", str(path.parent), str(path)],
            capture_output=True, text=True, timeout=30
        )
        txt_path = path.with_suffix(".txt")
        if txt_path.exists():
            pages = extract_txt(txt_path)
            txt_path.unlink()  # удаляем временный файл
            logger.info(f"DOC: конвертирован через LibreOffice '{path.name}'")
            return pages
    except FileNotFoundError:
        pass  # LibreOffice не установлен, пробуем antiword
    except Exception as e:
        logger.warning(f"LibreOffice не смог конвертировать '{path.name}': {e}")

    # Запасной вариант — antiword
    try:
        result = subprocess.run(
            ["antiword", str(path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"DOC: прочитан через antiword '{path.name}'")
            return _text_to_pages(result.stdout, path.name)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"antiword не смог прочитать '{path.name}': {e}")

    logger.error(
        f"Не удалось прочитать DOC '{path.name}'. "
        "Установите LibreOffice: sudo apt install libreoffice"
    )
    return []


def extract_txt(path: Path) -> list[dict]:
    """TXT или MD → список страниц."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        logger.info(f"TXT/MD: прочитан '{path.name}' ({len(text)} символов)")
        return _text_to_pages(text, path.name)
    except Exception as e:
        logger.error(f"Ошибка чтения TXT '{path}': {e}")
        return []


def extract_xlsx(path: Path) -> list[dict]:
    """XLSX → список страниц (каждый лист — отдельный «блок текста»)."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        all_text = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None and str(c).strip()]
                if cells:
                    rows.append(" | ".join(cells))
            if rows:
                all_text.append(f"[Лист: {sheet_name}]\n" + "\n".join(rows))
        wb.close()
        full_text = "\n\n".join(all_text)
        logger.info(f"XLSX: прочитано {len(wb.sheetnames)} листов из '{path.name}'")
        return _text_to_pages(full_text, path.name)
    except ImportError:
        logger.error("openpyxl не установлен. Выполните: pip install openpyxl")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения XLSX '{path}': {e}")
        return []


def extract_csv(path: Path) -> list[dict]:
    """CSV → список страниц."""
    try:
        import csv
        rows = []
        # Пробуем разные кодировки
        for encoding in ("utf-8", "cp1251", "latin-1"):
            try:
                with open(path, newline="", encoding=encoding, errors="replace") as f:
                    reader = csv.reader(f)
                    rows = [" | ".join(r) for r in reader if any(c.strip() for c in r)]
                break
            except UnicodeDecodeError:
                continue
        full_text = "\n".join(rows)
        logger.info(f"CSV: прочитано {len(rows)} строк из '{path.name}'")
        return _text_to_pages(full_text, path.name)
    except Exception as e:
        logger.error(f"Ошибка чтения CSV '{path}': {e}")
        return []


def extract_pptx(path: Path) -> list[dict]:
    """PPTX → список страниц (каждый слайд — отдельная «страница»)."""
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        pages = []
        for slide_num, slide in enumerate(prs.slides, start=1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text.strip())
            if texts:
                pages.append({
                    "page_num": slide_num,
                    "text": _clean_text("\n".join(texts))
                })
        logger.info(f"PPTX: извлечено {len(pages)} слайдов из '{path.name}'")
        return pages
    except ImportError:
        logger.error("python-pptx не установлен. Выполните: pip install python-pptx")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения PPTX '{path}': {e}")
        return []


def extract_odt(path: Path) -> list[dict]:
    """ODT (LibreOffice Writer) → список страниц."""
    try:
        from odf.opendocument import load
        from odf.text import P
        from odf import teletype
        doc = load(str(path))
        paragraphs = doc.text.getElementsByType(P)
        lines = [teletype.extractText(p) for p in paragraphs]
        full_text = "\n".join(line for line in lines if line.strip())
        logger.info(f"ODT: прочитан '{path.name}' ({len(lines)} параграфов)")
        return _text_to_pages(full_text, path.name)
    except ImportError:
        logger.error("odfpy не установлен. Выполните: pip install odfpy")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения ODT '{path}': {e}")
        return []


# ─────────────────────────────────────────────────────────────
# Диспетчер форматов
# ─────────────────────────────────────────────────────────────

EXTRACTORS = {
    ".pdf":  extract_pdf,
    ".docx": extract_docx,
    ".doc":  extract_doc,
    ".txt":  extract_txt,
    ".md":   extract_txt,
    ".xlsx": extract_xlsx,
    ".csv":  extract_csv,
    ".pptx": extract_pptx,
    ".odt":  extract_odt,
}


def extract_document(path: Path) -> list[dict]:
    """Универсальный экстрактор: выбирает парсер по расширению файла."""
    ext = path.suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        logger.warning(f"Формат '{ext}' не поддерживается: {path.name}")
        return []
    return extractor(path)


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Нормализует пробелы и переносы строк."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _text_to_pages(text: str, filename: str, page_size: int = 2000) -> list[dict]:
    """
    Разбивает длинный текст на «страницы» по ~page_size символов.
    Используется для форматов без нативной нумерации страниц (TXT, DOCX и т.д.).
    Разбивка происходит по границам абзацев, а не посередине слова.
    """
    text = _clean_text(text)
    if not text:
        return []

    pages = []
    page_num = 1
    start = 0

    while start < len(text):
        end = start + page_size
        if end >= len(text):
            chunk = text[start:]
        else:
            # Ищем ближайший перенос строки, чтобы не резать посередине абзаца
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start + page_size // 2:
                end = newline_pos
            chunk = text[start:end]

        chunk = chunk.strip()
        if chunk:
            pages.append({"page_num": page_num, "text": chunk})
            page_num += 1

        start = end

    logger.debug(f"Текст из '{filename}' разбит на {len(pages)} страниц")
    return pages


def make_doc_id(file_name: str, page_num: int, chunk_idx: int) -> str:
    """Создаёт уникальный ID для чанка на основе имени файла и позиции."""
    raw = f"{file_name}::{page_num}::{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def detect_language(text: str) -> str:
    """Определяет язык текста ('ru', 'en', 'unknown')."""
    try:
        lang = detect(text[:500])
        return lang if lang in ("ru", "en") else "other"
    except LangDetectException:
        return "unknown"


def chunk_text(text: str) -> list[str]:
    """
    Нарезает текст на перекрывающиеся чанки.
    Параметры берутся из config.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + config.CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) >= config.MIN_CHUNK_LENGTH:
            chunks.append(chunk)
        start += config.CHUNK_SIZE - config.CHUNK_OVERLAP
    return chunks


# ─────────────────────────────────────────────────────────────
# ChromaDB — инициализация
# ─────────────────────────────────────────────────────────────

def get_collection(reset: bool = False):
    """Инициализирует ChromaDB и возвращает коллекцию."""
    client = chromadb.PersistentClient(
        path=str(config.CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    if reset:
        try:
            client.delete_collection(config.CHROMA_COLLECTION_NAME)
            logger.info("Коллекция ChromaDB сброшена.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "description": "Научные документы (PDF, DOCX, TXT и др.)",
        },
    )
    return collection


# ─────────────────────────────────────────────────────────────
# Основной генератор чанков
# ─────────────────────────────────────────────────────────────

def iter_doc_chunks(doc_dir: Path) -> Generator[dict, None, None]:
    """
    Рекурсивно обходит директорию, обрабатывает все поддерживаемые форматы.
    Для каждого чанка возвращает словарь с текстом и метаданными.
    """
    # Собираем все файлы поддерживаемых форматов
    all_files = []
    for ext in config.SUPPORTED_EXTENSIONS:
        all_files.extend(doc_dir.rglob(f"*{ext}"))
    all_files = sorted(set(all_files))

    logger.info(f"Найдено файлов для индексации: {len(all_files)}")
    if not all_files:
        logger.warning(f"Файлы не найдены в директории: {doc_dir}")
        return

    for file_path in tqdm(all_files, desc="Обработка документов", unit="файл"):
        pages = extract_document(file_path)
        if not pages:
            logger.warning(f"Текст не извлечён из: {file_path.name}")
            continue

        file_ext = file_path.suffix.lower().lstrip(".")

        for page in pages:
            chunks = chunk_text(page["text"])
            for chunk_idx, chunk_text_val in enumerate(chunks):
                lang = detect_language(chunk_text_val)
                # Добавляем префикс для multilingual-e5
                prefixed = f"passage: {chunk_text_val}"
                yield {
                    "id": make_doc_id(file_path.name, page["page_num"], chunk_idx),
                    "text": prefixed,
                    "metadata": {
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "file_type": file_ext,
                        "page_num": page["page_num"],
                        "chunk_idx": chunk_idx,
                        "language": lang,
                        "char_count": len(chunk_text_val),
                    },
                }


# ─────────────────────────────────────────────────────────────
# Основная функция индексации
# ─────────────────────────────────────────────────────────────

def run_ingestion(doc_dir: Path, reset: bool = False) -> None:
    """Запускает полную индексацию документов из директории."""
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("Запуск индексации архива документов")
    logger.info(f"Директория: {doc_dir}")
    logger.info(f"Форматы: {', '.join(sorted(config.SUPPORTED_EXTENSIONS))}")
    logger.info("=" * 60)

    # Модель эмбеддингов
    logger.info(
        f"Загрузка модели эмбеддингов: {config.EMBEDDING_MODEL} "
        f"(device={config.EMBEDDING_DEVICE or 'auto'})"
    )
    model = SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)

    # ChromaDB
    collection = get_collection(reset=reset)
    existing_ids = set(collection.get(include=[])["ids"])
    logger.info(f"Уже проиндексировано чанков: {len(existing_ids)}")

    # Накапливаем батч
    batch_ids, batch_texts, batch_metas = [], [], []
    new_chunks = 0
    skipped = 0

    for chunk in iter_doc_chunks(doc_dir):
        if chunk["id"] in existing_ids:
            skipped += 1
            continue

        batch_ids.append(chunk["id"])
        batch_texts.append(chunk["text"])
        batch_metas.append(chunk["metadata"])

        if len(batch_ids) >= config.CHROMA_BATCH_SIZE:
            _flush_batch(model, collection, batch_ids, batch_texts, batch_metas)
            new_chunks += len(batch_ids)
            batch_ids, batch_texts, batch_metas = [], [], []

    # Остаток
    if batch_ids:
        _flush_batch(model, collection, batch_ids, batch_texts, batch_metas)
        new_chunks += len(batch_ids)

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info(f"Индексация завершена за {elapsed:.1f} сек.")
    logger.info(f"Добавлено новых чанков: {new_chunks}")
    logger.info(f"Пропущено (уже в базе): {skipped}")
    logger.info(f"Всего в базе: {collection.count()}")
    logger.info("=" * 60)


def _flush_batch(model, collection, ids, texts, metas):
    """Генерирует эмбеддинги и записывает батч в ChromaDB."""
    embeddings = model.encode(
        texts,
        batch_size=config.EMBEDDING_BATCH_SIZE,
        normalize_embeddings=config.NORMALIZE_EMBEDDINGS,
        show_progress_bar=False,
    ).tolist()
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metas,
    )


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Индексация документов (PDF, DOCX, TXT и др.) в ChromaDB"
    )
    parser.add_argument(
        "--doc-dir", "--pdf-dir",   # --pdf-dir оставлен для обратной совместимости
        type=Path,
        default=config.KMS_ARCHIVE_DIR,
        help=f"Путь к директории с документами (по умолчанию: {config.KMS_ARCHIVE_DIR})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Полностью сбросить базу ChromaDB перед индексацией",
    )
    args = parser.parse_args()
    run_ingestion(doc_dir=args.doc_dir, reset=args.reset)
