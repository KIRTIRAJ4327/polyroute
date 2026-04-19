"""Live GBFS integration tests — Bike Share Toronto.

Skipped by default. Opt in with::

    pytest -m integration tests/integration/test_gbfs_live.py

Skips cleanly if the feed is unreachable so developers without
internet can still run ``pytest -m integration`` locally.
"""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from polyroute.adapters.gbfs import DEFAULT_DISCOVERY_URL, GBFSAdapter
from polyroute.core.types import JourneyRequest, Location, Mode


pytestmark = pytest.mark.integration


def _feed_reachable(url: str) -> bool:
    try:
        httpx.get(url, timeout=5.0).raise_for_status()
        return True
    except (httpx.HTTPError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="module")
def adapter() -> GBFSAdapter:
    if not _feed_reachable(DEFAULT_DISCOVERY_URL):
        pytest.skip(f"Bike Share Toronto GBFS not reachable at {DEFAULT_DISCOVERY_URL}")
    return GBFSAdapter()


def test_station_list_is_nontrivial(adapter: GBFSAdapter) -> None:
    stations = adapter.stations()
    assert len(stations) > 100
    # At least some stations have bikes
    assert sum(1 for s in stations if s.bikes_available > 0) > 10


def test_downtown_corridor_returns_bike_share_itinerary(adapter: GBFSAdapter) -> None:
    # King/Spadina → Bay/College — downtown core, station density is high
    req = JourneyRequest(
        origin=Location(43.6458, -79.3957, name="King/Spadina"),
        destination=Location(43.6610, -79.3848, name="Bay/College"),
        departure_time=datetime.now(),
    )
    itineraries = adapter.plan(req)
    assert len(itineraries) == 1
    modes = [leg.mode for leg in itineraries[0].legs]
    assert modes == [Mode.WALK, Mode.BIKE_SHARE, Mode.WALK]
