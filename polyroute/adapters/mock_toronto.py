"""Mock itinerary generator for the Fountainhead Rd → YYZ corridor.

This exists so the full pipeline (candidate generation → Pareto → LLM
explanation) is demonstrable before OTP2 is running. Numbers are
hand-tuned to reflect real Toronto costs and times as of April 2026.

Replace with real adapters (OTP2, rideshare heuristic, GBFS) once they're
wired up.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..core.types import Itinerary, JourneyRequest, Leg, Location, Mode


# Known anchors on the Mississauga → YYZ corridor
FOUNTAINHEAD = Location(43.6011, -79.5463, name="Fountainhead Rd, Mississauga")
KIPLING_STN = Location(43.6366, -79.5358, name="Kipling Station (TTC/MiWay)")
UNION_STN = Location(43.6453, -79.3806, name="Union Station")
YYZ = Location(43.6777, -79.6248, name="Toronto Pearson Terminal 1")


def _leg(mode: Mode, origin: Location, dest: Location,
         start: datetime, duration_min: int, cost: float,
         distance_m: float, sigma: float = 0.0,
         route: str | None = None, operator: str | None = None) -> Leg:
    return Leg(
        mode=mode,
        origin=origin,
        destination=dest,
        start_time=start,
        end_time=start + timedelta(minutes=duration_min),
        distance_m=distance_m,
        cost_cad=cost,
        reliability_sigma_min=sigma,
        route_name=route,
        operator=operator,
    )


def generate_candidates(req: JourneyRequest) -> list[Itinerary]:
    """Return realistic candidate itineraries for the Fountainhead → YYZ query."""
    t = req.departure_time or datetime.now()

    candidates: list[Itinerary] = []

    # 1. Pure rideshare — fast, expensive, reliable (minus surge)
    candidates.append(Itinerary(legs=[
        _leg(Mode.RIDESHARE, FOUNTAINHEAD, YYZ, t, 28, 52.0, 22000,
             sigma=6.0, operator="Uber (est.)"),
    ]))

    # 2. Drive own car + park (long-term lot + shuttle)
    candidates.append(Itinerary(legs=[
        _leg(Mode.CAR_OWN, FOUNTAINHEAD, YYZ, t, 25, 18.0, 22000,
             sigma=5.0, route="403 W → 427 N", operator="Self + Park'N Fly"),
    ]))

    # 3. MiWay bus to Kipling + TTC + UP Express (transit purist)
    leg1_start = t
    leg1_end = leg1_start + timedelta(minutes=22)
    leg2_start = leg1_end + timedelta(minutes=4)  # transfer wait
    leg2_end = leg2_start + timedelta(minutes=32)
    leg3_start = leg2_end + timedelta(minutes=5)
    candidates.append(Itinerary(legs=[
        _leg(Mode.BUS, FOUNTAINHEAD, KIPLING_STN, leg1_start, 22, 4.40, 6000,
             sigma=4.0, route="MiWay 26", operator="MiWay"),
        _leg(Mode.WALK, KIPLING_STN, KIPLING_STN, leg1_end, 4, 0.0, 200),
        _leg(Mode.SUBWAY, KIPLING_STN, UNION_STN, leg2_start, 32, 0.0, 14000,
             sigma=3.0, route="Line 2 → Line 1", operator="TTC"),
        _leg(Mode.WALK, UNION_STN, UNION_STN, leg2_end, 5, 0.0, 300),
        _leg(Mode.TRAIN, UNION_STN, YYZ, leg3_start, 25, 12.35, 22000,
             sigma=2.0, route="UP Express", operator="Metrolinx"),
    ]))

    # 4. Uber to Kipling + TTC + UP Express (mixed mode — the pitch)
    r1_start = t
    r1_end = r1_start + timedelta(minutes=12)
    r2_start = r1_end + timedelta(minutes=3)
    r2_end = r2_start + timedelta(minutes=32)
    r3_start = r2_end + timedelta(minutes=5)
    candidates.append(Itinerary(legs=[
        _leg(Mode.RIDESHARE, FOUNTAINHEAD, KIPLING_STN, r1_start, 12, 16.0, 6000,
             sigma=3.0, operator="Uber (est.)"),
        _leg(Mode.WALK, KIPLING_STN, KIPLING_STN, r1_end, 3, 0.0, 150),
        _leg(Mode.SUBWAY, KIPLING_STN, UNION_STN, r2_start, 32, 3.35, 14000,
             sigma=3.0, route="Line 2 → Line 1", operator="TTC"),
        _leg(Mode.WALK, UNION_STN, UNION_STN, r2_end, 5, 0.0, 300),
        _leg(Mode.TRAIN, UNION_STN, YYZ, r3_start, 25, 12.35, 22000,
             sigma=2.0, route="UP Express", operator="Metrolinx"),
    ]))

    # 5. Uber to nearest GO station + GO bus direct to YYZ
    g1_start = t
    g1_end = g1_start + timedelta(minutes=8)
    g2_start = g1_end + timedelta(minutes=10)  # GO bus headway wait
    candidates.append(Itinerary(legs=[
        _leg(Mode.RIDESHARE, FOUNTAINHEAD, KIPLING_STN, g1_start, 8, 12.0, 4000,
             sigma=2.5, operator="Uber (est.)"),
        _leg(Mode.WALK, KIPLING_STN, KIPLING_STN, g1_end, 10, 0.0, 150),
        _leg(Mode.BUS, KIPLING_STN, YYZ, g2_start, 30, 6.35, 20000,
             sigma=5.0, route="GO 34", operator="GO Transit"),
    ]))

    return candidates
