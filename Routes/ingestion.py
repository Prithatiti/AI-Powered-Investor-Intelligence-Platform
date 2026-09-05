"""InvestorIQ AI - document ingestion API route.

Accepts an uploaded annual-report file (PDF / Markdown / text), persists it
to ``Data/raw_pdfs``, converts PDFs to Markdown, and ingests the document
into the Azure AI Search vector store.

The uploaded filename must follow the ``{year}_{company}`` convention used
by the ingestion pipeline, e.g. ``2024_Apple.pdf``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_openai import AzureOpenAIEmbeddings

from Ingestion.ingest_documents import ingest_document
from Ingestion.pdf_to_markdown import convert_single_pdf
from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore

router = APIRouter()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
UPLOAD_DIR: Path = PROJECT_ROOT / "Data" / "annual_reports_pdfs"
MARKDOWN_OUTPUT_DIR: Path = PROJECT_ROOT / "Data" / "reports_markdown"
UPLOAD_FILE = File(default=...)

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


@router.post(path="/ingestion/upload")
async def upload_document(file: UploadFile = UPLOAD_FILE):
    """Save an uploaded report and index it into the vector store.

    Returns
    -------
    dict
        A success message, the persisted filename, and the number of
        chunks that were indexed into Azure AI Search.

    Raises
    ------
    HTTPException
        400 for an unsupported file type or an unparseable filename.
        500 when conversion or ingestion fails.
    """
    filename = Path(file.filename or "upload").name
    if not filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / filename

    contents = await file.read()
    file_path.write_bytes(data=contents)

    # PDFs are converted to Markdown first; Markdown / text files are used
    # directly since they are the format the ingestion pipeline expects.
    if file_path.suffix.lower() == ".pdf":
        try:
            md_path = convert_single_pdf(
                pdf_path=file_path,
                output_dir=MARKDOWN_OUTPUT_DIR,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PDF conversion failed: {exc}",
            ) from exc
    elif file_path.suffix.lower() in {".md", ".txt"}:
        md_path = file_path
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file_path.suffix}'. "
                "Upload a PDF, Markdown, or text file."
            ),
        )

    embeddings = AzureOpenAIEmbeddings(
        model=os.getenv(key="AZURE_OPENAI_EMBEDDING_MODEL") or "text-embedding-ada-002",
        azure_endpoint=os.getenv(key="AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv(key="AZURE_OPENAI_API_KEY"),
        api_version=os.getenv(key="AZURE_OPENAI_EMBEDDING_VERSION"),
    )

    vector_store = AzureAISearchVectorStore(
        endpoint=os.getenv(key="AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv(key="AZURE_SEARCH_API_KEY"),
        index_name=os.getenv(key="SEARCH_INDEX_NAME"),
        embeddings=embeddings,
    )

    try:
        chunks_uploaded = ingest_document(
            filepath=md_path,
            embeddings=embeddings,
            vector_store=vector_store,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(object=exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return {
        "message": "Document uploaded and ingested successfully.",
        "filename": filename,
        "chunks_indexed": chunks_uploaded,
    }