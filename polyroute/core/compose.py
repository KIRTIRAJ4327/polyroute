r"""Composition strategy — mixed-mode candidates at transit anchors.

This module is the "interesting" layer. Vanilla transit routers answer
"all transit, A to B." Vanilla rideshare quotes "all Uber, A to B." The
interesting Toronto answer is usually *neither* of those — it's a short
rideshare to a good transit anchor plus a fast transit leg to the
destination.

Design constraints (see CLAUDE.md §6 invariants):

- Core-only. No concrete adapter imports. Transit and rideshare sources
  come in as ``Protocol``\ s so this module is unit-testable with fakes
  and does not create a dependency cycle with the adapters.
- Pure in the Pareto sense: this module *generates* candidates. It does
  not score, dedupe-by-preference, or filter for feasibility —
  ``core/pareto.py`` owns that.
- Time-consistent: composed itineraries have the rideshare leg end time
  equal to the transit leg start time. The transit source is re-queried
  with a departure anchored at the rideshare arrival.

Currently only the first-mile pattern (rideshare → anchor → transit) is
implemented. Last-mile (transit → anchor → rideshare) can be layered
on later when user interviews confirm the demand; the airport-access
wedge is first-mile-dominant (catch the UP Express out, fly in and Uber
home).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Protocol

from .types import Itinerary, JourneyRequest, Location


# ---------------------------------------------------------------------------
# Source protocols
# ---------------------------------------------------------------------------


class TransitSource(Protocol):
    """Anything that can answer a transit-style routing query."""

    def plan(self, req: JourneyRequest, num_itineraries: int = 5) -> list[Itinerary]: ...


class RideshareEstimator(Protocol):
    """Anything that can price a single rideshare leg."""

    def estimate(self, req: JourneyRequest) -> Itinerary: ...


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Anchor:
    """A transit anchor point worth considering for first/last-mile mixing."""

    id: str
    name: str
    operator: str
    location: Location
    modes: tuple[str, ...]
    notes: str = ""


def load_gta_anchors() -> list[Anchor]:
    """Load the bundled GTA anchor set."""
    data = json.loads(resources.files("polyroute.core").joinpath("anchors_gta.json").read_text())
    anchors: list[Anchor] = []
    for raw in data.get("anchors", []):
        anchors.append(
            Anchor(
                id=raw["id"],
                name=raw["name"],
                operator=raw["operator"],
                location=Location(
                    lat=float(raw["lat"]),
                    lon=float(raw["lon"]),
                    name=raw["name"],
                ),
                modes=tuple(raw.get("modes", [])),
                notes=raw.get("notes", ""),
            )
        )
    return anchors


# ---------------------------------------------------------------------------
# First-mile composition
# ---------------------------------------------------------------------------


@dataclass
class ComposeOptions:
    """Knobs for candidate generation.

    ``per_anchor_transit_count`` bounds how many transit itineraries we
    request from each anchor (OTP2 queries are cheap but add latency).
    ``max_anchors`` caps how many anchors we try in a single call; past
    6–8 the Pareto frontier stops moving but latency keeps climbing.
    """

    per_anchor_transit_count: int = 2
    max_anchors: int = 6


def compose_first_mile(
    req: JourneyRequest,
    transit: TransitSource,
    rideshare: RideshareEstimator,
    anchors: list[Anchor],
    options: ComposeOptions | None = None,
) -> list[Itinerary]:
    """Generate rideshare-first-mile + transit candidates.

    For each anchor, we price ``origin → anchor`` as a rideshare leg,
    then ask the transit source for itineraries ``anchor → destination``
    with departure anchored at the rideshare arrival time. Each transit
    itinerary is stitched onto the end of the rideshare leg, producing
    one composed ``Itinerary`` per (anchor, transit-option) pair.

    Returns itineraries in the order they were generated. Callers should
    combine this list with the raw direct-transit and direct-rideshare
    itineraries before handing the combined list to the Pareto filter.
    """
    opts = options or ComposeOptions()
    candidates: list[Itinerary] = []

    for anchor in anchors[: opts.max_anchors]:
        first_mile = _estimate_first_mile(req, anchor, rideshare)
        if first_mile is None:
            continue

        transit_req = JourneyRequest(
            origin=anchor.location,
            destination=req.destination,
            departure_time=first_mile.end_time,
            arrive_by=req.arrive_by,
            has_luggage=req.has_luggage,
            has_own_bike=req.has_own_bike,
            has_own_car=req.has_own_car,
            max_walking_m=req.max_walking_m,
            time_weight=req.time_weight,
            cost_weight=req.cost_weight,
            effort_weight=req.effort_weight,
            reliability_weight=req.reliability_weight,
        )

        transit_itins = transit.plan(transit_req, num_itineraries=opts.per_anchor_transit_count)
        for transit_itin in transit_itins:
            if not transit_itin.legs:
                continue
            composed = Itinerary(legs=[*first_mile.legs, *transit_itin.legs])
            candidates.append(composed)

    return candidates


def _estimate_first_mile(
    req: JourneyRequest,
    anchor: Anchor,
    rideshare: RideshareEstimator,
) -> Itinerary | None:
    """Price ``origin → anchor`` as a rideshare leg."""
    first_mile_req = JourneyRequest(
        origin=req.origin,
        destination=anchor.location,
        departure_time=req.departure_time,
        # arrive_by does not flow to the first mile — we care about when
        # we get to the anchor, not the eventual destination
    )
    itin = rideshare.estimate(first_mile_req)
    if not itin.legs:
        return None
    return itin
