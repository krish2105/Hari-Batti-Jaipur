# HariBatti mobile app

Signal countdowns and spoken speed advice for the Mansarovar corridor (Expo SDK 57, iOS + Android).
Safety: advice never says "go", is capped at the speed limit minus 5 km/h, taps are locked above
5 km/h, and the physical signal always wins. Location is used only while Ride, Walk or Report is open.

```bash
cp apps/mobile/.env.example apps/mobile/.env   # set EXPO_PUBLIC_API_URL to your laptop's LAN IP for a phone
pnpm dev:mobile                                  # scan the QR code with Expo Go
pnpm --filter mobile web                         # or try it in a browser (react-native-web)
pnpm --filter mobile test                        # ride-mode safety and logic tests
```

Without the API (or without the simulator running) the app shows simulated countdowns from the
ASSUMED plans and says so. "Start ride · Simulated" drives a simulated GPS along the corridor.
Offline data: `src/data/corridor.json` (public aggregates, rebuilt by `python3 scripts/export_mobile_data.py`).
Android test APK: `cd apps/mobile && eas build -p android --profile preview` (needs an Expo account; uploads the code to Expo's build servers).
