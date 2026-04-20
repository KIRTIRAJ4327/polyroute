"""Tests for the FastAPI server.

Uses FastAPI's TestClient. The Planner is swapped via ``set_planner``
so the server is exercised end-to-end without needing OTP2, GBFS,
or a live rideshare source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest

from polyroute.core.planner import Planner
from polyroute.core.types import Itinerary, JourneyRequest, Leg, Location, Mode


pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from polyroute.api.server import app, set_explainer, set_planner  # noqa: E402
from polyroute.llm import LLMExplainer  # noqa: E402


FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead")
YYZ = Location(43.6777, -79.6248, name="YYZ")


def _single_leg(mode: Mode, depart: datetime, duration_min: int, cost: float) -> Itinerary:
    leg = Leg(
        mode=mode,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=depart,
        end_time=depart + timedelta(minutes=duration_min),
        distance_m=20_000.0,
        cost_cad=cost,
        reliability_sigma_min=2.0,
        operator="Test",
    )
    return Itinerary(legs=[leg])


@dataclass
class FakeRideshare:
    calls: list[JourneyRequest] = field(default_factory=list)

    def estimate(self, req: JourneyRequest) -> Itinerary:
        self.calls.append(req)
        depart = req.departure_time or datetime.now()
        return _single_leg(Mode.RIDESHARE, depart, 25, 48.00)


@dataclass
class FakeTransit:
    calls: list[JourneyRequest] = field(default_factory=list)

    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
        self.calls.append(req)
        depart = req.departure_time or datetime.now()
        return [_single_leg(Mode.SUBWAY, depart, 60, 3.35)]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_planner():
    """Tests get a fresh planner; avoid cross-test state leakage."""
    # Test body may override via ``set_planner`` — we don't assert a default
    # (the module-level planner at import time depends on env vars).
    yield
    # Reset explainer to None (rule-based) after each test so LLM-injecting
    # tests don't leak into plain /plan tests.
    set_explainer(None)


# ---------------------------------------------------------------------------
# Health / presets
# ---------------------------------------------------------------------------


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_presets(client: TestClient):
    r = client.get("/presets")
    assert r.status_code == 200
    body = r.json()
    assert "fountainhead" in body
    assert "yyz" in body
    assert body["yyz"]["lat"] == pytest.approx(43.6777)


# ---------------------------------------------------------------------------
# /plan endpoint
# ---------------------------------------------------------------------------


def _plan_payload() -> dict:
    return {
        "origin": {"lat": 43.6011, "lon": -79.5463, "name": "Fountainhead"},
        "destination": {"lat": 43.6777, "lon": -79.6248, "name": "YYZ"},
        "depart_at": "2026-04-22T06:00:00",
    }


def test_plan_uses_injected_planner(client: TestClient):
    set_planner(
        Planner(
            rideshare=FakeRideshare(),
            anchors=[],
            fallback=None,
        )
    )
    r = client.post("/plan", json=_plan_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["candidates_generated"] == 1
    assert body["pareto_optimal"] == 1
    assert len(body["itineraries"]) == 1
    itin = body["itineraries"][0]
    assert itin["legs"][0]["mode"] == "rideshare"
    assert "rideshare" in body["sources"]


def test_plan_surfaces_fan_out_sources(client: TestClient):
    set_planner(
        Planner(
            transit=FakeTransit(),
            rideshare=FakeRideshare(),
            anchors=[],
            fallback=None,
        )
    )
    r = client.post("/plan", json=_plan_payload())
    body = r.json()
    # With both transit and rideshare wired, compose_first_mile is
    # advertised even though we gave zero anchors (it just doesn't
    # produce extra candidates). That's fine — we are reporting wiring.
    assert "transit" in body["sources"]
    assert "rideshare" in body["sources"]
    assert "compose_first_mile" in body["sources"]


def test_plan_reports_mock_fallback_when_only_fallback_wired(client: TestClient):
    from polyroute.adapters.mock_toronto import generate_candidates

    set_planner(Planner(anchors=[], fallback=generate_candidates))
    r = client.post("/plan", json=_plan_payload())
    body = r.json()
    assert body["sources"] == ["mock_fallback"]
    assert body["candidates_generated"] >= 1


def test_plan_rejects_missing_origin(client: TestClient):
    set_planner(Planner(rideshare=FakeRideshare(), anchors=[], fallback=None))
    r = client.post("/plan", json={"destination": {"lat": 0, "lon": 0}})
    assert r.status_code == 422  # pydantic validation


def test_plan_honors_arrive_by(client: TestClient):
    set_planner(Planner(rideshare=FakeRideshare(), anchors=[], fallback=None))
    payload = _plan_payload()
    # FakeRideshare takes 25 min; a hard deadline 10 min from departure
    # makes the 90%-confidence arrival infeasible → 0 scored results
    payload["arrive_by"] = "2026-04-22T06:10:00"
    r = client.post("/plan", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["pareto_optimal"] == 0


# ---------------------------------------------------------------------------
# LLM explainer wiring
# ---------------------------------------------------------------------------


def test_plan_uses_rule_based_when_no_explainer(client: TestClient):
    set_planner(Planner(rideshare=FakeRideshare(), anchors=[], fallback=None))
    set_explainer(None)
    r = client.post("/plan", json=_plan_payload())
    body = r.json()
    assert body["itineraries"][0]["explanation_source"] == "rule-based"


def test_plan_uses_llm_when_explainer_wired(client: TestClient):
    set_planner(Planner(rideshare=FakeRideshare(), anchors=[], fallback=None))
    set_explainer(LLMExplainer(generate=lambda _prompt: "LLM-generated tradeoff text."))
    r = client.post("/plan", json=_plan_payload())
    body = r.json()
    first = body["itineraries"][0]
    assert first["explanation_source"] == "llm"
    assert first["explanation"] == "LLM-generated tradeoff text."


def test_plan_falls_back_when_llm_errors(client: TestClient):
    set_planner(Planner(rideshare=FakeRideshare(), anchors=[], fallback=None))

    def _broken(_prompt: str) -> str:
        raise RuntimeError("provider down")

    set_explainer(LLMExplainer(generate=_broken))
    r = client.post("/plan", json=_plan_payload())
    body = r.json()
    first = body["itineraries"][0]
    assert first["explanation_source"] == "rule-based-fallback"
    # Rule-based text should appear — not empty
    assert first["explanation"]


def test_default_explainer_none_without_env(monkeypatch):
    monkeypatch.delenv("POLYROUTE_LLM_PROVIDER", raising=False)
    from polyroute.api.server import default_explainer

    assert default_explainer() is None


def test_default_explainer_anthropic(monkeypatch):
    monkeypatch.setenv("POLYROUTE_LLM_PROVIDER", "anthropic")
    from polyroute.api.server import default_explainer

    ex = default_explainer()
    assert ex is not None
    assert isinstance(ex, LLMExplainer)


def test_default_explainer_unknown_provider_returns_none(monkeypatch):
    monkeypatch.setenv("POLYROUTE_LLM_PROVIDER", "bogus-provider")
    from polyroute.api.server import default_explainer

    assert default_explainer() is None


def test_default_explainer_azure_needs_deployment(monkeypatch):
    monkeypatch.setenv("POLYROUTE_LLM_PROVIDER", "azure")
    monkeypatch.delenv("POLYROUTE_LLM_MODEL", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    from polyroute.api.server import default_explainer

    # Without a deployment name, azure path refuses rather than misbehaving
    assert default_explainer() is None


# ---------------------------------------------------------------------------
# CORS env var
# ---------------------------------------------------------------------------


def test_cors_origins_defaults_to_wildcard(monkeypatch):
    monkeypatch.delenv("POLYROUTE_CORS_ORIGINS", raising=False)
    from polyroute.api.server import _cors_origins

    assert _cors_origins() == ["*"]


def test_cors_origins_parses_comma_separated(monkeypatch):
    monkeypatch.setenv(
        "POLYROUTE_CORS_ORIGINS",
        "https://polyroute.dev, https://app.polyroute.dev ,",
    )
    from polyroute.api.server import _cors_origins

    assert _cors_origins() == ["https://polyroute.dev", "https://app.polyroute.dev"]
