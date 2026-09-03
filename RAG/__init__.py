"""
RAG package - retrieval-augmented generation components.

Exposes the KPI extractor that retrieves report context from the vector
store and produces structured financial KPIs via the chat model.
"""

from RAG.kpi_extractor import KPIExtractor

__all__ = ["KPIExtractor"]