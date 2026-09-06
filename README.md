# InvestorIQ-AI: AI Powered Investor Intelligence Platform

An AI-powered investor intelligence platform that analyzes financial reports
to automatically extract key financial KPIs, business risks, growth drivers,
and executive-level insights — while enabling users to ask contextual
questions through an interactive AI chat interface.

---

## Project Overview

InvestorIQ-AI ingests annual report PDFs, converts them into Markdown, splits
them into semantically coherent chunks using Azure OpenAI embeddings, and
stores the chunks in an Azure AI Search index for fast, hybrid retrieval.
After the chunks are uploaded, the platform extracts financial metrics from
the **newly ingested** data via RAG and persists them to PostgreSQL for
dashboard and comparison views.  Users can then query the platform
conversationally to surface relevant evidence from across multiple company
reports.

### Core Pipeline

```text
PDF Annual Reports
        │  pymupdf4llm
        ▼
Markdown Files  (Data/reports_markdown)
        │  SemanticChunker + Azure OpenAI Embeddings
        ▼
Semantic Chunks  (Ingestion/semantic_chunker.py)
        │  Azure AI Search
        ▼
Search Index  (Ingestion/create_index.py)
        │  AzureAISearchVectorStore.upload_chunks
        ▼
Vector Store  (Vector_Store/azure_ai_search.py)
        │  KPIExtractor (RAG over newly ingested chunks)
        ├───────────────────────────────┐
        ▼                               ▼
Retriever  (Vector_Store/retriever.py)  PostgreSQL financial_metrics
        │                                 (Database/save_metrics.py)
        ▼
Investor Insights & Q&A Chat
```

### Directory Structure

```text
.
├── Data/
│   ├── annual_reports_pdfs/   # Source PDF annual reports
│   └── reports_markdown/      # Converted Markdown (auto-generated)
├── Ingestion/
│   ├── pdf_to_markdown.py     # PDF -> Markdown conversion
│   ├── semantic_chunker.py    # Semantic chunking via embeddings
│   ├── ingest_documents.py    # Chunk -> embed -> upload -> extract & persist metrics
│   └── create_index.py        # Azure AI Search index creation
├── RAG/
│   └── kpi_extractor.py       # RAG KPI extraction (financial metrics)
├── Database/
│   ├── create_table.py        # financial_metrics table
│   ├── save_metrics.py        # Persist metrics to PostgreSQL
│   ├── postgres_connect.py    # PostgreSQL connection / engine
│   └── remove_duplicate_metrics.py
├── Vector_Store/
│   ├── azure_ai_search.py     # Vector store: upload chunks to index
│   ├── retriever.py           # Hybrid search retrieval
│   └── __init__.py
├── Frontend/
│   ├── vite.config.ts         # Tailwind + /api dev proxy
│   └── src/
│       ├── pages/             # Dashboard · Research · Ingestion
│       ├── components/        # Layout + shared UI primitives
│       └── lib/               # API client + formatting helpers
├── main.py                    # Application entry-point
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata & dependencies
└── .env                       # Environment configuration (not committed)
```

---

## Requirements

Before you begin, ensure you have the following installed:

| Requirement                         | Version / Notes                                          |
| ----------------------------------- | -------------------------------------------------------- |
| **Python**                          | `>= 3.14` (see `.python-version`)                        |
| **pip**                             | Bundled with Python                                       |
| **azure-cli** (optional)            | Latest (only needed for Azure CLI based auth flows)       |

### Azure Resources

You will also need the following Azure services provisioned and accessible:

- **Azure OpenAI** resource with:
  - An **embeddings** model deployment (e.g. `text-embedding-ada-002`).
  - A **chat** model deployment (e.g. `gpt-4o` / `gpt-35-turbo`) for the Q&A layer.
- **Azure AI Search** service with:
  - An index (created automatically by the ingestion pipeline, e.g. `investor-reports`).
  - An admin or query API key.
- **Azure Database for PostgreSQL** (or any reachable PostgreSQL server) for the relational store.

---

## Create the Environment

### Windows (PowerShell)

```powershell
# 1. Create a virtual environment in the project folder
uv venv venv

# 2. Activate it (PowerShell)
.venv\Scripts\Activate.ps1

# 3. Confirm the interpreter
python --version
```

If activation is blocked by the execution policy, run once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Linux / macOS (bash/zsh)

```bash
# 1. Create a virtual environment in the project folder
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate

# 3. Confirm the interpreter
python --version
```

> Both approaches create an isolated `.venv` inside the project root. Because
> this folder is listed in `.gitignore`, your environment stays local to your
> machine.

---

## Install Dependencies

With the virtual environment activated, install all Python dependencies from
`requirements.txt`:

```bash
uv add -r requirements.txt
```

> **Note:** `pyproject.toml` also declares the same dependencies (for project
> tooling). It is safe to use either file; `requirements.txt` is the canonical
> list for running the application.

---

## Configure Environment Variables

Copy the provided template values into your local `.env` file (at the project
root). **Never commit real keys** — this file is excluded via `.gitignore`.

Create `.env` if it does not exist and populate the following variables:

```dotenv
# ==============================================================
# Azure OpenAI - Embeddings (Semantic Chunker)
# ==============================================================
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_EMBEDDING_VERSION=
AZURE_OPENAI_EMBEDDING_MODEL="text-embedding-ada-002"

# ==============================================================
# Azure OpenAI - Chat (LLM for answering / generation)
# ==============================================================
AZURE_OPENAI_CHAT_ENDPOINT=
AZURE_OPENAI_CHAT_MODEL=

# ==============================================================
# Azure AI Search (Vector + keyword retrieval)
# ==============================================================
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
SEARCH_INDEX_NAME="investor-reports"

# ==============================================================
# PostgreSQL (Relational store)
# ==============================================================
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DATABASE=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

### Variable Reference

| Variable                          | Description                                        |
| --------------------------------- | -------------------------------------------------- |
| `AZURE_OPENAI_ENDPOINT`           | Azure OpenAI resource endpoint for embeddings      |
| `AZURE_OPENAI_API_KEY`            | API key for the Azure OpenAI resource              |
| `AZURE_OPENAI_EMBEDDING_VERSION`  | Embedding API version (e.g. `2024-02-01`)          |
| `AZURE_OPENAI_EMBEDDING_MODEL`    | Embedding deployment name (e.g. `text-embedding-ada-002`) |
| `AZURE_OPENAI_CHAT_ENDPOINT`      | Endpoint for the chat/LLM deployment               |
| `AZURE_OPENAI_CHAT_MODEL`         | Chat model deployment name (e.g. `gpt-4o`)         |
| `AZURE_SEARCH_ENDPOINT`           | Azure AI Search service endpoint                   |
| `AZURE_SEARCH_API_KEY`            | Query / admin key for Azure AI Search              |
| `SEARCH_INDEX_NAME`               | Index to create/use (e.g. `investor-reports`)      |
| `POSTGRES_HOST`                   | PostgreSQL server host                             |
| `POSTGRES_PORT`                   | PostgreSQL server port (default `5432`)            |
| `POSTGRES_DATABASE`               | PostgreSQL database name                           |
| `POSTGRES_USER`                   | PostgreSQL username                                |
| `POSTGRES_PASSWORD`               | PostgreSQL password                                |

---

## Frontend (React UI)

An attractive, responsive React UI lives in the `Frontend/` folder.  It
reads from the FastAPI backend through a dev-time proxy, so no extra
configuration is required for local development.

### Directory Structure (Frontend)

```text
Frontend/
├── index.html                  # App shell + fonts
├── vite.config.ts              # Tailwind plugin + /api dev proxy
└── src/
    ├── App.tsx                 # Router (Dashboard / Research / Ingestion)
    ├── components/
    │   ├── Layout.tsx          # Sidebar + top-bar shell, health indicator
    │   └── ui.tsx              # Shared primitives (spinner, panels, pills)
    ├── lib/
    │   ├── api.ts              # Typed API client for the FastAPI backend
    │   └── format.ts           # Money parsing / list formatting helpers
    ├── pages/
    │   ├── Dashboard.tsx       # KPI cards, charts, company scorecards
    │   ├── Research.tsx        # RAG-based conversational UI
    │   └── Ingestion.tsx       # Drag-and-drop report upload
    └── types.ts                # Shared response types
```

### Run the Frontend

With the backend running (`uvicorn main:app --reload` on port `8000`):

```bash
cd Frontend
npm install
npm run dev
```

Then open http://localhost:5173.  The Vite dev server proxies `/api/*`
calls to the FastAPI backend, and the sidebar shows real-time API health.

> **Production:** `npm run build` outputs a static bundle in
> `Frontend/dist`.  Serve it with any static host (or via the FastAPI app)
> and point `VITE_API_URL` at the API base URL for non-proxied setups.

---

## Next Steps

More documentation (running the application, ingestion workflow, embedding,
and Q&A usage) will be added here as the project progresses.