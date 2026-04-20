# Letter of intent — template

**Purpose.** A signed LOI from one of GTAA, a Mississauga/Brampton employer,
or a settlement agency is the 90-day validation milestone in CLAUDE.md §8 /
§15. An LOI is **not** a contract — it's a written signal that a named
organization would pilot polyroute if it matched a concrete spec. Two pages
max. No commercial terms. No exclusivity. Non-binding.

Before sending, read: CLAUDE.md §4 (non-negotiables), §13 (business risks —
especially the "transit agency relationship management is slow and political"
note), and CLAUDE.md §2 on Kirtiraj's communication style (casual, direct,
accuracy over confidence).

---

## When to send

Send only **after** at least 5 Cohort A interviews are done. The LOI should
repeat language the operator has already used with you in conversation — if
you don't have that language yet, it's too early.

## Structure (1.5–2 pages)

1. **One-sentence framing.** Who you are, what polyroute is, one concrete
   example of the class of route the current tools miss on their corridor.
2. **Their problem, in their words.** Quote the interview line that made
   you think this organization in particular would care. One sentence.
3. **What a pilot would look like.** 8–12 weeks, specified scope, defined
   exit criterion. Bullet list, no more than five bullets.
4. **What you'd need from them.** Be honest. Typically: a named
   counterparty to answer questions, permission to mention their org in
   pitch materials, optional access to anonymized query logs.
5. **What you promise.** Open source on MIT. No scraping. No live
   rideshare pricing (CLAUDE.md §3.2). Working software before any paid
   conversation. A clear pull-the-plug clause.
6. **What happens next.** One paragraph. "If this is interesting, we both
   sign, and in October you're looking at a working pilot on <their
   corridor>. If not, nothing happens and we part friends."

## What NOT to include

- Payment terms, licensing terms, equity, or data-sharing terms past an
  NDA-free opt-in level. LOIs are not sales contracts.
- Promises about v0.2+ features — stick to what's in v0.1.0 today.
- Any language that makes this sound like a consumer subscription app
  (CLAUDE.md §4 #8).
- Links or attachments other than the GitHub repo and a one-page spec PDF.

---

## Variant 1 — GTAA (Greater Toronto Airports Authority)

Target: innovation team, not operations. GTAA publishes an innovation
portal intermittently — check toronto-pearson.com/en/corporate/innovation.

> **Subject:** Open-source mixed-mode planner for Pearson access — pilot proposal
>
> Hi <name>,
>
> I'm Kirtirajsinh Atodariya, a Toronto-based AI engineer. I've built
> polyroute — an MIT-licensed journey planner that mixes rideshare + TTC
> + GO + UP Express for Pearson access in ways consumer apps like Google
> Maps don't surface. (Demo, pre-alpha:
> https://github.com/KIRTIRAJ4327/polyroute).
>
> Talking to GTA commuters over the last month, the thing that keeps
> coming up is the 5 a.m. flight with no transit — a forced-Uber at $55
> when an $18 Uber-to-Kipling-then-UP would have worked. Polyroute is
> built around exactly that class of tradeoff.
>
> **What a pilot would look like**
>
> - 8 weeks, no cost to GTAA, hosted at polyroute.dev.
> - Co-branded demo page aimed at Pearson-bound travellers, linked from
>   one low-traffic GTAA channel of your choice.
> - We instrument query patterns (with user consent, no PII) and share
>   aggregate findings back.
> - Exit criterion: if the link generates <50 queries/week or the
>   tradeoff explanations don't match GTAA's tone, we pull it.
>
> **What I'd ask from you**
>
> - A named counterparty on the innovation team I can check in with
>   every two weeks.
> - Permission to list "piloting with GTAA" on the project landing
>   page during the 8 weeks.
> - Non-binding letter of intent (attached) — not a contract.
>
> **What I commit to**
>
> - Open source, MIT. No scraping of Uber/Lyft, no live rideshare
>   pricing (API ToU constraints documented in the repo).
> - Working software before any commercial conversation.
> - Pull-the-plug clause: either side can end the pilot in 30 days
>   with no obligations.
>
> If this is interesting I'd love 20 minutes next week.
>
> Thanks,
> Kirtirajsinh Atodariya
> <email> | <phone>

## Variant 2 — large GTA employer (Magna, Amazon YHM1, Maple Leaf Foods)

Target: benefits / HR / sustainability, **not** facilities. The question
for them is employee commute stress on airport-like corridors (think
Brampton DC staff flying back to their home country).

> **Subject:** Commute tool for <Employer> staff — 15-minute chat?
>
> Hi <name>,
>
> I'm Kirtirajsinh Atodariya, a Toronto AI engineer. I've built an
> open-source journey planner (polyroute) that mixes Uber + TTC + GO +
> UP Express for trips to Pearson. Most consumer apps silo these modes
> and the mixed-mode plans are where the real savings live.
>
> Talking to GTA commuters the last month, the group that keeps coming
> up is international-origin staff who fly home 2–3× a year and
> repeatedly over-spend on rideshare because mid-trip transit
> transitions aren't obvious from any app.
>
> **What a pilot would look like**
>
> - 10 weeks, free, hosted by polyroute.
> - Co-branded URL we share via your internal benefits channel
>   (Slack / intranet). Staff opt in — no default enrollment.
> - Monthly readout: query volume, mode mix, estimated dollars saved.
> - Exit criterion: <20 weekly active staff queries after 4 weeks.
>
> <...same "what I'd ask from you" / "what I commit to" blocks as
> Variant 1...>
>
> Happy to do 15 minutes next week if useful.
>
> Thanks,
> Kirtirajsinh Atodariya

## Variant 3 — settlement agency (WoodGreen, COSTI, ACCES)

Target: program director for newcomer employment / settlement programs.
The question here is the PRESTO/GO/UP/TTC fare-integration confusion
that shows up in the first 6 months after arrival (CLAUDE.md §3.6 #2).

> **Subject:** Free transit-explainer tool for your newcomer clients
>
> Hi <name>,
>
> I'm Kirtirajsinh Atodariya — Humber PG cert 2024, now an AI engineer
> in Toronto. I've been building polyroute, an open-source journey
> planner that explains Toronto transit in plain language (how PRESTO,
> GO, UP, and TTC fit together without overpaying). MIT-licensed, free
> for non-commercial use forever.
>
> The newcomer angle came out of two conversations with <Humber
> International Centre / settlement agency person> this month — the
> thing clients struggle with isn't *taking* transit, it's *picking
> between* PRESTO combinations that cost meaningfully different
> amounts.
>
> **What a pilot would look like**
>
> - 8 weeks, free.
> - Co-branded landing page in English + <Hindi / Mandarin / Tagalog
>   / Spanish — your call>.
> - Feedback form after every query; we review weekly with your
>   intake coordinators.
> - Exit criterion: if intake staff don't find themselves referring
>   clients to it after 4 weeks, we end it.
>
> <...same "what I'd ask" / "what I commit to" blocks...>
>
> I'd love to drop by the office or do a video call — whatever works
> for you.
>
> Thanks,
> Kirtirajsinh Atodariya

---

## Signature block (included in the attached PDF, not the email)

```
____________________________________
<name, title>
<organization>
Date: ____________

____________________________________
Kirtirajsinh Atodariya
polyroute
Date: ____________
```

---

## Follow-up cadence

- Day 0: email.
- Day 7: short nudge ("checking this isn't buried — happy to revise").
- Day 21: final nudge, then move on for 90 days.
- If they say yes but can't sign immediately: ask for a single email
  reply ("yes, we'd pilot if <specific condition> is met"). That's a
  soft LOI — keep a copy. Don't chase a signed PDF if a clear email
  statement exists.
