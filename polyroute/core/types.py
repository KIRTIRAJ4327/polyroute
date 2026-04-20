"""Core domain types for polyroute.

Every adapter, agent node, and scoring function speaks in these types.
Keep this module pure — no I/O, no LLM calls, no framework imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class Mode(str, Enum):
    """Transport modes. Values match common GTFS/GBFS conventions."""

    WALK = "walk"
    BIKE_OWN = "bike_own"
    BIKE_SHARE = "bike_share"
    CAR_OWN = "car_own"
    RIDESHARE = "rideshare"
    BUS = "bus"
    SUBWAY = "subway"
    TRAIN = "train"  # GO, UP Express
    TRAM = "tram"  # streetcar
    FLIGHT = "flight"  # future; sets anchor for airport wedge


@dataclass(frozen=True)
class Location:
    """A point in space. Address optional; lat/lon required."""

    lat: float
    lon: float
    name: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Leg:
    """One continuous segment of a journey in a single mode."""

    mode: Mode
    origin: Location
    destination: Location
    start_time: datetime
    end_time: datetime
    distance_m: float
    cost_cad: float = 0.0
    # Mode-specific detail (route name, operator, vehicle id, etc.)
    route_name: Optional[str] = None
    operator: Optional[str] = None
    # Reliability: std-dev of end_time in minutes. Higher = less reliable.
    reliability_sigma_min: float = 0.0
    # Human-readable turn-by-turn or transit instructions
    instructions: list[str] = field(default_factory=list)

    @property
    def duration_min(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 60.0


@dataclass
class Itinerary:
    """An end-to-end journey composed of one or more legs."""

    legs: list[Leg]
    # Provenance tag identifying which adapter / strategy produced this
    # candidate. Stamped by the Planner after fan-out. ``None`` when an
    # adapter is consumed directly (tests, examples).
    source: Optional[str] = None

    @property
    def start_time(self) -> datetime:
        return self.legs[0].start_time

    @property
    def end_time(self) -> datetime:
        return self.legs[-1].end_time

    @property
    def total_duration_min(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 60.0

    @property
    def total_cost_cad(self) -> float:
        return sum(leg.cost_cad for leg in self.legs)

    @property
    def total_distance_m(self) -> float:
        return sum(leg.distance_m for leg in self.legs)

    @property
    def num_transfers(self) -> int:
        """Transfers = mode changes, not counting walk glue."""
        non_walk_legs = [leg for leg in self.legs if leg.mode != Mode.WALK]
        return max(0, len(non_walk_legs) - 1)

    @property
    def walking_distance_m(self) -> float:
        return sum(leg.distance_m for leg in self.legs if leg.mode == Mode.WALK)

    @property
    def modes_used(self) -> list[Mode]:
        """Ordered, deduplicated list of modes."""
        seen: list[Mode] = []
        for leg in self.legs:
            if leg.mode not in seen:
                seen.append(leg.mode)
        return seen

    @property
    def reliability_sigma_min(self) -> float:
        """Combined reliability — sqrt of sum of variances (independent legs)."""
        variance = sum(leg.reliability_sigma_min**2 for leg in self.legs)
        return variance**0.5

    def arrival_by(self, confidence: float = 0.90) -> datetime:
        """Arrival time at a given confidence level.

        Uses normal approximation: arrival + z*sigma.
        Confidence 0.50 = mean, 0.90 ≈ mean + 1.28σ, 0.95 ≈ mean + 1.645σ.
        """
        # Inverse normal CDF approximation for common confidence levels
        z_table = {0.50: 0.0, 0.75: 0.674, 0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
        # Pick closest
        z = z_table[min(z_table.keys(), key=lambda k: abs(k - confidence))]
        return self.end_time + timedelta(minutes=z * self.reliability_sigma_min)


@dataclass
class JourneyRequest:
    """A routing request. `arrive_by` makes this an airport-style query."""

    origin: Location
    destination: Location
    departure_time: Optional[datetime] = None
    arrive_by: Optional[datetime] = None  # e.g., flight boarding time
    # Hard constraints
    has_luggage: bool = False
    has_own_bike: bool = False
    has_own_car: bool = False
    max_walking_m: float = 2000.0
    # Soft preferences — weights used by scoring
    time_weight: float = 1.0
    cost_weight: float = 1.0
    effort_weight: float = 0.5
    reliability_weight: float = 1.0
