# ABHAYA — Mobile App

Real React Native (Expo) app for the ABHAYA dynamic risk-aware navigation system. Talks to the
FastAPI backend in `../backend`, uses **real device GPS** (`expo-location`) and **real device
accelerometer/gyroscope** (`expo-sensors`) — no simulated sensor values are used anywhere in the
shipped app code. The one intentional exception is `LiveRideScreen`, which replays the real
recorded GPS trace at `../data/gps_traces/surat_real_trace.csv` as the "vehicle" position feed for
RouteGuard, since there is no public Uber/ride-hailing API to source a truly live vehicle feed from
— this was an explicit, agreed substitution (real recorded coordinates, not fabricated ones).
WalkGuard and general navigation always use the live device GPS/sensors.

## Screens

| Screen | File | Backend endpoint(s) |
|---|---|---|
| 1. Destination | `src/screens/DestinationScreen.js` | `POST /route` |
| 2. Route comparison | `src/screens/RouteComparisonScreen.js` | (uses `/route` response) |
| 3. Infrastructure view | `src/screens/InfrastructureScreen.js` | `GET /infrastructure` |
| 4. SafeDrop | `src/screens/SafeDropScreen.js` | `POST /safedrop` |
| 5. Live ride | `src/screens/LiveRideScreen.js` | `POST /routeguard/check` |
| 6. Deviation | `src/screens/DeviationScreen.js` | (driven by `/routeguard/check` state) |
| 7. WalkGuard | `src/screens/WalkGuardScreen.js` | `POST /walkguard/event` |
| 8. Safe-haven pickup | `src/screens/SafeHavenScreen.js` | `GET /safe-havens` |
| 9. Safety insight | `src/screens/SafetyInsightScreen.js` | `POST /safety-insight` |
| Settings | `src/screens/SettingsScreen.js` | lets you set the backend URL at runtime |
| Avatar customization | `src/screens/AvatarCustomizeScreen.js` | local only — no backend call |

## Design system: claymorphism

The whole app (`src/theme.js` + `src/components/Clay*.js`) uses a "claymorphism" visual system:
large border radii, a vivid warm/violet pastel palette (see `colors` in `src/theme.js`), and soft
dual light/dark shadows that make cards, buttons, inputs and badges read as puffy inflated clay
rather than flat material cards or glass panels. Reusable pieces live in `src/components/`
(`ClayCard`, `ClayButton`, `ClayBadge`, `ClayInput`, `ClayIconButton`); every screen's shared
`s`/`colors` tokens in `src/theme.js` were rebuilt on the same system so all 10 screens (plus the
navigation header in `App.js`) look consistent without any screen's backend calls or navigation
changing.

## Avatar companion

`src/components/avatar/` implements a from-scratch, no-external-API SVG avatar builder
(`react-native-svg`): `Face.js`, `Eyes.js`, `Hair.js`, `Outfit.js`, and `Accessory.js` are layered
by `AvatarRenderer.js` into one female-presenting character. `AvatarCustomizeScreen.js` offers a
Bitmoji-style horizontal swatch picker (6 skin tones, 6 hairstyles, 6 hair colors, 5 outfit colors,
4 accessories) with a live-updating preview. The chosen config is persisted via
`@react-native-async-storage/async-storage` through `src/context/AvatarContext.js`, and rendered
as a small clay-framed circular badge (`src/components/AvatarBadge.js`) in the navigation header,
on the Destination home screen, in Settings, and as the visible "companion" during WalkGuard and
the Deviation check-in flow.

## Prerequisites

- Node.js 18+ and npm
- The Expo Go app installed on a real Android/iOS phone (recommended — gives you real GPS and real
  motion sensors), or an Android/iOS simulator
- The ABHAYA backend running and reachable from your phone/emulator (see `../backend/README.md`)

## Install & run

```bash
cd app
npm install
npx expo start
```

(`react-native-svg`, `expo-linear-gradient`, and `@expo/vector-icons` were added for the
claymorphism/avatar UI — `npm install` picks them up; if versions ever mismatch your Expo SDK, run
`npx expo install react-native-svg expo-linear-gradient @expo/vector-icons`.)

Scan the QR code with Expo Go (Android) or the Camera app (iOS) to run it on a real device — this
is required to exercise real GPS and real accelerometer/gyroscope data.

## Pointing the app at your backend

The backend defaults to `http://localhost:8000`, which is **not reachable from a physical phone**.
Before testing on a real device:

1. Start the backend: `cd ../backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Find your computer's LAN IP (e.g. `192.168.1.23`)
3. In the app, open **Settings** and set the backend URL to `http://<your-LAN-ip>:8000`
   (or edit the default in `src/api/client.js`)

Special cases:
- **Android emulator**: use `http://10.0.2.2:8000` to reach your host machine.
- **iOS simulator**: `http://localhost:8000` works directly since the simulator shares the host's
  network stack.
- Phone and computer must be on the same Wi-Fi network for the LAN-IP case.

## Real data / real sensors used

- **GPS**: `src/hooks/useDeviceLocation.js` requests real foreground location permission via
  `expo-location` and streams real device coordinates. No hardcoded/simulated positions.
- **Motion**: `src/hooks/useMotionFeatures.js` reads real `Accelerometer`/`Gyroscope` samples from
  `expo-sensors`, computes magnitude/variance over a real sliding window, and converts to the
  `accel_magnitude` / `accel_variance` / `gyro_magnitude` feature shape the backend's
  `/walkguard/event` endpoint expects.
- **RouteGuard "live ride"**: `src/api/suratRealTrace.js` replays the real recorded OSM GPS trace
  bundled from `data/gps_traces/surat_real_trace.csv` (54 real points, recorded 2018-08-29) at
  real timestamps, since no live ride-hailing vehicle feed is available for a hackathon prototype.
  This is documented, not hidden.

## Known limitations

- `react-native-maps` requires a native build (or an Expo dev client / EAS build) for full
  map-tile rendering on some platforms; in plain Expo Go, map interactions may be limited to what
  Expo Go's included native modules support. For a production build, run
  `npx expo prebuild` and build with EAS or Android Studio / Xcode.
- The backend's imagery/crime datasets are currently thin (see `../data/README.md`), so
  `InfrastructureScreen` and `SafetyInsightScreen` will show sparse real evidence rather than a
  dense demo — this reflects genuine open-data scarcity for the target region, not an app bug.
- `LiveRideScreen`'s replayed trace is short (54 points); a longer real trace can be swapped in by
  replacing `data/gps_traces/surat_real_trace.csv` with another real recorded trace of the same
  format (`lat,lon,timestamp_utc`).
