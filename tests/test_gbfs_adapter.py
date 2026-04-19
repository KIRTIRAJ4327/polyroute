"""Unit tests for the GBFS (Bike Share Toronto) adapter.

Fixture-based; no network. The adapter's ``stations()`` is exercised
indirectly through ``plan()`` via a stub client that returns canned
GBFS discovery / info / status payloads.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from polyroute.adapters.gbfs import (
    GBFSAdapter,
    Station,
    _bike_fare,
    _build_itinerary,
    _merge_stations,
    _nearest,
)
from polyroute.core.types import JourneyRequest, Location, Mode


FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_merge_drops_decommissioned_stations():
    info = _load("gbfs_station_information.json")
    status = _load("gbfs_station_status.json")
    merged = _merge_stations(info, status)
    ids = {s.station_id for s in merged}
    assert "7001" in ids
    assert "7002" in ids
    assert "7003" in ids
    # 7004 is marked is_installed=0 and must be filtered
    assert "7004" not in ids


def test_merge_copies_availability_from_status():
    info = _load("gbfs_station_information.json")
    status = _load("gbfs_station_status.json")
    merged = {s.station_id: s for s in _merge_stations(info, status)}
    assert merged["7001"].bikes_available == 5
    assert merged["7002"].bikes_available == 0
    assert merged["7003"].bikes_available == 12
    assert merged["7002"].docks_available == 35


def test_nearest_requires_available_bikes():
    stations = [
        Station("a", "A", 43.645, -79.395, 20, 0, 20, True, True),
        Station("b", "B", 43.646, -79.394, 20, 7, 13, True, True),
    ]
    origin = Location(43.645, -79.395, name="orig")
    # Station a is closest but has no bikes — must fall through to b
    picked = _nearest(stations, origin, max_m=2000, need_bikes=True)
    assert picked is not None and picked.station_id == "b"


def test_nearest_returns_none_past_radius():
    stations = [
        Station("a", "A", 43.700, -79.400, 20, 5, 15, True, True),
    ]
    picked = _nearest(
        stations,
        Location(43.645, -79.395, name="origin"),
        max_m=200,
        need_bikes=True,
    )
    assert picked is None


def test_nearest_honors_dock_requirement():
    stations = [
        Station("a", "A", 43.645, -79.395, 20, 20, 0, True, True),  # full
        Station("b", "B", 43.650, -79.395, 20, 5, 15, True, True),
    ]
    picked = _nearest(stations, Location(43.645, -79.395), max_m=2000, need_docks=True)
    assert picked is not None and picked.station_id == "b"


def test_bike_fare_caps_at_day_pass():
    # 30 min at $0.12/min = $3.60 + $1 unlock = $4.60 — well under cap
    assert _bike_fare(30) == pytest.approx(4.60)
    # 500 min would exceed cap — clamp to $15
    assert _bike_fare(500) == pytest.approx(15.00)


# ---------------------------------------------------------------------------
# Itinerary construction
# ---------------------------------------------------------------------------


def test_build_itinerary_produces_walk_bike_walk():
    origin = Location(43.6440, -79.3970, name="origin")
    dest = Location(43.6620, -79.3840, name="dest")
    start = Station("7001", "King/Spadina", 43.6458, -79.3957, 31, 5, 26, True, True)
    end = Station("7002", "Bay/College", 43.6610, -79.3848, 35, 7, 28, True, True)

    req = JourneyRequest(origin=origin, destination=dest)
    depart = datetime(2026, 4, 22, 9, 0)
    itin = _build_itinerary(req, start, end, depart, operator="Bike Share Toronto")

    assert [leg.mode for leg in itin.legs] == [Mode.WALK, Mode.BIKE_SHARE, Mode.WALK]
    # Time-continuous
    assert itin.legs[0].end_time == itin.legs[1].start_time
    assert itin.legs[1].end_time == itin.legs[2].start_time
    # Bike leg carries operator and a non-zero fare
    assert itin.legs[1].operator == "Bike Share Toronto"
    assert itin.legs[1].cost_cad > 0


# ---------------------------------------------------------------------------
# Adapter end-to-end with a stubbed httpx client
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self.payload


class _FakeClient:
    """Minimal httpx.Client stand-in that routes by URL substring."""

    def __init__(self, route_map: dict[str, dict]):
        self.route_map = route_map
        self.requested: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> _FakeResponse:
        self.requested.append(url)
        for needle, payload in self.route_map.items():
            if needle in url:
                return _FakeResponse(payload)
        raise AssertionError(f"unexpected GBFS URL: {url}")


def _canned_discovery() -> dict:
    return {
        "data": {
            "en": {
                "feeds": [
                    {
                        "name": "station_information",
                        "url": "https://example.test/station_information.json",
                    },
                    {
                        "name": "station_status",
                        "url": "https://example.test/station_status.json",
                    },
                ]
            }
        }
    }


def _fake_client() -> _FakeClient:
    return _FakeClient(
        {
            "gbfs.json": _canned_discovery(),
            "station_information.json": _load("gbfs_station_information.json"),
            "station_status.json": _load("gbfs_station_status.json"),
        }
    )


def test_plan_returns_bike_share_itinerary():
    # Origin near station 7001 (King/Spadina); destination near 7002 (Bay/College)
    origin = Location(43.6440, -79.3970, name="Origin")
    dest = Location(43.6620, -79.3840, name="Destination")
    req = JourneyRequest(
        origin=origin,
        destination=dest,
        departure_time=datetime(2026, 4, 22, 9, 0),
    )

    adapter = GBFSAdapter(
        discovery_url="https://example.test/gbfs.json",
        client=_fake_client(),
    )
    results = adapter.plan(req)
    assert len(results) == 1
    itin = results[0]
    modes = [leg.mode for leg in itin.legs]
    assert modes == [Mode.WALK, Mode.BIKE_SHARE, Mode.WALK]
    # Routed via the available stations (7002 has 0 bikes but 7001→7002 works
    # because we need bikes at origin-side, docks at destination-side)
    # so first station name must match the one that had bikes
    assert "King" in itin.legs[0].destination.name
    assert "Bay" in itin.legs[2].origin.name


def test_plan_returns_empty_with_luggage():
    adapter = GBFSAdapter(
        discovery_url="https://example.test/gbfs.json",
        client=_fake_client(),
    )
    req = JourneyRequest(
        origin=Location(43.6440, -79.3970),
        destination=Location(43.6620, -79.3840),
        has_luggage=True,
    )
    assert adapter.plan(req) == []


def test_plan_returns_empty_when_no_nearby_station():
    adapter = GBFSAdapter(
        discovery_url="https://example.test/gbfs.json",
        client=_fake_client(),
        max_access_m=50.0,  # tight radius — no station within
    )
    req = JourneyRequest(
        origin=Location(43.6440, -79.3970),
        destination=Location(43.6620, -79.3840),
    )
    assert adapter.plan(req) == []
