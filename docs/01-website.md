# HariBatti 01 — 3D Showcase Website

As of 26 Sep 2026 · Krishna Mathur

## Goal, audience and success

The website has one job: make a traffic officer say "show me more" within 60 seconds. It tells the story problem → Jaipur map → solution → impact → ask, with the surveyed Mansarovar corridor running in 3D, its traffic density driven by real May 2026 counts.

| Audience | What they must feel | Section that delivers it |
| --- | --- | --- |
| Traffic DCP / Abhay Command Centre | "This helps our Mansarovar corridor succeed" | Map + dashboard preview + pilot ask |
| Data Core Infotech | "This adds to our ITMS, not against it" | Partner section |
| Citizens / press | "I want this app" | App demo + impact calculator |
| Recruiters (UAE, India) | "This person ships real systems" | Tech section + GitHub link |

**Success criteria**

- First meaningful 3D frame under 3 s on a mid-range Android on 4G.
- 60 fps on desktop, 30+ fps on phone; automatic low-quality mode.
- Works in English and Hindi (toggle).
- Every simulated number is labelled "Simulated"; survey numbers are labelled "Survey, May 2026". Show aggregates only, never the raw survey sheets.
- Lighthouse: Performance 80+, Accessibility 95+.

## Page structure: the scroll story

Ten sections, one continuous 3D canvas behind the scroll. The camera flies over Jaipur as the reader scrolls.

| # | Section | 3D / visual | Content |
| --- | --- | --- | --- |
| 1 | Hero | Dusk over a low-poly Pink City; a signal turns red, a counter starts | "Jaipur waits. Every red light, every day." + two buttons: See the map, Watch the demo |
| 2 | The wait | A queue of bikes, autos and cars piles up; red-wait counter ticks | Live counter: "hours Jaipur lost while you read this" (method shown, labelled estimate) |
| 3 | The squeeze | Green lasts a few seconds; only a few vehicles cross; the rest wait again | Starved greens, 2–3 cycle waits, red-light jumping, short pedestrian time |
| 4 | Jaipur map | Camera drops onto a 3D OSM map; 8 surveyed Mansarovar junctions glow | Click a junction → card: control type, real 24-h volume + PM peak PCU (from data/processed), simulated countdown |
| 5 | What Jaipur already did | A distant Rambagh Circle pulses blue (AI-ITMS) | Credit the police trial: 8–45 s saved per lane; 253 of 423 junctions next. "We build on this." |
| 6 | The solution: HariBatti | Phone mockup floats; timer mirrors the 3D signal | Three products: app, Signal Command, audit reports |
| 7 | Green wave demo | A scooter drives the Mansarovar corridor (J03→J08); speed advice keeps it in green | Toggle: "without HariBatti" (stops 5x) vs "with" (stops 1x), simulated |
| 8 | AI features | Floating cards orbit a junction | Phase prediction, queue vision, fairness audit, AI copilot, event mode |
| 9 | Impact calculator | Sliders; CO2 and fuel meters | Inputs: junctions, daily vehicles, seconds saved → hours, litres, CO2, ₹ (formula shown) |
| 10 | Pilot ask + contact | Camera rises to the whole city skyline | "60-day free pilot on the Mansarovar corridor" + contact form (mailto) + team |

Footer: OpenStreetMap attribution, "Independent project, not affiliated with Rajasthan Police" until an MoU exists, privacy note.

**Impact calculator formula (show it on the page)**

```
hours_saved_per_day = junctions × daily_vehicles_per_junction × seconds_saved / 3600
fuel_saved_litres   = hours_saved_per_day × idle_litres_per_hour   # default 0.6 L/h car idle (editable assumption)
co2_kg              = fuel_saved_litres × 2.31                     # kg CO2 per litre petrol
```

## 3D and map design

The look is "Pink City at dusk meets control room": warm terracotta buildings, dark navy sky, and signal colours as the only saturated accents. Keep it original: stylised low-poly Jaipur architecture (jharokha windows, chhatris, city walls), no copied 3D models or logos.

| Token | Value | Use |
| --- | --- | --- |
| `--pink` | #E8998D | Buildings, brand |
| `--terracotta` | #C1666B | Accent, headings |
| `--night` | #0F1B2D | Background |
| `--signal-red` | #FF3B30 | Red phase only |
| `--signal-amber` | #FFB020 | Amber phase only |
| `--signal-green` | #22C55E | Green phase only |
| `--itms-blue` | #3B82F6 | AI-ITMS junctions |
| Fonts | "Fraunces" (headings), "Inter" (body), "Noto Sans Devanagari" (Hindi) | Google Fonts |

**3D scene pieces**

1. `PinkCity`: procedural low-poly blocks with instanced meshes (one draw call for hundreds of buildings).
2. `SignalPole`: reusable 3-lamp signal with emissive lamps + digital countdown texture, driven by `PhaseState`.
3. `Vehicles`: instanced scooters, autos, cars and buses moving along corridor splines; they stop at red and bunch into queues.
4. `CameraRig`: GSAP ScrollTrigger timeline over Lenis smooth scroll; one keyframe per section.
5. `Post effects`: subtle bloom on signal lamps only; off in low-quality mode.

**Jaipur map (section 4)**

- MapLibre GL base map from OSM vector tiles (OpenFreeMap, no key), 3D building extrusion, 45° pitch.
- deck.gl layers: `ScatterplotLayer` for junctions coloured by health score, `TripsLayer` for animated vehicle trails on the Mansarovar corridor, `PathLayer` for the corridor.
- Junction click → side card with live simulated countdowns per approach, plus "Source: Simulated" badge.
- The three.js camera fades into the map at section 4 and back out at section 6.

## Stack, files and performance rules

Next.js 15 (App Router, TypeScript) on Vercel, with React Three Fiber for 3D and MapLibre + deck.gl for the map.

```
apps/web/
├── app/
│   ├── [locale]/page.tsx        # en | hi, all 10 sections
│   └── api/sim/route.ts         # proxies simulator (or local mock)
├── components/
│   ├── three/                   # PinkCity, SignalPole, Vehicles, CameraRig
│   ├── map/                     # JaipurMap, JunctionCard, layers.ts
│   ├── sections/                # Hero, Wait, Squeeze, ..., PilotAsk
│   └── ui/                      # Button, Badge("Simulated"), Slider
├── lib/
│   ├── useSignals.ts            # WebSocket hook → PhaseState[]
│   ├── mockSignals.ts           # offline fallback generator
│   └── impact.ts                # calculator formulas + tests
├── messages/en.json, hi.json    # next-intl strings
└── public/data/junctions.geojson
```

**Performance rules**

1. Instanced meshes for buildings and vehicles; never one mesh per object.
2. Lazy-load the map and 3D canvas with `next/dynamic` (no SSR).
3. Detect weak devices (`navigator.hardwareConcurrency < 6` or low FPS for 2 s) → low-quality mode: no bloom, fewer vehicles, lower DPR.
4. Respect `prefers-reduced-motion`: replace fly-throughs with fades.
5. Compress any GLB with Draco/Meshopt; textures as KTX2 or WebP.
6. `mockSignals.ts` must run with zero backend so the site never breaks in a demo.

**Accessibility**: all text as real HTML over the canvas; colour is never the only signal (countdown number + "RED" label); keyboard-navigable junction list mirrors the map.

## Build phases (for Claude Code)

- Phase 1 — Skeleton: design tokens, fonts, 10 empty sections, en/hi toggle, mockSignals.ts generating PhaseState for the 8 junctions in data/junction_registry.csv (cycle 90–150 s).
- Phase 2 — Hero + 3D city: PinkCity (instanced), SignalPole with live countdown texture, dusk lighting, CameraRig with ScrollTrigger keyframes.
- Phase 3 — Vehicles + Squeeze: instanced traffic on the Mansarovar corridor spline, density scaled by data/processed/hourly_profile_pcu.csv, queues form on red; Wait counter; Squeeze animation.
- Phase 4 — Jaipur map: MapLibre 3D map, junction layer by health, TripsLayer animation, JunctionCard with per-approach countdowns, keyboard-accessible junction list.
- Phase 5 — Solution, Green-wave demo (with/without toggle), AI feature cards, Impact calculator (lib/impact.ts + unit tests).
- Phase 6 — Pilot ask, footer, SEO metadata, OG image, low-quality mode, reduced-motion, Lighthouse pass, deploy to Vercel.

## Acceptance checklist

- [ ] First 3D frame under 3 s on a mid-range Android, 4G
- [ ] Works fully offline from the backend (mock signals)
- [ ] 8 Mansarovar junctions clickable on map, with countdowns
- [ ] Every simulated number carries a "Simulated" badge
- [ ] Rambagh Circle credited as the police AI-ITMS trial
- [ ] Hindi toggle translates every visible string
- [ ] Impact calculator shows its formula and assumptions
- [ ] Reduced-motion and low-quality modes work
- [ ] OSM attribution and "not affiliated" note in footer
- [ ] Lighthouse Performance 80+, Accessibility 95+ (mobile)
- [ ] Deployed on Vercel with a clean URL
