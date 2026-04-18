# FIRST_SESSION.md — Kickoff instructions for Claude Code

**This is a one-time document. Read it, execute it, then rely on `CLAUDE.md` for all future sessions.**

---

## Context

I'm Kirtiraj. I started this project (`polyroute`) in a claude.ai conversation with Claude Opus 4.7. We did deep research on the market, made strategic decisions, built the initial scaffold, and generated a complete handoff document (`CLAUDE.md`). I'm now moving the work into Claude Code so we can iterate on the repo directly.

You are picking up where that conversation left off. `CLAUDE.md` in the repo root has everything: the research, the strategy, the architecture, the roadmap, the non-negotiables, and my personal context. **Read it in full before doing anything else.**

---

## Immediate tasks (in order)

### 1. Orient yourself

Read, in full, without skimming:

- `CLAUDE.md` (working memory — the single most important file)
- `README.md`
- `docs/architecture.md`
- `CONTRIBUTING.md`

Confirm you've read them by summarizing back to me, in 3–4 sentences each:
- The strategic thesis (why B2B2C, not B2C)
- The four-layer architecture
- The three wedges and why airport-access is first
- The 90-day validation plan

If any of those summaries would be guesses, re-read until they're not.

### 2. Verify the scaffold works locally

Run:

```bash
pip install -e ".[dev,api]"
pytest
python examples/toronto_airport.py
python examples/toronto_airport.py --cheap --luggage
python examples/toronto_airport.py --fast
```

Expected:
- 9/9 tests pass
- Default demo prints 5 candidates → 4 on Pareto frontier with labels
- `--cheap` promotes transit-heavy options
- `--fast` promotes Uber to rank 1
- `--luggage` excludes any bike-share itineraries (there are none in the mock currently, so output should be identical to default)

Then start the server and confirm the web UI:

```bash
uvicorn polyroute.api.server:app --reload
```

Open http://localhost:8000 in a browser. Fill in the form, hit "Find routes", confirm ranked results render with the editorial aesthetic (warm paper background, Fraunces serif, TTC-blue/UP-red/GO-green leg chips).

Stop if anything fails. Report the failure to me. Do not paper over problems.

### 3. Verify the GitHub repo state

```bash
git status
git log --oneline
git remote -v
```

If there are uncommitted files or the initial commit hasn't been pushed:

```bash
git add .
git commit -m "feat: initial scaffold — core types, Pareto scoring, mock Toronto adapter, FastAPI server, web UI, OTP2 Docker setup

- 9 passing unit tests on core math
- End-to-end working demo for Fountainhead Rd → YYZ
- Editorial-style web UI (Fraunces + JetBrains Mono)
- OTP2 Docker compose + feed fetch script for GTA
- MIT license, CONTRIBUTING.md, architecture doc"
git push -u origin main
```

Confirm the repo is public at https://github.com/KIRTIRAJ4327/polyroute and the README renders correctly.

### 4. Set up the GitHub repo properly

Do these via `gh` CLI if available, otherwise give me the manual steps:

- Add topics to the repo: `agentic-ai`, `langgraph`, `multimodal-transport`, `routing`, `opentripplanner`, `mobility`, `toronto`, `gtfs`, `pareto-optimization`
- Enable Issues
- Enable Discussions (useful for contributor questions later)
- Set the description to the one-liner from `README.md`
- Set the website field to a placeholder (my LinkedIn for now is fine, since there's no hosted demo yet)

### 5. Create a v0.1.0 milestone and scaffold issues

Create these GitHub issues (or give me the commands to do it). Group them under a `v0.1.0` milestone:

1. **[feat] Real OTP2 adapter** — replace `mock_toronto.py` for transit/walk/bike legs
2. **[feat] Rideshare heuristic adapter** — published per-km + time-of-day surge, clearly labeled estimate
3. **[feat] GBFS adapter for Bike Share Toronto** — station availability and routing
4. **[feat] Composition strategy module** — first-mile/last-mile mixing around transit anchors (Kipling, Islington, Bloor, Dundas West, Union, major GO stations)
5. **[feat] LLM explainer via Anthropic SDK** — model-agnostic adapter, Claude primary, OpenAI and Azure AI Foundry also supported
6. **[feat] Integration tests for OTP2 adapter** — marked `@pytest.mark.integration`, skippable without container
7. **[chore] SR&ED documentation scaffold** — `docs/sred/` with a template for monthly summaries
8. **[docs] "Writing a new adapter" guide** — for future contributors adding cities or modes
9. **[chore] CI workflow** — GitHub Actions running pytest on push and PR

### 6. Check in with me on which track to start

Before writing any production code, ask me: "Which track first? A (OTP2 adapter), B (LLM explainer), C (rideshare heuristic), or D (interview recruiting posts)?"

If I don't answer, default to **A + D in parallel** — OTP2 build-time overlaps nicely with interview recruiting.

---

## Standing rules (distilled from CLAUDE.md)

- **Accuracy over confidence.** If you're unsure about an API, library behavior, price, or piece of Toronto transit information, search the web. Do not guess.
- **Casual and direct.** No corporate prose. No excessive apologies. Push back if you think I'm wrong.
- **6–10 hours of my time per week.** Don't propose plans that assume more.
- **Commit hygiene = SR&ED evidence.** Good commit messages are not optional — they're part of the R&D tax credit documentation.
- **Do not relitigate the non-negotiables** in `CLAUDE.md` § 4 without asking me first.
- **Do not build anything** that isn't on the v0.1.0 milestone without checking with me.

---

## How to talk to me

- I'm technical. Don't over-explain basics.
- I prefer short responses when you're asking a question. Verbose is fine when you're explaining a design decision.
- If you recommend something, tell me the trade-off, not just the recommendation.
- I'll push back on things. That's a feature, not a bug. Hold your position if you have a reason.

---

## Once this is done

Delete `FIRST_SESSION.md` (or archive it to `docs/archive/`). From then on, `CLAUDE.md` is the living memory. Update `CLAUDE.md` whenever we make a meaningful decision.

Let's get to work.
