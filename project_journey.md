# AI-Powered Investor Intelligence Platform

> End-to-end Financial Document Intelligence Platform using Azure OpenAI, Azure AI Search, Azure SQL, FastAPI, React and AKS.

---

## Project Goal

Build an enterprise-grade application capable of:

* Processing financial reports
* Extracting key financial insights
* Generating analytics dashboards
* Supporting RAG-based financial research
* Deploying to Azure Kubernetes Service (AKS)

---

## Phase 1: Project Planning

Status: Completed

Activities:

* Selected Financial Statement Analysis as the use case.
* Chose annual reports as the primary data source.
* Selected Tesla, Apple and Microsoft annual reports.
* Defined RAG + Dashboard architecture approach.
* Decided to build an Investor Intelligence Platform instead of a chatbot.

---

## Phase 2: Dataset Preparation

Status: Completed

Activities:

* Downloaded annual reports.
* Stored PDF files under:

```text
data/raw_pdfs/
```

* Selected publicly available investor reports.

---

## Phase 3: PDF to Markdown Conversion

Status: Completed

Module:

```text
ingestion/pdf_to_markdown.py
```

Objective:

Convert annual report PDFs into markdown format suitable for downstream LLM processing.

Library:

```text
PyMuPDF4LLM
```

Output:

```text
data/markdown/
```

---

## Phase 4: Semantic Chunking

Status: In Progress

Module:

```text
chunking/semantic_chunker.py
```

Objective:

Generate semantically meaningful chunks from markdown documents.

Library:

```text
LangChain SemanticChunker
```

Embedding Model:

```text
Azure OpenAI Embeddings
```

Output:

```text
Document Chunks
```

---

## Phase 5: Azure OpenAI Integration

Status: Pending

Module:

```text
llm/azure_openai.py
```

Objective:

Centralize Azure OpenAI configuration and model initialization.

Deliverables:

* Embedding Model Configuration
* GPT Model Configuration
* Azure OpenAI Client

---

## Phase 6: Azure AI Search Integration

Status: Pending

Module:

```text
vectorstore/azure_ai_search.py
```

Objective:

Store document chunks and embeddings for retrieval.

Deliverables:

* Create Index
* Upload Chunks
* Vector Search
* Metadata Filtering

---

## Phase 7: KPI Extraction

Status: Completed

Module:

```text
rag/kpi_extractor.py
```

Objective:

Extract financial KPIs using Retrieval-Augmented Generation (RAG).

KPIs:

* Revenue
* Net Income
* Cash Flow
* Operating Income
* Total Assets
* Total Liabilities
* Top Risk Factors
* Top Growth Drivers
* Executive Level Financial Summaries

Output:

```text
Structured Financial Metrics
```

The KPI extractor is now wired into the ingestion pipeline
(`Ingestion/ingest_documents.py`): after a document's chunks are uploaded
to the vector store, financial metrics are extracted from the newly ingested
data and persisted to PostgreSQL.

---

## Phase 8: PostgreSQL Integration

Status: Completed

Module:

```text
database/postgres_connect.py   # connection / engine
database/create_table.py       # financial_metrics table
database/save_metrics.py       # persist KPIs
database/remove_duplicate_metrics.py
```

Objective:

Store extracted KPI data for dashboard consumption.

Output:

```text
Financial Metrics Database
```

Metrics extracted during ingestion are persisted to the `financial_metrics`
table via `SaveMetrics`.

## Phase 9: FastAPI Backend

Status: Pending

Objective:

Expose APIs for application functionality.

Endpoints:

* Upload Documents
* Dashboard Data
* Company Comparison
* AI Research

---

## Phase 10: React Frontend

Status: Completed

Framework:

```text
React 19 + TypeScript + Vite
```

Styling:

```text
Tailwind CSS v4 · Recharts · React Router · lucide-react
```

Screens (`Frontend/`):

### Dashboard (`/`)

Display:

* Financial Overview (Revenue, Net Income, Operating Income, Cash Flow)
* KPI stat cards (companies tracked, reports analyzed, avg revenue, avg net income)
* Revenue vs Net Income comparison chart
* Operating Income vs Cash Flow comparison chart
* Balance sheet: Total Assets vs Total Liabilities
* Company scorecards (risk factors, growth drivers, executive summary)

### AI Research (`/research`)

Support financial report research through RAG.

Example Questions:

* Why did revenue increase?
* What are the major risks?
* What acquisitions were discussed?
* Compare AI investments across companies.

### Ingest Reports (`/ingestion`)

* Drag-and-drop upload with `{year}_{company}` filename validation
* PDF / Markdown / text ingestion into Azure AI Search + PostgreSQL

---

## Phase 11: RAG Research Pipeline

Status: Pending

Module:

```text
rag/rag_pipeline.py
```

Objective:

Retrieve relevant chunks and generate grounded financial insights.

Components:

* Retriever
* Prompt Builder
* GPT Response Generator

---

## Phase 12: Containerization

Status: Pending

Deliverables:

* Backend Docker Image
* Frontend Docker Image
* Docker Compose Configuration

---

## Phase 13: AKS Deployment

Status: Pending

Deliverables:

* Kubernetes Deployment
* Services
* Ingress
* Production Validation

---

## Final Deliverable

AI-Powered Investor Intelligence Platform

Capabilities:

* Financial Report Processing
* Semantic Search
* KPI Extraction
* Dashboard Analytics
* Company Comparison
* RAG-Based Financial Research
* Cloud-Native Deployment
