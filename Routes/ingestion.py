"""InvestorIQ AI - document ingestion API route.

Accepts an uploaded annual-report file (PDF / Markdown / text), persists it
to ``Data/annual_reports_pdfs``, converts PDFs to Markdown, and ingests the
document into the Azure AI Search vector store.

The uploaded filename must follow the ``{year}_{company}`` convention used
by the ingestion pipeline, e.g. ``2024_Apple.pdf``.

The endpoint streams Server-Sent Events (SSE) so the frontend can show a
live progress bar that covers the whole pipeline (upload, PDF conversion,
chunking, embedding / indexing, and metric extraction to PostgreSQL).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from queue import Empty, Queue

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from langchain_openai import AzureOpenAIEmbeddings

from Ingestion.ingest_documents import ingest_document, parse_year_and_company
from Ingestion.pdf_to_markdown import convert_single_pdf
from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore
from Vector_Store.create_index import AISearchIndexCreator

router = APIRouter()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
UPLOAD_DIR: Path = PROJECT_ROOT / "Data" / "annual_reports_pdfs"
MARKDOWN_OUTPUT_DIR: Path = PROJECT_ROOT / "Data" / "reports_markdown"
UPLOAD_FILE = File(default=...)

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def _sse(event: str, data: dict) -> str:
    """Serialize one Server-Sent Event payload."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _run_pipeline_sync(file: UploadFile, events: Queue) -> None:
    """Run the blocking ingestion pipeline and push SSE text onto *events*.

    Executed in a worker thread so the FastAPI event loop stays free and the
    response generator can pull progress events off the queue and stream them
    to the client as they happen.

    Parameters
    ----------
    file : UploadFile
        The multipart upload that FastAPI already spooled to disk/memory.
    events : Queue
        Thread-safe queue of SSE payload strings, drained by the async
        response generator.
    """
    try:
        filename = Path(file.filename or "upload").name

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_path = UPLOAD_DIR / filename

        contents = file.file.read()
        file_path.write_bytes(data=contents)  # overwrites an existing file
        events.put(item=_sse(event="progress", data={"stage": "upload", "percent": 20}))

        # PDFs are converted to Markdown first; Markdown / text files are used
        # directly since they are the format the pipeline expects.
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
        else:
            md_path = file_path
        events.put(_sse(event="progress", data={"stage": "convert", "percent": 25}))

        embeddings = AzureOpenAIEmbeddings(
            model=os.getenv(key="AZURE_OPENAI_EMBEDDING_MODEL")
            or "text-embedding-ada-002",
            azure_endpoint=os.getenv(key="AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv(key="AZURE_OPENAI_API_KEY"),
            api_version=os.getenv(key="AZURE_OPENAI_EMBEDDING_VERSION"),
        )

        vector_store = AzureAISearchVectorStore(
            endpoint=os.getenv(key="AZURE_SEARCH_ENDPOINT"),
            api_key=os.getenv(key="AZURE_SEARCH_API_KEY"),
            index_name=os.getenv(key="AZURE_SEARCH_INDEX_NAME")
            or os.getenv(key="SEARCH_INDEX_NAME"),
            embeddings=embeddings,
        )

        # Ensure the target Azure AI Search index exists before uploading
        # chunks. Reuses the existing index-creation implementation; this is
        # a harmless no-op when the index is already present.
        AISearchIndexCreator(index_name=vector_store.index_name).create_index()

        # Stage percentages roughly match how long each step takes:
        #   upload/convert :  0 -> 25   (file saved, PDF converted)
        #   indexing       : 25 -> 80   (semantic chunking + embedding + index write)
        #   saving         : 80 -> 99   (KPI extraction + PostgreSQL write)
        def on_progress(stage: str, fraction: float) -> None:
            if stage == "indexing":
                percent = 25 + int(fraction * 55)
            elif stage == "saving":
                percent = 80 + int(fraction * 19)
            else:
                percent = 25
            events.put(_sse("progress", {"stage": stage, "percent": min(percent, 99)}))

        chunks_uploaded = ingest_document(
            filepath=md_path,
            embeddings=embeddings,
            vector_store=vector_store,
            on_progress=on_progress,
        )

        events.put(item=_sse("progress", {"stage": "saving", "percent": 100}))
        events.put(
            item=_sse(
                event="complete",
                data={
                    "message": "Document uploaded and ingested successfully.",
                    "filename": filename,
                    "chunks_indexed": chunks_uploaded,
                },
            )
        )
    except HTTPException as exc:
        events.put(item=_sse(event="error", data={"message": str(object=exc.detail)}))
    except Exception as exc:  # noqa: BLE001 - report any failure via SSE
        events.put(
            item=_sse(event="error", data={"message": f"Ingestion failed: {exc}"})
        )


@router.post(path="/ingestion/upload")
async def upload_document(file: UploadFile = UPLOAD_FILE):
    """Save an uploaded report and index it into the vector store.

    Instead of doing all the work in one blocking request, this endpoint
    streams a sequence of SSE ``progress`` events (one per pipeline stage)
    followed by a final ``complete`` (or ``error``) event so the client can
    render an honest, slow-moving progress bar while the report is being
    converted, chunked, embedded, and written to PostgreSQL.

    Returns
    -------
    StreamingResponse
        An ``text/event-stream`` response.  Each ``progress`` event carries
        ``{"stage": str, "percent": int}`` and the final event is ``complete``
        with the success payload or ``error`` with the failure message.
    """
    filename = Path(file.filename or "upload").name

    # Validate the {year}_{company} naming convention and the file type up
    # front (both are cheap) so obvious 400s don't need a streaming response.
    try:
        _year, _company = parse_year_and_company(filename=filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid filename '{filename}'. Use the format "
                "'<year>_<company>', e.g. '2024_Apple.pdf'."
            ),
        ) from None

    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".md", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{suffix}'. "
                "Upload a PDF, Markdown, or text file."
            ),
        )

    events: Queue = Queue()

    async def event_source():
        worker = asyncio.get_running_loop().run_in_executor(
            None, _run_pipeline_sync, file, events
        )

        while True:
            # Drain any events produced by the worker so far.
            drained = False
            while True:
                try:
                    item = events.get_nowait()
                except Empty:
                    break
                drained = True
                yield item.encode("utf-8")

            if worker.done():
                # The worker always emits a terminal ``complete``/``error``
                # event.  If it finished without producing anything at all,
                # surface the raised exception (if any) to avoid a silent hang.
                if not drained:
                    try:
                        exc = worker.exception()
                    except BaseException:
                        exc = None
                    message = (
                        f"Ingestion failed: {exc}"
                        if exc is not None
                        else "Upload failed: no response from server."
                    )
                    yield _sse("error", {"message": message}).encode("utf-8")
                break

            # Yield to the event loop so the response can flush queued data.
            await asyncio.sleep(delay=0.05)

    return StreamingResponse(
        content=event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
