# Interview script — 20 minutes

From `CLAUDE.md` §8. Free-form, not a checklist — let the conversation
breathe. The goal is to be wrong about something you currently believe.

## Opener (1 min)

> Thanks for the time. I'm building an open-source tool that plans
> mixed-mode trips. I'd rather hear about your actual experience than
> demo anything yet. Mind if I take notes?

## Cohort A — Pearson commuter (15 min)

1. Walk me through the last time you travelled to or from Pearson.
2. What did you use to plan it? What did you actually do? (Tools used vs.
   actual decision often diverge — the gap is the signal.)
3. What did the app get wrong or miss?
4. How much would saving 15 minutes be worth? $20? $5? Nothing?
5. How much would saving $20 be worth if it cost you 15 extra minutes?
6. Would you ever take an Uber part of the way and transit the rest?
   When? When not?
7. What do you do when your flight is at 6 a.m. and transit doesn't run
   yet? (Common forced-Uber scenario — note the price ceiling.)

## Cohort B — newcomer (15 min)

Replace 4–7 with:

4. First time you took transit here — what confused you?
5. Did anyone teach you how PRESTO works? Or did you figure it out?
6. Have you ever paid more than you should have because of how the fares
   interact (TTC + GO, GO + UP, etc.)?
7. Do you avoid certain trips because the planning feels too complex?

## Demo + reaction (3 min)

8. Show polyroute on a corridor relevant to them. Don't narrate the UI —
   let them click and react. Note where they pause, what they ignore.

## Wrap (1 min)

9. Would you pay anything for a tool like this? Why or why not?
10. Who else should I talk to?

## After the call (within 24 h)

- Anonymized notes file: `docs/interviews/notes/<initials>-<yyyy-mm-dd>.md`
- Three-line summary at the top: surprise / confirmation / dead end.
- If the interview suggests a feature change, file an issue tagged
  `from-interview`.
- If it suggests a non-negotiable in `CLAUDE.md` §4 is wrong, ping
  yourself to talk to two more people before changing anything.
