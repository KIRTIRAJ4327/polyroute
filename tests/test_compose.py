"""Tests for the composition strategy module.

These tests use fake ``TransitSource`` and ``RideshareEstimator`` impls
to keep the module unit-testable with zero external dependencies — no
network, no Docker, no rate card revalidation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from polyroute.core.compose import (
    Anchor,
    ComposeOptions,
    compose_first_mile,
    load_gta_anchors,
)
from polyroute.core.types import Itinerary, JourneyRequest, Leg, Location, Mode


FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead Rd, Mississauga")
YYZ = Location(43.6777, -79.6248, name="Toronto Pearson Terminal 1")
KIPLING = Location(43.6372, -79.5355, name="Kipling Station")
UNION = Location(43.6452, -79.3806, name="Union Station")


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeRideshare:
    """Returns a single RIDESHARE leg with a fixed 10-minute duration."""

    duration_min: float = 10.0
    cost_cad: float = 15.0

    def estimate(self, req: JourneyRequest) -> Itinerary:
        depart = req.departure_time or datetime(2026, 4, 22, 6, 0)
        leg = Leg(
            mode=Mode.RIDESHARE,
            origin=req.origin,
            destination=req.destination,
            start_time=depart,
            end_time=depart + timedelta(minutes=self.duration_min),
            distance_m=5_000.0,
            cost_cad=self.cost_cad,
            route_name="Estimate only — not a live price",
            operator="Test rideshare",
            reliability_sigma_min=5.0,
        )
        return Itinerary(legs=[leg])


@dataclass
class FakeTransit:
    """Returns ``count`` transit itineraries, each one a 30-min SUBWAY leg
    starting from whatever departure the caller asked for.

    Tracks the requests it sees so tests can assert on the anchor-query
    contract (departure_time should equal the rideshare arrival).
    """

    count: int = 2
    requests_seen: list[JourneyRequest] | None = None

    def __post_init__(self) -> None:
        if self.requests_seen is None:
            self.requests_seen = []

    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
        assert self.requests_seen is not None
        self.requests_seen.append(req)
        depart = req.departure_time or datetime(2026, 4, 22, 6, 0)
        out: list[Itinerary] = []
        for i in range(min(self.count, num_itineraries)):
            leg = Leg(
                mode=Mode.SUBWAY,
                origin=req.origin,
                destination=req.destination,
                start_time=depart,
                end_time=depart + timedelta(minutes=30 + i * 5),
                distance_m=12_000.0,
                cost_cad=3.35,
                route_name=f"Line {2 - i}",
                operator="TTC",
                reliability_sigma_min=2.0,
            )
            out.append(Itinerary(legs=[leg]))
        return out


# ---------------------------------------------------------------------------
# Anchor loading
# ---------------------------------------------------------------------------


def test_load_gta_anchors_returns_expected_set():
    anchors = load_gta_anchors()
    ids = {a.id for a in anchors}
    # CLAUDE.md §7 explicitly names these
    for required in ("kipling", "islington", "bloor-yonge", "dundas-west", "union"):
        assert required in ids
    # Every anchor has real lat/lon in the GTA bounding box
    for a in anchors:
        assert 43.4 < a.location.lat < 44.0
        assert -80.0 < a.location.lon < -79.0
        assert a.location.name == a.name


# ---------------------------------------------------------------------------
# compose_first_mile
# ---------------------------------------------------------------------------


def _make_req() -> JourneyRequest:
    return JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 22, 6, 0),
    )


def _two_anchors() -> list[Anchor]:
    return [
        Anchor(
            id="kipling",
            name="Kipling Station",
            operator="TTC",
            location=KIPLING,
            modes=("subway", "bus"),
        ),
        Anchor(
            id="union",
            name="Union Station",
            operator="Metrolinx",
            location=UNION,
            modes=("subway", "train"),
        ),
    ]


def test_compose_generates_one_per_anchor_transit_pair():
    transit = FakeTransit(count=2)
    rideshare = FakeRideshare()
    req = _make_req()

    composed = compose_first_mile(req, transit, rideshare, _two_anchors())

    # 2 anchors * 2 transit itineraries each
    assert len(composed) == 4
    for itin in composed:
        assert itin.legs[0].mode == Mode.RIDESHARE
        assert itin.legs[-1].mode == Mode.SUBWAY


def test_compose_stitches_time_continuously():
    transit = FakeTransit(count=1)
    rideshare = FakeRideshare(duration_min=10.0)
    req = _make_req()

    composed = compose_first_mile(req, transit, rideshare, _two_anchors())

    for itin in composed:
        first_mile_end = itin.legs[0].end_time
        transit_start = itin.legs[1].start_time
        # Transit leg starts exactly when rideshare leg ends
        assert first_mile_end == transit_start


def test_compose_respects_max_anchors():
    transit = FakeTransit(count=1)
    rideshare = FakeRideshare()
    req = _make_req()

    composed = compose_first_mile(
        req,
        transit,
        rideshare,
        _two_anchors(),
        options=ComposeOptions(per_anchor_transit_count=1, max_anchors=1),
    )
    assert len(composed) == 1


def test_compose_transit_request_uses_anchor_as_origin():
    transit = FakeTransit(count=1)
    rideshare = FakeRideshare(duration_min=12.0)
    req = _make_req()

    compose_first_mile(req, transit, rideshare, _two_anchors())

    assert transit.requests_seen is not None
    assert len(transit.requests_seen) == 2
    # Kipling anchor → first transit request's origin
    assert transit.requests_seen[0].origin == KIPLING
    assert transit.requests_seen[0].destination == YYZ
    # Transit departure is rideshare arrival, not the original request time
    expected_depart = datetime(2026, 4, 22, 6, 0) + timedelta(minutes=12)
    assert transit.requests_seen[0].departure_time == expected_depart


def test_compose_skips_anchor_when_transit_returns_nothing():
    class EmptyTransit:
        def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
            return []

    composed = compose_first_mile(_make_req(), EmptyTransit(), FakeRideshare(), _two_anchors())
    assert composed == []


def test_compose_forwards_constraints_to_transit():
    transit = FakeTransit(count=1)
    rideshare = FakeRideshare()
    req = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 22, 6, 0),
        arrive_by=datetime(2026, 4, 22, 8, 0),
        has_luggage=True,
        max_walking_m=500.0,
    )

    compose_first_mile(req, transit, rideshare, _two_anchors()[:1])

    assert transit.requests_seen is not None
    forwarded = transit.requests_seen[0]
    assert forwarded.arrive_by == req.arrive_by
    assert forwarded.has_luggage is True
    assert forwarded.max_walking_m == pytest.approx(500.0)
