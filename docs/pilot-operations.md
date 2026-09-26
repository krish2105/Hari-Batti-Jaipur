# Pilot operations and new customers

*How the Signal Command dashboard supports a 60-day pilot, and how a second (non-police) customer is set up.*

## Pilot mode (Signal Command → Pilot)

| Part | What it does | Who can change it |
| --- | --- | --- |
| Pilot dates | Start and end of the pilot; shows "Day 12 of 60" and a progress bar | Admin |
| Success measures | Baseline, now and goal for each measure promised in the pilot proposal | Operator, Admin |
| Officer notes | Notes per junction, optionally pinned to an approach; pinned notes stay on top; can be marked resolved | Operator, Admin |
| 👍 / 👎 | One click on every insight card (audit fixes, junction heat map, forecasts, copilot answers …) | Everyone signed in |
| Weekly review | Five questions once a week (days used, most useful screen, action taken, what was missing, usefulness 1–5) | Operator, Admin |
| Timing-change log | Changes officers made **in their own signal system**, entered afterwards so before/after can be measured | Operator, Admin |
| Evidence Pack | Printable summary of all of the above in English or Hindi (Print → Save as PDF) | Everyone signed in |

### Honest numbers

- A value is either **measured**, with its source (FIELD, SURVEY, ITMS, CROWD or SIM), or shown as
  **"Not measured yet"**. The Evidence Pack prints those as *PLACEHOLDER — not measured yet*. Nothing is estimated to fill a gap.
- Two Jaipur baselines can already be computed from the May 2026 survey and are filled automatically, labelled
  **SURVEY counts + ASSUMED timing**: approach-peaks above v/c 0.9 (15 of 64) and the flow-weighted average red
  wait (21.4 s). They become FIELD values once stopwatch timings are collected.
- Goals are design goals from the proposal (for example "−20% stops with green-wave advice"), not results.
- HariBatti never changes a signal. The timing-change log only records what officers did.

## Pilot success measures (Jaipur)

| Measure | How it is measured | Goal |
| --- | --- | --- |
| Approach-peaks above v/c 0.9 | Survey peak PCU ÷ capacity from timings + lanes | Flag every approach above 0.9 |
| Average red wait per approach | Stopwatch timings + survey arrivals | −15% via recommended splits |
| Stops per corridor trip (J03→J08) | GPS test drives, 20 runs | −20% with green-wave speed advice |
| Crossings with enough walk time | Tape + timer at 1.0–1.2 m/s | 100% of crossings |
| App timer error vs the real signal | App vs physical signal, stopwatch | Under 2 s with a live feed |

## A new customer (Signal Command → Onboarding, Admin)

The wizard has six steps and one final "Create" (typically a few minutes; the automated test completes it in
about 2 seconds):

1. **Organisation**: name, type (traffic police, campus, township, fleet, other) and the name shown on reports.
   Branding is the name only; no customer logos without written permission.
2. **Sites**: a police tenant picks junctions from `data/junction_registry.csv` (J01–J08; new junctions cannot be
   invented). Other customers add their own gates or junctions (location optional).
3. **Data sources**: SIM for a demo, or FIELD / SURVEY / CROWD / ITMS / a configured data connector. Every value
   carries this label. A tenant whose only source is SIM is marked as a demo.
4. **Users**: emails that may see this organisation. What they can change follows their sign-in role.
5. **Pilot and report**: pilot name and dates, which success measures to track (a template per customer type),
   and the report template (title, sections, footer) used by the Evidence Pack.
6. **Review** and create.

Tenants are kept apart: notes, votes, reviews and the change log belong to one tenant, and a user who is not a
member does not see another tenant (the API answers "not found"). The Jaipur pilot and the SIM campus demo are
visible to every signed-in user. An Admin can **archive** a tenant when a customer leaves: it disappears from
every list, and its records are kept (there is no delete).

## Limits (honest)

- Membership decides which tenants a person sees; what they may change still follows their one sign-in role.
  Per-tenant roles are stored but not yet enforced separately.
- The time-to-onboard goal (under 15 minutes) is met by the automated test; it has not been timed with a real
  customer yet.
- The Evidence Pack is produced by the browser's print-to-PDF; there is no server-side PDF.
