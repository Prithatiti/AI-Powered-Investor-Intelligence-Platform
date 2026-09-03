"""
Vector Store package - persistence layer backed by Azure AI Search.

Exposes the retrieval wrapper and the uploader for chunked investor report
content.
"""

from Vector_Store.azure_ai_search_retriever import Retriever
from Vector_Store.azure_ai_search_upload import AzureAISearchVectorStore

__all__ = ["Retriever", "AzureAISearchVectorStore"]