"""Flagship demo: Fountainhead Rd → Toronto Pearson at 6am Tuesday.

Runs the full pipeline end-to-end using mock adapters so you can see
ranked, explained, Pareto-filtered results before OTP2 is running.

    python examples/toronto_airport.py
    python examples/toronto_airport.py --cheap
    python examples/toronto_airport.py --luggage --arrive-by 07:45

Once OTP2 and real adapters are wired in, swap the import in
`generate_candidates` and this script keeps working unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from polyroute.core import JourneyRequest, score_itineraries
from polyroute.adapters.mock_toronto import generate_candidates, FOUNTAINHEAD, YYZ
from polyroute.llm import explain, one_line_summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Polyroute Toronto airport demo")
    p.add_argument("--luggage", action="store_true",
                   help="Carrying luggage — no bike options")
    p.add_argument("--cheap", action="store_true",
                   help="Prioritize cost over time")
    p.add_argument("--fast", action="store_true",
                   help="Prioritize time over cost")
    p.add_argument("--arrive-by", type=str, default=None,
                   help="Flight-style arrival deadline, e.g. '07:45'")
    p.add_argument("--depart", type=str, default="06:00",
                   help="Departure time, e.g. '06:00'")
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

    # Run the pipeline
    candidates = generate_candidates(req)
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
    print(f"  Found {len(candidates)} candidates, "
          f"{len(scored)} on the Pareto frontier.")
    print()

    for i, s in enumerate(scored, 1):
        print(f"  {i}. {one_line_summary(s)}")
        print(f"     {explain(s, scored)}")
        print()


if __name__ == "__main__":
    main()
