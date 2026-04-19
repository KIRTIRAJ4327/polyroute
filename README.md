# polyroute

[![CI](https://github.com/KIRTIRAJ4327/polyroute/actions/workflows/ci.yml/badge.svg)](https://github.com/KIRTIRAJ4327/polyroute/actions/workflows/ci.yml)

**Agentic multi-modal journey planning that actually mixes modes.**

Most routing apps silo transit, driving, rideshare, and bikes into separate answers. Polyroute finds the interesting combinations they miss — the Uber-to-transit-station hops, the park-and-ride options, the bike-to-GO-station routes — and explains the tradeoffs in plain language.

```
  Fountainhead Rd, Mississauga  →  Toronto Pearson Terminal 1
  Depart: 06:00

  1. Balanced: Uber/Lyft → bus (GO 34) — 48 min, $18.35
     Plan for up to 11 min of delay — transit or surge variance is notable here.

  2. Most reliable: Uber/Lyft → subway → UP Express — 1h 17m, $31.70
     Saves 11 min vs the cheapest option, at $14.95 extra. 2 transfers.

  3. Fastest: Uber/Lyft — 28 min, $52.00
     Saves 1h vs the cheapest option, at $35.25 extra.

  4. Cheapest: MiWay 26 → subway → UP Express — 1h 28m, $16.75
     2 transfers — tight connections if anything runs late.
```

## Why this exists

Ask Google Maps how to get from a Mississauga suburb to Pearson at 6am and you'll get three siloed answers: all-transit, all-drive, all-Uber. What you actually want is the mix — a $16 Uber to a subway station plus a $3.35 fare the rest of the way — but no consumer app will show it to you.

The [research](./docs/research.md) behind this project found that every consumer multi-modal app has failed the same way (Citymapper, Whim, Trafi consumer). The technical substrate is commoditized open-source, rideshare APIs block honest price comparison, and the viable path is B2B2C: sell the reasoning layer to transit agencies, airports, and employers. Polyroute is built with that exit in mind.

## Architecture

```
 ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
 │ JourneyReq   │ ──▶ │ Candidate gen    │ ──▶ │ Pareto       │
 │ (A→B, prefs) │     │ (adapters)       │     │ filter       │
 └──────────────┘     └──────────────────┘     └──────┬───────┘
                                                       │
                              ┌────────────────────────┤
                              ▼                        ▼
                      ┌──────────────┐         ┌──────────────┐
                      │ Preference   │         │ LLM          │
                      │ scoring      │         │ explainer    │
                      └──────────────┘         └──────────────┘
```

Four clean layers:

1. **Adapters** — pluggable sources (OTP2 for transit, OSRM for routing, rideshare heuristic, GBFS for bike share). Each returns `Itinerary` objects.
2. **Core** — pure domain types and the Pareto filter. No I/O, no LLM.
3. **Scoring** — weighted combination of time, cost, effort, reliability across the non-dominated set.
4. **Explainer** — rule-based today, model-agnostic LLM (Claude / GPT / Gemini / Azure AI Foundry) tomorrow.

## Quickstart

```bash
git clone https://github.com/KIRTIRAJ4327/polyroute
cd polyroute
pip install -e ".[dev,api]"
pytest                          # 80 unit tests, 5 integration tests skip without OTP2/GBFS
python examples/toronto_airport.py
```

That demo uses hand-tuned mock data for the Fountainhead → Pearson corridor.

### Run the server

```bash
uvicorn polyroute.api.server:app --reload
# → http://127.0.0.1:8000/   (web UI)
# → http://127.0.0.1:8000/plan   (POST JSON)
```

With zero config, the planner wires up the rideshare heuristic and the mock Toronto fallback. Flip on real data per-adapter:

```bash
export POLYROUTE_OTP2_URL=http://localhost:8080   # see docker/otp2-toronto/
export POLYROUTE_GBFS_URL=https://tor.publicbikesystem.net/ube/gbfs/v1/
export POLYROUTE_DISABLE_FALLBACK=1               # production: don't mix mock data
```

### Opt in to the LLM explainer

```bash
pip install -e ".[llm]"
export POLYROUTE_LLM_PROVIDER=anthropic           # or openai, azure
export ANTHROPIC_API_KEY=sk-ant-...
```

The server falls back to the rule-based explainer if the provider call fails, and the API surfaces `explanation_source` (`"llm"` | `"rule-based-fallback"` | `"rule-based"`) per itinerary.

### Run OTP2 locally (real transit)

```bash
cd docker/otp2-toronto
./fetch-feeds.sh      # downloads GTFS + OSM (~400 MB)
docker compose up     # first build takes 3–8 min
```

Then point the OTP2 adapter at `http://localhost:8080`.

## Roadmap

- [x] Core types, Pareto filter, rule-based explainer
- [x] Mock Toronto airport demo
- [x] OTP2 Docker setup for GTA
- [x] FastAPI server + minimal web UI
- [x] OTP2 adapter scaffold + fixture-based unit tests (#2, #7)
- [x] Rideshare heuristic adapter (published per-km + surge model) (#3)
- [x] GBFS adapter (Bike Share Toronto) (#4)
- [x] Composition strategy module — mixed-mode candidates at transit anchors (#5)
- [x] Planner orchestrator + API wiring (fan-out, graceful degradation, env-driven)
- [x] LLM-backed explainer (Claude via Anthropic / OpenAI / Azure AI Foundry) (#6)
- [ ] OTP2 adapter integration-tested against a live container (#2)
- [ ] LangGraph agent for multi-step reasoning (v0.2)
- [ ] v0.1.0 on PyPI

## Scope

**In scope:** Toronto/GTA, airport-access wedge, web-first, library-style extensibility.

**Out of scope for v1:** native mobile apps, real-time mid-journey re-routing, global coverage, real rideshare API integration (documented as bring-your-own).

## Status

Pre-alpha. Built as an OSS reasoning layer that can later be sold to transit agencies, airports, or employers — not as a consumer app. The consumer MaaS market is a well-documented graveyard; this project exists to explore whether an agentic reasoning layer changes the economics.

## License

MIT. See [LICENSE](./LICENSE).

## Contact

Built by [Kirtirajsinh Atodariya](https://www.linkedin.com/in/kirtirajsinh-atodariya/). If you're a Toronto commuter, a transit agency, or a corporate travel lead who'd like to try it or share pain points, open an issue or DM on LinkedIn.
