"""GBFS adapter — dockful bike share (Bike Share Toronto).

Reads a GBFS v2 feed to build a walk → bike → walk itinerary: walk
from the request origin to the nearest station that has bikes, ride
to the station nearest the destination that has open docks, walk the
rest of the way.

Data source: Bike Share Toronto publishes a GBFS v2-compliant feed.
Discovery URL: https://tor.publicbikesystem.net/customer/gbfs/v2/gbfs.json
The feed lists per-language / per-dataset URLs under ``data.en.feeds``;
this adapter reads ``station_information`` and ``station_status`` and
merges them by ``station_id``.

GBFS spec: https://github.com/MobilityData/gbfs (v2.3 was the stable
draft as of 2026-04). Validated: 2026-04.

Core invariant respected: this adapter does **not** know about OTP2,
rideshare, scoring, or composition. It returns ``Itinerary`` objects
and nothing else (see ``docs/adapters.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Optional

import httpx

from ..core.types import Itinerary, JourneyRequest, Leg, Location, Mode


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


DEFAULT_DISCOVERY_URL = "https://tor.publicbikesystem.net/customer/gbfs/v2/gbfs.json"
DEFAULT_LANG = "en"

# Walk and bike pace priors. Bike Share Toronto bikes are heavy and
# riders tend to go slower than a personal commuter cyclist; 15 km/h is
# a conservative public-bike pace, 5 km/h is the usual walk speed prior.
WALK_KMH = 5.0
BIKE_KMH = 15.0

# Bike Share Toronto pricing snapshot (Apr 2026). Single trip = $1 unlock
# + $0.12 per minute up to a cap. Verify before user-facing deployment,
# same way we treat the rideshare rate card.
UNLOCK_FEE_CAD = 1.00
PER_MINUTE_CAD = 0.12
DAY_PASS_CAP_CAD = 15.00

# Reliability prior: bike share legs carry station-availability risk
# even above the measured sigma of a bike ride. 1.5 min is the compose
# guide's published value.
BIKE_SIGMA_MIN = 1.5
WALK_SIGMA_MIN = 0.5

# Only consider stations within this radius of the origin / destination
# when picking an anchor. Past ~1500 m the walk alone overwhelms the
# bike savings.
DEFAULT_MAX_ACCESS_M = 1500.0


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Station:
    """A GBFS station with merged information + live availability."""

    station_id: str
    name: str
    lat: float
    lon: float
    capacity: int
    bikes_available: int
    docks_available: int
    is_renting: bool
    is_returning: bool

    @property
    def location(self) -> Location:
        return Location(lat=self.lat, lon=self.lon, name=self.name)


@dataclass
class GBFSAdapter:
    """Read-only adapter over a GBFS v2 discovery URL.

    The adapter is stateless between calls. Each ``plan()`` invocation
    re-fetches ``station_status`` so availability is fresh. Pass an
    ``httpx.Client`` via ``client`` if you want connection reuse or
    custom timeouts.
    """

    discovery_url: str = DEFAULT_DISCOVERY_URL
    lang: str = DEFAULT_LANG
    timeout_s: float = 10.0
    max_access_m: float = DEFAULT_MAX_ACCESS_M
    client: Optional[httpx.Client] = field(default=None, repr=False)
    operator: str = "Bike Share Toronto"

    def _fetch(self, url: str) -> dict[str, Any]:
        if self.client is not None:
            resp = self.client.get(url, timeout=self.timeout_s)
        else:
            resp = httpx.get(url, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _resolve_feeds(self) -> dict[str, str]:
        """Return ``{feed_name: url}`` for the configured language."""
        discovery = self._fetch(self.discovery_url)
        data = discovery.get("data", {})
        # GBFS v2: data is keyed by language; v3 is flat.
        lang_block = data.get(self.lang) or next(iter(data.values()), {})
        feeds = lang_block.get("feeds", [])
        return {f["name"]: f["url"] for f in feeds if "name" in f and "url" in f}

    def stations(self) -> list[Station]:
        """Return the merged station list with live availability."""
        feeds = self._resolve_feeds()
        info_raw = self._fetch(feeds["station_information"])
        status_raw = self._fetch(feeds["station_status"])
        return _merge_stations(info_raw, status_raw)

    def plan(self, req: JourneyRequest, num_itineraries: int = 1) -> list[Itinerary]:
        """Return at most ``num_itineraries`` walk→bike→walk candidates.

        If the request forbids bike share (luggage) or no pair of
        stations is within ``max_access_m`` of origin/destination,
        returns ``[]``.
        """
        if req.has_luggage:
            return []

        stations = self.stations()
        start_station = _nearest(stations, req.origin, max_m=self.max_access_m, need_bikes=True)
        end_station = _nearest(stations, req.destination, max_m=self.max_access_m, need_docks=True)
        if start_station is None or end_station is None:
            return []
        if start_station.station_id == end_station.station_id:
            return []

        depart = req.departure_time or datetime.now()
        itin = _build_itinerary(
            req,
            start_station=start_station,
            end_station=end_station,
            depart=depart,
            operator=self.operator,
        )
        return [itin][:num_itineraries]


# ---------------------------------------------------------------------------
# Pure helpers (fixture-testable)
# ---------------------------------------------------------------------------


def _haversine_m(a: Location, b: Location) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6_371_000.0 * asin(sqrt(h))


def _merge_stations(info_raw: dict[str, Any], status_raw: dict[str, Any]) -> list[Station]:
    """Merge station_information + station_status responses by station_id."""
    info_rows = (info_raw.get("data") or {}).get("stations") or []
    status_rows = (status_raw.get("data") or {}).get("stations") or []
    status_by_id = {row["station_id"]: row for row in status_rows if "station_id" in row}

    merged: list[Station] = []
    for row in info_rows:
        sid = row.get("station_id")
        if sid is None:
            continue
        status = status_by_id.get(sid, {})
        # GBFS uses 0/1 ints for is_installed/is_renting/is_returning
        is_installed = bool(status.get("is_installed", 1))
        if not is_installed:
            continue
        merged.append(
            Station(
                station_id=sid,
                name=row.get("name") or sid,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                capacity=int(row.get("capacity", 0)),
                bikes_available=int(status.get("num_bikes_available", 0)),
                docks_available=int(status.get("num_docks_available", 0)),
                is_renting=bool(status.get("is_renting", 1)),
                is_returning=bool(status.get("is_returning", 1)),
            )
        )
    return merged


def _nearest(
    stations: list[Station],
    point: Location,
    max_m: float,
    need_bikes: bool = False,
    need_docks: bool = False,
) -> Optional[Station]:
    """Pick the closest station within ``max_m`` that satisfies availability."""
    best: Optional[Station] = None
    best_d = float("inf")
    for s in stations:
        if need_bikes and (not s.is_renting or s.bikes_available <= 0):
            continue
        if need_docks and (not s.is_returning or s.docks_available <= 0):
            continue
        d = _haversine_m(s.location, point)
        if d > max_m:
            continue
        if d < best_d:
            best = s
            best_d = d
    return best


def _walk_duration_min(distance_m: float) -> float:
    return (distance_m / 1000.0) / WALK_KMH * 60.0


def _bike_duration_min(distance_m: float) -> float:
    return (distance_m / 1000.0) / BIKE_KMH * 60.0


def _bike_fare(duration_min: float) -> float:
    return min(UNLOCK_FEE_CAD + duration_min * PER_MINUTE_CAD, DAY_PASS_CAP_CAD)


def _build_itinerary(
    req: JourneyRequest,
    start_station: Station,
    end_station: Station,
    depart: datetime,
    operator: str,
) -> Itinerary:
    access_m = _haversine_m(req.origin, start_station.location)
    bike_m = _haversine_m(start_station.location, end_station.location)
    egress_m = _haversine_m(end_station.location, req.destination)

    access_min = _walk_duration_min(access_m)
    bike_min = _bike_duration_min(bike_m)
    egress_min = _walk_duration_min(egress_m)

    t0 = depart
    t1 = t0 + timedelta(minutes=access_min)
    t2 = t1 + timedelta(minutes=bike_min)
    t3 = t2 + timedelta(minutes=egress_min)

    access_leg = Leg(
        mode=Mode.WALK,
        origin=req.origin,
        destination=start_station.location,
        start_time=t0,
        end_time=t1,
        distance_m=access_m,
        cost_cad=0.0,
        route_name=f"Walk to {start_station.name}",
        reliability_sigma_min=WALK_SIGMA_MIN,
    )
    bike_leg = Leg(
        mode=Mode.BIKE_SHARE,
        origin=start_station.location,
        destination=end_station.location,
        start_time=t1,
        end_time=t2,
        distance_m=bike_m,
        cost_cad=_bike_fare(bike_min),
        route_name=f"{start_station.name} → {end_station.name}",
        operator=operator,
        reliability_sigma_min=BIKE_SIGMA_MIN,
    )
    egress_leg = Leg(
        mode=Mode.WALK,
        origin=end_station.location,
        destination=req.destination,
        start_time=t2,
        end_time=t3,
        distance_m=egress_m,
        cost_cad=0.0,
        route_name=f"Walk from {end_station.name}",
        reliability_sigma_min=WALK_SIGMA_MIN,
    )
    return Itinerary(legs=[access_leg, bike_leg, egress_leg])
