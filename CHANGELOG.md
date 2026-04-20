# Changelog

All notable changes to polyroute. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project follows [SemVer](https://semver.org/).

## [0.1.0] — 2026-04-20

First tagged release. The adapter set, orchestrator, API, and web UI are
feature-complete for the Toronto airport wedge (CLAUDE.md §3.6 #1). Everything
past v0.1 is marked as v0.2+ in the roadmap.

### Added

- **Core domain model** — `Location`, `Leg`, `Itinerary`, `JourneyRequest`,
  `Mode`. Pure types, no I/O.
- **Pareto filter + scoring** — `pareto_front`, `score_itineraries`,
  `is_feasible`. Dominance on 4D `(time, cost, effort, reliability)`;
  min-max normalized weighted sum; extreme labels (Fastest, Cheapest,
  Most reliable, Least effort, Balanced).
- **Adapters**
  - `OTP2Adapter` — OTP2 Index GraphQL client with mode-map and reliability
    priors. Fixture-backed unit tests; live tests opt-in via
    `-m integration`.
  - `RideshareHeuristic` — published per-km + surge rate-card for
    UberX-Toronto, always labeled "Estimate only — not a live price"
    per CLAUDE.md §3.2.
  - `GBFSAdapter` — Bike Share Toronto GBFS v2 reader; builds
    walk→bike→walk itineraries via nearest available station on each
    end. Revalidate fare model quarterly.
  - `mock_toronto.generate_candidates` — hand-crafted Fountainhead → YYZ
    candidates for the zero-config demo pathway.
- **Composition strategy** (`polyroute/core/compose.py`)
  - `compose_first_mile` — rideshare-to-anchor + transit-the-rest
  - `compose_bike_share_first_mile` — walk→bike→walk first mile +
    transit-the-rest; auto-skipped when `has_luggage`
  - `load_gta_anchors` from `anchors_gta.json` (Kipling, Islington,
    Bloor-Yonge, Dundas West, Union, GO stations)
- **Planner orchestrator** (`polyroute/core/planner.py`)
  - Protocol-based adapter slots so one broken adapter never takes down
    the whole call
  - `default_planner()` reads `POLYROUTE_OTP2_URL`, `POLYROUTE_GBFS_URL`,
    `POLYROUTE_DISABLE_FALLBACK`
  - Fallback stands in for the transit pathway only — rideshare and
    bike-share run independently
  - Per-candidate `source` stamped onto each itinerary
- **Explainer**
  - Rule-based default (`polyroute/llm/explainer.py`)
  - Model-agnostic LLM explainer (`polyroute/llm/llm_explainer.py`) with
    concrete generators for Anthropic, OpenAI, Azure AI Foundry; SDKs
    lazy-imported; rule-based fallback on any provider error;
    `ExplainResult.source` reports which path produced the text.
- **FastAPI server** — `/health`, `/presets`, `/plan`. Module-level
  planner + explainer, both swappable via `set_planner` / `set_explainer`
  for tests. `/plan` responses include per-candidate
  `source` + `explanation_source` and query-level `sources[]`.
- **Web UI** — single-file `web/index.html`. Editorial/transit-notebook
  aesthetic. Renders query-level source pills and per-itinerary
  provenance.
- **CLI demo** — `python examples/toronto_airport.py` with
  `--cheap` / `--fast` / `--luggage` / `--arrive-by`.
- **OTP2 Docker setup** — `docker/otp2-toronto/` with feed fetch script
  (TTC, GO, UP, MiWay, Brampton, Ontario OSM).
- **App Dockerfile** — multi-stage Python 3.12 image for the FastAPI
  app, separate from the OTP2 container. Healthcheck, non-root user.
- **Tests** — 88 unit tests (network-free), 5 integration tests (opt-in
  with `pytest -m integration`).
- **CI** — pytest + ruff matrix on Python 3.10 / 3.11 / 3.12.
- **Docs** — `docs/architecture.md`, `docs/adapters.md`, plus
  `docs/interviews/` and `docs/sred/` scaffolding.

### Design decisions codified

- No live rideshare pricing — heuristic only, per Uber API ToU §II B
  (CLAUDE.md §3.2).
- No LangGraph in the single-query plan→rank→explain path
  (CLAUDE.md §3.4, §14).
- Toronto/GTA only; no other cities until the wedge is validated
  (CLAUDE.md §4.2).
- MIT license; B2B2C monetization endgame (CLAUDE.md §4.8).

[0.1.0]: https://github.com/KIRTIRAJ4327/polyroute/releases/tag/v0.1.0
