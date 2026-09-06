"""
Azure AI Search Vector Store Module

Provides a vector store backed by an existing Azure AI Search index.  The
store is responsible for embedding chunked documents and uploading them to
the search index so they can be retrieved later by semantic or hybrid search.

The class reads the following connection settings from ``.env`` (paths are
relative to the project root):

    AZURE_SEARCH_ENDPOINT             <- Azure AI Search resource endpoint
    AZURE_SEARCH_API_KEY              <- Query / admin API key for the resource
    SEARCH_INDEX_NAME                 <- Name of the index to write into
    AZURE_OPENAI_ENDPOINT             <- Azure OpenAI endpoint for embeddings
    AZURE_OPENAI_API_KEY              <- API key for the embedding resource
    AZURE_OPENAI_EMBEDDING_VERSION    <- Embedding API version (e.g. 2024-02-01)
    AZURE_OPENAI_EMBEDDING_MODEL      <- Deployment name of the embedding model

The uploaded documents match the index schema defined in
``Vector_Store/create_index.py``:

    - ``id``           : unique chunk id (str)
    - ``company``      : company name (filterable)
    - ``year``         : report year (filterable)
    - ``source_file``  : originating markdown filename (filterable)
    - ``content``      : chunk text
    - ``content_vector`` : vector embedding of ``content``

Usage:
    from Vector_Store.azure_ai_search import AzureAISearchVectorStore

    store = AzureAISearchVectorStore()
    store.upload_chunks(chunks, company="Apple", year="2024")
    print(store.get_document_count())
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class AzureAISearchVectorStore:
    """Store chunked documents into an Azure AI Search index.

    The class wires together the Azure AI Search client (for indexing) and
    the Azure OpenAI embeddings client (for vectorising text), then exposes
    a convenient ``upload_chunks`` method.

    Parameters
    ----------
    endpoint : str, optional
        Azure AI Search resource endpoint.  Defaults to the ``AZURE_SEARCH_ENDPOINT``
        environment variable; raises if neither is supplied.
    api_key : str, optional
        Azure AI Search API key.  Defaults to ``AZURE_SEARCH_API_KEY``.
    index_name : str, optional
        Name of the target index.  Defaults to ``SEARCH_INDEX_NAME`` and finally
        to ``"investor-reports"``.
    embeddings : AzureOpenAIEmbeddings | None, optional
        Embedding client to use for vectorising chunks.  When supplied, it is
        used instead of building a new one from ``.env`` so the whole pipeline
        shares a single embedder.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        index_name: str | None = None,
        embeddings: AzureOpenAIEmbeddings | None = None,
    ) -> None:
        # Make .env variables available regardless of the current working dir.
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        # ------------------------------------------------------------------
        # 1) Azure AI Search connection
        # ------------------------------------------------------------------
        self.endpoint: str = endpoint or self._require_env(name="AZURE_SEARCH_ENDPOINT")
        self.api_key: str = api_key or self._require_env(name="AZURE_SEARCH_API_KEY")
        self.index_name: str = (
            index_name
            or os.getenv(key="SEARCH_INDEX_NAME")
            or "investor-reports"
        )

        # SearchClient targets a single index inside the search service.
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.api_key),
        )

        # ------------------------------------------------------------------
        # 2) Embedding client (Azure OpenAI)
        # ------------------------------------------------------------------
        # Use the injected instance when provided so retriever/ingest and the
        # store share one embedder; otherwise fall back to the .env config.
        if embeddings is not None:
            self.embeddings = embeddings
        else:
            self.embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=self._require_env(name="AZURE_OPENAI_ENDPOINT"),
                api_key=self._require_env(name="AZURE_OPENAI_API_KEY"),
                api_version=self._require_env(name="AZURE_OPENAI_EMBEDDING_VERSION"),
                model=self._require_env(name="AZURE_OPENAI_EMBEDDING_MODEL"),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _require_env(name: str) -> str:
        """Return an environment variable or raise if it is missing."""
        value = os.getenv(key=name)
        if not value:
            raise OSError(
                f"Missing required environment variable: {name}. "
                "Add it to your .env file at the project root."
            )
        return value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upload_chunks(
        self,
        chunks: Iterable[Document],
        company: str,
        year: str,
        batch_size: int = 100,
        on_progress: Callable[[float], None] | None = None,
    ) -> int:
        """Embed ``chunks`` and upload them to the search index.

        Each chunk becomes a search document with the metadata fields the
        index expects.  Embedding is performed once per chunk up front, then
        documents are uploaded in batches of ``batch_size`` to keep each
        request within service limits.

        Parameters
        ----------
        chunks : iterable of Document
            Chunked documents (e.g. produced by the semantic chunker).
        company : str
            Company the report belongs to (e.g. ``"Apple"``).
        year : str
            Report year (e.g. ``"2024"``).
        batch_size : int, optional
            How many documents to upload per batch.  Defaults to ``100``.
        on_progress : Callable[[float], None] | None, optional
            Optional callback invoked with a fraction (0.0 -> 1.0) as the
            upload progresses.

        Returns
        -------
        int
            The total number of documents uploaded.
        """
        chunks = list(chunks)

        # Drop empty chunks to avoid embedding unnecessary / blank vectors.
        chunks = [c for c in chunks if c.page_content.strip()]

        if not chunks:
            print("No non-empty chunks to upload.")
            return 0

        # ------------------------------------------------------------------
        # Embed every chunk first so index writes run on already-computed
        # vectors rather than doing embedding inline per batch.
        # ------------------------------------------------------------------
        print(f"Embedding {len(chunks)} chunk(s) ...")
        vectors = self.embeddings.embed_documents(
            [c.page_content for c in chunks]
        )

        documents = []
        for chunk, vector in zip(chunks, vectors):
            documents.append(
                {
                    "id": str(object=uuid.uuid4()),
                    "company": company,
                    "year": year,
                    "source_file": chunk.metadata.get("source", "unknown"),
                    "content": chunk.page_content,
                    "content_vector": vector,
                }
            )

        # ------------------------------------------------------------------
        # Upload in batches via upsert (idempotent per document id).
        # ------------------------------------------------------------------
        total_uploaded = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            self.search_client.upload_documents(documents=batch)
            total_uploaded += len(batch)
            if on_progress is not None:
                on_progress(total_uploaded / len(documents))
            print(f"  Uploaded {total_uploaded}/{len(documents)}")

        print(f"[OK] {total_uploaded} document(s) indexed into "
              f"'{self.index_name}'")
        return total_uploaded

    def get_document_count(self) -> int:
        """Return the total number of documents currently in the index via
        a counting search (returns ``None``-safe integer)."""
        results = self.search_client.search(
            search_text="*",
            include_total_count=True,
        )
        return results.get_count() if results.get_count() is not None else 0


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload chunks to Azure AI Search")
    parser.add_argument("--company", required=True, help="Company name, e.g. Apple")
    parser.add_argument("--year", required=True, help="Report year, e.g. 2024")
    parser.add_argument(
        "--markdown-dir",
        default=None,
        help="Directory holding markdown files to chunk (optional)",
    )
    args = parser.parse_args()

    # Default flow: chunk markdown files, then upload them.
    from Ingestion.semantic_chunker import MarkdownSemanticChunker

    chunker = MarkdownSemanticChunker(markdown_dir=args.markdown_dir)
    chunks = chunker.chunk_all()

    store = AzureAISearchVectorStore()
    uploaded = store.upload_chunks(
        chunks=chunks,
        company=args.company,
        year=args.year,
    )
    print(f"\nIndex '{store.index_name}' now holds "
          f"{store.get_document_count()} document(s).")
