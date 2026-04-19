"""Rideshare (Uber/Lyft) heuristic estimator — clearly-labeled estimate.

Uber's Price Estimates API ToU §II B prohibits third-party price
comparison, and Lyft's public Developer Platform was retired in 2021.
Live third-party pricing is therefore off-limits (see CLAUDE.md §3.2).
This module produces an *honest estimate* from a published rate card
plus a deterministic surge multiplier. The user-facing label always
says "Estimate only — not a live price."

The rate card below is a **starting snapshot** of Uber-Canada UberX-style
fares and must be verified against Uber Canada's current public rates
before any production / user-facing deployment. Revalidate quarterly
(see ``docs/architecture.md`` risks).

Rates are in CAD. Times are minutes; distances are meters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from ..core.types import Itinerary, JourneyRequest, Leg, Location, Mode


# ---------------------------------------------------------------------------
# Rate card (verify before production — see module docstring)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RateCard:
    """Uber-style fare components. All CAD."""

    base_fare: float
    booking_fee: float
    per_km: float
    per_minute: float
    minimum_fare: float
    service_area: str = "Toronto/GTA"
    snapshot_date: str = "2026-04"


# Starting estimate. Verify against https://www.uber.com/en-CA/price-estimate/
# before any user-facing deployment. Numbers reflect commonly-published
# UberX ranges for Toronto/GTA.
UBERX_TORONTO_ESTIMATE = RateCard(
    base_fare=3.40,
    booking_fee=2.75,
    per_km=1.15,
    per_minute=0.38,
    minimum_fare=7.00,
)


# Surge multiplier by (weekday, hour-of-day). Conservative — real surge
# can spike higher. Covers the common cases: weekday peaks, late-night
# weekends, overnight dead zone where rides are scarce.
#
# weekday: Monday=0 .. Sunday=6
# hour: 0..23 in local time
_SURGE_RULES: list[tuple[str, set[int], set[int], float]] = [
    # name, weekdays, hours, multiplier
    ("weekday morning peak", {0, 1, 2, 3, 4}, {7, 8, 9}, 1.5),
    ("weekday evening peak", {0, 1, 2, 3, 4}, {16, 17, 18, 19}, 1.6),
    ("late-night weekend", {4, 5}, {23}, 1.8),
    ("overnight weekend", {5, 6}, {0, 1, 2, 3}, 1.9),
    ("early morning", {0, 1, 2, 3, 4, 5, 6}, {5, 6}, 1.3),
]


def surge_multiplier(when: datetime) -> tuple[float, str]:
    """Return (multiplier, label). Label is 'off-peak' when no rule fires."""
    weekday = when.weekday()
    hour = when.hour
    for label, days, hours, mult in _SURGE_RULES:
        if weekday in days and hour in hours:
            return mult, label
    return 1.0, "off-peak"


# ---------------------------------------------------------------------------
# Distance and time priors
# ---------------------------------------------------------------------------


# Urban driving path factor over straight-line (haversine) distance.
# Toronto-specific 1.3–1.5 is typical; 1.4 is the common-use number.
_PATH_FACTOR = 1.4

# Urban driving speed, km/h. Peak vs off-peak.
_SPEED_KMH_OFFPEAK = 30.0
_SPEED_KMH_PEAK = 20.0


def _haversine_m(a: Location, b: Location) -> float:
    """Great-circle distance in meters."""
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    r_earth_m = 6_371_000.0
    return 2 * r_earth_m * asin(sqrt(h))


def _drive_distance_m(origin: Location, destination: Location) -> float:
    return _haversine_m(origin, destination) * _PATH_FACTOR


def _drive_duration_min(distance_m: float, is_peak: bool) -> float:
    speed_kmh = _SPEED_KMH_PEAK if is_peak else _SPEED_KMH_OFFPEAK
    return (distance_m / 1000.0) / speed_kmh * 60.0


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------


@dataclass
class RideshareHeuristic:
    """Deterministic rideshare price estimator.

    The output is an ``Itinerary`` with a single ``RIDESHARE`` leg. The
    ``route_name`` is always the honesty label; the ``operator`` carries
    the snapshot date so downstream UI can show "as of 2026-04".
    """

    rate_card: RateCard = field(default_factory=lambda: UBERX_TORONTO_ESTIMATE)

    def estimate(self, req: JourneyRequest) -> Itinerary:
        depart = req.departure_time or datetime.now()
        multiplier, surge_label = surge_multiplier(depart)
        is_peak = multiplier > 1.0

        distance_m = _drive_distance_m(req.origin, req.destination)
        duration_min = _drive_duration_min(distance_m, is_peak)
        fare = _compute_fare(self.rate_card, distance_m, duration_min, multiplier)

        from datetime import timedelta

        leg = Leg(
            mode=Mode.RIDESHARE,
            origin=req.origin,
            destination=req.destination,
            start_time=depart,
            end_time=depart + timedelta(minutes=duration_min),
            distance_m=distance_m,
            cost_cad=fare,
            route_name="Estimate only — not a live price",
            operator=f"UberX-style, {self.rate_card.snapshot_date} snapshot ({surge_label})",
            # Surge and traffic combine to widen variance at peak
            reliability_sigma_min=5.0 if not is_peak else 7.0,
        )
        return Itinerary(legs=[leg])


def _compute_fare(
    card: RateCard,
    distance_m: float,
    duration_min: float,
    multiplier: float,
) -> float:
    distance_component = (distance_m / 1000.0) * card.per_km
    time_component = duration_min * card.per_minute
    subtotal = card.base_fare + distance_component + time_component
    subtotal *= multiplier
    total = subtotal + card.booking_fee
    return max(total, card.minimum_fare)
