"""
Azure OpenAI Client & Structured Output Module

Encapsulates the Azure OpenAI chat client and provides a helper to obtain
structured (Pydantic) responses from a model.  The module has two main
components:

1. :class:`AzureOpenAIClient`
   A thin wrapper around :class:`openai.AzureOpenAI` holding the three
   connection credentials (API key, API version, and Azure endpoint) used
   for the chat model.

2. :func:`GetStructuredOutput` / :func:`get_structured_output`
   Takes a prompt and a model name, calls the model, and returns the
   response parsed directly into a user-supplied Pydantic model.  Useful for
   returning validated, typed JSON (e.g. an extracted ``FinancialMetrics``
   object) instead of raw text.

The connection settings default to these ``.env`` variables:

    AZURE_OPENAI_CHAT_ENDPOINT        <- Azure OpenAI endpoint for the chat model
    AZURE_OPENAI_API_KEY              <- API key for the Azure OpenAI resource
    AZURE_OPENAI_CHAT_VERSION         <- API version, e.g. "2024-12-01-preview"
                                           (fallback for chat if no chat-specific
                                            version variable is set)

If you prefer chat-specific settings, pass the three values explicitly to the
:class:`AzureOpenAIClient` constructor.

Usage:
    from pydantic import BaseModel, Field
    from LLM.azure_openai import AzureOpenAIClient, get_structured_output

    class Metrics(BaseModel):
        revenue: str | None = Field(None, alias="Revenue")

    client = AzureOpenAIClient()
    metrics = get_structured_output(
        prompt="Extract the revenue from this report.",
        model="gpt-4o",
        response_model=Metrics,
        client=client,
    )
    print(metrics.revenue)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Generic bound to any Pydantic model so the response type resembles the model.
ResponseModelT = TypeVar(name="ResponseModelT", bound=BaseModel)


# ---------------------------------------------------------------------------
# Component 1: Azure OpenAI client wrapper
# ---------------------------------------------------------------------------
class AzureOpenAIClient:
    """Wrap the Azure OpenAI chat client plus connection credentials.

    Parameters
    ----------
    api_key : str | None, optional
        Azure OpenAI API key.  Defaults to ``AZURE_OPENAI_API_KEY``.
    api_version : str | None, optional
        API version for the chat model (e.g. ``"2024-12-01-preview"``).  Defaults to
        ``AZURE_OPENAI_CHAT_VERSION`` and finally to ``"2024-12-01-preview"``.
    azure_endpoint : str | None, optional
        Azure OpenAI resource endpoint (e.g.
        ``"https://<resource>.openai.azure.com/"``).  Defaults to
        ``AZURE_OPENAI_CHAT_ENDPOINT``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_version: str | None = None,
        azure_endpoint: str | None = None,
    ) -> None:
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        # Captured from the environment (or overridden via constructor args).
        self.api_key: str = api_key or self._require_env(name="AZURE_OPENAI_API_KEY")
        self.api_version: str = (
            api_version
            or os.getenv(key="AZURE_OPENAI_CHAT_VERSION")
            or "2024-12-01-preview"
        )
        self.azure_endpoint: str = azure_endpoint or self._require_env(
            name="AZURE_OPENAI_CHAT_ENDPOINT"
        )

        # Instantiate the underlying OpenAI client.
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
        )

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.getenv(key=name)
        if not value:
            raise OSError(
                f"Missing required environment variable: {name}. "
                "Add it to your .env file at the project root."
            )
        return value

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"AzureOpenAIClient(endpoint={self.azure_endpoint!r}, "
            f"api_version={self.api_version!r})"
        )


# ---------------------------------------------------------------------------
# Component 2: Structured output
# ---------------------------------------------------------------------------
def GetStructuredOutput(
    prompt: str,
    model: str,
    response_model: type[ResponseModelT],
    client: AzureOpenAIClient | None = None,
    temperature: float | None = None,
) -> ResponseModelT:
    """Return a Pydantic-parsed response from an Azure OpenAI chat model.

    Uses the OpenAI structured-outputs endpoint (``beta.chat.completions.parse``)
    so the model is constrained to produce JSON that validates against
    ``response_model``.

    Parameters
    ----------
    prompt : str
        The instruction / context to send to the model.
    model : str
        Deployment name of the chat model (e.g. ``"gpt-4o"``).
    response_model : type[BaseModel]
        A Pydantic model describing the desired output structure.
    client : AzureOpenAIClient | None, optional
        Reusable client instance.  Defaults to building a fresh one.
    temperature : float | None, optional
        Sampling temperature.  When *None* the SDK default is used.

    Returns
    -------
    ResponseModelT
        An instance of ``response_model`` populated from the model output.

    Raises
    ------
    ValueError
        If the model response cannot be parsed into ``response_model``.
    """
    client = client or AzureOpenAIClient()

    # ``parse`` accepts the Pydantic class directly via ``response_format``.
    completion = client.client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial analyst. Respond only with valid "
                    "JSON matching the requested structure."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format=response_model,
        temperature=temperature,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:  # defensive guard against malformed responses
        raise ValueError("The model returned an empty / unparsable response.")

    return parsed


# ---------------------------------------------------------------------------
# Backwards-compatible alias used by the RAG extractor (RAG/kpi_extractor.py)
# ---------------------------------------------------------------------------
def get_structured_completion(
    prompt: str,
    model: str,
    response_model: type[ResponseModelT],
    client: AzureOpenAIClient | None = None,
) -> ResponseModelT:
    """Alias for :func:`GetStructuredOutput`.

    Kept for compatibility with ``RAG/kpi_extractor.py`` which imports
    ``from llm.azure_openai import get_structured_completion``.
    """
    return GetStructuredOutput(
        prompt=prompt,
        model=model,
        response_model=response_model,
        client=client,
    )


# Convenience lowercase alias matching the RAG extractor's import name.
get_structured_output = GetStructuredOutput


# ---------------------------------------------------------------------------
# CLI entry-point (smoke test)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from pydantic import Field

    class SmokeReport(BaseModel):
        summary: str = Field(default=..., description="One-sentence summary")

    client = AzureOpenAIClient()
    print(f"Client ready: {client!r}")
    result = GetStructuredOutput(
        prompt="Summarize the value of structured outputs in one sentence.",
        model=os.getenv(key="AZURE_OPENAI_CHAT_MODEL") or "gpt-5",
        response_model=SmokeReport,
        client=client,
    )
    print("Parsed:", result.model_dump())
