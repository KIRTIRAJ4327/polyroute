"""OpenTripPlanner 2 adapter — transit / walk / bike itineraries.

Talks to a local OTP2 instance over its Index GraphQL API. Returns
polyroute `Itinerary` objects for the transit / walk / bike portion of a
journey. Does **not** know about rideshare, composition, scoring, or
explanation — those are other layers (see CLAUDE.md §6).

Tested against OTP 2.5+. Schema has been stable since 2.3; earlier
versions used a different root field name (`plan` vs `trip`).

WIP: the response mapper is covered by fixture-based unit tests. Live
integration tests live in ``tests/integration/test_otp2_live.py`` and
require a running OTP2 container (see ``docker/otp2-toronto/``).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from ..core.types import Itinerary, JourneyRequest, Leg, Location, Mode


DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_GRAPHQL_PATH = "/otp/routers/default/index/graphql"


# OTP2 mode string → polyroute Mode. OTP2 uses GTFS route_type semantics
# plus a few synthetic modes (WALK, BICYCLE, CAR). See
# https://docs.opentripplanner.org/en/latest/RouteTypes/ for the full map.
_OTP_MODE_MAP: dict[str, Mode] = {
    "WALK": Mode.WALK,
    "BICYCLE": Mode.BIKE_OWN,  # OTP2 doesn't distinguish own vs share here
    "CAR": Mode.CAR_OWN,
    "BUS": Mode.BUS,
    "COACH": Mode.BUS,
    "SUBWAY": Mode.SUBWAY,
    "METRO": Mode.SUBWAY,
    "RAIL": Mode.TRAIN,
    "TRAM": Mode.TRAM,
    "FUNICULAR": Mode.TRAM,
    "FERRY": Mode.TRAM,  # no dedicated Mode; TRAM is the closest low-frequency fit
}


# Mode-level reliability priors (minutes of sigma) used when OTP2 does not
# provide realtime variance. Starting values; revisit once GTFS-Realtime
# monitoring is wired up in v0.2.
_MODE_SIGMA_PRIOR: dict[Mode, float] = {
    Mode.WALK: 0.5,
    Mode.BIKE_OWN: 1.0,
    Mode.BIKE_SHARE: 1.5,
    Mode.CAR_OWN: 5.0,
    Mode.RIDESHARE: 5.0,
    Mode.BUS: 4.0,
    Mode.SUBWAY: 2.0,
    Mode.TRAIN: 2.5,
    Mode.TRAM: 4.0,
    Mode.FLIGHT: 15.0,
}


PLAN_QUERY = """
query Plan(
  $from: String!
  $to: String!
  $date: String!
  $time: String!
  $numItineraries: Int!
  $maxWalkDistance: Float!
  $arriveBy: Boolean!
) {
  plan(
    fromPlace: $from
    toPlace: $to
    date: $date
    time: $time
    numItineraries: $numItineraries
    maxWalkDistance: $maxWalkDistance
    arriveBy: $arriveBy
  ) {
    itineraries {
      startTime
      endTime
      duration
      walkDistance
      legs {
        mode
        startTime
        endTime
        duration
        distance
        from { lat lon name }
        to { lat lon name }
        route { shortName longName }
        agency { name }
        transitLeg
      }
    }
  }
}
""".strip()


@dataclass
class OTP2Adapter:
    """Adapter for a local OpenTripPlanner 2 instance.

    Example:
        adapter = OTP2Adapter()
        itineraries = adapter.plan(request, num_itineraries=5)
    """

    base_url: str = DEFAULT_BASE_URL
    graphql_path: str = DEFAULT_GRAPHQL_PATH
    timeout_s: float = 10.0

    @property
    def url(self) -> str:
        return self.base_url.rstrip("/") + self.graphql_path

    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]:
        """Query OTP2 and return polyroute itineraries.

        Raises ``httpx.HTTPError`` on transport failure and ``OTP2Error``
        on GraphQL-level errors (which come back with HTTP 200).
        """
        variables = _request_to_variables(req, num_itineraries)
        payload = {"query": PLAN_QUERY, "variables": variables}

        response = httpx.post(self.url, json=payload, timeout=self.timeout_s)
        response.raise_for_status()
        body = response.json()

        if body.get("errors"):
            raise OTP2Error(body["errors"])

        data = body.get("data") or {}
        plan = data.get("plan") or {}
        raw_itineraries = plan.get("itineraries") or []
        return [_itinerary_from_otp2(i) for i in raw_itineraries]


class OTP2Error(RuntimeError):
    """OTP2 returned a GraphQL error (transport was fine)."""


def _request_to_variables(req: JourneyRequest, num_itineraries: int) -> dict[str, Any]:
    """Map a polyroute ``JourneyRequest`` to OTP2 plan variables."""
    arrive_by = req.arrive_by is not None
    anchor = req.arrive_by or req.departure_time or datetime.now()
    return {
        "from": f"{req.origin.lat},{req.origin.lon}",
        "to": f"{req.destination.lat},{req.destination.lon}",
        "date": anchor.strftime("%Y-%m-%d"),
        "time": anchor.strftime("%H:%M:%S"),
        "numItineraries": num_itineraries,
        "maxWalkDistance": float(req.max_walking_m),
        "arriveBy": arrive_by,
    }


def _itinerary_from_otp2(raw: dict[str, Any]) -> Itinerary:
    legs = [_leg_from_otp2(leg) for leg in raw.get("legs", [])]
    return Itinerary(legs=legs)


def _leg_from_otp2(raw: dict[str, Any]) -> Leg:
    mode = _map_mode(raw.get("mode", "WALK"))
    origin = _location_from_otp2(raw.get("from") or {})
    destination = _location_from_otp2(raw.get("to") or {})
    route = raw.get("route") or {}
    agency = raw.get("agency") or {}
    route_name = route.get("shortName") or route.get("longName") or None
    return Leg(
        mode=mode,
        origin=origin,
        destination=destination,
        start_time=_epoch_ms_to_dt(raw["startTime"]),
        end_time=_epoch_ms_to_dt(raw["endTime"]),
        distance_m=float(raw.get("distance", 0.0)),
        cost_cad=0.0,  # OTP2 does not compute fare in the default schema
        route_name=route_name,
        operator=agency.get("name"),
        reliability_sigma_min=_MODE_SIGMA_PRIOR.get(mode, 0.0),
    )


def _location_from_otp2(raw: dict[str, Any]) -> Location:
    return Location(
        lat=float(raw.get("lat", 0.0)),
        lon=float(raw.get("lon", 0.0)),
        name=raw.get("name"),
    )


def _map_mode(otp_mode: str) -> Mode:
    return _OTP_MODE_MAP.get(otp_mode.upper(), Mode.WALK)


def _epoch_ms_to_dt(value: int | float) -> datetime:
    """OTP2 returns epoch milliseconds. Convert to naive local datetime."""
    return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).replace(tzinfo=None)
