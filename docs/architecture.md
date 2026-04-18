# Architecture

## The shape of the problem

Given a journey request `(origin, destination, time, constraints, preferences)`, return a small set of ranked itineraries with natural-language tradeoff explanations. Three realities constrain the design:

1. **No single data source answers the full question.** Transit routers don't know rideshare prices. Rideshare APIs don't care about transit connections. Bike share is in a third silo. The system's job is orchestration.

2. **There is no single "best" route.** Time, cost, effort, and reliability are not commensurable. The correct answer is a *set* of Pareto-optimal options, ranked by user-stated preferences.

3. **The differentiator is explanation, not routing.** OTP2 and RAPTOR are commoditized. The part worth building is the layer that says *"this saves you $18 but adds a tight transfer at Kipling"* in words a human cares about.

## The four-layer design

```
  JourneyRequest
       │
       ▼
  ┌────────────┐
  │ Adapters   │  ← many sources, parallel fan-out
  └─────┬──────┘
        │ Itineraries (candidates)
        ▼
  ┌────────────┐
  │ Core       │  ← Pareto filter, feasibility, dominance
  └─────┬──────┘
        │ Non-dominated set
        ▼
  ┌────────────┐
  │ Scoring    │  ← weighted sum over normalized axes
  └─────┬──────┘
        │ ScoredItinerary[] (ranked)
        ▼
  ┌────────────┐
  │ Explainer  │  ← rule-based now, LLM later
  └─────┬──────┘
        │
        ▼
     Response
```

### Layer 1: adapters

Adapters are pluggable. Each knows how to talk to one data source (OTP2, OSRM, GBFS, a rideshare heuristic) and return `Leg` or `Itinerary` objects.

Critical design choice: adapters do not know about each other, do not score, and do not explain. They only generate candidates. This keeps each one testable in isolation and replaceable.

### Layer 2: core (Pareto + feasibility)

Pure domain logic. No I/O, no LLM, no framework coupling. Tests here are pure math.

Feasibility is a hard gate applied before scoring: luggage disqualifies bikes, `arrive_by` disqualifies options that miss the deadline at 90% confidence, absent assets disqualify modes that require them.

Pareto filtering drops dominated options — an itinerary that is worse on every axis than another. This is done on the full 4D vector `(time, cost, effort, reliability)`, which typically collapses 10–20 raw candidates to 3–7 interesting ones.

### Layer 3: scoring

For each non-dominated candidate, compute a weighted sum of normalized axes using user-stated preferences. Min-max normalization per axis ensures weights mean something comparable.

Label extremes (Fastest, Cheapest, Most reliable, Least effort). This matters for UX — users want to understand what each option optimizes for, not just a ranked list.

### Layer 4: explainer

Takes a `ScoredItinerary` plus the other options on the frontier and generates a two-to-three-sentence tradeoff explanation.

Today: rule-based comparisons against alternatives. Tomorrow: a model-agnostic LLM layer (Anthropic, OpenAI, Azure AI Foundry) that produces richer, more contextual narrative. The interface is the same either way: `explain(scored, others) -> str`.

## Why not a chatbot

Natural-language is the *input* to most LLM tools and the *output* of ours. The hard work — multi-modal candidate generation, Pareto filtering, preference-weighted scoring — is deterministic and should stay that way. An LLM is the wrong tool to pick between a $16 bus and a $52 Uber; it's the right tool to explain why one is better for this user.

The agentic / LangGraph wrapper (coming in v0.2) is useful not for the core planning loop but for higher-level flows: *"plan my week of commutes and adjust if weather changes"*, *"replan this trip now that my 7:15 train is delayed"*. Those are stateful, cyclical, and worth a real graph. The single-query path is not.

## What this is not

- Not a routing engine. OTP2 and OSRM exist and are excellent. Polyroute orchestrates them.
- Not a fare engine. Rideshare fares are estimates; published transit fares are authoritative. The system tells users which is which.
- Not a real-time navigation app. v1 is trip planning at departure. Mid-journey replanning is v2.

## Forward compatibility

The adapter protocols and core types are designed so that swapping the mock Toronto adapter for real OTP2 + GBFS + a rideshare heuristic does not change any downstream code. The scoring and explainer layers don't know which adapter produced a candidate, and shouldn't.
