"""Natural-language explanation layer.

Rule-based today, model-agnostic LLM tomorrow.
"""

from .explainer import explain, one_line_summary, summarize_legs

__all__ = ["explain", "one_line_summary", "summarize_legs"]
