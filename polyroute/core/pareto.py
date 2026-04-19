"""Pareto filtering and preference-based scoring for itineraries.

Two-stage ranking:
1. Pareto filter: remove itineraries dominated on all axes.
2. Preference scoring: weighted sum over the non-dominated set.

Axes are defined so that LOWER IS BETTER on every axis, which keeps
the dominance check uniform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .types import Itinerary, JourneyRequest, Mode


# ---------------------------------------------------------------------------
# Axis extraction
# ---------------------------------------------------------------------------


def _time_axis(it: Itinerary, req: JourneyRequest) -> float:
    """Minutes. For arrive_by queries, what matters is lateness risk, not
    raw duration — but we keep the duration axis for Pareto simplicity
    and handle arrive_by separately in filtering."""
    return it.total_duration_min


def _cost_axis(it: Itinerary, req: JourneyRequest) -> float:
    return it.total_cost_cad


def _effort_axis(it: Itinerary, req: JourneyRequest) -> float:
    """Composite effort score. Walking is the dominant term; transfers
    add a flat penalty; carrying luggage on a bike is disqualifying
    elsewhere, so effort doesn't need to re-penalize it here."""
    walk_penalty = it.walking_distance_m / 100.0  # 1 point per 100m
    transfer_penalty = it.num_transfers * 5.0  # 5 points per transfer
    return walk_penalty + transfer_penalty


def _reliability_axis(it: Itinerary, req: JourneyRequest) -> float:
    """Minutes of uncertainty. Lower = more reliable."""
    return it.reliability_sigma_min


AXES: dict[str, Callable[[Itinerary, JourneyRequest], float]] = {
    "time": _time_axis,
    "cost": _cost_axis,
    "effort": _effort_axis,
    "reliability": _reliability_axis,
}


# ---------------------------------------------------------------------------
# Hard feasibility
# ---------------------------------------------------------------------------


def is_feasible(it: Itinerary, req: JourneyRequest) -> bool:
    """Hard constraints. An itinerary failing these is discarded before
    scoring, not just penalized."""
    if it.walking_distance_m > req.max_walking_m:
        return False
    if req.has_luggage and any(leg.mode in (Mode.BIKE_OWN, Mode.BIKE_SHARE) for leg in it.legs):
        return False
    if not req.has_own_bike and any(leg.mode == Mode.BIKE_OWN for leg in it.legs):
        return False
    if not req.has_own_car and any(leg.mode == Mode.CAR_OWN for leg in it.legs):
        return False
    # Arrive-by check: 90% confidence arrival must be before deadline
    if req.arrive_by is not None and it.arrival_by(0.90) > req.arrive_by:
        return False
    return True


# ---------------------------------------------------------------------------
# Pareto filter
# ---------------------------------------------------------------------------


def _dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    """a dominates b iff a is <= b on every axis AND < on at least one."""
    better_or_equal = all(ai <= bi for ai, bi in zip(a, b))
    strictly_better = any(ai < bi for ai, bi in zip(a, b))
    return better_or_equal and strictly_better


def pareto_front(itineraries: list[Itinerary], req: JourneyRequest) -> list[Itinerary]:
    """Return the non-dominated subset."""
    feasible = [it for it in itineraries if is_feasible(it, req)]
    vectors = [tuple(axis_fn(it, req) for axis_fn in AXES.values()) for it in feasible]
    front: list[Itinerary] = []
    for i, it in enumerate(feasible):
        dominated = any(_dominates(vectors[j], vectors[i]) for j in range(len(feasible)) if j != i)
        if not dominated:
            front.append(it)
    return front


# ---------------------------------------------------------------------------
# Preference scoring
# ---------------------------------------------------------------------------


@dataclass
class ScoredItinerary:
    itinerary: Itinerary
    score: float  # lower is better
    axis_values: dict[str, float]
    label: str = ""  # e.g. "Fastest", "Cheapest", "Balanced"


def _normalize(values: list[float]) -> list[float]:
    """Min-max normalize to [0, 1]. All-equal lists collapse to 0."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def score_itineraries(itineraries: list[Itinerary], req: JourneyRequest) -> list[ScoredItinerary]:
    """Score the Pareto front using user preference weights."""
    front = pareto_front(itineraries, req)
    if not front:
        return []

    weights = {
        "time": req.time_weight,
        "cost": req.cost_weight,
        "effort": req.effort_weight,
        "reliability": req.reliability_weight,
    }

    # Compute raw axis values, then normalize each axis independently
    raw: dict[str, list[float]] = {name: [fn(it, req) for it in front] for name, fn in AXES.items()}
    normed = {name: _normalize(vals) for name, vals in raw.items()}

    scored: list[ScoredItinerary] = []
    for i, it in enumerate(front):
        axis_values = {name: raw[name][i] for name in AXES}
        score = sum(weights[name] * normed[name][i] for name in AXES)
        scored.append(ScoredItinerary(itinerary=it, score=score, axis_values=axis_values))

    # Label extremes for UX
    _assign_labels(scored)

    return sorted(scored, key=lambda s: s.score)


def _assign_labels(scored: list[ScoredItinerary]) -> None:
    """Tag extremes: Fastest, Cheapest, Most Reliable, Least Effort, Balanced."""
    if not scored:
        return
    extremes = {
        "Fastest": min(scored, key=lambda s: s.axis_values["time"]),
        "Cheapest": min(scored, key=lambda s: s.axis_values["cost"]),
        "Most reliable": min(scored, key=lambda s: s.axis_values["reliability"]),
        "Least effort": min(scored, key=lambda s: s.axis_values["effort"]),
    }
    used = set()
    for label, item in extremes.items():
        if id(item) not in used and not item.label:
            item.label = label
            used.add(id(item))
    for s in scored:
        if not s.label:
            s.label = "Balanced"
