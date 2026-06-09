"""
config.py — Центральная конфигурация RAG-системы.
Поддерживаемые форматы: PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT.
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Пути к директориям
# ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "documents"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
LOG_DIR = BASE_DIR / "logs"

for _dir in [PDF_DIR, CHROMA_PERSIST_DIR, LOG_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Поддерживаемые форматы файлов
# ─────────────────────────────────────────────────────────────
# Центральный список — используется watcher.py и ingest.py.
# Чтобы добавить или убрать формат — правьте только этот список.

SUPPORTED_EXTENSIONS: set[str] = {
    ".pdf",    # Adobe PDF
    ".docx",   # Microsoft Word (современный формат)
    ".doc",    # Microsoft Word (старый формат, требует antiword или LibreOffice)
    ".txt",    # Простой текст
    ".md",     # Markdown
    ".xlsx",   # Microsoft Excel
    ".csv",    # CSV-таблицы
    ".pptx",   # Microsoft PowerPoint
    ".odt",    # LibreOffice Writer
}

# ─────────────────────────────────────────────────────────────
# Параметры нарезки текста (chunking)
# ─────────────────────────────────────────────────────────────

CHUNK_SIZE: int = 512
CHUNK_OVERLAP: int = 64
MIN_CHUNK_LENGTH: int = 50

# ─────────────────────────────────────────────────────────────
# Параметры эмбеддингов
# ─────────────────────────────────────────────────────────────

EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"   # максимальное качество поиска (~2.2 ГБ)
EMBEDDING_BATCH_SIZE: int = 32
NORMALIZE_EMBEDDINGS: bool = True

# ─────────────────────────────────────────────────────────────
# Параметры ChromaDB
# ─────────────────────────────────────────────────────────────

CHROMA_COLLECTION_NAME: str = "petroleum_papers"
CHROMA_BATCH_SIZE: int = 64

# ─────────────────────────────────────────────────────────────
# Параметры LLM-провайдера (единый интерфейс)
# ─────────────────────────────────────────────────────────────
#
# LLM_PROVIDER — выбор провайдера:
#   "ollama"     — локальная Ollama (без ключа, уже установлена)
#   "groq"       — Groq Cloud (бесплатно, нужен ключ с console.groq.com/keys)
#   "deepseek"   — DeepSeek API (платно, очень дёшево; ключ: platform.deepseek.com)
#   "openrouter" — 50+ моделей, есть бесплатные (ключ: openrouter.ai/settings/keys)
#   "lmstudio"   — локальный LM Studio (без ключа, сервер на :1234)
#
# LLM_MODEL — модель для выбранного провайдера:
#   ollama:     qwen2.5:7b | qwen2.5:14b | deepseek-r1:7b | mistral | llama3.2
#   groq:       llama-3.3-70b-versatile | deepseek-r1-distill-llama-70b | gemma2-9b-it
#   deepseek:   deepseek-chat | deepseek-reasoner
#   openrouter: qwen/qwen3-14b:free | deepseek/deepseek-r1:free | google/gemma-3-12b-it:free
#   lmstudio:   local-model (любая загруженная в LM Studio)
#
# LLM_API_KEY — API-ключ (оставьте пустым для ollama и lmstudio)
#   Альтернативно: задайте переменную окружения RAG_GROQ_API_KEY / RAG_DEEPSEEK_API_KEY / RAG_OPENROUTER_API_KEY

LLM_PROVIDER: str = "ollama"          # <-- меняйте здесь
LLM_MODEL:    str = "qwen3.5:latest"  # <-- и здесь (используем уже установленную модель)
LLM_API_KEY:  str = ""                # <-- ключ для облачных провайдеров

# Параметры генерации (применяются ко всем провайдерам)
OLLAMA_OPTIONS: dict = {
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 1024,
    "repeat_penalty": 1.1,
}

# Таймаут запроса к LLM (секунды)
OLLAMA_TIMEOUT: int = 120

# Устаревшие параметры (оставлены для обратной совместимости)
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_API_URL: str = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL: str = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_MODEL: str = LLM_MODEL
OLLAMA_FALLBACK_MODEL: str = "llama3"

# ─────────────────────────────────────────────────────────────
# Параметры поиска (retrieval)
# ─────────────────────────────────────────────────────────────

DEFAULT_TOP_K: int = 7
MAX_CONTEXT_CHUNKS: int = 8

# Кросс-языковая балансировка выдачи (RU/EN).
# Модель multilingual-e5 даёт лёгкий перекос в пользу языка запроса: при малом
# top_k чанки на языке вопроса вытесняют релевантные источники на другом языке.
# Чтобы этого избежать, поиск идёт в два этапа: сначала достаётся широкий пул
# кандидатов (RETRIEVAL_FETCH_K), затем в финальную выдачу гарантированно
# попадает минимум MIN_CHUNKS_PER_LANGUAGE чанков каждого присутствующего языка,
# а оставшиеся места заполняются по лучшему семантическому скору.
CROSS_LANGUAGE_BALANCE: bool = True   # включить балансировку по языку
RETRIEVAL_FETCH_K: int = 40           # размер пула кандидатов до балансировки
MIN_CHUNKS_PER_LANGUAGE: int = 2      # гарантированный минимум чанков на язык
# Языки, которым гарантируется представление в выдаче. Чанки прочих категорий
# (langdetect: 'other' для таблиц/формул/смешанного текста, 'unknown') брони не
# получают и попадают в выдачу только по семантическому скору (добор).
BALANCED_LANGUAGES: tuple = ("ru", "en")

# ─────────────────────────────────────────────────────────────
# Параметры Gradio UI
# ─────────────────────────────────────────────────────────────

UI_HOST: str = "127.0.0.1"
UI_PORT: int = 7860
UI_TITLE: str = "Отдел технологий декарбонизации (архив)"
UI_DESCRIPTION: str = (
    "Интеллектуальная поисковая система по научным документам. "
    "Поддерживаемые форматы: PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT. "
    "Поддерживает русский и английский языки."
)

# ─────────────────────────────────────────────────────────────
# Системный промпт для LLM
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT: str = """Ты — экспертный ассистент в области нефтегазовой инженерии и разработки месторождений.
Ты отвечаешь на вопросы, опираясь ИСКЛЮЧИТЕЛЬНО на предоставленные фрагменты научных документов.

Правила:
1. Отвечай на том языке, на котором задан вопрос (русский или английский).
2. Используй ТОЛЬКО информацию из предоставленного контекста. Не придумывай факты.
3. Если контекст не содержит ответа — прямо скажи об этом.
4. Цитируй источники в формате [Файл: <имя>, стр. <номер>].
5. Структурируй ответ: краткий вывод, затем детали с цитатами.
6. Используй профессиональную техническую терминологию.

You are an expert assistant in petroleum and reservoir engineering.
Answer questions based SOLELY on the provided document fragments.

Rules:
1. Reply in the language of the question (Russian or English).
2. Use ONLY information from the provided context. Do not fabricate facts.
3. If the context lacks an answer, say so directly.
4. Cite sources as [File: <name>, p. <number>].
5. Structure: brief conclusion, then details with citations.
6. Use professional technical terminology.
"""

# ─────────────────────────────────────────────────────────────
# Параметры логирования
# ─────────────────────────────────────────────────────────────

LOG_LEVEL: str = "INFO"
LOG_FILE: str = str(LOG_DIR / "rag_system.log")
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# ─────────────────────────────────────────────────────────────
# Интеграция с Obsidian / KMS
# ─────────────────────────────────────────────────────────────

# Каталог KMS жёстко привязан к домашней директории пользователя
# ($HOME/KMS) и НЕ зависит от того, куда установлена папка rag_system.
# Это устраняет баг «двойного KMS» (~/KMS/KMS/archive), возникавший,
# когда rag_system лежит внутри ~/KMS, а путь вычислялся через BASE_DIR.parent.
# При необходимости переопределяется переменной окружения KMS_HOME
# (удобно, если архив лежит на USB-диске по нестандартному пути).
KMS_DIR = Path(os.environ.get("KMS_HOME", str(Path.home() / "KMS")))
KMS_ARCHIVE_DIR = KMS_DIR / "archive"
KMS_VAULT_DIR = KMS_DIR / "notes"

# Строковые псевдонимы — ОБЯЗАТЕЛЬНО абсолютные пути.
# ARCHIVE_DIR используется в watcher.py, OBSIDIAN_VAULT_DIR — в
# rag_query_from_obsidian.py. Если оставить их относительными
# ("KMS/archive"), путь разрешается относительно текущего рабочего каталога
# сервиса (~/KMS/rag_system), и наблюдатель следит не за той папкой.
ARCHIVE_DIR: str = str(KMS_ARCHIVE_DIR)
OBSIDIAN_VAULT_DIR: str = str(KMS_VAULT_DIR)

# ─────────────────────────────────────────────────────────────
# Гибридная таксономия тегов
# ─────────────────────────────────────────────────────────────

TAXONOMY: list[str] = [
    # ── CO2 Геологическое захоронение ──────────────────────────────────────
    "co2_storage", "ccs", "ccus", "co2_injection", "co2_trapping",
    "structural_trapping", "residual_trapping", "solubility_trapping",
    "mineral_trapping", "co2_plume", "co2_migration", "co2_leakage",
    "aquifer_storage", "saline_aquifer", "depleted_reservoir", "mmp",
    "co2_eor", "wellbore_integrity", "cap_rock_integrity",
    "monitoring_verification", "mvv", "risk_assessment_ccs",
    "storage_capacity", "geochemistry", "reactive_transport",
    "mineral_dissolution", "mineral_precipitation",

    # ── Петрофизика ────────────────────────────────────────────────────────
    "petrophysics", "porosity", "permeability", "relative_permeability",
    "capillary_pressure", "wettability", "saturation", "residual_saturation",
    "formation_water", "brine", "core_analysis", "well_logging", "nmr_logging",
    "resistivity", "sonic_log", "density_log", "neutron_log",
    "special_core_analysis", "digital_rock_physics", "pore_network_model",
    "x_ray_ct", "mercury_injection", "klinkenberg_effect", "rock_typing",
    "fluid_substitution", "gassmann",

    # ── Гидродинамическое моделирование ────────────────────────────────────
    "reservoir_simulation", "history_matching", "multiphase_flow",
    "darcy_flow", "material_balance", "pressure_transient_analysis",
    "well_test_analysis", "buildup_test", "drawdown_test", "interference_test",
    "pvt", "eos", "black_oil_model", "compositional_simulation",
    "dual_porosity", "dual_permeability", "upscaling", "numerical_simulation",
    "finite_difference", "finite_element", "streamline_simulation",
    "aquifer_model", "natural_fractures", "hydraulic_fracturing",
    "well_productivity", "inflow_performance", "decline_curve_analysis",

    # ── 3D Геологическое моделирование ─────────────────────────────────────
    "geological_modeling", "3d_model", "structural_model", "facies_model",
    "property_model", "geostatistics", "kriging",
    "sequential_gaussian_simulation", "variogram", "object_based_modeling",
    "multi_point_statistics", "stratigraphic_model", "horizons_faults",
    "grid_building", "depth_conversion", "seismic_interpretation",
    "seismic_attribute", "structural_uncertainty", "volumetrics",
    "stochastic_modeling", "deterministic_modeling", "well_correlation",

    # ── Геомеханика ────────────────────────────────────────────────────────
    "geomechanics", "rock_mechanics", "stress_state", "in_situ_stress",
    "pore_pressure", "effective_stress", "compaction", "subsidence",
    "fault_reactivation", "induced_seismicity", "wellbore_stability",
    "fracture_mechanics", "cap_rock_geomechanics", "reservoir_compaction",
    "coupled_simulation", "mohr_coulomb", "biot_coefficient",
    "mechanical_earth_model", "ucs", "tensile_strength", "young_modulus",
    "poisson_ratio", "creep",

    # ── Разработка месторождений / Общее ───────────────────────────────────
    "reservoir_characterization", "field_development", "production_optimization",
    "eor", "ior", "waterflooding", "gas_injection", "polymer_flooding",
    "surfactant_flooding", "thermal_methods", "steam_injection",
    "tight_reservoir", "shale_reservoir", "carbonate_reservoir",
    "sandstone_reservoir", "offshore", "onshore", "deepwater", "unconventional",
    "uncertainty_analysis", "sensitivity_analysis", "monte_carlo",
    "machine_learning", "deep_learning", "neural_network", "data_driven",
    "proxy_model", "optimization", "well_placement", "drilling", "completion",
    "production_logging", "formation_evaluation",
    "russia", "west_siberia", "volga_ural", "barents_sea",
]

TAXONOMY_AUTO_PREFIX: str = "auto"
WIKILINK_MIN_COMMON_TAGS: int = 2

# ─────────────────────────────────────────────────────────────
# Память диалога
# ─────────────────────────────────────────────────────────────

# Директория для сохранения истории диалогов
HISTORY_DIR = LOG_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# Максимум сообщений в контексте LLM (последние N пар)
MAX_HISTORY_MESSAGES: int = 6

# Максимум сессий для хранения на диске
MAX_SAVED_SESSIONS: int = 50
