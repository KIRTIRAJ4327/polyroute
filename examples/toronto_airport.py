"""Flagship demo: Fountainhead Rd → Toronto Pearson at 6am Tuesday.

Runs the full pipeline end-to-end through the Planner orchestrator so you
see the same fan-out the FastAPI server does — rideshare heuristic, mock
fallback, and (when env vars are set) OTP2 + GBFS on top.

    python examples/toronto_airport.py
    python examples/toronto_airport.py --cheap
    python examples/toronto_airport.py --luggage --arrive-by 07:45

Set ``POLYROUTE_OTP2_URL`` / ``POLYROUTE_GBFS_URL`` to pull in real data.
Set ``POLYROUTE_DISABLE_FALLBACK=1`` to hide the mock Toronto candidates.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from polyroute.adapters.mock_toronto import FOUNTAINHEAD, YYZ
from polyroute.core import JourneyRequest, score_itineraries
from polyroute.core.planner import default_planner
from polyroute.llm import explain, one_line_summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Polyroute Toronto airport demo")
    p.add_argument("--luggage", action="store_true", help="Carrying luggage — no bike options")
    p.add_argument("--cheap", action="store_true", help="Prioritize cost over time")
    p.add_argument("--fast", action="store_true", help="Prioritize time over cost")
    p.add_argument(
        "--arrive-by", type=str, default=None, help="Flight-style arrival deadline, e.g. '07:45'"
    )
    p.add_argument("--depart", type=str, default="06:00", help="Departure time, e.g. '06:00'")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Build the request
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dep_h, dep_m = map(int, args.depart.split(":"))
    depart = today + timedelta(hours=dep_h, minutes=dep_m)

    arrive_by = None
    if args.arrive_by:
        a_h, a_m = map(int, args.arrive_by.split(":"))
        arrive_by = today + timedelta(hours=a_h, minutes=a_m)

    # Preference weights
    time_w, cost_w = 1.0, 1.0
    if args.cheap:
        time_w, cost_w = 0.5, 2.0
    if args.fast:
        time_w, cost_w = 2.0, 0.5

    req = JourneyRequest(
        origin=FOUNTAINHEAD,
        destination=YYZ,
        departure_time=depart,
        arrive_by=arrive_by,
        has_luggage=args.luggage,
        time_weight=time_w,
        cost_weight=cost_w,
    )

    # Run the pipeline through the Planner so the demo mirrors the server
    planner = default_planner()
    candidates = planner.plan(req)
    scored = score_itineraries(candidates, req)

    # Render
    print()
    print(f"  {FOUNTAINHEAD.name}  →  {YYZ.name}")
    print(f"  Depart: {depart.strftime('%a %H:%M')}")
    if arrive_by:
        print(f"  Arrive by: {arrive_by.strftime('%H:%M')} (hard deadline)")
    if args.luggage:
        print("  Carrying luggage")
    print(f"  Preferences: time×{time_w}  cost×{cost_w}")
    print()
    print(f"  Found {len(candidates)} candidates, {len(scored)} on the Pareto frontier.")
    # Show the mix of sources — makes the Planner fan-out visible
    source_counts: dict[str, int] = {}
    for c in candidates:
        key = c.source or "unknown"
        source_counts[key] = source_counts.get(key, 0) + 1
    if source_counts:
        mix = ", ".join(f"{k}×{v}" for k, v in sorted(source_counts.items()))
        print(f"  Sources: {mix}")
    print()

    for i, s in enumerate(scored, 1):
        src = s.itinerary.source or "unknown"
        print(f"  {i}. {one_line_summary(s)}  [via {src}]")
        print(f"     {explain(s, scored)}")
        print()


if __name__ == "__main__":
    main()
