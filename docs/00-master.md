# HariBatti 00 — Master Plan & Mansarovar Corridor Pilot

As of 26 Sep 2026 · Krishna Mathur

## Executive summary

HariBatti (working name, "green light") is a citizen + police layer on top of Jaipur's signals: live countdowns for drivers, and an audit that shows police where red waits are too long and greens too short. We do not replace signal control. Jaipur Police is already rolling AI-ITMS to 253 of 423 junctions with Data Core Infotech.

**The problem, in Jaipur terms**

- Long red waits: old fixed cycles of 60–90 s run regardless of actual traffic.
- Starved greens: some phases are too short to clear the queue, so vehicles wait 2–3 cycles and jump reds.
- Short pedestrian clearance on wide roads (Tonk Road, JLN Marg).
- No citizen visibility: a driver 500 m away cannot know when the light will change.
- Jaipur drivers lost 121 rush-hour hours in 2025 (TomTom); about 7.5 lakh cars; public transport share about 13%.

**Positioning**

| Player | What they own | Our move |
| --- | --- | --- |
| Jaipur Police + Data Core Infotech | AI signal control at 253 junctions | Partner. We consume their data, never compete. |
| Mappls (MapmyIndia) | Live signal timers, Bengaluru only | Beat them to Jaipur with a local, Hindi, two-wheeler-first app plus a police dashboard they don't offer. |
| Google Maps | Routing, no signal timers in India | Ignore; we are signal-specific. |

**Product family (one backend, three front-ends)**

| # | Product | User | Document |
| --- | --- | --- | --- |
| 1 | 3D showcase website | Police, officials, investors, recruiters | docs/01-website.md |
| 2 | Signal Command dashboard | Traffic DCP, Abhay Command Centre | docs/02-dashboard.md |
| 3 | HariBatti mobile app (iOS + Android) | Drivers, riders, pedestrians | docs/03-mobile.md |

## Pilot decision: Mansarovar corridor (8 surveyed junctions)

We pitch the Mansarovar corridor between Mansarovar Metro and Sanganer Stadium, because we already hold professional 24-hour classified turning-movement counts for 8 junctions there (11 and 12 May 2026). No other team walking into the police office will have measured data on day one. Tonk Road (the police's announced Model Corridor) becomes the phase-2 expansion.

**Why this corridor wins**

1. Real data: 14 junction-days of 15-minute counts by vehicle class and turn, 24 hours each (see docs/05-data-analysis.md).
2. One arterial, six signals in a row (J03–J08): the ideal shape for a coordinated green wave and speed advice.
3. The main road carries 66–90% of peak-hour PCU at J04–J08, so any signal giving side streets equal time is wasting green — a concrete, testable fix.
4. High visibility: Mansarovar is one of Jaipur's densest residential zones, with the metro terminal and Sanganer/airport traffic.

**Pilot junctions (IDs used everywhere in code: data/junction_registry.csv)**

| ID | Junction | Survey code | Days counted | 24-h vehicles (11 May) | PM peak (PCU/hr) |
| --- | --- | --- | --- | --- | --- |
| J01 | SFS RIICO | — | 1 | 176,546 | 9,340 |
| J02 | SFS Agrawal | — | 1 | 125,444 | 6,836 |
| J03 | Jansunvai | TMC-01 | 2 | 127,998 | 7,392 |
| J04 | Vijay Path | TMC-02 | 2 | 129,047 | 7,270 |
| J05 | Patel Marg | TMC-03 | 2 | 128,195 | 7,187 |
| J06 | VT Road | TMC-04 | 2 | 153,323 | 8,307 |
| J07 | Rajat Path | TMC-05 | 2 | 127,981 | 7,972 |
| J08 | Bhrigu Path | TMC-06 | 2 | 114,811 | 6,331 |

**Still missing (collect before the demo)**

| Data | Why | How |
| --- | --- | --- |
| Signal timings (cycle, green per phase) | Needed for red wait, degree of saturation, Webster plans | Phone stopwatch, 10 cycles per junction at AM and PM peak → data/signal_timings.csv |
| Lanes and stop-line widths per approach | Capacity and saturation flow | DWG drawing if available, else Google Maps measure |
| Exact coordinates and junction order | Map, simulator, green-wave offsets | Google Maps → lat/lng columns in data/junction_registry.csv |
| Confirm approach names | Survey files label some cross roads differently | One site visit or ask the survey agency |

**Pilot success metrics (what we promise to measure, not guarantee)**

| Metric | Baseline method | Target |
| --- | --- | --- |
| Degree of saturation (v/c) per approach | TMC peak PCU ÷ capacity from timings + lanes | Flag every approach above 0.9 |
| Average red wait per approach (s) | Stopwatch timings + TMC arrivals | Report it; then -15% via recommended splits |
| Stops per corridor trip (J03→J08) | GPS test drives, 20 runs | -20% with green-wave speed advice |
| Pedestrian clearance vs crossing width | Tape + timer | 100% of crossings at about 1.0–1.2 m/s walking speed |
| App timer accuracy (s error) | App vs physical signal | Under 2 s with live feed |

Targets are design goals, not results yet.

## Document map and build order

Build in this order: shared backend + simulator first, then website, then dashboard, then app. The simulator feeds all three until the real police feed arrives.

| Order | Document | Build in Claude Code | Depends on | Est. effort |
| --- | --- | --- | --- | --- |
| 0 | docs/00-master.md (this) | `packages/core` + `services/sim` | Nothing | 1 week |
| 1 | docs/01-website.md | `apps/web` | Simulator API | 2 weeks |
| 2 | docs/02-dashboard.md | `apps/dashboard` + `services/api` | Simulator + ML | 3 weeks |
| 3 | docs/03-mobile.md | `apps/mobile` | API + timers | 3–4 weeks |
| — | docs/04-runbook.md | All terminal commands | — | — |
| — | docs/05-data-analysis.md | Findings from the May 2026 traffic counts | — | — |

## Shared architecture, repo and stack

One monorepo, one signal data model, and a **Signal Phase Adapter** that can read from three sources: the simulator today, crowd-sourced GPS estimates next, and the police ITMS feed once the MoU is signed. Every front-end reads the same API, so swapping the source changes nothing downstream.

```
hari-batti/
├── apps/
│   ├── web/          # 01 — Next.js + React Three Fiber showcase
│   ├── dashboard/    # 02 — Next.js police Signal Command dashboard
│   └── mobile/       # 03 — Expo (React Native) iOS + Android app
├── services/
│   ├── api/          # FastAPI: REST + WebSocket /ws/signals
│   ├── sim/          # SUMO digital twin of the Mansarovar corridor + phase generator
│   └── ml/           # YOLO counts, phase prediction, plan optimiser
├── packages/
│   ├── core/         # shared TypeScript types: Junction, Phase, Countdown
│   └── ui/           # shared design tokens (colours, fonts)
├── data/
│   ├── osm/          # Jaipur OSM extract (ODbL, attribute it)
│   └── junctions.geojson  # the 8 pilot junctions
└── docs/             # these documents
```

**Core data model (in `packages/core`)**

```ts
// One signalised junction on the map
type Junction = {
  id: string;              // e.g. "J03"
  name: string;            // "Jansunvai Junction"
  lat: number; lng: number;
  controlType: "AI_ITMS" | "FIXED" | "FLASHING" | "UNKNOWN";
  approaches: Approach[];  // one per road arm
};

// Live state pushed every second over WebSocket
type PhaseState = {
  junctionId: string;
  approachId: string;
  colour: "RED" | "AMBER" | "GREEN" | "FLASHING_AMBER";
  secondsRemaining: number;          // countdown shown to users
  confidence: number;                // 0–1; 1.0 only with police feed
  source: "SIM" | "CROWD" | "ITMS";  // always shown in UI
  updatedAt: string;                 // ISO time
};
```

**Tech stack (zero paid APIs)**

| Layer | Choice | Why |
| --- | --- | --- |
| Website | Next.js 15, React Three Fiber, drei, GSAP, Lenis, MapLibre GL, deck.gl | 3D + real map, deploys on Vercel |
| Dashboard | Next.js, shadcn/ui, Recharts, MapLibre | Fast, clean admin UI |
| Mobile | Expo (React Native), MapLibre RN, expo-speech, expo-location | One codebase for iOS + Android |
| API | FastAPI, WebSockets, PostgreSQL + PostGIS, Redis | Geo queries + live push |
| Simulation | SUMO + TraCI (Python, `eclipse-sumo` package) | Free, standard traffic simulator |
| ML | Ultralytics YOLO, PyTorch (LSTM for phase prediction), OR-Tools or RL for plans | Proven, well documented |
| LLM copilot | Local Ollama (qwen2.5:7b) with read-only SQL tools | Free, runs on the Mac |
| Hosting | Vercel (web); dashboard + API on laptop until MoU | Free for a pilot |

**Data sources**

| Source | Status | Use |
| --- | --- | --- |
| OpenStreetMap Jaipur | Free now | Roads, junction geometry, 3D map |
| 24-h classified turning counts, 8 junctions, 11–12 May 2026 | Have it (data/raw/tmc) | Demand, peaks, turn ratios, simulator input |
| Signal timings at 8 junctions | You collect (stopwatch) | Red wait, v/c, Webster plans |
| GPS traces from test drives | You collect | Validate crowd phase estimates |
| Jaipur ITMS / Abhay Command Centre feed | Needs MoU | Real countdowns, confidence 1.0 |
| Citizen reports from the app | After launch | Broken or hidden signals |

## Outreach plan via family network

The ask is small on purpose: a 20-minute demo, then a free 60-day pilot with read-only data access on the Mansarovar corridor.

1. Build first: website live + dashboard demo on simulated data + a baseline report built on the 24-hour counts for 8 junctions.
2. Warm intro: family contact forwards a 5-line WhatsApp note + website link to the right officer (Traffic DCP office or Abhay Command Centre in-charge).
3. 20-minute demo in person, laptop + phone, no slides needed.
4. Leave behind: 2-page pilot proposal (PDF) + one-page data-sharing MoU draft.
5. Offer to meet Data Core Infotech too: frame HariBatti as the citizen + audit layer for their system.

**WhatsApp intro (family contact sends this)**

> Namaste Sir, my relative Krishna Mathur (B.Tech CSE AI/ML, now MAIB at SP Jain) has built HariBatti, a free citizen app + audit dashboard for Jaipur signals, already calibrated on 24-hour traffic counts from 8 Mansarovar junctions. It works with the new AI-ITMS rather than replacing it. Could he show you a 20-minute demo? Link: [website]

**20-minute demo script**

| Minute | Show | Say |
| --- | --- | --- |
| 0–3 | Website hero + Jaipur 3D map | "Your AI-ITMS trial saved 8–45 s per lane. Citizens can't see that yet." |
| 3–8 | Dashboard: Mansarovar Junction Health | "Here are 24-hour counts for 8 of your junctions: the main road carries up to 90% of peak traffic. Here is where green time doesn't match demand." |
| 8–13 | Phone app: countdown + voice speed advice | "Mappls did this in Bengaluru with Bengaluru Police. Jaipur can have a local version with a Rajasthan team." |
| 13–17 | Before/after report | "Every month you get a press-ready report: hours, fuel and CO2 saved." |
| 17–20 | The ask | "60-day free pilot, read-only feed, 8 junctions. We sign an MoU, you own the data." |

**MoU ask**: read-only access to live phase and countdown data for the 8 pilot junctions; no control rights; data stays in India; police own all data and reports; pilot ends after 60 days with a joint review; police can switch HariBatti off at any time.

## Business model, confidence and risks

Money comes from government pilots and B2B data, not app subscriptions. All rupee figures are planning estimates, not quotes.

| Stream | Buyer | Realistic year-1 range (est.) |
| --- | --- | --- |
| Paid pilot / audit contract | Jaipur Police, JDA, Smart City SPV | ₹5–25 lakh |
| Expansion to Kota, Udaipur, Jodhpur | Rajasthan city bodies | ₹10–50 lakh per city (year 2+) |
| Subcontract / licence to ITMS vendor | Data Core Infotech or similar | ₹5–20 lakh |
| Signal-aware ETA API | Delivery fleets, ambulances, school buses | ₹2–10 lakh |
| App premium | Drivers | ₹0–5 lakh |

Reference: full ATCS hardware ≈ ₹20 lakh per four-arm junction vs ≈ ₹7.5 lakh reusing existing cameras (IUDX); Bengaluru approved ₹56.45 crore for 110 adaptive junctions.

| Outcome | Confidence |
| --- | --- |
| Problem is real and painful | 90% |
| Police give read-only pilot data (warm intro + demo) | 40–50% |
| HariBatti, not Mappls, becomes Jaipur's timer app | 25–35% |
| Paid contract within 12 months | 15–25% |
| Strong job / consulting / portfolio outcome | 85–90% |

| Risk | Fallback |
| --- | --- |
| No police data feed | Ship on crowd estimates labelled "estimated"; sell audit on field data |
| Mappls arrives in Jaipur first | Two-wheeler voice, pedestrian mode, police audit, Hindi, Rajasthan cities |
| Adaptive signals make prediction hard | Exact countdowns only with ITMS feed; otherwise range + confidence |
| Driver distraction | Voice-first, no taps while moving |
| Wrong timer causes red-light jumping | Never say "go"; "prepare to stop" early; first-run disclaimer |

**Legal checklist**: DPDP Act 2023 consent + anonymised GPS + India hosting; Motor Vehicles Act (no handheld use → voice + mount only); OSM ODbL attribution; no police logos or endorsement claims before an MoU.

## Timeline and viva Q&A

| Week | Deliverable | Gate |
| --- | --- | --- |
| 1 | Monorepo, data model, SUMO twin, WebSocket sim feed | Sim streams 8 junctions live |
| 2–3 | 3D website on Vercel | Under 3 s on mid-range phone |
| 3–4 | Signal timings + coordinates at 8 junctions (counts already done) | Baseline v/c report with real numbers |
| 4–6 | Signal Command dashboard | Health scores + audit on field data |
| 6 | Police demo | Pilot yes / no / later (go/no-go) |
| 7–10 | App beta (Android first) | 50 test users on the Mansarovar corridor |

1. **Jaipur already has AI signals — why this?** ITMS controls lights; nobody shows drivers the countdown or audits fairness. We are that layer.
2. **Real timers without police data?** Simulator for demos, crowd GPS estimates with confidence, exact feed after MoU; UI always shows the source.
3. **What is GLOSA?** Green Light Optimal Speed Advisory; the UK A45 Birmingham trial cut journey time 7%.
4. **Dangerous while driving?** Voice-first, mount-only, never says "go".
5. **vs Mappls?** Mappls is Bengaluru-only; we add police audit, two-wheeler + pedestrian modes, Rajasthan focus.
6. **Money?** Government pilots/audits first, fleet APIs second; app stays free.

## Sources

- Traffic counts: classified 24-hour turning movement counts, 8 Mansarovar junctions, 11–12 May 2026 (source agency to confirm; treat as confidential)

- Jaipur AI signals at 253 intersections — https://www.pinkcitypost.com/jaipur-to-roll-out-ai-traffic-signals-at-253-intersections-after-successful-rambagh-circle-trial/
- Tonk Road model corridor — https://www.pinkcitypost.com/jaipur-to-get-4-adcps-8-acps-for-traffic-tonk-road-to-be-turned-into-citys-first-model-traffic-corridor/
- Mappls signal timers, Bengaluru — https://www.drivespark.com/off-beat/bengaluru-first-city-in-india-to-get-live-traffic-signal-countdown-on-mappls-app-077103.html
- TomTom Jaipur — https://www.tomtom.com/traffic-index/city/jaipur/
- Jaipur transport — https://www.downtoearth.org.in/air/how-india-moves-jaipurs-commuters-desperately-await-more-buses-as-other-transport-modes-prove-costly
- ATCS cost — https://iudx.org.in/enabling-low-cost-intelligent-traffic-signal-system-with-iudx/
- GLOSA A45 trial — https://www.interregeurope.eu/good-practices/glosa-green-light-optimal-speed-advisory
