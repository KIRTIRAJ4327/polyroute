# Writing a new adapter

This guide targets someone who wants to add a new routing source —
another city, another mode, or a partner API. A weekend should be
enough if you follow the contract below.

## What an adapter is (and isn't)

An adapter **returns a list of `Itinerary` objects** for a `JourneyRequest`.
That's it.

An adapter **does not**:

- Score itineraries (`polyroute/core/pareto.py` owns that).
- Explain tradeoffs (`polyroute/llm/explainer.py` owns that).
- Know about other adapters — composition happens in
  `polyroute/core/compose.py`.
- Make decisions about user preference weights.

If you find yourself importing another adapter, you're in the wrong
layer — see `docs/architecture.md` §4-layer design.

## The contract

Your adapter's public entry point is a single callable:

```python
def plan(request: JourneyRequest, **adapter_specific) -> list[Itinerary]:
    ...
```

Or as a class with a `plan` method — `OTP2Adapter` in
`polyroute/adapters/otp2.py` is the canonical example.

### Inputs you must respect

| Field | Behavior |
|---|---|
| `request.origin` / `request.destination` | Route between these lat/lon pairs |
| `request.departure_time` / `request.arrive_by` | At least one is set. `arrive_by` wins if both are present |
| `request.max_walking_m` | Do not return itineraries where `walking_distance_m > max_walking_m` |
| `request.has_luggage` | Core already drops bike-share legs when luggage is on, but don't generate them in the first place if you can avoid it |
| `request.has_own_car` / `request.has_own_bike` | Same — the feasibility filter enforces this, but adapters should be polite |

### What each `Leg` must carry

- `mode`: a `Mode` enum value. Unknown mode → pick the closest; don't invent new values.
- `origin`, `destination`: `Location` with lat/lon set. `name` helps the UI.
- `start_time`, `end_time`: naive `datetime`. Timezone handling is an open question — see [#NN](https://github.com/KIRTIRAJ4327/polyroute/issues).
- `distance_m`: meters.
- `cost_cad`: CAD, float. `0.0` if the source doesn't expose fare.
- `route_name`: the rider-facing label (`"Line 2"`, `"UP"`, `"26"`).
- `operator`: the agency (`"TTC"`, `"Metrolinx"`, `"MiWay"`, `"Uber (est.)"`).
- `reliability_sigma_min`: std-dev of arrival time in minutes. See
  reliability conventions below.

## Reliability conventions

Lower = more reliable. Values are minutes of σ on the leg's arrival
time. Combined across legs as sqrt(Σ σ²) — see
`Itinerary.reliability_sigma_min`.

Starting priors (from `polyroute/adapters/otp2.py`):

| Mode | σ (min) | Source |
|---|---|---|
| `WALK` | 0.5 | Clock-like; traffic-light variance |
| `SUBWAY` | 2.0 | Grade-separated, high headway |
| `TRAIN` (GO, UP) | 2.5 | Grade-separated but lower frequency |
| `BUS` | 4.0 | Surface transit, traffic-exposed |
| `TRAM` | 4.0 | Same as bus |
| `RIDESHARE` | 5.0 | Surge + traffic |
| `CAR_OWN` | 5.0 | Same as rideshare minus surge |
| `BIKE_SHARE` | 1.5 | Predictable pace, station availability risk |
| `BIKE_OWN` | 1.0 | No station risk |

If your source has GTFS-Realtime or live telemetry, use the measured
sigma instead of the prior. If not, document the prior in your module
docstring and justify it.

## Testing

### Unit tests — always required

Write a fixture-based unit test for the response translator. Capture a
representative API response in `tests/fixtures/<source>_response.json`
and assert on mode mapping, route/operator preservation, reliability
sigma, and itinerary totals. No network.

`tests/test_otp2_adapter.py` is the pattern to copy.

### Integration tests — required if the source is live

Put them under `tests/integration/` and mark with
`@pytest.mark.integration`. The default `pytest` run skips these; they
run on `pytest -m integration`. Your fixture should probe the live
service and `pytest.skip(...)` if unreachable, so developers without
the live dep can still run the suite.

`tests/integration/test_otp2_live.py` is the pattern.

## Dependencies

- Prefer `httpx` (already a direct dependency).
- Do not add a framework import to the adapter (no FastAPI, no LangChain).
- Do not add a provider SDK for a hosted service unless the adapter is
  fundamentally tied to it (e.g., a partner API).

## Checklist before PR

- [ ] Adapter returns `Itinerary` objects that pass
      `polyroute.core.pareto.is_feasible` for at least one sample request.
- [ ] Module docstring names the data source, the version / schema it
      targets, and the date it was last validated.
- [ ] Fixture-based unit tests pass without network.
- [ ] Integration tests skip cleanly when the live service is down.
- [ ] `ruff check .` and `ruff format --check .` are clean.
- [ ] New dependencies (if any) are in `pyproject.toml` with a
      conservative lower-bound version.
- [ ] Line in `docs/architecture.md` or `README.md` mentioning the
      adapter if it's user-facing.

## Walkthrough — `mock_toronto.py`

See `polyroute/adapters/mock_toronto.py` — it's the simplest working
example. Hand-crafted candidates, no network, no real data source. Read
it alongside `polyroute/core/types.py` to see exactly which fields end
up where.
