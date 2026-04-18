# Research: Viability of agentic multi-modal journey planning in Toronto

**Produced:** April 2026
**Purpose:** Evidence base for strategic decisions. Re-read before major direction changes.

---

## TL;DR

The consumer-facing multi-modal journey planning market is a graveyard, and nothing about generative AI changes the underlying unit economics — but a narrow B2B2C wedge in the GTA remains defensible for a solo senior Gen AI developer. Citymapper was effectively sold in a 2023 washout after burning ~$60M, MaaS Global (Whim) burned €75.5M before declaring bankruptcy in March 2024, and Trafi — the quiet technical winner behind Jelbi Berlin — exited to Canadian enterprise-software consolidator Enghouse Systems in April 2025 for undisclosed (almost certainly modest) terms. The only sustained value creation in this space sits in B2B tooling sold to transit agencies (Optibus: $1.3B valuation, ~$60M ARR, 450 customers) and in agency-owned MaaS projects where a city authority, not a startup, absorbs customer-acquisition cost. A Toronto-based solo founder should therefore treat a consumer app as a wedge, not a destination, anchor the first year on a specific high-pain corridor (Pearson airport access and newcomer wayfinding are the two most defensible), and plan to sell the underlying reasoning layer to agencies or enterprises within 18–24 months.

---

## 1. Why every consumer multi-modal app has failed the same way

The pattern across twelve years and billions of dollars is almost monotonous.

**Citymapper** raised roughly $52M in venture plus an $8M crowdfund, was covering 108 cities by 2023, and still lost £7.4M on £5.1M of revenue in 2021 before Via bought it in what TechCrunch sources described as a "washout" where most investors did not make their money back. The paid Club tier at $2.99/month was launched in late 2022 and lasted six months before the acquisition; Via then halved the price to $1.49/month and moved most features free, a clear admission that consumer willingness to pay is well below what the cost of building and maintaining multi-city transit data requires.

**MaaS Global** compounded the same flaw with a more ambitious and expensive bet. Whim raised €149M from Toyota, Mitsubishi, and BP Ventures, peaked at ~10,000 monthly active users in Helsinki, burned €75.5M in seven years, and went bankrupt in March 2024 with €9.3M of losses on €3.8M of revenue. The verdict from the industry is uniform: the subscription bundle forced users to pre-pay for transport they may not use, and flexibility — pay per trip, per mode — turned out to be what riders actually want. Sampo Hietanen, the "father of MaaS," conceded they tried to go "from zero to one in one step" in a market "more fragmented and slower than an agile start-up."

The survivors — **Jelbi in Berlin** (800,000 downloads, 360,000 users, 65,000 vehicles across ~200 hubs), Floya in Brussels, Breeze in the Solent — are all city-owned, agency-funded deployments powered by Trafi as a white-label vendor. The economics only close when a public authority, not a startup, subsidizes acquisition.

The one unambiguous consumer-app success is **Transit (Montreal)**, which has survived twelve years, reached 900+ cities, and generates an estimated $5–25M in annual revenue on just $27M of total capital raised. Its defensible moat is not product features but official partnership status with dozens of transit agencies — the app is the "endorsed" wayfinding tool for TTC, SF Muni, Philadelphia SEPTA and others, which effectively externalizes customer acquisition to the agencies themselves. This is the template a new entrant must study carefully; it is a B2B2C business dressed as a B2C app.

---

## 2. The Uber API is the silent killer of honest multi-modal UX

Here is the finding that reframes the entire product thesis.

**Uber's Price Estimates API terms of service explicitly state** that using the Uber API to offer price comparisons with competitive third party services is in violation of § II B of the API Terms of Use. This is why Citymapper, Transit, Google Maps and Apple Maps show Uber only through deep links with *estimated* fares pulled from cached public data — not live API pricing.

**Lyft closed its generic public Developer Platform in 2021** and now gates API access behind Lyft Business account approvals keyed to specific corporate programs; the "public API" exists only in legacy SDK repos.

**Bolt, Didi, Ola and Grab** all have similarly restricted partner-only access.

The practical implication for a Toronto builder is severe: a consumer app that promises honest side-by-side comparison of TTC + UP Express + Uber + bike share cannot legally show live Uber pricing, and can only show live Lyft pricing inside a B2B "Concierge" relationship. Workarounds include deep-linking with approximate fare ranges, relying on users to copy pricing back, or partnering with an aggregator such as Splyt — but none replicate the unified UX the product thesis requires. This constraint alone explains why rideshare has never been meaningfully integrated in any surviving consumer multi-modal app, and why agency-led MaaS in Europe (where ride-hailing penetration is far lower) has made more progress than anything in North America.

---

## 3. The technical stack is mostly solved, and mostly boring

For a solo Gen AI developer, the good news is that the routing substrate is commoditized open-source.

**OpenTripPlanner 2 (OTP2)**, now based on the RAPTOR algorithm published by Delling, Pajor and Werneck in 2012, is in production at Entur Norway, HSL Finland, TriMet Portland, and dozens of other agencies. RAPTOR is round-based rather than Dijkstra-based, computes Pareto-optimal journeys across arrival time and transfers (and via McRAPTOR across additional criteria like fare zones) in tens to hundreds of milliseconds, requires no preprocessing, and handles dynamic real-time updates. OTP2 natively integrates GTFS static, GTFS-Realtime, GBFS bike share (Bike Share Toronto publishes a compliant feed), park-and-ride, and GTFS-Flex demand-responsive transit — so "Uber to a GO station, train downtown, Bike Share Toronto to destination" is computable in a single query, provided you cheat the ride-hail leg with a straight-line time estimate. A Toronto instance covering TTC, GO, UP Express, MiWay, Brampton, York Region, Durham and Oakville likely needs 8–16 GB of RAM and a modest VM; Hetzner or Fly.io at $20–80/month is sufficient for the first 10,000 users.

**Agentic orchestration is where solo founders most often over-engineer.** LangGraph is genuinely valuable for long-running, stateful, resumable workflows with human-in-the-loop checkpoints — think multi-day travel planning with approvals. For the core journey-planning loop (parse natural-language intent → call 2–4 mode-specific tools in parallel → rerank with user-preference weights → explain tradeoffs), a single LLM call with structured tool-use through the OpenAI/Anthropic SDK, or Azure AI Foundry's agent service, is almost certainly enough and will ship in a third of the time. The honest answer multiple practitioner write-ups converge on: LangGraph is "overkill for a simple Q&A bot" and valuable only when you need durable execution, cyclical retries, or multi-agent supervisor patterns. Reserve it for a v2 feature like "plan my week of commutes and adjust for weather/transit disruptions," not for the initial path-ranking flow. For the natural-language explanation layer, Gemini 2.5 Flash, Claude Haiku 4.5 and GPT-4o-mini all cluster around $0.10–$0.40 per million input tokens and <2s latency — well inside budget for a free-tier product with a few hundred monthly users.

---

## 4. Funding reality: mobility has cooled, and solo B2C mobility is nearly uninvestable

Global mobility funding rebounded to $54B in 2024 (Oliver Wyman Mobility Investment Radar) and Q2 2025 hit $21.4B — but those headlines are misleading. Strip out autonomy and EV-infrastructure mega-rounds (Scale AI's $14.8B, Waymo, BETA Technologies, Didi Autonomous) and the picture is bleak: Streetlife Ventures / MIT analysis shows mobility deal values are down 64% from the 2021 peak, exits are down 85–90%, and the gap between rounds has widened 40–50%. Early-stage (seed / Series A) consumer mobility SaaS is the coldest corner of the market.

**Active mobility VCs** — Maniv Mobility, Trucks VC, Fontinalis, MobilityFund and Mobilitech Capital — are all still active, but their 2024–2025 cheques have concentrated on B2B software, fleet electrification, and logistics AI. They have explicitly learned to avoid consumer journey planners after Citymapper and MaaS Global.

**The Canadian non-dilutive stack** is, by global standards, exceptional and probably more important than equity for this project's first eighteen months:

- **SR&ED** provides a 35% refundable investment tax credit for CCPCs on the first $4M of eligible R&D (raised from $3M in Budget 2025), giving a solo technical founder a $1.4M ceiling on refundable credits. Ontario Innovation Tax Credit stacks another 8%, pushing effective recovery to ~43% on qualifying engineering time.
- **IRAP** averages ~$500K per contribution, funds ~3,100 firms annually, covers up to 80% of eligible R&D labour, and can stack with SR&ED (IRAP reduces the SR&ED base dollar-for-dollar). Realistically, a disciplined solo founder spending 60% of time on SR&ED-eligible experimentation can recover $30–60K in year one without an IRAP contribution and materially more if an Industrial Technology Advisor sponsors a project.
- **Accelerators** — CDL-Toronto (Cities stream is dormant but AI and mobility-adjacent streams remain active), NextAI ($100–250K for 6–8% equity, AI focus), MaRS and DMZ all take zero or minimal equity, providing access to mentors and corporate partners without the dilution of YC or Techstars.

---

## 5. Where a Toronto solo founder can actually win

The three corridors worth testing are airport access, newcomer wayfinding, and corporate commute tools — in that order of defensibility.

**Pearson access is the sharpest wedge.** Toronto Pearson is Canada's busiest airport and GTA residents outside the downtown core have genuinely poor options: UP Express charges $12.35 one-way and serves only Union Station (4.5M annual passengers in 2019, lighter commuter use since); TTC 900 Airport Express and 52 Lawrence West connect the subway but require transfers; GO Transit bus 34 runs to Finch; MiWay and Brampton Transit buses serve immediate suburbs; ride-hail runs $45–90 depending on origin and time. Existing apps (Google Maps, Transit app, Citymapper) handle this poorly because they optimize for transit-only or all-modes without weighting cost against reliability for a hard flight deadline. A tool that takes a flight time, factors live GTFS-Realtime delays, weather, and a learned reliability buffer, and then recommends the cheapest option that hits a chosen confidence threshold is demonstrably useful and has a clear willingness-to-pay signal (missed flights cost hundreds of dollars). It also maps directly to a GTAA partnership pitch within 12 months.

**Newcomer wayfinding is the largest underserved segment in the region.** Ontario hosts roughly 200,000 international students plus steady permanent-resident inflows. PRESTO, GO, UP and TTC fare integration is improving but remains confusing to new arrivals; no existing app explains tradeoffs in plain language ("this route is $2 cheaper but requires a 12-minute walk through a quiet area at 11pm"). This is where LLM-generated natural-language tradeoff explanations create genuine non-commodity value on top of OTP2. Monetization is through university and settlement-agency partnerships rather than consumer subscriptions.

**Corporate commute tools** (Commutifi, RideAmigos, Luum as benchmarks) are the most boring and most fundable long-term path — ACVs of $15–60K per 1,000 employees, HR or sustainability as buyer, 6–12 month sales cycles. This is the pivot destination, not the starting point.

---

## 6. Ninety-day validation plan and honest scope for a solo founder

A realistic MVP for one senior engineer working evenings and weekends is **Toronto-only, web-first** (PWA, not native), transit + walking + cycling + driving computed natively via OTP2, rideshare integrated only via deep links with cached public fare ranges, and an LLM layer that ranks results against a user-selected preference ("cheapest," "most reliable," "least walking," "lowest carbon") and produces a two-sentence plain-language explanation of the tradeoff.

Avoid native iOS/Android until post-PMF; React Native or Expo for v2. Avoid a subscription in v1 — the whole market tells you it will not work at this scale. The viable monetization ladder is:

1. Free for users
2. Embedded affiliate links (Omio, GetYourGuide, Uber deep-link referral)
3. Anonymized OD-pair data licensed to GTAA or Metrolinx
4. Enterprise commute dashboard sold to large Mississauga/Brampton employers
5. White-label agency product (the Trafi-to-Enghouse path)

**The first ninety days should look like this:**

- **Weeks 1–2**: interview 20 Pearson commuters and 20 recent newcomers for concrete pain points and price sensitivity
- **Weeks 3–4**: stand up an OTP2 instance for the GTA and a bare-bones web frontend
- **Weeks 5–8**: layer the LLM ranking and explanation; run a wizard-of-Oz test with 50 users from the interview pool
- **Weeks 9–12**: file SR&ED documentation from day one; request an IRAP ITA meeting; secure one letter of intent from either GTAA, a Mississauga employer, or a settlement agency

If no LOI is achievable in ninety days, the thesis is likely wrong and the right move is to pivot the underlying tech into a B2B developer-tools API (the Rome2Rio / Skedgo path) rather than push harder on B2C.

---

## 7. The takeaway

**A solo senior Gen AI developer in Toronto should build this if — and only if — the goal is an 18-month option on a B2B2C exit, not a consumer company.** The consumer market has been proven uninvestable and economically impossible four times over, the rideshare APIs make honest comparison UX legally impossible, and the surviving value in journey planning sits squarely in tools sold to transit agencies, airports and employers.

The right bet is to use the Gen AI advantage (natural-language tradeoff explanations, learned reliability buffers, agentic replanning on disruption) to build a genuinely differentiated reasoning layer on top of commoditized OTP2 routing, prove it on a sharp Toronto wedge where no incumbent is trying hard, fund the first eighteen months almost entirely from SR&ED and IRAP rather than equity, and plan the exit path to either a Canadian enterprise consolidator (the Enghouse/Trafi template), a transit-tech platform (the Optibus or Via/Citymapper template), or a single large corporate or airport authority contract.

Everything else in this space has failed, and the reasons are structural rather than executional.
