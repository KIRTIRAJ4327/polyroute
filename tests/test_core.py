"""Tests for core types and Pareto scoring.

These tests assert the math, not the side effects. No OTP2, no LLM.
Run: python -m pytest tests/ -v
"""
from datetime import datetime, timedelta

import pytest

from polyroute.core import (
    Itinerary,
    JourneyRequest,
    Leg,
    Location,
    Mode,
    is_feasible,
    pareto_front,
    score_itineraries,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FOUNTAINHEAD = Location(lat=43.6011, lon=-79.5463, name="Fountainhead Rd")
YYZ = Location(lat=43.6777, lon=-79.6248, name="Toronto Pearson")
KIPLING = Location(lat=43.6366, lon=-79.5358, name="Kipling Station")

BASE_TIME = datetime(2026, 4, 18, 6, 0, 0)


def _make_leg(mode: Mode, start_offset_min: int, duration_min: int,
              cost: float, distance_m: float, sigma: float = 0.0) -> Leg:
    start = BASE_TIME + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=duration_min)
    return Leg(
        mode=mode,
        origin=FOUNTAINHEAD,
        destination=YYZ,
        start_time=start,
        end_time=end,
        distance_m=distance_m,
        cost_cad=cost,
        reliability_sigma_min=sigma,
    )


# ---------------------------------------------------------------------------
# Basic type math
# ---------------------------------------------------------------------------

def test_itinerary_totals():
    legs = [
        _make_leg(Mode.WALK, 0, 10, 0.0, 500),
        _make_leg(Mode.SUBWAY, 10, 20, 3.35, 8000),
        _make_leg(Mode.WALK, 30, 5, 0.0, 300),
    ]
    it = Itinerary(legs=legs)
    assert it.total_duration_min == 35
    assert it.total_cost_cad == pytest.approx(3.35)
    assert it.total_distance_m == 8800
    assert it.walking_distance_m == 800
    assert it.num_transfers == 0  # only one non-walk leg


def test_transfer_count():
    legs = [
        _make_leg(Mode.BUS, 0, 15, 3.35, 5000),
        _make_leg(Mode.WALK, 15, 3, 0.0, 200),
        _make_leg(Mode.SUBWAY, 18, 20, 0.0, 10000),
        _make_leg(Mode.WALK, 38, 2, 0.0, 150),
        _make_leg(Mode.TRAIN, 40, 25, 12.35, 20000),
    ]
    it = Itinerary(legs=legs)
    assert it.num_transfers == 2  # three non-walk legs → 2 transfers


def test_reliability_combines_as_sqrt_sum_variances():
    legs = [
        _make_leg(Mode.BUS, 0, 10, 0.0, 1000, sigma=3.0),
        _make_leg(Mode.TRAIN, 10, 20, 0.0, 10000, sigma=4.0),
    ]
    it = Itinerary(legs=legs)
    # sqrt(9 + 16) = 5
    assert it.reliability_sigma_min == pytest.approx(5.0)


def test_arrival_by_confidence():
    legs = [_make_leg(Mode.TRAIN, 0, 30, 0.0, 10000, sigma=5.0)]
    it = Itinerary(legs=legs)
    mean_arrival = it.end_time
    # 90% confidence ≈ mean + 1.282 * 5 min
    p90 = it.arrival_by(0.90)
    assert (p90 - mean_arrival).total_seconds() / 60 == pytest.approx(6.41, abs=0.01)


# ---------------------------------------------------------------------------
# Feasibility
# ---------------------------------------------------------------------------

def test_feasibility_luggage_blocks_bike():
    it = Itinerary(legs=[_make_leg(Mode.BIKE_SHARE, 0, 20, 3.25, 5000)])
    req = JourneyRequest(
        origin=FOUNTAINHEAD, destination=YYZ,
        departure_time=BASE_TIME, has_luggage=True,
    )
    assert not is_feasible(it, req)


def test_feasibility_own_car_required():
    it = Itinerary(legs=[_make_leg(Mode.CAR_OWN, 0, 25, 8.0, 22000)])
    req_no_car = JourneyRequest(
        origin=FOUNTAINHEAD, destination=YYZ,
        departure_time=BASE_TIME, has_own_car=False,
    )
    assert not is_feasible(it, req_no_car)
    req_with_car = JourneyRequest(
        origin=FOUNTAINHEAD, destination=YYZ,
        departure_time=BASE_TIME, has_own_car=True,
    )
    assert is_feasible(it, req_with_car)


def test_feasibility_arrive_by_uses_p90():
    # Scheduled arrival 25 min, sigma 10 min → p90 arrival = 25 + ~12.8 = ~37.8 min
    it = Itinerary(legs=[_make_leg(Mode.TRAIN, 0, 25, 0.0, 10000, sigma=10.0)])
    # Deadline 35 min out — infeasible at 90% confidence
    req_tight = JourneyRequest(
        origin=FOUNTAINHEAD, destination=YYZ,
        departure_time=BASE_TIME,
        arrive_by=BASE_TIME + timedelta(minutes=35),
    )
    assert not is_feasible(it, req_tight)
    # Deadline 45 min out — feasible
    req_loose = JourneyRequest(
        origin=FOUNTAINHEAD, destination=YYZ,
        departure_time=BASE_TIME,
        arrive_by=BASE_TIME + timedelta(minutes=45),
    )
    assert is_feasible(it, req_loose)


# ---------------------------------------------------------------------------
# Pareto filter
# ---------------------------------------------------------------------------

def test_pareto_dominated_removed():
    """A strictly worse itinerary (longer AND more expensive) is dropped."""
    fast_expensive = Itinerary(legs=[_make_leg(Mode.RIDESHARE, 0, 25, 65.0, 22000)])
    slow_cheap = Itinerary(legs=[_make_leg(Mode.BUS, 0, 75, 3.35, 22000)])
    dominated = Itinerary(legs=[_make_leg(Mode.BUS, 0, 90, 5.00, 22000)])

    req = JourneyRequest(origin=FOUNTAINHEAD, destination=YYZ,
                         departure_time=BASE_TIME)
    front = pareto_front([fast_expensive, slow_cheap, dominated], req)
    assert fast_expensive in front
    assert slow_cheap in front
    assert dominated not in front


def test_scoring_labels_extremes():
    fastest = Itinerary(legs=[_make_leg(Mode.RIDESHARE, 0, 25, 65.0, 22000)])
    cheapest = Itinerary(legs=[_make_leg(Mode.BUS, 0, 75, 3.35, 22000)])
    balanced = Itinerary(legs=[
        _make_leg(Mode.WALK, 0, 5, 0.0, 300),
        _make_leg(Mode.SUBWAY, 5, 30, 3.35, 12000),
        _make_leg(Mode.TRAIN, 35, 15, 12.35, 10000),
    ])

    req = JourneyRequest(origin=FOUNTAINHEAD, destination=YYZ,
                         departure_time=BASE_TIME)
    scored = score_itineraries([fastest, cheapest, balanced], req)
    labels = {s.label for s in scored}
    assert "Fastest" in labels
    assert "Cheapest" in labels
