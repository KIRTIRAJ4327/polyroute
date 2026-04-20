"""Natural-language explanation layer.

Rule-based today, model-agnostic LLM tomorrow.
"""

from .explainer import explain, one_line_summary, summarize_legs
from .llm_explainer import (
    ExplainResult,
    LLMExplainer,
    anthropic_generate,
    azure_foundry_generate,
    openai_generate,
)

__all__ = [
    "explain",
    "one_line_summary",
    "summarize_legs",
    "ExplainResult",
    "LLMExplainer",
    "anthropic_generate",
    "azure_foundry_generate",
    "openai_generate",
]
