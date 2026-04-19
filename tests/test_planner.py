"""Tests for the orchestrator.

Validates fan-out behavior, graceful degradation on adapter errors,
and fallback semantics. All network-free — real adapters are not
wired here; we pass fakes that implement the same Protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from polyroute.core.compose import Anchor, ComposeOptions
from polyroute.core.planner import Planner
from polyroute.core.types import Itinerary, JourneyRequest, Leg, Location, Mode


FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead")
YYZ = Location(43.6777, -79.6248, name="YYZ")
KIPLING = Location(43.6372, -79.5355, name="Kipling")


def _one_leg_itinerary(mode: Mode, depart: datetime, duration_min: int, cost: float) -> Itinerary:
    leg = Leg(
        mode=mode,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=depart,
        end_time=depart + timedelta(minutes=duration_min),
        distance_m=20_000.0,
        cost_cad=cost,
        reliability_sigma_min=2.0,
    )
    return Itinerary(legs=[leg])


@dataclass
class FakeTransit:
    calls: list[JourneyRequest] = field(default_factory=list)
    itins: int = 1

    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
        self.calls.append(req)
        depart = req.departure_time or datetime(2026, 4, 22, 6, 0)
        return [
            _one_leg_itinerary(Mode.SUBWAY, depart, 40 + i * 5, 3.35)
            for i in range(min(self.itins, num_itineraries))
        ]


@dataclass
class FakeRideshare:
    calls: list[JourneyRequest] = field(default_factory=list)

    def estimate(self, req: JourneyRequest) -> Itinerary:
        self.calls.append(req)
        depart = req.departure_time or datetime(2026, 4, 22, 6, 0)
        return _one_leg_itinerary(Mode.RIDESHARE, depart, 25, 48.0)


@dataclass
class FakeBikeShare:
    calls: list[JourneyRequest] = field(default_factory=list)

    def plan(self, req: JourneyRequest, num_itineraries: int = 1) -> list[Itinerary]:
        self.calls.append(req)
        depart = req.departure_time or datetime(2026, 4, 22, 6, 0)
        return [_one_leg_itinerary(Mode.BIKE_SHARE, depart, 50, 5.0)]


def _req() -> JourneyRequest:
    return JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 22, 6, 0),
    )


def _two_anchors() -> list[Anchor]:
    return [
        Anchor(
            id="kipling",
            name="Kipling",
            operator="TTC",
            location=KIPLING,
            modes=("subway",),
        ),
    ]


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


def test_empty_planner_returns_empty():
    assert Planner(anchors=[]).plan(_req()) == []


def test_fallback_used_when_no_adapters():
    marker = _one_leg_itinerary(Mode.WALK, datetime(2026, 4, 22, 6, 0), 90, 0.0)
    planner = Planner(anchors=[], fallback=lambda _: [marker])
    out = planner.plan(_req())
    assert out == [marker]


def test_fallback_skipped_when_live_adapters_produce_candidates():
    fallback_called = []
    planner = Planner(
        transit=FakeTransit(),
        anchors=[],
        fallback=lambda r: fallback_called.append(r) or [],
    )
    out = planner.plan(_req())
    assert len(out) >= 1
    assert fallback_called == []


# ---------------------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------------------


def test_fans_out_direct_plus_composed():
    transit = FakeTransit()
    rideshare = FakeRideshare()
    bike_share = FakeBikeShare()

    planner = Planner(
        transit=transit,
        rideshare=rideshare,
        bike_share=bike_share,
        anchors=_two_anchors(),
        compose_opts=ComposeOptions(per_anchor_transit_count=1, max_anchors=1),
    )
    out = planner.plan(_req())

    modes = [tuple(leg.mode for leg in it.legs) for it in out]
    # Expected:
    #  - 1 direct transit itinerary
    #  - 1 direct rideshare itinerary
    #  - 1 direct bike-share itinerary
    #  - 1 composed rideshare → transit itinerary
    assert (Mode.SUBWAY,) in modes  # direct transit
    assert (Mode.RIDESHARE,) in modes  # direct rideshare
    assert (Mode.BIKE_SHARE,) in modes  # direct bike share
    assert (Mode.RIDESHARE, Mode.SUBWAY) in modes  # composed
    assert len(out) == 4


def test_fans_out_skips_missing_adapters():
    planner = Planner(rideshare=FakeRideshare(), anchors=[])
    out = planner.plan(_req())
    # Only the direct rideshare itinerary — no transit, no bike share,
    # no composition (composition needs both transit + rideshare)
    assert len(out) == 1
    assert out[0].legs[0].mode == Mode.RIDESHARE


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class _BrokenTransit:
    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
        raise RuntimeError("OTP2 down")


class _BrokenBikeShare:
    def plan(self, req: JourneyRequest, num_itineraries: int = 1) -> list[Itinerary]:
        raise RuntimeError("GBFS down")


def test_transit_failure_does_not_take_down_the_call():
    planner = Planner(
        transit=_BrokenTransit(),
        rideshare=FakeRideshare(),
        anchors=_two_anchors(),
    )
    out = planner.plan(_req())
    # Rideshare still produces a candidate; compose also skips because
    # the transit protocol raises mid-stitch
    assert any(it.legs[0].mode == Mode.RIDESHARE for it in out)


def test_bike_share_failure_isolated():
    planner = Planner(
        rideshare=FakeRideshare(),
        bike_share=_BrokenBikeShare(),
        anchors=[],
    )
    out = planner.plan(_req())
    # Just the rideshare itinerary; bike-share error swallowed
    assert len(out) == 1
    assert out[0].legs[0].mode == Mode.RIDESHARE


def test_fallback_triggered_when_every_live_adapter_fails():
    marker = _one_leg_itinerary(Mode.WALK, datetime(2026, 4, 22, 6, 0), 90, 0.0)
    planner = Planner(
        transit=_BrokenTransit(),
        bike_share=_BrokenBikeShare(),
        anchors=[],
        fallback=lambda _: [marker],
    )
    out = planner.plan(_req())
    assert out == [marker]


# ---------------------------------------------------------------------------
# Composition request forwarding
# ---------------------------------------------------------------------------


def test_composition_queries_transit_from_each_anchor():
    transit = FakeTransit()
    planner = Planner(
        transit=transit,
        rideshare=FakeRideshare(),
        anchors=_two_anchors(),
        compose_opts=ComposeOptions(per_anchor_transit_count=1, max_anchors=1),
    )
    planner.plan(_req())
    # FakeTransit will be called twice: once directly for req, once from
    # composition with origin=Kipling
    assert len(transit.calls) == 2
    direct, composed = transit.calls
    assert direct.origin == FOUNTAINHEAD
    assert composed.origin == KIPLING


# ---------------------------------------------------------------------------
# default_planner env var behavior
# ---------------------------------------------------------------------------


def test_default_planner_without_env_uses_fallback(monkeypatch):
    monkeypatch.delenv("POLYROUTE_OTP2_URL", raising=False)
    monkeypatch.delenv("POLYROUTE_GBFS_URL", raising=False)
    monkeypatch.delenv("POLYROUTE_DISABLE_FALLBACK", raising=False)

    from polyroute.core.planner import default_planner

    p = default_planner()
    assert p.transit is None
    assert p.bike_share is None
    assert p.rideshare is not None
    assert p.fallback is not None


def test_default_planner_honors_disable_fallback(monkeypatch):
    monkeypatch.setenv("POLYROUTE_DISABLE_FALLBACK", "1")
    monkeypatch.delenv("POLYROUTE_OTP2_URL", raising=False)
    monkeypatch.delenv("POLYROUTE_GBFS_URL", raising=False)

    from polyroute.core.planner import default_planner

    p = default_planner()
    assert p.fallback is None


def test_default_planner_wires_otp2_when_url_set(monkeypatch):
    monkeypatch.setenv("POLYROUTE_OTP2_URL", "http://example.test:8080")
    monkeypatch.delenv("POLYROUTE_GBFS_URL", raising=False)
    monkeypatch.delenv("POLYROUTE_DISABLE_FALLBACK", raising=False)

    from polyroute.core.planner import default_planner

    p = default_planner()
    assert p.transit is not None
    # Duck-type: OTP2Adapter has a .base_url attribute
    assert getattr(p.transit, "base_url", None) == "http://example.test:8080"


def test_default_planner_wires_gbfs_when_url_set(monkeypatch):
    monkeypatch.delenv("POLYROUTE_OTP2_URL", raising=False)
    monkeypatch.setenv("POLYROUTE_GBFS_URL", "http://example.test/gbfs.json")
    monkeypatch.delenv("POLYROUTE_DISABLE_FALLBACK", raising=False)

    from polyroute.core.planner import default_planner

    p = default_planner()
    assert p.bike_share is not None
    assert getattr(p.bike_share, "discovery_url", None) == "http://example.test/gbfs.json"
