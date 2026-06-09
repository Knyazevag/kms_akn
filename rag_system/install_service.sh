#!/usr/bin/env bash
# install_service.sh — Установка rag-watcher как пользовательского systemd-сервиса.
#
# Использование:
#   chmod +x install_service.sh
#   ./install_service.sh
#
# Что делает скрипт:
#   1. Определяет абсолютный путь к директории rag_system
#   2. Определяет имя текущего пользователя
#   3. Подставляет {{USER}} и {{RAG_DIR}} в rag-watcher.service
#   4. Копирует .service в ~/.config/systemd/user/
#   5. Перезагружает демон, включает и запускает сервис
#   6. Выводит статус

set -euo pipefail

# ─── Цвета для вывода ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── 1. Пути и пользователь ──────────────────────────────────────────────────

# Директория, в которой лежит этот скрипт (= директория rag_system)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAG_DIR="${SCRIPT_DIR}"

# Текущий пользователь (работает и при sudo, и без)
CURRENT_USER="${SUDO_USER:-$(id -un)}"

info "Директория RAG-системы : ${RAG_DIR}"
info "Пользователь           : ${CURRENT_USER}"

# ─── 2. Проверки ─────────────────────────────────────────────────────────────

SERVICE_TEMPLATE="${RAG_DIR}/rag-watcher.service"
if [[ ! -f "${SERVICE_TEMPLATE}" ]]; then
    error "Файл шаблона не найден: ${SERVICE_TEMPLATE}"
    exit 1
fi

VENV_PYTHON="${RAG_DIR}/.venv/bin/python"
if [[ ! -f "${VENV_PYTHON}" ]]; then
    warn "Виртуальное окружение не найдено: ${VENV_PYTHON}"
    warn "Убедитесь, что .venv создано перед запуском сервиса."
    warn "Команда: python3 -m venv ${RAG_DIR}/.venv && ${RAG_DIR}/.venv/bin/pip install -r ${RAG_DIR}/requirements.txt"
fi

WATCHER_PY="${RAG_DIR}/watcher.py"
if [[ ! -f "${WATCHER_PY}" ]]; then
    error "Файл watcher.py не найден: ${WATCHER_PY}"
    exit 1
fi

# ─── 3. Подстановка переменных в шаблон ──────────────────────────────────────

# Целевая директория systemd пользовательских сервисов
SYSTEMD_USER_DIR="/home/${CURRENT_USER}/.config/systemd/user"
mkdir -p "${SYSTEMD_USER_DIR}"

DEST_SERVICE="${SYSTEMD_USER_DIR}/rag-watcher.service"

# Создаём итоговый .service с подстановкой {{USER}} и {{RAG_DIR}}
sed \
    -e "s|{{USER}}|${CURRENT_USER}|g" \
    -e "s|{{RAG_DIR}}|${RAG_DIR}|g" \
    "${SERVICE_TEMPLATE}" > "${DEST_SERVICE}"

success "Service-файл записан: ${DEST_SERVICE}"

# ─── 4. Активация сервиса ─────────────────────────────────────────────────────

# Все systemctl --user команды нужно выполнять от имени целевого пользователя
run_as_user() {
    if [[ "${CURRENT_USER}" == "$(id -un)" ]]; then
        # Уже нужный пользователь
        systemctl --user "$@"
    else
        # Запущено через sudo — используем su
        su -l "${CURRENT_USER}" -s /bin/bash -c "systemctl --user $*"
    fi
}

info "Перезагрузка systemd daemon..."
run_as_user daemon-reload
success "daemon-reload выполнен."

info "Включение сервиса (enable)..."
run_as_user enable rag-watcher
success "Сервис включён (запускается при входе пользователя)."

info "Запуск сервиса (start)..."
run_as_user start rag-watcher
success "Сервис запущен."

# ─── 5. Статус ───────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Статус сервиса rag-watcher${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
run_as_user status rag-watcher --no-pager || true

echo ""
echo -e "${GREEN}Установка завершена!${NC}"
echo ""
echo "Полезные команды:"
echo "  Просмотр логов : journalctl --user -u rag-watcher -f"
echo "  Остановить     : systemctl --user stop rag-watcher"
echo "  Перезапустить  : systemctl --user restart rag-watcher"
echo "  Отключить      : systemctl --user disable rag-watcher"
echo ""
echo "Файл сервиса    : ${DEST_SERVICE}"
echo "Лог RAG-системы : ${RAG_DIR}/logs/rag_system.log"
