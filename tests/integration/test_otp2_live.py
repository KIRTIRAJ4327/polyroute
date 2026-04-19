"""Live OTP2 integration tests.

These run against a local OpenTripPlanner 2 instance (see
``docker/otp2-toronto/``). They are excluded from the default test run.

Run them with::

    pytest -m integration

If OTP2 isn't reachable the entire module skips with a clear reason.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest

from polyroute.adapters.otp2 import DEFAULT_BASE_URL, OTP2Adapter
from polyroute.core.types import JourneyRequest, Location, Mode

pytestmark = pytest.mark.integration


def _otp2_reachable(base_url: str) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/otp/routers/default", timeout=2.0)
    except (httpx.HTTPError, OSError):
        return False
    return r.status_code < 500


@pytest.fixture(scope="module")
def adapter() -> OTP2Adapter:
    if not _otp2_reachable(DEFAULT_BASE_URL):
        pytest.skip(
            f"OTP2 not reachable at {DEFAULT_BASE_URL}. "
            "Start it with `docker compose up` from docker/otp2-toronto/."
        )
    return OTP2Adapter()


# Test corridors. Times are next-Saturday-morning to avoid weekday peak
# while still hitting full transit service.
def _next_saturday_at(hour: int, minute: int = 0) -> datetime:
    today = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    days_until_saturday = (5 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_until_saturday)


CORRIDORS = [
    pytest.param(
        Location(43.6011, -79.5463, name="Fountainhead Rd, Mississauga"),
        Location(43.6777, -79.6248, name="Pearson T1"),
        id="fountainhead-to-yyz",
    ),
    pytest.param(
        Location(43.6453, -79.3806, name="Union Station"),
        Location(43.6777, -79.6248, name="Pearson T1"),
        id="union-to-yyz",
    ),
    pytest.param(
        Location(43.6366, -79.5358, name="Kipling Station"),
        Location(43.6777, -79.6248, name="Pearson T1"),
        id="kipling-to-yyz",
    ),
]


@pytest.mark.parametrize("origin,destination", CORRIDORS)
def test_corridor_returns_plausible_itineraries(adapter, origin, destination):
    req = JourneyRequest(
        origin=origin,
        destination=destination,
        departure_time=_next_saturday_at(6, 0),
        max_walking_m=2000.0,
    )

    itineraries = adapter.plan(req, num_itineraries=3)

    assert itineraries, "OTP2 returned no itineraries"
    for it in itineraries:
        assert it.legs, "itinerary has no legs"
        assert 5 < it.total_duration_min < 24 * 60, "duration outside plausible range"
        assert any(leg.mode != Mode.WALK for leg in it.legs), "all-walk itinerary"
        for leg in it.legs:
            assert leg.duration_min >= 0
