"""Orchestrator — fan out across adapters, fold in composed candidates.

The four-layer invariant (CLAUDE.md §6) says the *adapters* don't know
about each other and the *core* is pure. This module is the seam: it
knows about *all* adapters but only by their ``Protocol`` shape. It
doesn't score, doesn't explain, doesn't do I/O of its own — it just
gathers candidates and hands them off.

Design goals:

- **Graceful degradation.** If OTP2 or GBFS is unreachable, the call
  must still return useful candidates from the adapters that *are*
  live. Concretely: adapter failures are caught and logged, never
  raised past ``plan()``.
- **Zero required config.** An empty ``Planner()`` is a valid object
  that returns ``[]`` — callers supply adapters explicitly, or use
  ``default_planner()`` which reads env vars.
- **Pure composition.** Composed first-mile candidates are only
  generated when both a transit source and a rideshare source are
  present; the composition stitching itself lives in
  ``core/compose.py``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from .compose import (
    Anchor,
    BikeShareSource,
    ComposeOptions,
    RideshareEstimator,
    TransitSource,
    compose_bike_share_first_mile,
    compose_first_mile,
    load_gta_anchors,
)
from .types import Itinerary, JourneyRequest

log = logging.getLogger(__name__)


FallbackFn = Callable[[JourneyRequest], list[Itinerary]]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


@dataclass
class Planner:
    """Fan-out orchestrator over polyroute adapters.

    Every adapter field is optional. If a field is ``None`` the
    corresponding candidate strategy is skipped. If the configured
    adapter raises, we log and continue — one bad adapter never takes
    the whole response down.

    ``fallback`` stands in for the transit pathway. It fires when
    either no transit source is wired, or the wired transit source
    produced nothing (empty or raised). The rideshare and bike-share
    pathways always run independently. This shape exists so the demo
    keeps showing diverse mixed-mode candidates before OTP2 is wired
    up; in production, set ``POLYROUTE_DISABLE_FALLBACK`` so mock data
    never masquerades as live data.
    """

    transit: Optional[TransitSource] = None
    rideshare: Optional[RideshareEstimator] = None
    bike_share: Optional[BikeShareSource] = None
    anchors: list[Anchor] = field(default_factory=load_gta_anchors)
    compose_opts: ComposeOptions = field(default_factory=ComposeOptions)
    fallback: Optional[FallbackFn] = None

    def plan(self, req: JourneyRequest) -> list[Itinerary]:
        candidates: list[Itinerary] = []

        # Direct transit (OTP2 or any source matching the TransitSource protocol)
        transit_itins: list[Itinerary] = []
        if self.transit is not None:
            transit_itins = self._safe("transit", lambda: self.transit.plan(req))
            candidates.extend(transit_itins)

        # Direct rideshare (single itinerary)
        if self.rideshare is not None:
            candidates.extend(
                self._safe(
                    "rideshare",
                    lambda: [self.rideshare.estimate(req)],
                )
            )

        # Bike share walk→bike→walk (skipped automatically on has_luggage)
        if self.bike_share is not None:
            candidates.extend(self._safe("bike_share", lambda: self.bike_share.plan(req)))

        # Composed first-mile: rideshare to anchor + transit the rest
        if self.transit is not None and self.rideshare is not None:
            candidates.extend(
                self._safe(
                    "compose_first_mile",
                    lambda: compose_first_mile(
                        req,
                        self.transit,
                        self.rideshare,
                        self.anchors,
                        self.compose_opts,
                    ),
                )
            )

        # Composed first-mile: bike share to anchor + transit the rest
        # (auto-skipped when has_luggage — see compose.py)
        if self.transit is not None and self.bike_share is not None:
            candidates.extend(
                self._safe(
                    "compose_bike_share_first_mile",
                    lambda: compose_bike_share_first_mile(
                        req,
                        self.transit,
                        self.bike_share,
                        self.anchors,
                        self.compose_opts,
                    ),
                )
            )

        # Fallback stands in for the transit pathway when no real transit
        # itineraries were produced.
        if not transit_itins and self.fallback is not None:
            log.info("planner: no transit candidates, using fallback")
            candidates.extend(self._safe("fallback", lambda: list(self.fallback(req))))

        return candidates

    def _safe(self, name: str, call: Callable[[], list[Itinerary]]) -> list[Itinerary]:
        """Call an adapter, stamp each candidate's ``source``, swallow errors."""
        try:
            out = list(call())
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("planner: %s adapter failed (%s)", name, exc)
            return []
        for it in out:
            if it.source is None:
                it.source = name
        return out


# ---------------------------------------------------------------------------
# Default planner — picks up env config
# ---------------------------------------------------------------------------


def default_planner() -> Planner:
    """Build a planner from environment variables.

    Env vars (all optional):

    - ``POLYROUTE_OTP2_URL`` — base URL of an OTP2 instance. If set,
      the OTP2 adapter is wired in as the transit source.
    - ``POLYROUTE_GBFS_URL`` — GBFS discovery URL. If set, the GBFS
      adapter is wired in as the bike-share source.
    - ``POLYROUTE_DISABLE_FALLBACK`` — any truthy value turns off the
      mock Toronto fallback. Set this in production.

    Rideshare is always available (deterministic, no network).
    """
    # Lazy-import adapters so the core package stays importable without
    # the optional deps they pull (httpx is technically core-required,
    # but the import boundary keeps things honest).
    from ..adapters.rideshare_heuristic import RideshareHeuristic

    rideshare = RideshareHeuristic()

    transit: Optional[TransitSource] = None
    otp2_url = os.getenv("POLYROUTE_OTP2_URL")
    if otp2_url:
        from ..adapters.otp2 import OTP2Adapter

        transit = OTP2Adapter(base_url=otp2_url)

    bike_share: Optional[BikeShareSource] = None
    gbfs_url = os.getenv("POLYROUTE_GBFS_URL")
    if gbfs_url:
        from ..adapters.gbfs import GBFSAdapter

        bike_share = GBFSAdapter(discovery_url=gbfs_url)

    fallback: Optional[FallbackFn] = None
    if not _truthy(os.getenv("POLYROUTE_DISABLE_FALLBACK")):
        from ..adapters.mock_toronto import generate_candidates

        fallback = generate_candidates

    return Planner(
        transit=transit,
        rideshare=rideshare,
        bike_share=bike_share,
        fallback=fallback,
    )


def _truthy(val: Optional[str]) -> bool:
    return bool(val) and val.lower() not in ("0", "false", "no", "off", "")
