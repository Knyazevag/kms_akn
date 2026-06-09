"""
llm_provider.py — Единый интерфейс для работы с LLM-провайдерами.

Поддерживаемые провайдеры:
  - ollama    : локальная Ollama (http://localhost:11434), без API-ключа
  - groq      : cloud API, OpenAI-совместимый, бесплатный тариф
  - deepseek  : cloud API, OpenAI-совместимый, очень дёшево
  - openrouter: агрегатор 50+ моделей, OpenAI-совместимый
  - lmstudio  : локальный LM Studio (http://localhost:1234), без API-ключа

Настройка в config.py:
    LLM_PROVIDER = "ollama"          # имя провайдера
    LLM_MODEL    = "qwen2.5:7b"     # модель для этого провайдера
    LLM_API_KEY  = ""               # API-ключ (пусто для локальных)

Переключение без перезапуска:
    provider = LLMProvider.from_config()
    provider.switch(provider_name="groq", model="llama-3.3-70b-versatile")
"""

import logging
import os
from typing import Optional

import requests

import config

logger = logging.getLogger("llm_provider")


# ─────────────────────────────────────────────────────────────
# Конфигурация провайдеров
# ─────────────────────────────────────────────────────────────

PROVIDER_CONFIGS: dict[str, dict] = {
    "ollama": {
        "base_url":    "http://localhost:11434",
        "chat_path":   "/api/chat",
        "tags_path":   "/api/tags",
        "needs_key":   False,
        "openai_compat": False,
        "description": "Локальная Ollama (без API-ключа)",
        "default_model": "qwen2.5:7b",
        "example_models": [
            "qwen2.5:7b", "qwen2.5:14b", "deepseek-r1:7b",
            "mistral", "llama3.2", "gemma3:12b", "phi4:14b",
        ],
    },
    "groq": {
        "base_url":    "https://api.groq.com/openai",
        "chat_path":   "/v1/chat/completions",
        "tags_path":   "/v1/models",
        "needs_key":   True,
        "openai_compat": True,
        "description": "Groq Cloud (бесплатно: 14 400 req/день)",
        "default_model": "llama-3.3-70b-versatile",
        "example_models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "deepseek-r1-distill-llama-70b",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ],
        "get_key_url": "https://console.groq.com/keys",
    },
    "deepseek": {
        "base_url":    "https://api.deepseek.com",
        "chat_path":   "/v1/chat/completions",
        "tags_path":   "/v1/models",
        "needs_key":   True,
        "openai_compat": True,
        "description": "DeepSeek API ($0.07/1M токенов входа)",
        "default_model": "deepseek-chat",
        "example_models": [
            "deepseek-chat",
            "deepseek-reasoner",
        ],
        "get_key_url": "https://platform.deepseek.com/api_keys",
    },
    "openrouter": {
        "base_url":    "https://openrouter.ai/api",
        "chat_path":   "/v1/chat/completions",
        "tags_path":   "/v1/models",
        "needs_key":   True,
        "openai_compat": True,
        "description": "OpenRouter (50+ моделей, есть бесплатные)",
        "default_model": "qwen/qwen3-14b:free",
        "example_models": [
            "qwen/qwen3-14b:free",
            "deepseek/deepseek-r1:free",
            "google/gemma-3-12b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        ],
        "get_key_url": "https://openrouter.ai/settings/keys",
    },
    "lmstudio": {
        "base_url":    "http://localhost:1234",
        "chat_path":   "/v1/chat/completions",
        "tags_path":   "/v1/models",
        "needs_key":   False,
        "openai_compat": True,
        "description": "LM Studio локальный сервер (без API-ключа)",
        "default_model": "local-model",
        "example_models": ["local-model"],
    },
}


# ─────────────────────────────────────────────────────────────
# Основной класс
# ─────────────────────────────────────────────────────────────

class LLMProvider:
    """
    Единый интерфейс для работы с LLM через любого провайдера.

    Использование:
        provider = LLMProvider.from_config()
        answer = provider.chat(messages=[...])

        # Переключение на другого провайдера:
        provider.switch("groq", model="llama-3.3-70b-versatile", api_key="gsk_...")
    """

    def __init__(
        self,
        provider_name: str,
        model: str,
        api_key: str = "",
        timeout: int = None,
        options: dict = None,
    ) -> None:
        provider_name = provider_name.lower().strip()
        if provider_name not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Неизвестный провайдер: '{provider_name}'. "
                f"Доступные: {list(PROVIDER_CONFIGS.keys())}"
            )

        self.provider_name = provider_name
        self.cfg = PROVIDER_CONFIGS[provider_name]
        self.model = model or self.cfg["default_model"]
        self.api_key = api_key or os.environ.get(f"RAG_{provider_name.upper()}_API_KEY", "")
        self.timeout = timeout or getattr(config, "OLLAMA_TIMEOUT", 120)
        self.options = options or getattr(config, "OLLAMA_OPTIONS", {})

        logger.info(
            f"LLMProvider: провайдер={self.provider_name}, "
            f"модель={self.model}, "
            f"API-ключ={'***' if self.api_key else 'не требуется'}"
        )

    # ── Фабричный метод ───────────────────────────────────────

    @classmethod
    def from_config(cls) -> "LLMProvider":
        """Создаёт провайдер из настроек config.py."""
        return cls(
            provider_name=getattr(config, "LLM_PROVIDER", "ollama"),
            model=getattr(config, "LLM_MODEL", "qwen2.5:7b"),
            api_key=getattr(config, "LLM_API_KEY", ""),
            timeout=getattr(config, "OLLAMA_TIMEOUT", 120),
            options=getattr(config, "OLLAMA_OPTIONS", {}),
        )

    # ── Переключение провайдера без перезапуска ───────────────

    def switch(
        self,
        provider_name: str,
        model: str = "",
        api_key: str = "",
    ) -> None:
        """
        Переключает провайдера и/или модель без перезапуска системы.

        Пример:
            provider.switch("groq", model="llama-3.3-70b-versatile", api_key="gsk_...")
            provider.switch("ollama", model="qwen2.5:14b")
        """
        provider_name = provider_name.lower().strip()
        if provider_name not in PROVIDER_CONFIGS:
            raise ValueError(f"Неизвестный провайдер: '{provider_name}'")

        self.provider_name = provider_name
        self.cfg = PROVIDER_CONFIGS[provider_name]
        self.model = model or self.cfg["default_model"]
        if api_key:
            self.api_key = api_key

        logger.info(
            f"LLMProvider переключён: провайдер={self.provider_name}, модель={self.model}"
        )

    # ── Проверка доступности ──────────────────────────────────

    def check_availability(self) -> dict:
        """
        Проверяет доступность провайдера и возвращает список доступных моделей.

        Возвращает:
            {"ok": bool, "models": list[str], "error": str}
        """
        cfg = self.cfg
        url = cfg["base_url"] + cfg["tags_path"]
        headers = self._build_headers()

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Ollama: {"models": [{"name": "..."}, ...]}
            # OpenAI-compat: {"data": [{"id": "..."}, ...]}
            if cfg["openai_compat"]:
                models = [m["id"] for m in data.get("data", [])]
            else:
                models = [m["name"] for m in data.get("models", [])]

            logger.info(f"{self.provider_name}: доступно {len(models)} моделей")
            return {"ok": True, "models": models, "error": ""}

        except requests.exceptions.ConnectionError:
            msg = f"{self.provider_name}: сервер недоступен ({cfg['base_url']})"
            logger.error(msg)
            return {"ok": False, "models": [], "error": msg}
        except requests.exceptions.HTTPError as e:
            msg = f"{self.provider_name}: HTTP {e.response.status_code}"
            if e.response.status_code == 401:
                msg += " — неверный API-ключ"
            logger.error(msg)
            return {"ok": False, "models": [], "error": msg}
        except Exception as e:
            msg = f"{self.provider_name}: {e}"
            logger.error(msg)
            return {"ok": False, "models": [], "error": msg}

    # ── Основной метод генерации ──────────────────────────────

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
    ) -> str:
        """
        Отправляет список сообщений провайдеру и возвращает текст ответа.

        Аргументы:
            messages: список {"role": "user/assistant/system", "content": "..."}
            model: переопределить модель для этого запроса

        Возвращает: строку с ответом модели.
        """
        use_model = model or self.model
        if self.cfg["openai_compat"]:
            return self._chat_openai(messages, use_model)
        else:
            return self._chat_ollama(messages, use_model)

    # ── Ollama-специфичная реализация ─────────────────────────

    def _chat_ollama(self, messages: list[dict], model: str) -> str:
        url = self.cfg["base_url"] + self.cfg["chat_path"]
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,  # модели с "размышлением" (qwen3/r1) иначе отдают пустой content
            "options": self.options,
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("message", {}).get("content", "")
            if not answer:
                logger.warning("Ollama вернула пустой ответ.")
                return "Не удалось получить ответ от языковой модели."
            logger.info(f"Ollama: ответ {len(answer)} символов.")
            return answer

        except requests.exceptions.ConnectionError:
            return (
                "Ошибка подключения к Ollama. "
                "Убедитесь, что сервер запущен (`ollama serve`)."
            )
        except requests.exceptions.Timeout:
            return f"Таймаут запроса к Ollama (>{self.timeout} сек)."
        except requests.exceptions.HTTPError as e:
            return f"HTTP ошибка Ollama: {e.response.status_code} — {e.response.text[:200]}"
        except Exception as e:
            return f"Непредвиденная ошибка Ollama: {e}"

    # ── OpenAI-совместимая реализация (Groq/DeepSeek/OpenRouter/LMStudio) ──

    def _chat_openai(self, messages: list[dict], model: str) -> str:
        url = self.cfg["base_url"] + self.cfg["chat_path"]
        headers = self._build_headers()

        # Параметры генерации (не все провайдеры поддерживают все опции)
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        # Безопасно добавляем совместимые параметры
        opts = self.options
        if opts.get("temperature") is not None:
            payload["temperature"] = opts["temperature"]
        if opts.get("top_p") is not None:
            payload["top_p"] = opts["top_p"]
        if opts.get("num_predict") is not None:
            payload["max_tokens"] = opts["num_predict"]

        # OpenRouter требует заголовки сайта
        if self.provider_name == "openrouter":
            headers["HTTP-Referer"] = "https://rag-kms-local"
            headers["X-Title"] = "RAG KMS"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            if not answer:
                logger.warning(f"{self.provider_name}: пустой ответ.")
                return "Не удалось получить ответ от языковой модели."
            logger.info(f"{self.provider_name}: ответ {len(answer)} символов.")
            return answer

        except requests.exceptions.ConnectionError:
            return (
                f"Ошибка подключения к {self.provider_name} "
                f"({self.cfg['base_url']}). Проверьте интернет."
            )
        except requests.exceptions.Timeout:
            return f"Таймаут запроса к {self.provider_name} (>{self.timeout} сек)."
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            text = e.response.text[:300]
            if code == 401:
                return (
                    f"Ошибка авторизации {self.provider_name} (401). "
                    f"Проверьте API-ключ в config.py (LLM_API_KEY)."
                )
            if code == 429:
                return (
                    f"Превышен лимит запросов {self.provider_name} (429). "
                    f"Подождите или переключитесь на другого провайдера."
                )
            return f"HTTP ошибка {self.provider_name}: {code} — {text}"
        except (KeyError, IndexError):
            return f"Неожиданный формат ответа от {self.provider_name}."
        except Exception as e:
            return f"Непредвиденная ошибка {self.provider_name}: {e}"

    # ── Вспомогательные методы ────────────────────────────────

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_info(self) -> dict:
        """Возвращает информацию о текущем провайдере."""
        return {
            "provider": self.provider_name,
            "model": self.model,
            "description": self.cfg["description"],
            "base_url": self.cfg["base_url"],
            "needs_api_key": self.cfg["needs_key"],
            "api_key_set": bool(self.api_key),
            "example_models": self.cfg.get("example_models", []),
        }

    @staticmethod
    def list_providers() -> dict:
        """Возвращает список всех поддерживаемых провайдеров."""
        return {
            name: {
                "description": cfg["description"],
                "needs_key": cfg["needs_key"],
                "default_model": cfg["default_model"],
                "example_models": cfg.get("example_models", []),
                "get_key_url": cfg.get("get_key_url", ""),
            }
            for name, cfg in PROVIDER_CONFIGS.items()
        }
