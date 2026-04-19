"""FastAPI server — exposes polyroute over HTTP.

    uvicorn polyroute.api.server:app --reload

Endpoints:
    GET  /            → serves the minimal web UI (web/index.html)
    GET  /health      → liveness
    POST /plan        → plan a journey
    GET  /presets     → named O/D presets for the demo

Keep this thin. All business logic lives in polyroute.core and adapters.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..core import JourneyRequest, Location, score_itineraries
from ..adapters.mock_toronto import (
    FOUNTAINHEAD,
    YYZ,
    KIPLING_STN,
    UNION_STN,
    generate_candidates,
)
from ..llm import explain, summarize_legs


app = FastAPI(
    title="polyroute",
    description="Agentic multi-modal journey planning",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


# Serve the web UI at /
WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    idx = WEB_DIR / "index.html"
    if not idx.exists():
        raise HTTPException(404, "web/index.html missing")
    return FileResponse(idx)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class LocationIn(BaseModel):
    lat: float
    lon: float
    name: Optional[str] = None


class PlanRequest(BaseModel):
    origin: LocationIn
    destination: LocationIn
    depart_at: Optional[str] = Field(
        None,
        description="ISO datetime; defaults to now",
    )
    arrive_by: Optional[str] = Field(
        None,
        description="ISO datetime — hard deadline (e.g. flight time)",
    )
    has_luggage: bool = False
    has_own_bike: bool = False
    has_own_car: bool = False
    time_weight: float = 1.0
    cost_weight: float = 1.0
    effort_weight: float = 0.5
    reliability_weight: float = 1.0


class LegOut(BaseModel):
    mode: str
    origin: str
    destination: str
    start_time: str
    end_time: str
    duration_min: float
    distance_m: float
    cost_cad: float
    route_name: Optional[str] = None
    operator: Optional[str] = None


class ItineraryOut(BaseModel):
    label: str
    summary: str
    explanation: str
    total_duration_min: float
    total_cost_cad: float
    num_transfers: int
    walking_distance_m: float
    reliability_sigma_min: float
    legs: list[LegOut]


class PlanResponse(BaseModel):
    candidates_generated: int
    pareto_optimal: int
    itineraries: list[ItineraryOut]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.0.1"}


@app.get("/presets")
def presets() -> dict:
    """Named locations for the demo. Makes the UI one-click."""

    def _to_dict(loc: Location) -> dict:
        return {"lat": loc.lat, "lon": loc.lon, "name": loc.name}

    return {
        "fountainhead": _to_dict(FOUNTAINHEAD),
        "yyz": _to_dict(YYZ),
        "kipling": _to_dict(KIPLING_STN),
        "union": _to_dict(UNION_STN),
    }


@app.post("/plan", response_model=PlanResponse)
def plan(req_in: PlanRequest) -> PlanResponse:
    # Parse times
    depart = (
        datetime.fromisoformat(req_in.depart_at)
        if req_in.depart_at
        else datetime.now().replace(second=0, microsecond=0)
    )
    arrive_by = datetime.fromisoformat(req_in.arrive_by) if req_in.arrive_by else None

    req = JourneyRequest(
        origin=Location(
            lat=req_in.origin.lat,
            lon=req_in.origin.lon,
            name=req_in.origin.name,
        ),
        destination=Location(
            lat=req_in.destination.lat,
            lon=req_in.destination.lon,
            name=req_in.destination.name,
        ),
        departure_time=depart,
        arrive_by=arrive_by,
        has_luggage=req_in.has_luggage,
        has_own_bike=req_in.has_own_bike,
        has_own_car=req_in.has_own_car,
        time_weight=req_in.time_weight,
        cost_weight=req_in.cost_weight,
        effort_weight=req_in.effort_weight,
        reliability_weight=req_in.reliability_weight,
    )

    candidates = generate_candidates(req)
    scored = score_itineraries(candidates, req)

    itineraries: list[ItineraryOut] = []
    for s in scored:
        it = s.itinerary
        itineraries.append(
            ItineraryOut(
                label=s.label,
                summary=summarize_legs(it),
                explanation=explain(s, scored),
                total_duration_min=round(it.total_duration_min, 1),
                total_cost_cad=round(it.total_cost_cad, 2),
                num_transfers=it.num_transfers,
                walking_distance_m=round(it.walking_distance_m, 0),
                reliability_sigma_min=round(it.reliability_sigma_min, 1),
                legs=[
                    LegOut(
                        mode=leg.mode.value,
                        origin=leg.origin.name or f"{leg.origin.lat:.4f},{leg.origin.lon:.4f}",
                        destination=leg.destination.name
                        or f"{leg.destination.lat:.4f},{leg.destination.lon:.4f}",
                        start_time=leg.start_time.isoformat(),
                        end_time=leg.end_time.isoformat(),
                        duration_min=round(leg.duration_min, 1),
                        distance_m=round(leg.distance_m, 0),
                        cost_cad=round(leg.cost_cad, 2),
                        route_name=leg.route_name,
                        operator=leg.operator,
                    )
                    for leg in it.legs
                ],
            )
        )

    return PlanResponse(
        candidates_generated=len(candidates),
        pareto_optimal=len(scored),
        itineraries=itineraries,
    )
