"""
Azure AI Search Index Creation Module

Creates (or updates) the search index used by the retrieval pipeline.  The
index stores both the human-readable content of each chunk and its vector
embedding so a hybrid/multi-vector search can combine keyword and semantic
match.

The index is created by default with the name supplied via ``INDEX_NAME``
(``SEARCH_INDEX_NAME`` from ``.env`` if not passed explicitly).

Expected .env variables:
    AZURE_SEARCH_ENDPOINT     <- Azure AI Search resource endpoint
    AZURE_SEARCH_API_KEY      <- Admin / query API key
    SEARCH_INDEX_NAME         <- Index name (optional, has a sensible default)
    AZURE_OPENAI_EMBEDDING_MODEL    <- Not needed here directly, but the
                                       embedding dimension usually matches
                                       the model e.g. text-embedding-3-large
                                       -> 3072, text-embedding-ada-002 -> 1536.

Usage:
    from Ingestion.create_index import AISearchIndexCreator

    creator = AISearchIndexCreator()
    creator.create_index(sync=False)          # create if missing
    creator.create_index(sync=True)           # delete + recreate (overwrite)
"""

from __future__ import annotations

import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


class AISearchIndexCreator:
    """Create and manage the Azure AI Search index for investor reports.

    Parameters
    ----------
    index_name : str | None, optional
        Name of the index to create.  Defaults to ``SEARCH_INDEX_NAME``
        from the environment, falling back to ``investor-reports``.
    embedding_dimensions : int, optional
        Dimensionality of the embedding vectors stored in the index.
        Must match the deployed embedding model (e.g. 1536 for
        ``text-embedding-ada-002``).  Defaults to ``1536``.
    """

    def __init__(
        self,
        index_name: str | None = None,
        embedding_dimensions: int = 1536,
    ) -> None:
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        self.search_endpoint: str = self._require_env(name="AZURE_SEARCH_ENDPOINT")
        self.search_api_key: str = self._require_env(name="AZURE_SEARCH_API_KEY")

        self.index_name: str = (
            index_name
            or os.getenv(key="SEARCH_INDEX_NAME")
            or "investor-reports"
        )
        self.embedding_dimensions: int = embedding_dimensions

        # Credential-backed clients
        self._credential = AzureKeyCredential(self.search_api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self._credential,
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

    # ------------------------------------------------------------------
    # Index definition
    # ------------------------------------------------------------------
    def index_schema(self) -> SearchIndex:
        """Build the ``SearchIndex`` schema for investor report chunks."""
        fields: list = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,  # ty: ignore[invalid-argument-type]
                key=True,
            ),
            SimpleField(
                name="company",
                type=SearchFieldDataType.String,  # ty: ignore[invalid-argument-type]
                filterable=True,
            ),
            SimpleField(
                name="year",
                type=SearchFieldDataType.String,  # ty: ignore[invalid-argument-type]
                filterable=True,
            ),
            SimpleField(
                name="source_file",
                type=SearchFieldDataType.String,  # ty: ignore[invalid-argument-type]
                filterable=True,
            ),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single
                ),  # ty: ignore[call-non-callable]
                vector_search_dimensions=self.embedding_dimensions,
                vector_search_profile_name="vector-profile",
                searchable=True,
            ),
        ]

        # Vector search configuration (HNSW algorithm)
        vector_search = VectorSearch(
            algorithms = [
                HnswAlgorithmConfiguration(
                    name="hnsw-config"
                )
            ],

            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config",
                )
            ],
        )

        # Semantic search configuration (optional but recommended)
        semantic_config = SemanticConfiguration(
            name="investor-reports-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=None,
                content_fields=[SemanticField(field_name="content")],
            ),
        )
        semantic_search = SemanticSearch(
            configurations=[semantic_config]
        )

        return SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_index(
        self,
        sync: bool = False,
        overwrite: bool = False,
    ) -> str:
        """Create the index.

        Parameters
        ----------
        sync : bool, optional
            If *True*, delete any existing index before creating, so the
            resulting index is exactly this schema.  Defaults to *False*
            (only creates when absent).
        overwrite : bool, optional
            If *True*, overwrite an existing index definition in place via
            ``create_or_update_index``.

        Returns
        -------
        str
            The name of the index that was created/updated.
        """
        schema = self.index_schema()

        if (sync or overwrite) and self._index_exists():
            if sync:
                self.index_client.delete_index(self.index_name)
                print(f"[DELETE] Existing index: {self.index_name}")
            else:
                self.index_client.create_or_update_index(index=schema)
                print(f"[UPDATE] Index updated: {self.index_name}")
                return self.index_name

        # Create (idempotent if same schema)
        try:
            self.index_client.create_index(index=schema)
            print(f"[CREATE] Index ready: {self.index_name}")
        except Exception as exc:  # noqa: BLE001
            # Most likely the index already exists.
            print(
                f"[INFO] Could not create index (may already exist): {exc}"
            )
            self.index_client.create_or_update_index(index=schema)
            print(f"[UPDATE] Index upserted: {self.index_name}")

        return self.index_name

    def _index_exists(self) -> bool:
        try:
            self.index_client.get_index(self.index_name)
            return True
        except Exception:  # noqa: BLE001
            return False

    def list_indexes(self) -> list[str]:
        """Return the names of all indexes in the search service."""
        return [i.name for i in self.index_client.list_indexes()]


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    overwrite_mode = "--sync" in sys.argv
    creator = AISearchIndexCreator()
    creator.create_index(sync=overwrite_mode)
    print("Existing indexes:", creator.list_indexes())