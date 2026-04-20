# CLAUDE.md — polyroute project handoff

**This file is the permanent working memory for Claude Code on this project. Read it in full at the start of every session. Keep it updated as decisions, research, and scope change.**

Last updated: April 2026
Owner: Kirtirajsinh Atodariya (Kirtiraj)
Repo: https://github.com/KIRTIRAJ4327/polyroute

---

## 1. What this project is (the one-paragraph version)

Polyroute is an open-source Python library and reference application for **agentic, multi-modal journey planning**. It takes an A→B query, fans out to multiple data sources (transit, rideshare, bike share, routing engines), generates candidate itineraries that creatively *mix* modes (Uber-to-transit-station, park-and-ride, bike-to-GO-train), filters them to the Pareto frontier across time/cost/effort/reliability, scores them by user preference, and produces natural-language tradeoff explanations. The wedge is airport access in Toronto / GTA. The strategic end goal is **not** a consumer app — see section 3 for why — but an OSS reasoning layer that can later be sold to transit agencies, airports, and employers (B2B2C).

---

## 2. Who the owner is and what he brings

Kirtiraj is a senior Gen AI Developer at TCS Canada (contract through June 2026), working on innovation banking projects for CIBC. He is also actively exploring a Gen AI Developer opportunity at BMO through Virtusa. Technical background:

- **Agentic AI systems** with LangGraph, Azure AI Foundry, multi-agent pipelines
- **Azure ecosystem** — AI-102 certified (score 805), daily user of AI Foundry and related services
- **Hackathon builder** — Analytics Track winner at HackTheBrain 2025, StormHacks 2025 presenter, GenAI Genesis participant. Strong bias toward deployable, production-focused solutions over theoretical work.
- **Production code review agents** at TCS (Java, TypeScript, Angular, build error resolution) using GitHub Copilot agents in VS Code and Azure AI Foundry
- **Data sanitization pipelines** for banking (MT101 SWIFT payment files, PII masking, Faker + paramiko)
- **SDLC agentic systems** using Neo4j as knowledge fabric with hybrid search
- **Flutter / mobile** background (Atul Bakery app) and prior Indian government technology experience

Communication style preferences (important for Claude Code):
- **Casual and direct.** No corporate-sounding prose. No excessive apologies.
- **Accuracy over confidence.** He has explicitly corrected prior sessions for giving unverified answers, particularly on Azure billing and pricing. When uncertain, say so and search.
- **Concise and genuine.** Shorter is better when the content is right.
- **Continuous learning mindset.** Explanations of *why* a decision was made matter, not just what.

He is family-oriented, values authenticity, enjoys chess, cooking, running. Based in Toronto. Arrived in Canada late 2023 for post-graduate certificate at Humber College; pivoted from government IT / Flutter work to AI/ML in his third semester. Working on Canadian permanent residence through Express Entry / CEC.

**Context for motivation**: This project is primarily a career/portfolio accelerator with *optional* upside as a funded startup/product. Kirtiraj has a stable income and a strong career trajectory — the risk profile does not support quitting his contract for this. The project's job is to (a) showcase his agentic AI skills concretely, (b) explore whether the idea has real legs through disciplined validation, (c) preserve optionality for commercialization if it gains traction. **Do not push him toward "go full-time on this" framings.** Every decision should assume a part-time builder with 6–10 hours per week.

---

## 3. The research that underpins every major decision

Before writing any code, Claude Code must internalize these findings. They were produced by a deep research pass in the originating claude.ai conversation. They are non-negotiable starting constraints — not opinions to be relitigated.

### 3.1 Consumer multi-modal journey planning is a proven graveyard

The pattern across 12 years and billions of dollars is uniform:

- **Citymapper** (founded 2011, London): raised ~$52M venture + $8M crowdfund, reached 108 cities, lost £7.4M on £5.1M revenue in 2021, sold to Via in a March 2023 "washout" where most investors did not recover capital. Citymapper Club subscription launched at $2.99/month in late 2022, was halved to $1.49/month within six months of acquisition, and most features were moved free — a clear admission that consumer willingness to pay is below the cost of maintaining multi-city data.
- **MaaS Global / Whim** (Helsinki): raised €149M from Toyota, Mitsubishi, BP Ventures. Peaked at ~10,000 MAU. Burned €75.5M in seven years. Bankrupt March 2024 with €9.3M of losses on €3.8M of revenue. Failure mode: forced users to pre-pay subscription bundles when users actually wanted per-trip flexibility. Founder Sampo Hietanen (once called "the father of MaaS") conceded they tried to go "from zero to one in one step."
- **Trafi** (Lithuania): the quiet technical winner behind Jelbi Berlin, Floya Brussels, Breeze Solent. Exited to Canadian enterprise-software consolidator Enghouse Systems in April 2025 for undisclosed (almost certainly modest) terms. Jelbi worked because **the city-owned agency (BVG Berlin) absorbed customer acquisition cost** — Trafi was a white-label vendor.
- **Transit app** (Montreal): the one unambiguous consumer success. 12 years old, 900+ cities, estimated $5–25M ARR on just $27M total capital raised. Moat is **official partnership status with dozens of transit agencies** — externalizes CAC to the agencies themselves. It is a B2B2C business dressed as a B2C app.

**Implication for polyroute**: Do not build a consumer subscription app. Do not pitch this as "better Google Maps for consumers." Every strategic decision must assume the eventual monetization path is B2B (agency / airport / employer / white-label) with the consumer app as a wedge or reference implementation.

### 3.2 Rideshare APIs make honest price comparison legally impossible

- Uber's Price Estimates API Terms of Use **explicitly prohibit** using the API to offer price comparisons with competitive third-party services (§ II B of the API ToU). This is why Citymapper, Transit, Google Maps, and Apple Maps only show Uber via deep links with cached/estimated fares.
- Lyft closed its public Developer Platform in 2021. API access now requires a Lyft Business account tied to a specific corporate program.
- Bolt, Didi, Ola, Grab all have similarly restricted partner-only access.

**Implication for polyroute**: The rideshare adapter must be a **published per-km + surge heuristic**, clearly labeled as an estimate. Real live pricing is only available through a partner relationship (requires being a corporate customer or B2B partner). This is honest to the user and keeps us on the right side of every ToU. Do not scrape live prices. Do not promise "live Uber/Lyft comparison" anywhere in marketing.

### 3.3 The routing stack is commoditized open-source

This is good news — it means the hard technical substrate is free and the differentiator is what we build on top.

- **OpenTripPlanner 2 (OTP2)** — Java-based, uses RAPTOR (Delling/Pajor/Werneck 2012), in production at Entur Norway, HSL Finland, TriMet Portland, and dozens of others. Handles GTFS static, GTFS-Realtime, GBFS bike share, park-and-ride, GTFS-Flex demand-responsive transit natively. Sub-second query latency. This is our primary transit router.
- **OSRM** / **Valhalla** / **GraphHopper** — for car, walk, bike routing on OSM data.
- **GBFS** — bike share standard, Bike Share Toronto publishes compliant feed.
- **RAPTOR** computes Pareto-optimal journeys across arrival time and transfers in tens to hundreds of milliseconds without preprocessing.

**Implication**: We do not invent routing algorithms. We invent the *orchestration* layer — candidate generation, Pareto filtering over more axes than OTP2's built-in two, preference-weighted scoring, and natural-language explanation.

### 3.4 LangGraph is valuable but easy to over-apply

LangGraph shines for long-running, stateful, resumable workflows with human-in-the-loop checkpoints — multi-day travel planning with approvals, mid-journey re-routing on disruption. For the single-query plan → rank → explain flow, a single LLM call with structured tool use is enough and ships 3× faster. **Reserve LangGraph for v0.2 features** like "plan my week of commutes and adjust for weather/transit disruptions" or "replan this trip now that my 7:15 train is delayed."

### 3.5 Funding landscape (if the project ever pursues it)

- Consumer mobility seed / Series A is the coldest corner of mobility VC. Maniv, Trucks VC, Fontinalis, MobilityFund, Mobilitech Capital are active but have explicitly learned to avoid consumer journey planners after Citymapper and MaaS Global. Their 2024–2025 cheques concentrated on B2B software, fleet electrification, and logistics AI.
- **Canadian non-dilutive stack is the right primary path** for at least the first 18 months:
  - **SR&ED** — 35% refundable ITC for CCPCs on first $4M of eligible R&D (raised from $3M in Budget 2025). Ontario Innovation Tax Credit stacks another 8%. Effective recovery ~43% on qualifying engineering time. Refundable tax credits.
  - **IRAP** — averages ~$500K per contribution, covers up to 80% of eligible R&D labour, can stack with SR&ED (IRAP reduces SR&ED base dollar-for-dollar). Requires ITA (Industrial Technology Advisor) sponsorship.
  - **Accelerators** — MaRS Discovery District, Creative Destruction Lab (CDL-Toronto AI stream), NextAI ($100–250K for 6–8% equity), DMZ. Most take zero or minimal equity.
- Document all engineering time for SR&ED eligibility from day one. Commit messages, issue descriptions, design docs, and test plans are all evidence.

### 3.6 The three viable wedges for a Toronto solo founder

In order of defensibility:

1. **Airport access (Pearson)**. Clearest willingness-to-pay signal (missed flights cost hundreds of dollars). Existing tools handle this poorly because they don't weight cost against reliability under a hard deadline. GTAA partnership is a realistic 12-month pitch. This is our starting wedge.
2. **Newcomer wayfinding**. Ontario hosts ~200,000 international students plus PR inflows. PRESTO / GO / UP / TTC fare integration is genuinely confusing to new arrivals. LLM-generated plain-language tradeoff explanations add real non-commodity value. Monetization via university and settlement-agency partnerships. Kirtiraj has lived experience here and Humber College alumni network access.
3. **Corporate commute tools** (benchmarks: Commutifi, RideAmigos, Luum). ACVs $15–60K per 1,000 employees. HR or sustainability as buyer. 6–12 month sales cycles. This is the eventual pivot destination, not the starting point.

---

## 4. Strategic non-negotiables (do not relitigate these without explicit owner consent)

These are the rails. When in doubt, default to preserving them.

1. **The library is open source (MIT).** Hosted products, if any, sit on top.
2. **Toronto / GTA only for v0.x.** Do not add other cities until v0.1.0 ships and the Toronto wedge is validated.
3. **Airport-access wedge is the first validation target.** Do not broaden scope until interviews are done and the wedge is proven.
4. **Web-first (PWA-capable HTML).** No native iOS/Android until post-PMF signal. React Native / Expo is a v0.2+ consideration.
5. **No live rideshare pricing.** Heuristic estimator only, clearly labeled.
6. **No LangGraph in the core plan→rank→explain path.** Reserve it for stateful / multi-step flows.
7. **No scope creep into real-time navigation.** v1 is trip *planning* at departure. Mid-journey replanning is v0.2+.
8. **B2B2C is the endgame.** Never frame the product as a consumer subscription app in README, LinkedIn posts, or pitches.
9. **Accuracy over confidence.** When unsure, search or flag uncertainty. Do not fabricate citations, API prices, or behavior.
10. **Respect Kirtiraj's time.** Default to 6–10 hr/week cadence. Do not propose plans that require unrealistic hours.

---

## 5. The repo (what already exists)

As of handoff, the following is committed or ready to commit:

```
polyroute/
├── README.md                       # Editorial-style intro. B2B2C positioning.
├── CONTRIBUTING.md
├── LICENSE                         # MIT
├── pyproject.toml                  # Installable, extras: [dev], [api], [agent]
├── .gitignore
├── CLAUDE.md                       # THIS FILE — working memory
│
├── polyroute/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py                # Leg, Itinerary, JourneyRequest, Location, Mode
│   │   ├── pareto.py               # pareto_front, score_itineraries, is_feasible
│   │   ├── compose.py              # first-mile rideshare → transit-anchor composition
│   │   ├── planner.py              # fan-out orchestrator + env-driven default_planner()
│   │   └── anchors_gta.json        # Kipling, Islington, Bloor-Yonge, Dundas West, Union, ...
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── mock_toronto.py         # 5 realistic Fountainhead→YYZ candidates
│   │   ├── otp2.py                 # OTP2 Index GraphQL adapter (transit/walk/bike)
│   │   ├── rideshare_heuristic.py  # Clearly-labeled rate-card + surge estimator (no live prices)
│   │   └── gbfs.py                 # GBFS v2 adapter (Bike Share Toronto) — walk→bike→walk
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── explainer.py            # Rule-based tradeoff explanations
│   │   └── llm_explainer.py        # Model-agnostic LLM explainer (Anthropic / OpenAI / Azure AI Foundry)
│   └── api/
│       ├── __init__.py
│       └── server.py               # FastAPI: /health /presets /plan
│
├── tests/
│   ├── test_core.py                # Pareto + types
│   ├── test_otp2_adapter.py        # fixture-based unit tests for OTP2 mapper
│   ├── test_rideshare_heuristic.py # rate-card, surge, determinism
│   ├── test_compose.py             # composition strategy with mocked sources
│   ├── test_llm_explainer.py       # fake-generate LLM explainer, fallback, truncation
│   ├── test_gbfs_adapter.py        # GBFS merge, nearest-station, fare, walk→bike→walk
│   ├── test_planner.py             # fan-out, graceful degradation, env-var wiring
│   ├── test_api.py                 # FastAPI /plan end-to-end with injected planner
│   ├── fixtures/otp2_plan_response.json
│   ├── fixtures/gbfs_station_information.json
│   ├── fixtures/gbfs_station_status.json
│   └── integration/
│       ├── test_otp2_live.py       # marked `integration`; skips if OTP2 unreachable
│       └── test_gbfs_live.py       # marked `integration`; skips if GBFS feed unreachable
│
├── examples/
│   └── toronto_airport.py          # CLI demo with --cheap --fast --luggage --arrive-by
│
├── web/
│   └── index.html                  # Editorial/transit-notebook aesthetic UI
│
├── docker/
│   └── otp2-toronto/
│       ├── README.md
│       ├── docker-compose.yml
│       └── fetch-feeds.sh          # TTC, GO, UP, MiWay, Brampton, OSM Ontario
│
├── docs/
│   ├── architecture.md             # 4-layer design doc
│   ├── adapters.md                 # how to write a new adapter
│   ├── interviews/                 # Track D: recruiting posts, script, notes template
│   └── sred/                       # SR&ED monthly engineering logs
│
└── .github/workflows/ci.yml        # pytest + ruff matrix on Py 3.10/3.11/3.12
```

### What's working end-to-end
- `pytest` passes (86 unit tests covering core, OTP2 mapper, rideshare, composition, GBFS, LLM explainer, LLM API wiring, Planner, API); 5 integration tests opt-in
- `python examples/toronto_airport.py` → prints 5 candidates, 4 on Pareto frontier, with labels and explanations
- `uvicorn polyroute.api.server:app` → serves web UI at `/`; `POST /plan` routes through `Planner.default_planner()` and returns `candidates_generated`, `pareto_optimal`, ranked `itineraries`, and a `sources` provenance list
- `--cheap` / `--fast` / `--luggage` / `--arrive-by` flags all correctly shift ranking
- CI runs pytest + ruff on every push (Python 3.10 / 3.11 / 3.12)

### What's landed since initial scaffold
- **OTP2 adapter** (`polyroute/adapters/otp2.py`) — Index GraphQL client + mode-map + sigma priors. Unit-tested against a captured fixture; live-tested via opt-in integration suite.
- **Rideshare heuristic** (`polyroute/adapters/rideshare_heuristic.py`) — rate-card + surge table for UberX-Toronto, snapshot-dated, always labeled "Estimate only — not a live price" per CLAUDE.md §3.2.
- **Composition strategy** (`polyroute/core/compose.py` + `anchors_gta.json`) — two patterns: `compose_first_mile(req, transit, rideshare, anchors)` stitches rideshare-to-anchor onto transit-to-destination, and `compose_bike_share_first_mile(req, transit, bike_share, anchors)` does the same with a walk→bike→walk first leg (auto-skipped on `has_luggage`). Pure; takes `Protocol` sources so it does not depend on concrete adapters.
- **LLM explainer** (`polyroute/llm/llm_explainer.py`) — provider-agnostic `LLMExplainer` that takes a `Generate = Callable[[str], str]`. Concrete adapters for Anthropic, OpenAI, and Azure AI Foundry live in the same module with lazy SDK imports. Falls back to the rule-based explainer on any provider error and stamps `ExplainResult.source` so the UI can show which path produced the text. Install with `pip install -e ".[llm]"`.
- **GBFS adapter** (`polyroute/adapters/gbfs.py`) — reads Bike Share Toronto's GBFS v2 feed (configurable discovery URL) and builds a walk → bike → walk itinerary using the nearest station with bikes (origin side) and the nearest with free docks (destination side). Fare model is $1 unlock + $0.12/min capped at the day-pass price; revalidate quarterly. Unit tests run on captured fixtures; live tests in `tests/integration/test_gbfs_live.py` skip cleanly when the feed is unreachable.
- **Planner orchestrator** (`polyroute/core/planner.py`) — fan-out seam. Takes optional `transit`, `rideshare`, `bike_share`, `fallback` sources (by `Protocol` shape, not concrete adapter), plus anchors + `ComposeOptions`. `plan(req)` runs each live adapter inside a `_safe()` try/except so one broken adapter never takes the call down, and layers composed rideshare→anchor→transit and bike-share→anchor→transit candidates on top when the corresponding pair is wired. Fallback semantic: `mock_toronto` stands in for the transit pathway only — it fires when no transit itineraries were produced (either `transit=None` or the wired source raised/returned `[]`). Rideshare + bike-share run independently of the fallback. `default_planner()` reads `POLYROUTE_OTP2_URL`, `POLYROUTE_GBFS_URL`, and `POLYROUTE_DISABLE_FALLBACK` so a zero-config instance works for the demo and production flips `POLYROUTE_DISABLE_FALLBACK=1` to prevent mock data from masquerading as live.
- **API wiring** — `polyroute/api/server.py` now holds a module-level `_planner: Planner = default_planner()` (swap via `set_planner()` for tests and custom embeds) and `/plan` calls `planner.plan(req)` instead of `mock_toronto.generate_candidates` directly. `PlanResponse` gained a `sources: list[str]` field — reports which adapters were wired (`transit`, `rideshare`, `bike_share`, `compose_first_mile`, `compose_bike_share_first_mile`) plus `mock_fallback` when the fallback pathway actually fires (no transit wired + fallback present + candidates produced). `tests/test_api.py` exercises the full stack through FastAPI's `TestClient` with injected fakes. `tests/test_planner.py` covers fan-out, graceful degradation, and env-var wiring.
- **LLM explainer wired through API** — server exposes a module-level `_explainer: Optional[LLMExplainer] = default_explainer()` (swap via `set_explainer()` in tests). `default_explainer()` reads `POLYROUTE_LLM_PROVIDER` (`anthropic` | `openai` | `azure`) + `POLYROUTE_LLM_MODEL` and returns an `LLMExplainer` whose `generate` callable lazy-imports the SDK on first call. When the env var is absent, unknown, or the Azure path is missing a deployment, the server falls back to the rule-based explainer cleanly. Each `ItineraryOut` now carries `explanation_source` (`"llm"` | `"rule-based-fallback"` | `"rule-based"`) so the UI can badge generated output. The web UI renders an `LLM` / `RULE` badge next to the explanation accordingly.

### What's still stubbed
- **LangGraph agent wrapper** folder exists but is empty. Intentionally deferred.
- **OTP2 live-container integration tests** — `tests/integration/test_otp2_live.py` runs against a real OTP2 GraphQL endpoint when `POLYROUTE_OTP2_URL` is set; skipped otherwise. Still needs a green run against the full GTA feed set.
- **Per-candidate provenance** — `PlanResponse.sources` currently describes wiring (+ fallback-fired heuristic), not which adapter produced each specific candidate. A `PlannerResult` diagnostic struct is the clean fix when a consumer actually needs this.

---

## 6. The four-layer architecture (memorize this)

```
  JourneyRequest
       │
       ▼
  ┌────────────┐
  │ Adapters   │  ← many sources, parallel fan-out, no cross-knowledge
  └─────┬──────┘
        │ Itineraries (candidates)
        ▼
  ┌────────────┐
  │ Core       │  ← Pareto filter + feasibility. Pure math. No I/O.
  └─────┬──────┘
        │ Non-dominated set
        ▼
  ┌────────────┐
  │ Scoring    │  ← min-max normalize, weighted sum, label extremes
  └─────┬──────┘
        │ ScoredItinerary[] (ranked)
        ▼
  ┌────────────┐
  │ Explainer  │  ← rule-based today, model-agnostic LLM tomorrow
  └─────┬──────┘
        ▼
     Response
```

**Invariants:**
- Adapters do not know about each other, do not score, do not explain.
- Core is pure. No framework imports, no I/O.
- Scoring consumes the Pareto front only (never the raw candidate list).
- Explainer consumes ScoredItinerary only. Swap rule-based for LLM without changing callers.

### Axis definitions (all: lower is better)

- `time` — `total_duration_min`
- `cost` — `total_cost_cad`
- `effort` — `walking_distance_m / 100 + num_transfers * 5`
- `reliability` — combined sigma (sqrt of sum of leg variances)

### Feasibility hard gates (pre-scoring)

- Walking distance ≤ `req.max_walking_m`
- Luggage excludes `BIKE_OWN` and `BIKE_SHARE` legs
- `CAR_OWN` requires `has_own_car=True`; `BIKE_OWN` requires `has_own_bike=True`
- If `arrive_by` is set, 90% confidence arrival must beat the deadline (uses `arrival_by(0.90)` which applies z=1.282 to the combined sigma)

---

## 7. The roadmap (priority order)

### v0.1.0 — "real data, real users" (target: end of weekend 4)

Hard requirements:
1. OTP2 running locally with full GTA feeds (TTC, GO, UP Express, MiWay, Brampton)
2. `polyroute/adapters/otp2.py` — replaces `mock_toronto.py` for the transit/walk/bike portions
3. `polyroute/adapters/rideshare_heuristic.py` — clearly-labeled-estimate pricing based on published Uber Toronto rates + time-of-day surge multiplier
4. `polyroute/adapters/gbfs.py` — Bike Share Toronto station availability
5. Composition strategy module — generates first-mile/last-mile mixed-mode candidates around "transit anchors" (Kipling, Islington, Bloor, Dundas West, Union, major GO stations)
6. LLM explainer wired to Claude via Anthropic SDK (model-agnostic adapter; also support OpenAI and Azure AI Foundry). Rule-based stays as the zero-dep fallback.
7. Integration tests for the OTP2 adapter against a known corridor
8. v0.1.0 tagged and published to PyPI
9. **Parallel track: 10 user interviews completed** (see section 8)

### v0.2.0 — agentic depth

- LangGraph orchestrator for stateful / multi-step flows: week planning, disruption replanning
- Real-time disruption handling (GTFS-Realtime monitoring, proactive alerts)
- Personal assets + preferences persisted between queries
- Basic account system (just to store preferences — not for payment)

### v0.3.0 — second city / plugin maturity

- Montreal or Vancouver as second city (forces genuine generalization)
- Formal plugin spec — writing a new adapter should take a weekend
- Published "how to add your city" guide

### v1.0 — B2B pilot ready

- Hosted demo deployment on Fly.io or Azure (Kirtiraj knows Azure)
- Rate limiting, logging, observability
- Bring-your-own rideshare partner credentials
- One signed LOI from GTAA, a Mississauga/Brampton employer, or a settlement agency
- Pitch deck + pricing page for B2B

---

## 8. The 90-day validation plan (runs in parallel to building)

The research was unambiguous: **the most common failure mode in this space is building the wrong thing efficiently.** Interviews are non-negotiable.

### Weeks 1–2: Recruit and talk to 10 Pearson commuters

Recruit via:
- r/TorontoCommuting, r/personalfinancecanada, r/Mississauga, r/Brampton
- LinkedIn post tagged to Humber College alumni network
- Kirtiraj's existing hackathon community connections

Interview script (20 minutes, free-form):
1. "Walk me through the last time you traveled to or from Pearson."
2. "What did you use to plan it? What did you actually do?"
3. "What did the app get wrong or miss?"
4. "How much would saving 15 minutes be worth? $20? $5? Nothing?"
5. "How much would saving $20 be worth if it cost you 15 extra minutes?"
6. "Would you ever take an Uber part of the way and transit the rest?"
7. "What do you do when your flight is at 6am and transit doesn't run yet?"
8. Demo polyroute, ask for unfiltered reaction
9. "Would you pay anything for a tool like this? Why or why not?"
10. "Who else should I talk to?"

### Weeks 3–4: 10 newcomer interviews

Same script, different framing — focus on the confusion of PRESTO / GO / UP / TTC fare integration and the "is this neighborhood safe at this time" angle.

### Weeks 5–8: Let the interviews drive the build

If the interviews reveal a feature polyroute doesn't have but users desperately want, build that. If they reveal a corridor other than Pearson that's more painful, reconsider the wedge.

### Weeks 9–12: One letter of intent

Goal: one signed LOI from GTAA, a Mississauga/Brampton employer, OR a settlement agency by end of week 12. If none is achievable, the thesis is likely wrong and the right move is to pivot into a B2B developer-tools API (the Rome2Rio / Skedgo path) rather than push harder on B2C.

---

## 9. Working conventions for Claude Code

### Code style
- Python 3.10+, type hints on all public APIs
- `ruff` for lint + format (`ruff check .`, `ruff format .`)
- Tests required for any new logic in `core/`. The math has to be right.
- No premature abstraction. Concrete first, generic later.
- Keep `core/` pure — no I/O, no framework imports, no LLM calls.

### Commit hygiene
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Commit at logical checkpoints, not every file save
- Each commit message should explain *why*, not just *what*
- Good commit log is SR&ED evidence — treat it as such

### Testing
- `pytest` must pass before any commit touching core logic
- Integration tests that hit OTP2 should be marked with `@pytest.mark.integration` and skippable without the container running
- Target coverage for `core/` is 90%+. Adapters can be lower given live-system dependencies.

### Branching
- `main` stays deployable
- Feature branches: `feat/otp2-adapter`, `feat/rideshare-heuristic`, etc.
- Kirtiraj can review and merge solo; PRs are optional when working alone but useful for self-review

### Search / knowledge cutoff
- When adding a new library or touching an API, verify current pricing / rate limits / syntax by searching the web. Do not rely on training data for anything that can change.
- Especially true for: Azure AI Foundry pricing, Anthropic API pricing, OTP2 releases, GTFS feed URLs (these drift), LangGraph API (evolves rapidly).

### Documentation
- Every public function in `core/` and `adapters/` needs a docstring explaining inputs, outputs, and the one non-obvious thing about it.
- Architecture changes get a PR to `docs/architecture.md`.
- README is for outsiders (including future investors / agency contacts). Keep it current and professional.

### Interaction style with Kirtiraj
- Be direct. He wants the real answer, not a hedged one.
- Flag uncertainty explicitly. "I don't know, let me check" beats making something up.
- Pushback is welcome. If you think a request is wrong, say why.
- Don't over-explain simple things, but do explain non-obvious technical decisions.
- Respect the "accuracy over confidence" rule — this has been explicitly flagged in prior sessions.

---

## 10. Specific technical decisions already made (do not rehash)

### Core types (in `polyroute/core/types.py`)
- `Location` is frozen dataclass with lat/lon required, name/address optional
- `Leg` carries mode, origin, destination, times, distance, cost, reliability sigma, optional route name and operator
- `Itinerary` is a list of legs with computed totals and `arrival_by(confidence)` method
- `JourneyRequest` carries origin, destination, times, asset flags, max walking, and four preference weights
- `Mode` enum: WALK, BIKE_OWN, BIKE_SHARE, CAR_OWN, RIDESHARE, BUS, SUBWAY, TRAIN, TRAM, FLIGHT

### Scoring (in `polyroute/core/pareto.py`)
- Dominance: a dominates b iff ≤ on all axes AND < on at least one
- Min-max normalize each axis independently before applying weights
- Label extremes: Fastest, Cheapest, Most reliable, Least effort, Balanced

### Web UI (in `web/index.html`)
- Intentional editorial/transit-notebook aesthetic — not another SaaS dashboard
- Fonts: Fraunces (serif display + body) + JetBrains Mono
- Colors: warm paper base, TTC blue, UP Express red, GO green
- Single HTML file with vanilla JS. No build step. No React. Keeps contributor friction low.
- The aesthetic is a deliberate differentiator — don't let it drift toward generic shadcn/Tailwind-default look

### API (in `polyroute/api/server.py`)
- FastAPI, three endpoints: `/health`, `/presets`, `/plan`
- Pydantic v2 models, CORS open (tighten before any deployment)
- Returns both raw data and pre-rendered summary/explanation strings

### OTP2 setup
- `docker-compose.yml` uses official `opentripplanner/opentripplanner:latest`
- 6GB Java heap default, tunable
- `fetch-feeds.sh` pulls TTC, GO (includes UP Express), MiWay, Brampton, and Ontario OSM PBF
- Graph rebuild on container start (intentional — lets us pick up feed updates)

---

## 11. What to do in the first session (handoff checklist)

When Kirtiraj first runs Claude Code in the repo, do this in order:

1. Verify the scaffold:
   ```bash
   pip install -e ".[dev,api]"
   pytest
   python examples/toronto_airport.py
   ```
   All 9 tests must pass. Demo must print 4 ranked itineraries.

2. If not yet committed, make the initial commit:
   ```bash
   git add .
   git commit -m "feat: initial scaffold — core, Pareto, mock adapter, FastAPI, web UI, OTP2 Docker"
   git push -u origin main
   ```

3. Confirm the GitHub repo is public and the README renders correctly on github.com.

4. Read in full:
   - `README.md`
   - `docs/architecture.md`
   - `CONTRIBUTING.md`
   - This file (already reading)

5. Check in with Kirtiraj on which track to start:
   - **Track A — OTP2 adapter** (biggest technical dependency, unblocks real routing)
   - **Track B — LLM explainer** (fastest quality upgrade, plugs into existing pipeline)
   - **Track C — rideshare heuristic adapter** (smallest, finishes the MVP adapter set)
   - **Track D — interview recruiting posts** (non-code, highest strategic leverage)

   Default recommendation if he has no preference: **A + D in parallel.** OTP2 takes a few hours of setup wall-time where interviews can be recruited. LLM explainer and rideshare come after.

---

## 12. How to reference Claude products correctly (self-knowledge)

If Kirtiraj asks about Claude/Anthropic products:
- Do not rely on training data for pricing, rate limits, or model names. These change.
- Search official docs: `docs.claude.com`, `support.claude.com`, `docs.anthropic.com/en/docs/claude-code`
- For LLM integration in polyroute, prefer model-agnostic adapter pattern (Anthropic SDK + OpenAI SDK + Azure AI Foundry) rather than hard-coding one provider.
- Kirtiraj has Azure AI Foundry access through his TCS work — this is a natural fit for the LLM backend when he wants to demo it to colleagues.

---

## 13. Known risks and how to handle them

### Technical risks
- **GTFS feed URL drift.** Agencies rotate URLs. `fetch-feeds.sh` has fallback notes; when a feed 404s, check the agency open-data page and Open Canada mirrors (`open.canada.ca`).
- **OTP2 memory consumption.** Full GTA graph wants 6–8 GB. If host has less, drop Brampton/Oakville to shrink scope.
- **OTP2 Java upgrades.** Breaking changes do happen. Pin the image tag to a known-good version before any deployment.
- **Rideshare heuristic drift.** Published rates change. Document source and date; revalidate quarterly.

### Business risks
- **Google / Apple adding the feature.** If Google Maps ships true mixed-mode for YYZ tomorrow, the consumer wedge dies overnight. B2B2C thesis still holds. Don't panic-pivot.
- **OTP2 license.** LGPL 3.0 — fine for use, not fine for silent forking into a proprietary product. Read the license before any commercial derivative work.
- **Transit agency relationship management.** Agencies are slow and political. Budget 6–12 months from first conversation to first LOI.

### Capital / time risks
- Do not quit the TCS contract for this.
- Do not take VC money until an LOI is in hand. Non-dilutive Canadian capital (SR&ED + IRAP) is strictly better at this stage.
- If 90 days pass with zero validated demand, **pivot or park.** Do not grind on a dead thesis.

---

## 14. What NOT to do

- Do not build an iOS or Android app.
- Do not add real-time turn-by-turn navigation.
- Do not integrate live rideshare pricing via scraping.
- Do not add cities other than Toronto/GTA before v0.1.0 ships.
- Do not propose a paid consumer subscription.
- Do not use LangGraph for the single-query plan→rank→explain flow.
- Do not merge dependencies that aren't actually used ("just in case").
- Do not write README claims that aren't true yet.
- Do not commit API keys, `.env` files, or `graph-data/` (it's gitignored — keep it that way).
- Do not over-engineer the web UI. It's a demo artifact, not a product.

---

## 15. Success definition

By end of week 12:

- [ ] v0.1.0 published to PyPI with real OTP2, rideshare heuristic, GBFS adapters
- [ ] LLM explainer wired to Claude via Anthropic SDK (with Azure AI Foundry also working)
- [ ] 100+ GitHub stars (signals portfolio value)
- [ ] 20 user interviews completed (10 Pearson commuters, 10 newcomers)
- [ ] 1 signed LOI from GTAA, an employer, or a settlement agency — OR a clear documented decision to pivot
- [ ] SR&ED documentation current (commit log, design docs, test plans tagged appropriately)
- [ ] Project is referenceable on Kirtiraj's LinkedIn and resume as concrete evidence of agentic AI and systems-design capability

If all of those are hit, proceed to v0.2. If the LOI is missing, pivot the thesis honestly and update this file with the new direction.

---

## 16. When in doubt

1. Re-read section 3 (the research).
2. Re-read section 4 (non-negotiables).
3. If the question is a direction / scope / strategy question, ask Kirtiraj before acting. Don't silently decide big things.
4. If the question is implementation, decide, document the decision in this file or in `docs/`, and move on.

**End of handoff. Keep this file alive — update it as decisions are made, research emerges, and scope evolves.**
