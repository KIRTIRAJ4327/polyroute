# Contributing

Polyroute is pre-alpha. If you're reading this, you're probably considering whether it's worth your time — here's the honest answer.

## What's the project

An OSS reasoning layer for multi-modal journey planning. The consumer market for this has been thoroughly proven uninvestable (Citymapper, Whim, Trafi consumer), so the long-term play is selling the reasoning layer to transit agencies, airports, employers, and cities. The code stays open; the hosted product (if any) sits on top.

Scope for v0.1: Toronto / GTA, airport-access wedge, Python library + FastAPI server + minimal web UI.

## What would help most

In priority order:

1. **Real-world usage reports.** If you commute in the GTA — especially to/from Pearson — open an issue describing a trip you make regularly, what your current routing tool gives you, and what it misses. This is worth more than code right now.

2. **Adapter implementations.** OTP2 and OSRM are the two highest-leverage ones. The interfaces in `polyroute/adapters/` are small.

3. **Edge cases in scoring.** The Pareto + weighted-sum approach is deliberately simple. If you find a query where the ranking feels wrong, that's a bug report worth filing even without a proposed fix.

4. **Other cities.** The design is city-agnostic but the data plumbing is Toronto-specific. A parallel Docker setup for another city (Montreal, Vancouver, NYC) would be a meaningful contribution.

## What's *not* wanted yet

- Native mobile apps. Web-first until we have PMF signal.
- Rewrites into other languages or frameworks.
- Premature abstractions. Concrete first, generic later.
- LLM chatbot wrappers. The LLM role here is narrow and specific (tradeoff explanation), not conversational.

## Development setup

```bash
git clone https://github.com/KIRTIRAJ4327/polyroute
cd polyroute
pip install -e ".[dev,api]"
pytest
python examples/toronto_airport.py
uvicorn polyroute.api.server:app --reload
```

## Code style

- `ruff` for linting and formatting (`ruff check .` and `ruff format .`)
- Type hints on public APIs
- Tests required for new logic in `core/` — the math has to be right

## Filing issues

Describe:
1. The query (origin, destination, time, constraints)
2. What polyroute returned
3. What you expected — and ideally why
4. What existing tools return for comparison (Google Maps, Transit app, Citymapper)

## Recordkeeping (SR&ED)

Engineering logs live in `docs/sred/` (see `docs/sred/README.md`).
Every meaningful technical decision — especially resolutions to
technological uncertainty — should leave a trace in the monthly entry.
Commit messages and issue descriptions are the primary evidence; the
SR&ED logs just aggregate them into a reviewer-ready narrative.

## Questions

LinkedIn DM or GitHub issue both work. I'll try to respond within a few days.
