"""
Document Ingestion Module

End-to-end ingestion pipeline that turns Markdown annual reports into
embedded chunks stored in the Azure AI Search vector store, and then
extracts financial metrics from the **newly ingested** data and persists
them to PostgreSQL.

The module exposes three functions:

1. :func:`parse_year_and_company` - extract ``(year, company)`` from a
   markdown filename following the convention ``{year}_{company}.md``
   (e.g. ``2024_Apple.md`` -> ``("2024", "Apple")``).
2. :func:`ingest_document` - chunk a single markdown file, embed it, and
   upload it to the Azure AI Search vector store.  After the chunks are
   uploaded, it runs the KPI extraction pipeline over the newly ingested
   data and persists the extracted financial metrics to PostgreSQL.
   Takes the file path, an ``AzureOpenAIEmbeddings`` instance for
   embedding, and an ``AzureAISearchVectorStore`` instance for storage.
   An optional ``sqlalchemy.Engine`` can be passed to reuse an existing
   database connection.
3. :func:`ingest_directory` - ingest every ``*.md`` file in a directory.
   Takes only the source directory and returns nothing.

It reuses the existing project modules:

    from Ingestion.semantic_chunker import MarkdownSemanticChunker
    from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore
    from RAG.kpi_extractor import KPIExtractor
    from Database.postgres_connect import CreateDatabase, CreateEngine
    from Database.create_table import CreateFinancialMetricsTable

Directory structure:
    Data/
        reports_markdown/        <- Source Markdown files

Usage:
    from langchain_openai import AzureOpenAIEmbeddings
    from Ingestion.ingest_documents import ingest_document, ingest_directory
    from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore

    # Single document (chunks + metrics)
    ingest_document("Data/reports_markdown/2024_Apple.md", embeddings, vector_store)

    # Everything in the default markdown directory
    ingest_directory()
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings

from Ingestion.semantic_chunker import MarkdownSemanticChunker
from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Configuration: centralised directory paths (mirrors pdf_to_markdown.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Default directory that contains the Markdown annual reports
MARKDOWN_SOURCE_DIR: Path = PROJECT_ROOT / "Data" / "reports_markdown"


# ---------------------------------------------------------------------------
# Function 1: Parse the year and company from a filename
# ---------------------------------------------------------------------------
def parse_year_and_company(filename: str | Path) -> tuple[str, str]:
    """Extract the report ``year`` and ``company`` from a markdown filename.

    The expected convention is ``{year}_{company}.md`` where ``{year}`` is
    a four-digit year and ``{company}`` is the (possibly multi-word) company
    name, e.g.::

        "2024_Apple.md"        -> ("2024", "Apple")
        "2023_Microsoft.md"    -> ("2023", "Microsoft")
        "2025_Space X.md"      -> ("2025", "Space X")

    The first underscore separates the year from the company so company
    names that contain spaces (but not underscores) are preserved.

    Parameters
    ----------
    filename : str | Path
        The markdown filename (or full path) to parse.

    Returns
    -------
    tuple[str, str]
        A ``(year, company)`` pair, e.g. ``("2024", "Apple")``.

    Raises
    ------
    ValueError
        If the filename does not match the ``{year}_{company}`` pattern.
    """
    name = Path(filename).stem  # strip directory and extension

    # {year}_{company} where year is exactly four digits
    match = re.fullmatch(pattern=r"(\d{4})_(.+)", string=name)
    if not match:
        raise ValueError(
            f"Could not parse year and company from filename: {filename!r}. "
            "Expected the format '<year>_<company>.md', e.g. '2024_Apple.md'."
        )

    return match.group(1), match.group(2)


# ---------------------------------------------------------------------------
# Function 2: Ingest a single document
# ---------------------------------------------------------------------------
def ingest_document(
    filepath: str | Path,
    embeddings: AzureOpenAIEmbeddings,
    vector_store: AzureAISearchVectorStore,
    engine: Engine | None = None,
    extract_metrics: bool = True,
    on_progress: Callable[[str, float], None] | None = None,
) -> int:
    """Chunk, embed, store, and extract metrics from a single Markdown report.

    The function derives the ``company`` and ``year`` from the filename via
    :func:`parse_year_and_company`, reads the file, semantically chunks it
    with ``embeddings``, and uploads the chunks to the Azure AI Search index
    through ``vector_store`` (which embeds them before storage).

    After the chunks have been uploaded it extracts financial metrics using
    the **newly ingested** data via :class:`RAG.kpi_extractor.KPIExtractor`
    and persists them to PostgreSQL.  The database connection is either
    passed in via *engine* or created on the fly from the ``.env`` settings
    using :func:`Database.postgres_connect.CreateDatabase` and
    :func:`Database.postgres_connect.CreateEngine`; the ``financial_metrics``
    table is ensured through :func:`Database.create_table.CreateFinancialMetricsTable`.

    Parameters
    ----------
    filepath : str | Path
        Path to the ``.md`` file to ingest.
    embeddings : AzureOpenAIEmbeddings
        Azure OpenAI embedding client used both for semantic chunking and
        for computing the vectors that are stored in the index.
    vector_store : AzureAISearchVectorStore
        Vector store backed by the Azure AI Search index to write into.
    engine : sqlalchemy.Engine | None, optional
        An optional, already-configured SQLAlchemy engine for PostgreSQL.
        When ``None``, an engine is created from the environment and the
        ``financial_metrics`` table is created if missing.
    extract_metrics : bool, optional
        When ``True`` (default) financial metrics are extracted from the
        freshly uploaded chunks and persisted to PostgreSQL.
    on_progress : Callable[[str, float], None] | None, optional
        Optional callback invoked with ``(stage, fraction)`` as the pipeline
        progresses.  ``stage`` is one of ``"chunk"``, ``"indexing"``, or
        ``"saving"``; ``fraction`` ranges from 0.0 to 1.0.

    Returns
    -------
    int
        The number of chunks uploaded to the vector store.

    Raises
    ------
    FileNotFoundError
        If ``filepath`` does not point to an existing file.
    ValueError
        If the filename cannot be parsed into year/company.
    """
    filepath = Path(filepath)
    if not filepath.is_file():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")

    # Derive metadata from the filename
    year, company = parse_year_and_company(filename=filepath.name)
    print(f"[INGEST] {filepath.name} -> company={company}, year={year}")

    # Read the file and chunk it with the shared embedding client
    text = filepath.read_text(encoding="utf-8")
    document = Document(page_content=text, metadata={"source": filepath.name})

    chunker = MarkdownSemanticChunker(
        markdown_dir=filepath.parent,
        embeddings=embeddings,
    )
    chunks = chunker.chunk_documents(documents=[document])

    if not chunks:
        print(f"[WARN] No chunks produced for {filepath.name}")
        return 0

    # Embed the chunks and store them in the Azure AI Search index
    num_uploaded = vector_store.upload_chunks(
        chunks=chunks,
        company=company,
        year=year,
        on_progress=(
            (lambda fraction: on_progress("indexing", fraction))
            if on_progress is not None
            else None
        ),
    )

    # Extract financial metrics using the newly ingested data and persist
    # them to PostgreSQL.
    if extract_metrics:
        _extract_and_persist_metrics(
            engine=engine,
            company=company,
            year=year,
            on_progress=on_progress,
        )

    return num_uploaded


# ---------------------------------------------------------------------------
# Function 2b: Extract metrics from the newly ingested data & persist them
# ---------------------------------------------------------------------------
def _extract_and_persist_metrics(
    engine: Engine | None,
    company: str,
    year: str,
    on_progress: Callable[[str, float], None] | None = None,
) -> None:
    """Extract financial metrics from freshly ingested chunks and persist them.

    Runs the RAG-based :class:`RAG.kpi_extractor.KPIExtractor` over the data
    just uploaded to the vector store (retrieved via the shared index), then
    saves the resulting KPIs to the PostgreSQL ``financial_metrics`` table.
    ``KPIExtractor.run`` internally persists the metrics with
    :func:`Database.save_metrics.SaveMetrics`.

    Parameters
    ----------
    engine : sqlalchemy.Engine | None
        An optional, already-configured SQLAlchemy engine.  When ``None`` one
        is created from the environment (and the table ensured) on the fly.
    company : str
        Company of the newly ingested report.
    year : str
        Report year of the newly ingested report.
    on_progress : Callable[[str, float], None] | None, optional
        Optional progress callback forwarded from ``ingest_document``.

    Raises
    ------
    OSError
        If a required ``.env`` variable (PostgreSQL or chat model) is missing.
    """
    # Import lazily so vector-store-only usage does not require the DB stack.
    from Database.create_table import CreateFinancialMetricsTable
    from Database.postgres_connect import CreateDatabase, CreateEngine
    from RAG.kpi_extractor import KPIExtractor

    if on_progress is not None:
        on_progress("saving", 0.0)

    if engine is None:
        database = os.getenv(key="POSTGRES_DATABASE", default="investoriq")
        CreateDatabase()
        engine = CreateEngine(database=database)
        CreateFinancialMetricsTable(engine=engine)

    print(f"[METRICS] Extracting financial metrics for {company} ({year}) "
          f"from the newly ingested data ...")
    extractor = KPIExtractor(engine=engine)
    extractor.run(company=company, year=int(year))
    print(f"[METRICS] Metrics for {company} ({year}) persisted to PostgreSQL.")

    if on_progress is not None:
        on_progress("saving", 1.0)


# ---------------------------------------------------------------------------
# Function 3: Ingest a whole directory of documents
# ---------------------------------------------------------------------------
def ingest_directory(source_dir: str | Path | None = None) -> None:
    """Ingest every ``*.md`` file in a directory into the vector store.

    Builds the Azure OpenAI embeddings client and the Azure AI Search vector
    store once, then ingests each markdown file.  ``year`` and ``company``
    are parsed from each filename automatically.

    A single PostgreSQL engine is created once (along with the
    ``financial_metrics`` table) and shared across the whole batch so that
    after each document's chunks are uploaded, its financial metrics are
    extracted and persisted to PostgreSQL.

    Parameters
    ----------
    source_dir : str | Path | None, optional
        Directory that contains the Markdown files.  Defaults to
        ``Data/reports_markdown``.

    Raises
    ------
    NotADirectoryError
        If ``source_dir`` does not exist or is not a directory.
    """
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

    source_dir = Path(source_dir) if source_dir else MARKDOWN_SOURCE_DIR

    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory not found: {source_dir}")

    md_files = sorted(source_dir.glob(pattern="*.md"))
    if not md_files:
        print(f"No markdown files found in {source_dir}")
        return

    print(f"Found {len(md_files)} markdown file(s) in {source_dir}\n")

    # Embedding client - shared across the whole batch
    embeddings = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        azure_endpoint=os.getenv(key="AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv(key="AZURE_OPENAI_API_KEY"),
        api_version=os.getenv(key="AZURE_OPENAI_API_VERSION")
        or os.getenv(key="AZURE_OPENAI_EMBEDDING_VERSION"),
    )

    # Vector store - wired to the same embeddings used for chunking
    vector_store = AzureAISearchVectorStore(
        endpoint=os.getenv(key="AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv(key="AZURE_SEARCH_API_KEY"),
        index_name=os.getenv(key="AZURE_SEARCH_INDEX_NAME")
        or os.getenv(key="SEARCH_INDEX_NAME"),
        embeddings=embeddings,
    )

    # Build the PostgreSQL engine once and share it across the whole batch so
    # metrics for every ingested file are persisted through the same connection.
    from Database.create_table import CreateFinancialMetricsTable
    from Database.postgres_connect import CreateDatabase, CreateEngine

    database = os.getenv(key="POSTGRES_DATABASE", default="investoriq")
    CreateDatabase()
    engine = CreateEngine(database=database)
    CreateFinancialMetricsTable(engine=engine)

    for md_file in md_files:
        try:
            ingest_document(
                filepath=md_file,
                embeddings=embeddings,
                vector_store=vector_store,
                engine=engine,
            )
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            print(f"[ERROR] {md_file.name}: {exc}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest markdown annual reports into Azure AI Search"
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Path to a single .md file to ingest (optional)",
    )
    parser.add_argument(
        "--dir",
        default=None,
        help="Directory of .md files to ingest (optional, defaults to Data/reports_markdown)",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    _embeddings = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        azure_endpoint=os.getenv(key="AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv(key="AZURE_OPENAI_API_KEY"),
        api_version=os.getenv(key="AZURE_OPENAI_API_VERSION")
        or os.getenv(key="AZURE_OPENAI_EMBEDDING_VERSION"),
    )
    _vector_store = AzureAISearchVectorStore(
        endpoint=os.getenv(key="AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv(key="AZURE_SEARCH_API_KEY"),
        index_name=os.getenv(key="AZURE_SEARCH_INDEX_NAME")
        or os.getenv(key="SEARCH_INDEX_NAME"),
        embeddings=_embeddings,
    )

    if args.file:
        ingest_document(
            filepath=args.file,
            embeddings=_embeddings,
            vector_store=_vector_store,
        )
    else:
        ingest_directory(source_dir=args.dir)