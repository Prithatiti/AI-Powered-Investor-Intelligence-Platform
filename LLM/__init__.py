"""
LLM package - Azure OpenAI client and structured output helpers.

Exposes the chat client wrapper and the structured-output function used to
obtain typed, Pydantic responses from the chat model.
"""

from LLM.azure_openai import (
    AzureOpenAIClient,
    GetStructuredOutput,
    get_structured_output,
)

__all__ = [
    "AzureOpenAIClient",
    "GetStructuredOutput",
    "get_structured_output",
]