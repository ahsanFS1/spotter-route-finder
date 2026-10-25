# Spotter Route Finder: Implementation Plan

## 1. Goal
React + Django app that recommends the safest of 3 truck routes using forecast weather
sampled at the truck's ETA, the provided risk and load rules, and travel time. Graded:
40% routing/weather/risk/recommendation logic, 40% UI/map/heatmap smoothness and
performance, 15% code quality, 5% docs and walkthrough. Correctness and clarity over features.

## 2. Stack and providers
| Concern | Choice | Notes |
|---|---|---|
| Backend | Django 5 + DRF, Python 3.12+ | pure-Python domain package, no Django imports |
| Frontend | React 18 + Vite + TypeScript | MapLibre GL JS for map and heatmap layer |
| Routing | OSRM public demo (`alternatives=true`) behind a `RoutingProvider` interface | third route via via-point fallback |
| Geocoding | Photon (komoot) with Nominatim fallback, `GeocodingProvider` interface | autocomplete in UI |
| Weather | Open-Meteo forecast API, batched multi-location, hourly | keyless, mph and inch units |
| Basemap | OpenFreeMap or MapTiler-free-style raster/vector tiles | keyless |
| Cache | Django cache (LocMem dev, Redis optional) | geocode, route and weather keyed by rounded coords + hour |
| Tests | pytest + pytest-django (backend), Vitest + Testing Library (frontend) | |
| Hosting | Render (Django, gunicorn, whitenoise) + Vercel (frontend) | free tiers |

## 3. Domain rules (single source of truth: `risk/rules.py`)
Levels, ordered: LOW=0, MODERATE=1, HIGH=2, SEVERE=3, NO_TRAVEL=4.

Weather table (lower bound inclusive, upper bound exclusive):
- Wind mph: <25 low, 25-<35 moderate, 35-<45 high, 45-<55 severe, >=55 no travel
- Rain in/hr: <0.10 low, 0.10-<0.25 moderate, 0.25-<0.50 high, 0.50-<=1.00 severe, >1.00 no travel
- Snow in/hr: <0.5 low, 0.5-<1.0 moderate, 1.0-<2.0 high, 2.0-<=3.0 severe, >3.0 no travel

Load rules (wind only, as given), applied after the table, can only raise the level:
- wind >= 55: NO_TRAVEL for any load
- wind 45-<55 and load > 30,000 lb: NO_TRAVEL
- wind 35-<45 and load > 40,000 lb: SEVERE

Checkpoint level = max(wind level, rain level, snow level) after load rules.
Interpretation decisions to document in README:
- Worst-of across conditions.
- Boundary values: ranges in the brief are written inclusive of the lower bound; the upper
  edge of Severe rain/snow ("0.50-1.00", "2.0-3.0") is inclusive, No Travel is strictly greater.
- Wind uses sustained 10 m wind speed (gusts shown as extra info only).
- Rain = rain + showers; snow = snowfall (inches per hour).
- Load rules do not change rain/snow.

## 4. Pipeline
1. Validate input (origin, destination as text or lat/lng, ISO departure datetime with tz,
   load weight lb > 0, sample interval in {10, 25, 50}, default 25).
2. Geocode origin and destination.
3. Fetch up to 3 routes. OSRM alternatives first; if fewer than 3 distinct, create via-point
   routes (offset midpoint perpendicular to the straight line by about 10-15% of distance,
   snapped by routing) and de-duplicate by geometry overlap (>90% shared = duplicate).
   Label routes (Fastest, Alt 1, Alt 2). If only 1 or 2 are obtainable, return what exists
   with a warning; never fabricate.
4. Per route: resample polyline into checkpoints every N miles (always include start and end),
   compute cumulative distance, ETA = departure + cumulative duration (interpolated from
   OSRM per-step durations/annotations). Each checkpoint owns the segment from its midpoint
   with the previous checkpoint to its midpoint with the next, so miles per level sum
   exactly to route length.
5. Fetch weather for all checkpoints of all 3 routes in batched Open-Meteo calls (dedupe
   coordinates, round to 2 decimals), pick the hourly value nearest the ETA (interpolate
   linearly between the two surrounding hours for wind/precip). If the ETA is beyond
   the forecast horizon (more than 16 days is the API limit; we only support forecast_days up
   to 3 for the heatmap) mark the checkpoint `weather_unavailable` and exclude it from
   scoring, surfacing a warning; do not assume Low.
6. Score checkpoints (section 3). Route metrics: miles per level, average risk (mile-weighted
   mean of level index), max level, disqualified flag if any NO_TRAVEL, duration, distance.
7. Rank: not disqualified first; then fewest Severe miles, fewest High miles, lowest average
   risk, shortest duration. Return recommended route id plus a human-readable reason
   (which criterion decided it). If all disqualified, recommend none and say so.
8. Heatmap endpoint: corridor grid and hourly frames (section 6).

## 5. API (DRF)
- `GET /api/geocode/?q=` -> suggestions
- `POST /api/routes/analyze/` -> {routes[], recommended_route_id, reason, warnings[]}
  each route: id, label, geometry (GeoJSON LineString), distance_mi, duration_s, summary,
  metrics, checkpoints[{lat,lng,mile,eta,weather{wind_mph,rain_in_hr,snow_in_hr},levels,level}]
- `POST /api/heatmap/` -> {hours:[iso x 49], points:[{lat,lng}], frames:[[intensity...]]}
  compact columnar JSON (frame-major arrays) to keep payload small; gzip enabled.
- `GET /api/health/`
- Consistent error shape {error:{code,message,fields}}; request throttling; CORS limited to
  the frontend origin.

## 6. Heatmap design
- Corridor: union of the 3 route geometries, buffered about 25 miles; grid spacing about 20-25 miles,
  capped at about 150 points (adaptive spacing for very long trips).
- One batched Open-Meteo request set (chunked by 50-100 locations) for hours 0-48 from
  departure time rounded down to the hour. Per point per hour compute the weather level using
  the same rules (load-aware) so the heatmap matches route scoring.
- Frontend loads all frames once; slider changes only a MapLibre feature-state/data update
  (setData with precomputed per-frame GeoJSON or a heatmap-weight expression keyed by frame),
  debounced via requestAnimationFrame. Target 60 fps interaction.
- Heatmap weight = level/4; color ramp green-yellow-orange-red-dark.

## 7. Backend structure
```
backend/
  manage.py, pyproject.toml / requirements.txt
  config/ (settings split dev/prod, urls, wsgi)
  apps/api/ (views, serializers, urls, throttles, errors)
  domain/ (pure python)
    rules.py, scoring.py, sampling.py, ranking.py, geo.py, models.py (dataclasses)
  services/
    routing/ (base.py, osrm.py, alternatives.py)
    geocoding/ (base.py, photon.py)
    weather/ (base.py, open_meteo.py, interpolate.py)
    analysis.py (orchestrator)
    heatmap.py
  tests/ (unit for domain, provider tests with recorded fixtures, API tests)
```
Providers are injected so tests use fakes, and no test hits the network.

## 8. Frontend structure
```
frontend/src/
  api/ (client, types)
  features/
    trip-form/ (autocomplete, datetime, weight, interval)
    results/ (route cards, recommended badge, metrics, reason)
    map/ (MapView, route layers, checkpoint markers, popups, heatmap layer, legend)
    forecast-slider/
  hooks/, lib/ (format, colors), styles/
```
UX: form panel + results panel + full-height map. Route colors by identity; line casing
shows risk via segmented gradient (per-segment risk coloring). Checkpoint markers colored by
level with popup (ETA, weather values, level). Loading skeletons, error and empty states,
keyboard-accessible, responsive down to tablet and phone width, WCAG AA contrast, `prefers-reduced-motion`.
Map fits bounds on result; selecting a card
highlights its route.

## 9. Testing strategy
- Domain: table-driven tests for every threshold boundary, every load rule, combinations,
  segment mile accounting sums to total, ETA interpolation, ranking tie-breakers, disqualification,
  all-disqualified case.
- Services: provider parsing against saved fixtures; alternatives de-duplication; Open-Meteo
  batching and time interpolation; forecast-horizon handling.
- API: validation errors, happy path with fake providers, throttling, error shapes.
- Frontend: Vitest for formatters and the slider/frame logic; component tests for form and results;
  one Playwright smoke test against local stack.
- Manual: 3 real trips (short, long cross-country, one with winter weather) before deploy.

## 10. Performance and robustness
- Parallelize weather chunks (threadpool), per-request timeouts, retry with backoff on 429/5xx,
  circuit-friendly error messages when a provider is down.
- Cache by (rounded lat/lng, forecast hour) with a short TTL; cache routes by endpoints.
- Respect OSRM demo and Nominatim usage policy (User-Agent, low rate); README states
  providers are swappable for production.
- Frontend: memoized layers, no re-render of map on slider move, code-split the map bundle.

## 11. Deployment
- Render web service (gunicorn, whitenoise, env: SECRET_KEY, ALLOWED_HOSTS, CORS_ORIGINS, DEBUG=0).
- Vercel for frontend with `VITE_API_BASE_URL`.
- `render.yaml`, `vercel.json`, `.env.example`, a CI workflow (lint + tests) on GitHub Actions.
- Free-tier cold start mitigation: frontend shows a "waking server" state; health ping.

## 12. Documentation and walkthrough
- README: overview, screenshot, architecture diagram, setup, env vars, API, rule
  interpretations, assumptions and limitations, how to run tests, deployment.

## 13. Milestones
1. Scaffold, tooling, CI, health endpoint.
2. Domain package and exhaustive tests.
3. Providers (geocode, routing with alternatives, weather) with fixtures.
4. Analysis orchestrator and API.
5. Heatmap service and endpoint.
6. Frontend shell, form, results, map routes and checkpoints.
7. Heatmap layer and slider; performance pass.
8. Polish, accessibility, responsive, error states.
9. Docs, deploy, smoke test the hosted app, walkthrough script.

## 14. Risks
- OSRM demo may rate-limit or lack 3 alternatives -> via-point fallback, provider interface.
- Open-Meteo rate limits on large batches -> chunking, cache, grid cap.
- Render cold starts -> loading state.
- Ambiguous rules -> documented interpretation, centralized constants.

---

# Revisions (these supersede earlier sections)

Verified against the live APIs: Open-Meteo returns a list for multi-location requests and
a single object for one location (normalize both); with `wind_speed_unit=mph` and
`precipitation_unit=inch`, wind, rain, showers and snowfall all come back in mph / inches;
`timezone=UTC` returns times as UTC.

## Rules and scoring
- Bands: lower bound inclusive, upper bound exclusive, except the Severe rain/snow bands where
  1.00 / 3.0 are inclusive (No Travel is strictly greater). Load rules use strict `>`
  (30,000 lb and 40,000 lb exactly do not trigger). Load rules only raise the level (`max`).
- Wind = sustained 10 m wind. Rain = rain + showers. Snow = snowfall (inch/hr). Units are
  requested explicitly and asserted in a fixture test.
- Ranking key is an explicit tuple: (no_travel_miles > 0, severe_or_worse_miles,
  high_miles, avg_risk, duration_s). Severe miles include No Travel miles. Miles are rounded
  to 0.1 and average risk to 2 decimals before comparing so near-ties fall through. The
  `reason` names the first criterion where the winner differs from the runner-up.
- A route with any No Travel checkpoint is flagged "No Travel" and ranked after all others
  (documented interpretation). If all are flagged, no recommendation is made and the UI says so.
- Segment ownership: each checkpoint owns the miles from itself up to the next checkpoint
  (last one owns the remainder), so miles by level sum to route length. Tested, including
  routes shorter than one interval.

## Weather timing
- No interpolation. Use the hour nearest the ETA for every value. Drop `interpolate.py`.
- Fetch in UTC; convert for display only. ETAs display in the origin's local time zone with the
  zone label.
- Departure must be between now-1h and now+14 days. `forecast_days` is derived from
  offset + trip duration + 48h, capped at 16. Checkpoints beyond the horizon are
  `weather_unavailable`, excluded from averages (divide by scored miles), and surfaced as unscored
  miles with a visible badge. Never assumed Low.

## Routing
- OSRM public demo is car-profile only. README states this. Travel times use the car duration
  scaled by a documented truck speed factor (default 0.9) so ETAs are not claimed as truck-exact.
- The via-point fallback is the normal path. Try left and right perpendicular via-points at the
  midpoint, route through them, reject routes more than 1.5x the fastest distance or more than 90%
  overlapping another route, keep the best 3 distinct. Return fewer with a warning rather than faking.
- Request `overview=full&geometries=geojson&steps=true`; derive per-point time by linear
  interpolation along step durations. No per-edge annotations (too large for long trips).
- Base URL configurable. Responses cached by endpoints so repeat demos are fast.

## Geocoding
- Photon only (no Nominatim). Coordinates are GeoJSON [lon, lat], flipped in one place. The form
  submits the selected suggestion's coordinates; the backend geocodes free text only as a fallback.
  Autocomplete: 3 chars minimum, 300 ms debounce, US/CA bias.

## Heatmap
- No shapely. Corridor points = samples along all routes every ~25 mi plus lateral offsets of
  +/-15 mi, deduped on a rounded grid, capped at 150 (spacing grows for long trips).
- Hour h means "forecast valid at departure + h" for every grid point; the UI labels it so.
- Payload is plain JSON. One static GeoJSON with per-hour level properties `l0..l48`; the slider
  only updates a paint expression (`['get', 'l'+hour]`) inside requestAnimationFrame. No `setData`
  per frame. A MapLibre heatmap layer (weight from level, zoom-scaled radius) with a
  level-coloured circle layer on top so severity stays readable.
- Shares one scoring function with routes; a test asserts heatmap level equals checkpoint level for
  the same coordinate, hour and load.

## Scope cuts
- Drop Redis, Nominatim, Playwright, code-splitting. Keep LocMem cache.
- Deploy: single Render web service with whitenoise serving the built frontend if it works
  cleanly; otherwise Vercel + Render. gunicorn timeout 60 s, 2+ threads, concurrent provider calls.
- Route line coloured per route; checkpoint markers coloured by risk level. Per-segment gradients only if time remains.
- Checkpoint count guard: warn and cap when interval x distance gives more than ~400 checkpoints
  per route; weather chunked at 50-100 locations.
- UI progress stages while analyzing; partial results with warnings instead of 500s.
- Legend shows rule thresholds; slider is keyboard operable with play/pause and date+hour label.
