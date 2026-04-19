"""Unit tests for the rideshare heuristic estimator.

Deterministic — no network. The estimator is a pure function of
(rate_card, origin, destination, depart_at).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from polyroute.adapters.rideshare_heuristic import (
    RateCard,
    RideshareHeuristic,
    _compute_fare,
    _haversine_m,
    surge_multiplier,
)
from polyroute.core.types import JourneyRequest, Location, Mode


FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead Rd, Mississauga")
YYZ = Location(43.6777, -79.6248, name="Toronto Pearson Terminal 1")


def test_haversine_matches_known_corridor():
    # Fountainhead → YYZ is ~12 km straight-line.
    km = _haversine_m(FOUNTAINHEAD, YYZ) / 1000.0
    assert 10.0 < km < 14.0


def test_compute_fare_honors_minimum():
    card = RateCard(
        base_fare=3.40,
        booking_fee=2.75,
        per_km=1.15,
        per_minute=0.38,
        minimum_fare=7.00,
    )
    # A 100 m / 1 min trip would otherwise price below minimum.
    fare = _compute_fare(card, distance_m=100.0, duration_min=1.0, multiplier=1.0)
    assert fare == pytest.approx(7.00)


def test_compute_fare_applies_surge_before_booking_fee():
    card = RateCard(
        base_fare=3.00,
        booking_fee=2.00,
        per_km=1.00,
        per_minute=0.50,
        minimum_fare=0.0,
    )
    # 10 km, 20 min, surge 2x
    # subtotal = (3 + 10 + 10) * 2 = 46
    # total = 46 + 2 = 48
    fare = _compute_fare(card, distance_m=10_000.0, duration_min=20.0, multiplier=2.0)
    assert fare == pytest.approx(48.00)


def test_surge_off_peak_is_one():
    # Wednesday 14:00 — mid-afternoon weekday, no rule fires
    mult, label = surge_multiplier(datetime(2026, 4, 22, 14, 0))
    assert mult == 1.0
    assert label == "off-peak"


def test_surge_weekday_morning_peak():
    mult, _ = surge_multiplier(datetime(2026, 4, 22, 8, 0))  # Wed 08:00
    assert mult == pytest.approx(1.5)


def test_surge_weekday_evening_peak():
    mult, _ = surge_multiplier(datetime(2026, 4, 22, 18, 0))  # Wed 18:00
    assert mult == pytest.approx(1.6)


def test_surge_overnight_weekend():
    mult, _ = surge_multiplier(datetime(2026, 4, 25, 2, 0))  # Sat 02:00
    assert mult == pytest.approx(1.9)


def test_estimate_returns_single_rideshare_leg():
    req = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 18, 6, 0, 0),  # Sat 06:00 — early morning
    )
    itinerary = RideshareHeuristic().estimate(req)
    assert len(itinerary.legs) == 1
    leg = itinerary.legs[0]
    assert leg.mode == Mode.RIDESHARE
    assert leg.route_name == "Estimate only — not a live price"
    assert "2026-04" in (leg.operator or "")


def test_estimate_is_deterministic():
    req = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 18, 6, 0, 0),
    )
    a = RideshareHeuristic().estimate(req).legs[0]
    b = RideshareHeuristic().estimate(req).legs[0]
    assert a.cost_cad == b.cost_cad
    assert a.end_time == b.end_time
    assert a.distance_m == b.distance_m


def test_estimate_peak_costs_more_than_off_peak():
    req_offpeak = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 22, 14, 0, 0),  # Wed 14:00
    )
    req_peak = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=datetime(2026, 4, 22, 8, 0, 0),  # Wed 08:00 peak
    )
    off = RideshareHeuristic().estimate(req_offpeak).legs[0].cost_cad
    peak = RideshareHeuristic().estimate(req_peak).legs[0].cost_cad
    assert peak > off
