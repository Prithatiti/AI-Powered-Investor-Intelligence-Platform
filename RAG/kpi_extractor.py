"""
KPI Extractor Module

Extracts key financial KPIs from investor annual reports using a RAG
(retrieval-augmented generation) pipeline.  The flow is:

1. Retrieve broad financial context from the vector store using a
   keyword (full-text) search over the report chunks.
2. Build a focused KPI extraction prompt from that context.
3. Extract structured KPIs with the Azure OpenAI chat model, parsed
   directly into a Pydantic model (``FinancialMetrics``).
4. Save the extracted KPIs to a JSON file.

The module pulls its dependencies from the sibling packages:

    Vector_Store.azure_ai_search_retriever.Retriever  -> keyword retrieval
    LLM.azure_openai.AzureOpenAIClient                -> chat client
    LLM.azure_openai.GetStructuredOutput              -> typed parsing

Expected .env variables (used via the imported modules):
    AZURE_SEARCH_ENDPOINT             <- Azure AI Search endpoint
    AZURE_SEARCH_API_KEY              <- Search query / admin key
    SEARCH_INDEX_NAME                 <- Index to search
    AZURE_OPENAI_CHAT_ENDPOINT        <- Chat model endpoint
    AZURE_OPENAI_API_KEY              <- Azure OpenAI API key
    AZURE_OPENAI_EMBEDDING_VERSION    <- API version fallback for chat
    AZURE_OPENAI_CHAT_MODEL           <- Chat model deployment name

Usage:
    from RAG.kpi_extractor import KPIExtractor

    extractor = KPIExtractor()
    metrics = extractor.run(company="Apple", year="2024")
    print(metrics.model_dump())
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel, Field

from LLM.azure_openai import AzureOpenAIClient, GetStructuredOutput
from Vector_Store.azure_ai_search_retriever import Retriever

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Structured output schema for the KPIs we extract
# ---------------------------------------------------------------------------
class FinancialMetrics(BaseModel):
    """Pydantic schema describing the KPIs extracted from a report."""

    revenue: str | int | None = Field(default=None, alias="Revenue")
    net_income: str | int | None = Field(default=None, alias="Net Income")
    operating_income: str | int | None = Field(
        default=None, alias="Operating Income"
    )
    cash_flow: str | int | None = Field(
        default=None, alias="Cash Flow from Operating Activities"
    )
    total_assets: str | int | None = Field(default=None, alias="Total Assets")
    total_liabilities: str | int | None = Field(
        default=None, alias="Total Liabilities"
    )
    key_risk_factors: str | list | None = Field(
        default=None, alias="Top Risk Factors"
    )
    growth_drivers: str | list | None = Field(
        default=None, alias="Top Growth Drivers"
    )
    executive_summary: str | list | None = Field(
        default=None, alias="Executive Level Financial Summaries"
    )

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Module-level helpers (kept importable so the RAG extractor stays testable)
# ---------------------------------------------------------------------------
def retrieve_broad_context(
    retriever: Retriever,
    query: str,
    company: str | None = None,
    year: int | None = None,
    top_k: int = 20,
) -> str:
    """Retrieve broad financial context from the vector store via keyword
    search and combine the returned chunk texts into a single context block.

    Parameters
    ----------
    retriever : Retriever
        Configured Azure AI Search retriever.
    query : str
        Broad keyword query (e.g. "financial performance revenue expenses").
    company : str | None, optional
        Restrict to a single company.
    year : int | None, optional
        Restrict to a single report year.
    top_k : int, optional
        Number of chunks to retrieve.  Defaults to ``20``.

    Returns
    -------
    str
        Newline-joined text of the retrieved chunks, each labelled by its
        source file for traceability.
    """
    results = retriever.keyword_search(
        query=query,
        company=company,
        year=year,
        top_k=top_k,
    )

    sections: list[str] = []
    for i, result in enumerate(results, start=1):
        source = getattr(result, "source_file", "unknown")
        sections.append(f"--- Chunk {i} (source: {source}) ---\n{result.page_content}")

    return "\n\n".join(sections)


def build_kpi_prompt(
    context: str,
    company: str | None = None,
    year: str | int | None = None,
) -> str:
    """Build the KPI extraction prompt for the chat model.

    Parameters
    ----------
    context : str
        The retrieved report context (from :func:`retrieve_broad_context`).
    company : str | None, optional
        Optional company name to anchor the prompt.
    year : str | int | None, optional
        Optional report year to anchor the prompt.

    Returns
    -------
    str
        A single prompt string instructing the model to extract the KPIs.
    """
    scope = [part for part in (company, year) if part]
    header = (
        f"Analyse the annual report of {company} (year {year})."
        if scope
        else "Analyse the annual report excerpts below."
    )

    return (
        f"{header}\n\n"
        "Extract the following financial KPIs from the context and return "
        "them as JSON with the exact keys:\n"
        "  - Revenue\n"
        "  - Net Income\n"
        "  - Operating Income\n"
        "  - Cash Flow from Operating Activities\n"
        "  - Total Assets\n"
        "  - Total Liabilities\n"
        "  - Top Risk Factors\n"
        "  - Top Growth Drivers\n"
        "  - Executive Level Financial Summaries\n\n"
        "Use the original context only; do not invent figures. If a value "
        "is not present, set it to null.\n\n"
        "---- REPORT CONTEXT ----\n"
        f"{context}"
    )


def extract_kpis(
    prompt: str,
    model: str,
    client: AzureOpenAIClient | None = None,
    temperature: float | None = None,
) -> FinancialMetrics:
    """Extract structured KPIs from a prompt using the chat model.

    Parameters
    ----------
    prompt : str
        KPI extraction prompt (from :func:`build_kpi_prompt`).
    model : str
        Chat model deployment name (e.g. ``"gpt-4o"``).
    client : AzureOpenAIClient | None, optional
        Reusable OpenAI client.  A fresh one is created if omitted.
    temperature : float | None, optional
        Sampling temperature; defaults to the model default when *None*.

    Returns
    -------
    FinancialMetrics
        Parsed, validated KPIs.
    """
    return GetStructuredOutput(
        prompt=prompt,
        model=model,
        response_model=FinancialMetrics,
        client=client or AzureOpenAIClient(),
        temperature=temperature,
    )


def save_kpis_to_json(
    metrics: FinancialMetrics,
    output_dir: str | Path,
    company: str,
    year: str | int,
) -> Path:
    """Serialise the extracted KPIs to a JSON file under *output_dir*.

    The JSON is written with the human-friendly aliases (e.g. "Revenue")
    as keys for readability.

    Parameters
    ----------
    metrics : FinancialMetrics
        KPIs to serialise.
    output_dir : str | Path
        Directory where the JSON file will be written (created if missing).
    company : str
        Company name, used in the output filename.
    year : str | int
        Report year, used in the output filename.

    Returns
    -------
    Path
        Path to the written JSON file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ``by_alias=True`` keeps friendly keys like "Net Income".
    data = metrics.model_dump(by_alias=True, exclude_none=False)

    filename = f"kpis_{company}_{year}.json"
    output_path = output_dir / filename
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[SAVE] KPIs written to {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Orchestrator class
# ---------------------------------------------------------------------------
class KPIExtractor:
    """End-to-end KPI extraction from the vector store.

    Parameters
    ----------
    company : str, optional
        Default company filter used for retrieval.
    year : str | int | None, optional
        Default report year filter used for retrieval.
    model : str, optional
        Chat model deployment name.  Defaults to the ``AZURE_OPENAI_CHAT_MODEL``
        environment variable.
    top_k : int, optional
        Number of chunks retrieved for context.  Defaults to ``20``.
    output_dir : str | Path | None, optional
        Where JSON results are saved.  Defaults to
        ``RAG/extracted_kpis`` under the project root.
    """

    def __init__(
        self,
        company: str | None = None,
        year: str | int | None = None,
        model: str | None = None,
        top_k: int = 20,
        output_dir: str | Path | None = None,
    ) -> None:
        self.company = company
        self.year = year
        self.model = model or _env(name="AZURE_OPENAI_CHAT_MODEL")
        self.top_k = top_k
        self.output_dir = Path(output_dir) if output_dir else (
            PROJECT_ROOT / "RAG" / "extracted_kpis"
        )

        self.retriever = Retriever()
        self.client = AzureOpenAIClient()

    def run(
        self,
        query: str = "financial performance revenue expenses growth risks",
        company: str | None = None,
        year: str | int | None = None,
    ) -> FinancialMetrics:
        """Perform the full KPI extraction pipeline.

        Parameters
        ----------
        query : str, optional
            Keyword query used to retrieve broad context.
        company : str | None, optional
            Overrides the instance-level company for this run.
        year : str | int | None, optional
            Overrides the instance-level year for this run.

        Returns
        -------
        FinancialMetrics
            The extracted KPIs.
        """
        company = company or self.company
        year = year or self.year

        # 1) Retrieve broad financial context from the vector store.
        print(f"[1/4] Retrieving context for company={company}, year={year} ...")
        context = retrieve_broad_context(
            retriever=self.retriever,
            query=query,
            company=company,
            year=year,
            top_k=self.top_k,
        )

        # 2) Build the KPI extraction prompt from the retrieved context.
        print("[2/4] Building KPI extraction prompt ...")
        prompt = build_kpi_prompt(context=context, company=company, year=year)

        # 3) Extract KPIs using RAG (structured output).
        print("[3/4] Extracting KPIs with the chat model ...")
        metrics = extract_kpis(
            prompt=prompt,
            model=self.model,
            client=self.client,
        )

        # 4) Save the extracted KPIs to JSON.
        print("[4/4] Saving KPIs to JSON ...")
        save_kpis_to_json(
            metrics=metrics,
            output_dir=self.output_dir,
            company=company or "Unknown",
            year=year or "unknown",
        )

        return metrics


# ---------------------------------------------------------------------------
# Internal helper for environment lookups
# ---------------------------------------------------------------------------
def _env(name: str) -> str:
    import os

    value = os.getenv(key=name)
    if not value:
        raise OSError(
            f"Missing required environment variable: {name}. "
            "Add it to your .env file at the project root."
        )
    return value


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract KPIs via RAG")
    parser.add_argument("--company", required=True, help="Company name, e.g. Apple")
    parser.add_argument("--year", help="Report year, e.g. 2024")
    parser.add_argument("--model", help="Chat model deployment name")
    parser.add_argument("--query", default="financial performance revenue expenses growth risks")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    extractor = KPIExtractor(
        company=args.company,
        year=args.year,
        model=args.model,
        top_k=args.top_k,
    )
    metrics = extractor.run(query=args.query)
    print("\nExtracted KPIs:")
    print(metrics.model_dump(by_alias=True, indent=2))