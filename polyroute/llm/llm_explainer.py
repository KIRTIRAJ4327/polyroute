"""Model-agnostic LLM explainer.

Drop-in replacement for the rule-based ``explain()`` in
``polyroute.llm.explainer``. Same inputs (``ScoredItinerary`` and the
peer list), same contract (return a short tradeoff paragraph), but the
sentences come from an LLM rather than a handful of if-statements.

Design notes:

- **Provider-agnostic.** ``LLMExplainer`` takes a ``Callable[[str], str]``
  — prompt in, completion out. Concrete providers (Anthropic, OpenAI,
  Azure AI Foundry) live in ``providers`` and return that callable.
  Tests use an in-memory fake.
- **SDKs are lazy-imported.** Installing polyroute does not pull the
  anthropic / openai SDKs unless you opt in via the ``llm`` extra.
- **Rule-based is the fallback.** If the LLM call raises, we fall back
  to ``explainer.explain`` so the user still gets *something*. Errors
  are surfaced through the returned ``ExplainResult`` so callers / UI
  can tell "this was generated" from "this was rule-based."

See CLAUDE.md §12 for the provider matrix and why we don't hard-code
one vendor.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.types import Mode
from ..core.pareto import ScoredItinerary
from . import explainer as rule_based


Generate = Callable[[str], str]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


SYSTEM_INSTRUCTIONS = (
    "You explain multi-modal transit tradeoffs to Toronto commuters. "
    "Write 2–3 plain sentences. No marketing language, no bullet lists, "
    "no emoji. Focus on why this option might or might not suit the "
    "rider vs the named alternatives. Quote dollar amounts and time in "
    "minutes. Never invent routes, agencies, or fares — only use what "
    "is in the structured data."
)


def _itinerary_payload(s: ScoredItinerary) -> dict:
    it = s.itinerary
    legs = []
    for leg in it.legs:
        legs.append(
            {
                "mode": leg.mode.value,
                "route": leg.route_name,
                "operator": leg.operator,
                "duration_min": round(leg.duration_min, 1),
                "distance_m": round(leg.distance_m),
                "cost_cad": round(leg.cost_cad, 2),
            }
        )
    return {
        "label": s.label,
        "total_duration_min": round(it.total_duration_min, 1),
        "total_cost_cad": round(it.total_cost_cad, 2),
        "num_transfers": it.num_transfers,
        "walking_distance_m": round(it.walking_distance_m),
        "reliability_sigma_min": round(it.reliability_sigma_min, 1),
        "modes": [m.value for m in it.modes_used if m != Mode.WALK],
        "legs": legs,
    }


def build_prompt(s: ScoredItinerary, others: list[ScoredItinerary]) -> str:
    """Serialize option + peers as a JSON-in-text prompt."""
    payload = {
        "instructions": SYSTEM_INSTRUCTIONS,
        "option": _itinerary_payload(s),
        "alternatives": [_itinerary_payload(o) for o in others if o is not s],
    }
    return (
        "You will be given one candidate itinerary and the alternatives it "
        "is being compared against. Return only the explanation text — "
        "no preface, no JSON, no headings.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------


@dataclass
class ExplainResult:
    """Output bundle: the text plus provenance so the UI can distinguish
    LLM output from the rule-based fallback."""

    text: str
    source: str  # "llm" | "rule-based-fallback" | "rule-based"
    error: Optional[str] = None


@dataclass
class LLMExplainer:
    """Explainer backed by an arbitrary text-in / text-out callable.

    Example:
        generate = anthropic_generate(model="claude-sonnet-4-6")
        explainer = LLMExplainer(generate=generate)
        result = explainer.explain(scored[0], scored)
    """

    generate: Generate
    max_output_chars: int = 600
    # When True, any exception from ``generate`` falls back to the
    # rule-based explainer. Set False in tests where you want to assert
    # the raw failure mode.
    fallback_on_error: bool = True

    def explain(self, s: ScoredItinerary, others: list[ScoredItinerary]) -> ExplainResult:
        prompt = build_prompt(s, others)
        try:
            raw = self.generate(prompt)
        except Exception as exc:
            if not self.fallback_on_error:
                raise
            return ExplainResult(
                text=rule_based.explain(s, others),
                source="rule-based-fallback",
                error=str(exc),
            )
        text = _clean_completion(raw)[: self.max_output_chars]
        if not text:
            return ExplainResult(
                text=rule_based.explain(s, others),
                source="rule-based-fallback",
                error="empty completion",
            )
        return ExplainResult(text=text, source="llm")


def _clean_completion(raw: str) -> str:
    """Trim whitespace and strip stray markdown fences if the model adds them."""
    text = (raw or "").strip()
    if text.startswith("```"):
        # Drop the first fence line and anything after the closing fence
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


# ---------------------------------------------------------------------------
# Provider adapters (lazy imports — only load the SDK you actually use)
# ---------------------------------------------------------------------------


@dataclass
class ProviderConfig:
    """Common knobs across providers. Everything optional — env vars
    supply defaults where sensible."""

    model: str = ""
    api_key: Optional[str] = None
    max_tokens: int = 400
    temperature: float = 0.2
    extra: dict = field(default_factory=dict)


def anthropic_generate(model: str = "claude-sonnet-4-6", **kw) -> Generate:
    """Return a ``Generate`` backed by the Anthropic Messages API.

    Requires ``pip install polyroute[llm]`` (or ``pip install anthropic``).
    Reads ``ANTHROPIC_API_KEY`` from the environment unless ``api_key``
    is passed via kwargs.
    """
    cfg = ProviderConfig(model=model, **kw)

    def _generate(prompt: str) -> str:
        from anthropic import Anthropic  # lazy

        client = Anthropic(api_key=cfg.api_key or os.getenv("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            system=SYSTEM_INSTRUCTIONS,
            messages=[{"role": "user", "content": prompt}],
        )
        # Messages API returns a list of content blocks; join all text blocks
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(parts)

    return _generate


def openai_generate(model: str = "gpt-4o-mini", **kw) -> Generate:
    """Return a ``Generate`` backed by OpenAI Chat Completions.

    Requires ``pip install openai``. Reads ``OPENAI_API_KEY`` from env.
    """
    cfg = ProviderConfig(model=model, **kw)

    def _generate(prompt: str) -> str:
        from openai import OpenAI  # lazy

        client = OpenAI(api_key=cfg.api_key or os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    return _generate


def azure_foundry_generate(
    deployment: str,
    endpoint: Optional[str] = None,
    api_version: str = "2024-10-21",
    **kw,
) -> Generate:
    """Return a ``Generate`` backed by Azure AI Foundry / Azure OpenAI.

    Uses the OpenAI Python SDK in Azure mode. Requires
    ``pip install openai``. Reads ``AZURE_OPENAI_API_KEY`` and
    ``AZURE_OPENAI_ENDPOINT`` if not passed.
    """
    cfg = ProviderConfig(model=deployment, **kw)

    def _generate(prompt: str) -> str:
        from openai import AzureOpenAI  # lazy

        client = AzureOpenAI(
            api_key=cfg.api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_version=api_version,
        )
        resp = client.chat.completions.create(
            model=cfg.model,  # deployment name in Azure
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    return _generate
