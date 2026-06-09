# RAG KMS: Complete User Guide
## Intelligent Document Search System

**Version:** 5.1 (refined based on operational experience)  
**Author:** Alexander Knyazev, Head of the Decarbonization Technologies Department, JSC "SRI SPA "LUCH" — PB  
**Date:** 2026  

---

> **What was refined in version 5.1** (based on real installation and operation experience): the Python 3.10–3.12 requirement (ChromaDB does not build on 3.13+); the actual embedding model `multilingual-e5` (by default `e5-large` ~2.2 GB; `e5-small` ~470 MB — for speed); the real template names and note locations; correct flags (`doc_to_obsidian.py --force` instead of non-existent ones); reliable automatic processing on USB/NTFS (polling + catch-up scan on reconnection, repair of a "dirty" NTFS via `ntfsfix`); service autostart without logging in (`linger`); behavior of "reasoning" models (qwen3/deepseek-r1); optional GPU acceleration of indexing via NVIDIA CUDA (Section 6.11), while the chat uses CPU embedding, leaving the video memory for the LLM. The system scripts have been updated accordingly.

---

> This guide is written for people who don't call themselves "programmers" or "system administrators" but want a powerful tool for working with large archives of scientific, technical, and regulatory documents. We will move step by step, explaining every action and every command in simple terms.

---

## Table of Contents

- [Section 0. What You Get. How the System Works](#section-0-what-you-get-how-the-system-works)
- [Section 1. Installation](#section-1-installation)
  - [1.1 Opening the Terminal](#11-opening-the-terminal)
  - [1.2 Checking the Ubuntu Version](#12-checking-the-ubuntu-version)
  - [1.3 Checking Python](#13-checking-python)
  - [1.4 Checking Ollama](#14-checking-ollama)
  - [1.5 Downloading the Language Model](#15-downloading-the-language-model)
  - [1.6 Setting Up a USB Drive (if the archive is on USB)](#16-setting-up-a-usb-drive-if-the-archive-is-on-usb)
  - [1.7 If the Archive Is on the System Drive (no USB)](#17-if-the-archive-is-on-the-system-drive-no-usb)
  - [1.8 Extracting the System Archive](#18-extracting-the-system-archive)
  - [1.9 Creating a Virtual Environment](#19-creating-a-virtual-environment)
  - [1.10 Installing Dependencies](#110-installing-dependencies)
- [Section 2. Configuration](#section-2-configuration)
  - [2.1 Configuring Paths in config.py](#21-configuring-paths-in-configpy)
  - [2.2 Installing Obsidian](#22-installing-obsidian)
  - [2.3 Setting Up the Obsidian Vault](#23-setting-up-the-obsidian-vault)
  - [2.4 Copying Note Templates](#24-copying-note-templates)
- [Section 3. First Run](#section-3-first-run)
  - [3.1 Adding the First Documents](#31-adding-the-first-documents)
  - [3.2 Running RAG Indexing](#32-running-rag-indexing)
  - [3.3 Creating Obsidian Notes](#33-creating-obsidian-notes)
  - [3.4 Opening the Graph in Obsidian](#34-opening-the-graph-in-obsidian)
  - [3.5 Launching the Chat Interface](#35-launching-the-chat-interface)
- [Section 4. Auto-Starting the Watcher](#section-4-auto-starting-the-watcher)
  - [4.1 What the Watcher Does](#41-what-the-watcher-does)
  - [4.2 Installing as a Service](#42-installing-as-a-service)
  - [4.3 Managing the Service](#43-managing-the-service)
  - [4.4 Verifying the Watcher Works](#44-verifying-the-watcher-works)
  - [4.5 Working with a USB Drive](#45-working-with-a-usb-drive)
- [Section 5. Daily Use](#section-5-daily-use)
  - [5.1 Adding New Documents](#51-adding-new-documents)
  - [5.2 Working with Obsidian](#52-working-with-obsidian)
  - [5.3 Questions via the Chat Interface](#53-questions-via-the-chat-interface)
  - [5.4 Questions from the Command Line](#54-questions-from-the-command-line)
  - [5.5 Updating the Tag Taxonomy](#55-updating-the-tag-taxonomy)
- [Section 6. Troubleshooting](#section-6-troubleshooting)
  - [6.1 "command not found" When Running Python Scripts](#61-command-not-found-when-running-python-scripts)
  - [6.2 "Ollama unavailable" / "Connection refused"](#62-ollama-unavailable--connection-refused)
  - [6.3 "Model not found"](#63-model-not-found)
  - [6.4 Poor-Quality Answers in Russian](#64-poor-quality-answers-in-russian)
  - [6.5 A Document Is Not Indexed](#65-a-document-is-not-indexed)
  - [6.6 The Watcher Does Not See New Files](#66-the-watcher-does-not-see-new-files)
  - [6.7 No Disk Space](#67-no-disk-space)
  - [6.8 Forgot How to Launch the Chat](#68-forgot-how-to-launch-the-chat)
  - [6.9 Ollama Runs Very Slowly](#69-ollama-runs-very-slowly)
  - [6.10 Error When Installing Dependencies](#610-error-when-installing-dependencies)
  - [6.11 Speeding Up Indexing with a Video Card (GPU)](#611-speeding-up-indexing-with-a-video-card-gpu--nvidia-cuda)
- [Section 7. Managing LLM Providers](#section-7-managing-llm-providers)
  - [7.1 Switching the Provider](#71-switching-the-provider)
  - [7.2 Recommended Models for Oil & Gas Topics](#72-recommended-models-for-oil--gas-topics)
  - [7.3 Environment Variables](#73-environment-variables)
  - [7.4 Troubleshooting Providers](#74-troubleshooting-providers)
- [Section 8. Updating Ollama and the LLM](#section-8-updating-ollama-and-the-llm)
- [Section 9. Connecting Claude Code via MCP (optional)](#section-9-connecting-claude-code-via-mcp-optional)
  - [9.0 What Claude Code and MCP Are](#90-what-claude-code-and-mcp-are)
  - [9.1 Installing Claude Code](#91-installing-claude-code)
  - [9.2 Preparing the MCP Server](#92-preparing-the-mcp-server)
  - [9.3 Connecting MCP to Claude Code](#93-connecting-mcp-to-claude-code)
  - [9.4 First Queries](#94-first-queries)
  - [9.5 Configuring CLAUDE.md](#95-configuring-claudemd)
  - [9.6 Using the Tools Directly](#96-using-the-tools-directly)
  - [9.7 Troubleshooting](#97-troubleshooting)
  - [9.8 Claude Code Command Cheat Sheet](#98-claude-code-command-cheat-sheet)
- [Appendix A. System File Structure](#appendix-a-system-file-structure)
- [Appendix B. Glossary](#appendix-b-glossary)
- [Appendix C. Installation Checklist](#appendix-c-installation-checklist)
- [Appendix D. Frequently Asked Questions (FAQ)](#appendix-d-frequently-asked-questions-faq)
- [Cheat Sheet. All Key Commands](#cheat-sheet-all-key-commands)

---

## Section 0. What You Get. How the System Works

After you go through this guide from start to finish, you will have a working system that can:

- **Automatically process new documents** — just copy a file into a folder (or plug in a USB drive with the archive), and the system does everything itself: extracts the text, indexes it, and creates a note. Supported formats: PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT.
- **Answer questions about the content of your documents** — you can ask something like "Which regulations describe the requirements for pipeline pressure testing?" and get a specific answer with references to the sources.
- **Work fully offline** — all processing happens on your computer, no data goes to the internet, and no subscription is required.
- **Organize knowledge in Obsidian** — each document is automatically turned into a structured note with tags, a summary, and links to related works. The link graph in Obsidian shows which topics and authors overlap in your archive.
- **Ask questions in Russian and English** — the language model understands both languages and answers in the language you ask the question in.
- **Work with an archive on a USB drive** — if your documents are stored on an external drive, the system can work with it directly via a symbolic link, without duplicating gigabytes of data onto the system drive.
- **Use cloud and local LLM providers** — version 5.0 (v4.2) added support for Groq, DeepSeek, OpenRouter, and LM Studio in addition to the local Ollama.

---

### How the System Works

Before you begin, it is helpful to understand the "big picture" — how all the parts of the system relate to one another. Don't worry if something is unclear right now — by the end of the guide everything will fall into place.

```
Documents (PDF/DOCX/TXT/XLSX/PPTX/ODT/...) → Watcher (watcher.py)
                                                       ↓
                                            detected a new file
                                              /            \
                                    RAG indexing      Obsidian note
                                     (ChromaDB)       with tags and summary
                                                             ↓
                                                       Link graph

Question → RAG engine → ChromaDB → LLM provider → Answer + sources
                                       ↑
                          (Ollama / Groq / DeepSeek /
                           OpenRouter / LM Studio)
```

**Explanation of each part:**

- **Documents on USB** — your materials in PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT formats, stored on a flash drive or external disk (or in a regular folder on the computer).
- **Watcher (watcher.py)** — a small program that constantly "watches" your archive folder. As soon as a new file appears there, it launches processing.
- **RAG indexing (ChromaDB)** — RAG stands for *Retrieval-Augmented Generation*. Roughly speaking, this is a technology that first finds the most relevant fragments in your knowledge base and then uses them to answer. ChromaDB is a special database that can search by meaning, not just by exact word matches.
- **Obsidian note** — an automatically created structured document in Markdown format with metadata, a brief summary, and tags.
- **Link graph** — a visual representation of how the notes are connected to one another through shared topics, authors, and keywords.
- **LLM provider** — in version 5.0 the system supports several providers: the local Ollama (no internet), Groq (cloud, free), DeepSeek, OpenRouter, and LM Studio. It is the LLM that formulates the answers in human language.

---

## Section 1. Installation

This section is devoted to preparing all the necessary software. We will go through each step methodically, and at the end you will have an environment ready for work.

---

### 1.1 Opening the Terminal

**What is a terminal?**

A terminal (also called a "console," "command line," or "shell") is a program that lets you control the computer using text commands. Instead of clicking buttons with a mouse, you type instructions as text. It sounds old-fashioned, but for setup and automation tasks it is much faster and more precise than a graphical interface.

**How to open the terminal in Ubuntu:**

The simplest way is to press the key combination **Ctrl + Alt + T**. A dark window with a blinking cursor should appear.

If the key combination does not work, you can find the terminal manually:
1. Press the **Super** key (also called "Windows" on most keyboards) — the applications menu will open.
2. Start typing the word "Terminal".
3. Click the icon that appears.

**What does the prompt line mean?**

After opening the terminal, you will see something like:

```
username@computer:~$
```

Let's break it down piece by piece:
- `username` — the name of your Ubuntu account (what you enter when logging into the system).
- `computer` — the name of your computer.
- `~` — shorthand for your home directory (folder). Its full path usually looks like `/home/username`. The `~` symbol is just a convenient shortcut.
- `$` — means you are working as a regular user (not an administrator). If you were working as the administrator (root), there would be a `#` symbol here.

> [i] **Tip:** You don't need to type the `$` symbol itself when entering commands — it is already there in the prompt. Type only what is written after it.

---

### 1.2 Checking the Ubuntu Version

First, let's make sure you have a suitable version of the operating system. Our system runs on Ubuntu 20.04 and newer.

```bash
lsb_release -a
```

> **[>>] What you'll see:**
> ```
> No LSB modules are available.
> Distributor ID: Ubuntu
> Description:    Ubuntu 22.04.3 LTS
> Release:        22.04
> Codename:       jammy
> ```
> We are interested in the `Release` line. If it says 20.04, 22.04, or 24.04 — everything is fine, let's continue. If yours is older — it is recommended to update Ubuntu through official channels before continuing.

> [i] **Tip:** The letters `LTS` in the version name stand for *Long-Term Support* — meaning this version receives security updates for 5 years. For a production system, this is the best choice.

---

### 1.3 Checking Python

**What is Python?**

Python is a programming language in which most of our system is written. It is very popular in the scientific community and in the world of artificial intelligence precisely because it allows you to write working code quickly. To run Python programs on your computer, a Python interpreter must be installed — a program that "reads" the code and executes it.

Let's verify that Python is installed and has a suitable version:

```bash
python3 --version
```

> **[>>] What you'll see:**
> ```
> Python 3.10.12
> ```
> or a similar line with version 3.10, 3.11, or 3.12 — all of these are fine. You need Python **3.10–3.12**.
>
> [!] **Important:** on **Python 3.13 and newer**, installing dependencies currently fails — there are no ready-made ChromaDB packages for the latest Python yet, and the build of `chroma-hnswlib` ends with the error `Python.h: No such file or directory`. If `python3 --version` shows 3.13+, install 3.12 alongside it (`sudo apt install python3.12 python3.12-venv`) and create the environment with `python3.12 -m venv .venv`.

**If the version is below 3.10 (for example, 3.8 or 3.9):**

You need to install a newer version. In Ubuntu this is done as follows:

```bash
sudo apt update && sudo apt install python3.11 -y
```

**What is `sudo`?**

`sudo` — from the English *SuperUser DO*. Some commands require administrator privileges — for example, installing new programs. `sudo` temporarily grants your command these privileges. On first use, the system will ask you to enter your password. Note: when you type a password in the terminal, the characters do not appear on screen — this is normal, designed this way for security. Just type the password and press Enter.

> **[>>] What you'll see after `sudo apt update`:**
> A long list of lines like `Get:1 http://...` — the system is downloading information about available packages. At the end — the line `Reading package lists... Done`.

> **[>>] What you'll see after `sudo apt install python3.11 -y`:**
> An installation process with progress bars. The `-y` flag means "automatically answer 'yes' to all installer questions."

After installation, make sure everything went successfully:

```bash
python3.11 --version
```

> **[>>] What you'll see:**
> ```
> Python 3.11.x
> ```

---

### 1.4 Checking Ollama

**What is Ollama?**

Ollama is a program that lets you run large language models (LLMs) directly on your computer, without the internet and without paid APIs. It works as a "server" — it runs in the background and responds to requests from our system.

Let's check whether Ollama is installed:

```bash
ollama list
```

> **[>>] What you'll see if Ollama is installed:**
> ```
> NAME            ID              SIZE    MODIFIED
> mistral:latest  f974a74358d6    4.1 GB  2 weeks ago
> ```
> or an empty table with headers — this means Ollama is installed but no models have been downloaded yet.

> **[>>] What you'll see if Ollama is NOT installed:**
> ```
> bash: ollama: command not found
> ```
> In this case, proceed to the installation below.

**If Ollama is not installed:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Let's break down this command:
- `curl` — a program for downloading files from the internet.
- `-fsSL` — a set of flags: `-f` (don't show error pages), `-s` (silent mode), `-S` (still show errors), `-L` (follow redirects).
- `https://ollama.com/install.sh` — the address of the installation script.
- `| sh` — the `|` symbol is called a "pipe" and passes the downloaded script straight to execution by the `sh` command (the shell interpreter).

> **[>>] What you'll see:**
> ```
> >>> Installing ollama to /usr/local/bin...
> >>> Creating ollama user...
> >>> Adding ollama user to video group...
> >>> Adding current user to ollama group...
> >>> Creating ollama systemd service...
> >>> Enabling and starting ollama service...
> ```
> Installation will take 1–2 minutes.

After installation, check again:

```bash
ollama list
```

> **[>>] What you'll see:**
> An empty table with the headers `NAME  ID  SIZE  MODIFIED` — Ollama is installed and working.

> [!] **Important:** After installing Ollama, you may need to restart the terminal or run `source ~/.bashrc` so that the `ollama` command becomes available in the current session.

---

### 1.5 Downloading the Language Model

**What is an LLM (large language model)?**

An LLM (*Large Language Model*) is a program trained on huge amounts of text that can understand and generate human language. It is the LLM that will "think" and formulate answers to your questions. For the initial setup, we will use the **Mistral** model — an open model that works well on ordinary computers and understands Russian. Later you will be able to change the model (see Section 7).

```bash
ollama pull mistral
```

The `pull` command downloads the model from the Ollama repository onto your computer.

> ✅ **This is normal:** the model weighs about 4 GB, and the download will take 10 to 20 minutes depending on your internet speed. You will see a progress bar like:
> ```
> pulling manifest
> pulling ff82381e2bea... 100% ▕████████████████▏ 3.8 GB
> pulling 43070e2d4e53...  100% ▕████████████████▏  11 KB
> verifying sha256 digest
> writing manifest
> removing any unused layers
> success
> ```
> Do not close the terminal and wait for the word `success`.

After downloading, let's check:

```bash
ollama list
```

> **[>>] What you'll see:**
> ```
> NAME            ID              SIZE    MODIFIED
> mistral:latest  f974a74358d6    4.1 GB  Just now
> ```
> Great! The model is ready to use.

> [i] **Tip:** If you have a computer with 16 GB of RAM or more, it is recommended to install the `qwen2.5:7b` model — it works better with Russian and technical topics. More on this in Section 7.

---

### 1.6 Setting Up a USB Drive (if the archive is on USB)

> If your files are stored not on USB but directly on the computer — skip this step and go to Section 1.7.

**Why do you need a symbolic link?**

Imagine that your USB drive is a bookshelf in another room. Instead of going to that room every time, you can hang a sign with a pointer on the wall next to you: "Bookshelf — over there." A symbolic link (symlink) is such a "pointer" in the file system. The folder `~/KMS/archive` will look like an ordinary folder on your computer, but in reality it will be a "pointer" to a folder on your USB drive.

This is convenient for two reasons:
1. Programs can work with a single path `~/KMS/archive` without knowing where the files physically reside.
2. You don't waste space on the system drive — the data stays on the USB.

**Step 1: Plug in the USB drive** and find out its name in the system.

```bash
lsblk
```

The `lsblk` command (*list block devices*) shows all connected block devices (disks and partitions).

> **[>>] What you'll see:**
> ```
> NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
> sda      8:0    0 238.5G  0 disk
> ├─sda1   8:1    0   512M  0 part /boot/efi
> └─sda2   8:2    0   238G  0 part /
> sdb      8:16   1  14.9G  0 disk
> └─sdb1   8:17   1  14.9G  0 part /media/username/MY_USB
> ```
> Your USB drive is usually labeled `sdb` or `sdc`. Pay attention to the `MOUNTPOINT` column — there will be a path like `/media/username/MY_USB`. That is what we need.

Now let's look at the contents of the folder with mounted disks:

```bash
ls /media/$USER/
```

Here `$USER` is a special variable that automatically substitutes your username.

> **[>>] What you'll see:**
> ```
> MY_USB
> ```
> or another name for your disk. Remember this name — we will need it.

**Step 2: Create the folder structure and the symbolic link.**

First, let's create a `KMS` folder in the home directory (if it doesn't exist yet):

```bash
mkdir -p ~/KMS
```

The `-p` flag means "create all intermediate folders if they don't exist, and don't throw an error if the folder already exists."

Now let's create a folder for the archive on the USB drive (if it doesn't exist yet) and a symbolic link:

```bash
mkdir -p /media/$USER/DISK_NAME/petroleum_papers
ln -s /media/$USER/DISK_NAME/petroleum_papers ~/KMS/archive
```

> [!] **Important:** Replace `DISK_NAME` with the real name of your USB drive (the one you saw with the `ls /media/$USER/` command). And replace `petroleum_papers` with the name of the folder containing your documents if it already exists on the drive. For example, if your PDFs are in a folder `papers` at the root of the drive, the command will be:
> ```bash
> ln -s /media/$USER/MY_USB/papers ~/KMS/archive
> ```

Let's verify that the link was created correctly:

```bash
ls -la ~/KMS/archive
```

> **[>>] What you'll see:**
> ```
> lrwxrwxrwx 1 username username 35 Jan 15 10:23 /home/username/KMS/archive -> /media/username/MY_USB/petroleum_papers
> ```
> The arrow `->` shows where the symbolic link leads. If you see this arrow — everything is correct.

> [!] **Important:** The symbolic link will be "broken" if the USB drive is not connected. The command `ls ~/KMS/archive` will produce an error. This is normal behavior — just plug in the drive.

---

### 1.7 If the Archive Is on the System Drive (no USB)

If your documents are stored directly on the computer (or you want to try the system without USB first), simply create a folder for the archive:

```bash
mkdir -p ~/KMS/archive
```

Done! No symbolic links are needed — you will just place documents directly into this folder.

---

### 1.8 Extracting the System Archive

**What is tar.gz?**

When you download a program in Linux, it often comes as a file with the `.tar.gz` extension. This is a compressed archive — analogous to `.zip` in Windows, only with different algorithms. `tar` is a utility for packing multiple files into one, and `.gz` is additional compression with the gzip algorithm.

It is assumed that you downloaded the `rag_system_final.tar.gz` file into the Downloads folder (`~/Загрузки` on Russian-language Ubuntu or `~/Downloads` on English-language).

Let's go to the home directory and extract only the system folder into `~/KMS/`:

```bash
cd ~
tar -xzf ~/Downloads/rag_system_final.tar.gz -C ~/KMS/ rag_system
```

Let's break down the `tar` command flags:
- `-x` — *extract* (extract files from the archive)
- `-z` — use gzip for decompression (needed for `.gz` files)
- `-f` — the next argument is the name of the archive file
- `-C ~/KMS/` — *change directory* (extract into this folder, not the current one)

> [!] **Important:** If the `~/Downloads` folder doesn't find the file, try `~/Загрузки/rag_system_final.tar.gz` — the folder name depends on your system's language.

Let's verify that the extraction went successfully:

```bash
ls ~/KMS/rag_system/
```

> **[>>] What you'll see:**
> ```
> chat_ui.py          config.py           ingest.py
> doc_to_obsidian.py  pdf_to_obsidian.py  rag_engine.py
> llm_provider.py     requirements.txt    install_service.sh
> watcher.py          obsidian_templates/ chroma_db/
> logs/               mcp_rag_server.py
> ```
> If you see these files — the archive was extracted correctly. Each of these files is a part of the system we will work with in this guide. Note `llm_provider.py` — this is a new module in version 5.0 that manages several LLM providers.

> [i] **Tip:** All examples in the guide assume the system is installed in `~/KMS/rag_system`. The command above extracts it exactly there. If you extracted the archive elsewhere — the paths to the document archive and notes are still computed from your home directory (`~/KMS/archive` and `~/KMS/notes`), so the system will keep working (see Section 2.1).

---

### 1.9 Creating a Virtual Environment

**What is a virtual environment and why is it needed?**

Imagine that Python is a workshop, and packages (libraries) are tools. If different projects need different versions of the same tools, they can interfere with each other. A virtual environment is like a separate "toolbox" for each project. It holds exactly the package versions that this particular project needs, and they don't conflict with other projects or the system Python packages.

Let's go to the system folder and create a virtual environment:

```bash
cd ~/KMS/rag_system
python3 -m venv .venv
```

Let's break down the command:
- `python3 -m venv` — run the `venv` module (a tool built into Python for creating virtual environments).
- `.venv` — the name of the folder into which all environment files will be installed. The dot at the beginning means it is a "hidden" folder (it won't be shown by an ordinary `ls`, but `ls -a` will show it).

Now let's activate (turn on) the virtual environment:

```bash
source .venv/bin/activate
```

> **[>>] What you'll see:** `(.venv)` will appear at the beginning of the prompt line:
> ```
> (.venv) username@computer:~/KMS/rag_system$
> ```
> This means the virtual environment is active and all subsequent Python and pip commands will run inside it.

> [!] **Important:** The virtual environment must be **activated every time you open a new terminal** before running the system's programs. The activation command:
> ```bash
> source ~/KMS/rag_system/.venv/bin/activate
> ```
> If you forget to do this, you will see errors like `ModuleNotFoundError: No module named 'chromadb'`. This is not a system breakdown — you just need to activate the environment.

> [i] **Tip:** To exit the virtual environment, type `deactivate`. But while working with the system, you don't need to exit the environment.

---

### 1.10 Installing Dependencies

**What are dependencies and pip?**

Our system is written in Python and uses many ready-made libraries (packages) — for example, ChromaDB for working with the database, Gradio for the chat web interface, python-docx for working with Word documents. The list of all the needed libraries is recorded in the `requirements.txt` file.

**First, let's install system packages** — they are needed for processing the DOC format (old Word files):

```bash
sudo apt update
sudo apt install libreoffice antiword -y
```

> **What these packages do:**
> - `libreoffice` — an office suite. The system uses it in the background to convert old `.doc` files into text. You don't need to launch LibreOffice manually.
> - `antiword` — a backup `.doc` converter, used if LibreOffice is unavailable.
>
> Installation will take 3–5 minutes — LibreOffice is a fairly large package (~300 MB).

`pip` is the Python package manager (from *Pip Installs Packages*). It can download libraries from the internet and install them in the right place.

First, let's upgrade pip itself to the latest version:

```bash
pip install --upgrade pip
```

> **[>>] What you'll see:**
> ```
> Requirement already satisfied: pip in ./.venv/lib/python3.10/site-packages (23.0.1)
> Collecting pip
>   Downloading pip-24.0-py3-none-any.whl (2.1 MB)
> ...
> Successfully installed pip-24.0
> ```

Now let's install all dependencies from the requirements file:

```bash
pip install -r requirements.txt
```

> ✅ **This is normal:** You will see a long list of packages being downloaded and installed. The process will take 5 to 15 minutes depending on your internet speed. Don't be alarmed if the list seems huge — this is standard behavior. The lines will look roughly like:
> ```
> Collecting chromadb==0.4.22
>   Downloading chromadb-0.4.22-py3-none-any.whl (512 kB)
>      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 512.3/512.3 kB 3.2 MB/s eta 0:00:00
> Collecting langchain==0.1.0
>   Downloading langchain-0.1.0-py3-none-any.whl (800 kB)
>   ...
> Successfully installed chromadb-0.4.22 langchain-0.1.0 ...
> ```
> When everything is installed, the last line will be `Successfully installed ...` with a list of all installed packages.

> [!] **Important:** If a line with `ERROR` or `error` appears during installation, read it carefully. Often it means some system library is missing. The most common error is solved with the command:
> ```bash
> sudo apt install python3-dev build-essential libssl-dev libffi-dev -y
> ```
> After which repeat `pip install -r requirements.txt`.

---

## Section 2. Configuration

After installing all components, we need to configure the system for your specific environment: specify where the files are, install Obsidian, and prepare the note storage.

---

### 2.1 Configuring Paths in config.py

**What is nano?**

`nano` is a simple text editor that works right in the terminal. Unlike `vim` or `emacs`, it is easy to figure out without experience. Control is done with key combinations, which are always shown at the bottom of the screen (the `^` symbol means the Ctrl key).

Let's open the configuration file:

```bash
nano ~/KMS/rag_system/config.py
```

> **[>>] What you'll see:** The text editor will open right in the terminal. At the top — the file name, in the middle — its contents, at the bottom — control hints. You can move through the file with the arrow keys.

To quickly find the right place, use search: press **Ctrl+W** (W for *Where*), type `LLM_PROVIDER`, and press Enter. The cursor will move to the first occurrence of this word.

You only need to manually edit **three lines** — the choice of LLM provider and model:

```python
LLM_PROVIDER: str = "ollama"
LLM_MODEL:    str = "qwen3.5:latest"  # the already-installed model (or "mistral" if you downloaded it)
LLM_API_KEY:  str = ""
```

**What each line means:**
- `LLM_PROVIDER` — the active LLM provider (more on this in Section 7).
- `LLM_MODEL` — the name of the model for the selected provider. By default `config.py` specifies `qwen3.5:latest` — the model already installed in this deployment. If in Section 1.5 you downloaded `mistral`, specify `"mistral"`.
- `LLM_API_KEY` — the API key for cloud providers (leave empty when working with Ollama).

> [!] **Important (about paths):** The folders with documents and notes **do not need** to be specified manually — the system computes them automatically from your home directory:
> - document archive → `~/KMS/archive`
> - Obsidian notes → `~/KMS/notes`
>
> In the code, `KMS_ARCHIVE_DIR` and `KMS_VAULT_DIR` are responsible for this. Do not edit them and do not turn them into relative paths like `"KMS/archive"` — otherwise the watcher will watch the wrong folder.
>
> If your archive is on a USB drive at a non-standard path (and you did not make the symbolic link from Section 1.6), you can explicitly specify the KMS root folder via an environment variable. Add to the end of `~/.bashrc`:
> ```bash
> export KMS_HOME="/media/$USER/DISK_NAME/KMS"
> ```
> and run `source ~/.bashrc`.

To edit, simply move the cursor to the desired line with the arrows and make changes.

**Saving and exiting nano:**
1. Press **Ctrl+X** (exit)
2. The question `Save modified buffer?` will appear — press **Y** (yes)
3. A line with the file name will appear — press **Enter** to confirm

> **[>>] What you'll see after saving:** Nano will close, and you will return to the normal terminal command line.

> [i] **Tip:** If you accidentally messed something up and want to exit WITHOUT saving changes, press Ctrl+X, then **N** (no). The file will remain untouched.

**Checking the paths.** Make sure the system sees the correct folders. Run:

```bash
cd ~/KMS/rag_system && source .venv/bin/activate
python -c "import config; print('archive:', config.KMS_ARCHIVE_DIR); print('notes  :', config.KMS_VAULT_DIR)"
```

> **[>>] What you'll see:**
> ```
> archive: /home/YOUR_NAME/KMS/archive
> notes  : /home/YOUR_NAME/KMS/notes
> ```
> If instead you see a path with a double `KMS` (`.../KMS/KMS/archive`) or a relative path — you have an old version of `config.py` with a path-computation bug.

> [!] **If the paths are wrong — update `config.py`:** in the fixed version the KMS directory is tied to the home directory (`$HOME/KMS`) rather than the installation location of `rag_system`. Replace the "Obsidian / KMS integration" block in `config.py` with:
> ```python
> KMS_DIR = Path(os.environ.get("KMS_HOME", str(Path.home() / "KMS")))
> KMS_ARCHIVE_DIR = KMS_DIR / "archive"
> KMS_VAULT_DIR = KMS_DIR / "notes"
> ARCHIVE_DIR: str = str(KMS_ARCHIVE_DIR)
> OBSIDIAN_VAULT_DIR: str = str(KMS_VAULT_DIR)
> ```
> (previously it had `KMS_DIR = BASE_DIR.parent / "KMS"` and the relative strings `"KMS/archive"`/`"KMS/notes"`). After the fix, repeat the check above.

---

### 2.2 Installing Obsidian

**What is Obsidian?**

Obsidian is an application for creating and organizing notes in Markdown format (plain text with markup). Its main feature is the ability to build a "knowledge graph": a visual map of connections between your notes. In our system, each document is automatically turned into an Obsidian note, and you will be able to see how documents are connected to one another by topics and authors.

Download Obsidian from the official site: [https://obsidian.md](https://obsidian.md)

On the download page, choose the option for Linux — the file will be named something like `obsidian-1.5.3.deb`. Save it to the Downloads folder.

Let's install the downloaded `.deb` file (`.deb` is the package format for Ubuntu/Debian):

```bash
cd ~/Downloads
sudo dpkg -i obsidian-*.deb
```

The `dpkg -i` (*install*) command installs the package. The `*` symbol means "any characters" — this way we don't depend on the exact version number in the file name.

> **[>>] What you'll see:**
> ```
> Selecting previously unselected package obsidian.
> (Reading database ... 312840 files and directories currently installed.)
> Preparing to unpack obsidian-1.5.3.deb ...
> Unpacking obsidian (1.5.3) ...
> Setting up obsidian (1.5.3) ...
> ```

**If an error appears:**

Sometimes when installing `.deb` packages, Ubuntu reports missing dependencies. This looks like lines with `Depends:`. In this case, run:

```bash
sudo apt install -f
```

The `-f` flag means *fix broken* — apt will automatically download and install all the missing dependencies and complete the Obsidian installation.

After installation, Obsidian should appear in the Ubuntu applications menu. Press Super (Win) and start typing "Obsidian" — you should see its icon.

---

### 2.3 Setting Up the Obsidian Vault

**What is a Vault in Obsidian?**

A Vault is simply a folder on your computer that Obsidian tracks and in which it stores all notes. Obsidian can work with several vaults, but we need to create one — `~/KMS/notes`.

First, let's create a folder for the vault:

```bash
mkdir -p ~/KMS/notes
```

Now open Obsidian. On first launch, a welcome screen will appear:

1. Click **"Open folder as vault"**.
2. In the folder selection dialog, go to the home directory, then to `KMS`, then select the `notes` folder.
3. Click **"Open"**.

Obsidian will open with an empty vault. On the left you will see a file panel (empty for now), on the right — an area for writing notes.

> [i] **Tip:** If the system doesn't find the `~/KMS/notes` folder in the dialog, try entering the path manually in the address bar of the file dialog: press Ctrl+L (or Ctrl+Shift+G on some systems) and enter `/home/YOUR_NAME/KMS/notes`.

---

### 2.4 Copying Note Templates

Our system uses Obsidian templates — pre-made structures for notes that are automatically filled with data from documents. Let's copy them to the right place:

```bash
mkdir -p ~/KMS/notes/Templates
cp ~/KMS/rag_system/obsidian_templates/* ~/KMS/notes/Templates/
```

Let's verify that the templates were copied:

```bash
ls ~/KMS/notes/Templates/
```

> **[>>] What you'll see:**
> ```
> 'Literature Note.md'   'RAG Query.md'   'Research Session.md'   'Shell Commands.md'
> ```

Now we need to tell Obsidian where to look for templates:

1. In Obsidian, open **Settings** — click the gear icon in the bottom-left corner or Ctrl+,.
2. In the left settings menu, go to the **Core plugins** section.
3. Find the **Templates** plugin and make sure it is enabled (the toggle should be blue).
4. Click the settings icon next to Templates.
5. In the **Template folder location** field, enter: `Templates`
6. Close the settings.

> ✅ **This is normal:** If you see the `Templates` folder in the left panel of Obsidian — everything is configured correctly.

---

## Section 3. First Run

All components are installed and configured. It's time to launch the system for the first time! Let's add a few documents, create an index, and verify that everything works.

---

### 3.1 Adding the First Documents

For the first run, add 2–3 files to the archive folder. The system supports the formats: PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT. This can be done in two ways.

**Method 1: Through the file manager (Nautilus)**

Open the Ubuntu file manager (the folder icon on the taskbar or Ctrl+L → enter the path). Find your files, select them, and drag them into the `~/KMS/archive` folder. That's it!

**Method 2: Through the terminal**

```bash
cp /path/to/file.docx ~/KMS/archive/
```

For example, if the file is in the Downloads folder:

```bash
cp ~/Downloads/my_report.pdf ~/KMS/archive/
cp ~/Downloads/notes.docx ~/KMS/archive/
cp ~/Downloads/data.xlsx ~/KMS/archive/
```

Or copy all files of one type at once:

```bash
cp ~/Downloads/*.pdf ~/KMS/archive/
cp ~/Downloads/*.docx ~/KMS/archive/
```

> [i] **Tip:** Files of different formats can be mixed in one folder and in subfolders — the system processes each file in the right way automatically.

Let's verify that the files ended up where they should:

```bash
ls ~/KMS/archive/
```

> **[>>] What you'll see:**
> ```
> article_1.pdf  report.docx  data.xlsx
> ```

---

### 3.2 Running RAG Indexing

Now let's ask the system to process the documents: extract the text, split it into fragments, and create "vector representations" (embeddings — numerical codes that convey the meaning of the text) for subsequent search.

Let's make sure we're in the right folder and the virtual environment is active:

```bash
cd ~/KMS/rag_system
source .venv/bin/activate
```

Run indexing:

```bash
python ingest.py
```

> ✅ **This is normal:** On the **first** run, the system will download the multilingual embedding model `intfloat/multilingual-e5-large` (~2.2 GB, understands Russian well, high search quality). It is downloaded once, then taken from the cache; on a slow internet connection the download will take 15–30 minutes. You will see:
> ```
> Downloading intfloat/multilingual-e5-large...
> Downloading: 100%|████████████████| 2.24G/2.24G [18:40<00:00, 2.0MB/s]
> ```
> [i] **Tip:** if speed or saving space matters, you can specify a smaller model — `EMBEDDING_MODEL = "intfloat/multilingual-e5-small"` (~470 MB): slightly lower search quality, but noticeably faster. After changing the model, be sure to reindex: `python ingest.py --reset`.
>
> [i] **Embedding device.** By default the model runs on CPU (`EMBEDDING_DEVICE = "cpu"` in `config.py`). This is intentional: an 8 GB GPU cannot hold both the local LLM (Ollama, ~6 GB) and the embedding model (~2 GB) at once — indexing crashed with `CUDA out of memory`. On CPU there is no conflict, and embedding a single query still takes a fraction of a second (only bulk indexing is slower). If the GPU is free or has enough memory, set `EMBEDDING_DEVICE = "cuda"` (or `None` for auto-selection) to speed up indexing.

After the model is downloaded, file processing will begin:

> **[>>] What you'll see:**
> ```
> Processing: article_1.pdf  [PDF]
>   Extracting text... done (47 pages)
>   Splitting into chunks... done (312 chunks)
>   Creating embeddings... 100%|########| 312/312 [00:45<00:00, 6.9it/s]
>   Stored in ChromaDB.
> Processing: report.docx  [DOCX]
>   Extracting text... done (12 pages)
>   Splitting into chunks... done (78 chunks)
>   ...
>
> Indexing complete. Total documents: 3, Total chunks: 468
> ```

Each "chunk" (fragment) is a small piece of text from a document (usually 300–500 words) to which the system assigns a numerical representation. When searching, the system will find the most relevant fragments and pass them to the language model.

> [i] **Tip:** If indexing takes a very long time (more than 30 minutes for a single document), the system is most likely working without GPU support. This is normal — just slower. You can leave the process running and do other things; it does not require your attention.

---

### 3.3 Creating Obsidian Notes

Now let's ask the system to create structured notes in Obsidian for each indexed document. In v5.0 the `doc_to_obsidian.py` script is responsible for this — it can work with all supported formats.

**First, let's run it in "dry run" mode** — this will show what would be created without actually creating files:

```bash
python doc_to_obsidian.py --dry-run
```

> **[>>] What you'll see:**
> ```
> DRY RUN MODE - no files will be created
>
> Would create: ~/KMS/notes/Articles/article_1.md
>   Title: Enhanced Oil Recovery Using CO2 Injection...
>   Type: PDF
>   Tags: #auto/co2-injection #auto/eor #auto/reservoir-simulation
>
> Would create: ~/KMS/notes/Articles/report.md
>   Title: Quarterly Report Q1 2024
>   Type: DOCX
>   Tags: #auto/report #auto/quarterly
>
> Total: 3 notes would be created.
> ```

If everything looks right, we run the actual note creation:

```bash
python doc_to_obsidian.py
```

> **[>>] What you'll see:**
> ```
> Processing article_1.pdf [PDF]...
>   Generating summary via LLM... done
>   Extracting metadata... done
>   Creating note: ~/KMS/notes/Articles/article_1.md
>   Created
>
> Processing report.docx [DOCX]...
>   Generating summary via LLM... done
>   ...
>
> All done! Created 3 notes in ~/KMS/notes/Articles/
> ```

Creating notes takes about 1–2 minutes per document — during this time the language model generates a brief summary of the content based on the extracted text.

> [i] **Tip:** The `--dry-run` flag is a very useful tool. Many programs support it. It lets you "play out" an operation and see what will happen before actually changing anything. It is useful before operations that are hard to undo.

---

### 3.4 Opening the Graph in Obsidian

Now open Obsidian. In the left panel you should see a new `Articles` folder with notes for each document.

To open the link graph:
1. Click the **graph** icon in the left panel (an icon with dots connected by lines) — or use the hotkey **Ctrl+G**.
2. An interactive graph will open.

> **[>>] What you'll see:** A graph with several nodes (dots) — one for each note — and lines connecting them through shared tags and mentions. The more documents you have, the more interesting the graph will look: "clusters" by topic will appear, central nodes (frequently cited authors or key topics), and peripheral documents.

You can:
- **Click a node** — the note will open.
- **Drag a node** — move it around the graph.
- **Scroll the mouse wheel** — zoom in/out.
- **Right-click on empty space** — open display settings.

---

### 3.5 Launching the Chat Interface

The final step is launching the web interface for communicating with your archive:

```bash
python chat_ui.py
```

> **[>>] What you'll see:**
> ```
> Running on local URL:  http://127.0.0.1:7860
>
> To create a public link, set `share=True` in `launch()`.
> ```

Open a browser (Firefox, Chrome — any) and go to the address:

```
http://127.0.0.1:7860
```

> **[>>] What you'll see in the browser:** A simple chat interface. At the top — a field for entering a question, below — the dialog history. There is also a `top-k` slider — it controls how many fragments from the knowledge base the system uses for an answer (the more, the fuller the answer, but the slower) — and an **"Answer language"** switch.

> [i] **"Answer language" switch (🌐 Auto / 🇷🇺 Russian / 🇬🇧 English).** Controls the
> language the LLM **writes the answer** in:
> - **Auto** (default) — answer in the language of the question;
> - **Russian / English** — answer forced into the chosen language, even if the
>   question and the retrieved sources are in another language.
>
> This does not affect **source retrieval** — cross-language search is handled by a
> separate mechanism (dual-query, see 9.6): sources are found in both languages
> regardless of the chosen answer language.

Try asking your first question! For example:

- "What topics are discussed in my documents?"
- "List the key conclusions from the reports"
- "What is the main conclusion of the articles about CO2 injection?"

> ✅ **This is normal:** The first answer may appear after 15–30 seconds — the model is "warming up." Subsequent answers will be faster (5–15 seconds).

> [!] **Important:** The chat interface works while the terminal with the `python chat_ui.py` command is open. Do not close this terminal! If you need to do something else in the terminal — open a **new** terminal window (Ctrl+Alt+T).

---

## Section 4. Auto-Starting the Watcher

---

### 4.1 What the Watcher Does

The watcher (`watcher.py`) is a program that constantly "watches" your archive folder. Imagine a guard on duty at the entrance to a library. As soon as a new book is brought in, he immediately registers it: enters it in the catalog (ChromaDB) and creates a card (a note in Obsidian). You don't need to run `ingest.py` and `doc_to_obsidian.py` manually each time — the watcher does this automatically.

Technically, the watcher works as a **system service** (*systemd service*). Systemd is the service management system in Linux: it can start programs at computer startup, restart them on errors, and keep logs of their operation.

---

### 4.2 Installing as a Service

To install the watcher as a system service, we use a ready-made script:

```bash
cd ~/KMS/rag_system
bash install_service.sh
```

> **What happens automatically during script execution:**
> 1. A service configuration file is created in `~/.config/systemd/user/rag-watcher.service`
> 2. Systemd re-reads the list of services (`systemctl --user daemon-reload`)
> 3. The service is enabled (its autostart at login is permitted)
> 4. The service is started immediately

> **[>>] What you'll see:**
> ```
> Installing RAG Watcher service...
> Created: ~/.config/systemd/user/rag-watcher.service
> Reloading systemd daemon...
> Enabling service...
> Starting service...
>
> ✓ Service installed and running!
> Check status with: systemctl --user status rag-watcher
> ```

---

### 4.3 Managing the Service

Now you have a set of commands for managing the watcher:

**Check whether the service is running:**

```bash
systemctl --user status rag-watcher
```

> **[>>] What you'll see if the service is running:**
> ```
> ● rag-watcher.service - RAG Watcher Service
>      Loaded: loaded (/home/username/.config/systemd/user/rag-watcher.service; enabled)
>      Active: active (running) since Mon 2024-01-15 10:23:45 MSK; 5min ago
>    Main PID: 12345 (python)
>    ...
> ```
> The key phrase is `active (running)`. The green dot (●) also means everything is fine.

**Stop the service** (for example, if you need to make changes):

```bash
systemctl --user stop rag-watcher
```

**Start the service again:**

```bash
systemctl --user start rag-watcher
```

**Watch the logs in real time** (the `-f` flag means *follow*, i.e., show new lines as they appear):

```bash
journalctl --user -u rag-watcher -f
```

> **[>>] What you'll see:**
> ```
> Jan 15 10:23:45 computer python[12345]: Watching directory: /home/username/KMS/archive
> Jan 15 10:23:45 computer python[12345]: Ready. Waiting for new files...
> ```
> When a new document appears, lines about its processing will be shown here in real time. To exit log-viewing mode, press **Ctrl+C**.

> [i] **Tip:** The command `journalctl --user -u rag-watcher -n 50` (without the `-f` flag) can be used to view the last 50 lines of the log without "sticking" to it. This is convenient for a quick check of what happened recently.

---

### 4.4 Verifying the Watcher Works

Let's make sure everything works in practice:

1. Make sure the service is running: `systemctl --user status rag-watcher`
2. Open a second terminal for monitoring: `journalctl --user -u rag-watcher -f`
3. In the first terminal, copy a new document into the archive:

```bash
cp ~/Downloads/test_article.pdf ~/KMS/archive/
```

4. Wait 30–60 seconds and watch the second terminal.

> **[>>] What you'll see in the logs:**
> ```
> Detected new file: test_article.pdf
> Running ingestion...
>   Extracting text... done
>   Creating embeddings... done
>   Stored in ChromaDB.
> Running doc_to_obsidian...
>   Generating summary... done
>   Created note: ~/KMS/notes/Articles/test_article.md
> Done processing test_article.pdf
> ```

5. Open Obsidian and press Ctrl+R to refresh — a new note should appear.

---

### 4.5 Working with a USB Drive

> [!] **Important:** If you use a USB drive as document storage, it is recommended to **connect it before starting the computer** or **before logging in**. This guarantees that the drive will be mounted before the watcher begins work.

**If you connected the USB after the computer was already running:**

The system will automatically mount the drive — usually at `/run/media/$USER/DISK_NAME` (on some systems — at `/media/$USER/DISK_NAME`). The symbolic link `~/KMS/archive` will "come alive" automatically. Within ~30 seconds the watcher will restart its monitoring **and perform a catch-up scan**: files added to the drive while it was disconnected will be automatically indexed and get notes. No duplicates are created in the process — indexing is verified by content (hash), and notes by the `source_file` field.

> [i] **Tip:** the watcher monitors the folder in polling mode (rather than via inotify) — this is exactly why it reliably sees changes on USB/NTFS and through a symbolic link.

Check that the link works:

```bash
ls ~/KMS/archive
```

> **[>>] What you'll see:** A list of files on your USB drive. If you see an error `No such file or directory` or `Too many levels of symbolic links` — the USB is not mounted. Try ejecting and reconnecting the drive.

**If you need to restart the watcher** after connecting USB:

```bash
systemctl --user restart rag-watcher
```

> [!] **If the drive won't mount** (for NTFS — an error like `wrong fs type, bad option, bad superblock`): the volume is marked as "dirty" (it was ejected incorrectly or was used in Windows). Fix the flag and reconnect the drive:
> ```bash
> lsblk                       # find the disk partition, e.g. /dev/sdb2
> sudo ntfsfix /dev/sdb2
> ```
> After that, eject and re-insert the drive — it will mount normally.

> [i] **Autostart without logging in.** By default, a user service runs only while you are logged into a graphical session. To make the watcher start at computer boot and keep running after you log out, enable "linger" (once):
> ```bash
> loginctl enable-linger $USER
> ```

---

## Section 5. Daily Use

After the initial setup, the system requires minimal maintenance. This section describes the typical workflow.

---

### 5.1 Adding New Documents

When you find new material, simply add it to the archive in any supported format. The system will do the rest itself (if the watcher is running).

**Supported formats:** PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT

**Method 1: Through the file manager**

Open the file manager, find the file, drag (or copy/paste) it into the `~/KMS/archive` folder. Done.

**Method 2: Through the terminal**

```bash
cp ~/Downloads/new_article.pdf ~/KMS/archive/
cp ~/Downloads/report.docx ~/KMS/archive/
cp ~/Downloads/data.xlsx ~/KMS/archive/
```

**Method 3: Organizing into subfolders**

The system supports nested folders in the archive. You can organize documents by topic, type, or year:

```bash
mkdir -p ~/KMS/archive/CO2_storage
mkdir -p ~/KMS/archive/Reports
cp ~/Downloads/co2_paper.pdf ~/KMS/archive/CO2_storage/
cp ~/Downloads/quarterly.xlsx ~/KMS/archive/Reports/
```

The watcher tracks all subfolders inside `~/KMS/archive`, recursively.

> [i] **Tip:** Files with formats not in the list `.pdf .docx .doc .txt .md .xlsx .csv .pptx .odt` will be silently ignored — the system will not throw an error, it will simply skip such a file.

After copying a file, wait 1–3 minutes and check for the note appearing in Obsidian (Ctrl+R to refresh the file tree).

> [i] **Tip:** If you add many documents at once (for example, 20–30 of them), give the system time to process them. The watcher processes files sequentially, roughly 1–3 minutes per file. You can monitor progress via: `journalctl --user -u rag-watcher -f`

---

### 5.2 Working with Obsidian

**Viewing a document note**

Open Obsidian and find the `Articles` folder in the left panel. Click any note. You will see a structured document roughly like this:

```markdown
---
title: "Enhanced Oil Recovery Using CO2 Injection in Carbonate Reservoirs"
authors: ["Smith J.", "Brown A."]
year: 2023
doi: "10.1016/j.petrol.2023.01.001"
tags: [auto/co2-injection, auto/eor, auto/carbonate-reservoir]
source: "article_1.pdf"
file_type: PDF
---

## Summary

The article investigates the effectiveness of CO₂ injection for enhanced oil recovery in carbonate reservoirs...

## Key Conclusions

- CO₂ injection increases oil recovery by 12–18% under conditions of...
- Mineral trapping of CO₂ is most effective at...

## Related Topics

[[CO2 Sequestration]] | [[Carbonate Reservoirs]] | [[EOR Methods]]
```

**Link graph**

Press Ctrl+G to open the graph. The more documents in your archive, the more valuable the graph:
- **Large nodes** — notes with many connections (important topics or authors).
- **Clusters** — groups of documents on adjacent topics.
- **Bridges** — documents connecting different topical clusters (often the most interesting for reviews).

**Searching by tags**

Click a tag in any note (for example, `#auto/co2-injection`) — a list of all notes with this tag will open. This is a powerful tool for topical search.

**Tags with the `auto/` prefix**

All tags created automatically by the system have the `auto/` prefix. This makes it easy to distinguish automatically assigned tags from those you added manually. You can add your own tags directly in Obsidian notes, and they will not be overwritten on reprocessing.

---

### 5.3 Questions via the Chat Interface

Launch the chat:

```bash
cd ~/KMS/rag_system && source .venv/bin/activate && python chat_ui.py
```

Open `http://127.0.0.1:7860` in a browser.

**Tips for phrasing questions:**

Good questions are specific and have context:

- ❌ Bad: "What is CO2?"
- ✅ Good: "What is the role of CO2 in mineral trapping in carbonate reservoirs, according to the articles in my database?"

- ❌ Bad: "Tell me about oil"
- ✅ Good: "What enhanced oil recovery methods are mentioned in the articles from 2020–2023?"

- ✅ Good: "List all authors who studied the topic of CO2 mineral trapping"
- ✅ Good: "What contradictions exist between the articles on water injection and CO2 injection?"
- ✅ Good: "Summarize the key findings about permeability in tight reservoirs"

**The top-k parameter:**

If there is a `top-k` slider in the interface, it controls the number of knowledge base fragments the system uses to form an answer:
- **top-k = 3** — fast answer, based on the 3 most relevant fragments. Suitable for clear questions.
- **top-k = 7–10** — a fuller answer covering more material. Takes more time. Suitable for summarizing questions.

---

### 5.4 Questions from the Command Line

If you don't need a browser, you can ask questions directly from the terminal:

```bash
python rag_engine.py "What is the role of calcite in CO2 mineral trapping?"
```

> **[>>] What you'll see:**
> ```
> Searching knowledge base...
> Found 5 relevant chunks from 3 documents.
>
> Generating answer...
>
> Calcite plays a key role in the process of CO₂ mineral trapping...
> [followed by a detailed answer]
>
> Sources:
>   - article_1.pdf (pages 12-14)
>   - review_2023.pdf (pages 5-7)
>   - article_3.pdf (page 22)
> ```

To get knowledge base statistics:

```bash
python rag_engine.py --stats
```

> **[>>] What you'll see:**
> ```
> Knowledge Base Statistics
> ─────────────────────────
> Total documents indexed:  47
> Total chunks in ChromaDB: 14,832
> Embedding model:          intfloat/multilingual-e5-large
> LLM provider:             ollama
> LLM model:                qwen3.5:latest
> Last updated:             2026-01-15 14:23:11
> Archive size:             2.3 GB (47 files)
> ChromaDB size:            1.1 GB
> ```

---

### 5.5 Updating the Tag Taxonomy

Over time, hundreds of automatically created tags will accumulate in your archive. It is useful to periodically check which tags occur most often and add the most popular ones to the "core" taxonomy.

Let's look at the most frequent automatic tags:

```bash
grep -r "auto/" ~/KMS/notes/ | grep "tags:" | sort | uniq -c | sort -rn | head -20
```

Let's break down this command piece by piece:
- `grep -r "auto/" ~/KMS/notes/` — recursively search for lines containing `auto/` in all notes.
- `| grep "tags:"` — from those, keep only lines with tags (in the metadata block).
- `| sort` — sort to prepare for the next step.
- `| uniq -c` — count the number of identical lines.
- `| sort -rn` — sort in descending order by number (-r reverse, -n numeric order).
- `| head -20` — take only the first 20 results.

> **[>>] What you'll see:**
> ```
>      23 tags: [auto/co2-injection, ...
>      19 tags: [auto/reservoir-simulation, ...
>      17 tags: [auto/eor, ...
>      15 tags: [auto/carbonate-reservoir, ...
>      12 tags: [auto/permeability, ...
>      ...
> ```

See tags that occur more than 10 times? They can be added to `config.py` as "core tags" — this will improve the quality of automatic classification of new documents.

Open the config:

```bash
nano ~/KMS/rag_system/config.py
```

Find the `TAXONOMY` section (Ctrl+W to search) and add the frequent tags to the list. Save the file (Ctrl+X → Y → Enter).

If you want to recreate all notes with the new tags:

```bash
cd ~/KMS/rag_system
source .venv/bin/activate
python doc_to_obsidian.py --force
```

> [!] **Important:** The `--force` flag recreates all Obsidian notes (without it, a repeat run skips already-processed files — by the `source_file` field, so no duplicates arise). If you manually added anything to the automatic notes, save those edits separately before running with `--force` — it will overwrite the content.

---

## Section 6. Troubleshooting

This section collects the most frequently encountered problems and ways to solve them. If your situation is not described here — look in the system logs (`tail -f ~/KMS/rag_system/logs/rag_system.log`) for error details.

---

### 6.1 "command not found" When Running Python Scripts

**Symptom:**

```
bash: python: command not found
```

or

```
ModuleNotFoundError: No module named 'chromadb'
```

**Cause:** The virtual environment is not activated.

**Solution:**

```bash
source ~/KMS/rag_system/.venv/bin/activate
```

After this, `(.venv)` will appear at the beginning of the line and all commands will work. You need to do this every time you **open a new terminal**.

> [i] **Tip:** To avoid forgetting about activation, you can add an alias. Open `~/.bashrc` (the terminal configuration) and add to the end the line:
> ```bash
> alias rag='cd ~/KMS/rag_system && source .venv/bin/activate'
> ```
> Now it is enough to type `rag` in any terminal — and you will be in the right folder with the activated environment.

---

### 6.2 "Ollama unavailable" / "Connection refused"

**Symptom:**

```
Error: Could not connect to Ollama at http://localhost:11434
Connection refused
```

**Cause:** The Ollama service is not running.

**Solution:**

```bash
ollama serve
```

> **[>>] What you'll see:**
> ```
> 2024/01/15 10:23:45 routes.go:1007: Listening on 127.0.0.1:11434 (version 0.1.17)
> ```
> Leave this terminal open (or run `ollama serve &` with the `&` symbol to run in the background) and repeat your command.

> [i] **Tip:** Usually Ollama starts automatically at system startup. If this happens regularly, try:
> ```bash
> sudo systemctl enable ollama
> sudo systemctl start ollama
> ```

---

### 6.3 "Model not found"

**Symptom:**

```
Error: model 'mistral' not found
```

**Solution:**

First, let's see which models are available:

```bash
ollama list
```

If the model is not in the list, download it:

```bash
ollama pull mistral
```

If the list is empty, Ollama may have been recently reinstalled or the data was deleted. Download the needed model again.

---

### 6.4 Poor-Quality Answers in Russian

**Symptom:** The model answers a Russian query very briefly, mixes languages, or makes gross grammatical errors.

**Cause:** The `mistral` model, although it understands Russian, works better with English. For better quality in Russian, the models `qwen2.5:7b` or `llama3.1:8b` are recommended.

> [!] **Important:** To run `llama3.1:8b` you need at least **16 GB of RAM**. Check: `free -h` — in the `Mem:` line, look at the `total` column.

Let's download the recommended model (~5 GB file):

```bash
ollama pull qwen2.5:7b
```

> ✅ **This is normal:** The download will take 15–30 minutes.

After downloading, update the config:

```bash
nano ~/KMS/rag_system/config.py
```

Find the lines and change them to:

```python
OLLAMA_MODEL: str = "qwen2.5:7b"
LLM_PROVIDER: str = "ollama"
LLM_MODEL:    str = "qwen2.5:7b"
```

Save (Ctrl+X → Y → Enter). Restart the chat interface or rag_engine — the changes will apply automatically.

---

### 6.5 A Document Is Not Indexed

**Variant A: Scanned PDF**

**Symptom:** After adding a PDF file, the system outputs:

```
Warning: article_name.pdf - No text extracted (0 characters)
Skipping: file may be a scanned document.
```

**Cause:** Some PDFs are just scans of pages (images); they have no "real" text, only pictures. Standard text-extraction tools cannot process them.

**How to tell:** Try opening the PDF in any viewer and selecting text with the mouse. If you can't — the document is scanned.

**What to do:**

You need OCR (*Optical Character Recognition*) — converting images of text into real text. Install the `ocrmypdf` utility:

```bash
sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-rus -y
```

Process the file (this will create a new PDF with a text layer):

```bash
ocrmypdf -l rus+eng ~/KMS/archive/scanned_article.pdf ~/KMS/archive/scanned_article_ocr.pdf
```

Now you can index the processed file:

```bash
cd ~/KMS/rag_system && source .venv/bin/activate
python ingest.py            # reindex the archive: the new OCR file is added, the rest is skipped (dedup by hash)
python doc_to_obsidian.py   # a note for the new file (already-processed ones are skipped by source_file)
```

> [i] **Tip:** The `-l rus+eng` flag tells OCR to use both languages. If the document is only in English, use `-l eng` — processing will be more accurate and faster.

**Variant B: A DOC file is not recognized**

**Symptom:**
```
Warning: document.doc - extraction failed, text empty
```

**Cause:** For the old `.doc` format, the system uses LibreOffice. If LibreOffice is not installed — processing will not go through.

**Solution:**
```bash
sudo apt install libreoffice antiword -y
# Restart the watcher:
systemctl --user restart rag-watcher
```

After that, copy the file again (or the watcher will pick it up itself on restart).

**Variant C: Unsupported format**

Files with extensions not in the list `.pdf .docx .doc .txt .md .xlsx .csv .pptx .odt` are silently ignored — this is normal behavior, not an error.

---

### 6.6 The Watcher Does Not See New Files

**Step 1:** Let's check the service status:

```bash
systemctl --user status rag-watcher
```

If you see `inactive (dead)` or `failed` — the service is not running.

**Step 2:** Let's look at the last lines of the log:

```bash
journalctl --user -u rag-watcher -n 50
```

Read the last lines — they should contain information about the error.

**Step 3:** Let's restart the service:

```bash
systemctl --user restart rag-watcher
```

**If the error recurs:**

A common cause is that the Python virtual environment is not found. Check that the path in the service file is correct:

```bash
cat ~/.config/systemd/user/rag-watcher.service
```

In the `ExecStart=` line there should be a full path to Python in the virtual environment like:
```
ExecStart=/home/username/KMS/rag_system/.venv/bin/python watcher.py
```

If the username differs from `username` — edit the service file, then:

```bash
systemctl --user daemon-reload
systemctl --user restart rag-watcher
```

---

### 6.7 No Disk Space

**Symptom:** Errors like `No space left on device` or the system runs slowly.

**Diagnosis:**

Let's see how much space there is on the disks in general:

```bash
df -h
```

> **[>>] What you'll see:**
> ```
> Filesystem      Size  Used Avail Use% Mounted on
> /dev/sda2       234G  187G   35G  85% /
> /dev/sdb1        15G  8.2G  6.8G  55% /media/username/MY_USB
> ```
> Pay attention to the `Use%` column. If it is more than 90% — you need to free up space.

Let's see how much the ChromaDB database takes up:

```bash
du -sh ~/KMS/rag_system/chroma_db/
```

> **[>>] What you'll see:**
> ```
> 2.3G    /home/username/KMS/rag_system/chroma_db/
> ```

The ChromaDB database grows as documents are added. Roughly: 1 GB of source documents → 0.5 GB of ChromaDB.

**Solution options:**

1. **Free up space:** Delete unneeded files from Downloads and other folders.
2. **Move ChromaDB to another disk:** In `config.py`, the database parameter is called `CHROMA_PERSIST_DIR` (by default — the `chroma_db` folder inside `rag_system`). To move the database, replace the line `CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"` with an absolute path, for example `CHROMA_PERSIST_DIR = Path("/mnt/big_disk/chroma_db")`.
3. **Clear the pip cache:** `pip cache purge` (will free 100–500 MB).
4. **Clear old journals:** `journalctl --user --vacuum-size=100M` (will keep only the last 100 MB of logs).

---

### 6.8 Forgot How to Launch the Chat

This is the most frequent question! Here is the full command, which you can copy straight from this guide:

```bash
cd ~/KMS/rag_system && source .venv/bin/activate && python chat_ui.py
```

Three commands joined by `&&` (run the next one only if the previous succeeded). After launching, open a browser and go to `http://127.0.0.1:7860`.

> [i] **Tip:** Add this command as an alias in `~/.bashrc`:
> ```bash
> echo "alias ragchat='cd ~/KMS/rag_system && source .venv/bin/activate && python chat_ui.py'" >> ~/.bashrc
> source ~/.bashrc
> ```
> After this, it is enough to type `ragchat` in any terminal.

---

### 6.9 Ollama Runs Very Slowly

**Symptom:** An answer to a simple question takes more than 2–3 minutes.

**Cause:** The system generates answers on the CPU (processor), not on the GPU (video card). For language models, the GPU provides a 5–20× speedup.

**Let's check whether Ollama uses the GPU:**

```bash
ollama ps
```

> **[>>] What you'll see:**
> ```
> NAME            ID              SIZE    PROCESSOR    UNTIL
> mistral:latest  f974a74358d6    5.4 GB  100% GPU     4 minutes from now
> ```
> If the `PROCESSOR` column says `100% CPU` or `0% GPU` — the model is running without GPU.

**If you have an NVIDIA GPU:**

Install CUDA following NVIDIA's official documentation for your Ubuntu version. After installing CUDA, Ollama will automatically start using the GPU.

**If there is no GPU or it is integrated Intel/AMD:**

Unfortunately, significant acceleration cannot be achieved. Consider two options:

1. Use a lighter model:
```bash
ollama pull mistral:7b-instruct-q4_0
```
In the config, specify: `OLLAMA_MODEL: str = "mistral:7b-instruct-q4_0"` — this is a more "compressed" version of the model, works faster, but is slightly worse in quality.

2. **Switch to the Groq cloud provider** — it is free and works significantly faster. More on this in Section 7.

---

### 6.10 Error When Installing Dependencies

**Symptom:**

```
error: legacy-install-failure
× Encountered error while trying to install package.
╰─> chroma-hnswlib
```

**Cause:** There is no ready-made package for your Python version, and `chroma-hnswlib` tries to build from source. **The most common cause is a too-new Python (3.13+):** there are no ready-made ChromaDB packages for it yet.

**Solution:**

If you have Python **3.13 or newer** — recreate the environment with Python 3.12 (see also Section 1.3):
```bash
sudo apt install python3.12 python3.12-venv -y
cd ~/KMS/rag_system && rm -rf .venv && python3.12 -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt
```

If Python is 3.10–3.12, but build tools are missing:
```bash
sudo apt install python3-dev build-essential cmake -y
pip install -r requirements.txt
```

---

### 6.11 Speeding Up Indexing with a Video Card (GPU / NVIDIA CUDA)

By default, the system installs the CPU build of PyTorch — it works everywhere, but creating embeddings is slow (especially with the `e5-large` model). If you have an NVIDIA video card (for example, GeForce RTX 30xx/40xx), you can install the CUDA build of PyTorch and speed up indexing **by about 20–25×**.

**Step 1. Check the video card and driver:**
```bash
nvidia-smi
```
You will see the card model and a line `CUDA Version: 12.x` (or newer). If the command is missing — install the proprietary NVIDIA driver via "Software & Updates" → "Additional Drivers".

**Step 2. Replace torch with the CUDA build** (in the activated environment):
```bash
cd ~/KMS/rag_system && source .venv/bin/activate
pip install --force-reinstall --index-url https://download.pytorch.org/whl/cu128 torch
```
> [i] `cu128` is CUDA 12.8; suitable for modern drivers. The download is large (~3 GB: torch itself + cuDNN/cuBLAS libraries). If you use `uv`: `uv pip install --reinstall-package torch --index-url https://download.pytorch.org/whl/cu128 torch`.

**Step 3. Check that the GPU is visible:**
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
It should output `True` and the name of your card.

After this, `python ingest.py` and the watcher automatically use the GPU — no settings need changing (`sentence-transformers` chooses CUDA itself).

> [!] **About video memory (VRAM).** Embeddings and the Ollama language model share the same video memory. On **8 GB** cards, their joint operation is possible but "tight." Therefore the chat interface (`chat_ui.py`) deliberately computes embeddings **on the CPU** (embedding one short question is instant anyway), leaving all the video memory for the LLM — so answers are generated faster. Batch indexing still runs on the GPU. If you want to use the GPU in the chat too — run `CUDA_VISIBLE_DEVICES=0 python chat_ui.py`.

> [i] **Tip:** on the GPU, a full reindex (`python ingest.py --reset`) runs tens of times faster than on the CPU (in our test on an RTX 3070 — about 26×).

---

## Section 7. Managing LLM Providers

RAG system version 5.0 (v4.2) supports **5 providers** through a single interface — the `llm_provider.py` file. This means you can switch between the local Ollama, the cloud-based Groq and DeepSeek, the OpenRouter aggregator, and the local LM Studio — all through three lines in `config.py`, without changing the rest of the code.

**Why does this matter?**

- No internet, or full confidentiality needed → **ollama** (local, free)
- Need powerful models without a GPU → **groq** (cloud, free, up to 14,400 requests/day)
- Need the smartest reasoning → **deepseek** (cloud, cheap, $0.07/1M tokens)
- Want to choose from 50+ models → **openrouter** (free options available)
- Want a nice GUI + locality → **lmstudio** (local, free)

> [i] **"Reasoning" models (qwen3, deepseek-r1, and the like).** They first generate a hidden "chain of reasoning." The system **automatically disables** this mode (`think: false`) when contacting Ollama — otherwise the model spends its entire token budget on "reasoning" and returns an empty answer. If, after switching to an ollama model, answers suddenly become empty ("Ollama returned an empty answer") — it is almost certainly a "thinking" model; make sure you have the current `llm_provider.py` and `doc_to_obsidian.py` (this fix is already in them).

### Provider Table

| Provider | Description | API key | Free |
|-----------|----------|----------|-----------|
| `ollama` | Local Ollama (already installed) | Not needed | Yes |
| `groq` | Groq Cloud — fast LLMs in the cloud | console.groq.com/keys | 14,400 req/day |
| `deepseek` | DeepSeek API | platform.deepseek.com | Paid ($0.07/1M) |
| `openrouter` | 50+ models from various providers | openrouter.ai/settings/keys | Free options available |
| `lmstudio` | Local LM Studio (GUI) | Not needed | Yes |

---

### 7.1 Switching the Provider

Open the configuration file:

```bash
nano ~/KMS/rag_system/config.py
```

Find and edit **three lines** (Ctrl+W → `LLM_PROVIDER`):

```python
LLM_PROVIDER: str = "ollama"
LLM_MODEL:    str = "qwen2.5:7b"
LLM_API_KEY:  str = ""
```

Save (Ctrl+X → Y → Enter) and restart the chat or script.

#### Configuration examples for each provider

**Ollama (local, default):**
```python
LLM_PROVIDER: str = "ollama"
LLM_MODEL:    str = "qwen2.5:7b"
LLM_API_KEY:  str = ""
```
> [i] Before use, make sure the model is downloaded: `ollama pull qwen2.5:7b`

---

**Groq (cloud, free):**
```python
LLM_PROVIDER: str = "groq"
LLM_MODEL:    str = "llama-3.3-70b-versatile"
LLM_API_KEY:  str = "gsk_YOUR_KEY_HERE"
```
> Get a free API key: [console.groq.com/keys](https://console.groq.com/keys)
>
> [i] Groq is a cloud service that provides powerful models with very high generation speed. Free tier limit: 14,400 requests per day. Data is sent to Groq's servers (USA).

---

**DeepSeek (cloud, paid):**
```python
LLM_PROVIDER: str = "deepseek"
LLM_MODEL:    str = "deepseek-chat"
LLM_API_KEY:  str = "sk-YOUR_KEY_HERE"
```
> Get a key and top up the balance: [platform.deepseek.com](https://platform.deepseek.com)
>
> [i] DeepSeek is a Chinese provider with very low prices ($0.07 per 1 million tokens for deepseek-chat). It handles technical texts excellently. For tasks requiring deep reasoning, use the `deepseek-reasoner` model.

---

**OpenRouter (50+ models, free options available):**
```python
LLM_PROVIDER: str = "openrouter"
LLM_MODEL:    str = "qwen/qwen3-14b:free"
LLM_API_KEY:  str = "sk-or-YOUR_KEY_HERE"
```
> Get a key: [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys)
>
> [i] OpenRouter is an aggregator that gives access to dozens of models through a single API. Models with the `:free` suffix (for example, `qwen/qwen3-14b:free`, `deepseek/deepseek-r1:free`) are available for free with certain speed limitations.

---

**LM Studio (local, with GUI):**
```python
LLM_PROVIDER: str = "lmstudio"
LLM_MODEL:    str = "qwen2.5-7b-instruct"
LLM_API_KEY:  str = ""
```
> [i] LM Studio is an application with a graphical interface for running local LLMs. Before use: 1) Download LM Studio from [lmstudio.ai](https://lmstudio.ai), 2) Load the needed model through the interface, 3) Start the local server in LM Studio (Local Server menu). The RAG system will connect to it automatically at `http://localhost:1234`.

---

### 7.2 Recommended Models for Oil & Gas Topics

When working with technical, regulatory, and scientific documentation for the oil & gas industry, the following models are recommended:

#### Ollama (local, no internet)

| Model | Size | RAM | Russian quality | Recommendation |
|--------|--------|-----|-------------------|--------------|
| `qwen2.5:7b` | ~5 GB | 8 GB | ★★★★★ | **Recommended** — best balance of quality and speed |
| `qwen2.5:14b` | ~9 GB | 16 GB | ★★★★★ | Better for analyzing long documents |
| `deepseek-r1:7b` | ~5 GB | 8 GB | ★★★★☆ | Good for technical reasoning |
| `mistral` | ~4 GB | 8 GB | ★★★☆☆ | Basic option, suitable for starting out |
| `llama3.1:8b` | ~5 GB | 16 GB | ★★★★☆ | Good Russian, especially for dialogues |

Downloading a model:
```bash
ollama pull qwen2.5:7b
```

#### Groq (cloud, free)

| Model | Description |
|--------|----------|
| `llama-3.3-70b-versatile` | Powerful model for comprehensive analysis |
| `deepseek-r1-distill-llama-70b` | Best for technical reasoning |
| `mixtral-8x7b-32768` | Handles long texts well |

> [i] Groq is especially good if you don't have a powerful GPU but need answers from a large model.

#### OpenRouter (free options)

| Model | Description |
|--------|----------|
| `qwen/qwen3-14b:free` | Excellent Russian, free |
| `deepseek/deepseek-r1:free` | Strong technical reasoning, free |
| `meta-llama/llama-3.3-70b-instruct:free` | Powerful open model, free |

#### DeepSeek (paid, low prices)

| Model | Use |
|--------|------------|
| `deepseek-chat` | Standard questions about documents |
| `deepseek-reasoner` | Complex analysis, comparison, reasoning |

---

### 7.3 Environment Variables

Storing API keys directly in `config.py` is not the best practice (the file may end up in a backup or version control system). The alternative is environment variables.

Add the keys to the `~/.bashrc` file (your terminal's configuration):

```bash
nano ~/.bashrc
```

Add to the end of the file:

```bash
# API keys for RAG KMS
export RAG_GROQ_API_KEY="gsk_your_groq_key"
export RAG_DEEPSEEK_API_KEY="sk-your_deepseek_key"
export RAG_OPENROUTER_API_KEY="sk-or-your_openrouter_key"
```

Save (Ctrl+X → Y → Enter) and activate:

```bash
source ~/.bashrc
```

If the environment variables are set, `llm_provider.py` will automatically pick up the right key — the `LLM_API_KEY` field in `config.py` can be left empty:

```python
LLM_PROVIDER: str = "groq"
LLM_MODEL:    str = "llama-3.3-70b-versatile"
LLM_API_KEY:  str = ""   # ← taken from the RAG_GROQ_API_KEY variable
```

> [!] **Important:** Do not share API keys with anyone. Do not add a `~/.bashrc` file with keys to backups stored in the cloud.

---

### 7.4 Troubleshooting Providers

#### Error 401 (Unauthorized — invalid key)

**Symptom:**
```
Error: 401 Unauthorized
APIError: Invalid API key
```

**What to do:**
1. Check that the key was copied in full (without extra spaces)
2. Make sure the key is active in the provider's account dashboard
3. Check that `LLM_PROVIDER` is correctly specified in `config.py`

**Quick check of a Groq key:**
```bash
curl -s -H "Authorization: Bearer $RAG_GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models | python3 -m json.tool | head -20
```

---

#### Error 429 (Rate Limit — request limit exceeded)

**Symptom:**
```
Error: 429 Too Many Requests
RateLimitError: Rate limit exceeded
```

**What to do:**
- For **Groq**: the free limit is 14,400 requests/day. Wait for the reset (at midnight UTC) or temporarily switch to ollama.
- For **OpenRouter** with free models: add a delay or switch to a paid quota.
- For **DeepSeek**: top up the balance on the platform.

**Temporary switch to Ollama without changing config.py:**
```bash
# Run the script with a different provider (if supported):
LLM_PROVIDER=ollama python rag_engine.py "your question"
```

---

#### Timeout (the provider does not respond)

**Symptom:**
```
Error: ConnectionTimeout
ReadTimeout: The read operation timed out
```

**What to do:**
1. Check the internet connection: `ping api.groq.com`
2. Switch to a local provider (ollama or lmstudio)
3. Try later — there may be temporary problems on the provider's side

---

#### LM Studio does not respond

**Symptom:**
```
Error: Could not connect to LM Studio at http://localhost:1234
```

**What to do:**
1. Make sure LM Studio is running
2. In LM Studio, go to the "Local Server" tab
3. Click the "Start Server" button
4. Make sure the model is loaded (green indicator)

---

## Section 8. Updating Ollama and the LLM

Over time, new versions of Ollama come out with performance improvements, as well as new language models with better quality. This section describes how to safely update everything.

---

### Updating Ollama

To update Ollama to the latest version, use the same command as for the initial installation:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

The script will automatically detect the installed version and update it without affecting the downloaded models.

Check the version after updating:

```bash
ollama --version
```

> **[>>] What you'll see:**
> ```
> ollama version is 0.3.12
> ```

---

### Viewing Installed Models

```bash
ollama list
```

> **[>>] What you'll see:**
> ```
> NAME                    ID              SIZE    MODIFIED
> qwen2.5:7b              a04eb7c1...     4.7 GB  2 weeks ago
> mistral:latest          f974a743...     4.1 GB  1 month ago
> nomic-embed-text:latest 0a109f42...     274 MB  3 weeks ago
> ```

---

### Downloading a New Model

```bash
ollama pull qwen2.5:14b
```

The model will be downloaded and added to the existing ones. After downloading, update `config.py`:

```bash
nano ~/KMS/rag_system/config.py
```

Replace the values:
```python
OLLAMA_MODEL: str = "qwen2.5:14b"
LLM_MODEL:    str = "qwen2.5:14b"
```

---

### Updating an Existing Model

Re-running `ollama pull` updates the model to the latest version:

```bash
ollama pull qwen2.5:7b
```

If the latest version is already installed, you will see:
```
pulling manifest
Up to date.
```

---

### Removing an Old Model

To free up disk space, you can remove models that are no longer used:

```bash
ollama rm mistral
```

> **[>>] What you'll see:**
> ```
> deleted 'mistral'
> ```

> [!] **Important:** Before removing, make sure that `config.py` specifies a different model as the main one.

---

### Managing Models — Summary Table

| Action | Command |
|----------|---------|
| Update Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Check Ollama version | `ollama --version` |
| List installed models | `ollama list` |
| Download a new model | `ollama pull qwen2.5:14b` |
| Update an existing model | `ollama pull qwen2.5:7b` (repeat pull) |
| Remove a model | `ollama rm mistral` |
| Status of running models | `ollama ps` |
| Start the Ollama server | `ollama serve` |
| Check the Ollama API | `curl http://localhost:11434/api/tags` |

---

## Section 9. Connecting Claude Code via MCP (optional)

> **This section is optional.** It describes connecting the RAG system to Claude Code — Anthropic's AI assistant that runs in the terminal. If you use only the web interface (`chat_ui.py`), this section can be skipped. Integration with Claude Code provides additional capabilities: Claude can decide on its own when to query your knowledge base, combine search results with its own knowledge, and work in the context of a specific project.

---

### 9.0 What Claude Code and MCP Are

#### Claude Code — an AI assistant right in the terminal

**Claude Code** is a tool from Anthropic that lets you communicate with the Claude AI model directly from the command line (terminal). You simply write a question in Russian or English, and Claude answers — like an experienced colleague who knows everything and is always at hand.

Unlike the web interface, Claude Code can:
- Read files on your computer
- Run commands in the terminal
- Call external tools (including your RAG system)
- Work in the context of a specific project

#### MCP — a "power socket" for connecting tools

**MCP (Model Context Protocol)** is an open protocol developed by Anthropic that allows Claude Code to connect to external tools and data sources. Think of it as a standard "power socket": any tool written to the MCP standard can be "plugged into" Claude Code, and it will immediately start using it.

A simple analogy: if Claude Code is your smart assistant, then MCP is the phone over which it can call the library (your RAG system) and ask for the needed information.

#### What the RAG + Claude Code integration provides

Without integration:
- Claude answers only from its general knowledge
- It does not know about your specific documents, regulations, reports
- It may "hallucinate" technical details

With RAG integration:
- Claude searches for answers in **your** documents: PDF, DOCX, XLSX, and others
- Cites specific sources from the archive
- Answers taking into account your regulations, standards, and reports
- You can ask in Russian on oil & gas topics

#### Table: 4 MCP server tools

| Tool | What it does | When to use |
|---|---|---|
| `search_knowledge_base` | Semantic search of documents + answer generation via LLM | Main tool: questions about document content |
| `list_documents` | Shows a list of all indexed files | When you want to know what is in the database at all |
| `get_document_info` | Detailed information about a specific file | When you need details: date, size, number of chunks |
| `get_stats` | Knowledge base statistics and LLM provider status | Diagnostics: is everything working |

#### How the system works

```
You (a question in Russian)
        │
        ▼
┌───────────────────┐
│   Claude Code     │  ← AI assistant in the terminal
│  (claude CLI)     │
└────────┬──────────┘
         │  MCP protocol (JSON-RPC over stdio)
         ▼
┌───────────────────┐
│  mcp_rag_server   │  ← Python script, the "bridge" between Claude and RAG
│  .py              │
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ChromaDB│ │ LLM provider │  ← Vector database + LLM (Ollama/Groq/...)
│(search)│ │ (answer)     │
└────────┘ └──────────────┘
         │
         ▼
┌───────────────────┐
│   Your documents  │  ← PDF, DOCX, XLSX, TXT...
│   ~/KMS/archive/  │
└───────────────────┘
```

**How it works step by step:**
1. You ask Claude Code a question in the terminal
2. Claude understands that it needs to consult the knowledge base and calls `search_knowledge_base`
3. The MCP server searches for relevant fragments in ChromaDB
4. The found fragments are sent to the LLM provider to generate an answer
5. The ready answer with citations is returned to you through Claude Code

---

### 9.1 Installing Claude Code

#### Step 9.1.1: Check for Node.js

Claude Code is an npm package, so it needs Node.js (version 18 or newer) to run.

Open the terminal and run:

```bash
node --version
```

**[>>] What you'll see if Node.js is installed:**
```
v20.11.0
```

If the command is not found (`command not found`), install Node.js:

```bash
# For Ubuntu/Debian:
sudo apt update
sudo apt install nodejs npm -y

# Check after installation:
node --version
npm --version
```

**[>>] What you should get:**
```
v20.11.0
10.2.3
```

> **Note:** Version numbers may differ — that's normal. The main thing is that Node.js is version 18 or higher.

---

#### Step 9.1.2: Install Claude Code via npm

Run in the terminal:

```bash
npm install -g @anthropic-ai/claude-code
```

The `-g` flag means "global installation" — Claude Code will be available from any folder.

**[>>] What you'll see during installation:**
```
added 247 packages in 15s
found 0 vulnerabilities
```

> **If an EACCES error appears (no permissions):** This means the npm folder belongs to root. Fix with the command:
> ```bash
> sudo npm install -g @anthropic-ai/claude-code
> ```

---

#### Step 9.1.3: Authorization

Claude Code requires authentication through Anthropic. There are two ways:

**Method A: Interactive login (recommended)**

```bash
claude login
```

An Anthropic authorization page will open in the browser. Log into your account or create a new one at [console.anthropic.com](https://console.anthropic.com).

**Method B: API key (if there is no browser or automation is needed)**

1. Get an API key at [console.anthropic.com/settings/api-keys](https://console.anthropic.com/settings/api-keys)
2. Add it to the environment variables:

```bash
# Add to ~/.bashrc for permanent storage:
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

> [!] **Important:** Do not share the API key with other people. This is your personal access key.

---

#### Step 9.1.4: Verifying the Installation

```bash
claude --version
```

**[>>] What you should get:**
```
Claude Code 1.x.x
```

An additional check — try asking a simple question:

```bash
claude "Hi! What is 2+2?"
```

**[>>] Expected answer:**
```
Hi! 2+2 = 4.
```

If everything works — Claude Code is successfully installed. Proceed to the next section.

---

### 9.2 Preparing the MCP Server

#### Step 9.2.1: Make sure RAG system v5.0 is installed

Let's check that all the necessary components are in place:

```bash
# Check the structure of the KMS folder:
ls ~/KMS/
# Expected output:
# archive/  notes/  rag_system/

# Check the contents of rag_system:
ls ~/KMS/rag_system/

# Check whether Ollama is running (if you use Ollama):
ollama list
```

Let's check whether the virtual environment is active:

```bash
source ~/KMS/rag_system/.venv/bin/activate
python --version
```

**[>>] Expected output:**
```
Python 3.11.x
```

---

#### Step 9.2.2: Check for the mcp_rag_server.py file

```bash
ls -la ~/KMS/rag_system/mcp_rag_server.py
```

**[>>] What you should get:**
```
-rw-r--r-- 1 USERNAME USERNAME 8192 Jan 15 14:30 /home/USERNAME/KMS/rag_system/mcp_rag_server.py
```

If the file is there — great, it was already created as part of the RAG system v5.0 installation. If the file is not found — refer to the RAG system installation documentation.

---

#### Step 9.2.3: Test-run the server manually

Let's run the server manually to make sure there are no errors:

```bash
# Activate the environment and start the server:
source ~/KMS/rag_system/.venv/bin/activate
cd ~/KMS/rag_system/
python mcp_rag_server.py
```

**[>>] What you'll see (diagnostic messages):**
```
[INFO] RAG MCP Server starting...
[INFO] Loading embedding model...
[INFO] ChromaDB connected: /home/USERNAME/KMS/rag_system/chroma_db
[INFO] Documents in index: 47
[INFO] MCP server ready. Waiting for connections...
```

> [!] **Important:** After this the server will wait for incoming messages. It is not "hanging" — this is normal behavior for an MCP server. Stop it by pressing `Ctrl+C`.

> **Note about stderr/stdout:** The MCP server deliberately writes all status messages (logs) to `stderr`, while `stdout` is reserved exclusively for transmitting data over the MCP protocol. This is important — if extraneous messages end up in `stdout`, Claude Code will not be able to parse the responses.

---

#### Step 9.2.4: Find the path to the Python interpreter

To configure the configuration file, we need the **full path** to Python.

```bash
source ~/KMS/rag_system/.venv/bin/activate
which python
```

**[>>] Example output:**
```
/home/USERNAME/KMS/rag_system/.venv/bin/python
```

**Find out your USERNAME:**

```bash
echo $USER
```

**[>>] Example output:**
```
ivanov_ap
```

Write down these paths — they will be needed in the next section.

---

### 9.3 Connecting MCP to Claude Code

#### Step 9.3.1: Create the ~/.claude/ directory

```bash
mkdir -p ~/.claude
```

The `-p` flag means "create, even if the folder already exists" — the command is safe to run repeatedly.

**Check:**
```bash
ls -la ~/ | grep .claude
```

**[>>] What you should get:**
```
drwxr-xr-x 2 USERNAME USERNAME 4096 Jan 15 15:00 .claude
```

---

#### Step 9.3.2: Create the mcp_servers.json file

Let's create the configuration file. First, clarify your path to Python (from step 9.2.4).

```bash
# Find out USERNAME again:
echo $USER
# For example: ivanov_ap

# Find out the path to Python:
source ~/KMS/rag_system/.venv/bin/activate && which python
# For example: /home/ivanov_ap/KMS/rag_system/.venv/bin/python
```

Now create the configuration file, **replacing USERNAME with your real login**:

```bash
nano ~/.claude/mcp_servers.json
```

Paste the following content (replace `USERNAME` with your login, obtained with the `echo $USER` command):

```json
{
  "rag_kms": {
    "command": "/home/USERNAME/KMS/rag_system/.venv/bin/python",
    "args": ["/home/USERNAME/KMS/rag_system/mcp_rag_server.py"],
    "cwd": "/home/USERNAME/KMS/rag_system"
  }
}
```

**Example for the user ivanov_ap:**
```json
{
  "rag_kms": {
    "command": "/home/ivanov_ap/KMS/rag_system/.venv/bin/python",
    "args": ["/home/ivanov_ap/KMS/rag_system/mcp_rag_server.py"],
    "cwd": "/home/ivanov_ap/KMS/rag_system"
  }
}
```

Save the file: `Ctrl+O`, then `Enter`, then `Ctrl+X`.

---

#### Step 9.3.3: Check the JSON syntax

JSON is very sensitive to syntax: one extra comma or quote — and the file won't be read. Let's check:

```bash
cat ~/.claude/mcp_servers.json | python3 -m json.tool
```

**[>>] What you should get (the file is correct):**
```json
{
  "rag_kms": {
    "command": "/home/ivanov_ap/KMS/rag_system/.venv/bin/python",
    "args": [
      "/home/ivanov_ap/KMS/rag_system/mcp_rag_server.py"
    ],
    "cwd": "/home/ivanov_ap/KMS/rag_system"
  }
}
```

**If there is an error:**
```
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 4 column 5 (char 87)
```
Open the file again (`nano ~/.claude/mcp_servers.json`) and check the commas and quotes.

---

#### Step 9.3.4: Launch Claude Code and check the tools

```bash
cd ~/KMS
claude
```

After launching, enter the command:

```
/tools
```

**[>>] Expected output — you should see 4 tools from RAG:**

```
Available tools:
...
rag_kms:search_knowledge_base - Semantic search of the knowledge base with answer generation
rag_kms:list_documents         - List of all indexed documents
rag_kms:get_document_info      - Detailed information about a specific document
rag_kms:get_stats              - Knowledge base statistics and LLM provider status
...
```

If the tools appeared — the integration is successfully configured! Proceed to the next section.

> **Don't see the tools?** Go to Section 9.7 — it describes the solution to this problem.

---

### 9.4 First Queries

Launch Claude Code from the project folder:

```bash
cd ~/KMS
claude
```

Now just write questions in natural language. Claude Code will decide on its own when to consult your knowledge base.

---

#### Examples of oil & gas queries

**Query 1: Searching the regulations**
```
What requirements for oil pipeline pressure testing are specified in our regulations?
```

**[>>] What will happen:**
```
Claude Code calls: search_knowledge_base("requirements pressure testing oil pipeline regulation")

Answer:
According to the document "Reglament_TO_nefteprovod_2024.pdf" (page 12):
Oil pipeline pressure testing must be carried out at 1.25 of the working pressure,
duration — at least 24 hours...
```

---

**Query 2: Searching for incident cases**
```
Were there any depressurization incidents at the Zapadnoye field in our reports?
Find all mentions.
```

---

**Query 3: Technical parameters**
```
What technical specifications of the TsNS-180 pumps are specified in the documentation?
```

---

**Query 4: Analysis in English**
```
What are the recommended intervals for pipeline inspection according to our documents?
```

> Claude Code supports queries in Russian and English — use the language in which your documents are written.

---

**Query 5: Comparing data**
```
Compare the well flow rate indicators from the 2023 and 2024 reports.
Is there a declining trend?
```

---

**Query 6: Searching for a specific document**
```
Show me which files we have in the knowledge base. Are there documents on
well logging (GIS)?
```

**[>>] What will happen:**
```
Claude Code calls: list_documents()

Answer:
47 documents found in the knowledge base. GIS files:
- GIS_Otchet_Skvazhina_245_2024.pdf
- Metodika_GIS_interpretaciya.docx
- ...
```

---

#### How Claude Code decides when to use RAG

Claude Code automatically consults the knowledge base when:
- The question concerns specific documents, reports, or regulations
- The question contains the words: "in our documents," "in the regulation," "in the report"
- The question requires precise technical data from your industry

Claude Code does **not** consult RAG when:
- The question is general ("what is pressure?")
- You ask it to write code or text
- The question clearly does not require documents

**Tip:** If you want to guarantee the use of RAG, ask explicitly:
```
Using our knowledge base, find information about...
```

---

#### Example of a complete dialog

```
You: Find the occupational safety requirements for working at heights in the documents

Claude Code: Consulting the knowledge base...
[Call: search_knowledge_base("occupational safety requirements working at heights")]

Found 3 relevant documents:

1. **OT_Reglament_vysotnye_raboty.pdf** (relevance: 94%)
   > "When working at heights above 1.8 meters, a type A or B safety harness
   > must be used according to GOST R 58758-2019..."

2. **Instrukciya_IOT-045-2023.docx** (relevance: 87%)
   > "Before beginning work at heights, the foreman must conduct an
   > unscheduled briefing and fill out a work permit of form ND-3..."

**Final answer:**
According to your corporate documents, the main requirements are as follows:
- Mandatory safety harness at heights from 1.8 m
- Work permit of form ND-3 before starting work
- Unscheduled briefing of the crew...
```

---

### 9.5 Configuring CLAUDE.md

#### What CLAUDE.md is and why it's needed

`CLAUDE.md` is a special file that Claude Code automatically reads when launched from a certain folder. It sets the **context and rules of behavior** for the AI: who you are, what you do, which tools to use by default.

Without `CLAUDE.md`:
- Claude does not know that you work in the oil & gas industry
- It does not know that you have a knowledge base with documents
- It does not know the preferred answer language

With `CLAUDE.md`:
- Claude immediately understands the project context
- Automatically checks the knowledge base for professional questions
- Answers in Russian by default
- Uses the correct terminology

#### Step 9.5.1: Create the ~/KMS/CLAUDE.md file

```bash
nano ~/KMS/CLAUDE.md
```

Paste the following content:

```markdown
# Project context: KMS — Oil & Gas Engineer's Knowledge Base

## About the project
This is the working environment of an oil engineer at JSC "SRI SPA "LUCH" — PB.
The main task is the search and analysis of technical documentation for the oil & gas industry.

## Project structure
- `~/KMS/archive/` — document archive (PDF, DOCX, XLSX, PPTX, TXT, CSV, ODT)
- `~/KMS/notes/` — Obsidian notes in Markdown format
- `~/KMS/rag_system/` — RAG system v5.0 based on ChromaDB

## Knowledge base (RAG system)
You have access to tools through the MCP server `rag_kms`.

**IMPORTANT:** For any question about oil & gas topics, technical
regulations, reports, or documentation — ALWAYS first consult the
knowledge base via `search_knowledge_base`.

Available tools:
- `rag_kms:search_knowledge_base` — the main search tool
- `rag_kms:list_documents` — list of documents in the database
- `rag_kms:get_document_info` — details of a specific file
- `rag_kms:get_stats` — system status

## Document topics
Documents may contain information on the following topics:
- Development and operation of oil and gas fields
- Technical regulations and instructions on OSH and IS
- Well logging (GIS)
- Well testing / hydrodynamic studies (GDIS)
- Pipeline transport of oil and gas
- Geological reports and reserve estimates
- Drilling operations and well completion
- ESP, SRP, AGZU equipment

## Working rules
1. Answer in the language in which the question is asked (by default — Russian)
2. When searching the knowledge base, use top_k=7 for ordinary questions,
   top_k=10-15 for complex analytical queries
3. Always indicate the source (file name) when citing
4. If information is not found in the database — say so directly, do not make things up
5. To check the system state, use `get_stats`

## Answer format
- Technical data — with a reference to the source and page, if available
- Figures and standards — precisely, without rounding
- If multiple sources are found — compare them, indicate discrepancies
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

#### How to launch Claude Code with the project context

Always launch Claude from the `~/KMS` folder:

```bash
cd ~/KMS
claude
```

On launch, you will see confirmation that `CLAUDE.md` is loaded:
```
Loading project context from CLAUDE.md...
Context loaded: KMS — Oil & Gas Engineer's Knowledge Base
```

> [i] **Tip:** Add an alias to `~/.bashrc` for quick launch:
> ```bash
> echo "alias kms='cd ~/KMS && claude'" >> ~/.bashrc
> source ~/.bashrc
> # Now you can launch with a single command:
> kms
> ```

---

### 9.6 Using the Tools Directly

Sometimes it is convenient to call the tools explicitly, without relying on Claude's automatic decision. This is especially useful for fine-tuning the search.

#### search_knowledge_base — the main search tool

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | — | Search query (required) |
| `top_k` | number | 7 | Number of fragments returned |
| `generate_answer` | bool | True | Generate an answer via LLM |
| `file_filter` | string | "" | Filter by file name |

**Examples of explicit calls:**

```
Call search_knowledge_base with parameters:
- query: "pressure testing pressure of a field pipeline"
- top_k: 10
- generate_answer: true
```

```
Use search_knowledge_base to search for:
- query: "ESP maintenance"
- file_filter: "regulation"
(search only in files whose name contains "regulation")
```

```
Search without answer generation (only relevant fragments):
- query: "pressure buildup hydrodynamics"
- top_k: 3
- generate_answer: false
```

**When to change top_k:**
- `top_k=3` — fast search, sufficient for simple questions
- `top_k=7` — standard (default)
- `top_k=10` — deep analysis, when you need to cover more documents
- `top_k=15-20` — full coverage of a topic (slower)

> [!] **Problem: the same question in Russian and in English returned different
> sources.** The `multilingual-e5` embedding model strongly favours the language of
> the query: for many questions *all* of the nearest neighbours turn out to be in a
> single language. In practice a Russian question returned only Russian papers
> (`{ru: 7}`), while the same question in English returned only English ones
> (`{en: 7}`), and the two source sets did not overlap at all.
>
> **The fix works in two layers.**
>
> 1. **Language balancing of the results.** Retrieval fetches a wide candidate pool
>    (`RETRIEVAL_FETCH_K = 200`), then the final result is guaranteed to include at
>    least `MIN_CHUNKS_PER_LANGUAGE = 2` chunks for each of the languages in
>    `BALANCED_LANGUAGES = ("ru", "en")`, with the remaining slots filled by best
>    score. The balancing is "soft": if a topic only has documents in one language,
>    the other language is not forced in. Disable it with
>    `CROSS_LANGUAGE_BALANCE = False`.
>
> 2. **Dual-query (query translation).** Balancing alone was not enough: if the
>    candidate pool contains no chunks of the second language at all (which is exactly
>    what happens under the strong `e5` bias), there is nothing to balance. So the
>    system translates your question into the other language (ru↔en) with one fast
>    LLM call and searches with **both** phrasings, merging the pools. This brings in
>    *relevant* (not "forced") sources in the other language. Result: the same
>    question in RU and EN yields an almost identical source set (e.g. `{en: 5, ru: 2}`
>    in both cases). Disable it with `CROSS_LANGUAGE_TRANSLATE_QUERY = False`. The
>    cost is one extra (fast) LLM call per query.
>
> All flags live in `config.py`. To inspect the language mix of the results:
> `python check_cross_language.py "your question"` (and `--stats` shows the languages in the index).
>
> Do not confuse this with the **answer language** (the switch in the chat UI, see
> 3.5): that controls the language the LLM writes the answer in, not the retrieval.

---

#### list_documents — list of all documents

```
Show me a list of all documents in the knowledge base
```

or explicitly:

```
Call list_documents with limit=100
```

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `limit` | 50 | Maximum number of files in the output |

**[>>] Example output:**
```
Documents in the knowledge base (47 files):

1. Reglament_TO_nefteprovod_2024.pdf (uploaded: 2024-11-15)
2. GIS_Otchet_Skvazhina_245.pdf (uploaded: 2024-10-03)
3. Instrukciya_po_OT_vysotnye_raboty.docx (uploaded: 2024-09-20)
...
```

---

#### get_document_info — details of a specific document

```
Get information about the document "Reglament_TO_nefteprovod_2024.pdf"
```

**[>>] Example output:**
```
File: GIS_Otchet_Skvazhina_245.pdf
Size: 4.2 MB
Indexing date: 2024-10-03 14:22
Number of chunks: 87
Language: Russian
Brief content: Well logging report for well No. 245 of the Zapadnoye field...
```

**When to use:**
- You need to make sure a specific file is indexed
- You want to know the date of the document's last update
- You need to understand how finely the document is split into fragments

---

#### get_stats — statistics and diagnostics

```
Check the state of the knowledge base
```

**[>>] Example output:**
```
=== RAG System Statistics ===
Documents in index: 47
Total fragments (chunks): 2847
ChromaDB database size: 156 MB
Embedding model: nomic-embed-text

=== LLM Provider Status ===
Provider: ollama
Status: ONLINE
Model: qwen3.5:latest
Answer generation: AVAILABLE

Last index update: 2026-01-15 09:30
```

**When to use:**
- Before an important work session — to make sure everything works
- If answers seem incomplete — to check the number of documents
- When you suspect the LLM provider is not working

---

### 9.7 Troubleshooting

#### 9.7.1: ModuleNotFoundError — wrong path to Python

**Symptom:**
```
Error: ModuleNotFoundError: No module named 'chromadb'
```

**Cause:** `mcp_servers.json` specifies the wrong path to Python — the system Python is used instead of the Python from the virtual environment.

**Solution:**

```bash
# 1. Activate the environment:
source ~/KMS/rag_system/.venv/bin/activate

# 2. Get the EXACT path to Python:
which python
# Output: /home/ivanov_ap/KMS/rag_system/.venv/bin/python

# 3. Update mcp_servers.json:
nano ~/.claude/mcp_servers.json
# Replace the value of "command" with the obtained path

# 4. Check the path manually:
/home/ivanov_ap/KMS/rag_system/.venv/bin/python -c "import chromadb; print('OK')"
```

**[>>] Expected output of the last command:**
```
OK
```

---

#### 9.7.2: Tools do not appear in /tools

**Symptom:** The `/tools` command in Claude Code does not show the `rag_kms:*` tools.

**Step-by-step diagnosis:**

```bash
# Step 1: Check the JSON syntax:
cat ~/.claude/mcp_servers.json | python3 -m json.tool

# Step 2: Check that the file is in the right place:
ls -la ~/.claude/mcp_servers.json

# Step 3: Check read permissions on the file:
chmod 644 ~/.claude/mcp_servers.json

# Step 4: Test-run the server manually:
source ~/KMS/rag_system/.venv/bin/activate
python ~/KMS/rag_system/mcp_rag_server.py
# If errors appear — fix them (see item 9.7.1)
```

After the fixes, **fully restart Claude Code** (exit via `/exit` and launch again).

---

#### 9.7.3: The knowledge base is empty

**Symptom:**
```
get_stats returned: Documents in index: 0
```

**Cause:** The documents have not yet been indexed.

**Solution:**

```bash
source ~/KMS/rag_system/.venv/bin/activate
cd ~/KMS/rag_system/

# Run document indexing:
python ingest.py
```

After indexing, check via `get_stats` — the number of documents should increase.

---

#### 9.7.4: The LLM provider is unavailable

**Symptom:**
```
get_stats returned: Status: OFFLINE
Answer generation: UNAVAILABLE
```

**This is not critical:** the system will continue to work, search will return relevant fragments without a final LLM answer.

**Solution for Ollama:**

```bash
# Check Ollama status:
ollama list

# If Ollama is not running — start it:
ollama serve &

# Check that the needed models are loaded:
ollama list
```

**Solution for a cloud provider (Groq/DeepSeek/OpenRouter):**

1. Check the internet connection: `ping api.groq.com`
2. Check that the API key in `config.py` or environment variables is correct
3. Temporarily switch to ollama in `config.py`

---

#### 9.7.5: Claude Code does not see mcp_servers.json

**Symptom:** The file is created, but Claude Code ignores it.

**Diagnosis:**

```bash
# Check the exact location:
ls -la ~/.claude/
# The file should be named exactly mcp_servers.json

# Check the content:
cat ~/.claude/mcp_servers.json

# Make sure ~/.claude is a folder, not a file:
file ~/.claude
# Should be: /home/USERNAME/.claude: directory
```

> **Common mistake:** The file is created as `~/.claude` (without a slash) instead of `~/.claude/mcp_servers.json`. Check that `~/.claude` is specifically a **folder**.

---

#### 9.7.6: Slow first launch

**Symptom:** The first query after starting Claude Code takes 30–60 seconds.

**This is normal.** On the first consultation of the knowledge base, the following happens:
1. Loading the embedding model into RAM (~500 MB)
2. Connecting to ChromaDB
3. Initializing the connection with the LLM provider

All subsequent queries within one session will be significantly faster (2–5 seconds).

**Tip:** Do not press `Ctrl+C` while waiting — give the system time to initialize.

---

### 9.8 Claude Code Command Cheat Sheet

| Action | Command |
|---|---|
| **Installation** | |
| Install Claude Code | `npm install -g @anthropic-ai/claude-code` |
| Update Claude Code | `npm update -g @anthropic-ai/claude-code` |
| Authorization | `claude login` |
| Check version | `claude --version` |
| **Launch** | |
| Launch Claude Code (regular) | `claude` |
| Launch from the KMS folder (recommended) | `cd ~/KMS && claude` |
| Exit Claude Code | `/exit` |
| **Diagnostics in Claude Code** | |
| Check available tools | `/tools` (inside Claude Code) |
| Check system status | Ask: `Call get_stats` |
| **Configuration** | |
| Open the MCP config | `nano ~/.claude/mcp_servers.json` |
| Check the JSON syntax | `cat ~/.claude/mcp_servers.json \| python3 -m json.tool` |
| Show USERNAME | `echo $USER` |
| Find out the path to Python | `source ~/KMS/rag_system/.venv/bin/activate && which python` |
| Check dependency imports | `python -c "import chromadb, ollama; print('OK')"` |
| **MCP server** | |
| Test-run the server | `source ~/KMS/rag_system/.venv/bin/activate && python ~/KMS/rag_system/mcp_rag_server.py` |
| **Logs and debugging** | |
| Launch Claude with debugging | `claude --debug` |

---

## Appendix A. System File Structure

For those who want to understand what is responsible for what:

```
~/KMS/
├── CLAUDE.md                    ← Project context for Claude Code (Section 9)
│
├── archive/                     → Your documents (or a symbolic link to USB)
│   ├── article_1.pdf            → PDF document
│   ├── report.docx              → Word document
│   ├── data.xlsx                → Excel spreadsheet
│   ├── presentation.pptx        → Presentation
│   └── CO2_storage/             → Can be organized into subfolders
│       └── co2_paper.pdf
│
├── notes/                       → Obsidian vault
│   ├── <document-title>.md      → Notes are created directly in notes/ (name — title slug)
│   ├── ...                      → one note per document
│   └── Templates/               → Templates for notes
│       ├── Literature Note.md
│       ├── RAG Query.md
│       ├── Research Session.md
│       └── Shell Commands.md
│
└── rag_system/                  → The system itself
    ├── config.py                → Settings (paths, provider, model, formats)
    ├── llm_provider.py          → Multi-provider LLM module (v5.0, NEW)
    ├── ingest.py                → Indexing documents of all formats into ChromaDB
    ├── doc_to_obsidian.py       → Creating Obsidian notes (all formats)
    ├── pdf_to_obsidian.py       → Old script (PDF only, for compatibility)
    ├── watcher.py               → Folder watcher (all formats)
    ├── rag_engine.py            → Search and answer engine
    ├── chat_ui.py               → Chat web interface
    ├── mcp_rag_server.py        → MCP server for Claude Code (Section 9)
    ├── requirements.txt         → List of Python packages
    ├── install_service.sh       → systemd service installation script
    ├── chroma_db/               → Vector representation database
    ├── logs/                    → System operation logs
    │   └── rag_system.log
    └── .venv/                   → Python virtual environment
        └── bin/
            └── activate         → Environment activation script

~/.claude/                       → Claude Code configuration (Section 9)
└── mcp_servers.json             → MCP configuration
```

---

## Appendix B. Glossary

**API key** — a unique secret code for authentication when accessing a cloud service (Groq, DeepSeek, OpenRouter, etc.). Issued in the service's account dashboard. Do not share it with anyone.

**ChromaDB** — a database for storing and searching vector representations (embeddings). Unlike ordinary databases, it can find records "similar in meaning," not just exact matches.

**Claude Code** — Anthropic's AI assistant that runs on the command line. It can call external tools via the MCP protocol, including your RAG system.

**Embedding (vector representation)** — a numerical vector (a set of numbers) encoding the meaning of a text fragment. Texts with similar meaning have close vectors. This is exactly what allows the system to find documents about "carbon dioxide absorption" if you ask about "CO₂ sequestration."

**LLM (Large Language Model)** — a program trained on huge volumes of text, capable of understanding and generating human language. Examples: GPT-4, Claude, Mistral, Qwen, LLaMA.

**LLM provider** — a service or program providing access to a language model. RAG KMS v5.0 supports: ollama (local), groq, deepseek, openrouter, lmstudio.

**Markdown** — a simple language for marking up text with special characters. For example, `**bold**` → **bold**, `# Heading` → a large heading. Obsidian uses Markdown for all notes.

**MCP (Model Context Protocol)** — an open protocol from Anthropic that allows AI assistants (in particular, Claude Code) to connect to external tools and data sources. It works via JSON-RPC over stdio.

**Ollama** — a program for running language models locally without the internet.

**OCR (Optical Character Recognition)** — technology for recognizing text in images. Needed for working with scanned PDFs.

**pip** — the Python package manager. Lets you install libraries with the `pip install` command.

**RAG (Retrieval-Augmented Generation)** — a technology in which the language model first searches for relevant fragments in a knowledge base and then uses them to generate an answer. Without RAG, the model answers only based on its "knowledge" from training; with RAG — it relies on your specific documents.

**Systemd / systemctl** — the service management system in Linux. `systemctl` is the utility for managing services.

**Symlink (symbolic link)** — a file that is a "pointer" to another file or folder in the file system. Like a shortcut in Windows, but more "real" — programs work with it as with an actual file.

**Vault (Obsidian vault)** — a folder on the disk that Obsidian uses to store notes and track the connections between them.

**Virtual environment (Python virtual environment)** — an isolated Python environment with its own set of installed packages, independent of the system Python.

---

## Appendix C. Installation Checklist

Use this list to make sure all steps were done correctly:

**Base system (required):**
- [ ] Ubuntu 20.04/22.04/24.04 installed and updated
- [ ] Python 3.10–3.12 available (`python3 --version`; on 3.13+ ChromaDB won't build — 3.12 is needed)
- [ ] Ollama installed (`ollama list` does not produce an error)
- [ ] Language model downloaded (visible in `ollama list`)
- [ ] The `~/KMS/archive` folder created (or a symbolic link to USB)
- [ ] System archive extracted into `~/KMS/rag_system/`
- [ ] The `llm_provider.py` file is present in `~/KMS/rag_system/`
- [ ] Virtual environment created (`~/KMS/rag_system/.venv/`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Paths in `config.py` configured
- [ ] LLM provider and model in `config.py` selected
- [ ] Obsidian installed
- [ ] Obsidian vault opened (`~/KMS/notes/`)
- [ ] Templates copied to `~/KMS/notes/Templates/`
- [ ] First documents added to the archive
- [ ] Indexing completed successfully (`python ingest.py`)
- [ ] Obsidian notes created (`python doc_to_obsidian.py`)
- [ ] Chat interface opens in the browser (http://127.0.0.1:7860)
- [ ] Watcher service installed and running (`systemctl --user status rag-watcher`)

**Multi-provider (if you use cloud LLMs):**
- [ ] API key obtained (Groq / DeepSeek / OpenRouter)
- [ ] Key added to `~/.bashrc` or `config.py`
- [ ] Provider specified in `config.py` (the `LLM_PROVIDER` field)
- [ ] Model for the provider specified (the `LLM_MODEL` field)
- [ ] Connection to the provider tested

**Claude Code + MCP (optional, Section 9):**
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Claude Code installed (`claude --version`)
- [ ] Authorization completed (`claude login`)
- [ ] The `~/.claude/` folder created
- [ ] The `~/.claude/mcp_servers.json` file created with correct paths
- [ ] JSON syntax checked (`cat ~/.claude/mcp_servers.json | python3 -m json.tool`)
- [ ] RAG tools visible in `/tools` inside Claude Code
- [ ] The `~/KMS/CLAUDE.md` file created with the project context

---

## Appendix D. Frequently Asked Questions (FAQ)

**Q: Is a constant internet connection needed for the system to work?**

A: No. After installing all components and downloading the models, the system works fully offline (if the `ollama` or `lmstudio` provider is selected). When using cloud providers (groq, deepseek, openrouter), the internet is needed for each request.

---

**Q: Can I use other language models, not just Mistral?**

A: Yes! In version 5.0, 5 providers are available. For Ollama, any model from the ollama.com/library catalog will do. Recommended: `qwen2.5:7b` (local, best for this project), `llama-3.3-70b-versatile` (Groq, free, more powerful). Download the model via `ollama pull MODEL_NAME` and specify it in `config.py`. More on this in Section 7.

---

**Q: What if a PDF is in multiple languages (for example, Russian text + English tables)?**

A: The system will correctly process mixed text. The language model will also understand mixed content. Tags will be created based on the content.

---

**Q: What is the maximum number of documents the system can store?**

A: There is no practical limit. ChromaDB scales well. The real limits are disk space (the database takes up about 50% of the document size) and RAM during search. With 10,000+ documents, search may take 3–5 seconds instead of the usual 0.5–1 second.

---

**Q: The system lost the index. Do I need to process all documents again?**

A: Yes, if the `chroma_db/` folder was deleted or corrupted. Just run `python ingest.py` — the system will process all documents currently in `~/KMS/archive/`. This will take time, but everything will be restored.

---

**Q: Can the chat be run from several computers on the network?**

A: Yes. Change the `launch()` line in `chat_ui.py` to `launch(server_name="0.0.0.0")` — the interface will become available at your computer's IP address on the local network: `http://192.168.x.x:7860`.

---

**Q: How do I make a backup of the knowledge base?**

A: Copy the `~/KMS/rag_system/chroma_db/` folder to a backup disk. Also don't forget to copy `~/KMS/notes/` (Obsidian notes) and `~/KMS/rag_system/config.py` (settings).

---

**Q: How do I switch from Ollama to Groq and back?**

A: Open `config.py` and change three lines: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`. Restart the chat or script. Detailed examples — in Section 7.1.

---

**Q: My Groq API key ran out for today. What do I do?**

A: The Groq free tier is 14,400 requests per day. Wait for the reset (at midnight UTC) or temporarily switch to `ollama`: in `config.py` change `LLM_PROVIDER: str = "ollama"`. After the limit resets, switch back.

---

**Q: Why do I need Claude Code if I already have chat_ui.py?**

A: `chat_ui.py` is a simple chat interface: you ask a question, get an answer. Claude Code is a more powerful tool: it can work with several tools at once, read files, run commands, build multi-step reasoning. For example, Claude Code can find information in the knowledge base, then open a specific file, then write a summary — all in one conversation. More on this in Section 9.

---

**Q: How do I securely store API keys without putting them in config.py?**

A: Use environment variables in `~/.bashrc` (details — Section 7.3). The `LLM_API_KEY` field in `config.py` can be left empty — `llm_provider.py` will automatically read the environment variable `RAG_GROQ_API_KEY`, `RAG_DEEPSEEK_API_KEY`, or `RAG_OPENROUTER_API_KEY`.

---

## Cheat Sheet. All Key Commands

This table contains all the main commands in one place. We recommend printing it out or saving it in a separate file.

---

### Main RAG System Operations

| Action | Command |
|----------|---------| 
| Launch the chat | `cd ~/KMS/rag_system && source .venv/bin/activate && python chat_ui.py` |
| Open the chat in a browser | http://127.0.0.1:7860 |
| Watcher status | `systemctl --user status rag-watcher` |
| Restart the watcher | `systemctl --user restart rag-watcher` |
| Update the index manually | `cd ~/KMS/rag_system && source .venv/bin/activate && python ingest.py` |
| Update Obsidian notes | `cd ~/KMS/rag_system && source .venv/bin/activate && python doc_to_obsidian.py` |
| Question without a browser | `cd ~/KMS/rag_system && source .venv/bin/activate && python rag_engine.py "question"` |
| Database statistics | `cd ~/KMS/rag_system && source .venv/bin/activate && python rag_engine.py --stats` |
| Activate the environment | `source ~/KMS/rag_system/.venv/bin/activate` |

---

### Managing the Watcher Service

| Action | Command |
|----------|---------| 
| Status | `systemctl --user status rag-watcher` |
| Start | `systemctl --user start rag-watcher` |
| Stop | `systemctl --user stop rag-watcher` |
| Restart | `systemctl --user restart rag-watcher` |
| Enable autostart | `systemctl --user enable rag-watcher` |
| Disable autostart | `systemctl --user disable rag-watcher` |
| Last 50 log lines | `journalctl --user -u rag-watcher -n 50` |
| Real-time log | `journalctl --user -u rag-watcher -f` |

---

### Managing Ollama and Models

| Action | Command |
|----------|---------| 
| List installed models | `ollama list` |
| Download Mistral | `ollama pull mistral` |
| Download Qwen2.5 7B (recommended) | `ollama pull qwen2.5:7b` |
| Download Qwen2.5 14B (more powerful) | `ollama pull qwen2.5:14b` |
| Download LLaMA 3.1 8B | `ollama pull llama3.1:8b` |
| Download DeepSeek R1 7B | `ollama pull deepseek-r1:7b` |
| Download a compact model | `ollama pull mistral:7b-instruct-q4_0` |
| Update Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Check Ollama version | `ollama --version` |
| Remove a model | `ollama rm mistral` |
| Status of running models | `ollama ps` |
| Start the Ollama server | `ollama serve` |
| Check the Ollama API | `curl http://localhost:11434/api/tags` |

---

### Managing LLM Providers

| Action | Description |
|----------|---------| 
| Switch to Ollama | In config.py: `LLM_PROVIDER="ollama"`, `LLM_MODEL="qwen2.5:7b"` |
| Switch to Groq | In config.py: `LLM_PROVIDER="groq"`, `LLM_MODEL="llama-3.3-70b-versatile"`, `LLM_API_KEY="gsk_..."` |
| Switch to DeepSeek | In config.py: `LLM_PROVIDER="deepseek"`, `LLM_MODEL="deepseek-chat"`, `LLM_API_KEY="sk-..."` |
| Switch to OpenRouter | In config.py: `LLM_PROVIDER="openrouter"`, `LLM_MODEL="qwen/qwen3-14b:free"`, `LLM_API_KEY="sk-or-..."` |
| Switch to LM Studio | In config.py: `LLM_PROVIDER="lmstudio"`, `LLM_MODEL="qwen2.5-7b-instruct"` |
| Set the Groq key via env | `export RAG_GROQ_API_KEY="gsk_..."` (in ~/.bashrc) |
| Set the DeepSeek key via env | `export RAG_DEEPSEEK_API_KEY="sk-..."` (in ~/.bashrc) |
| Set the OpenRouter key via env | `export RAG_OPENROUTER_API_KEY="sk-or-..."` (in ~/.bashrc) |

---

### Diagnostics and Maintenance

| Action | Command |
|----------|---------| 
| Disk space | `df -h` |
| ChromaDB database size | `du -sh ~/KMS/rag_system/chroma_db/` |
| Document archive size | `du -sh ~/KMS/archive/` |
| Number of PDFs in the archive | `find ~/KMS/archive -name "*.pdf" \| wc -l` |
| All documents by type | `find ~/KMS/archive -type f \| sed 's/.*\.//' \| sort \| uniq -c` |
| Python version | `python3 --version` |
| System logs (file) | `tail -f ~/KMS/rag_system/logs/rag_system.log` |
| USB link status | `ls -la ~/KMS/archive` |
| Top 20 frequent tags | `grep -r "auto/" ~/KMS/notes/ \| grep "tags:" \| sort \| uniq -c \| sort -rn \| head -20` |
| Clear the pip cache | `pip cache purge` |
| Clear old journals | `journalctl --user --vacuum-size=100M` |

---

### Claude Code and MCP (Section 9)

| Action | Command |
|----------|---------| 
| Install Claude Code | `npm install -g @anthropic-ai/claude-code` |
| Update Claude Code | `npm update -g @anthropic-ai/claude-code` |
| Authorization | `claude login` |
| Check version | `claude --version` |
| Launch with project context | `cd ~/KMS && claude` |
| Exit Claude Code | `/exit` |
| Check RAG tools | `/tools` (inside Claude Code) |
| Open the MCP config | `nano ~/.claude/mcp_servers.json` |
| Check the MCP config syntax | `cat ~/.claude/mcp_servers.json \| python3 -m json.tool` |
| Test the MCP server manually | `source ~/KMS/rag_system/.venv/bin/activate && python ~/KMS/rag_system/mcp_rag_server.py` |
| Launch with debugging | `claude --debug` |
| Quick launch (alias) | `kms` (after `echo "alias kms='cd ~/KMS && claude'" >> ~/.bashrc`) |

---

*The system runs fully locally when using the `ollama` and `lmstudio` providers. Data does not leave your computer. When using cloud providers (groq, deepseek, openrouter), search queries and document context are transmitted to the provider's servers — use this with regard to your organization's confidentiality policy.*

---

**Document version:** 5.1 (refined based on operational experience) | **Year:** 2026  
**Author:** Alexander Knyazev, Head of the Decarbonization Technologies Department, JSC "SRI SPA "LUCH" — PB  
**Supported document formats:** PDF, DOCX, DOC, TXT, MD, XLSX, CSV, PPTX, ODT
