# RAG-KMS — Local Knowledge Management System
## Offline Search over a Technical Archive | Russian + English

A local system for searching and generating answers (RAG) over an archive of
scientific and technical documents. It runs inside a secure perimeter: indexing
and embeddings are computed fully offline, while the LLM can be either a local
Ollama instance or cloud APIs (optionally).

The thematic profile of the knowledge base is oil & gas engineering and
geological CO₂ storage, but the system is not tied to a specific domain.

---

## Features

- **Multi-format indexing** — PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT
  (the format list is in `config.SUPPORTED_EXTENSIONS`).
- **Semantic search** by meaning (rather than word matching) in two languages —
  Russian and English — via the `intfloat/multilingual-e5-large` model.
- **Cross-language retrieval** — the same question in RU and EN yields a matching
  set of sources: the `e5` bias toward the query language is compensated by a
  dual-query (translating the question into the other language) plus result balancing.
- **Answer language selector** in the chat — 🌐 Auto / 🇷🇺 Russian / 🇬🇧 English
  (controls the language the answer is written in, independent of the question and sources).
- **Flexible LLM choice** — the unified `llm_provider.py` interface supports 5
  providers: `ollama`, `groq`, `deepseek`, `openrouter`, `lmstudio`.
  Switching is done through `config.py` without changing code.
- **Web interface** built on Gradio, with dialog history and context memory; a
  "Knowledge base maintenance" panel adds **Index new files**, **Generate notes**
  and **Sync deletions** buttons with a live progress %; the notes button
  activates after a successful indexing run.
- **Automatic indexing** of new files via a watcher on the archive folder
  (`watcher.py`), installable as a systemd service.
- **Incremental indexing** — unchanged files are skipped without re-parsing
  (manifest `chroma_db/ingest_manifest.json` keyed by `size:mtime`), so a repeat
  run over a large archive takes seconds rather than hours. On completion a flag
  file `logs/ingest_status.txt` is written.
- **Deletion sync** — removing a file from the archive removes its chunks from the
  index and its Obsidian note (`ingest.py --prune` / UI button; the watcher reacts
  to deletions automatically). Safeguard: if the archive is empty/unavailable (an
  unmounted drive), prune is aborted so the whole index is not wiped.
- **Obsidian integration** — auto-generation of notes with YAML frontmatter,
  taxonomy tags (capped at 15 taxonomy + 5 auto per note) and an IDF-weighted
  wikilink graph (top-15 related notes), plus RAG queries directly from notes.
  Generation is robust: the JSON token budget auto-grows and metadata is sanitized.
- **MCP server** — access to the knowledge base from Claude Code as a set of tools.

---

## System Architecture

```
        Documents (archive/, recursively)
        PDF · DOCX · DOC · TXT · MD · XLSX · CSV · PPTX · ODT
                          │
          ┌───────────────┴────────────────┐
          ▼                                 ▼
   [watcher.py]                       (manual run)
   auto-watcher                              │
          │                                  │
          ▼                                  ▼
   ┌──────────────────────────────────────────────┐
   │  [ingest.py]  parsing → chunking →            │
   │  multilingual-e5-large → ChromaDB (on disk)   │
   └──────────────────────────────────────────────┘
          │                                  │
          │                                  ▼
          │                        [doc_to_obsidian.py]
          │                        → notes in notes/ (Obsidian)
          ▼
   ┌──────────────────────────────────────────────┐
   │  [rag_engine.py]  semantic search +           │
   │  answer generation via [llm_provider.py]      │
   └──────────────────────────────────────────────┘
       │            │              │
       ▼            ▼              ▼
  [chat_ui.py]  [mcp_rag_     [rag_query_from_
   Gradio UI     server.py]    obsidian.py]
                 Claude Code   query from a note
```

### Directory Layout (KMS)

The system is designed around the `~/KMS` structure (overridable via the
`KMS_HOME` environment variable):

```
~/KMS/
├── archive/      # source documents (may be a symlink to a USB drive)
├── notes/        # Obsidian vault (generated notes)
└── rag_system/   # the system code (this directory)
```

> The KMS path is computed from `$HOME`, **not** from the location of
> `rag_system` — so the code can be kept anywhere without breaking the paths to
> the archive and notes (`config.KMS_DIR`, `config.KMS_ARCHIVE_DIR`,
> `config.KMS_VAULT_DIR`).

---

## Components

| File | Purpose |
|---|---|
| `config.py` | Single configuration: paths, formats, chunking, embeddings, LLM, taxonomy, dialog memory |
| `llm_provider.py` | Unified interface to 5 LLM providers (Ollama + 4 OpenAI-compatible) |
| `ingest.py` | Indexing documents of all formats → ChromaDB |
| `rag_engine.py` | Semantic search + answer generation with citations |
| `chat_ui.py` | Gradio web interface (history, context memory) |
| `watcher.py` | Watcher on `archive/`: auto-indexing + auto-notes |
| `mcp_rag_server.py` | MCP server for Claude Code (4 tools) |
| `doc_to_obsidian.py` | Generating Obsidian notes from documents of all formats |
| `pdf_to_obsidian.py` | The same for PDF only (historical predecessor of `doc_to_obsidian.py`) |
| `rag_query_from_obsidian.py` | RAG query that writes the answer into an Obsidian note |
| `check_cross_language.py` | Cross-language retrieval diagnostics: languages in the index (`--stats`) and the language of each retrieved chunk |
| `rag-watcher.service` | systemd unit template for `watcher.py` |
| `install_service.sh` | Installs the watcher as a user systemd service |

---

## Requirements

- **OS:** Linux (tested on Ubuntu 22.04)
- **Python:** 3.10+ (3.12 is used)
- **RAM:** at least 8 GB (16 GB recommended for large archives)
- **GPU (optional):** a CUDA card speeds up embedding generation during indexing
- **LLM:** Ollama (by default) **or** a key for a cloud provider
- **System packages** (for parsing `.doc`):
  ```bash
  sudo apt install libreoffice antiword
  ```

---

## Installation

### 1. Virtual environment and dependencies

```bash
cd ~/KMS/rag_system
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> On the first run, the embedding model `intfloat/multilingual-e5-large` (~2.2 GB)
> will download automatically from Hugging Face.

### 2. LLM provider

**Option A — local Ollama (default, no keys):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve                       # in a separate terminal or as a service
ollama pull qwen2.5:7b             # or another model from config
```

**Option B — a cloud provider** (Groq is free, DeepSeek/OpenRouter are cheap) —
see the [“Choosing an LLM”](#choosing-an-llm) section.

---

## Usage

### Step 1. Documents

Place files into `~/KMS/archive/` (subfolders and symlinks are supported):

```bash
cp ~/articles/*.pdf ~/KMS/archive/
# or an entire archive from an external drive:
ln -s /run/media/$USER/MyDisk/library ~/KMS/archive
```

### Step 2. Indexing

```bash
source .venv/bin/activate

python ingest.py                       # index ~/KMS/archive
python ingest.py --doc-dir /path/docs  # another directory (--pdf-dir is an alias)
python ingest.py --reset               # full reset of the database before indexing
python ingest.py --prune --prune-notes # index + remove data of files deleted from the archive
python ingest.py --prune-only --dry-run --prune-notes  # preview what would be removed (no deletion)
```

A repeat run **does not reindex everything**. Unchanged files are skipped at the
file level without re-parsing — via the manifest `chroma_db/ingest_manifest.json`
(a `size:mtime` fingerprint); only new and modified files are parsed. Chunk-level
deduplication by hash still applies. A no-change run takes seconds; `--reset`
clears both the database and the manifest.

### Step 3. Queries

**Web interface (Gradio):**

```bash
python chat_ui.py                      # http://127.0.0.1:7860
python chat_ui.py --host 0.0.0.0 --port 7860   # access from the local network
```

> By default, the chat computes the query embedding on the CPU, leaving the GPU
> for the LLM (important on cards with 8 GB VRAM). To force the chat to use the
> GPU: `CUDA_VISIBLE_DEVICES=0 python chat_ui.py`.

**Console:**

```bash
python rag_engine.py "How is the well skin factor calculated?"
python rag_engine.py "What is Darcy velocity?" --top-k 8
python rag_engine.py --stats           # collection statistics
```

---

## Automatic Indexing (watcher + systemd)

The watcher monitors `~/KMS/archive/` and, when a file appears/changes, runs
`ingest.py` and `doc_to_obsidian.py`.

**One-off run:**

```bash
python watcher.py                      # watches config.ARCHIVE_DIR
python watcher.py --watch-dir /path --interval 5
```

**Installing as a user systemd service:**

```bash
chmod +x install_service.sh
./install_service.sh
```

The script substitutes the user and paths into `rag-watcher.service`, copies the
unit to `~/.config/systemd/user/`, enables and starts the service. Management:

```bash
journalctl --user -u rag-watcher -f          # logs
systemctl --user restart rag-watcher
systemctl --user stop rag-watcher
```

> If the archive is on a USB drive, uncomment `After=...mount` in
> `rag-watcher.service` so the service starts after mounting.

---

## Obsidian Integration

The Obsidian vault is `~/KMS/notes/`.

**Generating notes from documents** (frontmatter + taxonomy tags + wikilinks):

```bash
python doc_to_obsidian.py                     # all formats from archive/
python doc_to_obsidian.py --force             # regenerate existing ones
python doc_to_obsidian.py --dry-run           # without writing files
python doc_to_obsidian.py --force-single PATH # a single specific file
python pdf_to_obsidian.py                     # PDF only (legacy variant)
```

For each document, the text of the first pages is extracted, sent to the LLM for
analysis, and a `.md` file with YAML frontmatter is created. Generation is robust:
the JSON token budget auto-grows on long answers (`done_reason=length` → doubling)
and metadata is sanitized (dropping `null`/empty), so one document never breaks
the whole run. Tags are capped (15 taxonomy + 5 auto per note) to stop the model
from degenerating into long repetitive lists.

A second pass builds wikilinks: for each note it keeps the **top-15** closest —
shared tags are weighted by **IDF** (`log(N/df)`), so a rare specific tag matters
more than a ubiquitous one (`co2_storage` appears in hundreds of notes); the
threshold is ≥ `WIKILINK_MIN_COMMON_TAGS` shared tags.

**RAG query that writes the answer directly into a note:**

```bash
python rag_query_from_obsidian.py "Which CO2 trapping mechanisms are described at Sleipner?"
python rag_query_from_obsidian.py "CO2 trapping mechanisms" --note "RAG Query" --append
```

---

## MCP Server (Claude Code)

`mcp_rag_server.py` gives Claude Code access to the knowledge base as a set of
tools:

| Tool | Purpose |
|---|---|
| `search_knowledge_base` | Semantic search (+ optional LLM answer generation) |
| `list_documents` | List of indexed documents |
| `get_document_info` | Information about a specific document |
| `get_stats` | Knowledge base statistics |

Registration in `~/.claude/mcp_servers.json`:

```json
{
  "rag_kms": {
    "command": "python",
    "args": ["/home/<user>/KMS/rag_system/mcp_rag_server.py"],
    "cwd": "/home/<user>/KMS/rag_system"
  }
}
```

---

## Choosing an LLM

The provider and model are set in `config.py`:

```python
LLM_PROVIDER = "ollama"          # ollama | groq | deepseek | openrouter | lmstudio
LLM_MODEL    = "qwen3.5:latest"  # model for the selected provider (already installed in this deployment)
LLM_API_KEY  = ""                # key for cloud providers (empty for local)
```

The API key can be kept out of the file and set via an environment variable
instead: `RAG_GROQ_API_KEY`, `RAG_DEEPSEEK_API_KEY`, `RAG_OPENROUTER_API_KEY`.

| Provider | Key | Example model | Note |
|---|---|---|---|
| `ollama` | — | `qwen2.5:7b`, `mistral`, `llama3.2` | Local, offline (default) |
| `lmstudio` | — | `local-model` | Local LM Studio server (:1234) |
| `groq` | yes | `llama-3.3-70b-versatile` | Free tier |
| `deepseek` | yes | `deepseek-chat`, `deepseek-reasoner` | Very cheap |
| `openrouter` | yes | `qwen/qwen3-14b:free` | 50+ models, free options available |

> Only `ollama` and `lmstudio` provide a fully offline perimeter.
> Cloud providers send the query context to an external service.

---

## Configuration

All parameters are in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `SUPPORTED_EXTENSIONS` | 9 formats | Which files to index |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 512 / 64 | Chunk size and overlap |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Embedding model |
| `EMBEDDING_DEVICE` | `cpu` | Device for embeddings (`cpu`/`cuda`/`None`); CPU by default to avoid competing with Ollama for the GPU |
| `EMBEDDING_BATCH_SIZE` | 32 | Embedding batch (reduce if memory is low) |
| `CHROMA_COLLECTION_NAME` | `petroleum_papers` | ChromaDB collection name |
| `DEFAULT_TOP_K` / `MAX_CONTEXT_CHUNKS` | 7 / 8 | Retrieved / passed-to-LLM chunks |
| `CROSS_LANGUAGE_BALANCE` | `True` | Language-balanced retrieval (RU/EN) so a query in one language does not crowd out sources in the other |
| `CROSS_LANGUAGE_TRANSLATE_QUERY` | `True` | Dual-query: translates the question into the other language (ru↔en) and searches with both, merging the pools — otherwise the `e5` bias leaves the pool single-language and there is nothing to balance |
| `RETRIEVAL_FETCH_K` / `MIN_CHUNKS_PER_LANGUAGE` | 200 / 2 | Candidate pool before balancing / guaranteed minimum chunks per language |
| `LLM_PROVIDER` / `LLM_MODEL` | `ollama` / … | LLM provider and model |
| `OLLAMA_OPTIONS` | temp 0.2 … | Generation parameters |
| `UI_HOST` / `UI_PORT` | `127.0.0.1` / 7860 | Gradio UI address |
| `KMS_DIR` | `$HOME/KMS` | KMS root (env `KMS_HOME`) |
| `TAXONOMY` | ~140 tags | Controlled tag vocabulary for Obsidian notes (the LLM picks only from it; concepts outside it become `auto/`-prefixed tags) |
| `WIKILINK_MIN_COMMON_TAGS` | 2 | Minimum shared tags to link two notes |
| `MAX_HISTORY_MESSAGES` | 6 | Dialog memory depth |

> Tag and link-graph caps live in `doc_to_obsidian.py`: `MAX_TAXONOMY_TAGS=15`,
> `MAX_AUTO_TAGS=5` (tags per note), `RELATED_TOP_N=15` (links per note). The
> incremental-indexing manifest is `chroma_db/ingest_manifest.json`.

---

## Project Structure

```
rag_system/
├── config.py                  # configuration
├── llm_provider.py            # interface to LLM providers
├── ingest.py                  # indexing → ChromaDB
├── rag_engine.py              # search + generation
├── chat_ui.py                 # Gradio UI
├── watcher.py                 # auto-watcher
├── mcp_rag_server.py          # MCP server for Claude Code
├── doc_to_obsidian.py         # Obsidian notes (all formats)
├── pdf_to_obsidian.py         # Obsidian notes (PDF only, legacy)
├── rag_query_from_obsidian.py # RAG query from a note
├── check_cross_language.py    # cross-language retrieval diagnostics
├── obsidian_templates/        # Obsidian note templates
├── rag-watcher.service        # systemd unit template
├── install_service.sh         # service installation
├── requirements.txt           # Python dependencies
├── README.md                  # documentation (Russian)
├── README_eng.md              # this documentation (English)
├── documents/                 # local folder for documents (optional)
├── chroma_db/                 # ChromaDB vector database (created by indexing)
└── logs/
    ├── rag_system.log         # system log
    └── history/               # dialog history (JSON)
```

---

## Troubleshooting

**Ollama unavailable** (`Connection error to Ollama`):
```bash
ollama list        # check status
ollama serve       # start the server
```

**Model not found:**
```bash
ollama pull qwen2.5:7b
```

**Database is empty** (`no relevant documents found`):
```bash
ls ~/KMS/archive/  # check that files are present
python ingest.py   # run indexing
```

**Out-of-memory error during indexing** — reduce in `config.py`:
```python
EMBEDDING_BATCH_SIZE = 8
```

**Cloud provider: 401 / 429** — check `LLM_API_KEY` (401) or wait for the limit to
reset / switch to another provider (429).

**Watcher watching the wrong folder** — `ARCHIVE_DIR` must be absolute;
check `KMS_HOME` if the archive is at a non-standard path.

---

## License

The project is for internal use. Dependencies are under their own licenses:
sentence-transformers (Apache 2.0), ChromaDB (Apache 2.0), Gradio (Apache 2.0),
PyMuPDF (AGPL-3.0 — a commercial license is required for commercial use),
Ollama (MIT).
