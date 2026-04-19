"""Unit tests for the OTP2 response mapper.

These tests do not require a live OTP2 instance — they exercise the pure
translation from a captured GraphQL response to polyroute domain types.
Live integration tests live in ``tests/integration/test_otp2_live.py``.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from polyroute.adapters.otp2 import (
    OTP2Adapter,
    _itinerary_from_otp2,
    _request_to_variables,
)
from polyroute.core.types import JourneyRequest, Location, Mode


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "otp2_plan_response.json"


@pytest.fixture
def fixture_response() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_itinerary_from_otp2_maps_modes(fixture_response):
    raw = fixture_response["data"]["plan"]["itineraries"][0]
    itinerary = _itinerary_from_otp2(raw)

    assert [leg.mode for leg in itinerary.legs] == [
        Mode.WALK,
        Mode.BUS,
        Mode.SUBWAY,
        Mode.TRAIN,
    ]


def test_itinerary_from_otp2_preserves_route_and_operator(fixture_response):
    raw = fixture_response["data"]["plan"]["itineraries"][0]
    itinerary = _itinerary_from_otp2(raw)

    bus, subway, train = itinerary.legs[1], itinerary.legs[2], itinerary.legs[3]
    assert bus.route_name == "26" and bus.operator == "MiWay"
    assert subway.route_name == "2" and subway.operator == "TTC"
    assert train.route_name == "UP" and train.operator == "Metrolinx"


def test_itinerary_from_otp2_assigns_mode_priors(fixture_response):
    raw = fixture_response["data"]["plan"]["itineraries"][0]
    itinerary = _itinerary_from_otp2(raw)

    walk, bus, subway, train = itinerary.legs
    assert walk.reliability_sigma_min == pytest.approx(0.5)
    assert bus.reliability_sigma_min == pytest.approx(4.0)
    assert subway.reliability_sigma_min == pytest.approx(2.0)
    assert train.reliability_sigma_min == pytest.approx(2.5)


def test_itinerary_totals_match_fixture(fixture_response):
    raw = fixture_response["data"]["plan"]["itineraries"][0]
    itinerary = _itinerary_from_otp2(raw)

    # 1776398400 → 1776402600 epoch s = 70 minutes
    assert itinerary.total_duration_min == pytest.approx(70.0)
    assert itinerary.total_distance_m == pytest.approx(42200.0)
    assert itinerary.num_transfers == 2  # bus + subway + train, minus one
    assert itinerary.walking_distance_m == pytest.approx(200.0)


def test_request_to_variables_depart_at():
    req = JourneyRequest(
        origin=Location(43.6011, -79.5463),
        destination=Location(43.6777, -79.6248),
        departure_time=datetime(2026, 4, 18, 6, 0, 0),
        max_walking_m=1500.0,
    )
    variables = _request_to_variables(req, num_itineraries=5)

    assert variables["from"] == "43.6011,-79.5463"
    assert variables["to"] == "43.6777,-79.6248"
    assert variables["date"] == "2026-04-18"
    assert variables["time"] == "06:00:00"
    assert variables["numItineraries"] == 5
    assert variables["maxWalkDistance"] == 1500.0
    assert variables["arriveBy"] is False


def test_request_to_variables_arrive_by_overrides_departure():
    req = JourneyRequest(
        origin=Location(43.6011, -79.5463),
        destination=Location(43.6777, -79.6248),
        departure_time=datetime(2026, 4, 18, 4, 0, 0),
        arrive_by=datetime(2026, 4, 18, 6, 0, 0),
    )
    variables = _request_to_variables(req, num_itineraries=3)

    assert variables["arriveBy"] is True
    assert variables["time"] == "06:00:00"


def test_adapter_url_property():
    adapter = OTP2Adapter(base_url="http://otp.example.com/")
    assert adapter.url == "http://otp.example.com/otp/routers/default/index/graphql"
