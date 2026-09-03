"""
Retriever Module

A thin wrapper around the Azure AI Search client used to pull the most
relevant chunks for a query.  It mirrors the ``Retriever`` used by the RAG
extractor: given a natural-language query it performs a hybrid search (full-
text + vector) over the investor report index and returns the top matches as
``SimpleNamespace`` objects exposing ``page_content`` and the original
metadata.

The search fields used:

    - ``content``        : full-text searchable chunk text
    - ``content_vector`` : vector embedding of ``content`` (semantic match)
    - ``company``        : optional filter (exact match)
    - ``year``           : optional filter (exact match)

The class reads the following from ``.env``:

    AZURE_SEARCH_ENDPOINT             <- Azure AI Search resource endpoint
    AZURE_SEARCH_API_KEY              <- Query / admin API key
    SEARCH_INDEX_NAME                 <- Index to search (default: investor-reports)
    AZURE_OPENAI_ENDPOINT             <- Azure OpenAI endpoint for embeddings
    AZURE_OPENAI_API_KEY              <- API key for the embedding resource
    AZURE_OPENAI_EMBEDDING_VERSION    <- Embedding API version (e.g. 2024-02-01)
    AZURE_OPENAI_EMBEDDING_MODEL      <- Deployment name of the embedding model

Usage:
    from Vector_Store.retriever import Retriever

    retriever = Retriever()
    results = retriever.invoke(
        query="What were Apple's 2024 revenue drivers?",
        company="Apple",
        year=2024,
        top_k=5,
    )
    for r in results:
        print(r.page_content)
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class Retriever:
    """Retrieve relevant chunks from Azure AI Search.

    Wraps a :class:`azure.search.documents.SearchClient` bound to a single
    index.  On each :meth:`invoke` call the query is embedded and a hybrid
    search (text + vector) is executed, optionally filtered by company and
    year, and the top matches are returned.

    Parameters
    ----------
    endpoint : str, optional
        Azure AI Search endpoint.  Defaults to ``AZURE_SEARCH_ENDPOINT``.
    api_key : str, optional
        Azure AI Search API key.  Defaults to ``AZURE_SEARCH_API_KEY``.
    index_name : str, optional
        Index name.  Defaults to ``SEARCH_INDEX_NAME`` and finally to
        ``"investor-reports"``.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        index_name: str | None = None,
    ) -> None:
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        # ------------------------------------------------------------------
        # Azure AI Search connection
        # ------------------------------------------------------------------
        self.endpoint: str = endpoint or self._require_env(name="AZURE_SEARCH_ENDPOINT")
        self.api_key: str = api_key or self._require_env(name="AZURE_SEARCH_API_KEY")
        self.index_name: str = (
            index_name
            or os.getenv(key="SEARCH_INDEX_NAME")
            or "investor-reports"
        )

        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.api_key),
        )

        # ------------------------------------------------------------------
        # Embedding client (Azure OpenAI) for turning the query into a vector
        # ------------------------------------------------------------------
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
        value = os.getenv(key=name)
        if not value:
            raise OSError(
                f"Missing required environment variable: {name}. "
                "Add it to your .env file at the project root."
            )
        return value

    def _build_filter(self, company: str | None, year: int | None) -> str | None:
        """Combine optional company/year filters into an OData filter string."""
        clauses: list[str] = []

        if company:
            clauses.append(f"company eq '{company}'")

        if year is not None:
            # Index stores ``year`` as a string, so cast the int to str.
            clauses.append(f"year eq '{year}'")

        return " and ".join(clauses) if clauses else None

    def keyword_search(
        self,
        query: str,
        company: str | None = None,
        year: int | None = None,
        top_k: int = 20,
    ) -> list[SimpleNamespace]:
        """Retrieve chunks using keyword (full-text) search only.

        Unlike :meth:`invoke`, this does not embed the query, so it can be
        used without Azure OpenAI embedding credentials configured.  It runs
        a pure ``search_text`` match over the ``content`` field.

        Parameters
        ----------
        query : str
            Keyword / full-text query to match against the chunks.
        company : str | None, optional
            Restrict results to this company (exact filter).
        year : int | None, optional
            Restrict results to this report year (exact filter).
        top_k : int, optional
            Maximum number of chunks to return.  Defaults to ``20``.

        Returns
        -------
        list[SimpleNamespace]
            Ordered list of relevant chunks with ``page_content`` and metadata.
        """
        filter_clause = self._build_filter(company, year)

        results = self.search_client.search(
            search_text=query,
            filter=filter_clause,
            top=top_k,
        )

        retrieved: list[SimpleNamespace] = []
        for item in results:
            retrieved.append(
                SimpleNamespace(
                    page_content=item.get("content", ""),
                    id=item.get("id"),
                    company=item.get("company"),
                    year=item.get("year"),
                    source_file=item.get("source_file"),
                    score=item.get("@search.score"),
                )
            )

        print(f"[KEYWORD] '{query}' -> {len(retrieved)} chunk(s) (top_k={top_k})")
        return retrieved

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def invoke(
        self,
        query: str,
        company: str | None = None,
        year: int | None = None,
        top_k: int = 20,
    ) -> list[SimpleNamespace]:
        """Retrieve relevant chunks from Azure AI Search.

        Parameters
        ----------
        query : str
            Natural-language question or search phrase to match against the
            report chunks.
        company : str | None, optional
            If given, restrict results to chunks from this company.
        year : int | None, optional
            If given, restrict results to chunks from this report year.
        top_k : int, optional
            Maximum number of chunks to return.  Defaults to ``20``.

        Returns
        -------
        list[SimpleNamespace]
            Ordered list of the most relevant chunks.  Each item exposes
            ``page_content`` (the chunk text) plus the remaining index fields
            (id, company, year, source_file) via ``SimpleNamespace``.
        """
        filter_clause = self._build_filter(company, year)

        # Query embedding for the semantic (vector) portion of hybrid search.
        query_vector = self.embeddings.embed_query(query)

        # Build a typed vector query pointing at the content_vector field.
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_clause,
            top=top_k,
        )

        retrieved: list[SimpleNamespace] = []
        for item in results:
            retrieved.append(
                SimpleNamespace(
                    page_content=item.get("content", ""),
                    id=item.get("id"),
                    company=item.get("company"),
                    year=item.get("year"),
                    source_file=item.get("source_file"),
                    score=item.get("@search.score"),
                )
            )

        print(f"[RETRIEVE] '{query}' -> {len(retrieved)} chunk(s) (top_k={top_k})")
        return retrieved


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Retrieve chunks from Azure AI Search")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--company", default=None, help="Optional company filter")
    parser.add_argument("--year", type=int, default=None, help="Optional year filter")
    parser.add_argument("--top-k", type=int, default=20, help="Number of results")
    args = parser.parse_args()

    retriever = Retriever()
    results = retriever.invoke(
        query=args.query,
        company=args.company,
        year=args.year,
        top_k=args.top_k,
    )

    for i, r in enumerate(iterable=results, start=1):
        print(f"\n--- Result {i} (score={r.score:.4f}) ---")
        print(f"  source: {r.source_file} | company={r.company} | year={r.year}")
        print(r.page_content[:500])