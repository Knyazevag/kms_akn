"""
watcher.py — Наблюдатель за папкой KMS/archive.
Автоматически запускает индексацию и создание Obsidian-заметок
при появлении новых файлов поддерживаемых форматов.

Поддерживаемые форматы определяются в config.SUPPORTED_EXTENSIONS.
Зависимости: watchdog>=4.0.0
"""

import argparse
import logging
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

# ─── Путь к директории проекта ───────────────────────────────────────────────
RAG_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RAG_DIR))

import config  # noqa: E402

# ─── Настройка логирования ────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("watcher")

# ─── Watchdog ─────────────────────────────────────────────────────────────────
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
    # PollingObserver опрашивает папку и работает на любой ФС (USB/NTFS)
    # и через символические ссылки, где inotify (обычный Observer) молчит.
    from watchdog.observers.polling import PollingObserver
except ImportError:
    logger.error(
        "Библиотека watchdog не установлена. Выполните: pip install watchdog>=4.0.0"
    )
    sys.exit(1)


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def wait_for_file_stable(path: Path, stable_seconds: float = 2.0, poll: float = 0.5) -> bool:
    """
    Ждёт, пока файл перестанет расти (полностью скопирован).
    Возвращает True, если файл стабилен; False — если файл исчез.
    """
    prev_size = -1
    stable_count = 0
    needed = int(stable_seconds / poll)

    while True:
        if not path.exists():
            return False
        try:
            cur_size = path.stat().st_size
        except OSError:
            return False

        if cur_size == prev_size:
            stable_count += 1
        else:
            stable_count = 0
        prev_size = cur_size

        if stable_count >= needed:
            return True
        time.sleep(poll)


def run_subprocess(cmd: list[str], label: str) -> bool:
    """Запускает подпроцесс; возвращает True при успехе."""
    logger.info("[%s] Запуск: %s", label, " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            cwd=str(RAG_DIR),
            capture_output=True,
            text=True,
            timeout=3600,   # 1 час максимум
        )
        if result.returncode == 0:
            logger.info("[%s] Завершён успешно.", label)
            if result.stdout.strip():
                logger.debug("[%s] stdout:\n%s", label, result.stdout.strip())
        else:
            logger.error(
                "[%s] Завершён с ошибкой (код %d).\nstderr:\n%s",
                label,
                result.returncode,
                result.stderr.strip(),
            )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error("[%s] Превышен тайм-аут (3600 с).", label)
        return False
    except Exception as exc:
        logger.error("[%s] Ошибка запуска: %s", label, exc)
        return False


# ─── Обработчик событий файловой системы ─────────────────────────────────────

class DocumentEventHandler(FileSystemEventHandler):
    """
    Обрабатывает события появления файлов в наблюдаемой директории.
    Фильтрует только форматы из config.SUPPORTED_EXTENSIONS.
    """

    def __init__(self, python_exec: str, processed: set[str]):
        super().__init__()
        self._python = python_exec
        self._processed = processed   # разделяемое множество обработанных путей

    def _handle_file(self, src_path: str) -> None:
        path = Path(src_path).resolve()

        # Фильтрация по расширению — берём список из config
        if path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
            return

        key = str(path)
        if key in self._processed:
            logger.debug("Антидребезг: %s уже обработан, пропускаем.", path.name)
            return

        logger.info(
            "Обнаружен новый файл [%s]: %s",
            path.suffix.upper().lstrip("."),
            path.name
        )

        # Ждём 5 секунд — файл ещё может копироваться
        logger.debug("Ожидание 5 с перед проверкой стабильности...")
        time.sleep(5)

        # Проверяем, что файл полностью записан
        if not wait_for_file_stable(path):
            logger.warning(
                "Файл %s исчез до завершения копирования — пропускаем.", path.name
            )
            return

        logger.info("Файл стабилен (%s). Начинаем обработку.", path.name)

        # Фиксируем как обработанный (ДО запуска, чтобы не задублировать)
        self._processed.add(key)

        # 1) Обновляем RAG-базу
        run_subprocess(
            [self._python, str(RAG_DIR / "ingest.py")],
            label="ingest",
        )

        # 2) Создаём Obsidian-заметку
        run_subprocess(
            [
                self._python,
                str(RAG_DIR / "doc_to_obsidian.py"),
                "--force-single",
                str(path),
            ],
            label="obsidian",
        )

    def on_created(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            self._handle_file(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            self._handle_file(event.dest_path)


# ─── Основной класс наблюдателя ───────────────────────────────────────────────

class DocumentWatcher:
    """Управляет жизненным циклом watchdog-observer с поддержкой USB-дисков."""

    def __init__(self, watch_dir: Path, interval: int = 5):
        self.watch_dir = watch_dir
        self.interval = interval
        self._running = True
        self._observer: Observer | None = None
        self._processed: set[str] = set()
        self._python = sys.executable   # тот же интерпретатор, что запустил watcher

        # Перехватываем SIGTERM для корректного завершения
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    # ── Сигналы ──────────────────────────────────────────────────────────────

    def _handle_sigterm(self, signum, frame):  # noqa: ANN001
        logger.info("Получен сигнал %s — завершение работы...", signal.Signals(signum).name)
        self._running = False
        self._stop_observer()

    # ── Observer ─────────────────────────────────────────────────────────────

    def _start_observer(self) -> bool:
        """Запускает watchdog observer. Возвращает True при успехе."""
        if not self.watch_dir.exists():
            return False

        handler = DocumentEventHandler(
            python_exec=self._python,
            processed=self._processed
        )
        # Опрос вместо inotify: надёжно для USB/NTFS и символических ссылок.
        self._observer = PollingObserver(timeout=self.interval)
        self._observer.schedule(handler, str(self.watch_dir), recursive=True)
        self._observer.start()

        exts = ", ".join(sorted(config.SUPPORTED_EXTENSIONS))
        logger.info("Наблюдение запущено: %s (рекурсивно)", self.watch_dir)
        logger.info("Отслеживаемые форматы: %s", exts)
        return True

    def _stop_observer(self) -> None:
        """Останавливает watchdog observer, если он запущен."""
        if self._observer is not None:
            try:
                if self._observer.is_alive():
                    self._observer.stop()
                    self._observer.join(timeout=10)
            except Exception as exc:
                logger.warning("Ошибка при остановке observer: %s", exc)
            self._observer = None
            logger.info("Observer остановлен.")

    def _observer_alive(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def _catch_up_scan(self) -> None:
        """Догоняющее сканирование при (пере)запуске слежения.

        Обрабатывает файлы, добавленные пока наблюдатель не работал
        (например, на USB-диск при отключённом носителе): запускает полную
        индексацию и создание заметок. Обе операции идемпотентны —
        ingest пропускает уже проиндексированное (по хэшу), а doc_to_obsidian
        не трогает файлы, для которых заметка уже существует.
        """
        logger.info("Догоняющее сканирование каталога %s ...", self.watch_dir)
        # 1) Индексация в ChromaDB — идемпотентна (дедуп по хэшу).
        run_subprocess(
            [self._python, str(RAG_DIR / "ingest.py")],
            label="catch-up ingest",
        )
        # 2) Заметки — ТОЛЬКО для файлов без существующей заметки.
        #    Имя заметки зависит от заголовка, который выдаёт LLM, поэтому
        #    запуск полного doc_to_obsidian повторно плодил бы дубли. Сверяем
        #    по полю source_file во фронтматтере уже созданных заметок.
        try:
            vault = Path(config.KMS_VAULT_DIR)
            noted: set[str] = set()
            for md in vault.glob("*.md"):
                # фронтматтер целиком: source_file может быть за первыми 2000
                # символами при раздутых списках тегов (иначе — ложные дубли)
                head = md.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'^source_file:\s*"?(.+?)"?\s*$', head, re.MULTILINE)
                if m:
                    noted.add(m.group(1).strip())
            new_files = [
                p for p in self.watch_dir.rglob("*")
                if p.is_file()
                and p.suffix.lower() in config.SUPPORTED_EXTENSIONS
                and p.name not in noted
            ]
            if not new_files:
                logger.info("Догоняющее сканирование: новых файлов без заметок нет.")
                return
            logger.info(
                "Догоняющее сканирование: создаю заметки для %d новых файлов.",
                len(new_files),
            )
            for p in new_files:
                run_subprocess(
                    [self._python, str(RAG_DIR / "doc_to_obsidian.py"),
                     "--force-single", str(p)],
                    label=f"catch-up note: {p.name}",
                )
        except Exception as exc:
            logger.warning("Догоняющее сканирование (заметки): %s", exc)

    # ── Главный цикл ─────────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("DocumentWatcher запущен. Целевая директория: %s", self.watch_dir)

        if self._start_observer():
            self._catch_up_scan()
        else:
            logger.warning(
                "Директория %s недоступна (возможно USB не подключён). "
                "Ожидание появления директории каждые %d с...",
                self.watch_dir,
                self.interval * 6,
            )

        while self._running:
            time.sleep(self.interval)

            if not self._running:
                break

            if self._observer_alive():
                if not self.watch_dir.exists():
                    logger.warning(
                        "Директория %s стала недоступна (USB отключён?). "
                        "Останавливаем observer.",
                        self.watch_dir,
                    )
                    self._stop_observer()
            else:
                if not hasattr(self, "_retry_ticks"):
                    self._retry_ticks = 0

                self._retry_ticks += 1
                ticks_needed = max(1, 30 // self.interval)

                if self._retry_ticks >= ticks_needed:
                    self._retry_ticks = 0
                    if self.watch_dir.exists():
                        logger.info(
                            "Директория %s снова доступна — перезапускаем observer.",
                            self.watch_dir
                        )
                        if self._start_observer():
                            self._catch_up_scan()
                    else:
                        logger.warning(
                            "Директория %s всё ещё недоступна (ожидание USB)...",
                            self.watch_dir,
                        )

        self._stop_observer()
        logger.info("DocumentWatcher завершён.")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    exts = ", ".join(sorted(config.SUPPORTED_EXTENSIONS))
    parser = argparse.ArgumentParser(
        description=(
            "Наблюдатель за папкой архива документов. "
            f"Автоматически обрабатывает: {exts}"
        ),
    )
    parser.add_argument(
        "--watch-dir",
        type=Path,
        default=Path(config.ARCHIVE_DIR),
        help=(
            f"Путь для мониторинга (default: {config.ARCHIVE_DIR!r}). "
            "Поддерживаются символические ссылки (USB-диск)."
        ),
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Интервал проверки состояния observer в секундах (default: 5).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    watch_dir = args.watch_dir
    if not watch_dir.is_absolute():
        watch_dir = RAG_DIR / watch_dir
    watch_dir = watch_dir.expanduser()

    logger.info(
        "Параметры запуска: watch_dir=%s, interval=%d с",
        watch_dir,
        args.interval,
    )

    watcher = DocumentWatcher(watch_dir=watch_dir, interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()
