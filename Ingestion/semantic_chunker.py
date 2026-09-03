"""
Semantic Chunker Module

Reads Markdown annual reports and splits them into semantically coherent
chunks using Azure OpenAI embeddings.  Each chunk preserves its source
filename as metadata so downstream retrieval can trace content back to
the original document.

Directory structure:
    Data/
        reports_markdown/        <- Source Markdown files

Expected .env variables:
    AZURE_OPENAI_ENDPOINT       <- Azure OpenAI resource endpoint
    AZURE_OPENAI_API_KEY        <- API key for the resource
    AZURE_OPENAI_EMBEDDING_VERSION    <- API embedding version (e.g. 2024-02-01)
    AZURE_OPENAI_EMBEDDING_MODEL <- Deployment name of the embedding model

Usage:
    from Ingestion.semantic_chunker import MarkdownSemanticChunker

    chunker = MarkdownSemanticChunker()
    chunks  = chunker.chunk_all()        # list[Document]
    for c in chunks:
        print(c.metadata["source"], c.page_content[:80])
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import AzureOpenAIEmbeddings

# ---------------------------------------------------------------------------
# Project paths (mirrors convention in pdf_to_markdown.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

MARKDOWN_SOURCE_DIR: Path = PROJECT_ROOT / "Data" / "reports_markdown"


class MarkdownSemanticChunker:
    """Semantic chunker powered by Azure OpenAI embeddings.

    Parameters
    ----------
    breakpoint_threshold_type : str, optional
        Strategy used by ``SemanticChunker`` to decide where to split.
        Accepted values: ``"percentile"``, ``"standard_deviation"``,
        ``"interquartile"``, ``"gradient"``.
        Defaults to ``"percentile"``.
    markdown_dir : str | Path | None, optional
        Directory that contains the Markdown files to chunk.
        Defaults to ``Data/reports_markdown``.
    """

    def __init__(
        self,
        breakpoint_threshold_type: Literal[
            "percentile", "standard_deviation", "interquartile", "gradient"
        ] = "percentile",
        markdown_dir: str | Path | None = None,
    ) -> None:
        # Load .env from project root
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        # ---- Capture environment variables ----
        self.endpoint: str = self._require_env(name="AZURE_OPENAI_ENDPOINT")
        self.api_key: str = self._require_env(name="AZURE_OPENAI_API_KEY")
        self.api_version: str = self._require_env(name="AZURE_OPENAI_EMBEDDING_VERSION")
        self.embedding_model: str = self._require_env(
            name="AZURE_OPENAI_EMBEDDING_MODEL"
        )

        # Resolve markdown source directory
        self.markdown_dir: Path = (
            Path(markdown_dir) if markdown_dir else MARKDOWN_SOURCE_DIR
        )

        # ---- Build the Azure OpenAI embeddings instance ----
        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            model=self.embedding_model,
        )

        # ---- Build the semantic chunker ----
        self.chunker = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
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
    def read_markdown_files(self) -> list[Document]:
        """Read every ``*.md`` file in ``self.markdown_dir`` and return
        them as a list of LangChain ``Document`` objects.

        Each document's ``metadata["source"]`` is set to the filename
        (e.g. ``"2024_Apple.md"``) so chunks can be traced back.

        Returns
        -------
        list[Document]
            One document per Markdown file.

        Raises
        ------
        NotADirectoryError
            If the configured markdown directory does not exist.
        FileNotFoundError
            If no ``*.md`` files are found in the directory.
        """
        if not self.markdown_dir.is_dir():
            raise NotADirectoryError(
                f"Markdown directory not found: {self.markdown_dir}"
            )

        md_files = sorted(self.markdown_dir.glob(pattern="*.md"))

        if not md_files:
            raise FileNotFoundError(
                f"No markdown files found in {self.markdown_dir}"
            )

        documents: list[Document] = []
        for md_file in md_files:
            text = md_file.read_text(encoding="utf-8")
            documents.append(
                Document(page_content=text, metadata={"source": md_file.name})
            )

        print(f"Loaded {len(documents)} markdown file(s) from {self.markdown_dir}")
        return documents

    # Chunking methods
    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of documents into semantically coherent chunks.

        Parameters
        ----------
        documents : list[Document]
            Documents to chunk (typically from :meth:`read_markdown_files`).

        Returns
        -------
        list[Document]
            Flattened list of chunked documents.  Each chunk inherits the
            ``metadata`` of its parent document.
        """
        all_chunks: list[Document] = []

        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            chunks = self.chunker.create_documents(
                texts=[doc.page_content],
                metadatas=[doc.metadata],
            )
            print(f"  {source}: {len(chunks)} chunk(s)")
            all_chunks.extend(chunks)

        return all_chunks

    def chunk_all(self) -> list[Document]:
        """Convenience method: read all Markdown files **and** chunk them
        in one call.

        Returns
        -------
        list[Document]
            Semantically chunked documents ready for embedding / storage.
        """
        documents = self.read_markdown_files()
        return self.chunk_documents(documents)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    chunker = MarkdownSemanticChunker()
    chunks = chunker.chunk_all()

    print(f"\nTotal chunks: {len(chunks)}\n")
    for i, chunk in enumerate(iterable=chunks, start=1):
        src = chunk.metadata.get("source", "?")
        preview = chunk.page_content[:120].replace("\n", " ")
        print(f"[{i}] {src}  |  {preview}...")
