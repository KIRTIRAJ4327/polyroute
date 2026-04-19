# SR&ED recordkeeping

**This is organizational scaffolding, not legal advice.** Before filing
anything, engage a SR&ED consultant. The goal of this folder is to make
the engineering log *reviewer-ready* — so that whoever helps with the
T661 has a month-by-month narrative to work from.

Why it matters: CLAUDE.md §3.5 sizes the refundable credit at ~43% of
qualifying engineering time when SR&ED + OITC stack. That's material.
The credit is only as good as the evidence.

## What counts

Eligible:

- **Technological uncertainty** that required systematic investigation to
  resolve — e.g., "can OTP2's GraphQL schema express Pareto-over-four-axes
  without a second RAPTOR pass?"
- **Systematic investigation or experimentation** — hypothesis, method,
  result (even null results).
- **Technological advancement** — something you learned, even if it only
  moved you from "not sure" to "confirmed it doesn't work."

Not eligible:

- Market research (interviews are valuable but not SR&ED).
- Commercial / sales work.
- Routine debugging that didn't resolve an uncertainty.
- Straightforward engineering where the outcome was never in doubt.

## Folder layout

```
docs/sred/
├── README.md         # this file
├── template.md       # copy into a new monthly entry
└── YYYY-MM.md        # one per calendar month
```

## How to use this

1. At the end of each month (or sooner when a non-obvious decision is
   made), copy `template.md` to `YYYY-MM.md`.
2. Fill each section concisely. **Prose, not marketing copy.** Cite
   commits and issues rather than re-narrating them.
3. Log hours as you go in a simple list — CRA reviewers want to see
   granularity, not a single round number.
4. When the fiscal year ends, the consultant will aggregate these into
   the T661 narrative.

## Conventions

- Commits referenced by short SHA + subject (`7156cb8 feat: initial scaffold`).
- Issues referenced by `#N` — GitHub will auto-link on render.
- Hours in decimal (`2.5 h`, not `2h 30m`).
- No PII — contributor initials or GitHub handles only.
