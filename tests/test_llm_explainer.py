"""Tests for the LLM-backed explainer.

Zero-network: we pass in a fake ``Generate`` callable and assert on the
prompt that would have been sent plus the result wrapping. Providers
(Anthropic, OpenAI, Azure) are not tested here — that lives in the
integration suite once we have credentials configured.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from polyroute.core.pareto import ScoredItinerary
from polyroute.core.types import Itinerary, Leg, Location, Mode
from polyroute.llm.llm_explainer import (
    ExplainResult,
    LLMExplainer,
    build_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead")
YYZ = Location(43.6777, -79.6248, name="YYZ Terminal 1")


def _rideshare_only() -> ScoredItinerary:
    t0 = datetime(2026, 4, 22, 6, 0)
    leg = Leg(
        mode=Mode.RIDESHARE,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=t0,
        end_time=t0 + timedelta(minutes=25),
        distance_m=17_000.0,
        cost_cad=48.50,
        route_name="Estimate only — not a live price",
        operator="UberX-style",
        reliability_sigma_min=5.0,
    )
    return ScoredItinerary(
        itinerary=Itinerary(legs=[leg]),
        score=0.8,
        axis_values={"time": 25.0, "cost": 48.50, "effort": 0.0, "reliability": 5.0},
        label="Fastest",
    )


def _transit_only() -> ScoredItinerary:
    t0 = datetime(2026, 4, 22, 6, 0)
    bus = Leg(
        mode=Mode.BUS,
        origin=FOUNTAINHEAD,
        destination=Location(43.5935, -79.6428, name="Square One"),
        start_time=t0,
        end_time=t0 + timedelta(minutes=30),
        distance_m=6_000.0,
        cost_cad=3.35,
        route_name="26",
        operator="MiWay",
        reliability_sigma_min=4.0,
    )
    subway = Leg(
        mode=Mode.SUBWAY,
        origin=Location(43.6372, -79.5355, name="Kipling"),
        destination=Location(43.6452, -79.3806, name="Union"),
        start_time=t0 + timedelta(minutes=35),
        end_time=t0 + timedelta(minutes=70),
        distance_m=22_000.0,
        cost_cad=0.0,
        route_name="Line 2",
        operator="TTC",
        reliability_sigma_min=2.0,
    )
    up = Leg(
        mode=Mode.TRAIN,
        origin=Location(43.6452, -79.3806, name="Union"),
        destination=YYZ,
        start_time=t0 + timedelta(minutes=75),
        end_time=t0 + timedelta(minutes=100),
        distance_m=25_000.0,
        cost_cad=12.35,
        route_name="UP",
        operator="Metrolinx",
        reliability_sigma_min=2.5,
    )
    return ScoredItinerary(
        itinerary=Itinerary(legs=[bus, subway, up]),
        score=0.3,
        axis_values={
            "time": 100.0,
            "cost": 15.70,
            "effort": 10.0,
            "reliability": 5.12,
        },
        label="Cheapest",
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_build_prompt_includes_option_and_alternatives():
    option = _rideshare_only()
    alt = _transit_only()
    prompt = build_prompt(option, [option, alt])

    # Prompt should include a JSON block — load it back
    start = prompt.find("{")
    payload = json.loads(prompt[start:])
    assert payload["option"]["label"] == "Fastest"
    assert payload["option"]["total_cost_cad"] == pytest.approx(48.50)
    assert len(payload["alternatives"]) == 1
    assert payload["alternatives"][0]["label"] == "Cheapest"


def test_build_prompt_excludes_self_from_alternatives():
    option = _rideshare_only()
    prompt = build_prompt(option, [option])
    start = prompt.find("{")
    payload = json.loads(prompt[start:])
    assert payload["alternatives"] == []


def test_build_prompt_strips_walk_from_modes():
    """Walk glue is visual noise — summary modes list shouldn't repeat it."""
    t0 = datetime(2026, 4, 22, 6, 0)
    walk = Leg(
        mode=Mode.WALK,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=t0,
        end_time=t0 + timedelta(minutes=5),
        distance_m=400.0,
        cost_cad=0.0,
    )
    rideshare = Leg(
        mode=Mode.RIDESHARE,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=t0 + timedelta(minutes=5),
        end_time=t0 + timedelta(minutes=30),
        distance_m=17_000.0,
        cost_cad=48.50,
    )
    scored = ScoredItinerary(
        itinerary=Itinerary(legs=[walk, rideshare]),
        score=0.5,
        axis_values={"time": 25.0, "cost": 48.50, "effort": 4.0, "reliability": 5.0},
        label="Fastest",
    )
    prompt = build_prompt(scored, [scored])
    payload = json.loads(prompt[prompt.find("{") :])
    assert "walk" not in payload["option"]["modes"]
    assert "rideshare" in payload["option"]["modes"]


# ---------------------------------------------------------------------------
# LLMExplainer flow
# ---------------------------------------------------------------------------


def test_explainer_returns_llm_source_on_success():
    scored = _rideshare_only()
    explainer = LLMExplainer(
        generate=lambda _: "Fastest but priciest. Transit alternatives save real money."
    )
    out = explainer.explain(scored, [scored])
    assert isinstance(out, ExplainResult)
    assert out.source == "llm"
    assert "priciest" in out.text
    assert out.error is None


def test_explainer_strips_markdown_code_fences():
    scored = _rideshare_only()
    fenced = "```\nFastest but priciest.\n```"
    explainer = LLMExplainer(generate=lambda _: fenced)
    out = explainer.explain(scored, [scored])
    assert out.text == "Fastest but priciest."


def test_explainer_falls_back_to_rule_based_on_exception():
    scored = _rideshare_only()

    def boom(_: str) -> str:
        raise RuntimeError("no API key")

    explainer = LLMExplainer(generate=boom)
    out = explainer.explain(scored, [scored])
    assert out.source == "rule-based-fallback"
    assert out.error == "no API key"
    # Must still return a non-empty, human-usable sentence
    assert len(out.text) > 10


def test_explainer_falls_back_on_empty_completion():
    scored = _rideshare_only()
    explainer = LLMExplainer(generate=lambda _: "   ")
    out = explainer.explain(scored, [scored])
    assert out.source == "rule-based-fallback"
    assert out.error == "empty completion"
    assert len(out.text) > 10


def test_explainer_propagates_exception_when_fallback_disabled():
    scored = _rideshare_only()

    def boom(_: str) -> str:
        raise RuntimeError("deliberate")

    explainer = LLMExplainer(generate=boom, fallback_on_error=False)
    with pytest.raises(RuntimeError, match="deliberate"):
        explainer.explain(scored, [scored])


def test_explainer_truncates_over_long_completions():
    scored = _rideshare_only()
    explainer = LLMExplainer(generate=lambda _: "x" * 2000, max_output_chars=100)
    out = explainer.explain(scored, [scored])
    assert len(out.text) == 100
    assert out.source == "llm"


def test_explainer_prompt_receives_payload():
    """Regression guard: the generate callable must see the serialized prompt."""
    seen: list[str] = []

    def capture(prompt: str) -> str:
        seen.append(prompt)
        return "ok"

    scored = _transit_only()
    LLMExplainer(generate=capture).explain(scored, [scored, _rideshare_only()])
    assert len(seen) == 1
    assert "Toronto" in seen[0]
    assert '"label": "Cheapest"' in seen[0]
