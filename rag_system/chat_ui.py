"""
chat_ui.py — Gradio чат-интерфейс для RAG-системы научных PDF-архивов.

Возможности:
  - Текстовый ввод вопроса с поддержкой Enter.
  - Отображение ответа + список источников (файл, страница).
  - Сохранение истории чата для контекстных вопросов.
  - Кнопка "Очистить историю".
  - Информационная панель со статистикой базы знаний.

Запуск:
  python chat_ui.py
  Откройте браузер: http://127.0.0.1:7860
"""

import os

# Чат-интерфейс по умолчанию использует CPU для встраивания запросов.
# Встраивание одного короткого вопроса на CPU мгновенно, зато вся видеопамять
# GPU остаётся под языковую модель (Ollama) — это важно на картах с 8 ГБ VRAM.
# Пакетная индексация (ingest.py) при этом по-прежнему использует GPU.
# Чтобы принудительно отдать чату GPU: CUDA_VISIBLE_DEVICES=0 python chat_ui.py
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import logging
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import gradio as gr

import config
from rag_engine import RAGEngine, ConversationMemory

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
logger = logging.getLogger("chat_ui")


# ─────────────────────────────────────────────────────────────
# Инициализация движка RAG (однократно при запуске)
# ─────────────────────────────────────────────────────────────

logger.info("Запуск Gradio UI, инициализация RAGEngine...")

try:
    engine = RAGEngine()
    ENGINE_ERROR = None
    logger.info("RAGEngine успешно инициализирован.")
except Exception as e:
    engine = None
    ENGINE_ERROR = str(e)
    logger.error(f"Не удалось инициализировать RAGEngine: {e}")

# Инициализация памяти диалога
memory = ConversationMemory() if engine is not None else None


# ─────────────────────────────────────────────────────────────
# Вспомогательные функции UI
# ─────────────────────────────────────────────────────────────

def format_sources_markdown(sources: list[dict]) -> str:
    """Форматирует список источников с фрагментами текста."""
    if not sources:
        return "_Источники не найдены._"

    lines = ["**Источники:**\n"]
    for src in sources:
        lang_label = {"ru": "рус.", "en": "англ."}.get(src.get("language", ""), src.get("language", ""))
        file_name = src.get("file_name", "Неизвестный файл")
        page_num = src.get("page_num", "?")
        idx = src.get("index", "?")
        snippet = src.get("snippet", "")

        lines.append(f"**[{idx}]** `{file_name}` — стр. **{page_num}** ({lang_label})")
        if snippet:
            lines.append(f"> _{snippet}_")
        lines.append("")  # пустая строка между источниками

    return "\n".join(lines)


def get_stats_text() -> str:
    """
    Возвращает текст со статистикой базы знаний для отображения в UI.
    """
    if engine is None:
        return f"⚠️ Движок не загружен: {ENGINE_ERROR}"

    try:
        stats = engine.get_collection_stats()
        return (
            f"📚 Документов в базе: **{stats.get('document_count', '?')}**  \n"
            f"🤖 Провайдер: `{stats.get('llm_provider', '?')}` — `{stats.get('llm_model', '?')}`  \n"
            f"🔍 Эмбеддинги: `{stats.get('embedding_model', '?')}`  \n"
            f"🔑 API-ключ: {'✅ задан' if stats.get('llm_api_key_set') else '— (локальный провайдер)'}"
        )
    except Exception as e:
        return f"Ошибка получения статистики: {e}"


# ─────────────────────────────────────────────────────────────
# Обслуживание базы: индексация новых файлов и формирование заметок
# ─────────────────────────────────────────────────────────────

RAG_DIR = Path(__file__).resolve().parent
_PCT_RE = re.compile(r"(\d+)%\|")          # процент из tqdm-вывода скриптов
_maint_lock = threading.Lock()             # не запускать две операции разом


def _stream_script_progress(script_name: str, label: str):
    """
    Запускает скрипт обслуживания (ingest.py / doc_to_obsidian.py) как подпроцесс
    и стримит проценты выполнения, вытаскивая их из tqdm-вывода. Генератор —
    Gradio обновляет статус-компонент на каждый yield.
    """
    if not _maint_lock.acquire(blocking=False):
        yield "⚠️ Дождитесь окончания текущей операции обслуживания."
        return
    try:
        yield f"⏳ {label}: запуск…"
        try:
            proc = subprocess.Popen(
                [sys.executable, str(RAG_DIR / script_name)],
                cwd=str(RAG_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:                       # noqa: BLE001
            yield f"❌ {label}: не удалось запустить — {exc}"
            return

        # tqdm обновляет строку через '\r', поэтому читаем посимвольно и режем
        # по '\r'/'\n', выбирая последний процент.
        last_pct = -1
        buf = ""
        while True:
            ch = proc.stdout.read(1)
            if ch == "":
                break
            if ch in "\r\n":
                m = _PCT_RE.search(buf)
                if m:
                    pct = int(m.group(1))
                    if pct != last_pct:
                        last_pct = pct
                        yield f"⏳ {label}: **{pct}%**"
                buf = ""
            else:
                buf += ch
        proc.wait()

        if proc.returncode == 0:
            yield f"✅ {label}: завершено (100%)."
        else:
            yield f"❌ {label}: ошибка (код {proc.returncode}). Подробности в логах."
    finally:
        _maint_lock.release()


def run_index_ui():
    """Индексация вновь добавленных файлов архива (ingest.py инкрементален)."""
    yield from _stream_script_progress("ingest.py", "Индексация новых файлов")


def run_notes_ui():
    """Формирование Obsidian-заметок (doc_to_obsidian.py пропускает готовые)."""
    yield from _stream_script_progress("doc_to_obsidian.py", "Формирование заметок")


def run_prune_ui():
    """
    Синхронизация удалений: убирает из базы и заметок данные файлов, удалённых из
    архива (`ingest.py --prune-only --prune-notes`). Операция быстрая и без tqdm,
    поэтому читаем вывод целиком и показываем итоговые счётчики.
    """
    if not _maint_lock.acquire(blocking=False):
        yield "⚠️ Дождитесь окончания текущей операции обслуживания."
        return
    try:
        yield "⏳ Синхронизация удалений: выполняется…"
        try:
            proc = subprocess.Popen(
                [sys.executable, str(RAG_DIR / "ingest.py"),
                 "--prune-only", "--prune-notes"],
                cwd=str(RAG_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:                       # noqa: BLE001
            yield f"❌ Синхронизация удалений: не удалось запустить — {exc}"
            return
        out = proc.stdout.read()
        proc.wait()

        if "Prune ОТМЕНЁН" in out:
            yield ("⚠️ Синхронизация отменена: архив пуст или недоступен — "
                   "проверьте, примонтирован ли диск (индекс не тронут).")
        elif proc.returncode != 0:
            yield f"❌ Синхронизация удалений: ошибка (код {proc.returncode}). См. логи."
        else:
            m = re.search(r"Чанков: (\d+), файлов: (\d+), заметок: (\d+)", out)
            if m:
                yield (f"✅ Синхронизация удалений: убрано чанков {m.group(1)} "
                       f"(файлов {m.group(2)}), заметок {m.group(3)}.")
            else:
                yield "✅ Синхронизация удалений завершена."
    finally:
        _maint_lock.release()


# ─────────────────────────────────────────────────────────────
# Основная функция обработки сообщений
# ─────────────────────────────────────────────────────────────

# Соответствие подписей переключателя кодам языка для движка
LANGUAGE_CHOICES = {
    "🌐 Авто (язык вопроса)": "auto",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en",
}


def chat(
    user_message: str,
    history: list[list[Optional[str]]],
    top_k: int,
    response_language: str,
) -> tuple[list[list[Optional[str]]], str, str]:
    """
    Обрабатывает сообщение пользователя и возвращает обновлённые данные UI.

    Аргументы:
        user_message: Вопрос пользователя.
        history: История чата в формате Gradio [[user_msg, bot_msg], ...].
        top_k: Количество извлекаемых чанков.
        response_language: Подпись выбранного языка ответа (из LANGUAGE_CHOICES).

    Возвращает:
        (обновлённая история, текст источников, пустая строка ввода)
    """
    lang_code = LANGUAGE_CHOICES.get(response_language, "auto")
    global memory

    if engine is None:
        error_msg = f"[X] RAG-движок не инициализирован: {ENGINE_ERROR}"
        history.append([user_message, error_msg])
        return history, "_Движок недоступен._", ""

    user_message = user_message.strip()
    if not user_message:
        return history, "", ""

    logger.info(f"Вопрос пользователя: '{user_message[:100]}'")

    # Добавляем вопрос в память
    if memory is not None:
        memory.add_user_message(user_message)

    # Выполняем RAG-запрос
    try:
        result = engine.query(
            question=user_message,
            top_k=top_k,
            memory=memory,
            response_language=lang_code,
        )
        answer = result["answer"]
        sources = result["sources"]
        sources_text = format_sources_markdown(sources)

        # Сохраняем ответ в память
        if memory is not None:
            memory.add_assistant_message(answer, sources)

    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        answer = f"[X] Ошибка при обработке запроса: {e}"
        sources_text = "_Источники недоступны._"

    # Добавляем обмен в историю Gradio
    history.append([user_message, answer])

    return history, sources_text, ""


def clear_history() -> tuple[list, str, str, object]:
    """
    Очищает историю чата.
    """
    global memory
    logger.info("История чата очищена.")
    if memory is not None:
        memory.clear()
        memory = ConversationMemory()  # новая сессия
    return [], "_Задайте вопрос для начала диалога._", "", gr.File(visible=False)


def export_history():
    """Экспортирует историю диалога в Markdown-файл."""
    if memory is None or not memory.messages:
        return None

    import tempfile
    md_content = memory.export_markdown()
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False,
        prefix=f"rag_dialog_{memory.session_id}_",
        encoding="utf-8"
    )
    tmp.write(md_content)
    tmp.close()
    logger.info(f"История экспортирована: {tmp.name}")
    return tmp.name


# ─────────────────────────────────────────────────────────────
# Построение Gradio UI
# ─────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    """
    Конструирует интерфейс Gradio.
    """
    # Цветовая схема (нефтегазовая тематика: тёмные тона + янтарный акцент)
    theme = gr.themes.Base(
        primary_hue="amber",
        secondary_hue="stone",
        neutral_hue="zinc",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
    ).set(
        body_background_fill="#1a1a2e",
        body_text_color="#e0e0e0",
        block_background_fill="#16213e",
        block_border_color="#0f3460",
        button_primary_background_fill="#f5a623",
        button_primary_text_color="#1a1a2e",
        button_secondary_background_fill="#0f3460",
        button_secondary_text_color="#e0e0e0",
    )

    with gr.Blocks(
        title=config.UI_TITLE,
        theme=theme,
        css="""
        /* Стили чата */
        .chatbot-wrap { height: 520px; overflow-y: auto; }
        .message.user { background: #0f3460 !important; }
        .message.bot  { background: #1a1a2e !important; border-left: 3px solid #f5a623; }
        /* Информационные панели: чёрный текст на светлом фоне (иначе сливается) */
        #sources-panel, #stats-panel {
            background: #ffffff !important;
            color: #111111 !important;
            border: 1px solid #c5d5e8;
            border-radius: 8px;
            padding: 12px;
        }
        #sources-panel *, #stats-panel * { color: #111111 !important; }
        #stats-panel { font-size: 0.85em; }
        /* Поле ввода вопроса: тёмный текст на светлом фоне (иначе сливается) */
        textarea, input[type="text"], .gr-textbox textarea {
            color: #111111 !important;
            background-color: #ffffff !important;
            -webkit-text-fill-color: #111111 !important;
        }
        textarea::placeholder, input[type="text"]::placeholder {
            color: #777777 !important;
            -webkit-text-fill-color: #777777 !important;
        }
        """,
    ) as demo:

        # ── Заголовок ──────────────────────────────────────────
        gr.Markdown(
            f"""
# 🛢️ {config.UI_TITLE}
{config.UI_DESCRIPTION}

> **Инструкция:** Введите вопрос на русском или английском. Система найдёт
> релевантные фрагменты из загруженных PDF и сформирует ответ с указанием источников.
            """
        )

        with gr.Row():

            # ── Левая колонка: чат ──────────────────────────────
            with gr.Column(scale=2):

                chatbot = gr.Chatbot(
                    label="Диалог",
                    elem_classes=["chatbot-wrap"],
                    bubble_full_width=False,
                    show_copy_button=True,
                    height=520,
                    placeholder="*Задайте вопрос по документам архива...*",
                )

                with gr.Row():
                    user_input = gr.Textbox(
                        placeholder="Введите вопрос и нажмите Enter или кнопку '➤'...",
                        label="Вопрос",
                        scale=5,
                        lines=2,
                        max_lines=5,
                        show_label=True,
                        container=True,
                        autofocus=True,
                    )
                    send_btn = gr.Button(
                        "➤ Отправить",
                        variant="primary",
                        scale=1,
                        min_width=110,
                    )

                with gr.Row():
                    clear_btn = gr.Button(
                        "🗑️ Очистить историю",
                        variant="secondary",
                        scale=1,
                    )
                    export_btn = gr.Button(
                        "💾 Экспорт диалога",
                        variant="secondary",
                        scale=1,
                    )
                    top_k_slider = gr.Slider(
                        minimum=1,
                        maximum=config.MAX_CONTEXT_CHUNKS,
                        value=config.DEFAULT_TOP_K,
                        step=1,
                        label="Число источников (top-k)",
                        scale=3,
                    )

                with gr.Row():
                    language_selector = gr.Radio(
                        choices=list(LANGUAGE_CHOICES.keys()),
                        value=list(LANGUAGE_CHOICES.keys())[0],
                        label="Язык ответа",
                        info="«Авто» — отвечать на языке вопроса; иначе ответ принудительно на выбранном языке.",
                        scale=1,
                    )

            # ── Правая колонка: источники и статистика ──────────
            with gr.Column(scale=1):

                gr.Markdown("### 📑 Источники")
                sources_output = gr.Markdown(
                    value="_Задайте вопрос для отображения источников._",
                    elem_id="sources-panel",
                )
                export_file = gr.File(
                    label="Скачать диалог (.md)",
                    visible=False,
                )

                gr.Markdown("---")
                gr.Markdown("### ℹ️ База знаний")
                stats_display = gr.Markdown(
                    value=get_stats_text(),
                    elem_id="stats-panel",
                )

                refresh_stats_btn = gr.Button(
                    "🔄 Обновить статистику",
                    variant="secondary",
                    size="sm",
                )

                gr.Markdown("---")
                with gr.Accordion("🗂️ Обслуживание базы знаний", open=False):
                    gr.Markdown(
                        "Проиндексируйте вновь добавленные файлы архива, затем "
                        "сформируйте по ним заметки Obsidian."
                    )
                    index_btn = gr.Button(
                        "🔄 Индексировать новые файлы",
                        variant="primary",
                        size="sm",
                    )
                    index_status = gr.Markdown(
                        "_Готово к индексации._",
                        elem_id="maint-status",
                    )
                    notes_btn = gr.Button(
                        "📝 Сформировать заметки",
                        variant="secondary",
                        size="sm",
                        interactive=False,
                    )
                    notes_status = gr.Markdown(
                        "_Станет доступно после индексации._",
                        elem_id="maint-status",
                    )
                    prune_btn = gr.Button(
                        "🧹 Синхронизировать удаления",
                        variant="secondary",
                        size="sm",
                    )
                    prune_status = gr.Markdown(
                        "_Убирает из базы и заметок файлы, удалённые из архива._",
                        elem_id="maint-status",
                    )

        # ── Примеры вопросов ────────────────────────────────────
        gr.Markdown("### 💡 Примеры вопросов")
        gr.Examples(
            examples=[
                ["Как рассчитывается скин-фактор скважины?"],
                ["Какие методы повышения нефтеотдачи пласта наиболее эффективны?"],
                ["Объясните уравнение Дарси для фильтрации флюида в пористой среде"],
                ["What are the main challenges in deepwater reservoir development?"],
                ["How does hydraulic fracturing affect reservoir permeability?"],
                ["Каков механизм работы штангового глубинного насоса?"],
            ],
            inputs=user_input,
            label="Кликните на вопрос, чтобы вставить его в поле ввода",
        )

        # ── Нижняя строка ────────────────────────────────────────
        gr.Markdown(
            "_Система работает полностью локально. Данные не покидают ваш компьютер._",
            elem_id="footer",
        )

        # ── Привязка событий ─────────────────────────────────────

        # Отправка по кнопке
        send_btn.click(
            fn=chat,
            inputs=[user_input, chatbot, top_k_slider, language_selector],
            outputs=[chatbot, sources_output, user_input],
            queue=True,
        )

        # Отправка по Enter (submit в Textbox)
        user_input.submit(
            fn=chat,
            inputs=[user_input, chatbot, top_k_slider, language_selector],
            outputs=[chatbot, sources_output, user_input],
            queue=True,
        )

        # Очистка истории
        clear_btn.click(
            fn=clear_history,
            inputs=[],
            outputs=[chatbot, sources_output, user_input, export_file],
            queue=False,
        )

        # Экспорт истории
        export_btn.click(
            fn=export_history,
            inputs=[],
            outputs=[export_file],
            queue=False,
        ).then(
            fn=lambda f: gr.File(visible=f is not None, value=f),
            inputs=[export_file],
            outputs=[export_file],
        )

        # Обновление статистики
        refresh_stats_btn.click(
            fn=get_stats_text,
            inputs=[],
            outputs=[stats_display],
            queue=False,
        )

        # Индексация новых файлов (стрим процентов) → после завершения
        # активируем кнопку заметок и обновляем статистику базы.
        index_btn.click(
            fn=run_index_ui,
            inputs=[],
            outputs=[index_status],
            queue=True,
        ).then(
            fn=lambda: (gr.update(interactive=True),
                        "_Индексация завершена — можно формировать заметки._"),
            inputs=[],
            outputs=[notes_btn, notes_status],
            queue=False,
        ).then(
            fn=get_stats_text,
            inputs=[],
            outputs=[stats_display],
            queue=False,
        )

        # Формирование заметок (стрим процентов)
        notes_btn.click(
            fn=run_notes_ui,
            inputs=[],
            outputs=[notes_status],
            queue=True,
        )

        # Синхронизация удалений → обновляем статистику базы
        prune_btn.click(
            fn=run_prune_ui,
            inputs=[],
            outputs=[prune_status],
            queue=True,
        ).then(
            fn=get_stats_text,
            inputs=[],
            outputs=[stats_display],
            queue=False,
        )

    return demo


# ─────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Запуск Gradio UI для RAG-системы")
    parser.add_argument(
        "--host",
        default=config.UI_HOST,
        help=f"Хост для запуска (по умолчанию: {config.UI_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.UI_PORT,
        help=f"Порт для запуска (по умолчанию: {config.UI_PORT})",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Создать публичную ссылку через Gradio Share (tunnel)",
    )
    args = parser.parse_args()

    demo = build_ui()

    logger.info(f"Запуск Gradio на http://{args.host}:{args.port}")
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=False,   # Не открывать браузер автоматически (для сервера)
        quiet=False,
    )
