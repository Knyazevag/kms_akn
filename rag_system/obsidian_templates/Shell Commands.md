# Настройка Shell Commands для RAG

## Установка плагина
1. Obsidian → Settings → Community plugins → Browse
2. Найти "Shell Commands" → Install → Enable

## Команды для настройки

### Команда 1: Задать вопрос RAG
- **Name:** "Задать вопрос RAG"
- **Shell command:**
  ```
  cd {{RAG_DIR}} && source .venv/bin/activate && python rag_query_from_obsidian.py "{{! Ask question}}" --note "{{title}}" --vault-dir "{{VAULT_DIR}}"
  ```
- **Hotkey:** Ctrl+Shift+R

### Команда 2: Проиндексировать новые PDF
- **Name:** "Обновить RAG-индекс"
- **Shell command:**
  ```
  cd {{RAG_DIR}} && source .venv/bin/activate && python ingest.py
  ```
- **Hotkey:** Ctrl+Shift+I

### Команда 3: Обновить заметки Obsidian
- **Name:** "Обновить заметки из PDF"
- **Shell command:**
  ```
  cd {{RAG_DIR}} && source .venv/bin/activate && python pdf_to_obsidian.py
  ```
- **Hotkey:** Ctrl+Shift+O

## Переменные для подстановки
Замените в командах:
- `{{RAG_DIR}}` → полный путь к папке rag_system (например: `/home/username/rag_system`)
- `{{VAULT_DIR}}` → полный путь к KMS/notes (например: `/home/username/KMS/notes`)

## Примечания
- `{{! Ask question}}` — встроенная переменная Shell Commands, вызывает диалог ввода текста
- `{{title}}` — встроенная переменная, подставляет имя текущего открытого файла без расширения
- Убедитесь, что виртуальное окружение `.venv` создано в папке `{{RAG_DIR}}`
- На Windows замените `source .venv/bin/activate` на `.venv\Scripts\activate`
