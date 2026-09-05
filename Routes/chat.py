"""InvestorIQ AI - conversational question-answering API route.

Retrieves the most relevant chunks from the Azure AI Search vector store
for a user's question and answers it using the Azure OpenAI chat model.
The retrieved context is grounded in the indexed investor reports so the
model can answer follow-up questions about a specific company or year.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from LLM.azure_openai import AzureOpenAIClient
from Vector_Store.azure_ai_search_retriever import Retriever

router = APIRouter()

TOP_K: int = 4

_retriever = None
_client = None


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    question: str
    company: str | None = None
    year: int | None = None


def _get_retriever() -> Retriever:
    """Return a lazily-created Azure AI Search retriever."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def _get_client() -> AzureOpenAIClient:
    """Return a lazily-created Azure OpenAI chat client."""
    global _client
    if _client is None:
        _client = AzureOpenAIClient()
    return _client


def _build_context(results) -> str:
    """Combine the retrieved chunks into a labelled context block."""
    sections: list[str] = []
    for i, result in enumerate(results, start=1):
        source = getattr(result, "source_file", "unknown")
        sections.append(
            f"--- Chunk {i} (source: {source}) ---\n{result.page_content}"
        )
    return "\n\n".join(sections)


@router.post(path="/chat")
async def chat(request: ChatRequest):
    """Answer a question grounded in the indexed investor reports.

    Returns
    -------
    dict
        ``{"answer": <generated answer>}``.

    Raises
    ------
    HTTPException
        400 for an empty question.
        500 when retrieval or answer generation fails.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Retrieve the most relevant chunks (optionally scoped to company/year).
    try:
        results = _get_retriever().invoke(
            query=request.question,
            company=request.company,
            year=request.year,
            top_k=TOP_K,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve context: {exc}",
        ) from exc

    context = (
        _build_context(results)
        if results
        else "No relevant context was found in the report index."
    )

    prompt = (
        "You are an expert financial analyst. Use the following context "
        "from corporate reports to answer the user's question. If the "
        "context does not contain relevant information, politely indicate "
        "that you do not have enough data.\n\n"
        f"Context:\n{context}\n\n"
        f"User Question: {request.question}\n\n"
        "Answer:"
    )

    model = os.getenv(key="AZURE_OPENAI_CHAT_MODEL") or os.getenv(
        key="AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    if not model:
        raise HTTPException(
            status_code=500,
            detail="Missing Azure OpenAI chat model deployment. "
            "Set AZURE_OPENAI_CHAT_MODEL in .env.",
        )

    try:
        response = _get_client().client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {exc}",
        ) from exc

    answer = response.choices[0].message.content
    return {
      "answer": answer
      }