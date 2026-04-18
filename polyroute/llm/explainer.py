"""Natural-language explanations of itineraries and tradeoffs.

This module ships a rule-based explainer that works offline with zero
dependencies — it's good enough for the MVP and for interviews. An
LLM-backed explainer (Claude / GPT / Gemini / Azure AI Foundry) will
plug in here via the same `explain()` interface once we wire it up.
"""
from __future__ import annotations

from ..core.types import Itinerary, Mode
from ..core.pareto import ScoredItinerary


MODE_LABELS = {
    Mode.WALK: "walk",
    Mode.BIKE_OWN: "your bike",
    Mode.BIKE_SHARE: "Bike Share",
    Mode.CAR_OWN: "drive",
    Mode.RIDESHARE: "Uber/Lyft",
    Mode.BUS: "bus",
    Mode.SUBWAY: "subway",
    Mode.TRAIN: "train",
    Mode.TRAM: "streetcar",
}


def _fmt_money(x: float) -> str:
    return f"${x:.2f}"


def _fmt_time(m: float) -> str:
    if m < 60:
        return f"{int(round(m))} min"
    h, r = divmod(int(round(m)), 60)
    return f"{h}h {r}m" if r else f"{h}h"


def summarize_legs(it: Itinerary) -> str:
    """Condensed itinerary description: 'Uber → subway → UP Express'."""
    non_walk = [l for l in it.legs if l.mode != Mode.WALK]
    if not non_walk:
        return "Walk"
    parts = []
    for leg in non_walk:
        label = MODE_LABELS.get(leg.mode, leg.mode.value)
        if leg.route_name:
            parts.append(f"{label} ({leg.route_name})")
        else:
            parts.append(label)
    return " → ".join(parts)


def one_line_summary(s: ScoredItinerary) -> str:
    it = s.itinerary
    return (
        f"{s.label}: {summarize_legs(it)} — "
        f"{_fmt_time(it.total_duration_min)}, "
        f"{_fmt_money(it.total_cost_cad)}"
    )


def explain(s: ScoredItinerary, others: list[ScoredItinerary]) -> str:
    """Two-to-three sentence tradeoff explanation vs alternatives."""
    it = s.itinerary
    notes: list[str] = []

    # Compare to the cheapest alternative
    cheaper = [o for o in others if o is not s and
               o.axis_values["cost"] < s.axis_values["cost"]]
    if cheaper:
        best_cheap = min(cheaper, key=lambda o: o.axis_values["cost"])
        save = s.axis_values["cost"] - best_cheap.axis_values["cost"]
        time_penalty = best_cheap.axis_values["time"] - s.axis_values["time"]
        if save >= 5:
            if time_penalty <= 5:
                notes.append(
                    f"You could save {_fmt_money(save)} with minimal time "
                    f"penalty by taking the {best_cheap.label.lower()} option."
                )
            else:
                notes.append(
                    f"This saves {_fmt_time(time_penalty)} vs the cheapest "
                    f"option, at {_fmt_money(save)} extra."
                )

    # Reliability warning
    if it.reliability_sigma_min > 5:
        notes.append(
            f"Plan for up to {_fmt_time(2 * it.reliability_sigma_min)} "
            f"of delay — transit or surge variance is notable here."
        )

    # Transfer warning
    if it.num_transfers >= 2:
        notes.append(
            f"{it.num_transfers} transfers — tight connections if anything "
            f"runs late."
        )

    # Walking note
    if it.walking_distance_m > 800:
        notes.append(
            f"About {int(it.walking_distance_m)}m of walking total."
        )

    if not notes:
        notes.append("Straightforward option with no major caveats.")

    return " ".join(notes)
