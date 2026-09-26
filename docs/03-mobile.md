# HariBatti 03 — Mobile App (iOS + Android)

As of 26 Sep 2026 · Krishna Mathur

## Purpose, users and safety

HariBatti shows the countdown of the next signals on your route and speaks one simple piece of advice: keep this speed to catch green, or prepare to stop. Free, Hindi-first, built for two-wheelers as much as cars.

| User | Need | Mode |
| --- | --- | --- |
| Two-wheeler rider | Hands-free, helmet audio | Rider mode (voice only) |
| Car / cab / auto driver | Glanceable timer on a mount | Drive mode |
| Pedestrian | "Can I cross safely now?" | Walk mode (big numbers + audio) |
| Delivery / fleet driver | Fewer stops, better ETA | Drive mode + fleet API later |

**Safety principles (non-negotiable)**

1. Voice-first. No typing or tapping while speed is above 5 km/h.
2. Never say "go" or "you can make it". Only "hold X km/h", "prepare to stop", or "red, X seconds".
3. Never advise above the speed limit; cap advice at the posted limit minus 5 km/h.
4. Show the data source on every countdown: Live (police feed), Estimated (crowd), or Simulated.
5. When confidence is low, show a range ("red, 20–40 s") instead of a false exact number.
6. The physical signal always wins; say so on first launch.

## Features: MVP vs later

| Feature | MVP (Mansarovar corridor beta) | Later |
| --- | --- | --- |
| Next 3 signals countdown on route | Yes | Whole city |
| Green-wave speed advice (voice) | Yes | Adaptive to live queues |
| Rider mode (Bluetooth helmet audio) | Yes | |
| Walk mode (pedestrian countdown + audio) | Yes | Accessibility partners |
| Hindi + English voice and UI | Yes | Rajasthani voice pack |
| Report a signal problem (photo + GPS) | Yes | Status updates from police |
| Engine-off nudge on long red (above 30 s) | Yes | Fuel/CO2 saved profile |
| Route choice by fewest reds / expected wait | | Yes |
| Event mode alerts (SMS Stadium, festivals, VIP) | | Yes |
| Home-screen widget + iOS Live Activity | | Yes |
| Android Auto / CarPlay | | Yes |
| Ambulance green-corridor alert ("move left") | | Yes, with police |
| Kota, Udaipur, Jodhpur | | Yes |

## Screens and user flow

| # | Screen | Content |
| --- | --- | --- |
| 1 | Onboarding (3 cards) | What it does · safety rule ("the real signal always wins") · language: हिंदी / English |
| 2 | Permissions | Location "while using" only, with a plain reason; microphone never needed |
| 3 | Home map | Jaipur map, Mansarovar corridor junctions with live colour dots; big "Start ride" and "Walk" buttons |
| 4 | Ride / Drive | Next signal with huge countdown + colour band; next 2 signals smaller; advice line ("Hold 32 km/h"); source badge; screen stays on |
| 5 | Walk | Nearest crossing, pedestrian countdown in giant digits, audio every 5 s |
| 6 | Report | Type (broken / hidden / timing bad / other), auto GPS, optional photo — only when stopped |

**Flow**: Open → Home map → Start ride → GPS matched to the corridor → next 3 signals → spoken advice at 400 m, 200 m and 100 m → trip summary (stops, time waited, fuel saved estimate).

## Green-wave and countdown logic

```ts
// packages/core/glosa.ts — Green Light Optimal Speed Advisory, kept simple and safe

type Advice =
  | { kind: "HOLD_SPEED"; kmh: number }         // arrive during green at this speed
  | { kind: "PREPARE_TO_STOP"; redSecs: number } // green can't be caught safely
  | { kind: "UNKNOWN" };                         // low confidence: show range only

export function adviseSpeed(
  distanceM: number,          // metres to the stop line
  phase: PhaseState,          // current colour + secondsRemaining + confidence
  nextGreenStartS: number,    // seconds until next green (0 if green now)
  nextGreenEndS: number,      // seconds until that green ends
  speedLimitKmh: number,      // posted limit for this road
): Advice {
  if (phase.confidence < 0.7) return { kind: "UNKNOWN" };   // never guess loudly

  const maxKmh = speedLimitKmh - 5;                          // safety cap below limit
  const minKmh = 15;                                         // slower than this blocks traffic
  const toKmh = (mps: number) => mps * 3.6;

  // Arrival window: [green start + 2 s, green end - 3 s]
  const earliest = nextGreenStartS + 2;
  const latest = nextGreenEndS - 3;
  if (latest <= earliest) return { kind: "PREPARE_TO_STOP", redSecs: nextGreenStartS };

  const slowest = toKmh(distanceM / latest);                 // arrive at the last safe moment
  const fastest = toKmh(distanceM / Math.max(earliest, 0.1)); // arrive at the first safe moment

  const lo = Math.max(slowest, minKmh);
  const hi = Math.min(fastest, maxKmh);
  if (lo > hi) return { kind: "PREPARE_TO_STOP", redSecs: nextGreenStartS };

  const kmh = Math.round(Math.min(hi, lo + 5) / 5) * 5;     // round to 5s, easy to hold
  return { kind: "HOLD_SPEED", kmh };
}
```

**Worked example (must be a unit test)**: 300 m to the signal, green starts in 20 s and ends at 50 s, limit 50 km/h. Window 22–47 s → 23–49 km/h, capped at 45. GLOSA v1 said "Hold 30 km/h" (slowest safe speed + 5); **GLOSA v2 says "Hold 45 km/h"** — the fastest safe speed that still arrives in the green window, so riders stop less without taking longer.

| Source | Confidence | Shown as |
| --- | --- | --- |
| Police ITMS feed | 0.95–1.0 | "Live · 23 s" |
| Crowd estimate | 0.5–0.8 | "Est. · 20–30 s" |
| Simulator | Demo only | "Simulated · 23 s" |

Adaptive signals can change a phase early or late, so the app re-computes every second and never promises a number more than about 60 s ahead.

## Stack, privacy and store release

| Need | Library |
| --- | --- |
| Map | `@maplibre/maplibre-react-native` + OSM tiles |
| Location | `expo-location` (foreground; background only during an active ride) |
| Voice | `expo-speech` (hi-IN, en-IN) |
| Keep screen on | `expo-keep-awake` |
| Live data | WebSocket to `/ws/signals` + reconnect |
| State | Zustand |
| i18n | `i18next` (hi, en) |
| Crashes | Sentry free tier (no personal data) |
| Builds | EAS Build + EAS Submit |

**Privacy (DPDP Act 2023)**: consent screen before location use; location only during a ride, rounded, no user ID; traces deleted after 30 days; no login in MVP; data hosted in India.

| Step | Android | iOS |
| --- | --- | --- |
| Account | Play Console ($25 one-time) | Apple Developer ($99/year) |
| Beta | Internal track / APK link, 50 users | TestFlight, 50 users |
| Launch | Mansarovar corridor only, "Beta" label | Same |

## Build phases (for Claude Code)

- Phase 1 — Shell: onboarding, permissions, Home map with junctions from the API, offline mock fallback.
- Phase 2 — Ride mode: map-match GPS, next 3 signals, giant countdown, advice via adviseSpeed, keep-awake, trip summary.
- Phase 3 — Voice: Hindi + English prompts at 400/200/100 m, Rider mode, engine-off nudge on red > 30 s.
- Phase 4 — Walk mode + Report flow (only when stopped), POST /reports.
- Phase 5 — Polish: dark mode, large text, Sentry, icons, EAS profiles, Play internal track + TestFlight.

## Acceptance checklist

- [ ] First launch to live countdown in under 30 s
- [ ] Countdown matches the simulated feed within 1 s
- [ ] Advice never above limit minus 5 km/h and never says "go"
- [ ] Low confidence shows a range
- [ ] Hindi + English voice works with phone locked (Rider mode)
- [ ] No taps accepted above 5 km/h
- [ ] Location stops when the ride ends
- [ ] Report submits with GPS when stopped
- [ ] Android + iOS test builds install on real phones
- [x] adviseSpeed tests pass, including the 300 m example (45 km/h with GLOSA v2)

## Status (W8, 26 Sep 2026)

Built in `apps/mobile` (Expo SDK 57, runs in Expo Go):

| Area | Status |
| --- | --- |
| Onboarding (3 cards, safety rule, हिंदी / English), consent before location | Done |
| Home: corridor strip J08 → J03 with live colour dots, countdown for both directions | Done (a schematic strip instead of a MapLibre map, so it runs in Expo Go without a native build) |
| Ride: GPS matched to the corridor, next 3 signals, giant countdown, GLOSA v2 advice, keep-awake, trip summary | Done; if this green cannot be caught safely it advises for the following green before saying "prepare to stop" |
| Voice at 400 / 200 / 100 m (hi-IN, en-IN), Rider mode (voice only), engine-off nudge on red > 30 s | Done (on-device voices) |
| No taps above 5 km/h; advice ≤ limit − 5 km/h; never "go"; low confidence shows a range | Done and unit-tested (`pnpm --filter mobile test`) |
| Walk mode (pedestrian countdown, audio every 5 s) | Done, estimated from the vehicle phases (labelled Estimate) |
| Report (only when stopped, location rounded to ~100 m, POST /reports) | Done; photo upload not in the MVP |
| Simulated ride along the corridor (for demos and testing, labelled Simulated GPS) | Done |
| EAS profiles (preview APK, production bundle) | `eas.json` ready; the cloud build uploads the code to Expo, so it waits for the owner's go-ahead |
| Locked-phone voice, Sentry, store listings | Later (need a native development build and accounts) |

Checklist items above that need real phones (install on Android and iOS, voice with the phone locked,
1 s match with a live feed on the road) are still open.

